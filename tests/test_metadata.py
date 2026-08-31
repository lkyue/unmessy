from bs4 import BeautifulSoup

from unmessy.metadata import PageMeta, extract_meta

SINGLEFILE_HTML = """<!DOCTYPE html><html lang=en-US>
<!--
 Page saved with SingleFile
 url: https://www.vle.cam.ac.uk/course/section.php?id=4558807
 saved date: Tue Sep 01 2026 00:33:15 GMT+0800 (China Standard Time)
-->
<head><title>Section: Get started | Moodle</title></head>
<body><p>hello</p></body></html>"""


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_parses_singlefile_comment_url_and_date_and_title():
    meta = extract_meta(soup_of(SINGLEFILE_HTML))
    assert meta.url == "https://www.vle.cam.ac.uk/course/section.php?id=4558807"
    assert meta.saved_date == "Tue Sep 01 2026 00:33:15 GMT+0800 (China Standard Time)"
    assert meta.title == "Section: Get started | Moodle"


def test_page_without_singlefile_comment_yields_none_url_and_date():
    html = "<html><head><title>Just a page</title></head><body></body></html>"
    meta = extract_meta(soup_of(html))
    assert meta.url is None
    assert meta.saved_date is None
    assert meta.title == "Just a page"


def test_page_without_title_is_tolerated():
    html = "<html><body><p>no head at all</p></body></html>"
    meta = extract_meta(soup_of(html))
    assert isinstance(meta, PageMeta)
    assert meta.title is None
    assert meta.url is None


def test_singlefile_comment_is_found_even_when_relocated_into_head():
    # SingleFile places the comment right after <!DOCTYPE html>; the parser
    # may relocate it inside <head> — it must be found either way.
    html = (
        "<html><head>"
        "<!-- Page saved with SingleFile"
        " url: https://example.org/page"
        " saved date: Tue Sep 01 2026 -->"
        "</head><body></body></html>"
    )
    meta = extract_meta(soup_of(html))
    assert meta.url == "https://example.org/page"
    assert meta.saved_date == "Tue Sep 01 2026"
