import base64
import io
import os

from bs4 import BeautifulSoup
from PIL import Image

from unmessy.images import ImageStats, process_images


def make_png(w: int, h: int, noisy: bool = False) -> Image.Image:
    if noisy:
        return Image.frombytes("RGB", (w, h), os.urandom(w * h * 3))
    return Image.new("RGB", (w, h), (200, 200, 200))


def as_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def html_with_img(src: str, alt: str = "") -> BeautifulSoup:
    alt_attr = f' alt="{alt}"' if alt else ""
    return BeautifulSoup(f'<div><p>before</p><img src="{src}"{alt_attr}><p>after</p></div>', "lxml")


def test_smart_small_icon_is_dropped(tmp_path):
    soup = html_with_img(as_data_uri(make_png(20, 20)), alt="logo")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    assert soup.find("img") is None
    assert "[image: logo]" in soup.get_text()
    assert stats.dropped == 1
    assert stats.exported == 0


def test_smart_large_screenshot_is_exported_and_referenced(tmp_path):
    soup = html_with_img(as_data_uri(make_png(300, 200, noisy=True)), alt="login steps")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    img = soup.find("img")
    assert img is not None
    assert img["src"] == "images/page-1.png"
    assert (tmp_path / "images" / "page-1.png").exists()
    assert stats.exported == 1


def test_identical_images_are_deduplicated(tmp_path):
    uri = as_data_uri(make_png(300, 200, noisy=True))
    soup = html_with_img(uri)
    soup.div.append(BeautifulSoup(f'<img src="{uri}" alt="again">', "lxml").img)
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    srcs = [img["src"] for img in soup.find_all("img")]
    assert srcs[0] == srcs[1] == "images/page-1.png"
    assert len(list((tmp_path / "images").iterdir())) == 1
    assert stats.exported == 1
    assert stats.reused == 1


def test_tiny_bytes_are_dropped_even_if_pixel_dimensions_are_large(tmp_path):
    # 300x300 uniform image encodes to ~1KB: the byte threshold catches it.
    soup = html_with_img(as_data_uri(make_png(300, 300)), alt="")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    assert soup.find("img") is None
    assert stats.dropped == 1
    assert stats.exported == 0


def test_small_pixel_dimensions_are_dropped_even_if_bytes_are_large(tmp_path):
    # 199x199 random noise encodes to ~85KB: only the dimension threshold
    # (<200px) can classify it as an icon.
    soup = html_with_img(as_data_uri(make_png(199, 199, noisy=True)), alt="")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    assert soup.find("img") is None
    assert stats.dropped == 1
    assert stats.exported == 0


def test_remote_http_image_is_left_untouched(tmp_path):
    soup = html_with_img("https://example.org/pic.png", alt="remote")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    img = soup.find("img")
    assert img["src"] == "https://example.org/pic.png"
    assert stats.exported == 0 and stats.dropped == 0


def test_alt_mode_keeps_only_placeholder(tmp_path):
    soup = html_with_img(as_data_uri(make_png(300, 200, noisy=True)), alt="chart")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="alt")
    assert soup.find("img") is None
    assert "[image: chart]" in soup.get_text()
    assert not (tmp_path / "images").exists()
    assert stats.dropped == 1


def test_none_mode_removes_everything_silently(tmp_path):
    soup = html_with_img(as_data_uri(make_png(300, 200, noisy=True)), alt="chart")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="none")
    assert soup.find("img") is None
    assert "[image:" not in soup.get_text()
    assert stats.dropped == 1


def test_corrupt_data_uri_is_dropped_without_crash(tmp_path):
    soup = html_with_img("data:image/png;base64,!!!not-base64!!!", alt="broken")
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    assert soup.find("img") is None
    assert stats.dropped == 1


def test_jpeg_mime_maps_to_jpg_extension(tmp_path):
    buf = io.BytesIO()
    make_png(300, 200, noisy=True).save(buf, format="JPEG")
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    soup = html_with_img(uri)
    stats = process_images(soup.div, tmp_path / "images", "page", mode="smart")
    assert soup.find("img")["src"] == "images/page-1.jpg"
    assert stats.exported == 1


def test_stats_object_shape():
    assert ImageStats().exported == 0
    assert ImageStats().dropped == 0
    assert ImageStats().reused == 0
