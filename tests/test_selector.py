
from bs4 import BeautifulSoup

from unmessy.metadata import PageMeta
from unmessy.selector import SiteRule, default_rules, load_rules, select_content

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat. Duis aute irure dolor in reprehenderit in voluptate."
)


def page(url: str | None, body: str) -> tuple[BeautifulSoup, PageMeta, str]:
    html = f"<html><head><title>t</title></head><body>{body}</body></html>"
    soup = BeautifulSoup(html, "lxml")
    return soup, PageMeta(url=url), html


MOODLE_BODY = (
    '<nav class="navbar">site nav</nav>'
    '<div id="region-main"><h2>Get started</h2>'
    '<p>Welcome to the course. Read <a href="https://isaacscience.org">Isaac</a>.</p>'
    f"<p>{LOREM}</p></div>"
)

RULES = [
    SiteRule(match="vle.cam.ac.uk", name="Moodle", selectors=["#region-main", "[role=main]"]),
    SiteRule(match="sharepoint.com", name="SharePoint", selectors=["#content-canvas"]),
]


def test_rule_match_selects_region_main():
    soup, meta, html = page("https://www.vle.cam.ac.uk/course/section.php?id=1", MOODLE_BODY)
    sel = select_content(soup, meta, RULES, html_text=html)
    assert sel.kind == "tag"
    assert sel.tag.get("id") == "region-main"
    assert sel.strategy.startswith("rule:Moodle")


def test_rule_selector_with_too_little_content_is_skipped():
    body = '<div id="region-main">tiny</div><article><p>' + LOREM + "</p></article>"
    soup, meta, html = page("https://www.vle.cam.ac.uk/x", body)
    sel = select_content(soup, meta, RULES, html_text=html)
    assert sel.strategy != "rule:Moodle:#region-main"


def test_no_rule_match_falls_back_to_trafilatura():
    soup, meta, html = page(
        "https://example.org/blog/post", f"<article><h1>Hi</h1><p>{LOREM}</p></article>"
    )
    sel = select_content(soup, meta, RULES, html_text=html)
    assert sel.kind == "markdown"
    assert sel.strategy == "trafilatura"
    assert "Lorem ipsum" in sel.markdown


def test_garbage_page_ends_at_body_fallback():
    soup, meta, html = page("https://example.org/", "<div><span>x</span></div>")
    sel = select_content(soup, meta, RULES, html_text=html)
    assert sel.kind == "tag"
    assert sel.strategy == "body"
    assert sel.tag.name == "body"


def test_missing_url_skips_rules_entirely():
    soup, meta, html = page(None, f"<article><h1>Hi</h1><p>{LOREM}</p></article>")
    sel = select_content(soup, meta, RULES, html_text=html)
    assert sel.strategy == "trafilatura"


def test_load_rules_parses_yaml(tmp_path):
    yaml_file = tmp_path / "sites.yaml"
    yaml_file.write_text(
        "rules:\n  - match: example.com\n    name: Example\n    selectors:\n      - '#main'\n",
        encoding="utf-8",
    )
    rules = load_rules(yaml_file)
    assert rules == [SiteRule(match="example.com", name="Example", selectors=["#main"])]


def test_load_rules_missing_file_returns_empty(tmp_path):
    assert load_rules(tmp_path / "nope.yaml") == []


def test_default_rules_include_moodle_and_sharepoint():
    rules = default_rules()
    matches = {r.match for r in rules}
    assert "vle.cam.ac.uk" in matches
    assert "sharepoint.com" in matches
