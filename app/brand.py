"""Оформление: логотип из /settings, хранится в data/brand/logo.<ext>."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from . import config

MAX_LOGO_BYTES = 1024 * 1024
MIME = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "gif": "image/gif", "svg": "image/svg+xml"}


class LogoError(ValueError):
    """Файл не подходит на роль логотипа; текст показывается на странице настроек."""


def is_emoji(text: str) -> bool:
    """Плашка из эмодзи, а не из букв: у неё свой стиль (.brand-mark.is-emoji)."""
    if not text or any(unicodedata.category(ch)[0] in "LN" for ch in text):
        return False
    return any(unicodedata.category(ch) == "So" or ord(ch) >= 0x1F000 for ch in text)


def sniff(data: bytes) -> str | None:
    """Расширение по содержимому, а не по имени файла: имя может врать."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    head = data[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<svg") or (head.startswith((b"<?xml", b"<!--", b"<!doctype svg")) and b"<svg" in head):
        return "svg"
    return None


def save_logo(data: bytes) -> str:
    """Сохранить логотип, вернуть имя файла для config.logo_file."""
    if not data:
        raise LogoError("Файл логотипа пустой.")
    if len(data) > MAX_LOGO_BYTES:
        raise LogoError("Логотип больше 1 МБ — уменьшите картинку.")
    ext = sniff(data)
    if ext is None:
        raise LogoError("Логотип должен быть картинкой PNG, JPG, WebP, GIF или SVG.")
    config.BRAND_DIR.mkdir(parents=True, exist_ok=True)
    name = f"logo.{ext}"
    tmp = config.BRAND_DIR / f".{name}.tmp"
    tmp.write_bytes(data)
    tmp.replace(config.BRAND_DIR / name)
    # прежний логотип с другим расширением больше не нужен
    for old in config.BRAND_DIR.glob("logo.*"):
        if old.name != name:
            old.unlink(missing_ok=True)
    return name


def remove_logo() -> None:
    for old in config.BRAND_DIR.glob("logo.*"):
        old.unlink(missing_ok=True)


def logo_path(name: str) -> Path | None:
    if not re.fullmatch(r"logo\.(png|jpg|webp|gif|svg)", name or ""):
        return None
    path = config.BRAND_DIR / name
    return path if path.is_file() else None


def logo_url(cfg: dict) -> str | None:
    """Адрес логотипа с меткой версии — после замены браузер не покажет старый из кэша."""
    path = logo_path(cfg.get("logo_file", ""))
    if path is None:
        return None
    return f"/_brand/{path.name}?v={int(path.stat().st_mtime)}"
