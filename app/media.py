"""Картинки, видео и аудио из тел запросов и ответов.

Встроенные в JSON данные (`data:image/…;base64,…`, `source.data` у /v1/messages,
`b64_json` у images/generations) сохраняются файлами в data/media/, а в логе
заменяются ссылкой `media://<файл>`. Иначе картинка в 50 КБ base64 раздувает базу,
а обрезка тела до 400 000 символов делает её нечитаемой.

Внешние URL не скачиваются — запоминается только ссылка. Имя файла — хэш
содержимого, поэтому одна и та же картинка, присланная десять раз, лежит на диске
один раз.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from . import config

REF_PREFIX = "media://"
# встроенные данные короче этого — заглушки и примеры, а не содержимое
MIN_INLINE = 200
# ключи, под которыми в запросах лежат ссылки на входные картинки:
# image_url, image_urls, reference_image_urls, end_image_url, input.image_url…
IMAGE_KEY = re.compile(r"image", re.I)
FILE_NAME = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{1,5}$")
_DATA_URI = re.compile(r"^data:([\w.+-]+/[\w.+-]+)?((?:;[\w.+-]+=[\w.+-]+)*);base64,", re.I)

_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp",
    "image/gif": "gif", "image/avif": "avif", "image/heic": "heic", "image/bmp": "bmp",
    "image/svg+xml": "svg",
    "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov",
    "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav",
    "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/aac": "aac", "audio/flac": "flac",
}
_MIME = {ext: mime for mime, ext in reversed(list(_EXT.items()))}
_VIDEO_EXT = {"mp4", "webm", "mov", "m4v", "mkv"}
_AUDIO_EXT = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "opus"}


def kind_of(mime: str | None = None, url: str | None = None) -> str:
    """image | video | audio — по MIME или по расширению в URL."""
    if mime:
        head = mime.split("/", 1)[0].lower()
        if head in ("video", "audio"):
            return head
        if head == "image":
            return "image"
    if url:
        ext = url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
        if ext in _VIDEO_EXT:
            return "video"
        if ext in _AUDIO_EXT:
            return "audio"
    return "image"


def mime_of_file(name: str) -> str:
    return _MIME.get(name.rsplit(".", 1)[-1], "application/octet-stream")


def path_of(name: str):
    """Путь к сохранённому файлу или None, если имя не похоже на наше."""
    if not FILE_NAME.match(name):
        return None
    return config.MEDIA_DIR / name


def resolve(src: Any) -> str | None:
    """Ссылка для браузера: media:// → /_media/…, data: и http(s) — как есть."""
    if not isinstance(src, str) or not src:
        return None
    if src.startswith(REF_PREFIX):
        return "/_media/" + src[len(REF_PREFIX):]
    if src.startswith(("http://", "https://", "data:")):
        return src
    return None


def _sniff(data: bytes) -> str | None:
    """MIME по сигнатуре — у b64_json и сырого base64 тип не указан."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[4:8] == b"ftyp":
        return "image/avif" if data[8:12] in (b"avif", b"avis") else "video/mp4"
    return None


class Collector:
    """Собирает медиа из одного тела; `items` потом пишутся в таблицу media."""

    def __init__(self, direction: str, store: bool = True) -> None:
        self.direction = direction
        self.store = store
        self.items: list[dict[str, Any]] = []
        self.changed = False
        self.prompt: str | None = None

    def inline(self, payload: str, mime: str | None = None) -> str | None:
        """Сохранить base64 в файл; вернуть ссылку media:// или None, если это не данные."""
        try:
            data = base64.b64decode(payload, validate=False)
        except (binascii.Error, ValueError):
            return None
        if not data:
            return None
        mime = (mime or "").lower() or _sniff(data) or "image/png"
        name = hashlib.sha256(data).hexdigest()[:32] + "." + _EXT.get(mime, "bin")
        if self.store:
            config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            path = config.MEDIA_DIR / name
            if not path.exists():
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)
        self.items.append({
            "key": f"{self.direction}:{name}", "direction": self.direction,
            "kind": kind_of(mime), "file": name, "url": None, "mime": mime, "bytes": len(data),
        })
        return REF_PREFIX + name

    def url(self, url: str) -> None:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return
        if any(item["url"] == url for item in self.items):
            return
        self.items.append({
            "key": f"{self.direction}:{url}", "direction": self.direction,
            "kind": kind_of(url=url), "file": None, "url": url, "mime": None, "bytes": None,
        })

    def ref(self, value: str) -> None:
        """Учесть уже переписанную ссылку media:// (повторный разбор)."""
        name = value[len(REF_PREFIX):]
        if FILE_NAME.match(name) and not any(item["file"] == name for item in self.items):
            self.items.append({
                "key": f"{self.direction}:{name}", "direction": self.direction,
                "kind": kind_of(mime_of_file(name)), "file": name, "url": None,
                "mime": mime_of_file(name), "bytes": None,
            })


def _inline_string(value: str, collector: Collector) -> str | None:
    match = _DATA_URI.match(value)
    if not match or len(value) < MIN_INLINE:
        return None
    return collector.inline(value[match.end():], match.group(1))


def _walk(node: Any, collector: Collector, key: str | None, urls: bool) -> Any:
    """Обойти JSON, заменив встроенные данные ссылками; при urls — собрать ссылки на картинки."""
    if isinstance(node, str):
        if node.startswith("data:"):
            ref = _inline_string(node, collector)
            if ref:
                collector.changed = True
                return ref
        elif node.startswith(REF_PREFIX):
            collector.ref(node)
        elif urls and key and IMAGE_KEY.search(key):
            collector.url(node)
        return node
    if isinstance(node, list):
        return [_walk(item, collector, key, urls) for item in node]
    if not isinstance(node, dict):
        return node

    # /v1/messages: {"type": "base64", "media_type": "image/png", "data": "…"}
    data = node.get("data")
    if node.get("type") == "base64" and isinstance(data, str) and len(data) >= MIN_INLINE:
        ref = collector.inline(data, node.get("media_type"))
        if ref:
            collector.changed = True
            return {**node, "data": ref}
    if node.get("type") == "base64" and isinstance(data, str) and data.startswith(REF_PREFIX):
        collector.ref(data)
        return node
    # /v1/messages: {"type": "url", "url": "https://…"} внутри блока image
    if urls and node.get("type") == "url" and key == "source":
        collector.url(node.get("url"))
        return node

    result = {}
    for child_key, value in node.items():
        # b64_json у images/generations
        if child_key == "b64_json" and isinstance(value, str):
            if value.startswith(REF_PREFIX):
                collector.ref(value)
            elif len(value) >= MIN_INLINE:
                ref = collector.inline(value, _format_mime(node.get("output_format")))
                if ref:
                    collector.changed = True
                    result[child_key] = ref
                    continue
        # {"image_url": {"url": "…"}} — ключ-контекст берём у родителя
        inner_key = key if child_key == "url" else child_key
        result[child_key] = _walk(value, collector, inner_key, urls)
    return result


def _format_mime(fmt: Any) -> str | None:
    if isinstance(fmt, str) and fmt:
        return "image/" + ("jpeg" if fmt.lower() in ("jpg", "jpeg") else fmt.lower())
    return None


def _parse(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if not raw or not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def extract_request(payload: Any, store: bool = True) -> tuple[Any, Collector]:
    """Входные медиа запроса: встроенные данные → файлы, ссылки на картинки → учёт."""
    collector = Collector("input", store)
    if payload is None:
        return payload, collector
    rewritten = _walk(payload, collector, None, urls=True)
    if isinstance(payload, dict) and isinstance(payload.get("input"), dict):
        prompt = payload["input"].get("prompt")
        collector.prompt = prompt if isinstance(prompt, str) else None
    elif isinstance(payload, dict) and isinstance(payload.get("prompt"), str):
        collector.prompt = payload["prompt"]
    return rewritten, collector


def result_urls(payload: Any) -> list[str]:
    """Ссылки на результат медиа-задачи из data.resultJson.resultUrls."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return []
    results = _parse(data.get("resultJson"))
    urls = results.get("resultUrls") if isinstance(results, dict) else None
    return [u for u in urls if isinstance(u, str)] if isinstance(urls, list) else []


def response_images(payload: Any) -> list[str]:
    """Картинки в ответе: images/generations (data[].url|b64_json) и chat (message.images)."""
    found: list[str] = []
    if not isinstance(payload, dict):
        return found
    data = payload.get("data")
    # images/generations: {"created": …, "data": [{"url" | "b64_json"}]}; у каталогов
    # (/v1/models и т.п.) тоже есть data-список, но нет created
    if isinstance(data, list) and "created" in payload:
        for item in data:
            if isinstance(item, dict):
                src = item.get("url") or item.get("b64_json")
                if isinstance(src, str):
                    found.append(src)
    for choice in payload.get("choices") or []:
        message = choice.get("message") if isinstance(choice, dict) else None
        if not isinstance(message, dict):
            continue
        for image in message.get("images") or []:
            if isinstance(image, dict):
                inner = image.get("image_url")
                src = inner.get("url") if isinstance(inner, dict) else inner
                if isinstance(src, str):
                    found.append(src)
    return found


def extract_response(payload: Any, store: bool = True) -> tuple[Any, Collector]:
    """Выходные медиа ответа. Ссылки собираются только из известных мест: ответ статуса
    задачи повторяет входные параметры (inputParams.image_url), и обход по ключам
    записал бы входные картинки в результаты."""
    collector = Collector("output", store)
    if payload is None:
        return payload, collector
    rewritten = _walk(payload, collector, None, urls=False)
    for src in response_images(rewritten):
        if src.startswith(REF_PREFIX):
            collector.ref(src)
        else:
            collector.url(src)
    for url in result_urls(payload):
        collector.url(url)
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        params = data.get("inputParams") if isinstance(data.get("inputParams"), dict) else {}
        prompt = data.get("prompt") or params.get("prompt")
        collector.prompt = prompt if isinstance(prompt, str) else None
    return rewritten, collector


def rewrite_body(raw: str | None, payload: Any, rewritten: Any, collector: Collector) -> str | None:
    """Тело для лога: исходный текст, если менять было нечего, иначе JSON со ссылками."""
    if not collector.changed or payload is None:
        return raw
    return json.dumps(rewritten, ensure_ascii=False)


def input_sources(node: Any) -> list[str]:
    """Все ссылки на картинки под «картиночными» ключами (для карточки медиа-задачи)."""
    found: list[str] = []

    def visit(value: Any, key: str | None) -> None:
        if isinstance(value, str):
            if key and IMAGE_KEY.search(key) and resolve(value):
                found.append(value)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, key if child_key == "url" else child_key)

    visit(node, None)
    return found
