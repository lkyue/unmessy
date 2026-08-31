"""unmessy CLI: batch-convert saved-webpage HTML into clean Markdown."""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from unmessy.clean import clean
from unmessy.convert import build_document, postprocess, to_markdown
from unmessy.images import ImageStats, process_images
from unmessy.metadata import extract_meta
from unmessy.selector import default_rules, load_rules, select_content

_LINK_RE = re.compile(r"\]\((https?://[^)]+)\)")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_HTML_SUFFIXES = {".html", ".htm"}


_SLUG_MAX = 40


def slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.lower()).strip("-") or "page"
    return slug[:_SLUG_MAX].rstrip("-") or "page"


@dataclass
class ConvertResult:
    src: Path
    out: Path
    strategy: str = ""
    chars: int = 0
    links: int = 0
    images: ImageStats = field(default_factory=ImageStats)
    error: str | None = None


def convert_file(
    src: Path,
    outdir: Path,
    rules,
    images_mode: str = "smart",
    also_html: bool = False,
) -> ConvertResult:
    out = outdir / f"{src.stem}.md"
    try:
        html_text = src.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
        if not html_text.strip():
            raise ValueError("file is empty")

        soup = BeautifulSoup(html_text, "lxml")
        meta = extract_meta(soup)
        sel = select_content(soup, meta, rules, html_text=html_text)

        slug = slugify(src.stem)
        stats = ImageStats()
        if sel.kind == "tag":
            region = sel.tag
            clean(region)
            if images_mode == "all":
                stats = process_images(
                    region, outdir / "images", slug, "smart", small_bytes=0, small_px=0
                )
            else:
                stats = process_images(region, outdir / "images", slug, images_mode)
            body_md = postprocess(to_markdown(region))
            if also_html:
                html_out = outdir / f"{src.stem}.clean.html"
                html_out.write_text(str(region), encoding="utf-8")
        else:
            if not sel.markdown:
                raise ValueError("trafilatura returned no content")
            body_md = postprocess(sel.markdown)

        doc = build_document(body_md, meta, sel.strategy)
        outdir.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        return ConvertResult(
            src=src,
            out=out,
            strategy=sel.strategy,
            chars=len(body_md),
            links=len(_LINK_RE.findall(body_md)),
            images=stats,
        )
    except Exception as exc:  # noqa: BLE001 — one bad file must not stop the batch
        return ConvertResult(src=src, out=out, error=f"{type(exc).__name__}: {exc}")


def collect_files(inputs: list[str], outdir: Path) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            for suffix in _HTML_SUFFIXES:
                files.extend(p for p in path.rglob(f"*{suffix}"))
        elif path.suffix.lower() in _HTML_SUFFIXES:
            files.append(path)
        else:
            print(f"skipping (not .html): {path}", file=sys.stderr)
    out_resolved = outdir.resolve()
    unique, seen = [], set()
    for p in sorted(files):
        if out_resolved in p.resolve().parents or p.resolve() in seen:
            continue
        seen.add(p.resolve())
        unique.append(p)
    return unique


def default_outdir(inputs: list[str]) -> Path:
    first = Path(inputs[0]).expanduser().resolve()
    base = first if first.is_dir() else first.parent
    return base / "converted"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unmessy",
        description="Turn messy saved-webpage HTML (SingleFile etc.) into clean, AI-readable Markdown.",
    )
    parser.add_argument("inputs", nargs="+", help="HTML files and/or directories (recursive)")
    parser.add_argument("-o", "--outdir", help="output directory (default: <input dir>/converted)")
    parser.add_argument("--sites", type=Path, help="extra site-rules YAML, tried before built-ins")
    parser.add_argument(
        "--images",
        choices=["smart", "alt", "all", "none"],
        default="smart",
        help="image policy: smart=drop icons, export screenshots (default); alt=placeholders only; "
        "all=export everything; none=discard",
    )
    parser.add_argument(
        "--html", action="store_true", help="also write cleaned HTML next to the .md"
    )
    parser.add_argument("--debug", action="store_true", help="show tracebacks for failed files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    rules = default_rules()
    if args.sites:
        rules = load_rules(args.sites) + rules

    outdir = Path(args.outdir).expanduser() if args.outdir else default_outdir(args.inputs)
    files = collect_files(args.inputs, outdir)
    if not files:
        print("no HTML files found", file=sys.stderr)
        return 1

    failed = 0
    for src in files:
        result = convert_file(src, outdir, rules, images_mode=args.images, also_html=args.html)
        if result.error:
            failed += 1
            print(f"error   {src.name}: {result.error}")
            if args.debug:
                raise SystemExit(result.error)
        else:
            img = f"images +{result.images.exported}/-{result.images.dropped}"
            if result.images.reused:
                img += f" (={result.images.reused} reused)"
            print(
                f"ok      {src.name} -> {result.out.name}  "
                f"[{result.strategy}] {result.chars} chars, {result.links} links, {img}"
            )

    print(f"\n{len(files)} file(s), {failed} failed -> {outdir}")
    return 1 if failed else 0
