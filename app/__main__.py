"""Запуск прокси: python -m app [--host H] [--port P] [--reload]

Адрес и порт берутся из data/config.json (их меняют на /settings); аргументы
и переменные AI_PROXY_HOST / AI_PROXY_PORT имеют приоритет. Сервис запускается
именно так, а не через `uvicorn --port …`: тогда смена порта в интерфейсе
применяется простым перезапуском, без переустановки описания сервиса.
"""
from __future__ import annotations

import argparse
import os

import uvicorn

from . import config


def main() -> None:
    cfg = config.load()
    parser = argparse.ArgumentParser(prog="python -m app", description="AI Monitoring Proxy")
    parser.add_argument("--host", default=os.environ.get("AI_PROXY_HOST") or cfg["host"])
    parser.add_argument("--port", type=int, default=int(os.environ.get("AI_PROXY_PORT") or cfg["port"]))
    parser.add_argument("--reload", action="store_true", help="перезапуск при правке кода (разработка)")
    args = parser.parse_args()

    # страница настроек сравнивает фактический адрес с сохранённым
    os.environ["AI_PROXY_LISTEN"] = f"{args.host}:{args.port}"
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
