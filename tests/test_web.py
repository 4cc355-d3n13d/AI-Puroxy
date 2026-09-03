"""Смоук-тест HTTP-слоя: каждая страница должна отрендериться, каждый /_api/* — ответить.

Ловит поломки шаблонов и несовместимость с новыми версиями FastAPI/Starlette —
именно такую, как удалённая из Starlette старая сигнатура TemplateResponse.

Запуск: ./.venv/bin/python tests/test_web.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AI_PROXY_DATA_DIR"] = tempfile.mkdtemp(prefix="ai-proxy-web-test-")

from fastapi.testclient import TestClient  # noqa: E402

from app import docsrc  # noqa: E402
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

    for path in ("/monitor", "/balance", "/models", "/settings"):
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

print()
if failures:
    print(f"ПРОВАЛЕНО {len(failures)} из {checks}:")
    for label in failures:
        print(f"  — {label}")
    sys.exit(1)
print(f"Все проверки пройдены: {checks}")
