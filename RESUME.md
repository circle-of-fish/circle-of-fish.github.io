# 재개 지점

2026-08-20 작업 중단 시점의 상태입니다. 이어서 할 일과 이미 끝난 일을 구분해 둡니다.

## 지금 상태로 할 수 있는 것

```bash
cd c:/Users/inhoc/Projects/circle-of-fish
python build.py --serve --port 8000     # 빌드 후 http://localhost:8000
python build.py --serve --no-build      # 빌드 없이 미리보기만
```

4개 언어 28개 페이지가 모두 정상 빌드됩니다. 저장소 루트에서 그대로 발행되므로,
GitHub Pages는 `main` 브랜치 루트만 지정하면 됩니다.

## 끝난 것

- 정적 사이트 생성기(`build.py`) + 템플릿 7종 + `data/*.json` 콘텐츠 원본
- 4개 언어(en·ko·zh·ja), 언어 전환, hreflang·canonical·sitemap
- 복어 모래 원 히어로 SVG(`_build/make_fish_circle.py`가 기하학적으로 생성)
- 구성원 9인: 확인된 소속·한글 이름·개인 홈페이지/ORCID/Scholar 링크, 이메일은 링크 없이 표기
- 출판 136편: 주제 9갈래 분류, 2문장 요약, 검증된 전문 링크 24건
- 세미나 41건 아카이브 (영문·국문)
- 자료·링크 137건 (학자 40, 사료·DB 34, 도구 25, 학술지 15, 연구기관 12, 네트워크 11)
- 이론적·방법론적 지향 각 5항목 — 구성원들의 실제 논문에 근거해 서술
- 산문 302건 한·중·일 번역 적용

## 이어서 할 일 (우선순위 순)

### 1. 중국어·일본어판 세미나 표기 (진행하다 중단)

한국어판만 한글로 옮겨져 있고 zh·ja는 영문 그대로입니다.
입력 파일은 이미 만들어 두었습니다 — `research/seminars_for_translation.json` (41건).

중단한 워크플로를 캐시에서 이어서 돌릴 수 있습니다:

```
Workflow({scriptPath: "…/workflows/scripts/cof-seminars-zh-ja.js",
          resumeFromRunId: "wf_755c18e1-9cd"})
```

결과를 `data/seminars.json`의 각 entry `title`/`meta` 묶음에 `zh`·`ja` 키로 넣으면 됩니다.

### 2. 출판 목록 필터 (착수 직후 중단)

136편이라 구성원·언어·전문공개 여부로 걸러 보는 기능이 필요합니다.
`build.py`에 `memberkey` 필터(밑줄→하이픈)만 추가해 둔 상태이고, 나머지는 미착수입니다.
필요한 것: `templates/publications.html.j2`의 `.pub`에 `data-members`·`data-lang`·`data-oa`
속성 부여, `assets/filter.js`, 필터 바 UI, 주제별·전체 건수 갱신.

### 3. 추가 항목 검토 결과 (사용자 판단 필요)

연구 종합이 권고한 11개 항목 중 이미 반영한 것과 남은 것:

| 항목 | 상태 |
| --- | --- |
| 주제별 연구 갈래 | **반영** (9갈래) |
| 전문 공개 여부가 붙은 출판 라이브러리 | **반영** (필터는 위 2번) |
| 구성원 페이지 최신화·식별자 | **반영** |
| 사료·도구 안내 | **반영** (자료·링크 137건) |
| 다국어 제공 | **반영** (4개 언어) |
| 세미나 아카이브 주석화 | 미반영 — 지금은 목록. 무엇을 왜 읽었고 무엇이 나왔는지 덧붙이면 대학원생이 인용하는 자료가 됨 |
| **개념 사전** | 미반영 — 바로 만들 수 있음. interpolity order·aretocracy·존재론적 복합성·국가의 덕·공생적 국가·문명의 표준·사대·세(勢)·일어난 미래·以意逆志·전염 효과·개체화·실효적 평화·행성적 공진화 등 14~15항목, 각 2문장 + 읽을 논문 링크 |
| **방법론 랩(以意逆志)** | 미반영 — 복어회의 가장 독자적인 자산인데 현재는 지향 카드 한 장뿐. 2023년 5일 워크숍 틀 + 최인호·권민주 EJIR 논문을 실제 예시로 |
| 워킹페이퍼 + 원고 요청 | 구성원 협조 필요 — 초록과 심사 중 여부 확인 |
| 강의계획서 공유 | 구성원 협조 필요 — 2025년 EAI 교수법 워크숍 산출물 |
| 원로 학자 대담 시리즈 | 구성원 협조 필요 — 2026-01-03 하영선 대담이 이미 있음 |

수집해 둔 구성원 활동 **156건**(수상 6·연구비 13·펠로십 18·학회 29·워크숍 28·강의 14·
언론 4·편집위원 3 등)이 `research/dossier.json`에 있습니다. 소식·활동 페이지를 만들거나
구성원 카드에 최근 활동 한 줄을 넣는 데 쓸 수 있습니다.

### 4. GitHub 배포

`https://circle-of-fish.github.io/` 로 가려면 **조직 `circle-of-fish`를 먼저 웹에서
생성**해야 합니다(API·CLI 불가): <https://github.com/organizations/plan>

조직이 생기면:

```bash
gh repo create circle-of-fish/circle-of-fish.github.io --public --source=. --push
gh api -X POST repos/circle-of-fish/circle-of-fish.github.io/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

현재 `gh` 계정은 `simoninhochoi`이고 `admin:org` 스코프가 없습니다. 저장소 생성만이면
필요 없을 것으로 보이나, 막히면 `gh auth refresh -h github.com -s admin:org`.

## 확인이 필요한 사항

`NOTES.md` 참조. 남은 것은 한자 이름(전원 미확인, 옥창준 玉昌埈만 확인)과
`research/report.md`에 정리된 귀속 불확실 항목 몇 건입니다.
