# -*- coding: utf-8 -*-
"""Generate the pufferfish sand-circle hero motif as an SVG.

The male white-spotted pufferfish (Torquigener albomaculatus) ploughs a ~2 m
geometric nest into the seabed: an outer field of radial ridges and valleys,
a smoother inner ring, and a fine decorative pattern at the centre.  The site's
name comes from that circle, so the hero background reproduces its geometry
rather than a stock texture.
"""
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

W = H = 1200
CX = CY = W / 2

# ridge counts follow the observed nest: many fine outer spokes, fewer inner ones
OUTER_SPOKES = 28
INNER_SPOKES = 24


def polar(r, theta):
    return CX + r * math.cos(theta), CY + r * math.sin(theta)


def petal_path(r_in, r_out, theta, half_width, curve=0.34):
    """One radial ridge: a slim leaf reaching outward from r_in to r_out."""
    a0, a1 = theta - half_width, theta + half_width
    x_in, y_in = polar(r_in, theta)
    x_out, y_out = polar(r_out, theta)
    r_mid = r_in + (r_out - r_in) * 0.5
    xa, ya = polar(r_mid, theta - half_width * curve * 3.0)
    xb, yb = polar(r_mid, theta + half_width * curve * 3.0)
    return (
        f"M{x_in:.1f},{y_in:.1f} "
        f"Q{xa:.1f},{ya:.1f} {x_out:.1f},{y_out:.1f} "
        f"Q{xb:.1f},{yb:.1f} {x_in:.1f},{y_in:.1f} Z"
    )


parts = []
add = parts.append

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Pufferfish sand circle">')
# no background rect: the motif has to composite over whatever colour the
# hero band is, or its own panel shows as a visible rectangle
add("""  <defs>
    <radialGradient id="core" cx="50%" cy="50%" r="50%">
      <stop offset="0%"   stop-color="#ffffff" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>""")

TEAL = "#0e7490"
SAND = "#a8763f"

# --- outer ridge field -------------------------------------------------------
add(f'  <g fill="{TEAL}">')
for i in range(OUTER_SPOKES):
    th = 2 * math.pi * i / OUTER_SPOKES
    add(f'    <path d="{petal_path(352, 520, th, 0.055)}" opacity="0.13"/>')
    # a shorter counter-ridge sits in each valley
    th2 = th + math.pi / OUTER_SPOKES
    add(f'    <path d="{petal_path(360, 452, th2, 0.030)}" opacity="0.09"/>')
add("  </g>")

# --- ring boundaries ---------------------------------------------------------
for r, op, wid, dash in (
    (352, 0.30, 1.6, ""),
    (338, 0.14, 1.0, ""),
    (250, 0.28, 1.4, ""),
    (238, 0.12, 1.0, ' stroke-dasharray="3 7"'),
    (150, 0.26, 1.2, ""),
):
    add(f'  <circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="{TEAL}" stroke-opacity="{op}" stroke-width="{wid}"{dash}/>')

# --- inner ridge field -------------------------------------------------------
add(f'  <g fill="{TEAL}">')
for i in range(INNER_SPOKES):
    th = 2 * math.pi * i / INNER_SPOKES + math.pi / INNER_SPOKES
    add(f'    <path d="{petal_path(158, 246, th, 0.048)}" opacity="0.16"/>')
add("  </g>")

# --- centre: the fine decorative pattern the fish combs last -----------------
add(f'  <g stroke="{SAND}" fill="none" stroke-opacity="0.20">')
for i in range(INNER_SPOKES * 2):
    th = 2 * math.pi * i / (INNER_SPOKES * 2)
    x0, y0 = polar(58, th)
    x1, y1 = polar(146, th)
    add(f'    <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke-width="0.9"/>')
for r in (72, 92, 112, 132):
    add(f'    <circle cx="{CX}" cy="{CY}" r="{r}" stroke-width="0.7"/>')
add("  </g>")

# --- scattered shell fragments the fish lays along the ridges ----------------
add(f'  <g fill="{SAND}" opacity="0.30">')
for i in range(OUTER_SPOKES):
    th = 2 * math.pi * i / OUTER_SPOKES
    for rr, rad in ((392, 2.4), (444, 1.8), (492, 1.3)):
        x, y = polar(rr, th)
        add(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}"/>')
add("  </g>")

add(f'  <circle cx="{CX}" cy="{CY}" r="150" fill="url(#core)"/>')
add("</svg>")

out = "c:/Users/inhoc/Projects/circle-of-fish/assets/fish-circle.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
print(f"wrote {out} ({len('\n'.join(parts))} bytes)")
