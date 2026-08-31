"""Remove non-content elements from a selected subtree."""

from collections import Counter

from bs4 import BeautifulSoup, Tag

JUNK_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "button",
        "form",
        "input",
        "select",
        "textarea",
        "video",
        "audio",
        "canvas",
        "template",
        "object",
        "embed",
        "dialog",
    }
)

CHROME_TAGS = frozenset({"nav", "header", "footer", "aside"})

CHROME_ROLES = frozenset(
    {
        "navigation",
        "banner",
        "contentinfo",
        "complementary",
        "search",
        "menu",
        "menubar",
        "toolbar",
        "dialog",
    }
)

SR_ONLY_CLASSES = frozenset({"sr-only", "sr-only-focusable", "visually-hidden", "d-none"})


def _is_hidden(tag: Tag) -> bool:
    if tag.has_attr("hidden"):
        return True
    if (tag.get("aria-hidden") or "").strip().lower() == "true":
        return True
    style = (tag.get("style") or "").lower()
    if "display:none" in style.replace(" ", "") or "visibility:hidden" in style.replace(" ", ""):
        return True
    classes = set(tag.get("class") or [])
    return bool(classes & SR_ONLY_CLASSES)


def _is_chrome(tag: Tag) -> bool:
    if tag.name in CHROME_TAGS:
        return True
    role = (tag.get("role") or "").strip().lower()
    return role in CHROME_ROLES


def _prune_empty(tag: Tag) -> None:
    """Remove elements that hold no text, no media and no links."""
    for el in list(tag.find_all(True)):
        if el.decomposed:
            continue
        if not el.get_text(strip=True) and el.name not in ("img", "br", "hr", "td", "th"):
            if not el.find(["img", "td", "th"]):
                el.decompose()


def clean(container: Tag) -> Counter:
    counts: Counter = Counter()

    def remove(tag: Tag, category: str) -> None:
        tag.decompose()
        counts[category] += 1

    for tag in list(container.find_all(True)):
        if tag.decomposed or tag is container:
            continue
        if tag.name in JUNK_TAGS:
            remove(tag, "junk")
        elif _is_chrome(tag):
            remove(tag, "chrome")
        elif _is_hidden(tag):
            remove(tag, "hidden")

    _prune_empty(container)
    return counts


def clean_fragment(html: str) -> tuple[BeautifulSoup, Counter]:
    """Convenience: parse a fragment and clean its root element."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    return soup, clean(root)
