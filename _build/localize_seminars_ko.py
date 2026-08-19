# -*- coding: utf-8 -*-
"""세미나 항목의 한국어판 표기를 data/seminars.json에 붙인다.

서양 저자명은 외래어 표기법대로 한글로 옮기고 괄호에 원어를 병기한다.
저서·논문 제목은 원어 그대로 둔다(한국 학계의 통상적인 인용 관행).
한국 연구자의 이름은 확인된 경우에만 한글로 적고, 그렇지 않으면 로마자를 유지한다.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

KO_TITLE = {
    "2026-07-25": "최정운. 2012. 『오월의 사회과학』. 오월의봄.",
    "2026-06-24": "여름 세미나",
    "2026-06-15": "여름 세미나",
    "2026-04-18": "허수진, 「Iberian Early-Modern Languages of Inter-Polity Ordering in Japan」",
    "2026-01-03": "하영선 선생님과의 대담",
    "2025-07-21": "국제정치학·아시아 연구 교수법 워크숍",
    "2025-04-17": "용채영, 「Trauma Time and Memory in Understanding Gender-Based Violence」",
    "2024-12-20": "오인환, 「Explaining the Absence of a War during China&rsquo;s Quantitative Naval Overtake, 2008–2023」",
    "2024-10-02": "최인호, 「Literary Reconstruction of the 1636 Qing Invasion of Korea」",
    "2024-09-20": "기획 모임",
    "2024-03-08": "권민주 &middot; 용채영, 「Global Human Rights Institutions」",
    "2023-07-24": "국제정치학 방법론 워크숍: 以意逆志로 읽는 동아시아 외교사",
    "2023-04-28": "오인환, 「Racial Hierarchy, Restraint, and the Resolution of the Commitment Problem: Japan&rsquo;s Pursuit of Status and the Washington Naval System, 1921–1936」",
    "2023-04-01": "용채영, 「The Politics of Emotional Deference to Self-Esteem: The Case of Japan–US Diplomatic Negotiations in 1951」",
    "2023-02-24": "최인호, 「On Being Chinese and Being Complexified: Chinese IR as a Transcultural Project」(<em>Review of International Studies</em>, 2022) 및 「사대의 국제정치이론」(<em>국제정치논총</em> 63-1, 2023)",
    "2023-01-19": "패트릭 새디어스 잭슨(Patrick Thaddeus Jackson) &middot; 허수진. 2022. 「Working on Relationalism」. <em>New Perspectives</em> 30(2): 157–169.",
    "2022-12-09": "니콜라 기요(Nicolas Guilhot) 엮음. 2011. <em>The Invention of International Relations Theory: Realism, the Rockefeller Foundation, and the 1954 Conference on Theory</em>. Columbia University Press.",
    "2022-10-21": "에두아르두 비베이루스 지 카스트루(Eduardo Viveiros de Castro). 2015. 「Who Is Afraid of the Ontological Wolf?」. <em>Cambridge Journal of Anthropology</em> 33(1): 2–17. / 애너벨 브렛(Annabel Brett). 2021. <em>Between History, Politics, Law</em>. Cambridge University Press, 1장.",
    "2022-08-16": "아이셰 자라콜(Ayşe Zarakol). 2022. <em>Before the West: The Rise and Fall of Eastern World Orders</em>. Cambridge University Press.",
    "2022-07-21": "발레리 더 쿠이여르(Valerie de Koeijer) &middot; 로비 실리엄(Robbie Shilliam). 2021. 「Forum: International Relations as a Geoculturally Pluralistic Field」. <em>International Politics Reviews</em> 9: 272–275.",
    "2022-06-03": "옥창준, 「냉전 초기 한국 국제정치 지식의 재구성」 — 서울대학교 박사학위논문, 2022.",
    "2022-02-24": "타마라 트라운셀(Tamara A. Trownsell) 외. 2021. 「Differing about Difference: Relational IR from around the World」. <em>International Studies Perspectives</em> 22(1): 25–64.",
    "2022-01-19": "토론: <em>Review of International Studies</em> 특집호 「The Multiple Origins of IR」(2021)",
    "2021-12-29": "전재성(서울대학교) 초청 세미나: 불완전 주권",
    "2021-12-17": "데이비드 블레이니(David L. Blaney) &middot; 알린 티크너(Arlene B. Tickner). 2017. 「Worlding, Ontological Politics and the Possibility of a Decolonial IR」. <em>Millennium</em> 45(3): 293–311.",
    "2021-11-24": "Jungmin Seo &middot; Young Chul Cho. 2021. 「The Emergence and Evolution of International Relations Studies in Postcolonial South Korea」. <em>Review of International Studies</em> 47(5): 619–636.",
    "2021-10-24": "라인하르트 코젤렉(Reinhart Koselleck). 2018. <em>Sediments of Time: On Possible Histories</em>. Stanford University Press.",
    "2021-09-24": "Seo-Hyun Park. 2017. <em>Sovereignty and Status in East Asian International Relations</em>. Cambridge University Press.",
    "2021-08-20": "토론",
    "2021-07-24": "애너벨 브렛(Annabel S. Brett). 2011. <em>Changes of State: Nature and the Limits of the City in Early Modern Natural Law</em>. Princeton University Press.",
    "2021-05-22": "C. H. 알렉산드로비치(C. H. Alexandrowicz), 데이비드 아미티지(David Armitage) &middot; 제니퍼 피츠(Jennifer Pitts) 엮음. 2017. <em>The Law of Nations in Global History</em>. Oxford University Press.",
    "2021-04-24": "리디아 류(Lydia H. Liu, 劉禾). 2006. <em>The Clash of Empires: The Invention of China in Modern World Making</em>. Harvard University Press.",
    "2021-03-27": "로런 벤턴(Lauren Benton), 애덤 클룰로(Adam Clulow), 베인 애트우드(Bain Attwood) 엮음. 2017. <em>Protection and Empire: A Global History</em>. Cambridge University Press.",
    "2021-02-20": "살리하 벨메수스(Saliha Belmessous) 엮음. 2014. <em>Empire by Treaty: Negotiating European Expansion, 1600–1900</em>. Oxford University Press.",
    "2020-12-18": "마리아 아델레 카라이(Maria Adele Carrai). 2019. <em>Sovereignty in China: A Genealogy of a Concept since 1840</em>. Cambridge University Press.",
    "2020-11-20": "아미타브 아차리아(Amitav Acharya) &middot; 배리 부잔(Barry Buzan). 2019. <em>The Making of Global International Relations: Origins and Evolution of IR at its Centenary</em>. Cambridge University Press.",
    "2020-10-23": "로템 코브너(Rotem Kowner) &middot; 발터 데멜(Walter Demel) 엮음. 2015. <em>Race and Racism in Modern East Asia</em>, 1권. Brill.",
    "2020-09-26": "제러미 옐런(Jeremy A. Yellen). 2019. <em>The Greater East Asia Co-Prosperity Sphere: When Total Empire Met Total War</em>. Cornell University Press.",
    "2020-08-22": "아돔 게타츄(Adom Getachew). 2019. <em>Worldmaking after Empire: The Rise and Fall of Self-Determination</em>. Princeton University Press.",
    "2020-07-25": "우르스 마티아스 차흐만(Urs Matthias Zachmann) 엮음. 2017. <em>Asia after Versailles: Asian Perspectives on the Paris Peace Conference and the Interwar Order, 1919–33</em>. Edinburgh University Press.",
    "2020-06-27": "첫 모임",
}

KO_META = {
    "2026-07-25": "초판 1999년. 영역본: Jung-Woon Choi. 2005. <em>The Gwangju Uprising: The Pivotal Democratic Movement that Changed the History of Modern Korea</em>. Homa &amp; Sekey Books, 유영난 옮김.",
    "2026-04-18": "초고",
    "2025-07-21": "동아시아연구원(EAI), 서울",
    "2025-04-17": "초고",
    "2024-12-20": "초고",
    "2024-10-02": "연구계획서",
    "2024-03-08": "초고",
    "2023-04-28": "초고",
    "2023-04-01": "초고",
    "2023-02-24": "복어회 구성원의 논문 두 편을 함께 읽음",
    "2022-12-09": "부록 1: 국제정치 학술회의, 1954년 5월 7–8일",
    "2022-06-03": "초고",
    "2021-05-22": "1–2부",
}


def main() -> None:
    path = Path(__file__).resolve().parent.parent / "data" / "seminars.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    missing = []
    for e in data["entries"]:
        iso = e["iso"]
        ko = KO_TITLE.get(iso)
        if not ko:
            missing.append(iso)
            continue
        en = e["title"] if isinstance(e["title"], str) else e["title"]["en"]
        e["title"] = {"en": en, "ko": ko}
        if "meta" in e:
            en_meta = e["meta"] if isinstance(e["meta"], str) else e["meta"]["en"]
            e["meta"] = {"en": en_meta, "ko": KO_META.get(iso, en_meta)}

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(data['entries']) - len(missing)}건 한국어 표기 추가"
          + (f", 누락 {missing}" if missing else ""))


if __name__ == "__main__":
    main()
