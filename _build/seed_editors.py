# -*- coding: utf-8 -*-
"""편집자 계정을 만들어 Cloudflare KV에 넣을 형태로 출력한다.

비밀번호는 여기서 임의로 만든다. 만들어진 비밀번호는 이 화면에 한 번만 나오므로
그때 각자에게 전달하고, 첫 로그인 때 바꾸게 한다(must_change).

    python _build/seed_editors.py 최인호:inho 오인환:inhwan …
    python _build/seed_editors.py --from editors.txt        # "이름:아이디" 한 줄에 하나

해시 형식은 Worker(src/index.js)의 PBKDF2-SHA256 규격과 같아야 한다 —
pbkdf2$<반복>$<base64 salt>$<base64 hash>
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROUNDS = 100000
OUT = Path(__file__).resolve().parent.parent / "worker" / "seed"

# 서로 헷갈리는 글자(l/1/I, O/0)를 뺐다 — 받아 적다 틀리는 일이 없도록
ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def make_password(words: int = 4) -> str:
    """읽어서 옮겨 적을 수 있는 길이의 임의 비밀번호."""
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(words))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ROUNDS, dklen=32)
    return "pbkdf2${}${}${}".format(
        ROUNDS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("editors", nargs="*", help="이름:아이디")
    ap.add_argument("--from", dest="path", help="이름:아이디 목록 파일")
    args = ap.parse_args()

    raw = list(args.editors)
    if args.path:
        raw += [l.strip() for l in Path(args.path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not raw:
        raise SystemExit("편집자를 하나 이상 지정하십시오. 예: python _build/seed_editors.py 최인호:inho")

    OUT.mkdir(parents=True, exist_ok=True)
    handout, commands = [], []
    for item in raw:
        if ":" not in item:
            raise SystemExit(f"'이름:아이디' 형식이어야 합니다 — {item}")
        name, username = (part.strip() for part in item.split(":", 1))
        username = username.lower()
        if not username.replace("-", "").isalnum():
            raise SystemExit(f"아이디는 영문·숫자·하이픈만 씁니다 — {username}")

        password = make_password()
        record = {"username": username, "name": name,
                  "hash": hash_password(password), "must_change": True}
        (OUT / f"{username}.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8")
        handout.append((name, username, password))
        commands.append(
            f'npx wrangler kv key put --binding USERS --remote "{username}" '
            f'--path seed/{username}.json')

    print("\n=== 각자에게 전달할 것 (이 화면에만 나옵니다) ===\n")
    print(f"  {'이름':<10} {'아이디':<12} 임시 비밀번호")
    print(f"  {'-'*10} {'-'*12} {'-'*22}")
    for name, username, password in handout:
        print(f"  {name:<10} {username:<12} {password}")
    print("\n  첫 로그인 때 각자 비밀번호를 바꾸게 됩니다.\n")

    print("=== worker/ 에서 실행할 것 ===\n")
    for c in commands:
        print("  " + c)
    print(f"\n  (해시만 담긴 파일 {len(handout)}개가 {OUT} 에 있습니다.")
    print("   KV에 넣은 뒤에는 지워도 됩니다 — worker/seed/ 는 .gitignore 대상입니다.)")


if __name__ == "__main__":
    main()
