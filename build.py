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
import datetime
import hashlib
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
# The site is published straight from the repository root, the way a
# <name>.github.io repo is served with no Pages configuration at all. Source
# directories live alongside the output, so cleaning has to be explicit about
# what it may delete — see generated_paths().
OUT = ROOT

LANGS = ["en", "ko", "zh", "ja"]
LANG_NAMES = {"en": "EN", "ko": "한국어", "zh": "中文", "ja": "日本語"}
HTML_LANG = {"en": "en", "ko": "ko", "zh": "zh-Hans", "ja": "ja"}
OG_LOCALE = {"en": "en_US", "ko": "ko_KR", "zh": "zh_CN", "ja": "ja_JP"}

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

# Flip to True to pull the whole site back out of search engines.
NOINDEX = False

# Everything in the repository is served, including the sources the site is
# built from. Crawlers should spend their budget on pages, not on templates.
CRAWL_DISALLOW = ["/admin/", "/assets/", "/data/", "/templates/", "/_build/",
                  "/worker/", "/research/", "/.github/"]


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


def memberkey(key: str) -> str:
    """The research dossier keys members with underscores; the site uses hyphens."""
    return str(key).replace("_", "-")


def doi_url(doi: str) -> str:
    doi = (doi or "").strip()
    if not doi:
        return ""
    if doi.startswith("http"):
        return doi
    return "https://doi.org/" + doi.removeprefix("doi:").strip()


def stamp_admin_assets() -> None:
    """Version the editor's own script and stylesheet by content.

    The editor changes far more often than the site, and a browser holding a
    ten-minute-old copy of it looks like a broken feature rather than a stale
    cache. Its markup ships with `?v=DEV`, which is replaced here by a digest of
    what it actually loads, so a changed file is always a changed URL.
    """
    page = OUT / "admin" / "index.html"
    if not page.exists():
        return
    digest = hashlib.sha1()
    for name in ("admin.css", "admin.js"):
        asset = OUT / "admin" / name
        if asset.exists():
            # Windows checks these out with CRLF and the Actions runner with LF,
            # so hashing the raw bytes gives two digests for one file and the
            # stamp flips back and forth on every build. Normalise first.
            digest.update(asset.read_bytes().replace(b"\r\n", b"\n"))
    page.write_text(page.read_text(encoding="utf-8").replace("v=DEV", "v=" + digest.hexdigest()[:10]),
                    encoding="utf-8")


def json_ld(page: str, lang: str, ctx: dict) -> str:
    """Structured data, so a search engine reads this as a research group.

    Only facts already on the page go in here — names, affiliations, citations.
    Nothing is asserted that a reader could not check against the page itself.
    """
    site, base = ctx["site"], BASE_URL
    here = f"{base}/{'' if lang == 'en' else lang + '/'}{ctx['page_file']}"
    graph: list[dict] = []

    org = {
        "@type": "Organization",
        "@id": f"{base}/#organization",
        "name": site["title"],
        "alternateName": ["Circle of the Fish", "복어회", "河豚会", "河豚の会"],
        "url": base + "/",
        "description": site["meta_description"],
        "foundingDate": "2020-06",
        "logo": f"{base}/favicon.svg",
        "image": f"{base}/share-card.png",
        "knowsAbout": [
            "International Relations theory", "Global IR",
            "Historical East Asian international orders", "Interpolity order",
            "Korean foreign policy", "History of international law",
        ],
    }

    if page == "home":
        graph.append(org)
        graph.append({
            "@type": "WebSite",
            "@id": f"{base}/#website",
            "url": base + "/",
            "name": site["title"],
            "inLanguage": HTML_LANG[lang],
            "publisher": {"@id": f"{base}/#organization"},
        })
    elif page == "members":
        graph.append({
            "@type": "CollectionPage", "@id": here, "url": here,
            "name": ctx["members"]["title"], "isPartOf": {"@id": f"{base}/#website"},
            "about": {"@id": f"{base}/#organization"},
            "mainEntity": {
                "@type": "ItemList",
                "itemListElement": [
                    {
                        "@type": "ListItem", "position": i + 1,
                        "item": {k: v for k, v in {
                            "@type": "Person",
                            "name": m["name"],
                            "alternateName": m.get("name_alt"),
                            "affiliation": {"@type": "Organization", "name": m["affiliation"]},
                            "url": next((l["url"] for l in m.get("links", [])
                                         if l["label"] in ("Website", "Faculty page")), None),
                            "sameAs": [l["url"] for l in m.get("links", [])] or None,
                            "memberOf": {"@id": f"{base}/#organization"},
                        }.items() if v},
                    }
                    for i, m in enumerate(ctx["members"]["people"])
                ],
            },
        })
    elif page == "publications":
        pubs = [e for g in ctx["publications"]["themes"] + ctx["publications"]["other_groups"]
                for e in g["entries"]]
        kinds = {"book": "Book", "book_chapter": "Chapter", "edited_volume": "Book",
                 "dissertation": "Thesis"}
        graph.append({
            "@type": "CollectionPage", "@id": here, "url": here,
            "name": ctx["publications"]["title"], "isPartOf": {"@id": f"{base}/#website"},
            "mainEntity": {
                "@type": "ItemList", "numberOfItems": len(pubs),
                "itemListElement": [
                    {
                        "@type": "ListItem", "position": i + 1,
                        "item": {k: v for k, v in {
                            "@type": kinds.get(p.get("type"), "ScholarlyArticle"),
                            "headline": re.sub(r"<[^>]+>", "", str(p.get("title", ""))),
                            "author": p.get("authors"),
                            "datePublished": (p.get("year")
                                              if str(p.get("year", "")).isdigit() else None),
                            "isPartOf": ({"@type": "Periodical",
                                          "name": re.sub(r"<[^>]+>", "", str(p["venue"]))}
                                         if p.get("venue") else None),
                            "identifier": (doi_url(p["doi"]) if p.get("doi") else None),
                            "url": p.get("url_fulltext") or p.get("url_publisher") or None,
                            "abstract": p.get("summary"),
                            "inLanguage": p.get("language"),
                        }.items() if v},
                    }
                    for i, p in enumerate(pubs)
                ],
            },
        })
    else:
        graph.append({
            "@type": "WebPage", "@id": here, "url": here,
            "name": ctx["site"]["nav"][page],
            "isPartOf": {"@id": f"{base}/#website"},
            "about": {"@id": f"{base}/#organization"},
            "inLanguage": HTML_LANG[lang],
        })

    payload = {"@context": "https://schema.org", "@graph": graph}
    # a literal </script> inside JSON would end the tag early
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def generated_paths() -> list[Path]:
    """Every path a build writes — and the only paths a build may delete."""
    out = [OUT / "sitemap.xml", OUT / "robots.txt", OUT / ".nojekyll", OUT / "404.html"]
    out += [OUT / a.name for a in ASSETS.iterdir()]      # files and asset folders alike
    for _, filename, _ in PAGES:
        out.append(OUT / filename)
        for lang in LANGS[1:]:
            out.append(OUT / lang / filename)
    out += [OUT / lang for lang in LANGS[1:]]
    return out


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
    env.filters["memberkey"] = memberkey

    # Only ever remove what a previous build wrote. Windows also keeps a handle
    # on any directory a running preview server has open, so removal is
    # best-effort and the write below overwrites whatever survives.
    for path in sorted(generated_paths(), key=lambda q: -len(q.parts)):
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path) if path.name not in LANGS else path.rmdir()
        except OSError:
            pass

    # assets sit at the site root; every page reaches them through `prefix`
    for asset in ASSETS.iterdir():
        if asset.is_file():
            shutil.copy2(asset, OUT / asset.name)
        else:
            # cleaning above is best-effort — Windows can hold a directory handle
            # open — so the copy has to be able to write over what survived
            shutil.copytree(asset, OUT / asset.name, dirs_exist_ok=True)
    stamp_admin_assets()
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
            "lang_codes": HTML_LANG,
            "og_locale": OG_LOCALE[lang],
            "og_locales": OG_LOCALE,
            "langs": LANGS,
            "lang_names": LANG_NAMES,
            "prefix": prefix,
            "base_url": BASE_URL,
            "noindex": NOINDEX,
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

        pub_members = {m for g in ctx_common["publications"]["themes"]
                       + ctx_common["publications"]["other_groups"]
                       for e in g["entries"] for m in e.get("members", [])}
        ctx_common["publishing_members"] = [
            m for m in ctx_common["members"]["people"]
            if m["key"].replace("-", "_") in pub_members
        ]

        for slug, filename, navkey in PAGES:
            tpl = env.get_template(f"{slug}.html.j2")
            ctx = dict(ctx_common, page=navkey, page_file=filename)
            ctx["json_ld"] = json_ld(navkey, lang, ctx)
            html = tpl.render(**ctx)
            (subdir / filename).write_text(html, encoding="utf-8")
            written.append(str((subdir / filename).relative_to(OUT)).replace("\\", "/"))

    # GitHub Pages serves /404.html for any address it cannot find, whatever the
    # language, so this one is English and stays out of the sitemap.
    (OUT / "404.html").write_text(
        env.get_template("404.html.j2").render(
            site=t(site, "en"), pages=PAGES,
            font_href=f"https://fonts.googleapis.com/css2?{FONT_FAMILIES}&display=swap"),
        encoding="utf-8")

    # One sitemap entry per page per language, each naming its alternates, so a
    # crawler that lands on one edition can find the other three.
    lastmod = datetime.date.fromtimestamp(
        max(f.stat().st_mtime for f in DATA.glob("*.json"))).isoformat()
    blocks = []
    for _, filename, _ in PAGES:
        for lang in LANGS:
            loc = f"{BASE_URL}/{'' if lang == 'en' else lang + '/'}{filename}"
            alts = "".join(
                f'\n    <xhtml:link rel="alternate" hreflang="{HTML_LANG[other]}" '
                f'href="{BASE_URL}/{"" if other == "en" else other + "/"}{filename}"/>'
                for other in LANGS
            )
            alts += (f'\n    <xhtml:link rel="alternate" hreflang="x-default" '
                     f'href="{BASE_URL}/{filename}"/>')
            blocks.append(f"  <url>\n    <loc>{loc}</loc>\n"
                          f"    <lastmod>{lastmod}</lastmod>{alts}\n  </url>")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(blocks) + "\n</urlset>\n",
        encoding="utf-8",
    )

    # Everything in the repository is served, sources included; crawlers should
    # spend their budget on pages, not on templates and build scripts.
    if NOINDEX:
        robots = "User-agent: *\nDisallow: /\n"
    else:
        robots = ("User-agent: *\nAllow: /\n"
                  + "".join(f"Disallow: {path}\n" for path in CRAWL_DISALLOW)
                  + f"\nSitemap: {BASE_URL}/sitemap.xml\n")
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")

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
    ap.add_argument("--no-build", action="store_true", help="serve without rebuilding")
    args = ap.parse_args()
    if not args.no_build:
        build()
    if args.serve:
        serve(args.port)
