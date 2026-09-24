"""Проксирование запросов к ИИ-API: подстановка ключа, логирование, предупреждение о балансе."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import config, db, media, usage as usage_mod

# заголовки, которые не пробрасываем в апстрим / клиенту
_DROP_REQUEST_HEADERS = {
    "host", "authorization", "content-length", "connection", "accept-encoding",
    "transfer-encoding", "expect", "cookie", "x-api-key",
}
_DROP_RESPONSE_HEADERS = {
    "content-length", "content-encoding", "transfer-encoding", "connection",
    "keep-alive", "server", "date",
}

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

# кэш баланса, чтобы не дёргать апстрим на каждый запрос; относится к одному источнику
_balance_amount: float | None = None
_balance_checked_at: float = 0.0
_balance_source: str = ""
_balance_lock = asyncio.Lock()


async def get_client() -> httpx.AsyncClient:
    global _client
    async with _client_lock:
        if _client is None:
            _client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=900.0, write=120.0, pool=15.0),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=64, max_keepalive_connections=16),
            )
        return _client


async def shutdown() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone().replace(tzinfo=None)


def upstream_url(cfg: dict[str, Any], subpath: str) -> str:
    return f"{cfg['base_url'].rstrip('/')}/{subpath.lstrip('/')}"


# --------------------------------------------------------------------------- баланс


async def fetch_balance(force: bool = False) -> float | None:
    """Баланс апстрима с кэшем; при force — обязательный запрос к API."""
    global _balance_amount, _balance_checked_at, _balance_source
    cfg = config.load()
    if not cfg["api_key"]:
        return None
    async with _balance_lock:
        if _balance_source != cfg["source"]:
            # источник переключили — баланс прежнего к новому отношения не имеет
            _balance_amount, _balance_checked_at, _balance_source = None, 0.0, cfg["source"]
        fresh = (time.monotonic() - _balance_checked_at) < cfg["balance_poll_seconds"]
        if not force and fresh and _balance_amount is not None:
            return _balance_amount
        try:
            client = await get_client()
            response = await client.get(
                upstream_url(cfg, "v1/balance"),
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Accept": "application/json"},
                timeout=30.0,
            )
            amount = usage_mod.parse_balance(response.text) if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            amount = None
        if amount is not None:
            _balance_amount = amount
            _balance_checked_at = time.monotonic()
            db.record_balance(amount, source="poll", upstream=cfg["source"])
        return _balance_amount


def observe_balance(amount: float, source: str = "proxy", upstream: str = "") -> None:
    """Зафиксировать баланс, увиденный при проксировании GET /v1/balance."""
    global _balance_amount, _balance_checked_at, _balance_source
    _balance_amount = amount
    _balance_checked_at = time.monotonic()
    _balance_source = upstream
    db.record_balance(amount, source=source, upstream=upstream)


def cached_balance() -> float | None:
    """Баланс активного источника, если он известен."""
    return _balance_amount if _balance_source == config.load()["source"] else None


def _apply_local_cost(cost: float | None) -> None:
    """Уменьшить кэш баланса на стоимость запроса, чтобы предупреждение было актуальным."""
    global _balance_amount
    if cost and cached_balance() is not None:
        _balance_amount = max(0.0, _balance_amount - cost)


def balance_warning(cfg: dict[str, Any]) -> str | None:
    """Текст предупреждения, если баланс ниже порога."""
    threshold = cfg["balance_threshold"]
    if not threshold or threshold <= 0:
        return None
    amount = cached_balance()
    if amount is None or amount >= threshold:
        return None
    return (
        f"⚠️ Низкий баланс ИИ-API: {amount:.2f} ₽ (порог {threshold:.2f} ₽). "
        f"Пополните счёт, чтобы запросы не начали отклоняться.\n\n"
    )


# --------------------------------------------------------------------------- вставка предупреждения


def _inject_into_payload(payload: Any, warning: str, endpoint: str) -> bool:
    """Дописать предупреждение в начало текстового ответа. True — если что-то изменили."""
    if not isinstance(payload, dict):
        return False
    changed = False
    if endpoint.endswith("chat/completions"):
        for choice in payload.get("choices") or []:
            message = choice.get("message") if isinstance(choice, dict) else None
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                message["content"] = warning + message["content"]
                changed = True
            elif isinstance(message, dict) and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        block["text"] = warning + block["text"]
                        changed = True
                        break
    elif endpoint.endswith("messages"):
        for block in payload.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                block["text"] = warning + block["text"]
                changed = True
                break
    return changed


def _sse_chat_warning_chunk(sample: dict[str, Any], warning: str) -> str:
    chunk = {
        "id": sample.get("id", "proxy-balance-warning"),
        "object": "chat.completion.chunk",
        "created": sample.get("created", int(time.time())),
        "model": sample.get("model", ""),
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": warning}, "finish_reason": None}],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def _sse_messages_warning_events(index: int, warning: str) -> str:
    delta = {
        "type": "content_block_delta",
        "index": index,
        "delta": {"type": "text_delta", "text": warning},
    }
    return f"event: content_block_delta\ndata: {json.dumps(delta, ensure_ascii=False)}\n\n"


# --------------------------------------------------------------------------- вспомогательное


def _parse_json(raw: bytes | str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _endpoint_label(subpath: str) -> str:
    """Нормализованный ярлык эндпоинта: id задач заменяем на {task_id}."""
    parts = [p for p in subpath.split("/") if p]
    if len(parts) >= 4 and parts[:3] == ["v1", "async", "media"] and parts[3] == "tasks" and len(parts) > 4:
        return "v1/async/media/tasks/{task_id}"
    return "/".join(parts)


def _model_from(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    if isinstance(model, str) and model:
        return model
    data = payload.get("data")
    if isinstance(data, dict):
        return _model_from(data)
    return None


def _sse_data_objects(event_text: str) -> list[Any]:
    objects = []
    for line in event_text.split("\n"):
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                parsed = _parse_json(payload)
                if parsed is not None:
                    objects.append(parsed)
    return objects


def _sse_event_name(event_text: str) -> str | None:
    for line in event_text.split("\n"):
        if line.startswith("event:"):
            return line[6:].strip()
    return None


def _collect_stream_text(payload: Any) -> str:
    """Текст из SSE-чанка — чтобы в логе был читаемый ответ."""
    if not isinstance(payload, dict):
        return ""
    for choice in payload.get("choices") or []:
        delta = choice.get("delta") if isinstance(choice, dict) else None
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            return delta["content"]
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("text"), str):
        return delta["text"]
    return ""


class _StreamAccumulator:
    """Склеивает из SSE-чанков то, что интересно мониторингу.

    Текст, рассуждения (`delta.reasoning`) и вызовы инструментов приходят кусками:
    у tool_calls в первом фрагменте есть id и имя, в следующих — части `arguments`,
    склеиваемые по полю `index`.
    """

    def __init__(self) -> None:
        self.text: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: dict[int, dict[str, Any]] = {}
        self.finish_reason: str | None = None
        self.usage: dict[str, Any] | None = None

    def feed(self, payload: dict[str, Any]) -> None:
        self.text.append(_collect_stream_text(payload))
        # итоговый usage приходит в предпоследнем чанке — он нужен для разбора
        # рассуждений и кэша в карточке запроса
        if isinstance(payload.get("usage"), dict):
            self.usage = payload["usage"]

        for choice in payload.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                continue
            if isinstance(delta.get("reasoning"), str):
                self.reasoning.append(delta["reasoning"])
            for fragment in delta.get("tool_calls") or []:
                if isinstance(fragment, dict):
                    self._merge_tool_call(fragment)

        # формат /v1/messages: рассуждения приходят как thinking_delta
        delta = payload.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("thinking"), str):
            self.reasoning.append(delta["thinking"])
        if payload.get("type") == "message_delta":
            stop = (payload.get("delta") or {}).get("stop_reason") if isinstance(payload.get("delta"), dict) else None
            if stop:
                self.finish_reason = stop

    def _merge_tool_call(self, fragment: dict[str, Any]) -> None:
        index = fragment.get("index")
        index = int(index) if isinstance(index, int) else len(self.tool_calls)
        call = self.tool_calls.setdefault(index, {"name": None, "arguments": "", "id": None})
        if fragment.get("id"):
            call["id"] = fragment["id"]
        function = fragment.get("function")
        if isinstance(function, dict):
            if function.get("name"):
                call["name"] = function["name"]
            if isinstance(function.get("arguments"), str):
                call["arguments"] += function["arguments"]

    def result(self) -> dict[str, Any]:
        calls = []
        for _, call in sorted(self.tool_calls.items()):
            arguments = call["arguments"]
            parsed = None
            if arguments:
                try:
                    parsed = json.loads(arguments)
                except (ValueError, TypeError):
                    parsed = None
            calls.append({
                "name": call["name"],
                "arguments": parsed if parsed is not None else (arguments or None),
                "id": call["id"],
            })
        result: dict[str, Any] = {
            "text": "".join(self.text),
            "reasoning": "".join(self.reasoning),
            "tool_calls": calls,
            "finish_reason": self.finish_reason,
        }
        if self.usage:
            result["usage"] = self.usage
        return result


# --------------------------------------------------------------------------- основной обработчик


async def handle(request: Request, subpath: str) -> Response:
    cfg = config.load()
    if not config.is_configured():
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "Прокси не настроен: укажите api_key и base_url на странице /settings",
                    "type": "proxy_not_configured",
                }
            },
        )

    subpath = subpath.lstrip("/")
    body = await request.body()
    request_payload = _parse_json(body)
    endpoint = _endpoint_label(subpath)
    model = _model_from(request_payload)
    is_stream = bool(isinstance(request_payload, dict) and request_payload.get("stream"))

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _DROP_REQUEST_HEADERS}
    headers["Authorization"] = f"Bearer {cfg['api_key']}"
    if body and "content-type" not in {k.lower() for k in headers}:
        headers["Content-Type"] = "application/json"

    entry: dict[str, Any] = {
        "ts": _now(),
        "method": request.method,
        "path": "/" + subpath,
        "endpoint": endpoint,
        "model": model,
        "stream": is_stream,
        "client_ip": request.client.host if request.client else None,
        "upstream": cfg["source"],
        "request_body": body.decode("utf-8", "replace") if body else None,
    }
    # в апстрим уходит исходное тело; в лог — со встроенными картинками, вынесенными в файлы
    rewritten, inputs = media.extract_request(request_payload)
    entry["request_body"] = media.rewrite_body(entry["request_body"], request_payload, rewritten, inputs)
    _attach_media(entry, inputs)

    started = time.perf_counter()
    client = await get_client()
    upstream_request = client.build_request(
        request.method,
        upstream_url(cfg, subpath),
        headers=headers,
        params=dict(request.query_params),
        content=body or None,
    )

    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        entry.update(
            status_code=502,
            duration_ms=(time.perf_counter() - started) * 1000,
            error=f"{type(exc).__name__}: {exc}",
        )
        db.log_request(entry)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"Апстрим недоступен: {exc}", "type": "upstream_error"}},
        )

    content_type = upstream.headers.get("content-type", "")
    out_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _DROP_RESPONSE_HEADERS
    }

    if "text/event-stream" in content_type.lower():
        entry["stream"] = True
        generator = _stream_response(upstream, entry, cfg, endpoint, started)
        return StreamingResponse(
            generator,
            status_code=upstream.status_code,
            headers=out_headers,
            media_type=content_type,
        )

    try:
        raw = await upstream.aread()
    finally:
        await upstream.aclose()

    entry["status_code"] = upstream.status_code
    entry["duration_ms"] = (time.perf_counter() - started) * 1000

    response_payload = _parse_json(raw)
    entry["response_body"] = raw.decode("utf-8", "replace") if raw else None
    rewritten, outputs = media.extract_response(response_payload)
    entry["response_body"] = media.rewrite_body(entry["response_body"], response_payload, rewritten, outputs)
    _attach_media(entry, outputs)
    if not entry["model"]:
        entry["model"] = _model_from(response_payload)
    if isinstance(response_payload, dict) and isinstance(response_payload.get("id"), str):
        entry["upstream_id"] = response_payload["id"]

    entry.update(usage_mod.extract_usage(response_payload))
    usage_mod.fill_cost(entry, cfg["cost_mode"])
    if upstream.status_code >= 400:
        entry["error"] = _error_text(response_payload) or f"HTTP {upstream.status_code}"

    _post_process(endpoint, response_payload, entry)

    # предупреждение о балансе в начало текстового ответа
    if upstream.status_code < 400 and response_payload is not None:
        warning = balance_warning(cfg)
        if warning and _inject_into_payload(response_payload, warning, endpoint):
            raw = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")

    db.log_request(entry)
    return Response(content=raw, status_code=upstream.status_code, headers=out_headers, media_type=content_type or None)


def _attach_media(entry: dict[str, Any], collector: media.Collector) -> None:
    """Добавить найденные медиа к записи; подпись для галереи — промпт, если он есть."""
    items = entry.setdefault("media", [])
    prompt = collector.prompt or next((i.get("prompt") for i in items if i.get("prompt")), None)
    for item in collector.items:
        items.append({**item, "prompt": prompt})


def _error_text(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if isinstance(error, str):
            return error
        if payload.get("msg") and payload.get("code") not in (200, "200", None):
            return f"{payload.get('code')}: {payload.get('msg')}"
    return None


def _post_process(endpoint: str, payload: Any, entry: dict[str, Any]) -> None:
    """Побочные эффекты: кэш цен из /v1/models и снимок баланса из /v1/balance."""
    if endpoint == "v1/models" and isinstance(payload, dict):
        models = payload.get("data")
        if isinstance(models, list):
            db.upsert_model_pricing([m for m in models if isinstance(m, dict)], entry.get("upstream") or "")
            # появились цены — у прошлых запросов этих моделей появляется и оценка
            db.fill_estimates()
            db.recompute_costs(config.load()["cost_mode"])
    elif endpoint == "v1/balance":
        amount = usage_mod.parse_balance(payload)
        if amount is not None:
            observe_balance(amount, source="proxy", upstream=entry.get("upstream") or "")
    _apply_local_cost(entry.get("cost"))


async def _stream_response(
    upstream: httpx.Response,
    entry: dict[str, Any],
    cfg: dict[str, Any],
    endpoint: str,
    started: float,
) -> AsyncIterator[bytes]:
    """Прокидываем SSE как есть, попутно собирая usage и вставляя предупреждение о балансе."""
    warning = balance_warning(cfg)
    injected = warning is None
    is_chat = endpoint.endswith("chat/completions")
    is_messages = endpoint.endswith("messages")

    buffer = ""
    raw_events: list[str] = []
    parsed_chunks: list[dict[str, Any]] = []
    collected = _StreamAccumulator()
    error: str | None = None

    try:
        async for piece in upstream.aiter_bytes():
            buffer += piece.decode("utf-8", "replace").replace("\r\n", "\n")
            while "\n\n" in buffer:
                event_text, buffer = buffer.split("\n\n", 1)
                if not event_text.strip():
                    continue
                raw_events.append(event_text)
                out = ""
                for payload in _sse_data_objects(event_text):
                    if isinstance(payload, dict):
                        parsed_chunks.append(payload)
                        collected.feed(payload)
                        if not entry.get("model"):
                            entry["model"] = _model_from(payload)
                        if not entry.get("upstream_id") and isinstance(payload.get("id"), str):
                            entry["upstream_id"] = payload["id"]
                        if not injected and is_chat and payload.get("choices"):
                            out += _sse_chat_warning_chunk(payload, warning or "")
                            injected = True
                        if (
                            not injected
                            and is_messages
                            and payload.get("type") == "content_block_start"
                            and isinstance(payload.get("content_block"), dict)
                            and payload["content_block"].get("type") == "text"
                        ):
                            # предупреждение вставляем после старта текстового блока
                            out += event_text + "\n\n"
                            yield out.encode("utf-8")
                            yield _sse_messages_warning_events(
                                int(payload.get("index") or 0), warning or ""
                            ).encode("utf-8")
                            injected = True
                            out = ""
                            event_text = ""
                            break
                if event_text:
                    out += event_text + "\n\n"
                if out:
                    yield out.encode("utf-8")
        if buffer.strip():
            raw_events.append(buffer)
            yield buffer.encode("utf-8")
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        await upstream.aclose()
        entry["status_code"] = upstream.status_code
        entry["duration_ms"] = (time.perf_counter() - started) * 1000
        entry["error"] = error or (None if upstream.status_code < 400 else f"HTTP {upstream.status_code}")
        entry.update(usage_mod.merge_stream_usage(parsed_chunks))
        usage_mod.fill_cost(entry, cfg["cost_mode"])
        entry["response_body"] = json.dumps(
            {
                "stream": True,
                **collected.result(),
                "events": len(raw_events),
                "raw": "\n\n".join(raw_events[-200:]),
            },
            ensure_ascii=False,
        )
        _apply_local_cost(entry.get("cost"))
        db.log_request(entry)
