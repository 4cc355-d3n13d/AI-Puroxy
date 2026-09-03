"""AI Monitoring Proxy — локальный прокси к ИИ-API с логом, балансом и документацией."""
from __future__ import annotations

import asyncio
import contextlib
import sys
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, docsrc, proxy, stats

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="AI Monitoring Proxy", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

_background: list[asyncio.Task[Any]] = []


# --------------------------------------------------------------------------- жизненный цикл


@app.on_event("startup")
async def _startup() -> None:
    try:
        db.connect()
    except db.DatabaseBusyError as error:
        # без трейсбека: причина понятна и требует действия пользователя, а не отладки
        print(error, file=sys.stderr, flush=True)
        raise SystemExit(1) from None
    db.backfill_details()  # разбор тел у записей, сделанных до появления этих полей
    cfg = config.load()
    db.apply_retention(cfg["retention_days"])
    _background.append(asyncio.create_task(_maintenance_loop()))


@app.on_event("shutdown")
async def _shutdown() -> None:
    for task in _background:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    _background.clear()
    await proxy.shutdown()
    db.close()


async def _maintenance_loop() -> None:
    """Периодически опрашиваем баланс и чистим старые записи."""
    while True:
        cfg = config.load()
        try:
            if config.is_configured():
                await proxy.fetch_balance(force=True)
            db.apply_retention(cfg["retention_days"])
        except Exception:  # фоновая задача не должна падать
            pass
        await asyncio.sleep(max(30, cfg["balance_poll_seconds"]))


def _static_version() -> str:
    """Метка версии статики по времени изменения файлов.

    Без неё браузер может показывать закэшированный CSS/JS после обновления кода:
    StaticFiles не присылает Cache-Control, и браузер кэширует эвристически,
    иногда вообще не спрашивая сервер.
    """
    static_dir = BASE_DIR / "static"
    try:
        newest = max(path.stat().st_mtime for path in static_dir.glob("*") if path.is_file())
    except (OSError, ValueError):
        return "0"
    return str(int(newest))


def _page_context(request: Request, active: str) -> dict[str, Any]:
    cfg = config.load()
    return {
        "request": request,
        "active": active,
        "configured": config.is_configured(),
        "base_url": cfg["base_url"],
        "balance_threshold": cfg["balance_threshold"],
        "v": _static_version(),
    }


# --------------------------------------------------------------------------- страницы


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/monitor" if config.is_configured() else "/settings", status_code=302)


@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "monitor.html", _page_context(request, "monitor"))


@app.get("/balance", response_class=HTMLResponse)
async def balance_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "balance.html", _page_context(request, "balance"))


@app.get("/models", response_class=HTMLResponse)
async def models_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "models.html", _page_context(request, "models"))


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: int = 0) -> HTMLResponse:
    cfg = config.load()
    context = _page_context(request, "settings")
    context.update(
        {
            "cfg": cfg,
            "masked_key": config.masked_key(cfg["api_key"]),
            "saved": bool(saved),
            "db_path": str(config.DB_PATH),
            "db_size": stats.db_size_bytes(),
            "overview": stats.overview(),
        }
    )
    return templates.TemplateResponse(request, "settings.html", context)


@app.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    api_key: str = Form(""),
    base_url: str = Form(config.DEFAULTS["base_url"]),
    retention_days: str = Form("0"),
    balance_threshold: str = Form("0"),
    docs_domain: str = Form("localhost"),
    balance_poll_seconds: str = Form("300"),
) -> Response:
    current = config.load()
    # пустое поле ключа означает «оставить как есть»
    values = {
        "api_key": api_key.strip() or current["api_key"],
        "base_url": base_url.strip() or config.DEFAULTS["base_url"],
        "retention_days": _to_number(retention_days, 0, integer=True),
        "balance_threshold": _to_number(balance_threshold, 0.0),
        "docs_domain": docs_domain.strip() or "localhost",
        "balance_poll_seconds": _to_number(balance_poll_seconds, 300, integer=True),
    }
    cfg = config.save(values)
    db.apply_retention(cfg["retention_days"])
    docsrc._raw.cache_clear()
    if config.is_configured():
        await proxy.fetch_balance(force=True)
    return RedirectResponse("/settings?saved=1", status_code=303)


def _to_number(raw: str, default: float, integer: bool = False) -> float | int:
    try:
        value = float(str(raw).replace(",", ".").strip())
    except (TypeError, ValueError):
        return default
    return int(value) if integer else value


@app.get("/docs", response_class=HTMLResponse)
async def docs_index(request: Request) -> Response:
    pages = docsrc.pages()
    if not pages:
        return HTMLResponse("<h1>Документация не найдена</h1>", status_code=404)
    return RedirectResponse(f"/docs/{pages[0]['slug']}", status_code=302)


@app.get("/docs/{slug}", response_class=HTMLResponse)
async def docs_page(request: Request, slug: str) -> HTMLResponse:
    cfg = config.load()
    page = docsrc.page(slug, cfg["docs_domain"])
    if page is None:
        return HTMLResponse("<h1>Страница документации не найдена</h1>", status_code=404)
    context = _page_context(request, "docs")
    context.update({"page": page, "pages": docsrc.pages(), "sections": docsrc.SECTIONS, "domain": cfg["docs_domain"]})
    return templates.TemplateResponse(request, "docs.html", context)


# --------------------------------------------------------------------------- API интерфейса


@app.get("/_api/overview")
async def api_overview() -> JSONResponse:
    cfg = config.load()
    balance = proxy.cached_balance()
    if balance is None and config.is_configured():
        balance = await proxy.fetch_balance()
    latest = db.latest_balance()
    return JSONResponse(
        stats.jsonable(
            {
                **stats.overview(),
                "balance": balance,
                "balance_checked_at": latest["ts"] if latest else None,
                "balance_threshold": cfg["balance_threshold"],
                "configured": config.is_configured(),
                "low_balance": bool(
                    cfg["balance_threshold"] and balance is not None and balance < cfg["balance_threshold"]
                ),
            }
        )
    )


@app.get("/_api/requests")
async def api_requests(
    model: str = "",
    endpoint: str = "",
    status: str = "",
    kind: str = "",
    q: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 50,
) -> JSONResponse:
    filters = {
        "model": model or None,
        "endpoint": endpoint or None,
        "status": status or None,
        "kind": kind or None,
        "q": q or None,
        "date_from": date_from or None,
        "date_to": date_to or None,
    }
    return JSONResponse(stats.jsonable(stats.requests_page(filters, page, page_size)))


@app.get("/_api/requests/{request_id}")
async def api_request_detail(request_id: int) -> JSONResponse:
    row = stats.request_detail(request_id)
    if row is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(stats.jsonable(row))


@app.get("/_api/filters")
async def api_filters() -> JSONResponse:
    return JSONResponse(stats.jsonable(stats.filter_options()))


@app.get("/_api/chart")
async def api_chart(days: int = 30, model: str = "") -> JSONResponse:
    return JSONResponse(stats.jsonable(stats.daily_model_counts(days, model or None)))


@app.get("/_api/models")
async def api_models() -> JSONResponse:
    return JSONResponse(stats.jsonable(stats.models_summary()))


@app.get("/_api/balance/calendar")
async def api_balance_calendar(month: str = "") -> JSONResponse:
    data = stats.balance_calendar(month or None)
    data["balance"] = proxy.cached_balance()
    latest = db.latest_balance()
    data["balance_checked_at"] = latest["ts"] if latest else None
    return JSONResponse(stats.jsonable(data))


@app.get("/_api/balance/day/{day}")
async def api_balance_day(day: str) -> JSONResponse:
    return JSONResponse(stats.jsonable(stats.day_breakdown(day)))


@app.post("/_api/balance/refresh")
async def api_balance_refresh() -> JSONResponse:
    amount = await proxy.fetch_balance(force=True)
    return JSONResponse({"balance": amount, "checked_at": str(date.today())})


# --------------------------------------------------------------------------- прокси


@app.api_route(
    "/v1/{subpath:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_v1(request: Request, subpath: str) -> Response:
    return await proxy.handle(request, f"v1/{subpath}")


@app.api_route(
    "/api/v1/{subpath:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_api_v1(request: Request, subpath: str) -> Response:
    """Совместимость с base_url вида http://localhost:8787/api."""
    return await proxy.handle(request, f"v1/{subpath}")
