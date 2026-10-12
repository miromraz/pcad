#!/usr/bin/env python3
"""Extra clean-room drawing helpers for the passive batch (gen_passive.py).

Owned by the passive team (draw_lib.py is owned by the style lead and not
edited). Pure geometry on top of draw_lib.Ppd; all coords 0.1 mm, y down.
"""
import math


def zigzag_v(p, y0, y1, amp, n=6, lw=4):
    """Vertical ANSI zig-zag (saw-tooth) resistor body from (0,y0) to (0,y1).
    Peaks sit exactly at x=+/-amp so the drawn width is 2*amp."""
    span = y1 - y0
    pts = [(0, y0)]
    for i in range(n):
        yy = y0 + span * (i + 0.5) / n
        pts.append((amp if i % 2 == 0 else -amp, yy))
    pts.append((0, y1))
    p.polyline(pts, lw)


def accordion_h(p, x0, x1, amp, n=6, lw=4):
    """Horizontal accordion/bellows line from (x0,0) to (x1,0) (flexible WG)."""
    span = x1 - x0
    pts = [(x0, 0)]
    for i in range(n):
        xx = x0 + span * (i + 0.5) / n
        pts.append((xx, amp if i % 2 == 0 else -amp))
    pts.append((x1, 0))
    p.polyline(pts, lw)


def dashed_v(p, x, y0, y1, dash=14, lw=4):
    """Broken vertical line from (x,y0) to (x,y1)."""
    y = y0
    while y < y1:
        p.line(x, y, x, min(y + dash * 0.6, y1), lw)
        y += dash


def hatch_wall(p, x_surface, y0, y1, depth, step=12, lw=2):
    """Short diagonal hatch ticks hanging off a vertical reflector surface,
    extending by `depth` in +x (sign of depth sets side)."""
    y = y0
    while y <= y1:
        p.line(x_surface, y, x_surface + depth, y - abs(step) * 0.7, lw)
        y += step
