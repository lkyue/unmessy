
from unmessy.cli import convert_file, main
from unmessy.selector import default_rules

RULES = default_rules()


def test_convert_file_extracts_moodle_region_and_exports_images(tmp_path, moodle_page_factory):
    src = moodle_page_factory(with_image=True)
    result = convert_file(src, tmp_path / "out", RULES)
    assert result.error is None
    assert result.strategy.startswith("rule:Moodle")
    md = result.out.read_text(encoding="utf-8")
    assert md.startswith("---\n")
    assert "## Get set up on Isaac Science" in md
    assert "[Isaac Science](https://isaacscience.org/login)" in md
    assert "| Step | Who |" in md
    assert "1. Log in" in md
    assert "footer" not in md.lower() or "legal" not in md
    assert "images/" in md  # exported screenshot referenced
    assert result.images.exported == 1
    exported = list((tmp_path / "out" / "images").glob("*.png"))
    assert len(exported) == 1


def test_convert_file_default_images_mode_drops_icons(tmp_path):
    from tests.conftest import as_data_uri, make_png

    src = tmp_path / "icons.html"
    icon_uri = as_data_uri(make_png(16, 16))
    src.write_text(
        "<!-- Page saved with SingleFile\n url: https://www.vle.cam.ac.uk/course/x -->\n"
        f"<main><h1>Hi</h1><div id='region-main'><p>{'word ' * 60}</p>"
        f"<img alt='dot' src='{icon_uri}'></div></main>",
        encoding="utf-8",
    )
    result = convert_file(src, tmp_path / "out", RULES)
    assert result.error is None
    assert result.strategy.startswith("rule:Moodle")
    assert result.images.dropped == 1
    md = result.out.read_text(encoding="utf-8")
    assert "data:" not in md
    assert "[image: dot]" in md


def test_convert_file_generic_page_uses_trafilatura(tmp_path, moodle_page_factory):
    src = tmp_path / "plain.html"
    body = (
        "<article><h1>Some Article</h1><p>"
        + ("lorem ipsum dolor sit amet " * 30)
        + "</p></article>"
    )
    src.write_text(
        "<!-- Page saved with SingleFile\n url: https://blog.example.org/post-1 -->\n"
        f"<body>{body}</body>",
        encoding="utf-8",
    )
    result = convert_file(src, tmp_path / "out", RULES)
    assert result.error is None
    assert result.strategy == "trafilatura"
    assert "lorem ipsum" in result.out.read_text(encoding="utf-8")


def test_convert_file_reports_error_on_unreadable_input(tmp_path):
    src = tmp_path / "empty.html"
    src.write_text("", encoding="utf-8")
    result = convert_file(src, tmp_path / "out", RULES)
    assert result.error is not None


def test_main_batch_converts_and_prints_summary(tmp_path, capsys, moodle_page_factory):
    page_a = moodle_page_factory("a.html")
    page_b = moodle_page_factory("b.html", with_image=False)
    rc = main([str(page_a), str(page_b), "-o", str(tmp_path / "out")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "a.md" in out or "a" in out
    assert "rule:Moodle" in out
    assert (tmp_path / "out" / "a.md").exists()
    assert (tmp_path / "out" / "b.md").exists()


def test_main_returns_nonzero_when_a_file_fails(tmp_path, capsys):
    (tmp_path / "empty.html").write_text("", encoding="utf-8")
    (tmp_path / "bad.html").write_text("\x00\x01\x02 not html at all", encoding="utf-8")
    rc = main(
        [str(tmp_path / "empty.html"), str(tmp_path / "bad.html"), "-o", str(tmp_path / "out")]
    )
    assert rc == 1
    assert "error" in capsys.readouterr().out.lower()


def test_main_directory_input_processes_html_files_and_skips_outdir(
    tmp_path, capsys, moodle_page_factory
):
    moodle_page_factory("inside/one.html")
    (tmp_path / "inside" / "notes.txt").write_text("ignore me", encoding="utf-8")
    rc = main([str(tmp_path / "inside")])  # no -o: defaults to <dir>/converted
    assert rc == 0
    assert (tmp_path / "inside" / "converted" / "one.md").exists()
    assert not (tmp_path / "inside" / "converted" / "notes.md").exists()


def test_main_custom_sites_rule_takes_precedence(tmp_path, capsys):
    sites = tmp_path / "sites.yaml"
    sites.write_text(
        "rules:\n  - match: example.org\n    name: Custom\n    selectors:\n      - 'article'\n",
        encoding="utf-8",
    )
    body = "<article><h1>Custom Region</h1><p>" + ("content word " * 40) + "</p></article>"
    src = tmp_path / "page.html"
    src.write_text(
        f"<!-- Page saved with SingleFile\n url: https://example.org/x -->\n<body>{body}</body>",
        encoding="utf-8",
    )
    rc = main([str(src), "-o", str(tmp_path / "out"), "--sites", str(sites)])
    assert rc == 0
    assert "rule:Custom" in capsys.readouterr().out


def test_images_all_mode_exports_even_icons(tmp_path):
    from tests.conftest import as_data_uri, make_png

    src = tmp_path / "icons.html"
    src.write_text(
        "<!-- Page saved with SingleFile\n url: https://www.vle.cam.ac.uk/course/x -->\n"
        f"<main><h1>Hi</h1><div id='region-main'><p>{'word ' * 60}</p>"
        f"<img alt='dot' src='{as_data_uri(make_png(16, 16))}'></div></main>",
        encoding="utf-8",
    )
    result = convert_file(src, tmp_path / "out", RULES, images_mode="all")
    assert result.images.exported == 1


def test_exported_image_filenames_are_short(tmp_path, moodle_page_factory):
    src = moodle_page_factory(
        "a-really-quite-long-course-section-title-2026-09-01-with-timestamp.html",
        with_image=True,
    )
    result = convert_file(src, tmp_path / "out", RULES)
    assert result.error is None
    exported = list((tmp_path / "out" / "images").iterdir())
    assert len(exported) == 1
    assert len(exported[0].stem) <= 50
