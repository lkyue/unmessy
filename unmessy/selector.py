"""Locate the main content region of a page.

Cascade: site rules (URL-matched CSS selectors) -> trafilatura -> <body>.
"""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import trafilatura
import yaml
from bs4 import BeautifulSoup, Tag

from unmessy.metadata import PageMeta

DEFAULT_MIN_CHARS = 200

_RULES_PATH = Path(__file__).with_name("sites.yaml")


@dataclass
class SiteRule:
    match: str
    name: str
    selectors: list[str]
    min_chars: int = 60  # explicit selectors are trusted more than generic extraction


@dataclass
class Selection:
    kind: str  # 'tag' | 'markdown'
    tag: Tag | None
    markdown: str | None
    strategy: str


def load_rules(path: Path) -> list[SiteRule]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    rules = []
    for item in data.get("rules") or []:
        selectors = [s for s in (item.get("selectors") or []) if s]
        if item.get("match") and selectors:
            rules.append(
                SiteRule(
                    match=str(item["match"]),
                    name=str(item.get("name") or item["match"]),
                    selectors=selectors,
                    min_chars=int(item.get("min_chars") or 60),
                )
            )
    return rules


def default_rules() -> list[SiteRule]:
    return load_rules(_RULES_PATH)


def _netloc(url: str | None) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def _text_len(tag: Tag) -> int:
    return len(tag.get_text(" ", strip=True))


def _try_rules(soup: BeautifulSoup, meta: PageMeta, rules: list[SiteRule]) -> Selection | None:
    netloc = _netloc(meta.url)
    if not netloc:
        return None
    for rule in rules:
        if rule.match.lower() not in netloc:
            continue
        for css in rule.selectors:
            try:
                candidates = soup.select(css)
            except Exception:  # invalid selector string
                continue
            for cand in candidates:
                if _text_len(cand) >= rule.min_chars:
                    return Selection(
                        kind="tag",
                        tag=cand,
                        markdown=None,
                        strategy=f"rule:{rule.name}:{css}",
                    )
    return None


def _try_trafilatura(html_text: str, min_chars: int) -> Selection | None:
    try:
        md = trafilatura.extract(html_text, output_format="markdown")
    except Exception:
        return None
    if md and len(md) >= min_chars:
        return Selection(kind="markdown", tag=None, markdown=md, strategy="trafilatura")
    return None


def select_content(
    soup: BeautifulSoup,
    meta: PageMeta,
    rules: list[SiteRule],
    *,
    html_text: str,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> Selection:
    ruled = _try_rules(soup, meta, rules)
    if ruled:
        return ruled

    fallback = _try_trafilatura(html_text, min_chars)
    if fallback:
        return fallback

    body = soup.body or soup
    return Selection(kind="tag", tag=body, markdown=None, strategy="body")
