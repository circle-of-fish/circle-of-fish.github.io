# -*- coding: utf-8 -*-
"""연구 결과의 네트워크 링크를 자료·링크 페이지 구조로 정리한다.

에이전트가 붙인 범주가 20종으로 잘게 갈라져 있어 페이지에 쓸 6개 묶음으로 통합한다.
기존에 손으로 정리해 둔 도구 목록(달력 변환기·인명 사전 등)은 그대로 두고 뒤에 붙인다.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

# 세부 범주 -> 페이지 묶음
GROUPS = [
    ("networks", ("network/association", "research group", "working group"),
     {"en": "Networks and associations", "ko": "네트워크·학회", "zh": "网络与学会", "ja": "ネットワーク・学会"},
     {"en": "Sections, standing workshops, and collectives working the same seam.",
      "ko": "같은 문제를 파고 있는 분과·상설 워크숍·연구 모임.",
      "zh": "在同一问题上持续推进的分会、常设工作坊与研究集体。",
      "ja": "同じ問題を掘り続けている分科会・常設ワークショップ・研究集団。"}),
    ("institutes", ("research institute", "think tank", "university", "department", "workshop"),
     {"en": "Institutes and centres", "ko": "연구기관·센터", "zh": "研究机构与中心", "ja": "研究機関・センター"},
     None),
    ("scholars", ("scholar",),
     {"en": "Scholars", "ko": "학자", "zh": "学者", "ja": "研究者"},
     {"en": "Colleagues and senior interlocutors whose work ours answers to. Pages verified live in August 2026.",
      "ko": "우리 작업이 응답하고 있는 동료·선배 연구자들. 2026년 8월에 접속을 확인한 페이지입니다.",
      "zh": "我们的研究所回应的同行与前辈学者。页面于2026年8月核实可访问。",
      "ja": "私たちの仕事が応答している同僚・先達の研究者。ページは2026年8月に接続を確認しました。"}),
    ("journals", ("journal", "book series", "open-access publisher"),
     {"en": "Journals and book series", "ko": "학술지·총서", "zh": "期刊与丛书", "ja": "学術誌・叢書"},
     None),
    ("archives", ("database", "archive", "text corpus", "open-access repository"),
     {"en": "Archives and databases", "ko": "사료·데이터베이스", "zh": "档案与数据库", "ja": "史料・データベース"},
     {"en": "Where the sources actually are — Korean, Chinese, Japanese, and Western collections.",
      "ko": "사료가 실제로 있는 곳 — 한국·중국·일본·서양 자료군.",
      "zh": "史料真正所在之处——韩国、中国、日本与西方的资料群。",
      "ja": "史料が実際にある場所——韓国・中国・日本・西洋の資料群。"}),
    ("tools", ("digital humanities tool", "teaching resource", "historical gis", "blog", "podcast"),
     {"en": "Tools, maps, and blogs", "ko": "도구·지도·블로그", "zh": "工具、地图与博客", "ja": "ツール・地図・ブログ"},
     None),
]


def bucket(category: str) -> str:
    c = category.lower()
    for key, needles, _, _ in GROUPS:
        if any(n in c for n in needles):
            return key
    return "tools"


def sort_key(item: dict) -> tuple:
    """학자는 성(姓)으로, 나머지는 이름 그대로 정렬."""
    name = item["name"]
    parts = re.sub(r"\s*\(.*?\)\s*", " ", name).split()
    return (parts[-1].lower() if parts else name.lower(), name.lower())


def main() -> None:
    dossier = json.loads((ROOT / "research" / "dossier.json").read_text(encoding="utf-8"))
    res_path = ROOT / "data" / "resources.json"
    res = json.loads(res_path.read_text(encoding="utf-8"))

    seen, by_group = set(), {k: [] for k, *_ in GROUPS}
    for e in dossier["network"]:
        url = (e.get("url") or "").strip().rstrip("/")
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        by_group[bucket(e.get("category", ""))].append({
            "name": e["name"],
            "url": e["url"],
            **({"affiliation": e["affiliation"]} if e.get("affiliation") else {}),
            "desc": e.get("description", ""),
        })

    # 기존 손질 목록은 살려 두고 새 항목을 합친다
    old_tools = {}
    for block in res["link_blocks"]:
        for g in block.get("groups", []):
            for item in g.get("entries", []):
                old_tools[item["url"].rstrip("/")] = item

    network_groups, archive_groups = [], []
    for key, _, title, note in GROUPS:
        entries = sorted(by_group[key], key=sort_key)
        if key in ("archives", "tools"):
            extra = [v for k, v in old_tools.items() if k not in seen]
            if key == "tools":
                entries += sorted(extra, key=sort_key)
                seen.update(k for k in old_tools)
        if not entries:
            continue
        group = {"title": title, "entries": entries}
        if note:
            group["note"] = note
        (network_groups if key in ("networks", "institutes", "scholars", "journals")
         else archive_groups).append(group)

    res["link_blocks"] = [
        {
            "id": "network",
            "title": {"en": "Networks and Interlocutors", "ko": "네트워크와 대화 상대",
                      "zh": "网络与对话者", "ja": "ネットワークと対話者"},
            "kicker": {"en": "Who we read with and argue with", "ko": "함께 읽고 함께 다투는 이들",
                       "zh": "与我们共读、共辩者", "ja": "共に読み、論じ合う人びと"},
            "groups": network_groups,
        },
        {
            "id": "archives",
            "title": {"en": "Archives, Databases, and Tools", "ko": "사료·데이터베이스·도구",
                      "zh": "档案、数据库与工具", "ja": "史料・データベース・ツール"},
            "kicker": {"en": "What we work with", "ko": "우리가 다루는 것들",
                       "zh": "我们借以工作的东西", "ja": "私たちが使うもの"},
            "groups": archive_groups,
        },
    ]

    res_path.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(g["entries"]) for b in res["link_blocks"] for g in b["groups"])
    for b in res["link_blocks"]:
        for g in b["groups"]:
            print(f"  {g['title']['ko']:16} {len(g['entries']):3}건")
    print(f"자료·링크 {total}건")


if __name__ == "__main__":
    main()
