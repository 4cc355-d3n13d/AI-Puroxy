"""Извлечение токенов/стоимости из ответов ИИ-API и оценка цены по прайсу моделей.

Форматы отличаются между документацией и живым API, поэтому проверяем все известные:
  * usage.cost.total_cost        — chat/completions (актуальный ответ API)
  * usage.cost_rub / usage.cost  — chat/completions (документация)
  * usage.input_tokens/…         — /v1/messages (стоимость не возвращается → считаем по прайсу)
"""
from __future__ import annotations

import json
from typing import Any

from . import db


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _int(value: Any) -> int | None:
    number = _num(value)
    return int(number) if number is not None else None


def extract_cost(usage: dict[str, Any]) -> float | None:
    """Стоимость запроса в рублях, если API её вернул."""
    cost = usage.get("cost")
    if isinstance(cost, dict):
        for key in ("total_cost", "total", "cost_rub", "amount", "rub"):
            value = _num(cost.get(key))
            if value is not None:
                return value
    for key in ("cost_rub", "cost", "total_cost", "total_cost_rub"):
        value = _num(usage.get(key))
        if value is not None:
            return value
    return None


def extract_usage(payload: Any) -> dict[str, Any]:
    """Токены и стоимость из тела ответа (chat/completions или messages)."""
    result: dict[str, Any] = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "cost": None,
        "cost_source": None,
    }
    if not isinstance(payload, dict):
        return result

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("usage"), dict):
            usage = data["usage"]
        else:
            return result

    prompt = _int(usage.get("prompt_tokens"))
    if prompt is None:
        prompt = _int(usage.get("input_tokens"))
        cached = _int(usage.get("cache_read_input_tokens")) or 0
        created = _int(usage.get("cache_creation_input_tokens")) or 0
        if prompt is not None:
            prompt += cached + created

    completion = _int(usage.get("completion_tokens"))
    if completion is None:
        completion = _int(usage.get("output_tokens"))

    total = _int(usage.get("total_tokens"))
    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)

    result["prompt_tokens"] = prompt
    result["completion_tokens"] = completion
    result["total_tokens"] = total

    cost = extract_cost(usage)
    if cost is not None:
        result["cost"] = cost
        result["cost_source"] = "api"
    return result


def estimate_cost(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    upstream: str = "",
) -> float | None:
    """Оценка стоимости по кэшу цен источника (цены указаны за 1M токенов)."""
    if not model or (not prompt_tokens and not completion_tokens):
        return None
    pricing = db.model_pricing(model, upstream)
    if not pricing:
        return None
    context_price = pricing.get("cost_context")
    completion_price = pricing.get("cost_completion")
    if context_price is None and completion_price is None:
        return None
    total = 0.0
    if prompt_tokens and context_price:
        total += prompt_tokens * float(context_price) / 1_000_000
    if completion_tokens and completion_price:
        total += completion_tokens * float(completion_price) / 1_000_000
    return total


def fill_cost(entry: dict[str, Any], mode: str = "auto") -> None:
    """Проставить cost/cost_source в записи лога по режиму config.cost_mode.

    Обе суммы — из ответа API (`cost_api`) и по прайсу (`cost_estimated`) — сохраняются,
    чтобы при смене режима историю можно было пересчитать без разбора тел.
    """
    api_cost = entry.get("cost_api")
    if api_cost is None:
        api_cost = entry.get("cost")
    estimated = estimate_cost(
        entry.get("model"), entry.get("prompt_tokens"), entry.get("completion_tokens"),
        entry.get("upstream") or "",
    )
    entry["cost_api"] = api_cost
    entry["cost_estimated"] = estimated
    if mode == "api":
        order = (("api", api_cost),)
    elif mode == "pricelist":
        order = (("estimated", estimated), ("api", api_cost))
    else:
        order = (("api", api_cost), ("estimated", estimated))
    entry["cost"], entry["cost_source"] = next(
        ((value, source) for source, value in order if value is not None), (None, None)
    )


def parse_balance(payload: Any) -> float | None:
    """Баланс из ответа /v1/balance: {"RUB": "..."} (живой API) или {"amount": "..."} (документация)."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return None
    if isinstance(payload, (int, float)):
        return float(payload)
    if not isinstance(payload, dict):
        return None
    for key in ("amount", "RUB", "rub", "balance", "value"):
        value = _num(payload.get(key))
        if value is not None:
            return value
    data = payload.get("data")
    if isinstance(data, dict):
        return parse_balance(data)
    return None


def merge_stream_usage(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Итоговый usage из SSE-чанков: берём последний непустой."""
    merged: dict[str, Any] = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "cost": None,
        "cost_source": None,
    }
    for chunk in chunks:
        extracted = extract_usage(chunk)
        for key, value in extracted.items():
            if value is not None:
                merged[key] = value
    return merged
