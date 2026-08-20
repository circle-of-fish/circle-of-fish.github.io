# cof-editor — 편집 API

`/admin/`이 아이디·비밀번호로 동작하게 하는 작은 서버입니다. 사이트 자체는 GitHub
Pages에 그대로 있고, 이 Worker는 **비밀번호 확인과 저장소 커밋만** 맡습니다.

    구성원 → 아이디·비밀번호 → [이 Worker] → 저장소 커밋 → Actions 재빌드 → 사이트

정적 사이트만으로는 비밀번호를 확인할 수 없습니다. 브라우저가 확인할 수 있는 것은
독자도 읽을 수 있고, 저장소 쓰기 토큰이 그 옆에 나란히 놓이게 됩니다. 그래서 확인이
여기에 있습니다. 비밀번호 해시와 GitHub 토큰은 이 Worker 바깥으로 나가지 않습니다.

## 엔드포인트

| | | |
|---|---|---|
| `POST` | `/api/login` | `{username, password}` → 세션 토큰 (12시간) |
| `POST` | `/api/password` | 자기 비밀번호 변경 |
| `GET` | `/api/data` | 네 개 데이터 파일 전부 + 각 sha |
| `PUT` | `/api/data/:file` | 파일 하나 커밋 |
| `POST` | `/api/photo/:key` | 구성원 사진 교체 + 크기 기록 |

커밋 작성자에는 편집자 이름이 들어갑니다. 토큰은 하나지만 기록상 누가 고쳤는지 남습니다.

## 처음 한 번 설치

`worker/` 안에서 실행합니다.

```bash
# 1. Cloudflare 로그인 (브라우저에서 Allow 한 번)
npx wrangler login

# 2. 편집자 계정을 넣을 KV 네임스페이스
npx wrangler kv namespace create USERS
#    → 출력된 id 를 wrangler.toml 의 PLACEHOLDER_KV_ID 자리에 넣는다

# 3. 비밀 값 두 개
npx wrangler secret put GITHUB_TOKEN     # 세분화 PAT, 이 저장소 Contents: Read and write
npx wrangler secret put SESSION_SECRET   # 아무 임의 문자열 (아래 명령으로 생성 가능)
#    python -c "import secrets;print(secrets.token_urlsafe(48))"

# 4. 배포
npx wrangler deploy
#    → https://cof-editor.<계정>.workers.dev
```

## 편집자 추가

```bash
python ../_build/seed_editors.py 최인호:inho 오인환:inhwan …
```

임시 비밀번호가 화면에 한 번 나옵니다. 그때 각자에게 전달하십시오 — 첫 로그인 때
바꾸게 되어 있습니다. 이어서 안내되는 `wrangler kv key put …` 명령을 실행하면 계정이
올라갑니다. `worker/seed/` 는 저장소에 올라가지 않습니다.

편집자를 빼려면:

```bash
npx wrangler kv key delete --binding USERS --remote "<아이디>"
```

## GitHub 토큰

<https://github.com/settings/personal-access-tokens/new>

- Resource owner: `circle-of-fish`
- Repository access: `circle-of-fish.github.io` 하나만
- Permissions → Repository → **Contents: Read and write** 하나만
- 만료일이 오면 `npx wrangler secret put GITHUB_TOKEN` 으로 새 값을 넣으면 됩니다

토큰 소유자 계정이 조직에 쓰기 권한을 갖고 있어야 하고, 조직 설정에서 세분화 토큰이
허용되어 있어야 합니다(Settings → Third-party Access → Personal access tokens).

## 비밀번호 규격

PBKDF2-SHA256, **100,000회**, 사용자마다 16바이트 salt.

10만은 Workers가 허용하는 상한입니다(그 이상은 `Pbkdf2 failed: iteration counts above
100000 are not supported`로 거부됩니다). 일반 권고치보다 낮으므로 비밀번호 자체를 강하게
잡았습니다 — 발급되는 임시 비밀번호는 56자 알파벳에서 뽑은 16자(약 93비트)이고,
직접 바꿀 때는 열두 자 이상을 요구합니다.
저장 형태는 `pbkdf2$<반복>$<base64 salt>$<base64 hash>` 이며,
`_build/seed_editors.py`(파이썬)와 `src/index.js`(Worker)가 같은 값을 만들어 냅니다.

없는 아이디로 들어와도 해시 계산을 한 번 하고 답합니다. 아이디가 있는지 없는지가
응답 시간으로 새어 나가지 않게 하기 위한 것입니다.
