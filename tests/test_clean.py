from bs4 import BeautifulSoup

from unmessy.clean import clean


def frag(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_junk_tags_are_removed():
    soup = frag(
        "<div><p>keep</p><script>evil()</script><style>.x{}</style>"
        "<iframe src='x'></iframe><button>click</button><noscript>ns</noscript></div>"
    )
    counts = clean(soup.div)
    assert soup.div.get_text(strip=True) == "keep"
    assert counts["junk"] == 5


def test_chrome_tags_nav_header_footer_aside_removed():
    soup = frag(
        "<div><nav>menu</nav><header>top</header><article><p>real</p></article>"
        "<footer>foot</footer><aside>side</aside></div>"
    )
    counts = clean(soup.div)
    assert soup.div.get_text(strip=True) == "real"
    assert counts["chrome"] == 4


def test_aria_roles_marking_chrome_are_removed():
    soup = frag(
        '<div><div role="navigation">menu</div>'
        '<div role="banner">banner</div><p>content</p>'
        '<div role="contentinfo">info</div></div>'
    )
    counts = clean(soup.div)
    assert soup.div.get_text(strip=True) == "content"
    assert counts["chrome"] == 3


def test_hidden_elements_are_removed():
    soup = frag(
        '<div><p hidden>gone1</p><p aria-hidden="true">gone2</p>'
        '<p style="display:none">gone3</p>'
        '<p style="visibility:hidden">gone4</p><p>visible</p></div>'
    )
    counts = clean(soup.div)
    assert soup.div.get_text(strip=True) == "visible"
    assert counts["hidden"] == 4


def test_screen_reader_only_classes_are_removed():
    soup = frag(
        '<div><a class="sr-only sr-only-focusable" href="#main">Skip to main</a>'
        '<span class="visually-hidden">hint</span><p>visible</p></div>'
    )
    counts = clean(soup.div)
    assert soup.div.get_text(strip=True) == "visible"
    assert counts["hidden"] == 2


def test_visible_content_survives_intact():
    soup = frag(
        "<div><h2>Title</h2><ul><li>a</li><li>b</li></ul>"
        '<p>Read <a href="https://x.org">the docs</a>.</p>'
        "<table><tr><td>cell</td></tr></table></div>"
    )
    clean(soup.div)
    text = soup.div.get_text(" ", strip=True)
    assert "Title" in text and "a b" in text and "the docs" in text and "cell" in text
    assert soup.div.find("a")["href"] == "https://x.org"


def test_empty_containers_are_pruned():
    soup = frag("<div><div><div></div></div><p>text</p><div><span>  </span></div></div>")
    clean(soup.div)
    # Only the <p> and its ancestors remain.
    assert soup.div.get_text(strip=True) == "text"
    assert len(soup.div.find_all("div")) == 0
