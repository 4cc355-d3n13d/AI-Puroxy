"""AI Monitoring Proxy — локальный прокси к ИИ-API с логом, балансом и документацией."""
from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, docsrc, media, proxy, stats

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
    _remember_listen_address()
    cfg = config.load()
    db.migrate(cfg["source"])  # источники и раздельные суммы у записей прежних версий
    db.backfill_details()  # разбор тел у записей, сделанных до появления этих полей
    db.backfill_media()  # картинки из записей, сделанных до появления галереи
    db.recompute_costs(cfg["cost_mode"])
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
    source = config.find_source(cfg, cfg["source"])
    return {
        "request": request,
        "active": active,
        "configured": config.is_configured(),
        "base_url": cfg["base_url"],
        "balance_threshold": cfg["balance_threshold"],
        "sources": cfg["sources"],
        "source_names": {s["id"]: s["name"] for s in cfg["sources"]},
        "active_source_name": source["name"] if source else "",
        "v": _static_version(),
    }


def _launch_address() -> tuple[str, int | None]:
    """Адрес, на котором запущен процесс.

    `python -m app` и run.sh выставляют AI_PROXY_LISTEN; сервисы прежних версий
    запускали `uvicorn … --host H --port P` — тогда адрес берётся из аргументов.
    """
    listen = os.environ.get("AI_PROXY_LISTEN", "")
    if ":" in listen:
        host, port = listen.rsplit(":", 1)
        return host, int(port) if port.isdigit() else None
    args = sys.argv[1:]
    found: dict[str, str] = {}
    for index, arg in enumerate(args):
        for key in ("--host", "--port"):
            if arg == key and index + 1 < len(args):
                found[key] = args[index + 1]
            elif arg.startswith(key + "="):
                found[key] = arg.split("=", 1)[1]
    port = found.get("--port", "")
    return found.get("--host", ""), int(port) if port.isdigit() else None


def _listen_address(request: Request) -> tuple[str, int | None]:
    """Фактический адрес; если он неизвестен, порт берётся из сокета."""
    host, port = _launch_address()
    if port is None:
        server = request.scope.get("server") or (None, None)
        port = server[1]
    return host, port


def _remember_listen_address() -> None:
    """Записать фактический адрес в настройки, если там его ещё нет.

    У сервиса прежней версии адрес жил только в plist, а в настройках стояло
    значение по умолчанию 127.0.0.1: первое же сохранение формы записало бы его,
    и после перезапуска сервис молча пропал бы из локальной сети.
    """
    stored = config.stored_keys()
    if not config.CONFIG_PATH.exists() or {"host", "port"} <= stored:
        return
    host, port = _launch_address()
    values = {}
    if "host" not in stored and host:
        values["host"] = host
    if "port" not in stored and port:
        values["port"] = port
    if values:
        config.save(values)


def _can_restart() -> bool:
    """Перезапуститься можно только под сервисом: launchd/systemd поднимут процесс сами."""
    return os.environ.get("AI_PROXY_SERVICE") == "1"


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


@app.get("/images", response_class=HTMLResponse)
async def images_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "images.html", _page_context(request, "images"))


@app.get("/models", response_class=HTMLResponse)
async def models_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "models.html", _page_context(request, "models"))


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: int = 0) -> HTMLResponse:
    cfg = config.load()
    listen_host, listen_port = _listen_address(request)
    context = _page_context(request, "settings")
    context.update(
        {
            "cfg": cfg,
            "source_rows": [
                {**source, "masked_key": config.masked_key(source["api_key"])} for source in cfg["sources"]
            ],
            "cost_modes": config.COST_MODES,
            "listen_host": listen_host,
            "listen_port": listen_port,
            "restart_needed": listen_port is not None and (
                listen_port != cfg["port"] or bool(listen_host and listen_host != cfg["host"])
            ),
            "can_restart": _can_restart(),
            "saved": bool(saved),
            "db_path": str(config.DB_PATH),
            "db_size": stats.db_size_bytes(),
            "overview": stats.overview(),
        }
    )
    return templates.TemplateResponse(request, "settings.html", context)


@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request) -> Response:
    form = await request.form()
    current = config.load()
    values: dict[str, Any] = {
        key: str(form.get(key) or "").strip()
        for key in ("retention_days", "balance_threshold", "docs_domain", "balance_poll_seconds",
                    "host", "port", "cost_mode")
        if key in form
    }
    if "src_url" in form:
        values.update(_sources_from_form(form, current))
    elif "base_url" in form or "api_key" in form:
        # прежний вид формы (один источник): пустой ключ означает «оставить как есть»
        values["api_key"] = str(form.get("api_key") or "").strip() or current["api_key"]
        values["base_url"] = (str(form.get("base_url") or "").strip()
                              or current["base_url"] or config.DEFAULT_BASE_URL)

    cfg = config.save(values)
    db.apply_retention(cfg["retention_days"])
    if cfg["cost_mode"] != current["cost_mode"]:
        db.recompute_costs(cfg["cost_mode"])
    docsrc._raw.cache_clear()
    if config.is_configured():
        await proxy.fetch_balance(force=True)
    return RedirectResponse("/settings?saved=1", status_code=303)


def _sources_from_form(form: Any, current: dict[str, Any]) -> dict[str, Any]:
    """Список источников из строк формы. Пустой ключ у существующего источника — «не менять»."""
    ids, names = form.getlist("src_id"), form.getlist("src_name")
    urls, keys = form.getlist("src_url"), form.getlist("src_key")
    deleted = set(form.getlist("src_delete"))
    active_row = str(form.get("active_source") or "")
    known = {source["id"]: source for source in current["sources"]}

    sources = []
    for index, url in enumerate(urls):
        source_id = str(ids[index]) if index < len(ids) else ""
        url = str(url).strip()
        if str(index) in deleted or not url:
            continue
        key = str(keys[index] if index < len(keys) else "").strip()
        if not key and source_id in known:
            key = known[source_id]["api_key"]
        name = str(names[index] if index < len(names) else "").strip()
        # новому источнику id назначит config; существующий сохраняет свой — на нём история
        sources.append({"id": source_id, "name": name, "base_url": url, "api_key": key,
                        "active": active_row == str(index)})
    return {"sources": sources, "active_source": ""}


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
    latest = db.latest_balance(cfg["source"])
    return JSONResponse(
        stats.jsonable(
            {
                **stats.overview(),
                "balance": balance,
                "balance_checked_at": latest["ts"] if latest else None,
                "balance_threshold": cfg["balance_threshold"],
                "source": cfg["source"],
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
    upstream: str = "",
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
        "upstream": upstream or None,
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
    source = config.load()["source"] or None
    data = stats.balance_calendar(month or None, source)
    data["balance"] = proxy.cached_balance()
    latest = db.latest_balance(source)
    data["balance_checked_at"] = latest["ts"] if latest else None
    return JSONResponse(stats.jsonable(data))


@app.get("/_api/balance/day/{day}")
async def api_balance_day(day: str) -> JSONResponse:
    return JSONResponse(stats.jsonable(stats.day_breakdown(day, config.load()["source"] or None)))


@app.post("/_api/balance/refresh")
async def api_balance_refresh() -> JSONResponse:
    amount = await proxy.fetch_balance(force=True)
    return JSONResponse({"balance": amount, "checked_at": str(date.today())})


@app.get("/_api/media")
async def api_media(
    direction: str = "", kind: str = "", model: str = "", q: str = "", page: int = 1, page_size: int = 60
) -> JSONResponse:
    filters = {"direction": direction or None, "kind": kind or None, "model": model or None, "q": q or None}
    return JSONResponse(stats.jsonable(stats.media_page(filters, page, page_size)))


@app.get("/_media/{name}")
async def media_file(name: str) -> Response:
    path = media.path_of(name)
    if path is None or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    # имя — хэш содержимого, поэтому файл по этому адресу никогда не меняется
    return FileResponse(path, media_type=media.mime_of_file(name),
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.post("/_api/restart")
async def api_restart() -> JSONResponse:
    """Завершить процесс, чтобы сервис поднял его с новыми адресом и портом."""
    if not _can_restart():
        return JSONResponse(
            {"error": "Прокси запущен не сервисом — перезапустите его вручную."}, status_code=409
        )
    cfg = config.load()
    # ответ должен успеть уйти до остановки; SIGTERM даёт uvicorn штатно закрыть базу
    asyncio.get_running_loop().call_later(0.5, os.kill, os.getpid(), signal.SIGTERM)
    return JSONResponse({"ok": True, "host": cfg["host"], "port": cfg["port"]})


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
