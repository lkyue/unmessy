"""Image handling: decode/export/dedupe data-URI images per policy.

Modes:
  smart — drop icons (small bytes or small pixels), export real screenshots
  alt   — drop everything, keep an ``[image: alt]`` placeholder when possible
  none  — drop everything silently
  (remote http(s) images are always left untouched)
"""

import base64
import binascii
import dataclasses
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from bs4 import NavigableString, Tag
from PIL import Image, UnidentifiedImageError

DEFAULT_SMALL_BYTES = 30_000
DEFAULT_SMALL_PX = 200

_MIME_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "webp": "webp",
    "gif": "gif",
    "bmp": "bmp",
    "svg+xml": "svg",
}


@dataclass
class ImageStats:
    exported: int = 0
    dropped: int = 0
    reused: int = 0

    def add(self, other: "ImageStats") -> "ImageStats":
        return ImageStats(
            exported=self.exported + other.exported,
            dropped=self.dropped + other.dropped,
            reused=self.reused + other.reused,
        )


def _placeholder(img: Tag) -> None:
    alt = (img.get("alt") or "").strip()
    if alt:
        img.replace_with(NavigableString(f"[image: {alt}]"))
    else:
        img.decompose()


def _export(
    raw: bytes,
    ext: str,
    images_dir: Path,
    slug: str,
    by_hash: dict[str, str],
) -> tuple[str, bool]:
    """Return (relative src, was_new)."""
    digest = hashlib.sha1(raw).hexdigest()
    if digest in by_hash:
        return by_hash[digest], False
    fname = f"{slug}-{len(by_hash) + 1}.{ext}"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / fname).write_bytes(raw)
    rel = f"images/{fname}"
    by_hash[digest] = rel
    return rel, True


def _handle_data_uri(
    img: Tag,
    src: str,
    images_dir: Path,
    slug: str,
    mode: str,
    small_bytes: int,
    small_px: int,
    by_hash: dict[str, str],
) -> ImageStats:
    stats = ImageStats()

    def drop() -> ImageStats:
        _placeholder(img)
        stats.dropped += 1
        return stats

    if mode == "alt":
        return drop()

    header, _, payload = src.partition(",")
    mime = header.removeprefix("data:").split(";", 1)[0]
    if not mime.startswith("image/") or not payload:
        return drop()
    ext = _MIME_EXT.get(mime.removeprefix("image/"))
    if ext is None:
        return drop()

    try:
        raw = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError):
        return drop()

    if ext == "svg":
        # SVGs are UI icons in practice; keep only genuinely large ones.
        if len(raw) < small_bytes:
            return drop()
    else:
        try:
            with Image.open(io.BytesIO(raw)) as im:
                width, height = im.size
        except (UnidentifiedImageError, OSError, ValueError):
            return drop()
        if len(raw) < small_bytes or max(width, height) < small_px:
            return drop()

    rel, is_new = _export(raw, ext, images_dir, slug, by_hash)
    img["src"] = rel
    if is_new:
        stats.exported += 1
    else:
        stats.reused += 1
    return stats


def process_images(
    container: Tag,
    images_dir: Path,
    slug: str,
    mode: str = "smart",
    *,
    small_bytes: int = DEFAULT_SMALL_BYTES,
    small_px: int = DEFAULT_SMALL_PX,
) -> ImageStats:
    if mode == "none":
        stats = ImageStats()
        for img in container.find_all("img"):
            img.decompose()
            stats.dropped += 1
        return stats

    by_hash: dict[str, str] = {}
    stats = ImageStats()
    for img in container.find_all("img"):
        src = (img.get("src") or "").strip()
        if src.startswith(("http://", "https://")):
            continue
        if src.startswith("data:"):
            stats = stats.add(
                _handle_data_uri(img, src, images_dir, slug, mode, small_bytes, small_px, by_hash)
            )
        else:
            # Relative/unknown src: drop it — it cannot resolve from Markdown.
            _placeholder(img)
            stats.dropped += 1
    return stats


def merge_stats(*stats: ImageStats) -> ImageStats:
    out = ImageStats()
    for s in stats:
        out = dataclasses.replace(
            out,
            exported=out.exported + s.exported,
            dropped=out.dropped + s.dropped,
            reused=out.reused + s.reused,
        )
    return out
