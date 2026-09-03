"""Агрегаты для веб-интерфейса: лог, модели, баланс по дням."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from . import db, inspect

MAX_PAGE_SIZE = 200


def _where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if filters.get("model"):
        clauses.append("model = ?")
        params.append(filters["model"])
    if filters.get("endpoint"):
        clauses.append("endpoint = ?")
        params.append(filters["endpoint"])
    status = filters.get("status")
    if status == "ok":
        clauses.append("status_code < 400")
    elif status == "error":
        clauses.append("(status_code >= 400 OR status_code IS NULL OR error IS NOT NULL)")
    kind = filters.get("kind")
    if kind == "tools":
        clauses.append("tools_called IS NOT NULL")
    elif kind == "reasoning":
        clauses.append("coalesce(reasoning_tokens, 0) > 0 OR reasoning_preview IS NOT NULL")
    elif kind == "images":
        clauses.append("coalesce(images, 0) > 0")
    elif kind == "stream":
        clauses.append("stream IS TRUE")
    if filters.get("date_from"):
        clauses.append("day >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("day <= ?")
        params.append(filters["date_to"])
    if filters.get("q"):
        clauses.append(
            "(coalesce(request_body,'') ILIKE ? OR coalesce(response_body,'') ILIKE ?"
            " OR coalesce(model,'') ILIKE ? OR coalesce(path,'') ILIKE ?)"
        )
        needle = f"%{filters['q']}%"
        params.extend([needle] * 4)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def requests_page(filters: dict[str, Any], page: int = 1, page_size: int = 50) -> dict[str, Any]:
    page = max(1, int(page or 1))
    page_size = min(MAX_PAGE_SIZE, max(1, int(page_size or 50)))
    where, params = _where(filters)
    total = db.query(f"SELECT count(*) AS n FROM requests{where}", params)[0]["n"]
    rows = db.query(
        f"""
        SELECT id, ts, day, method, path, endpoint, model, stream, status_code, duration_ms,
               prompt_tokens, completion_tokens, total_tokens, cost, cost_source, error,
               prompt_preview, answer_preview, reasoning_preview, tools_offered, tools_called,
               images, finish_reason, reasoning_tokens, cached_tokens,
               length(coalesce(request_body,'')) AS request_size,
               length(coalesce(response_body,'')) AS response_size
        FROM requests{where}
        ORDER BY ts DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    )
    return {
        "items": rows,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }


def request_detail(request_id: int) -> dict[str, Any] | None:
    rows = db.query("SELECT * FROM requests WHERE id = ?", [request_id])
    if not rows:
        return None
    row = rows[0]
    # разбираем тела на лету: так карточка работает и для записей, сделанных
    # до появления полей разбора, и не раздувает базу вторым копированием текста
    row["summary"] = inspect.summarize(row.get("request_body"), row.get("response_body"))
    return row


def filter_options() -> dict[str, Any]:
    models = db.query(
        "SELECT model, count(*) AS n FROM requests WHERE model IS NOT NULL GROUP BY model ORDER BY n DESC"
    )
    endpoints = db.query(
        "SELECT endpoint, count(*) AS n FROM requests WHERE endpoint IS NOT NULL GROUP BY endpoint ORDER BY n DESC"
    )
    return {"models": models, "endpoints": endpoints}


def daily_model_counts(days: int = 30, model: str | None = None) -> dict[str, Any]:
    """Данные для графика: запросы по дням в разрезе моделей."""
    since = date.today() - timedelta(days=max(1, days) - 1)
    params: list[Any] = [since]
    model_clause = ""
    if model:
        model_clause = " AND model = ?"
        params.append(model)
    rows = db.query(
        f"""
        SELECT day, coalesce(model, '—') AS model, count(*) AS n, coalesce(sum(cost), 0) AS cost
        FROM requests
        WHERE day >= ?{model_clause}
        GROUP BY day, model
        ORDER BY day
        """,
        params,
    )
    totals: dict[str, int] = {}
    for row in rows:
        totals[row["model"]] = totals.get(row["model"], 0) + int(row["n"])
    top = [m for m, _ in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:8]]
    by_day: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["day"].isoformat()
        bucket = by_day.setdefault(key, {"day": key, "total": 0, "models": {}})
        name = row["model"] if row["model"] in top else "прочие"
        bucket["models"][name] = bucket["models"].get(name, 0) + int(row["n"])
        bucket["total"] += int(row["n"])
    series = []
    cursor = since
    today = date.today()
    while cursor <= today:
        key = cursor.isoformat()
        series.append(by_day.get(key, {"day": key, "total": 0, "models": {}}))
        cursor += timedelta(days=1)
    legend = top + (["прочие"] if len(totals) > len(top) else [])
    return {"series": series, "models": legend, "days": days}


def models_summary() -> list[dict[str, Any]]:
    return db.query(
        """
        SELECT coalesce(model, '—') AS model,
               count(*) AS requests,
               sum(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
               coalesce(sum(prompt_tokens), 0) AS prompt_tokens,
               coalesce(sum(completion_tokens), 0) AS completion_tokens,
               coalesce(sum(cost), 0) AS cost,
               avg(duration_ms) AS avg_duration_ms,
               max(ts) AS last_used,
               min(ts) AS first_used
        FROM requests
        GROUP BY model
        ORDER BY requests DESC, cost DESC
        """
    )


def month_bounds(month: str | None) -> tuple[date, date]:
    today = date.today()
    if month:
        try:
            year, mon = (int(part) for part in month.split("-")[:2])
            first = date(year, mon, 1)
        except (ValueError, TypeError):
            first = today.replace(day=1)
    else:
        first = today.replace(day=1)
    next_month = date(first.year + (first.month // 12), (first.month % 12) + 1, 1)
    return first, next_month - timedelta(days=1)


def balance_calendar(month: str | None = None) -> dict[str, Any]:
    """Календарь трат за месяц + баланс на конец каждого дня."""
    first, last = month_bounds(month)
    spend = db.query(
        """
        SELECT day, coalesce(sum(cost), 0) AS cost, count(*) AS requests
        FROM requests
        WHERE day BETWEEN ? AND ?
        GROUP BY day ORDER BY day
        """,
        [first, last],
    )
    snapshots = db.query(
        """
        SELECT day,
               min(amount) AS min_amount,
               max(amount) AS max_amount,
               arg_min(amount, ts) AS first_amount,
               arg_max(amount, ts) AS last_amount
        FROM balance_snapshots
        WHERE day BETWEEN ? AND ?
        GROUP BY day ORDER BY day
        """,
        [first, last],
    )
    snap_by_day = {row["day"].isoformat(): row for row in snapshots}
    days = []
    cursor = first
    spend_by_day = {row["day"].isoformat(): row for row in spend}
    while cursor <= last:
        key = cursor.isoformat()
        row = spend_by_day.get(key)
        snap = snap_by_day.get(key)
        days.append(
            {
                "day": key,
                "cost": float(row["cost"]) if row else 0.0,
                "requests": int(row["requests"]) if row else 0,
                "balance_end": float(snap["last_amount"]) if snap else None,
                "balance_start": float(snap["first_amount"]) if snap else None,
            }
        )
        cursor += timedelta(days=1)
    total_cost = sum(day["cost"] for day in days)
    return {
        "month": first.strftime("%Y-%m"),
        "first_day": first.isoformat(),
        "last_day": last.isoformat(),
        "weekday_offset": first.weekday(),
        "days": days,
        "total_cost": total_cost,
        "total_requests": sum(day["requests"] for day in days),
        "prev_month": (first - timedelta(days=1)).strftime("%Y-%m"),
        "next_month": (last + timedelta(days=1)).strftime("%Y-%m"),
    }


def day_breakdown(day: str) -> dict[str, Any]:
    """Детализация трат за день по моделям."""
    rows = db.query(
        """
        SELECT coalesce(model, '—') AS model,
               count(*) AS requests,
               coalesce(sum(cost), 0) AS cost,
               coalesce(sum(prompt_tokens), 0) AS prompt_tokens,
               coalesce(sum(completion_tokens), 0) AS completion_tokens,
               sum(CASE WHEN cost_source = 'estimated' THEN 1 ELSE 0 END) AS estimated
        FROM requests
        WHERE day = ?
        GROUP BY model
        ORDER BY cost DESC, requests DESC
        """,
        [day],
    )
    endpoints = db.query(
        """
        SELECT endpoint, count(*) AS requests, coalesce(sum(cost), 0) AS cost
        FROM requests WHERE day = ? GROUP BY endpoint ORDER BY requests DESC
        """,
        [day],
    )
    # фактическое изменение баланса за день — учитывает и то, что API не тарифицирует в ответе
    snapshot = db.query(
        """
        SELECT arg_min(amount, ts) AS first_amount, arg_max(amount, ts) AS last_amount, count(*) AS n
        FROM balance_snapshots WHERE day = ?
        """,
        [day],
    )[0]
    balance_delta = None
    if snapshot["n"] and snapshot["n"] > 1:
        balance_delta = float(snapshot["first_amount"]) - float(snapshot["last_amount"])
    return {
        "day": day,
        "models": rows,
        "endpoints": endpoints,
        "total_cost": sum(float(r["cost"]) for r in rows),
        "total_requests": sum(int(r["requests"]) for r in rows),
        "balance_delta": balance_delta,
        "balance_start": float(snapshot["first_amount"]) if snapshot["n"] else None,
        "balance_end": float(snapshot["last_amount"]) if snapshot["n"] else None,
    }


def overview() -> dict[str, Any]:
    row = db.query(
        """
        SELECT count(*) AS requests,
               coalesce(sum(cost), 0) AS cost,
               coalesce(sum(total_tokens), 0) AS tokens,
               sum(CASE WHEN status_code >= 400 OR error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
               count(DISTINCT model) AS models
        FROM requests
        """
    )[0]
    today = db.query(
        "SELECT count(*) AS requests, coalesce(sum(cost), 0) AS cost FROM requests WHERE day = ?",
        [date.today()],
    )[0]
    return {
        "requests": int(row["requests"]),
        "cost": float(row["cost"]),
        "tokens": int(row["tokens"]),
        "errors": int(row["errors"] or 0),
        "models": int(row["models"] or 0),
        "today_requests": int(today["requests"]),
        "today_cost": float(today["cost"]),
    }


def db_size_bytes() -> int:
    from . import config

    try:
        return config.DB_PATH.stat().st_size
    except OSError:
        return 0


def jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value
