"""Слой хранения: DuckDB с логом запросов, снимками баланса и кэшем цен моделей."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import duckdb

from . import config, inspect, media

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

-- источник (апстрим), через который прошёл запрос; см. config.sources
ALTER TABLE requests ADD COLUMN IF NOT EXISTS upstream VARCHAR;
ALTER TABLE balance_snapshots ADD COLUMN IF NOT EXISTS upstream VARCHAR;
-- обе оценки стоимости хранятся отдельно, а cost — выбранная по config.cost_mode:
-- так смена режима пересчитывает историю одним UPDATE, без повторного разбора тел
ALTER TABLE requests ADD COLUMN IF NOT EXISTS cost_api DOUBLE;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS cost_estimated DOUBLE;
-- медиа в ответе и признак, что тела уже просмотрены на предмет медиа
ALTER TABLE requests ADD COLUMN IF NOT EXISTS media_out INTEGER;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS media_scanned BOOLEAN DEFAULT FALSE;

-- прайс по источникам: у разных апстримов одна модель стоит по-разному.
-- model_pricing (ключ — только модель) остаётся ради миграции старых баз
CREATE TABLE IF NOT EXISTS model_prices (
    upstream        VARCHAR NOT NULL,
    model           VARCHAR NOT NULL,
    cost_context    DOUBLE,
    cost_completion DOUBLE,
    currency        VARCHAR,
    updated_at      TIMESTAMP,
    PRIMARY KEY (upstream, model)
);

-- галерея: одна строка на уникальную картинку/видео (файл или URL) и направление
CREATE TABLE IF NOT EXISTS media (
    key             VARCHAR PRIMARY KEY,
    direction       VARCHAR,       -- input | output
    kind            VARCHAR,       -- image | video | audio
    file            VARCHAR,       -- имя файла в data/media или NULL
    url             VARCHAR,       -- внешняя ссылка или NULL
    mime            VARCHAR,
    bytes           BIGINT,
    model           VARCHAR,
    upstream        VARCHAR,
    prompt          VARCHAR,
    request_id      BIGINT,        -- где встретилась впервые
    ts              TIMESTAMP,
    day             DATE,
    last_request_id BIGINT,        -- где встретилась последний раз (для ретеншена)
    last_ts         TIMESTAMP,
    last_day        DATE,
    uses            INTEGER DEFAULT 1
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
    """Записать проксированный запрос, вернуть его id.

    `entry["media"]` — найденные в телах медиа (media.Collector.items); пишутся
    в галерею с привязкой к id запроса.
    """
    ts = entry.get("ts") or datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
    request_body = _truncate(entry.get("request_body"))
    response_body = _truncate(entry.get("response_body"))
    details = inspect.compact(request_body, response_body)
    items = entry.get("media") or []
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
        entry.get("upstream"),
        entry.get("cost_api"),
        entry.get("cost_estimated"),
        details["media_out"],
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
                tools_called, images, finish_reason, reasoning_tokens, cached_tokens, inspected,
                upstream, cost_api, cost_estimated, media_out, media_scanned
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            params,
        )
        request_id = conn.execute("SELECT currval('seq_request_id')").fetchone()[0]
        _record_media(conn, items, request_id, ts, entry.get("model"), entry.get("upstream"),
                      details["prompt_preview"])
        return request_id


def _record_media(
    conn: duckdb.DuckDBPyConnection,
    items: list[dict[str, Any]],
    request_id: int,
    ts: datetime,
    model: str | None,
    upstream: str | None,
    fallback_prompt: str | None,
    prompt: str | None = None,
) -> None:
    """Добавить медиа в галерею; повторная встреча только сдвигает last_* и счётчик."""
    for item in items:
        caption = item.get("prompt") or prompt or fallback_prompt
        conn.execute(
            """
            INSERT INTO media (key, direction, kind, file, url, mime, bytes, model, upstream, prompt,
                               request_id, ts, day, last_request_id, last_ts, last_day, uses)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            ON CONFLICT (key) DO UPDATE SET
                last_request_id = excluded.last_request_id,
                last_ts = excluded.last_ts,
                last_day = excluded.last_day,
                uses = media.uses + 1
            """,
            [
                item["key"], item["direction"], item["kind"], item["file"], item["url"],
                item["mime"], item["bytes"], model, upstream,
                (caption or "")[:400] or None,
                request_id, ts, ts.date(), request_id, ts, ts.date(),
            ],
        )


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


def backfill_media(limit: int = 5000) -> int:
    """Найти медиа в записях, сделанных до появления галереи.

    Тела старых записей не переписываются: картинка из обрезанного тела всё равно
    потеряна, а целые data:-ссылки карточка запроса покажет и так.
    """
    rows = query(
        "SELECT id, ts, model, upstream, request_body, response_body FROM requests "
        "WHERE media_scanned IS NOT TRUE ORDER BY id LIMIT ?",
        [limit],
    )
    for row in rows:
        _, inputs = media.extract_request(inspect.parse(row["request_body"]))
        _, outputs = media.extract_response(inspect.parse(row["response_body"]))
        details = inspect.compact(row["request_body"], row["response_body"])
        with _lock:
            conn = connect()
            _record_media(conn, inputs.items, row["id"], row["ts"], row["model"], row["upstream"],
                          details["prompt_preview"], inputs.prompt)
            _record_media(conn, outputs.items, row["id"], row["ts"], row["model"], row["upstream"],
                          details["prompt_preview"], outputs.prompt)
            conn.execute(
                "UPDATE requests SET images = ?, media_out = ?, media_scanned = TRUE WHERE id = ?",
                [details["images"], details["media_out"], row["id"]],
            )
    return len(rows)


def migrate(source_id: str) -> None:
    """Привести записи старых версий к текущей схеме.

    Всё идемпотентно: каждое условие отбирает только ещё не мигрированные строки.
    """
    with _lock:
        conn = connect()
        if source_id:
            # до появления источников всё шло через единственный апстрим
            conn.execute("UPDATE requests SET upstream = ? WHERE upstream IS NULL", [source_id])
            conn.execute("UPDATE balance_snapshots SET upstream = ? WHERE upstream IS NULL", [source_id])
            conn.execute(
                """
                INSERT INTO model_prices (upstream, model, cost_context, cost_completion, currency, updated_at)
                SELECT ?, model, cost_context, cost_completion, currency, updated_at FROM model_pricing
                ON CONFLICT DO NOTHING
                """,
                [source_id],
            )
            conn.execute("DELETE FROM model_pricing")
        conn.execute(
            "UPDATE requests SET cost_api = cost WHERE cost_source = 'api' AND cost_api IS NULL"
        )
        conn.execute(
            "UPDATE requests SET cost_estimated = cost "
            "WHERE cost_source = 'estimated' AND cost_estimated IS NULL"
        )
    fill_estimates()


def fill_estimates() -> None:
    """Оценка по прайсу для записей, где её ещё нет, а токены и цены есть."""
    execute(
        """
        UPDATE requests SET cost_estimated =
            (coalesce(requests.prompt_tokens, 0) * coalesce(p.cost_context, 0)
             + coalesce(requests.completion_tokens, 0) * coalesce(p.cost_completion, 0)) / 1000000
        FROM model_prices p
        WHERE p.model = requests.model AND p.upstream = requests.upstream
          AND requests.cost_estimated IS NULL
          AND (coalesce(requests.prompt_tokens, 0) > 0 OR coalesce(requests.completion_tokens, 0) > 0)
          AND (p.cost_context IS NOT NULL OR p.cost_completion IS NOT NULL)
        """
    )


_COST_SQL = {
    "auto": (
        "coalesce(cost_api, cost_estimated)",
        "CASE WHEN cost_api IS NOT NULL THEN 'api' WHEN cost_estimated IS NOT NULL THEN 'estimated' END",
    ),
    "api": ("cost_api", "CASE WHEN cost_api IS NOT NULL THEN 'api' END"),
    "pricelist": (
        "coalesce(cost_estimated, cost_api)",
        "CASE WHEN cost_estimated IS NOT NULL THEN 'estimated' WHEN cost_api IS NOT NULL THEN 'api' END",
    ),
}


def recompute_costs(mode: str) -> None:
    """Пересчитать выбранную стоимость всех записей под режим config.cost_mode."""
    cost, source = _COST_SQL.get(mode, _COST_SQL["auto"])
    execute(
        f"UPDATE requests SET cost = {cost}, cost_source = {source} "
        f"WHERE cost IS DISTINCT FROM {cost} OR cost_source IS DISTINCT FROM {source}"
    )


def record_balance(amount: float, source: str = "poll", upstream: str | None = None) -> None:
    ts = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
    execute(
        "INSERT INTO balance_snapshots (ts, day, amount, source, upstream) VALUES (?,?,?,?,?)",
        [ts, ts.date(), float(amount), source, upstream],
    )


def latest_balance(upstream: str | None = None) -> dict[str, Any] | None:
    rows = query(
        "SELECT ts, amount, source FROM balance_snapshots "
        "WHERE ? IS NULL OR upstream = ? ORDER BY ts DESC LIMIT 1",
        [upstream, upstream],
    )
    return rows[0] if rows else None


def upsert_model_pricing(models: list[dict[str, Any]], upstream: str = "") -> int:
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
            conn.execute(
                "INSERT OR REPLACE INTO model_prices"
                " (upstream, model, cost_context, cost_completion, currency, updated_at)"
                " VALUES (?,?,?,?,?,?)",
                [upstream, *row],
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


def model_pricing(model: str, upstream: str = "") -> dict[str, Any] | None:
    rows = query(
        "SELECT model, cost_context, cost_completion, currency FROM model_prices"
        " WHERE model = ? AND upstream = ?",
        [model, upstream],
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
        # медиа живёт, пока его упоминает хоть один оставшийся запрос: last_day — последнее упоминание
        stale = [r[0] for r in conn.execute(
            "SELECT DISTINCT file FROM media WHERE last_day < ? AND file IS NOT NULL", [cutoff]
        ).fetchall()]
        conn.execute("DELETE FROM media WHERE last_day < ?", [cutoff])
        # один файл может быть и входом, и результатом — удаляем, только если ссылок не осталось
        kept = {r[0] for r in conn.execute(
            "SELECT DISTINCT file FROM media WHERE file IS NOT NULL"
        ).fetchall()}
        after = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
    for name in stale:
        path = media.path_of(name)
        if name not in kept and path is not None:
            path.unlink(missing_ok=True)
    return int(before - after)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
