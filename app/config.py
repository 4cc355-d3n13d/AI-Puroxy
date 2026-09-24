"""Конфигурация прокси: хранится в data/config.json, редактируется через /settings.

Апстримов может быть несколько (`sources`), запросы идут в активный (`active_source`).
Поля `api_key`, `base_url` и `source` в загруженной конфигурации — производные
от активного источника: так остальной код не знает о списке и берёт их как раньше.

Из командной строки (им пользуются run.sh и service.sh):
    python -m app.config get port
    python -m app.config set host=0.0.0.0 port=8787
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AI_PROXY_DATA_DIR") or (BASE_DIR / "data"))
CONFIG_PATH = DATA_DIR / "config.json"
DB_PATH = DATA_DIR / "proxy.duckdb"
MEDIA_DIR = DATA_DIR / "media"
BRAND_DIR = DATA_DIR / "brand"

DEFAULT_BASE_URL = "https://speshu.ai/api"

# режимы расчёта стоимости запроса
COST_MODES = {
    "auto": "API, иначе по прайсу",
    "api": "только из ответа API",
    "pricelist": "по прайсу, иначе API",
}

DEFAULTS: dict[str, Any] = {
    # Апстримы ИИ-API: [{"id", "name", "base_url", "api_key"}]
    "sources": [],
    # id источника, в который идут запросы
    "active_source": "",
    # Адрес и порт, на которых слушает прокси; применяются при перезапуске
    "host": "127.0.0.1",
    "port": 8787,
    # Как считать стоимость: см. COST_MODES
    "cost_mode": "auto",
    # Сколько дней хранить лог запросов; 0 — хранить всё
    "retention_days": 0,
    # Порог баланса, ниже которого в текстовые ответы добавляется предупреждение; 0 — выключено
    "balance_threshold": 0.0,
    # Домен, который подставляется в /docs вместо speshu.ai
    "docs_domain": "localhost",
    # Как часто опрашивать баланс апстрима, секунд
    "balance_poll_seconds": 300,
    # Оформление: название в шапке и заголовке вкладки, буквы в плашке без логотипа
    "brand_name": "Monitoring Proxy",
    "brand_mark": "AI",
    # Имя загруженного логотипа в data/brand/ (logo.png и т.п.); пусто — плашка с буквами
    "logo_file": "",
}

# производные поля — в файл не пишутся
_DERIVED = ("api_key", "base_url", "source")

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "source"


def source_name(base_url: str) -> str:
    """Имя источника по умолчанию — хост из base_url."""
    return urlparse(base_url).hostname or base_url or "источник"


def _coerce_sources(raw: Any) -> tuple[list[dict[str, str]], str]:
    """Список источников и id отмеченного флагом `active` (так его передаёт форма:
    id нового источника до приведения ещё неизвестен)."""
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    flagged = ""
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        base_url = str(item.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            continue
        name = str(item.get("name") or "").strip() or source_name(base_url)
        # id — ключ истории в базе: строится по хосту (имя бывает кириллицей и меняется),
        # а совпадения разводятся суффиксом, а не выкидываются
        source_id = slugify(str(item.get("id") or source_name(base_url)))
        base_id, n = source_id, 2
        while source_id in seen:
            source_id, n = f"{base_id}-{n}", n + 1
        seen.add(source_id)
        sources.append({
            "id": source_id,
            "name": name,
            "base_url": base_url,
            "api_key": str(item.get("api_key") or "").strip(),
        })
        if item.get("active"):
            flagged = source_id
    return sources, flagged


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    raw = dict(raw)
    # до появления списка источников ключ и URL лежали в корне — переносим их в первый источник
    if not raw.get("sources") and (raw.get("api_key") or raw.get("base_url")):
        base_url = str(raw.get("base_url") or DEFAULT_BASE_URL)
        raw["sources"] = [{"name": source_name(base_url), "base_url": base_url, "api_key": raw.get("api_key") or ""}]

    cfg = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        if key not in raw or raw[key] is None or key == "sources":
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
    cfg["sources"], flagged = _coerce_sources(raw.get("sources"))
    cfg["active_source"] = flagged or cfg["active_source"]
    cfg["retention_days"] = max(0, cfg["retention_days"])
    cfg["balance_threshold"] = max(0.0, cfg["balance_threshold"])
    cfg["balance_poll_seconds"] = max(30, cfg["balance_poll_seconds"])
    cfg["docs_domain"] = cfg["docs_domain"] or DEFAULTS["docs_domain"]
    cfg["host"] = cfg["host"] or DEFAULTS["host"]
    cfg["brand_name"] = " ".join(cfg["brand_name"].split())[:60] or DEFAULTS["brand_name"]
    cfg["brand_mark"] = "".join(cfg["brand_mark"].split())[:3]
    if not re.fullmatch(r"logo\.(png|jpg|webp|gif|svg)", cfg["logo_file"]):
        cfg["logo_file"] = ""
    if not 1 <= cfg["port"] <= 65535:
        cfg["port"] = DEFAULTS["port"]
    if cfg["cost_mode"] not in COST_MODES:
        cfg["cost_mode"] = DEFAULTS["cost_mode"]

    ids = [source["id"] for source in cfg["sources"]]
    if cfg["active_source"] not in ids:
        cfg["active_source"] = ids[0] if ids else ""
    active = find_source(cfg, cfg["active_source"]) or {}
    cfg["source"] = cfg["active_source"]
    cfg["api_key"] = active.get("api_key", "")
    cfg["base_url"] = active.get("base_url", "")
    return cfg


def find_source(cfg: dict[str, Any], source_id: str) -> dict[str, str] | None:
    return next((s for s in cfg["sources"] if s["id"] == source_id), None)


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
            if not raw.get("sources"):
                for key, env in (
                    ("api_key", "AI_PROXY_API_KEY"),
                    ("base_url", "AI_PROXY_BASE_URL"),
                ):
                    if not raw.get(key) and os.environ.get(env):
                        raw[key] = os.environ[env]
            _cache = _coerce(raw)
        return _copy(_cache)


def _copy(cfg: dict[str, Any]) -> dict[str, Any]:
    result = dict(cfg)
    result["sources"] = [dict(source) for source in cfg["sources"]]
    return result


def save(values: dict[str, Any]) -> dict[str, Any]:
    """Сохранить конфигурацию (частичное обновление).

    `api_key` / `base_url` без `sources` меняют активный источник — так работали
    прежние версии формы и так проще задавать ключ из тестов и скриптов.
    """
    global _cache
    current = load()
    with _lock:
        merged = {k: v for k, v in {**current, **values}.items() if k not in _DERIVED}
        if "sources" not in values and ("api_key" in values or "base_url" in values):
            sources = [dict(s) for s in current["sources"]]
            active = next((s for s in sources if s["id"] == current["active_source"]), None)
            if active is None:
                base_url = str(values.get("base_url") or DEFAULT_BASE_URL)
                active = {"name": source_name(base_url), "base_url": base_url, "api_key": ""}
                sources.append(active)
            if values.get("api_key") is not None:
                active["api_key"] = values["api_key"]
            if values.get("base_url"):
                active["base_url"] = values["base_url"]
            merged["sources"] = sources
        cfg = _coerce(merged)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        stored = {k: v for k, v in cfg.items() if k not in _DERIVED}
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(stored, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(CONFIG_PATH)
        _cache = cfg
        return _copy(cfg)


def stored_keys() -> set[str]:
    """Ключи, реально записанные в config.json (а не подставленные по умолчанию)."""
    try:
        return set(json.loads(CONFIG_PATH.read_text("utf-8")))
    except (OSError, ValueError, TypeError):
        return set()


def is_configured() -> bool:
    cfg = load()
    return bool(cfg["api_key"] and cfg["base_url"])


def masked_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 12:
        return api_key[:3] + "…"
    return f"{api_key[:7]}…{api_key[-4:]}"


def _cli(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "get":
        value = load().get(argv[1])
        if value is None:
            return 1
        print(value)
        return 0
    if len(argv) >= 2 and argv[0] == "set":
        pairs = dict(arg.split("=", 1) for arg in argv[1:] if "=" in arg)
        save({k: v for k, v in pairs.items() if k in ("host", "port")})
        return 0
    print("использование: python -m app.config get <ключ> | set host=… port=…", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
