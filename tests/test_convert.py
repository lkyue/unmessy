from bs4 import BeautifulSoup
import yaml

from unmessy.convert import build_document, postprocess, to_markdown
from unmessy.metadata import PageMeta


def test_headings_links_lists_convert():
    soup = BeautifulSoup(
        "<h2>Get started</h2>"
        '<p>Read <a href="https://isaacscience.org">Isaac</a> first.</p>'
        "<ol><li>one</li><li>two</li></ol>"
        "<p><strong>bold</strong> and <em>ital</em></p>",
        "lxml",
    )
    md = to_markdown(soup)
    assert "## Get started" in md
    assert "[Isaac](https://isaacscience.org)" in md
    assert "1. one" in md and "2. two" in md
    assert "**bold**" in md and "*ital*" in md


def test_tables_become_pipe_tables():
    soup = BeautifulSoup(
        "<table><tr><th>Name</th><th>N</th></tr><tr><td>alpha</td><td>1</td></tr></table>",
        "lxml",
    )
    md = to_markdown(soup)
    assert "| Name | N |" in md
    assert "| --- | --- |" in md
    assert "| alpha | 1 |" in md


def test_empty_and_anchor_only_links_are_unwrapped():
    soup = BeautifulSoup(
        '<p><a href="">plain</a> and <a href="#module-1">anchored</a> '
        'and <a href="https://real.org">real</a>.</p>',
        "lxml",
    )
    md = postprocess(to_markdown(soup))
    assert "plain and anchored and [real](https://real.org)." in md


def test_postprocess_collapses_excess_blank_lines():
    md = postprocess("para one\n\n\n\n\npara two")
    assert md == "para one\n\npara two"


def test_postprocess_strips_leaked_data_uri_images():
    md = postprocess(
        "text ![logo](data:image/png;base64,AAAA) more ![chart](data:image/png;base64,BBBB)"
    )
    assert "data:" not in md
    assert "[image: logo]" in md
    assert "[image: chart]" in md


def test_postprocess_normalises_nbsp_and_trailing_whitespace():
    md = postprocess("a\xa0b   \nc   ")
    assert md == "a b\nc"


def test_build_document_emits_yaml_frontmatter():
    meta = PageMeta(
        url="https://www.vle.cam.ac.uk/course/section.php?id=1",
        saved_date="Tue Sep 01 2026 00:33:15 GMT+0800",
        title="Section: Get started | Moodle",
    )
    doc = build_document("# Hello\n\nbody", meta, "rule:Moodle:#region-main")
    assert doc.startswith("---\n")
    fm_text = doc.split("\n---\n", 1)[0].removeprefix("---\n")
    fm = yaml.safe_load(fm_text)
    assert fm["source"] == "https://www.vle.cam.ac.uk/course/section.php?id=1"
    assert fm["title"] == "Section: Get started | Moodle"
    assert fm["saved"] == "Tue Sep 01 2026 00:33:15 GMT+0800"
    assert fm["strategy"] == "rule:Moodle:#region-main"
    assert fm["converter"].startswith("unmessy ")
    assert "\n# Hello" in doc


def test_build_document_tolerates_missing_meta():
    doc = build_document("body text", PageMeta(), "body")
    assert "source:" not in doc
    assert "strategy: body" in doc
    assert doc.endswith("body text\n")


def test_postprocess_collapses_double_list_markers():
    assert postprocess("- - nested item") == "- nested item"
    assert postprocess("intro\n  - - deep item") == "intro\n  - deep item"
    assert postprocess("- normal") == "- normal"
