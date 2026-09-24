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

from app import config, docsrc  # noqa: E402
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

    check(client.get("/_api/requests/999999").status_code == 404,
          "/_api/requests/{id} на несуществующей записи → 404")

    print("прокси без настроек")
    response = client.get("/v1/models")
    check(response.status_code == 503 and response.json()["error"]["type"] == "proxy_not_configured",
          "/v1/* без ключа → понятная 503, а не падение")

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
