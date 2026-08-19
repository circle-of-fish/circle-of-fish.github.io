#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the Circle of the Fish site.

Content lives in data/*.json as {"en": ..., "ko": ..., "zh": ..., "ja": ...}
bundles; every page of every language is rendered from the same records, so a
citation is written once and appears in four languages.  Output goes to the
repository root (en) and ko/, zh/, ja/ so that a <name>.github.io repo serves
it with no further configuration.

    python build.py            # build everything
    python build.py --serve    # build, then serve at http://localhost:8000
"""
from __future__ import annotations

import argparse
import http.server
import json
import re
import shutil
import socketserver
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
OUT = ROOT / "docs"

LANGS = ["en", "ko", "zh", "ja"]
LANG_NAMES = {"en": "EN", "ko": "한국어", "zh": "中文", "ja": "日本語"}
HTML_LANG = {"en": "en", "ko": "ko", "zh": "zh-Hans", "ja": "ja"}

# Google Fonts: Latin faces everywhere, plus the CJK pair the page actually needs.
FONT_FAMILIES = "family=Inter:wght@300;400;500;600;700&family=Spectral:ital,wght@0,400;0,500;0,600;1,400"
CJK_FONTS = {
    "en": ("", "", ""),
    "ko": ("&family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;600;700",
           "'Noto Sans KR'", "'Noto Serif KR'"),
    "zh": ("&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@400;600;700",
           "'Noto Sans SC'", "'Noto Serif SC'"),
    "ja": ("&family=Noto+Sans+JP:wght@300;400;500;700&family=Noto+Serif+JP:wght@400;600;700",
           "'Noto Sans JP'", "'Noto Serif JP'"),
}
# English pages still have to render Korean/Chinese/Japanese titles in citations.
CJK_FALLBACK = "'Noto Sans KR', 'Noto Sans SC', 'Noto Sans JP', 'Malgun Gothic', 'Microsoft YaHei', 'Yu Gothic'"

PAGES = [
    # (slug, output filename, nav key)
    ("index", "index.html", "home"),
    ("about", "about.html", "about"),
    ("research", "research.html", "research"),
    ("members", "members.html", "members"),
    ("publications", "publications.html", "publications"),
    ("seminars", "seminars.html", "seminars"),
    ("resources", "resources.html", "resources"),
]

BASE_URL = "https://circle-of-fish.github.io"


# --------------------------------------------------------------------------- #
# data loading                                                                 #
# --------------------------------------------------------------------------- #
def load(name: str) -> dict:
    path = DATA / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"missing data file: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def t(value, lang: str):
    """Resolve an i18n bundle for `lang`, falling back to English.

    Accepts a bare string (same in every language), a {lang: ...} bundle, or a
    list/dict containing either; recurses so whole records can be resolved at
    once.
    """
    if isinstance(value, dict):
        # every bundle carries "en" as the fallback; a dict merely keyed by
        # language codes (e.g. a lookup table) is not a bundle
        if "en" in value and all(not isinstance(v, (dict, list)) or k in LANGS
                                 for k, v in value.items()):
            picked = value.get(lang)
            if picked in (None, ""):
                picked = value.get("en", "")
            return t(picked, lang) if isinstance(picked, (dict, list)) else picked
        return {k: t(v, lang) for k, v in value.items()}
    if isinstance(value, list):
        return [t(v, lang) for v in value]
    return value


# --------------------------------------------------------------------------- #
# jinja filters                                                                #
# --------------------------------------------------------------------------- #
def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", str(s).lower())
    return re.sub(r"[\s_]+", "-", s).strip("-") or "x"


def domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).replace("www.", "") if m else ""


def doi_url(doi: str) -> str:
    doi = (doi or "").strip()
    if not doi:
        return ""
    if doi.startswith("http"):
        return doi
    return "https://doi.org/" + doi.removeprefix("doi:").strip()


# --------------------------------------------------------------------------- #
# build                                                                        #
# --------------------------------------------------------------------------- #
def build() -> None:
    site = load("site")
    members = load("members")
    research = load("research")
    publications = load("publications")
    seminars = load("seminars")
    resources = load("resources")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )
    env.filters["slugify"] = slugify
    env.filters["domain"] = domain
    env.filters["doi_url"] = doi_url

    # Windows keeps a handle on any directory a running preview server has open,
    # so deleting the tree is best-effort: unlink what we can, overwrite the rest.
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(OUT.rglob("*"), key=lambda q: -len(q.parts)):
        try:
            path.unlink() if path.is_file() else path.rmdir()
        except OSError:
            pass

    # assets sit at the site root; every page reaches them through `prefix`
    for asset in ASSETS.iterdir():
        if asset.is_file():
            shutil.copy2(asset, OUT / asset.name)
        else:
            shutil.copytree(asset, OUT / asset.name)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "CNAME").unlink(missing_ok=True)

    written = []
    for lang in LANGS:
        subdir = OUT if lang == "en" else OUT / lang
        subdir.mkdir(parents=True, exist_ok=True)
        prefix = "" if lang == "en" else "../"

        cjk_link, cjk_sans, cjk_serif = CJK_FONTS[lang]
        ctx_common = {
            "lang": lang,
            "html_lang": HTML_LANG[lang],
            "langs": LANGS,
            "lang_names": LANG_NAMES,
            "prefix": prefix,
            "base_url": BASE_URL,
            "font_href": f"https://fonts.googleapis.com/css2?{FONT_FAMILIES}{cjk_link}&display=swap",
            "cjk_sans": ", ".join(x for x in [cjk_sans, CJK_FALLBACK] if x),
            "cjk_serif": cjk_serif or "'Noto Serif KR', Georgia",
            "site": t(site, lang),
            "site_raw": site,
            "members": t(members, lang),
            "research": t(research, lang),
            "publications": t(publications, lang),
            "seminars": t(seminars, lang),
            "resources": t(resources, lang),
            "pages": PAGES,
        }

        for slug, filename, navkey in PAGES:
            tpl = env.get_template(f"{slug}.html.j2")
            html = tpl.render(**ctx_common, page=navkey, page_file=filename)
            (subdir / filename).write_text(html, encoding="utf-8")
            written.append(str((subdir / filename).relative_to(OUT)).replace("\\", "/"))

    # sitemap + robots
    urls = "\n".join(
        f"  <url><loc>{BASE_URL}/{p}</loc></url>" for p in written
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8"
    )

    print(f"built {len(written)} pages into {OUT}")
    for p in written:
        print(f"  {p}")


def serve(port: int = 8000) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(OUT), **kw)

        def log_message(self, fmt, *args):  # quieter console
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"serving {OUT} at http://localhost:{port}/  (ctrl-c to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="serve after building")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    build()
    if args.serve:
        serve(args.port)
