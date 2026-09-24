"""Разбор тел запроса и ответа в читаемый вид: диалог, рассуждения, вызовы инструментов.

Логи хранят сырой JSON, а интерфейсу нужно показать суть: что спросили, что модель
думала и какие инструменты дёрнула. Форматы проверены на живом API:

  * chat/completions — `message.reasoning` (текст рассуждений), `message.tool_calls`,
    `usage.completion_tokens_details.reasoning_tokens`, `usage.prompt_tokens_details.cached_tokens`
  * стриминг — те же поля приходят кусками в `delta.reasoning` / `delta.content` /
    `delta.tool_calls`, поэтому прокси склеивает их заранее (см. proxy._stream_response)
  * messages (Anthropic) — блоки `content` с типами `text`, `thinking`, `tool_use`
"""
from __future__ import annotations

import json
from typing import Any

from . import media as media_mod

PREVIEW_LIMIT = 400


def _clip(text: str | None, limit: int = PREVIEW_LIMIT) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def parse(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _image_src(block: dict[str, Any]) -> str | None:
    """Ссылка на картинку из блока content любого формата (для браузера)."""
    image_url = block.get("image_url")
    if isinstance(image_url, dict):
        return media_mod.resolve(image_url.get("url"))
    if isinstance(image_url, str):
        return media_mod.resolve(image_url)
    source = block.get("source")
    if isinstance(source, dict):
        if source.get("type") == "base64" and isinstance(source.get("data"), str):
            data = source["data"]
            if data.startswith(media_mod.REF_PREFIX):
                return media_mod.resolve(data)
            return f"data:{source.get('media_type') or 'image/png'};base64,{data}"
        return media_mod.resolve(source.get("url"))
    return None


def _content_parts(content: Any) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Текст, картинки (ссылки для браузера) и прочие блоки из поля content любого формата.

    Картинка, которую не удалось показать (обрезанное тело), всё равно учитывается —
    пустой строкой, чтобы счётчик в логе не врал.
    """
    if isinstance(content, str):
        return content, [], []
    texts: list[str] = []
    images: list[str] = []
    extras: list[dict[str, Any]] = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                if isinstance(block, str):
                    texts.append(block)
                continue
            kind = block.get("type")
            if kind in ("text", "input_text", "output_text") and isinstance(block.get("text"), str):
                texts.append(block["text"])
            elif kind in ("image_url", "image", "input_image"):
                images.append(_image_src(block) or "")
            elif kind == "thinking" and isinstance(block.get("thinking"), str):
                extras.append({"kind": "thinking", "text": block["thinking"]})
            elif kind == "tool_use":
                extras.append({
                    "kind": "tool_call",
                    "name": block.get("name"),
                    "arguments": block.get("input"),
                    "id": block.get("id"),
                })
            elif kind == "tool_result":
                extras.append({
                    "kind": "tool_result",
                    "id": block.get("tool_use_id"),
                    "text": _stringify(block.get("content")),
                })
    return "\n".join(texts), images, extras


def _stringify(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            text = str(value)
    return text if len(text) <= limit else text[:limit] + "\n… (обрезано)"


def _tool_calls(raw: Any) -> list[dict[str, Any]]:
    """Нормализованные вызовы инструментов из ответа chat/completions."""
    calls = []
    if not isinstance(raw, list):
        return calls
    for item in raw:
        if not isinstance(item, dict):
            continue
        function = item.get("function") if isinstance(item.get("function"), dict) else {}
        arguments = function.get("arguments")
        # аргументы приходят строкой с JSON — разворачиваем для читаемости
        parsed = parse(arguments) if isinstance(arguments, str) else arguments
        calls.append({
            "name": function.get("name") or item.get("name"),
            "arguments": parsed if parsed is not None else arguments,
            "id": item.get("id"),
        })
    return calls


def _request_summary(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "system": None, "messages": [], "tools_offered": [],
        "params": {}, "images": 0, "reasoning_request": None,
    }

    def message(role: str, text: str, images: list[str], extras: list[dict[str, Any]]) -> dict[str, Any]:
        result["images"] += len(images)
        return {"role": role, "text": text, "images": len(images),
                "media": [src for src in images if src], "extras": extras}

    if not isinstance(payload, dict):
        return result

    for key in ("temperature", "max_tokens", "max_completion_tokens", "top_p",
                "presence_penalty", "frequency_penalty", "stream", "response_format",
                "tool_choice", "seed"):
        if payload.get(key) is not None:
            result["params"][key] = payload[key]

    if isinstance(payload.get("reasoning"), dict):
        result["reasoning_request"] = payload["reasoning"]

    for tool in payload.get("tools") or []:
        if isinstance(tool, dict):
            function = tool.get("function") if isinstance(tool.get("function"), dict) else tool
            name = function.get("name")
            if name:
                result["tools_offered"].append({
                    "name": name,
                    "description": _clip(function.get("description"), 200),
                })

    # у /v1/messages системный промпт лежит отдельным полем
    system = payload.get("system")
    if isinstance(system, str) and system.strip():
        result["system"] = system
    elif isinstance(system, list):
        text, _, _ = _content_parts(system)
        result["system"] = text or None

    if isinstance(payload.get("prompt"), str):
        result["messages"].append(message("user", payload["prompt"], [], []))

    # медиа-задачи: {"model", "input": {"prompt", "image_url" | "image_urls" | …}}
    task_input = payload.get("input")
    if isinstance(task_input, dict):
        prompt = task_input.get("prompt")
        images = [media_mod.resolve(src) or "" for src in media_mod.input_sources(task_input)]
        if isinstance(prompt, str) or images:
            result["messages"].append(message("user", prompt if isinstance(prompt, str) else "", images, []))
        result["params"].update({
            k: v for k, v in task_input.items()
            if k != "prompt" and not media_mod.IMAGE_KEY.search(k) and isinstance(v, (str, int, float, bool))
        })

    for item in payload.get("messages") or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role") or "user"
        text, images, extras = _content_parts(item.get("content"))
        if role == "system" and not result["system"]:
            result["images"] += len(images)
            result["system"] = text
            continue
        entry = message(role, text, images, extras)
        if item.get("tool_calls"):
            entry["extras"] = extras + [
                {"kind": "tool_call", **call} for call in _tool_calls(item["tool_calls"])
            ]
        if item.get("tool_call_id"):
            entry["tool_call_id"] = item["tool_call_id"]
        result["messages"].append(entry)

    return result


def _response_summary(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "text": None, "reasoning": None, "tool_calls": [],
        "finish_reason": None, "error": None, "media": None, "images": [],
    }
    if not isinstance(payload, dict):
        return result

    # images/generations и картинки в ответе chat/completions
    result["images"] = [src for src in map(media_mod.resolve, media_mod.response_images(payload)) if src]

    error = payload.get("error")
    if isinstance(error, dict):
        result["error"] = error.get("message") or _stringify(error)
    elif isinstance(error, str):
        result["error"] = error

    # склеенный прокси стрим
    if payload.get("stream"):
        result["text"] = payload.get("text") or None
        result["reasoning"] = payload.get("reasoning") or None
        result["tool_calls"] = payload.get("tool_calls") or []
        result["finish_reason"] = payload.get("finish_reason")
        return result

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        text, images, extras = _content_parts(message.get("content"))
        result["images"] += [src for src in images if src]
        result["text"] = text or None
        if isinstance(message.get("reasoning"), str):
            result["reasoning"] = message["reasoning"]
        result["tool_calls"] = _tool_calls(message.get("tool_calls"))
        result["finish_reason"] = choice.get("finish_reason")
        for extra in extras:
            if extra.get("kind") == "thinking" and not result["reasoning"]:
                result["reasoning"] = extra.get("text")
        return result

    # формат /v1/messages
    if payload.get("type") == "message" or isinstance(payload.get("content"), list):
        text, images, extras = _content_parts(payload.get("content"))
        result["images"] += [src for src in images if src]
        result["text"] = text or None
        result["finish_reason"] = payload.get("stop_reason")
        for extra in extras:
            if extra.get("kind") == "thinking" and not result["reasoning"]:
                result["reasoning"] = extra.get("text")
            elif extra.get("kind") == "tool_call":
                result["tool_calls"].append({
                    "name": extra.get("name"), "arguments": extra.get("arguments"), "id": extra.get("id"),
                })
        return result

    # медиа-задачи: показываем состояние и результат
    data = payload.get("data")
    if isinstance(data, dict) and (data.get("taskId") or data.get("state")):
        media = {"task_id": data.get("taskId"), "state": data.get("state"),
                 "urls": media_mod.result_urls(payload)}
        if data.get("failMsg"):
            result["error"] = str(data["failMsg"])
        result["media"] = media
    return result


def _tokens(payload: Any) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    if not isinstance(payload, dict):
        return tokens
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return tokens
    completion_details = usage.get("completion_tokens_details")
    if isinstance(completion_details, dict):
        for key in ("reasoning_tokens", "image_tokens"):
            if completion_details.get(key):
                tokens[key] = completion_details[key]
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        for key in ("cached_tokens", "cache_write_tokens"):
            if prompt_details.get(key):
                tokens[key] = prompt_details[key]
    for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
        if usage.get(key):
            tokens[key] = usage[key]
    return tokens


def summarize(request_body: Any, response_body: Any) -> dict[str, Any]:
    """Полный разбор для карточки запроса в интерфейсе."""
    request_payload = parse(request_body)
    response_payload = parse(response_body)
    summary = {
        "request": _request_summary(request_payload),
        "response": _response_summary(response_payload),
        "tokens": _tokens(response_payload),
    }
    summary["has_raw_request"] = request_payload is not None
    summary["has_raw_response"] = response_payload is not None
    return summary


def compact(request_body: Any, response_body: Any) -> dict[str, Any]:
    """Короткие поля для строки лога — считаются при записи и хранятся в БД."""
    summary = summarize(request_body, response_body)
    request = summary["request"]
    response = summary["response"]

    last_user = next(
        (m["text"] for m in reversed(request["messages"]) if m.get("role") == "user" and m.get("text")),
        None,
    )
    called = [c.get("name") for c in response["tool_calls"] if c.get("name")]
    return {
        "prompt_preview": _clip(last_user),
        "answer_preview": _clip(response["text"] or response["error"]),
        "reasoning_preview": _clip(response["reasoning"], 200),
        "tools_offered": len(request["tools_offered"]) or None,
        "tools_called": ",".join(called) or None,
        "images": request["images"] or None,
        "media_out": len(response["images"]) + len((response["media"] or {}).get("urls") or []) or None,
        "finish_reason": response["finish_reason"],
        "reasoning_tokens": summary["tokens"].get("reasoning_tokens"),
        "cached_tokens": summary["tokens"].get("cached_tokens") or summary["tokens"].get("cache_read_input_tokens"),
    }
