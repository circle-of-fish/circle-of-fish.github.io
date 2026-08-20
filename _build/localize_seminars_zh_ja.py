# -*- coding: utf-8 -*-
"""세미나 항목의 중국어·일본어판 표기를 data/seminars.json에 붙인다.

한국어판과 같은 원칙이다. 서양 저자명은 각 언어의 관용 표기로 옮기고 괄호에 원어를
병기하며, 저서·논문 제목은 원어 그대로 둔다. 한국 연구자의 이름은 한자 표기를 확인할
수 없으므로 로마자를 쓴다 — 중국어·일본어 독자가 찾아볼 수 있는 형태이면서
근거 없는 한자를 지어내지 않는 쪽이다.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ZH_TITLE = {
    "2026-07-25": "Choi Jung-woon（최정운）. 2012. 『오월의 사회과학』. 오월의봄.",
    "2026-06-24": "暑期研讨",
    "2026-06-15": "暑期研讨",
    "2026-04-18": "Sujin Heo，「Iberian Early-Modern Languages of Inter-Polity Ordering in Japan」",
    "2026-01-03": "与 Ha Young-sun（하영선）的对谈",
    "2025-07-21": "国际关系学与亚洲研究教学法工作坊",
    "2025-04-17": "Chaeyoung Yong，「Trauma Time and Memory in Understanding Gender-Based Violence」",
    "2024-12-20": "Inhwan Oh，「Explaining the Absence of a War during China&rsquo;s Quantitative Naval Overtake, 2008–2023」",
    "2024-10-02": "Inho Choi，「Literary Reconstruction of the 1636 Qing Invasion of Korea」",
    "2024-09-20": "筹备会议",
    "2024-03-08": "Minju Kwon &middot; Chaeyoung Yong，「Global Human Rights Institutions」",
    "2023-07-24": "国际关系学方法论工作坊：以「以意逆志」读东亚外交史",
    "2023-04-28": "Inhwan Oh，「Racial Hierarchy, Restraint, and the Resolution of the Commitment Problem: Japan&rsquo;s Pursuit of Status and the Washington Naval System, 1921–1936」",
    "2023-04-01": "Chaeyoung Yong，「The Politics of Emotional Deference to Self-Esteem: The Case of Japan–US Diplomatic Negotiations in 1951」",
    "2023-02-24": "Inho Choi，「On Being Chinese and Being Complexified: Chinese IR as a Transcultural Project」（<em>Review of International Studies</em>, 2022）及「사대의 국제정치이론」（<em>국제정치논총</em> 63-1, 2023）",
    "2023-01-19": "帕特里克·撒迪厄斯·杰克逊（Patrick Thaddeus Jackson）&middot; Sujin Heo. 2022.「Working on Relationalism」. <em>New Perspectives</em> 30(2): 157–169.",
    "2022-12-09": "尼古拉·吉约（Nicolas Guilhot）编. 2011. <em>The Invention of International Relations Theory: Realism, the Rockefeller Foundation, and the 1954 Conference on Theory</em>. Columbia University Press.",
    "2022-10-21": "爱德华多·维韦罗斯·德卡斯特罗（Eduardo Viveiros de Castro）. 2015.「Who Is Afraid of the Ontological Wolf?」. <em>Cambridge Journal of Anthropology</em> 33(1): 2–17. / 安娜贝尔·布雷特（Annabel Brett）. 2021. <em>Between History, Politics, Law</em>. Cambridge University Press, 第1章.",
    "2022-08-16": "阿伊莎·扎拉科尔（Ayşe Zarakol）. 2022. <em>Before the West: The Rise and Fall of Eastern World Orders</em>. Cambridge University Press.",
    "2022-07-21": "瓦莱丽·德科伊耶（Valerie de Koeijer）&middot; 罗比·希利厄姆（Robbie Shilliam）. 2021.「Forum: International Relations as a Geoculturally Pluralistic Field」. <em>International Politics Reviews</em> 9: 272–275.",
    "2022-06-03": "Chang Joon Ok，「냉전 초기 한국 국제정치 지식의 재구성」——首尔大学博士学位论文, 2022.",
    "2022-02-24": "塔玛拉·特朗塞尔（Tamara A. Trownsell）等. 2021.「Differing about Difference: Relational IR from around the World」. <em>International Studies Perspectives</em> 22(1): 25–64.",
    "2022-01-19": "讨论：<em>Review of International Studies</em> 专号「The Multiple Origins of IR」（2021）",
    "2021-12-29": "特邀研讨：Chun Chae-sung（전재성，首尔大学），不完全主权",
    "2021-12-17": "大卫·布莱尼（David L. Blaney）&middot; 阿琳·蒂克纳（Arlene B. Tickner）. 2017.「Worlding, Ontological Politics and the Possibility of a Decolonial IR」. <em>Millennium</em> 45(3): 293–311.",
    "2021-11-24": "Jungmin Seo &middot; Young Chul Cho. 2021.「The Emergence and Evolution of International Relations Studies in Postcolonial South Korea」. <em>Review of International Studies</em> 47(5): 619–636.",
    "2021-10-24": "莱因哈特·科泽勒克（Reinhart Koselleck）. 2018. <em>Sediments of Time: On Possible Histories</em>. Stanford University Press.",
    "2021-09-24": "Seo-Hyun Park. 2017. <em>Sovereignty and Status in East Asian International Relations</em>. Cambridge University Press.",
    "2021-08-20": "讨论",
    "2021-07-24": "安娜贝尔·布雷特（Annabel S. Brett）. 2011. <em>Changes of State: Nature and the Limits of the City in Early Modern Natural Law</em>. Princeton University Press.",
    "2021-05-22": "C. H. 亚历山德罗维奇（C. H. Alexandrowicz）著，大卫·阿米蒂奇（David Armitage）&middot; 詹妮弗·皮茨（Jennifer Pitts）编. 2017. <em>The Law of Nations in Global History</em>. Oxford University Press.",
    "2021-04-24": "刘禾（Lydia H. Liu）. 2006. <em>The Clash of Empires: The Invention of China in Modern World Making</em>. Harvard University Press.",
    "2021-03-27": "劳伦·本顿（Lauren Benton）、亚当·克卢洛（Adam Clulow）、贝恩·阿特伍德（Bain Attwood）编. 2017. <em>Protection and Empire: A Global History</em>. Cambridge University Press.",
    "2021-02-20": "萨利哈·贝尔梅苏（Saliha Belmessous）编. 2014. <em>Empire by Treaty: Negotiating European Expansion, 1600–1900</em>. Oxford University Press.",
    "2020-12-18": "玛丽亚·阿黛尔·卡拉伊（Maria Adele Carrai）. 2019. <em>Sovereignty in China: A Genealogy of a Concept since 1840</em>. Cambridge University Press.",
    "2020-11-20": "阿米塔·阿查亚（Amitav Acharya）&middot; 巴里·布赞（Barry Buzan）. 2019. <em>The Making of Global International Relations: Origins and Evolution of IR at its Centenary</em>. Cambridge University Press.",
    "2020-10-23": "罗特姆·科夫纳（Rotem Kowner）&middot; 瓦尔特·德梅尔（Walter Demel）编. 2015. <em>Race and Racism in Modern East Asia</em>, 第1卷. Brill.",
    "2020-09-26": "杰里米·耶伦（Jeremy A. Yellen）. 2019. <em>The Greater East Asia Co-Prosperity Sphere: When Total Empire Met Total War</em>. Cornell University Press.",
    "2020-08-22": "阿多姆·盖塔丘（Adom Getachew）. 2019. <em>Worldmaking after Empire: The Rise and Fall of Self-Determination</em>. Princeton University Press.",
    "2020-07-25": "乌尔斯·马蒂亚斯·察赫曼（Urs Matthias Zachmann）编. 2017. <em>Asia after Versailles: Asian Perspectives on the Paris Peace Conference and the Interwar Order, 1919–33</em>. Edinburgh University Press.",
    "2020-06-27": "首次聚会",
}

ZH_META = {
    "2026-07-25": "初版1999年。英译本：Jung-Woon Choi. 2005. <em>The Gwangju Uprising: The Pivotal Democratic Movement that Changed the History of Modern Korea</em>. Homa &amp; Sekey Books, Young-nan Yu 译。",
    "2026-04-18": "稿本",
    "2025-07-21": "东亚研究院（EAI），首尔",
    "2025-04-17": "稿本",
    "2024-12-20": "稿本",
    "2024-10-02": "研究计划书",
    "2024-03-08": "稿本",
    "2023-04-28": "稿本",
    "2023-04-01": "稿本",
    "2023-02-24": "共读河豚会成员的两篇论文",
    "2022-12-09": "附录1：国际政治学术会议，1954年5月7–8日",
    "2022-06-03": "稿本",
    "2021-05-22": "第1–2部分",
}

JA_TITLE = {
    "2026-07-25": "Choi Jung-woon（최정운）. 2012. 『오월의 사회과학』. 오월의봄.",
    "2026-06-24": "夏期セミナー",
    "2026-06-15": "夏期セミナー",
    "2026-04-18": "Sujin Heo「Iberian Early-Modern Languages of Inter-Polity Ordering in Japan」",
    "2026-01-03": "Ha Young-sun（하영선）との対談",
    "2025-07-21": "国際関係論・アジア研究 教育法ワークショップ",
    "2025-04-17": "Chaeyoung Yong「Trauma Time and Memory in Understanding Gender-Based Violence」",
    "2024-12-20": "Inhwan Oh「Explaining the Absence of a War during China&rsquo;s Quantitative Naval Overtake, 2008–2023」",
    "2024-10-02": "Inho Choi「Literary Reconstruction of the 1636 Qing Invasion of Korea」",
    "2024-09-20": "企画会合",
    "2024-03-08": "Minju Kwon &middot; Chaeyoung Yong「Global Human Rights Institutions」",
    "2023-07-24": "国際関係論方法論ワークショップ——「以意逆志」で読む東アジア外交史",
    "2023-04-28": "Inhwan Oh「Racial Hierarchy, Restraint, and the Resolution of the Commitment Problem: Japan&rsquo;s Pursuit of Status and the Washington Naval System, 1921–1936」",
    "2023-04-01": "Chaeyoung Yong「The Politics of Emotional Deference to Self-Esteem: The Case of Japan–US Diplomatic Negotiations in 1951」",
    "2023-02-24": "Inho Choi「On Being Chinese and Being Complexified: Chinese IR as a Transcultural Project」（<em>Review of International Studies</em>, 2022）および「사대의 국제정치이론」（<em>국제정치논총</em> 63-1, 2023）",
    "2023-01-19": "パトリック・サディアス・ジャクソン（Patrick Thaddeus Jackson）&middot; Sujin Heo. 2022.「Working on Relationalism」<em>New Perspectives</em> 30(2): 157–169.",
    "2022-12-09": "ニコラ・ギヨ（Nicolas Guilhot）編. 2011. <em>The Invention of International Relations Theory: Realism, the Rockefeller Foundation, and the 1954 Conference on Theory</em>. Columbia University Press.",
    "2022-10-21": "エドゥアルド・ヴィヴェイロス・デ・カストロ（Eduardo Viveiros de Castro）. 2015.「Who Is Afraid of the Ontological Wolf?」<em>Cambridge Journal of Anthropology</em> 33(1): 2–17. ／ アナベル・ブレット（Annabel Brett）. 2021. <em>Between History, Politics, Law</em>. Cambridge University Press, 第1章.",
    "2022-08-16": "アイシェ・ザラコル（Ayşe Zarakol）. 2022. <em>Before the West: The Rise and Fall of Eastern World Orders</em>. Cambridge University Press.",
    "2022-07-21": "ヴァレリー・デ・クーイエル（Valerie de Koeijer）&middot; ロビー・シリアム（Robbie Shilliam）. 2021.「Forum: International Relations as a Geoculturally Pluralistic Field」<em>International Politics Reviews</em> 9: 272–275.",
    "2022-06-03": "Chang Joon Ok「냉전 초기 한국 국제정치 지식의 재구성」——ソウル大学博士学位論文, 2022.",
    "2022-02-24": "タマラ・トラウンセル（Tamara A. Trownsell）ほか. 2021.「Differing about Difference: Relational IR from around the World」<em>International Studies Perspectives</em> 22(1): 25–64.",
    "2022-01-19": "討論：<em>Review of International Studies</em> 特集号「The Multiple Origins of IR」（2021）",
    "2021-12-29": "招待セミナー：Chun Chae-sung（전재성、ソウル大学）「不完全主権」",
    "2021-12-17": "デイヴィッド・ブレイニー（David L. Blaney）&middot; アーリーン・ティックナー（Arlene B. Tickner）. 2017.「Worlding, Ontological Politics and the Possibility of a Decolonial IR」<em>Millennium</em> 45(3): 293–311.",
    "2021-11-24": "Jungmin Seo &middot; Young Chul Cho. 2021.「The Emergence and Evolution of International Relations Studies in Postcolonial South Korea」<em>Review of International Studies</em> 47(5): 619–636.",
    "2021-10-24": "ラインハルト・コゼレック（Reinhart Koselleck）. 2018. <em>Sediments of Time: On Possible Histories</em>. Stanford University Press.",
    "2021-09-24": "Seo-Hyun Park. 2017. <em>Sovereignty and Status in East Asian International Relations</em>. Cambridge University Press.",
    "2021-08-20": "討論",
    "2021-07-24": "アナベル・ブレット（Annabel S. Brett）. 2011. <em>Changes of State: Nature and the Limits of the City in Early Modern Natural Law</em>. Princeton University Press.",
    "2021-05-22": "C. H. アレクサンドロヴィチ（C. H. Alexandrowicz）著、デイヴィッド・アーミテイジ（David Armitage）&middot; ジェニファー・ピッツ（Jennifer Pitts）編. 2017. <em>The Law of Nations in Global History</em>. Oxford University Press.",
    "2021-04-24": "リディア・リウ（Lydia H. Liu、劉禾）. 2006. <em>The Clash of Empires: The Invention of China in Modern World Making</em>. Harvard University Press.",
    "2021-03-27": "ローレン・ベントン（Lauren Benton）、アダム・クルーロー（Adam Clulow）、ベイン・アトウッド（Bain Attwood）編. 2017. <em>Protection and Empire: A Global History</em>. Cambridge University Press.",
    "2021-02-20": "サリハ・ベルメスス（Saliha Belmessous）編. 2014. <em>Empire by Treaty: Negotiating European Expansion, 1600–1900</em>. Oxford University Press.",
    "2020-12-18": "マリア・アデーレ・カライ（Maria Adele Carrai）. 2019. <em>Sovereignty in China: A Genealogy of a Concept since 1840</em>. Cambridge University Press.",
    "2020-11-20": "アミタフ・アチャリア（Amitav Acharya）&middot; バリー・ブザン（Barry Buzan）. 2019. <em>The Making of Global International Relations: Origins and Evolution of IR at its Centenary</em>. Cambridge University Press.",
    "2020-10-23": "ロテム・コウナー（Rotem Kowner）&middot; ヴァルター・デーメル（Walter Demel）編. 2015. <em>Race and Racism in Modern East Asia</em>, 第1巻. Brill.",
    "2020-09-26": "ジェレミー・イェレン（Jeremy A. Yellen）. 2019. <em>The Greater East Asia Co-Prosperity Sphere: When Total Empire Met Total War</em>. Cornell University Press.",
    "2020-08-22": "アドム・ゲタチュウ（Adom Getachew）. 2019. <em>Worldmaking after Empire: The Rise and Fall of Self-Determination</em>. Princeton University Press.",
    "2020-07-25": "ウルス・マティアス・ツァハマン（Urs Matthias Zachmann）編. 2017. <em>Asia after Versailles: Asian Perspectives on the Paris Peace Conference and the Interwar Order, 1919–33</em>. Edinburgh University Press.",
    "2020-06-27": "初回会合",
}

JA_META = {
    "2026-07-25": "初版1999年。英訳：Jung-Woon Choi. 2005. <em>The Gwangju Uprising: The Pivotal Democratic Movement that Changed the History of Modern Korea</em>. Homa &amp; Sekey Books, Young-nan Yu 訳。",
    "2026-04-18": "草稿",
    "2025-07-21": "東アジア研究院（EAI）、ソウル",
    "2025-04-17": "草稿",
    "2024-12-20": "草稿",
    "2024-10-02": "研究計画書",
    "2024-03-08": "草稿",
    "2023-04-28": "草稿",
    "2023-04-01": "草稿",
    "2023-02-24": "会のメンバー自身の論文二本を併読",
    "2022-12-09": "付録1：国際政治学術会議、1954年5月7–8日",
    "2022-06-03": "草稿",
    "2021-05-22": "第1–2部",
}


def main() -> None:
    path = Path(__file__).resolve().parent.parent / "data" / "seminars.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    missing = []
    for e in data["entries"]:
        iso = e["iso"]
        if iso not in ZH_TITLE or iso not in JA_TITLE:
            missing.append(iso)
            continue
        e["title"]["zh"] = ZH_TITLE[iso]
        e["title"]["ja"] = JA_TITLE[iso]
        if "meta" in e:
            en = e["meta"]["en"]
            e["meta"]["zh"] = ZH_META.get(iso, en)
            e["meta"]["ja"] = JA_META.get(iso, en)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(data['entries']) - len(missing)}건 중국어·일본어 표기 추가"
          + (f", 누락 {missing}" if missing else ""))


if __name__ == "__main__":
    main()
