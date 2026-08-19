# -*- coding: utf-8 -*-
"""Collect English-only prose out of data/*.json for translation, and put it back.

Anything the research pass produced arrives as a plain English string where the
site wants a {"en","ko","zh","ja"} bundle.  This finds those strings, writes
them out in batches for translators to work on, and merges the finished batches
back into the data files by path.

Bibliographic fields are deliberately excluded: author names, titles, and
journal names stay in their original language in every edition of the site.

    python _build/i18n_batches.py split --batches 8
    python _build/i18n_batches.py apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TR = ROOT / "research" / "tr"

LANGS = ("en", "ko", "zh", "ja")

# prose keys only — never `authors`, `venue`, or a publication's `title`
PROSE_KEYS = {"summary", "blurb", "desc", "lede", "note", "kicker", "group_note",
              "rationale", "body", "heading"}
# `title` is prose when it heads a theme or a resource group, but never inside
# `entries` — those titles are bibliographic and stay in their original language
TITLE_OK_PARENTS = {"themes", "other_groups", "groups", "reading", "link_blocks"}

FILES = ["publications.json", "resources.json", "members.json", "research.json", "site.json"]


def is_bundle(v) -> bool:
    return isinstance(v, dict) and any(k in v for k in LANGS)


def walk(node, path, out):
    if isinstance(node, dict):
        for k, v in node.items():
            p = path + [k]
            if isinstance(v, str) and v.strip():
                translate = k in PROSE_KEYS or (
                    k == "title"
                    and "entries" not in path
                    and any(seg in TITLE_OK_PARENTS for seg in path)
                )
                if translate:
                    out.append((p, v))
            elif not is_bundle(v):
                walk(v, p, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            p = path + [i]
            if isinstance(v, str) and v.strip() and path and path[-1] in PROSE_KEYS:
                out.append((p, v))          # e.g. body: ["para", "para"]
            elif not is_bundle(v):
                walk(v, p, out)


def get_at(root, path):
    node = root
    for seg in path:
        node = node[seg]
    return node


def set_at(root, path, value):
    node = root
    for seg in path[:-1]:
        node = node[seg]
    node[path[-1]] = value


def cmd_split(batches: int) -> None:
    TR.mkdir(parents=True, exist_ok=True)
    for old in TR.glob("batch_*.json"):
        old.unlink()

    records = []
    for name in FILES:
        path = DATA / name
        if not path.exists():
            continue
        found: list = []
        walk(json.loads(path.read_text(encoding="utf-8")), [], found)
        for p, v in found:
            records.append({"file": name, "path": p, "en": v})

    if not records:
        print("nothing to translate — every prose field is already a language bundle")
        return

    size = -(-len(records) // batches)
    for i in range(0, len(records), size):
        n = i // size + 1
        (TR / f"batch_{n:02d}.json").write_text(
            json.dumps(records[i:i + size], ensure_ascii=False, indent=1), encoding="utf-8")
    written = len(list(TR.glob("batch_*.json")))
    print(f"{len(records)} strings -> {written} batches in {TR}")
    for f in sorted(TR.glob("batch_*.json")):
        print(f"  {f.name}: {len(json.loads(f.read_text(encoding='utf-8')))}")


def cmd_apply() -> None:
    done = sorted(TR.glob("batch_*.done.json"))
    if not done:
        raise SystemExit(f"no batch_*.done.json in {TR}")

    by_file: dict[str, list] = {}
    for f in done:
        for rec in json.loads(f.read_text(encoding="utf-8")):
            by_file.setdefault(rec["file"], []).append(rec)

    total = 0
    for name, recs in by_file.items():
        path = DATA / name
        root = json.loads(path.read_text(encoding="utf-8"))
        for rec in recs:
            bundle = {l: rec.get(l, "") for l in LANGS}
            if not bundle["en"]:
                bundle["en"] = get_at(root, rec["path"])
            set_at(root, rec["path"], bundle)
            total += 1
        path.write_text(json.dumps(root, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: {len(recs)} fields translated")
    print(f"total {total}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("split"); sp.add_argument("--batches", type=int, default=8)
    sub.add_parser("apply")
    a = ap.parse_args()
    cmd_split(a.batches) if a.cmd == "split" else cmd_apply()
