"""Extract page metadata: SingleFile comment (url, saved date) and <title>."""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Comment

_URL_RE = re.compile(r"url:\s*(\S+)")
_SAVED_RE = re.compile(r"saved date:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class PageMeta:
    url: str | None = None
    saved_date: str | None = None
    title: str | None = None


def _parse_singlefile_comment(comment_text: str) -> tuple[str | None, str | None]:
    url_m = _URL_RE.search(comment_text)
    saved_m = _SAVED_RE.search(comment_text)
    return (url_m.group(1) if url_m else None), (saved_m.group(1) if saved_m else None)


def extract_meta(soup: BeautifulSoup) -> PageMeta:
    url = saved = None
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if "Page saved with SingleFile" in comment:
            url, saved = _parse_singlefile_comment(str(comment))
            break

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) or None if title_tag else None

    return PageMeta(url=url, saved_date=saved, title=title)
