# -*- coding: utf-8 -*-
"""공유 카드용 이미지(1200×630 PNG)를 만든다.

og:image 로 SVG 를 걸어 두었는데, 페이스북·트위터·카카오톡·구글 어느 쪽도 SVG 를
미리보기로 쓰지 않는다. 링크를 붙여넣으면 그림 없이 제목만 나온다. 그래서 히어로와
같은 복어 모래 원 기하를 PNG 로 그려 둔다.

    python _build/make_og_image.py
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

W, H = 1200, 630
OUT = Path(__file__).resolve().parent.parent / "assets" / "share-card.png"

BAND = (245, 249, 250)
TEAL = (14, 116, 144)
INK = (28, 37, 41)
MUTED = (125, 136, 141)
SAND = (168, 118, 63)

SERIF = "C:/Windows/Fonts/cambriab.ttf"       # 라틴 세리프, 히어로의 Spectral 과 결이 맞는다
SANS = "C:/Windows/Fonts/segoeui.ttf"


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def sand_circle(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> None:
    """히어로와 같은 흰점박이복어 산란 구조물의 기하."""
    def polar(r, t):
        return cx + r * scale * math.cos(t), cy + r * scale * math.sin(t)

    def ridge(r_in, r_out, theta, half, fill):
        a, b = polar(r_in, theta), polar(r_out, theta)
        mid = r_in + (r_out - r_in) * 0.5
        c = polar(mid, theta - half * 1.0)
        d = polar(mid, theta + half * 1.0)
        draw.polygon([a, c, b, d], fill=fill)

    for i in range(28):
        t = 2 * math.pi * i / 28
        ridge(352, 520, t, 0.055, (222, 235, 238))
        ridge(360, 452, t + math.pi / 28, 0.030, (231, 241, 243))
    for i in range(24):
        t = 2 * math.pi * i / 24 + math.pi / 24
        ridge(158, 246, t, 0.048, (216, 232, 236))
    for r, width in ((352, 2), (250, 2), (150, 2)):
        box = [cx - r * scale, cy - r * scale, cx + r * scale, cy + r * scale]
        draw.ellipse(box, outline=(206, 226, 231), width=width)
    for i in range(28):
        t = 2 * math.pi * i / 28
        for rr, rad in ((392, 3), (444, 2)):
            x, y = polar(rr, t)
            draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(226, 214, 196))


def main() -> None:
    img = Image.new("RGB", (W, H), BAND)
    draw = ImageDraw.Draw(img)

    sand_circle(draw, W * 0.5, H * 0.46, scale=0.62)

    # 원 위로 흰 기운을 덮어 글자가 읽히게 한다
    veil = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    ImageDraw.Draw(veil).ellipse([W * 0.5 - 520, H * 0.46 - 380, W * 0.5 + 520, H * 0.46 + 380],
                                 fill=(255, 255, 255, 150))
    img = Image.alpha_composite(img.convert("RGBA"), veil).convert("RGB")
    draw = ImageDraw.Draw(img)

    title = font(SERIF, 74)
    sub = font(SANS, 27)
    tag = font(SANS, 24)

    def centered(text, y, fnt, fill, spacing=0):
        if spacing:
            widths = [draw.textlength(ch, font=fnt) for ch in text]
            total = sum(widths) + spacing * (len(text) - 1)
            x = (W - total) / 2
            for ch, w in zip(text, widths):
                draw.text((x, y), ch, font=fnt, fill=fill)
                x += w + spacing
        else:
            w = draw.textlength(text, font=fnt)
            draw.text(((W - w) / 2, y), text, font=fnt, fill=fill)

    centered("Circle of the Fish", 216, title, INK)
    centered("GLOBALIZING IR FROM EAST ASIA", 316, sub, MUTED, spacing=3.4)
    centered("Kautilya never asked the fish what it is like to live as one.", 404, tag, TEAL)

    draw.rectangle([0, H - 8, W, H], fill=TEAL)
    draw.rectangle([W * 0.5 - 46, 372, W * 0.5 + 46, 373], fill=SAND)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"{OUT} — {W}×{H}, {OUT.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
