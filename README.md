# unmessy

Turn messy-but-viewable saved-webpage HTML (SingleFile, browser "Save As", etc.) into clean, AI-readable, git-friendly Markdown.

A 4 MB SharePoint/Moodle archive page becomes a ~16 KB Markdown file — body text, headings, lists, tables and links fully preserved; navigation menus, embedded styles and other chrome gone.

## How it works

Every file goes through one pipeline:

```
read → parse → extract metadata → locate content (cascade) → clean → images → Markdown → postprocess
```

1. **Metadata**: SingleFile embeds the original URL and save date in a comment at the top of the file. unmessy parses it and writes it into the output's YAML front-matter.
2. **Content location (cascade)**:
   - Match the page URL against site rules (`sites.yaml`) and try their CSS selectors, e.g. Moodle's `#region-main`;
   - No rule hit → fall back to generic main-content extraction via [trafilatura](https://github.com/adbar/trafilatura);
   - Still nothing → clean the whole `<body>`.
   The strategy used is reported per file, so results are auditable.
3. **Cleaning**: removes script/style/iframe/button/nav/footer, hidden elements, and empty containers.
4. **Images (default `smart` policy)**:
   - Icons (< 30 KB or < 200 px) → dropped; a `[image: alt]` placeholder is kept when alt text exists;
   - Content screenshots → base64-decoded and exported to `images/`, deduplicated by content hash, referenced by relative path;
   - Remote images → original URL kept as-is.
5. **Markdown**: markdownify (including pipe tables), then postprocessing (collapse blank lines, fix list artifacts, add front-matter).

## Install

```bash
# The project's own .venv already has everything:
.venv/bin/python -m unmessy --help

# Or install standalone (provides the `unmessy` command):
pip install .
```

Requires Python ≥ 3.10.

## Usage

```bash
# Single file or several
unmessy "Part IA (9_1_2026 12：18：50 AM).html"

# A whole directory (recursively finds .html/.htm)
unmessy ~/saved-pages/

# Custom output directory (default: <input dir>/converted/)
unmessy ~/saved-pages/ -o ~/clean-md/
```

| Option | Description |
|---|---|
| `-o, --outdir` | Output directory (default: `<input dir>/converted/`) |
| `--sites FILE` | Extra site-rules YAML, tried before built-ins |
| `--images {smart,alt,all,none}` | Image policy; default `smart`; `all` = export icons too, `alt` = placeholders only, `none` = drop all |
| `--html` | Also write cleaned semantic HTML (`.clean.html`) |
| `--debug` | Show detailed errors on failure |

A per-file summary (strategy, chars, links, images) is printed at the end; the exit code is 1 if any file failed.

### Example output

```markdown
---
converter: unmessy 0.1.0
strategy: rule:Moodle:#region-main
title: 'Section: Get started with essential first tasks | STEMbridge NST 2026 | Moodle'
source: https://www.vle.cam.ac.uk/course/section.php?id=4558807
saved: Tue Sep 01 2026 00:33:15 GMT+0800
---

## Get set up on Isaac Science

Go to [Isaac Science](https://isaacscience.org/login) and sign in.

1. Log in
2. Join the group
```

## Adding site rules

Edit `unmessy/unmessy/sites.yaml` (or pass your own file via `--sites`):

```yaml
rules:
  - match: vle.cam.ac.uk        # substring of the URL netloc
    name: Moodle
    selectors:                   # tried in order; first one with enough content wins
      - "#region-main"
      - "[role='main']"
    # min_chars: 60             # optional: match threshold, default 60
```

## Development

```bash
.venv/bin/python -m pytest     # 49 unit tests
.venv/bin/ruff check .         # lint
```

```
unmessy/
├── unmessy/
│   ├── cli.py        # batch CLI + summary
│   ├── selector.py   # site-rule matching + cascade
│   ├── clean.py      # junk-element cleaning
│   ├── images.py     # image policy (decode/dedupe/export)
│   ├── convert.py    # markdownify config + postprocess + front-matter
│   ├── metadata.py   # SingleFile comment parsing
│   └── sites.yaml    # built-in site rules
└── tests/
```

## Known trade-offs

- `rowspan`/`colspan` in tables degrade to ragged rows in pipe tables (pipe syntax has no merged cells).
- In `smart` mode, a small but meaningful diagram may be reduced to `[image: alt]` — tune thresholds in `images.py` or use `--images all`.
- No JavaScript is executed: the input is the serialized DOM from SingleFile etc., which is already the rendered state.

## License

MIT
