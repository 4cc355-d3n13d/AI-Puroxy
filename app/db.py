"""Слой хранения: DuckDB с логом запросов, снимками баланса и кэшем цен моделей."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import duckdb

from . import config, inspect

_lock = threading.RLock()
_conn: duckdb.DuckDBPyConnection | None = None

SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS seq_request_id START 1;

CREATE TABLE IF NOT EXISTS requests (
    id            BIGINT PRIMARY KEY DEFAULT nextval('seq_request_id'),
    ts            TIMESTAMP NOT NULL,
    day           DATE NOT NULL,
    method        VARCHAR,
    path          VARCHAR,
    endpoint      VARCHAR,
    model         VARCHAR,
    stream        BOOLEAN DEFAULT FALSE,
    status_code   INTEGER,
    duration_ms   DOUBLE,
    client_ip     VARCHAR,
    upstream_id   VARCHAR,
    request_body  VARCHAR,
    response_body VARCHAR,
    error         VARCHAR,
    prompt_tokens BIGINT,
    completion_tokens BIGINT,
    total_tokens  BIGINT,
    cost          DOUBLE,
    cost_source   VARCHAR
);

CREATE TABLE IF NOT EXISTS balance_snapshots (
    ts     TIMESTAMP NOT NULL,
    day    DATE NOT NULL,
    amount DOUBLE NOT NULL,
    source VARCHAR
);

-- поля разбора тел (что спросили, что модель думала, какие инструменты дёрнула);
-- добавляются отдельно, чтобы существующие базы не пришлось пересоздавать
ALTER TABLE requests ADD COLUMN IF NOT EXISTS prompt_preview VARCHAR;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS answer_preview VARCHAR;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS reasoning_preview VARCHAR;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS tools_offered INTEGER;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS tools_called VARCHAR;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS images INTEGER;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS finish_reason VARCHAR;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS reasoning_tokens BIGINT;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS cached_tokens BIGINT;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS inspected BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS model_pricing (
    model           VARCHAR PRIMARY KEY,
    cost_context    DOUBLE,
    cost_completion DOUBLE,
    currency        VARCHAR,
    updated_at      TIMESTAMP
);
"""


class DatabaseBusyError(RuntimeError):
    """База уже занята другим процессом (DuckDB допускает одного писателя)."""


def _busy_message(error: Exception) -> str:
    """Понятное объяснение вместо трейсбека DuckDB."""
    holder = re.search(r"PID (\d+)", str(error))
    pid = holder.group(1) if holder else None
    lines = [
        "",
        "База данных уже открыта другим процессом ai-puroxy.",
        f"Файл: {config.DB_PATH}",
    ]
    if pid:
        lines.append(f"Держит процесс PID {pid}.")
    lines += [
        "",
        "DuckDB допускает только одного писателя, поэтому два экземпляра прокси",
        "одновременно работать не могут. Скорее всего прокси уже запущен сервисом",
        "и стартовал сам после перезагрузки.",
        "",
        "Что делать:",
        "  ./service.sh status     — посмотреть, запущен ли сервис (он мог подняться сам)",
        "  ./service.sh stop       — остановить сервис, если нужен ручной запуск",
        "  ./service.sh restart    — просто перезапустить сервис",
        "",
    ]
    return "\n".join(lines)


def connect() -> duckdb.DuckDBPyConnection:
    global _conn
    with _lock:
        if _conn is None:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            try:
                _conn = duckdb.connect(str(config.DB_PATH))
            except duckdb.IOException as error:
                if "lock" in str(error).lower():
                    raise DatabaseBusyError(_busy_message(error)) from None
                raise
            _conn.execute(SCHEMA)
        return _conn


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    """SELECT, результат — список словарей."""
    with _lock:
        cur = connect().execute(sql, list(params))
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with _lock:
        connect().execute(sql, list(params))


def _truncate(text: str | None, limit: int = 400_000) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [обрезано, всего {len(text)} символов]"


def log_request(entry: dict[str, Any]) -> int:
    """Записать проксированный запрос, вернуть его id."""
    ts = entry.get("ts") or datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
    request_body = _truncate(entry.get("request_body"))
    response_body = _truncate(entry.get("response_body"))
    details = inspect.compact(request_body, response_body)
    params = [
        ts,
        ts.date(),
        entry.get("method"),
        entry.get("path"),
        entry.get("endpoint"),
        entry.get("model"),
        bool(entry.get("stream")),
        entry.get("status_code"),
        entry.get("duration_ms"),
        entry.get("client_ip"),
        entry.get("upstream_id"),
        request_body,
        response_body,
        entry.get("error"),
        entry.get("prompt_tokens"),
        entry.get("completion_tokens"),
        entry.get("total_tokens"),
        entry.get("cost"),
        entry.get("cost_source"),
        details["prompt_preview"],
        details["answer_preview"],
        details["reasoning_preview"],
        details["tools_offered"],
        details["tools_called"],
        details["images"],
        details["finish_reason"],
        details["reasoning_tokens"],
        details["cached_tokens"],
        True,
    ]
    with _lock:
        conn = connect()
        conn.execute(
            """
            INSERT INTO requests (
                ts, day, method, path, endpoint, model, stream, status_code, duration_ms,
                client_ip, upstream_id, request_body, response_body, error,
                prompt_tokens, completion_tokens, total_tokens, cost, cost_source,
                prompt_preview, answer_preview, reasoning_preview, tools_offered,
                tools_called, images, finish_reason, reasoning_tokens, cached_tokens, inspected
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            params,
        )
        return conn.execute("SELECT currval('seq_request_id')").fetchone()[0]


def backfill_details(limit: int = 5000) -> int:
    """Разобрать тела у записей, сделанных до появления этих полей."""
    rows = query(
        "SELECT id, request_body, response_body FROM requests "
        "WHERE inspected IS NOT TRUE ORDER BY id DESC LIMIT ?",
        [limit],
    )
    if not rows:
        return 0
    with _lock:
        conn = connect()
        for row in rows:
            details = inspect.compact(row["request_body"], row["response_body"])
            conn.execute(
                """
                UPDATE requests SET prompt_preview = ?, answer_preview = ?, reasoning_preview = ?,
                    tools_offered = ?, tools_called = ?, images = ?, finish_reason = ?,
                    reasoning_tokens = ?, cached_tokens = ?, inspected = TRUE
                WHERE id = ?
                """,
                [
                    details["prompt_preview"], details["answer_preview"], details["reasoning_preview"],
                    details["tools_offered"], details["tools_called"], details["images"],
                    details["finish_reason"], details["reasoning_tokens"], details["cached_tokens"],
                    row["id"],
                ],
            )
    return len(rows)


def record_balance(amount: float, source: str = "poll") -> None:
    ts = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
    execute(
        "INSERT INTO balance_snapshots (ts, day, amount, source) VALUES (?,?,?,?)",
        [ts, ts.date(), float(amount), source],
    )


def latest_balance() -> dict[str, Any] | None:
    rows = query("SELECT ts, amount, source FROM balance_snapshots ORDER BY ts DESC LIMIT 1")
    return rows[0] if rows else None


def upsert_model_pricing(models: list[dict[str, Any]]) -> int:
    """Обновить кэш цен из ответа GET /v1/models (цены за 1M токенов)."""
    now = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
    rows = []
    for model in models:
        model_id = model.get("id")
        if not model_id:
            continue
        rows.append(
            [
                str(model_id),
                _as_float(model.get("cost_context") or _nested_price(model, "prompt")),
                _as_float(model.get("cost_completion") or _nested_price(model, "completion")),
                str(model.get("currency") or "RUB"),
                now,
            ]
        )
    if not rows:
        return 0
    with _lock:
        conn = connect()
        for row in rows:
            conn.execute("DELETE FROM model_pricing WHERE model = ?", [row[0]])
            conn.execute(
                "INSERT INTO model_pricing (model, cost_context, cost_completion, currency, updated_at)"
                " VALUES (?,?,?,?,?)",
                row,
            )
    return len(rows)


def _nested_price(model: dict[str, Any], key: str) -> Any:
    pricing = model.get("pricing")
    if isinstance(pricing, dict):
        return pricing.get(key)
    return None


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def model_pricing(model: str) -> dict[str, Any] | None:
    rows = query(
        "SELECT model, cost_context, cost_completion, currency FROM model_pricing WHERE model = ?",
        [model],
    )
    return rows[0] if rows else None


def apply_retention(retention_days: int) -> int:
    """Удалить записи старше retention_days. 0 — хранить всё."""
    if not retention_days or retention_days <= 0:
        return 0
    cutoff = (datetime.now() - timedelta(days=retention_days)).date()
    with _lock:
        conn = connect()
        before = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
        conn.execute("DELETE FROM requests WHERE day < ?", [cutoff])
        conn.execute("DELETE FROM balance_snapshots WHERE day < ?", [cutoff])
        after = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
    return int(before - after)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
