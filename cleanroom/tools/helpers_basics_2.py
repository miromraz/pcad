#!/usr/bin/env python3
"""Extra clean-room drawing helpers for the basics_2 batch.

draw_lib.py is owned by the style lead and not edited; batch-specific glyphs
live here. Everyday schematic basics: IEC logic gates, meters, passive parts,
discrete semiconductors, tubes, optocouplers, audio devices. Reuses winding
bumps (machines team) and the semicircle/arc helper (switching team) so the
look matches the existing families. Pure stdlib; coords 0.1 mm, y DOWN.
"""
import math
import draw_lib as dl
from draw_lib import Ppd, arrow, arrowhead, sine, add_outlets
from helpers_machines_power import winding_bumps_v
from helpers_switching_protection import semicircle


# --- windings along an arbitrary direction (star / triangle 3-phase coils) ---

def winding_along(p, x0, y0, x1, y1, n, bulge, lw=dl.STD_LW):
    """n semicircular bumps along the segment (x0,y0)->(x1,y1), bulging to one
    side by `bulge`. Generalises winding_bumps_v to any direction."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L            # along the axis
    px, py = -uy, ux                   # perpendicular (bulge side)
    step = L / n
    r = step / 2.0
    pts = []
    for k in range(n):
        c = step * (k + 0.5)
        for i in range(13):
            a = -math.pi / 2 + math.pi * i / 12.0
            along = c + r * math.sin(a)
            out = bulge * math.cos(a)
            pts.append((x0 + ux * along + px * out,
                        y0 + uy * along + py * out))
    p.polyline(pts, lw)


# --- diode primitives (horizontal or vertical) ---------------------------

def tri_bar_v(p, cx, cy, h=14, w=14):
    """Anode triangle pointing DOWN to a cathode bar (vertical diode, current
    downwards). Triangle apex at (cx,cy+h), bar at y=cy+h."""
    p.polygon([(cx - w, cy - h), (cx + w, cy - h), (cx, cy + h)])
    p.line(cx - w, cy + h, cx + w, cy + h)


def tri_bar_h(p, cx, cy, h=16, w=14, flip=False):
    """Anode triangle -> cathode bar along +x (flip=True points -x)."""
    s = -1 if flip else 1
    p.polygon([(cx - s * w, cy - h), (cx - s * w, cy + h), (cx + s * w, cy)])
    p.line(cx + s * w, cy - h, cx + s * w, cy + h)


# --- resistor rectangle (vertical, IEC 4:1) ------------------------------

def res_rect_v(p, cx, cy, halfw, halfh):
    p.rect(cx - halfw, cy - halfh, cx + halfw, cy + halfh)


# --- capacitor plates ----------------------------------------------------

def cap_plates(p, cx, cy, halfw, gap):
    """Two straight plates perpendicular to a vertical lead axis."""
    p.line(cx - halfw, cy - gap, cx + halfw, cy - gap)
    p.line(cx - halfw, cy + gap, cx + halfw, cy + gap)


def cap_polarized(p, cx, cy, halfw, gap):
    """Electrolytic: top plate straight (+), bottom plate curved (-)."""
    p.line(cx - halfw, cy - gap, cx + halfw, cy - gap)        # + plate
    semicircle(p, cx, cy + gap - halfw * 0.5, halfw, 20, 160, n=14)  # curved -


# --- tube electrode stack ------------------------------------------------

def tube(pins, r, grids, anodes=1):
    """Generic thermionic valve: circular envelope with a heater V at the
    bottom, a cathode line, `grids` dashed grid lines, and `anodes` anode
    plates at the top. Leads run to the spec pins. Good-enough EN form."""
    p = Ppd()
    p.circle(0, 0, r)
    # heater: inverted V near the bottom to the two lowest pins
    lows = sorted(pins, key=lambda q: -q[1])[:2]
    if len(lows) == 2:
        (ax, ay), (bx, by) = lows
        hy = r * 0.55
        p.line(ax * 0.3, hy, 0, hy - 10)
        p.line(bx * 0.3, hy, 0, hy - 10)
        for (x, y) in lows:
            p.line(x * 0.3, hy, x, y)
    # cathode line just above the heater
    p.line(-14, r * 0.35, 14, r * 0.35)
    # grids: dashed horizontal lines stacked in the middle; side pins feed them
    side = sorted([pt for pt in pins if abs(pt[0]) >= r * 0.5 and abs(pt[1]) < r],
                  key=lambda q: q[1])
    gy0 = -r * 0.1
    for g in range(grids):
        yy = gy0 - g * 12
        x = -22
        while x < 22:
            p.line(x, yy, x + 8, yy, lw=2)
            x += 14
        if g < len(side):
            sx, sy = side[g]
            p.line(22 if sx > 0 else -22, yy, sx, sy)
    # anode plate(s) at the top + lead to the top pin
    top = min(pins, key=lambda q: q[1])
    ay = -r * 0.55
    if anodes == 1:
        p.line(-16, ay, 16, ay)
        p.line(0, ay, top[0], top[1])
    else:
        p.line(-26, ay, -6, ay)
        p.line(16, ay, 36, ay)
    add_outlets(p, pins)
    return p
