# -*- coding: utf-8 -*-
"""Fold the research dossier into data/*.json.

The dossier (research/dossier.json) is what the research fan-out returned:
one profile per member, a verdict for every claimed open-access link, a list of
verified network links, and an editorial synthesis.  This script does the
mechanical part of turning that into site data — deduplicating co-authored
publications, dropping full-text links that failed verification, sorting
publications into the synthesis's themes — and writes a report listing
everything a human still has to decide.

    python _build/merge_research.py            # report only
    python _build/merge_research.py --apply    # rewrite data/*.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOSSIER = ROOT / "research" / "dossier.json"
REPORT = ROOT / "research" / "report.md"

# publication types that belong in the thematic groups vs. the trailing section
THEMED = {"journal_article", "book", "book_chapter", "edited_volume", "dissertation"}
OTHER_ORDER = ["working_paper", "policy_report", "review", "translation", "other"]
OTHER_LABELS = {
    "working_paper": {"en": "Working and conference papers", "ko": "워킹페이퍼·학회 발표문",
                      "zh": "工作论文与会议论文", "ja": "ワーキングペーパー・学会報告"},
    "policy_report": {"en": "Policy reports and commentary", "ko": "정책보고서·논평", "zh": "政策报告与评论", "ja": "政策報告・論評"},
    "review": {"en": "Book reviews", "ko": "서평", "zh": "书评", "ja": "書評"},
    "translation": {"en": "Translations", "ko": "번역", "zh": "译作", "ja": "翻訳"},
    "other": {"en": "Other writing", "ko": "그 밖의 글", "zh": "其他文字", "ja": "その他"},
}
TYPE_LABELS = {
    "book": {"en": "Book", "ko": "단행본", "zh": "专著", "ja": "単著"},
    "book_chapter": {"en": "Chapter", "ko": "단행본 장", "zh": "论文集章节", "ja": "所収論考"},
    "edited_volume": {"en": "Edited volume", "ko": "편저", "zh": "编著", "ja": "編著"},
    "dissertation": {"en": "PhD dissertation", "ko": "박사학위논문", "zh": "博士论文", "ja": "博士論文"},
}

LINK_LABELS = {
    "homepage": "Website",
    "institutional_page": "Faculty page",
    "google_scholar": "Google Scholar",
    "orcid": "ORCID",
    "academia_or_rg": "ResearchGate",
    "x_twitter": "X",
    "kci": "KCI",
}
LINK_ORDER = ["homepage", "institutional_page", "google_scholar", "orcid", "academia_or_rg", "kci", "x_twitter"]

# dossier key -> members.json key
KEY_MAP = {
    "inho_choi": "inho-choi", "sujin_heo": "sujin-heo", "jaeyoung_kim": "jaeyoung-kim",
    "minju_kwon": "minju-kwon", "inhwan_oh": "inhwan-oh", "chang_joon_ok": "chang-joon-ok",
    "kayeon_roh": "kayeon-roh", "jeeye_song": "jeeye-song", "chaeyoung_yong": "chaeyoung-yong",
}


def norm(title: str) -> str:
    """Normalize a title enough that the same article filed by two co-authors matches."""
    s = unicodedata.normalize("NFKC", title or "").lower()
    s = re.sub(r"\[[^\]]*\]", " ", s)          # drop bracketed English glosses
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:90]


def year_key(pub: dict) -> tuple:
    y = str(pub.get("year", ""))
    if "forth" in y.lower():
        return (9999, y)
    m = re.search(r"\d{4}", y)
    return (int(m.group()) if m else 0, y)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="rewrite data/*.json")
    args = ap.parse_args()

    dossier = load_json(DOSSIER)
    profiles = [p for p in dossier.get("profiles", []) if p]
    verdicts = dossier.get("link_verdicts", []) or []
    network = dossier.get("network", []) or []
    synth = dossier.get("synthesis") or {}
    notes: list[str] = []

    # ---- 1. link verdicts ------------------------------------------------- #
    verdict_by_url: dict[str, dict] = {}
    for v in verdicts:
        if v.get("url"):
            verdict_by_url[v["url"].strip()] = v
    dropped = replaced = kept = 0

    def resolve_fulltext(pub: dict) -> str:
        nonlocal dropped, replaced, kept
        url = (pub.get("url_fulltext") or "").strip()
        if not url:
            return ""
        v = verdict_by_url.get(url)
        if v is None:                                   # never checked -> keep, flag
            notes.append(f"unchecked full-text link: {pub.get('title','?')[:70]} — {url}")
            kept += 1
            return url
        if v.get("verdict") == "full_text_confirmed":
            kept += 1
            return url
        if v.get("replacement_url"):
            replaced += 1
            return v["replacement_url"].strip()
        dropped += 1
        return ""

    # ---- 2. gather + dedupe publications ---------------------------------- #
    merged: dict[tuple, dict] = {}
    uncertain: list = []
    for prof in profiles:
        for pub in prof.get("publications", []) or []:
            k = (norm(pub.get("title", "")), pub.get("type", ""))
            if not k[0]:
                continue
            if pub.get("confidence") == "uncertain":
                uncertain.append((prof["key"], pub))
                continue
            rec = merged.setdefault(k, {"members": []})
            if prof["key"] not in rec["members"]:
                rec["members"].append(prof["key"])
            for field, value in pub.items():
                if field == "url_fulltext":
                    continue
                if value in (None, "", []):
                    continue
                # first non-empty wins, except take the longer summary/authors
                if field in ("summary", "authors", "venue") and rec.get(field):
                    if len(str(value)) > len(str(rec[field])):
                        rec[field] = value
                elif field not in rec:
                    rec[field] = value
            best = resolve_fulltext(pub)
            if best and not rec.get("url_fulltext"):
                rec["url_fulltext"] = best

    # an article that was later collected as a book chapter is one piece of work;
    # keep the journal version and note the reprint rather than listing both
    reprints = []
    for (title_key, kind) in list(merged):
        if kind == "book_chapter" and (title_key, "journal_article") in merged:
            reprints.append(merged.pop((title_key, "book_chapter")))

    pubs = list(merged.values())
    for p in pubs:
        p.setdefault("url_fulltext", "")
        if p.get("type") in TYPE_LABELS:
            p["type_label"] = TYPE_LABELS[p["type"]]

    # ---- 3. sort into themes ---------------------------------------------- #
    theme_defs = synth.get("publication_themes", []) or []
    assign: dict[str, str] = {}
    for th in theme_defs:
        for title in th.get("publication_titles", []) or []:
            assign[norm(title)] = th["id"]
    # hand-checked assignments for what the synthesis did not place
    overrides = ROOT / "research" / "theme_overrides.json"
    if overrides.exists():
        for title, tid in load_json(overrides).items():
            assign[norm(title)] = tid

    themed = [p for p in pubs if p.get("type") in THEMED]
    other = [p for p in pubs if p.get("type") not in THEMED]

    buckets: dict[str, list] = defaultdict(list)
    unassigned = []
    for p in themed:
        tid = assign.get(norm(p.get("title", "")))
        if tid:
            buckets[tid].append(p)
        else:
            unassigned.append(p)
    for p in unassigned:
        notes.append(f"no theme assigned: {p.get('year')} {p.get('title','?')[:80]}")

    other_buckets: dict[str, list] = defaultdict(list)
    for p in other:
        other_buckets[p.get("type", "other")].append(p)

    # ---- 4. rebuild publications.json ------------------------------------- #
    pubdata = load_json(DATA / "publications.json")
    old_blurbs = {t["id"]: t for t in pubdata.get("themes", [])}

    themes = []
    for th in theme_defs:
        entries = sorted(buckets.get(th["id"], []), key=year_key, reverse=True)
        if not entries:
            continue
        prev = old_blurbs.get(th["id"], {})
        themes.append({
            "id": th["id"],
            "title": prev.get("title") or th["title_en"],
            "blurb": prev.get("blurb") or th.get("blurb_en", ""),
            "entries": entries,
        })
    if unassigned:
        themes.append({
            "id": "further-work",
            "title": {"en": "Further Work", "ko": "그 밖의 연구", "zh": "其他研究", "ja": "その他の研究"},
            "blurb": {"en": "Work by members that sits outside the clusters above.",
                      "ko": "위 갈래에 들어가지 않는 구성원들의 작업.",
                      "zh": "不属于上述几组的成员研究。",
                      "ja": "上のいずれにも収まらないメンバーの仕事。"},
            "entries": sorted(unassigned, key=year_key, reverse=True),
        })
    pubdata["themes"] = themes

    pubdata["other_groups"] = [
        {"id": t.replace("_", "-"), "title": OTHER_LABELS[t],
         "entries": sorted(other_buckets[t], key=year_key, reverse=True)}
        for t in OTHER_ORDER if other_buckets.get(t)
    ]

    articles = [p for p in themed if p.get("type") in ("journal_article", "book")]
    pubdata["featured"] = sorted(articles, key=year_key, reverse=True)[:4]

    # ---- 5. members ------------------------------------------------------- #
    memdata = load_json(DATA / "members.json")
    by_key = {m["key"]: m for m in memdata["people"]}
    for prof in profiles:
        m = by_key.get(KEY_MAP.get(prof["key"], ""))
        if not m:
            notes.append(f"profile with no member card: {prof.get('key')}")
            continue
        aff = (prof.get("confirmed_affiliation") or "").strip()
        if aff and not aff.lower().startswith("unverified"):
            notes.append(f"affiliation for {m['name']}: {aff[:150]}")
        links = [l for l in m.get("links", []) if l["url"].startswith("mailto:")]
        found = prof.get("links") or {}
        for field in LINK_ORDER:
            url = (found.get(field) or "").strip()
            if url.startswith("http"):
                links.append({"label": LINK_LABELS[field], "url": url})
        if links:
            m["links"] = links
        if prof.get("korean_name") and not m.get("name_alt"):
            notes.append(f"Korean name found for {m['name']}: {prof['korean_name']}")

    # ---- 6. network links ------------------------------------------------- #
    resdata = load_json(DATA / "resources.json")
    groups: dict[str, list] = defaultdict(list)
    seen_urls = set()
    for e in network:
        url = (e.get("url") or "").strip()
        if not url.startswith("http") or url in seen_urls:
            continue
        seen_urls.add(url)
        groups[(e.get("category") or "other").lower()].append({
            "name": e.get("name", ""),
            "url": url,
            "affiliation": e.get("affiliation", ""),
            "desc": e.get("description", ""),
        })

    # ---- 7. report -------------------------------------------------------- #
    lines = ["# 연구 수합 결과\n",
             f"- 프로필 {len(profiles)}건, 중복 제거 후 출판물 **{len(pubs)}건** "
             f"(주제 배정 {len(themed) - len(unassigned)} / 미배정 {len(unassigned)} / 기타 {len(other)})",
             f"- 전문 링크: 확인 {kept} · 대체 {replaced} · 폐기 {dropped}",
             f"- 네트워크 링크: {len(seen_urls)}건, 범주 {len(groups)}종\n",
             "## 범주별 네트워크 링크 수\n"]
    for cat, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"- {cat}: {len(items)}")
    if synth.get("corrections"):
        lines += ["\n## 원본 사이트 정정 사항\n"] + [f"- {c}" for c in synth["corrections"]]
    if synth.get("recommended_sections"):
        lines += ["\n## 추가 권고 항목\n"]
        for s in synth["recommended_sections"]:
            lines.append(f"### {s['title']} ({s.get('effort','')})\n\n{s.get('rationale','')}\n\n"
                         f"바로 쓸 수 있는 재료: {s.get('content_available','')}\n")
    lines += ["\n## 확인 필요\n"] + [f"- {n}" for n in notes]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:12]))
    print(f"\nreport -> {REPORT}")

    if args.apply:
        write_json(DATA / "publications.json", pubdata)
        write_json(DATA / "members.json", memdata)
        write_json(ROOT / "research" / "network_by_category.json", dict(groups))
        print("applied to data/publications.json, data/members.json")
        print("network links staged at research/network_by_category.json")
    else:
        print("\n(dry run — pass --apply to write)")


if __name__ == "__main__":
    main()
