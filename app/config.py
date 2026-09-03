"""Конфигурация прокси: хранится в data/config.json, редактируется через /settings."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AI_PROXY_DATA_DIR") or (BASE_DIR / "data"))
CONFIG_PATH = DATA_DIR / "config.json"
DB_PATH = DATA_DIR / "proxy.duckdb"

DEFAULTS: dict[str, Any] = {
    # Ключ от ИИ-API (провайдер-агностично)
    "api_key": "",
    # Базовый URL ИИ-API; пути документации добавляются как /v1/...
    "base_url": "https://speshu.ai/api",
    # Сколько дней хранить лог запросов; 0 — хранить всё
    "retention_days": 0,
    # Порог баланса, ниже которого в текстовые ответы добавляется предупреждение; 0 — выключено
    "balance_threshold": 0.0,
    # Домен, который подставляется в /docs вместо speshu.ai
    "docs_domain": "localhost",
    # Как часто опрашивать баланс апстрима, секунд
    "balance_poll_seconds": 300,
}

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        if isinstance(value, str) and not isinstance(default, str):
            # в формах десятичный разделитель может быть запятой
            value = value.strip().replace(",", ".")
        try:
            if isinstance(default, bool):
                cfg[key] = bool(value)
            elif isinstance(default, int) and not isinstance(default, bool):
                cfg[key] = int(float(value))
            elif isinstance(default, float):
                cfg[key] = float(value)
            else:
                cfg[key] = str(value).strip()
        except (TypeError, ValueError):
            cfg[key] = default
    cfg["base_url"] = cfg["base_url"].rstrip("/")
    cfg["retention_days"] = max(0, cfg["retention_days"])
    cfg["balance_threshold"] = max(0.0, cfg["balance_threshold"])
    cfg["balance_poll_seconds"] = max(30, cfg["balance_poll_seconds"])
    cfg["docs_domain"] = cfg["docs_domain"] or DEFAULTS["docs_domain"]
    return cfg


def load() -> dict[str, Any]:
    """Текущая конфигурация (кэшируется в памяти)."""
    global _cache
    with _lock:
        if _cache is None:
            raw: dict[str, Any] = {}
            if CONFIG_PATH.exists():
                try:
                    raw = json.loads(CONFIG_PATH.read_text("utf-8"))
                except (OSError, json.JSONDecodeError):
                    raw = {}
            for key, env in (
                ("api_key", "AI_PROXY_API_KEY"),
                ("base_url", "AI_PROXY_BASE_URL"),
            ):
                if not raw.get(key) and os.environ.get(env):
                    raw[key] = os.environ[env]
            _cache = _coerce(raw)
        return dict(_cache)


def save(values: dict[str, Any]) -> dict[str, Any]:
    """Сохранить конфигурацию (частичное обновление)."""
    global _cache
    with _lock:
        current = dict(_cache) if _cache is not None else {}
        merged = {**DEFAULTS, **current, **values}
        cfg = _coerce(merged)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(CONFIG_PATH)
        _cache = cfg
        return dict(cfg)


def is_configured() -> bool:
    cfg = load()
    return bool(cfg["api_key"] and cfg["base_url"])


def masked_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 12:
        return api_key[:3] + "…"
    return f"{api_key[:7]}…{api_key[-4:]}"
