# -*- coding: utf-8 -*-
"""원본 Google Sites 구성원 페이지에서 프로필 이미지를 가져와 assets/photos/ 에 넣는다.

구성원마다 고른 이미지가 제각각이다 — 증명사진도 있고, 삽화도, 물고기 그림도,
케이크 사진도 있다. 자르지 않는다. 원본 비율 그대로 두고 짧은 쪽만 320px로 줄여
저장하며, 각 사진의 크기를 data/members.json에 적어 둔다. 사이트는 그 값으로
width·height 속성을 채워 이미지가 로드되기 전에도 자리를 잡는다.

이미지 URL은 서명이 붙어 있어 몇 시간이면 만료된다. 그래서 페이지를 매번 새로
받아 그 자리에서 내려받는다. 이미지가 바뀌었을 때만 다시 돌리면 된다.

    python _build/fetch_member_photos.py
"""
import html
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

SRC = "https://sites.google.com/chapman.edu/circle-of-fish/member"
OUT = Path(__file__).resolve().parent.parent / "assets" / "photos"
SHORT_SIDE = 320

# 페이지에서 이미지는 언제나 해당 구성원의 <h3> 바로 앞에 온다. 이름으로 짝을 맞춘다.
NAME_TO_KEY = {
    "Inho Choi": "inho-choi", "Sujin Heo": "sujin-heo", "Jaeyoung Kim": "jaeyoung-kim",
    "Minju Kwon": "minju-kwon", "Inhwan Oh": "inhwan-oh", "Chang Joon Ok": "chang-joon-ok",
    "Kayeon Roh": "kayeon-roh", "Jeeye Song": "jeeye-song", "Chaeyoung Yong": "chaeyoung-yong",
}


def fetch(url: str, referer: str | None = None) -> bytes:
    cmd = ["curl", "-sL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", url]
    if referer:
        cmd += ["-e", referer]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def main() -> None:
    page = fetch(SRC).decode("utf-8", errors="replace")

    marks = []
    for m in re.finditer(r'src="(https://lh3\.googleusercontent\.com/sitesv/[^"]+)"', page):
        if "5OWXMRpQ" in m.group(1):        # 사이트 로고, 구성원 사진이 아니다
            continue
        marks.append((m.start(), "img", html.unescape(m.group(1))))
    for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", page, re.S):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip()
        if text in NAME_TO_KEY:
            marks.append((m.start(), "name", text))
    marks.sort()

    pairs, pending = {}, None
    for _, kind, value in marks:
        if kind == "img":
            pending = value
        elif pending:
            pairs[NAME_TO_KEY[value]] = pending
            pending = None

    missing = set(NAME_TO_KEY.values()) - set(pairs)
    if missing:
        print(f"경고: 사진을 찾지 못한 구성원 — {sorted(missing)}")

    OUT.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for key, url in pairs.items():
        raw = fetch(url, referer="https://sites.google.com/")
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = im.size
        scale = SHORT_SIDE / min(w, h)
        if scale < 1:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        path = OUT / f"{key}.jpg"
        im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
        sizes[key] = {"w": im.size[0], "h": im.size[1]}
        print(f"  {key:15} {im.size[0]}×{im.size[1]}  {path.stat().st_size // 1024}KB")

    # 사이트가 원본 비율을 알아야 이미지 자리를 미리 잡을 수 있다
    members_path = OUT.parent.parent / "data" / "members.json"
    members = json.loads(members_path.read_text(encoding="utf-8"))
    for m in members["people"]:
        if m["key"] in sizes:
            m["photo"] = sizes[m["key"]]
        else:
            m.pop("photo", None)
    members_path.write_text(json.dumps(members, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(f"{len(pairs)}장 저장 → {OUT}, 크기를 data/members.json에 기록")


if __name__ == "__main__":
    main()
