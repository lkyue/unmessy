import base64
import io
import os

import pytest
from PIL import Image


def make_png(w: int, h: int, noisy: bool = False) -> Image.Image:
    if noisy:
        return Image.frombytes("RGB", (w, h), os.urandom(w * h * 3))
    return Image.new("RGB", (w, h), (200, 200, 200))


def as_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def moodle_page_factory(tmp_path):
    """Write a Moodle-like SingleFile page and return its path."""

    def _write(name: str = "moodle page.html", with_image: bool = False) -> "object":
        big_img = (
            f'<img alt="login steps" src="{as_data_uri(make_png(300, 200, noisy=True))}">'
            if with_image
            else ""
        )
        html = (
            "<!DOCTYPE html><html lang=en>"
            "<!--\n Page saved with SingleFile\n"
            " url: https://www.vle.cam.ac.uk/course/section.php?id=4558807\n"
            " saved date: Tue Sep 01 2026 00:33:15 GMT+0800 (China Standard Time)\n-->"
            "<head><title>Section: Get started | Moodle</title>"
            "<style>.huge{color:red}</style></head>"
            '<body class="path-course">'
            '<nav aria-label="Site navigation"><a href="https://www.vle.cam.ac.uk/">Home</a></nav>'
            '<div id="region-main">'
            "<h2>Get set up on Isaac Science</h2>"
            "<p>Go to <a href='https://isaacscience.org/login'>Isaac Science</a> and sign in.</p>"
            "<ol><li>Log in</li><li>Join the group</li></ol>"
            f"<p>{big_img}</p>"
            "<table><tr><th>Step</th><th>Who</th></tr><tr><td>1</td><td>you</td></tr></table>"
            "</div>"
            "<footer>legal blah</footer>"
            "</body></html>"
        )
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return path

    return _write
