#!/usr/bin/env python3
"""Extra clean-room drawing helpers for the machines_power batch.

Builds on draw_lib.py (owned by the style lead; not edited here). Pure stdlib.
Adds winding/coil glyphs (transformer windings, chokes, current transformers)
and a radius picker for rotating-machine circles so the measured box matches the
spec size. See cleanroom/STYLE.md for the house style these encode.
"""
import math
from draw_lib import STD_LW


def pick_r(pins, w, h, lo=10):
    """Best circle radius (centred on origin) so that the union of the circle
    (+/-r in x and y) and the fixed pin coordinates fills the spec box w x h.
    Used for rotating machines and current-transformer core rings."""
    xs = [x for x, _ in pins] + [0]
    ys = [y for _, y in pins] + [0]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    hi = max(w, h) // 2 + 1
    cand = []
    for r in range(lo, max(hi, lo + 1) + 1, 2):
        bw = max(xmax, r) - min(xmin, -r)
        bh = max(ymax, r) - min(ymin, -r)
        err = abs(bw - w) / max(w, 1) + abs(bh - h) / max(h, 1)
        cand.append((err, r))
    be = min(e for e, _ in cand)
    # largest radius among the best: puts on-circle pins exactly on the body
    # (no spurious radial lead), instead of the smallest tied radius.
    return max(r for e, r in cand if e <= be + 1e-9)


def winding_bumps_v(p, ax, y0, y1, n, bulge, lw=STD_LW):
    """EN 60617 winding: a column of n semicircular loops ('bumps') along a
    vertical axis at x=ax, from y0..y1, each bulging horizontally by `bulge`
    (signed: + right, - left)."""
    pts = []
    step = (y1 - y0) / n
    r = abs(step) / 2.0
    for k in range(n):
        yc = y0 + step * (k + 0.5)
        for i in range(13):
            a = -math.pi / 2 + math.pi * i / 12.0
            pts.append((ax + bulge * math.cos(a), yc + r * math.sin(a)))
    p.polyline(pts, lw)


def coil_h(p, x0, x1, yaxis, n, bulge, lw=STD_LW):
    """n semicircular humps along a horizontal axis from x0..x1 bulging by
    `bulge` in +y (down). A flat winding (auto-transformer form-2)."""
    pts = []
    step = (x1 - x0) / n
    r = abs(step) / 2.0
    for k in range(n):
        xc = x0 + step * (k + 0.5)
        for i in range(11):
            a = -math.pi / 2 + math.pi * i / 10.0
            pts.append((xc + r * math.sin(a), yaxis + bulge * math.cos(a)))
    p.polyline(pts, lw)


def sine_path(p, x0, x1, y0, y1, amp, humps=3, lw=STD_LW):
    """A gentle wave from (x0,y0) to (x1,y1) with `amp` vertical amplitude -
    used for a 'flexible' / wavy connection filling its box height."""
    pts = []
    n = humps * 12
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t - amp * math.sin(2 * math.pi * humps * t)
        pts.append((x, y))
    p.polyline(pts, lw)
