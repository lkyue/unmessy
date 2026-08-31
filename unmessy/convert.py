"""Markdown conversion, post-processing and front-matter assembly."""

import re

import yaml
from bs4 import Tag
from markdownify import MarkdownConverter

from unmessy.metadata import PageMeta

CONVERTER = MarkdownConverter(
    heading_style="ATX",
    bullets="-",
    strong_em_symbol="*",
    wrap=False,
)

_EMPTY_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:|#(?:[^)]*))\)")
_DATA_URI_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(data:[^)]*\)")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_DOUBLE_BULLET_RE = re.compile(r"^(\s*)- (?:- )+", re.MULTILINE)


def to_markdown(tag: Tag) -> str:
    return CONVERTER.convert(str(tag))


def postprocess(md: str) -> str:
    # leaked data-URI images (safety net) -> alt placeholder
    md = _DATA_URI_IMAGE_RE.sub(
        lambda m: f"[image: {m.group(1).strip()}]" if m.group(1).strip() else "",
        md,
    )
    # links with no useful href -> plain text
    md = _EMPTY_LINK_RE.sub(r"\1", md)
    # Moodle's nested <li> artifacts: "- - text" -> "- text"
    md = _DOUBLE_BULLET_RE.sub(r"\1- ", md)
    md = md.replace("\xa0", " ")
    md = "\n".join(line.rstrip() for line in md.splitlines())
    md = _BLANK_LINES_RE.sub("\n\n", md)
    return md.strip()


def build_document(body_md: str, meta: PageMeta, strategy: str) -> str:
    import unmessy

    front: dict[str, str] = {"converter": f"unmessy {unmessy.__version__}", "strategy": strategy}
    if meta.title:
        front["title"] = meta.title
    if meta.url:
        front["source"] = meta.url
    if meta.saved_date:
        front["saved"] = meta.saved_date

    fm = yaml.safe_dump(
        front, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).strip()
    return f"---\n{fm}\n---\n\n{body_md.strip()}\n"
