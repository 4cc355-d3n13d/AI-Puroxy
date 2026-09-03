"""Документация для /docs: исходные .md с заменой домена speshu.ai на домен из настроек."""
from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

DOCS_DIR = Path(__file__).resolve().parent / "docs"
ORIGIN_DOMAIN = "speshu.ai"

# Порядок и группировка страниц в сайдбаре: (slug, ярлык эндпоинта).
# Пустой ярлык — у страниц-каталогов, которым не соответствует отдельный эндпоинт.
SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Модели", [("models_list", "/models")]),
    ("Текст", [("chat_completions", "/chat/completions"), ("messages_create", "/messages/create")]),
    (
        "Медиа",
        [
            ("media_models", "/media/models"),
            ("media_create", "/media/create"),
            ("media_status", "/media/status"),
            ("media_list", "/media/list"),
            ("media_sessions", "/media/sessions"),
        ],
    ),
    (
        "Каталоги медиа-моделей",
        [
            ("media_image-models", ""),
            ("media_video-models", ""),
            ("media_audio-models", ""),
        ],
    ),
    ("Прочее", [("balance", "/balance")]),
]

_INDEX_NOTE = re.compile(r"\A(?:>[^\n]*\n)+\s*", re.MULTILINE)
_md = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table").enable("strikethrough")

# Исходники написаны в MDX: компоненты нужно развернуть в обычный markdown,
# иначе они выводятся на страницу как текст.
_MDX_WRAPPER = re.compile(r"^[ \t]*</?(?:CardGroup|CodeGroup|Columns|Frame|Accordion)[^>]*>[ \t]*\n?", re.MULTILINE)
_MDX_CARD = re.compile(r"<Card\s+([^>]*)>\s*(.*?)\s*</Card>", re.DOTALL)
_MDX_CALLOUT = re.compile(r"<(Note|Tip|Info|Warning|Danger)>\s*(.*?)\s*</\1>", re.DOTALL)
_MDX_ATTR = re.compile(r'(\w+)="([^"]*)"')
_CALLOUT_LABELS = {"Note": "Примечание", "Tip": "Совет", "Info": "Справка",
                   "Warning": "Важно", "Danger": "Внимание"}

# Перекрёстные ссылки исходной документации, которые не должны вести наружу.
_CROSS_LINK = re.compile(r"/docs/api-reference/([a-z0-9/_-]+)")
_ORIGINAL_PATH_OVERRIDES = {"balance": "other/balance"}


def _original_path(slug: str) -> str:
    """Путь страницы в исходной документации ИИ-API."""
    return _ORIGINAL_PATH_OVERRIDES.get(slug) or slug.replace("_", "/", 1)


def _demdx(markdown: str) -> str:
    """Развернуть MDX-компоненты в обычный markdown."""

    def card(match: re.Match[str]) -> str:
        attrs = dict(_MDX_ATTR.findall(match.group(1)))
        body = " ".join(match.group(2).split())
        title = attrs.get("title", "Подробнее")
        href = attrs.get("href")
        link = f"[{title}]({href})" if href else title
        return f"- **{link}**{' — ' + body if body else ''}"

    def callout(match: re.Match[str]) -> str:
        label = _CALLOUT_LABELS.get(match.group(1), "Примечание")
        body = " ".join(match.group(2).split())
        return f"> **{label}.** {body}"

    markdown = _MDX_CARD.sub(card, markdown)
    markdown = _MDX_CALLOUT.sub(callout, markdown)
    return _MDX_WRAPPER.sub("", markdown)


def _relink(markdown: str) -> str:
    """Ссылки на исходную документацию перевести на локальные страницы."""
    by_path = {_original_path(slug): slug for _, items in SECTIONS for slug, _ref in items}

    def repl(match: re.Match[str]) -> str:
        slug = by_path.get(match.group(1).strip("/"))
        return f"/docs/{slug}" if slug else match.group(0)

    return _CROSS_LINK.sub(repl, markdown)


def _local(domain: str) -> bool:
    host = domain.split(":", 1)[0].lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local")


def replace_domain(text: str, domain: str) -> str:
    """speshu.ai -> домен из настроек (для локальных доменов схема понижается до http)."""
    domain = (domain or ORIGIN_DOMAIN).strip().strip("/")
    if not domain or domain == ORIGIN_DOMAIN:
        return text
    domain = re.sub(r"^https?://", "", domain)
    scheme = "http" if _local(domain) else "https"
    text = text.replace(f"https://{ORIGIN_DOMAIN}", f"{scheme}://{domain}")
    text = text.replace(f"http://{ORIGIN_DOMAIN}", f"{scheme}://{domain}")
    return text.replace(ORIGIN_DOMAIN, domain)


@lru_cache(maxsize=64)
def _raw(slug: str) -> str | None:
    path = DOCS_DIR / f"{slug}.md"
    if not path.is_file():
        return None
    text = path.read_text("utf-8")
    text = _INDEX_NOTE.sub("", text, count=1)
    return _relink(_demdx(text))


def _title(markdown: str, fallback: str) -> tuple[str, str]:
    title, subtitle = fallback, ""
    for line in markdown.split("\n"):
        if line.startswith("# ") and title == fallback:
            title = line[2:].strip()
        elif line.startswith("> ") and title != fallback and not subtitle:
            subtitle = line[2:].strip()
            break
    return title, subtitle


def pages() -> list[dict[str, Any]]:
    """Список страниц документации для сайдбара."""
    result = []
    for section, items in SECTIONS:
        for slug, ref in items:
            markdown = _raw(slug)
            if markdown is None:
                continue
            title, subtitle = _title(markdown, ref or slug)
            result.append({"slug": slug, "section": section, "ref": ref, "title": title, "subtitle": subtitle})
    return result


def _render_html(markdown: str) -> str:
    html_text = _md.render(markdown)
    # у fence-блоков вида ```bash theme={null} подсветку берём по первому слову
    html_text = re.sub(r'<code class="language-([^"\s]+)[^"]*"', r'<code class="language-\1"', html_text)
    return html_text


def page(slug: str, domain: str) -> dict[str, Any] | None:
    markdown = _raw(slug)
    if markdown is None:
        return None
    meta = next((p for p in pages() if p["slug"] == slug), None)
    markdown = replace_domain(markdown, domain)
    body = _render_html(markdown)
    toc = [
        {"level": len(m.group(1)), "text": m.group(2).strip(), "anchor": _anchor(m.group(2))}
        for m in re.finditer(r"^(#{2,3})\s+(.+)$", markdown, re.MULTILINE)
    ]
    body = _add_anchors(body)
    return {
        "slug": slug,
        "title": (meta or {}).get("title", slug),
        "subtitle": (meta or {}).get("subtitle", ""),
        "section": (meta or {}).get("section", ""),
        "ref": (meta or {}).get("ref", slug),
        "html": body,
        "toc": toc,
        "markdown": markdown,
    }


def _anchor(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.strip().lower(), flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", slug)


def _add_anchors(html_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        level, inner = match.group(1), match.group(2)
        plain = re.sub(r"<[^>]+>", "", inner)
        return f'<h{level} id="{html.escape(_anchor(plain))}">{inner}</h{level}>'

    return re.sub(r"<h([23])>(.*?)</h\1>", repl, html_text, flags=re.DOTALL)
