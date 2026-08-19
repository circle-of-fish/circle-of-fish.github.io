# -*- coding: utf-8 -*-
"""Turn the seminar archive into data/seminars.json.

The entries are citations, so the title字 stay in their original language in
every edition of the site; only the surrounding chrome (kind labels, page
copy) is translated.

Kinds: reading (a book or set of articles), draft (a member's manuscript),
workshop, guest (an invited interlocutor), planning.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# (iso date for sorting, displayed date, kind, title, meta-or-None)
E = [
    ("2026-07-25", "25 July 2026", "reading",
     "최정운. 2012. 『오월의 사회과학』. 오월의봄.",
     "First edition 1999. English translation: Jung-Woon Choi. 2005. <em>The Gwangju Uprising: The Pivotal Democratic Movement that Changed the History of Modern Korea</em>. Homa &amp; Sekey Books, tr. Young-nan Yu."),
    ("2026-06-24", "24 June 2026", "reading", "Summer Seminar", None),
    ("2026-06-15", "15–19 June 2026", "workshop", "Summer Seminar", None),
    ("2026-04-18", "18 April 2026", "draft",
     "Sujin Heo, &ldquo;Iberian Early-Modern Languages of Inter-Polity Ordering in Japan&rdquo;", "Draft"),
    ("2026-01-03", "3 January 2026", "guest", "Speaking with Young-sun Ha (하영선)", None),
    ("2025-07-21", "21–23 July 2025", "workshop",
     "International Relations / Asian Studies Pedagogy Workshop", "East Asia Institute, Seoul"),
    ("2025-04-17", "17 April 2025", "draft",
     "Chaeyoung Yong, &ldquo;Trauma Time and Memory in Understanding Gender-Based Violence&rdquo;", "Draft"),
    ("2024-12-20", "20 December 2024", "draft",
     "Inhwan Oh, &ldquo;Explaining the Absence of a War during China&rsquo;s Quantitative Naval Overtake, 2008–2023&rdquo;", "Draft"),
    ("2024-10-02", "2 October 2024", "draft",
     "Inho Choi, &ldquo;Literary Reconstruction of the 1636 Qing Invasion of Korea&rdquo;", "Project proposal"),
    ("2024-09-20", "20 September 2024", "planning", "Planning meeting", None),
    ("2024-03-08", "8 March 2024", "draft",
     "Minju Kwon and Chaeyoung Yong, &ldquo;Global Human Rights Institutions&rdquo;", "Draft"),
    ("2023-07-24", "24–28 July 2023", "workshop",
     "IR Methodology Workshop: East Asian Diplomatic History through <em>Iuiyeokji</em> (以意逆志)", None),
    ("2023-04-28", "28 April 2023", "draft",
     "Inhwan Oh, &ldquo;Racial Hierarchy, Restraint, and the Resolution of the Commitment Problem: Japan&rsquo;s Pursuit of Status and the Washington Naval System, 1921–1936&rdquo;", "Draft"),
    ("2023-04-01", "1 April 2023", "draft",
     "Chaeyoung Yong, &ldquo;The Politics of Emotional Deference to Self-Esteem: The Case of Japan–US Diplomatic Negotiations in 1951&rdquo;", "Draft"),
    ("2023-02-24", "24 February 2023", "draft",
     "Inho Choi, &ldquo;On Being Chinese and Being Complexified: Chinese IR as a Transcultural Project&rdquo; (<em>Review of International Studies</em>, 2022) and &ldquo;사대의 국제정치이론: 미래과거로서의 병자호란&rdquo; (<em>국제정치논총</em> 63-1, 2023)",
     "Two of the group&rsquo;s own articles, read together"),
    ("2023-01-19", "19 January 2023", "reading",
     "Patrick Thaddeus Jackson and Sujin Heo. 2022. &ldquo;Working on Relationalism.&rdquo; <em>New Perspectives</em> 30(2): 157–169.", None),
    ("2022-12-09", "9 December 2022", "reading",
     "Nicolas Guilhot, ed. 2011. <em>The Invention of International Relations Theory: Realism, the Rockefeller Foundation, and the 1954 Conference on Theory</em>. Columbia University Press.",
     "Appendix 1: Conference on International Politics, 7–8 May 1954"),
    ("2022-10-21", "21 October 2022", "reading",
     "Eduardo Viveiros de Castro. 2015. &ldquo;Who Is Afraid of the Ontological Wolf?&rdquo; <em>Cambridge Journal of Anthropology</em> 33(1): 2–17; and Annabel Brett. 2021. <em>Between History, Politics, Law</em>. Cambridge University Press, ch. 1.", None),
    ("2022-08-16", "16 August 2022", "reading",
     "Ayşe Zarakol. 2022. <em>Before the West: The Rise and Fall of Eastern World Orders</em>. Cambridge University Press.", None),
    ("2022-07-21", "21 July 2022", "reading",
     "Valerie de Koeijer and Robbie Shilliam. 2021. &ldquo;Forum: International Relations as a Geoculturally Pluralistic Field.&rdquo; <em>International Politics Reviews</em> 9: 272–275.", None),
    ("2022-06-03", "3 June 2022", "draft",
     "Chang Joon Ok, &ldquo;한국 국제정치 지식의 형성: 냉전 초기 남한&rdquo; — PhD dissertation, Seoul National University, 2022 [in Korean]", "Draft"),
    ("2022-02-24", "24 February 2022", "reading",
     "Tamara A. Trownsell et al. 2021. &ldquo;Differing about Difference: Relational IR from around the World.&rdquo; <em>International Studies Perspectives</em> 22(1): 25–64.", None),
    ("2022-01-19", "19 January 2022", "reading",
     "Discussion: <em>Review of International Studies</em> special issue, &ldquo;The Multiple Origins of IR&rdquo; (2021)", None),
    ("2021-12-29", "29 December 2021", "guest",
     "Seminar with Chaesung Chun (전재성, Seoul National University): Incomplete Sovereignty", None),
    ("2021-12-17", "17 December 2021", "reading",
     "David L. Blaney and Arlene B. Tickner. 2017. &ldquo;Worlding, Ontological Politics and the Possibility of a Decolonial IR.&rdquo; <em>Millennium</em> 45(3): 293–311.", None),
    ("2021-11-24", "24 November 2021", "reading",
     "Jungmin Seo and Young Chul Cho. 2021. &ldquo;The Emergence and Evolution of International Relations Studies in Postcolonial South Korea.&rdquo; <em>Review of International Studies</em> 47(5): 619–636.", None),
    ("2021-10-24", "24 October 2021", "reading",
     "Reinhart Koselleck. 2018. <em>Sediments of Time: On Possible Histories</em>. Stanford University Press.", None),
    ("2021-09-24", "24 September 2021", "reading",
     "Seo-Hyun Park. 2017. <em>Sovereignty and Status in East Asian International Relations</em>. Cambridge University Press.", None),
    ("2021-08-20", "20 August 2021", "planning", "Discussion", None),
    ("2021-07-24", "24 July 2021", "reading",
     "Annabel S. Brett. 2011. <em>Changes of State: Nature and the Limits of the City in Early Modern Natural Law</em>. Princeton University Press.", None),
    ("2021-05-22", "22 May 2021", "reading",
     "C. H. Alexandrowicz, ed. David Armitage and Jennifer Pitts. 2017. <em>The Law of Nations in Global History</em>. Oxford University Press.", "Parts 1–2"),
    ("2021-04-24", "24 April 2021", "reading",
     "Lydia H. Liu. 2006. <em>The Clash of Empires: The Invention of China in Modern World Making</em>. Harvard University Press.", None),
    ("2021-03-27", "27 March 2021", "reading",
     "Lauren Benton, Adam Clulow, and Bain Attwood, eds. 2017. <em>Protection and Empire: A Global History</em>. Cambridge University Press.", None),
    ("2021-02-20", "20 February 2021", "reading",
     "Saliha Belmessous, ed. 2014. <em>Empire by Treaty: Negotiating European Expansion, 1600–1900</em>. Oxford University Press.", None),
    ("2020-12-18", "18 December 2020", "reading",
     "Maria Adele Carrai. 2019. <em>Sovereignty in China: A Genealogy of a Concept since 1840</em>. Cambridge University Press.", None),
    ("2020-11-20", "20 November 2020", "reading",
     "Amitav Acharya and Barry Buzan. 2019. <em>The Making of Global International Relations: Origins and Evolution of IR at its Centenary</em>. Cambridge University Press.", None),
    ("2020-10-23", "23 October 2020", "reading",
     "Rotem Kowner and Walter Demel, eds. 2015. <em>Race and Racism in Modern East Asia</em>, vol. 1. Brill.", None),
    ("2020-09-26", "26 September 2020", "reading",
     "Jeremy A. Yellen. 2019. <em>The Greater East Asia Co-Prosperity Sphere: When Total Empire Met Total War</em>. Cornell University Press.", None),
    ("2020-08-22", "22 August 2020", "reading",
     "Adom Getachew. 2019. <em>Worldmaking after Empire: The Rise and Fall of Self-Determination</em>. Princeton University Press.", None),
    ("2020-07-25", "25 July 2020", "reading",
     "Urs Matthias Zachmann, ed. 2017. <em>Asia after Versailles: Asian Perspectives on the Paris Peace Conference and the Interwar Order, 1919–33</em>. Edinburgh University Press.", None),
    ("2020-06-27", "27 June 2020", "planning", "First meeting", None),
]

MONTHS = {
    "01": ("January", "1월", "1月", "1月"), "02": ("February", "2월", "2月", "2月"),
    "03": ("March", "3월", "3月", "3月"), "04": ("April", "4월", "4月", "4月"),
    "05": ("May", "5월", "5月", "5月"), "06": ("June", "6월", "6月", "6月"),
    "07": ("July", "7월", "7月", "7月"), "08": ("August", "8월", "8月", "8月"),
    "09": ("September", "9월", "9月", "9月"), "10": ("October", "10월", "10月", "10月"),
    "11": ("November", "11월", "11月", "11月"), "12": ("December", "12月", "12月", "12月"),
}


def localized_date(iso: str, display_en: str) -> dict:
    """CJK editions get YYYY.MM.DD, preserving any en-dash day range."""
    y, m, d = iso.split("-")
    head = display_en.split(" ")[0]          # "15–19" for a range, "24" otherwise
    day = head if "–" in head else d
    cjk = f"{y}.{m}.{day}"
    return {"en": display_en, "ko": cjk, "zh": cjk, "ja": cjk}


entries = []
for iso, disp, kind, title, meta in sorted(E, key=lambda r: r[0], reverse=True):
    rec = {
        "iso": iso,
        "year": iso[:4],
        "date_display": localized_date(iso, disp),
        "kind": kind,
        "title": title,
    }
    if meta:
        rec["meta"] = meta
    entries.append(rec)

data = {
    "title": {"en": "Seminars", "ko": "세미나", "zh": "研讨会", "ja": "セミナー"},
    "kicker": {"en": "Archive since June 2020", "ko": "2020년 6월 이후의 기록",
               "zh": "2020年6月以来的记录", "ja": "2020年6月以降の記録"},
    "lede": {
        "en": "Roughly once a month since 2020. Books and articles we read together, and members’ drafts we take apart before the reviewers do.",
        "ko": "2020년 이래 대략 한 달에 한 번. 함께 읽은 책과 논문, 그리고 심사자보다 먼저 우리가 해체한 구성원들의 원고.",
        "zh": "自2020年起大致每月一次。我们共读的书与论文，以及在审稿人之前先由我们拆解的成员稿件。",
        "ja": "2020年以来おおむね月に一度。共に読んだ本と論文、そして査読者より先に私たちが解体したメンバーの草稿。",
    },
    "kinds": {
        "reading": {"en": "Reading", "ko": "독회", "zh": "共读", "ja": "読書会"},
        "draft": {"en": "Draft", "ko": "원고 검토", "zh": "稿件研讨", "ja": "原稿検討"},
        "workshop": {"en": "Workshop", "ko": "워크숍", "zh": "工作坊", "ja": "ワークショップ"},
        "guest": {"en": "Guest", "ko": "초청", "zh": "特邀", "ja": "招待"},
        "planning": {"en": "Meeting", "ko": "모임", "zh": "会务", "ja": "会合"},
    },
    "meta_description": {
        "en": "Five years of the Circle of the Fish reading seminar: books, articles, member drafts, and workshops since June 2020.",
        "ko": "2020년 6월 이후 5년간 이어진 복어회 세미나 기록 — 단행본, 논문, 구성원 원고, 워크숍.",
        "zh": "河豚会研讨会五年记录：2020年6月以来的专著、论文、成员稿件与工作坊。",
        "ja": "2020年6月以降五年にわたる河豚の会セミナーの記録——単行本、論文、メンバーの草稿、ワークショップ。",
    },
    "note": {
        "en": "Seminar readings that have become standing references are collected on the Resources &amp; Links page.",
        "ko": "세미나에서 읽은 문헌 가운데 상시 참고 문헌이 된 것들은 자료·링크 페이지에 모아 두었습니다.",
        "zh": "研讨会读过的文献中已成为常备参考的部分，收录在「资源与链接」页面。",
        "ja": "セミナーで読んだ文献のうち常備参照となったものは「資料・リンク」ページにまとめています。",
    },
    "entries": entries,
}

out = Path(__file__).resolve().parent.parent / "data" / "seminars.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out} — {len(entries)} entries, {entries[0]['iso']} .. {entries[-1]['iso']}")
