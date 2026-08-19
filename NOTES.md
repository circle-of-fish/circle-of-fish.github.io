# 확인이 필요한 사항

기존 Google Sites에서 옮겨 오면서 낡았거나, 모호하거나, 손을 댄 항목들.
**괄호 안이 새 사이트에 현재 반영된 값**입니다.

## 1. 최인호 선생님 소속 (수정함)

기존 사이트: "Senior Researcher, Institute of International Studies, Seoul National University"
→ 새 사이트: **경기대학교 정치외교학과 교수** (`data/members.json`)

## 2. 세미나 날짜 하나 (수정함)

기존 사이트의 "12/29/2022 Seminar with Chaesung Chun (Seoul National University),
Incomplete Sovereignty" 항목이 목록에서 **2022년 1월 19일 항목과 2021년 12월 17일
항목 사이에** 놓여 있었습니다. 나머지 전체가 엄격한 역순이라 오타로 보고
**2021-12-29**로 넣었습니다. 아니라면 `data/seminars.json`에서 고쳐 주십시오.

## 3. "Interpolity Order Beyond Asia" (일단 뺐음)

세미나 페이지 맨 위에 이 한 줄이 단독으로 있었습니다(og:description에도 이 문구만
잡힙니다). 2026-07-25 최정운 『오월의 사회과학』 항목 바로 위에 있는데 그 책과는
내용이 맞지 않아, **현재 진행 중인 독회 주제 표지**인지 개별 세션 제목인지
판단하지 못했습니다. 새 사이트에는 넣지 않았습니다. 알려 주시면 세미나 페이지
상단의 주제 표지로 넣겠습니다.

## 4. 원본의 오탈자 (고침)

- Module 2 연구 영역: "race and gener" → **gender**
- Module 2 연구 영역: "pluriversial" → **pluriversal**
- 구성원 페이지: "Poltical Science, Acad emy of Korean Studies" → **Political Science,
  Academy of Korean Studies**

## 5. 송지예 선생님 이메일

기존 사이트에 `jeeye song@korea.ac.kr`로 **가운데 공백이 들어간 채** 적혀 있었습니다.
`jeeyesong@korea.ac.kr`로 적어 두었으니 확인 부탁드립니다.

## 6. 한글·한자 이름

구성원 카드에 한글 이름(영문판) / 한자 이름(CJK판)을 넣는 자리를 만들어 두었습니다.
현재 확실한 세 분만 채워 두었습니다 — 최인호·오인환·옥창준.
나머지 여섯 분의 한글 표기는 추측하지 않고 비워 두었습니다. 알려 주시면 채우겠습니다.
(한자 표기도 확인이 필요합니다 — 현재 값은 통용 표기 추정입니다.)

## 7. 그룹 대표 연락처

기존 사이트에는 그룹 공용 연락처가 없어, 구성원 페이지에 공개돼 있던
`inho.choi86@gmail.com`을 소개·홈 페이지의 문의처로 썼습니다. 별도 주소를
쓰시려면 `data/site.json`의 `contact.email`만 바꾸면 됩니다.

## 8. GitHub 저장소 이름

`build.py`의 `BASE_URL`이 `https://circle-of-fish.github.io`로 되어 있습니다.
실제 저장소 이름이 정해지면 이 값을 바꿔야 canonical·hreflang·sitemap이 맞습니다.
