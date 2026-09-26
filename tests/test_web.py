"""Смоук-тест HTTP-слоя: каждая страница должна отрендериться, каждый /_api/* — ответить.

Ловит поломки шаблонов и несовместимость с новыми версиями FastAPI/Starlette —
именно такую, как удалённая из Starlette старая сигнатура TemplateResponse.

Запуск: ./.venv/bin/python tests/test_web.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AI_PROXY_DATA_DIR"] = tempfile.mkdtemp(prefix="ai-proxy-web-test-")

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, docsrc  # noqa: E402
from app.main import app  # noqa: E402

checks = 0
failures: list[str] = []


def check(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if condition:
        print(f"  ✓ {label}")
    else:
        failures.append(label)
        print(f"  ✗ {label}")


# устаревшие вызовы библиотек не должны проходить незамеченными
warnings.simplefilter("error", DeprecationWarning)

with TestClient(app) as client:
    print("страницы")
    # прокси не настроен: корень должен вести на /settings
    response = client.get("/", follow_redirects=False)
    check(response.status_code == 302 and response.headers["location"] == "/settings",
          "/ без настроек → редирект на /settings")

    for path in ("/monitor", "/balance", "/models", "/images", "/settings"):
        response = client.get(path)
        check(response.status_code == 200 and "<html" in response.text.lower(),
              f"{path} рендерится")

    print("документация")
    response = client.get("/docs", follow_redirects=False)
    check(response.status_code == 302, "/docs → редирект на первую страницу")
    for page in docsrc.pages():
        response = client.get(f"/docs/{page['slug']}")
        check(response.status_code == 200 and "speshu.ai" not in response.text,
              f"/docs/{page['slug']} рендерится с подменённым доменом")

    print("API интерфейса")
    for path in (
        "/_api/overview",
        "/_api/requests?page_size=1",
        "/_api/filters",
        "/_api/chart?days=7",
        "/_api/models",
        "/_api/balance/calendar",
        "/_api/balance/day/2026-01-01",
        "/_api/media?direction=output",
    ):
        response = client.get(path)
        check(response.status_code == 200 and response.headers["content-type"].startswith("application/json"),
              f"{path} отвечает JSON")

    check(client.get("/_api/requests/999999/page").json() == {"page": None},
          "/_api/requests/{id}/page на несуществующей записи → page: null")
    check(client.get("/_api/requests/999999").status_code == 404,
          "/_api/requests/{id} на несуществующей записи → 404")

    print("прокси без настроек")
    response = client.get("/v1/models")
    check(response.status_code == 503 and response.json()["error"]["type"] == "proxy_not_configured",
          "/v1/* без настроек → понятная 503, а не падение")

    print("сохранение настроек")
    response = client.post(
        "/settings",
        data={
            "api_key": "sk-test", "base_url": "https://example.invalid/api",
            "retention_days": "3", "balance_threshold": "10,5",
            "docs_domain": "proxy.local", "balance_poll_seconds": "300",
        },
        follow_redirects=False,
    )
    check(response.status_code == 303, "POST /settings → редирект")
    response = client.get("/", follow_redirects=False)
    check(response.headers["location"] == "/monitor", "после настройки / ведёт на /monitor")
    check("proxy.local" in client.get("/docs/balance").text, "домен из настроек попал в /docs")

    print("источники, сервер и режим стоимости из формы")
    first_id = config.load()["source"]
    response = client.post(
        "/settings",
        data={
            "src_id": [first_id, "", ""],
            "src_name": ["Основной", "Запасной", "Удаляемый"],
            "src_url": ["https://example.invalid/api", "https://backup.invalid/api/", "https://gone.invalid"],
            "src_key": ["", "sk-backup", "sk-gone"],
            "src_delete": ["2"],
            "active_source": "1",
            "host": "0.0.0.0", "port": "9123", "cost_mode": "pricelist",
            "retention_days": "0", "balance_threshold": "0", "docs_domain": "proxy.local",
            "balance_poll_seconds": "300",
        },
        follow_redirects=False,
    )
    cfg = config.load()
    check(response.status_code == 303 and [s["name"] for s in cfg["sources"]] == ["Основной", "Запасной"],
          "источник добавлен, отмеченный на удаление — удалён")
    check(cfg["sources"][0]["id"] == first_id and cfg["sources"][0]["api_key"] == "sk-test",
          "у существующего источника id и ключ (пустое поле) сохранены")
    check(cfg["base_url"] == "https://backup.invalid/api" and cfg["api_key"] == "sk-backup",
          "активным стал отмеченный источник")
    check(cfg["host"] == "0.0.0.0" and cfg["port"] == 9123 and cfg["cost_mode"] == "pricelist",
          "адрес, порт и режим стоимости сохранены")
    page = client.get("/settings").text
    check("нужен перезапуск" in page and "Перезапустить сейчас" not in page,
          "/settings предупреждает о перезапуске; без сервиса кнопки нет")
    check(client.post("/_api/restart").status_code == 409, "перезапуск без сервиса → 409, процесс жив")

    print("префиксы источников")
    client.post("/settings", data={
        "src_id": [s["id"] for s in config.load()["sources"]],
        "src_name": ["Основной", "Запасной"], "src_prefix": ["", "backup"],
        "src_url": ["https://example.invalid/api", "https://backup.invalid/api"],
        "src_key": ["", ""], "active_source": "0",
    })
    cfg = config.load()
    check([s["prefix"] for s in cfg["sources"]] == [cfg["sources"][0]["id"], "backup"],
          "префикс из формы сохранён, пустой — по id")
    before = db.query("SELECT count(*) AS n FROM requests")[0]["n"]
    response = client.get("/backup/v1/models")
    last = db.query("SELECT upstream, path FROM requests ORDER BY id DESC LIMIT 1")[0]
    check(response.status_code == 502 and last["upstream"] == cfg["sources"][1]["id"]
          and last["path"] == "/v1/models",
          "/<префикс>/v1/… уходит в свой источник и логируется с ним")
    client.get("/v1/models")
    last = db.query("SELECT upstream FROM requests ORDER BY id DESC LIMIT 1")[0]
    check(last["upstream"] == cfg["source"], "/v1/… без префикса — в источник по умолчанию")
    client.get("/api/v1/models")
    last = db.query("SELECT upstream FROM requests ORDER BY id DESC LIMIT 1")[0]
    check(last["upstream"] == cfg["source"], "/api/v1/… не принимается за префикс «api»")
    response = client.get("/nope/v1/models")
    check(response.status_code == 404 and response.json()["error"]["type"] == "unknown_source"
          and db.query("SELECT count(*) AS n FROM requests")[0]["n"] == before + 3,
          "неизвестный префикс → понятная 404, в лог не пишется")
    check("/backup/v1" in client.get("/settings").text, "в настройках показан base URL источника")
    response = client.get(f"/_api/balance/calendar?upstream={cfg['sources'][1]['id']}")
    check(response.status_code == 200 and response.json()["upstream"] == cfg["sources"][1]["id"],
          "календарь баланса — по выбранному источнику")
    check('id="b-source"' in client.get("/balance").text, "на /balance есть выбор источника")

    print("источник без ключа")
    import httpx
    from app import proxy
    seen: dict = {}

    def upstream(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": []})

    real_client = proxy._client
    proxy._client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    try:
        keyed = config.load()["sources"][0]
        config.save({"sources": [
            {**keyed, "api_key": "sk-keyed"},
            {"name": "Без ключа", "prefix": "nokey", "base_url": "https://nokey.invalid/api", "api_key": ""},
        ], "active_source": keyed["id"]})
        response = client.get("/nokey/v1/models", headers={"Authorization": "Bearer client-key"})
        check(response.status_code == 200 and seen["auth"] is None,
              "без ключа запрос проходит, а не падает с 503; авторизация в апстрим не уходит")
        client.get("/v1/models", headers={"Authorization": "Bearer client-key"})
        check(seen["auth"] == "Bearer sk-keyed", "с ключом подставляется ключ источника")
    finally:
        proxy._client = real_client

    print("фактический адрес старого запуска")
    from app import main as main_mod
    saved_argv = sys.argv
    stored = {k: v for k, v in json.loads(config.CONFIG_PATH.read_text("utf-8")).items() if k not in ("host", "port")}
    config.CONFIG_PATH.write_text(json.dumps(stored), "utf-8")
    config._cache = None
    sys.argv = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
    try:
        main_mod._remember_listen_address()
    finally:
        sys.argv = saved_argv
    cfg = config.load()
    check(cfg["host"] == "0.0.0.0" and cfg["port"] == 8787,
          "адрес из аргументов uvicorn записан в настройки, если его там не было")
    config.save({"host": "127.0.0.1"})
    sys.argv = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
    try:
        main_mod._remember_listen_address()
    finally:
        sys.argv = saved_argv
    check(config.load()["host"] == "127.0.0.1", "сохранённый адрес не перезаписывается")

    print("оформление: название и логотип")
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
    response = client.post("/settings", data={"brand_name": "Мой  прокси", "brand_mark": "M P"},
                           files={"logo": ("logo.bin", png, "application/octet-stream")},
                           follow_redirects=False)
    cfg = config.load()
    check(response.status_code == 303 and cfg["brand_name"] == "Мой прокси" and cfg["brand_mark"] == "MP"
          and cfg["logo_file"] == "logo.png",
          "название, буквы и логотип сохранены; тип определён по содержимому, а не по имени")
    page = client.get("/models").text
    check("<title>Модели — Мой прокси</title>" in page and "/_brand/logo.png?v=" in page,
          "название в заголовке вкладки, логотип в шапке")
    response = client.get("/_brand/logo.png")
    check(response.status_code == 200 and response.headers["content-type"] == "image/png"
          and "sandbox" in response.headers.get("content-security-policy", ""),
          "логотип отдаётся с типом и запретом скриптов")
    check(client.get("/_brand/config.json").status_code == 404, "/_brand/ отдаёт только логотип")
    response = client.post("/settings", data={"brand_name": "Другое"},
                           files={"logo": ("evil.png", b"<html>not an image</html>", "image/png")},
                           follow_redirects=False)
    check("error=" in response.headers["location"] and config.load()["brand_name"] == "Другое"
          and config.load()["logo_file"] == "logo.png",
          "не картинка → ошибка, прежний логотип на месте, остальные поля сохранены")
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
    client.post("/settings", data={}, files={"logo": ("l.svg", svg, "image/svg+xml")})
    check(config.load()["logo_file"] == "logo.svg" and not (config.BRAND_DIR / "logo.png").exists(),
          "SVG принят, прежний PNG удалён")
    client.post("/settings", data={"logo_remove": "1", "brand_mark": "🤓"})
    check('class="brand-mark is-emoji"' in client.get("/models").text,
          "эмодзи в плашке получает класс is-emoji")
    client.post("/settings", data={"brand_mark": "M P"})
    check(config.load()["logo_file"] == "" and not list(config.BRAND_DIR.glob("logo.*"))
          and "brand-mark" in client.get("/models").text,
          "удаление логотипа возвращает плашку")

    print("медиа")
    check(client.get("/_media/../config.json").status_code == 404
          and client.get("/_media/not-a-hash.png").status_code == 404,
          "/_media/ отдаёт только файлы с именем-хэшем")
    name = "0123456789abcdef0123456789abcdef.png"
    config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (config.MEDIA_DIR / name).write_bytes(b"\x89PNG test")
    response = client.get(f"/_media/{name}")
    check(response.status_code == 200 and response.headers["content-type"] == "image/png"
          and "immutable" in response.headers.get("cache-control", ""),
          "сохранённый файл отдаётся с типом и вечным кэшем")

print()
if failures:
    print(f"ПРОВАЛЕНО {len(failures)} из {checks}:")
    for label in failures:
        print(f"  — {label}")
    sys.exit(1)
print(f"Все проверки пройдены: {checks}")
