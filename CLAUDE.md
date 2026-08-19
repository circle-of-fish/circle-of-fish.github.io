# Circle of the Fish — 웹사이트 (복어회)

기존 Google Sites(`https://sites.google.com/chapman.edu/circle-of-fish/home`)를
GitHub Pages로 확장 이전하는 작업 폴더. 디자인 참조는
`https://complex-intelligence.github.io/` (같은 레이아웃 DNA, 다른 팔레트).

## 구조

```
data/          ← 콘텐츠 원본(JSON). 여기만 고치면 4개 언어가 함께 바뀐다.
templates/     ← Jinja2 템플릿 (base + 페이지 7종)
assets/        ← style.css, fish-circle.svg, favicon.svg → 빌드 시 루트로 복사
_build/        ← 일회성 임포트·생성 스크립트(모래원 SVG, 세미나 목록, 연구 병합 등)
research/      ← 연구 원자료(dossier.json)·정리 보고서·번역 배치
build.py       ← 정적 사이트 생성기
*.html · ko/ · zh/ · ja/ · style.css …
               ← **빌드 산출물. 직접 고치지 말 것.** 저장소 루트에서 그대로 발행된다
```

빌드·미리보기:

```bash
python build.py                      # 산출물 재생성
python build.py --serve --port 8000  # 빌드 후 http://localhost:8000
python build.py --serve --no-build   # 다시 빌드하지 않고 미리보기만
```

산출물이 소스와 같은 폴더에 놓이므로, 빌드는 **자기가 만든 파일만** 지운다
(`generated_paths()`). 새 페이지·에셋을 추가하면 이 목록에 자동으로 잡히지만,
빌드가 만들지 않는 파일을 산출물 폴더에 두지 말 것.

## 다국어 규약

- 언어 4종: `en`(루트) · `ko` · `zh`(간체) · `ja`. 출력은 `index.html`,
  `ko/index.html`, `zh/...`, `ja/...`.
- JSON 안에서 번역 대상은 `{"en": ..., "ko": ..., "zh": ..., "ja": ...}` 묶음으로 쓴다.
  **번역이 없으면 자동으로 `en`으로 대체**되므로 일부만 채워도 빌드는 된다.
- 문자열이 그냥 `"..."`이면 모든 언어에서 같은 값으로 쓰인다.
  **서지 정보(저자·제목·게재지)는 원어 그대로 두는 것이 원칙** — 번역하지 않는다.
  번역하는 것은 요약·해설·UI 문구뿐이다.
- 언어 전환 링크는 같은 페이지의 다른 언어판으로 간다(상대 경로).

## 함정

- **JSON 키로 `items`를 쓰지 말 것.** Jinja2에서 `x.items`가 dict 메서드로 잡힌다.
  목록 키는 `entries`를 쓴다.
- 템플릿은 `StrictUndefined`다. 레코드마다 있을 수도 없을 수도 있는 필드는
  `x.get('field')`로 접근해야 한다(오타는 그대로 에러로 잡히도록).
- 서지 항목의 `title`·`venue`, 세미나 `title`·`meta`에는 `<em>` 같은 마크업을
  넣을 수 있다(템플릿에서 `|safe`). 그 외 필드는 이스케이프된다.
- `docs/` 삭제는 best-effort다 — 미리보기 서버가 떠 있으면 Windows가 디렉터리를
  잡고 있어 지워지지 않는다. 빌드는 덮어쓰기로 계속 진행된다.
- 미리보기 서버는 `python -m http.server ... --directory docs`로 띄울 것.
  `cd docs` 후에 띄우면 이후 빌드에서 디렉터리 잠금이 걸린다.
- headless Chrome 스크린샷은 Windows 디스플레이 배율 때문에 `--window-size`보다
  넓은 뷰포트로 렌더된다. 잘려 보여도 레이아웃 버그가 아닐 수 있다.

## 사실 확인이 필요한 항목

`NOTES.md` 참조 — 원본 사이트에서 낡았거나 모호한 정보를 모아 두었다.
