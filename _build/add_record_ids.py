# -*- coding: utf-8 -*-
"""data/*.json 의 모든 항목에 바뀌지 않는 식별자를 붙인다.

여러 사람이 동시에 편집할 때, 저장은 파일 하나를 통째로 쓰는 일이라 서로 다른
항목을 고쳐도 충돌한다. 항목마다 식별자가 있으면 편집 화면이 "내가 바꾼 항목만"
남의 최신본 위에 얹을 수 있고, 같은 항목을 동시에 건드린 경우에만 충돌이 남는다.

한 번만 돌리면 된다. 이미 id 가 있는 항목은 건드리지 않는다.

    python _build/add_record_ids.py
"""
import json
import secrets
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).resolve().parent.parent / "data"
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def new_id(taken: set) -> str:
    while True:
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if candidate not in taken:
            taken.add(candidate)
            return candidate


def record_lists(name: str, data: dict):
    """편집 화면이 실제로 다루는 배열들만 돌려준다."""
    if name == "publications":
        for group in data["themes"] + data["other_groups"]:
            yield group["entries"]
    elif name == "seminars":
        yield data["entries"]
    elif name == "members":
        yield data["people"]
    elif name == "resources":
        for group in data["reading"]:
            yield group["entries"]
        for block in data["link_blocks"]:
            for group in block["groups"]:
                yield group["entries"]


def main() -> None:
    taken, total, added = set(), 0, 0

    for name in ("publications", "seminars", "members", "resources"):
        path = DATA / f"{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entries in record_lists(name, data):
            for rec in entries:
                total += 1
                if rec.get("id"):
                    taken.add(rec["id"])

    for name in ("publications", "seminars", "members", "resources"):
        path = DATA / f"{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for entries in record_lists(name, data):
            for i, rec in enumerate(entries):
                if not rec.get("id"):
                    # id 를 맨 앞에 두어 파일을 눈으로 읽을 때 찾기 쉽다.
                    # 자리는 enumerate 로 잡는다 — index() 는 값이 같은 항목에서 어긋난다
                    entries[i] = {"id": new_id(taken), **rec}
                    count += 1
        if count:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        added += count
        print(f"  {name:14} {count:4}건에 식별자 부여")

    print(f"항목 {total}건 중 {added}건에 새로 부여, {total - added}건은 이미 있었음")


if __name__ == "__main__":
    main()
