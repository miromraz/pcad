#!/usr/bin/env python3
"""Glyph helpers for the installation_knx_floorplan batch.

Clean-room: drawn from EN/IEC 60617 part 11 (installation) + general
architectural / KNX-EIB drafting convention and the spec facts only. The
US floor-plan and KNX-EIB symbols are a building-automation convention (the
spec tags them with placeholder EN 60617 class numbers); shapes here are the
recognizable house-plan / bus-device forms, kept consistent and pin-compatible
with draw_lib. See the hand-off for the low-confidence set.
"""
import math

import draw_lib as dl
from draw_lib import Ppd


# --- small shared marks ---------------------------------------------------

def cross(p, cx, cy, r):
    """A '+' of two diameters inside radius r (lamp / ceiling-outlet mark)."""
    p.line(cx - r, cy, cx + r, cy)
    p.line(cx, cy - r, cx, cy + r)


def slots(p, n, r, cx=0, cy=0):
    """n short vertical ticks across the horizontal diameter = receptacle poles."""
    if n == 1:
        xs = [0.0]
    elif n == 2:
        xs = [-r * 0.34, r * 0.34]
    else:
        xs = [-r * 0.72, -r * 0.24, r * 0.24, r * 0.72]
    for x in xs:
        p.line(cx + x, cy - r * 0.42, cx + x, cy + r * 0.42)


def receptacle(p, n, w, h, square=False):
    """Architectural receptacle outlet: circle with a horizontal line through it
    and n pole-ticks. `w` sets the mounting-line half-width; `square` wraps it in
    an in-floor box. Centred on the origin."""
    r = min(h, 50) / 2.0 - 2
    if square:
        s = min(w, h) / 2.0
        p.rect(-s, -s, s, s)
        r = s - 6
    p.circle(0, 0, r)
    half = max(r, w / 2.0 - 1) if not square else r
    p.line(-half, 0, half, 0)
    slots(p, n, r)


def circle_cross(p, r, square=False, w=None, h=None):
    """Lamp outlet: circle + cross; optionally inside a square (recessed)."""
    pp = p
    if square:
        s = min(w, h) / 2.0
        pp.rect(-s, -s, s, s)
        r = s - 4
    pp.circle(0, 0, r)
    cross(pp, 0, 0, r)


def ceiling_fan(p, r):
    """Ceiling fan: small hub + four blades (thin ellipses) on the diagonals."""
    p.circle(0, 0, r * 0.14)
    bl = r * 0.92
    bw = r * 0.22
    for a in (45, 135, 225, 315):
        rad = math.radians(a)
        ex, ey = math.cos(rad) * bl, math.sin(rad) * bl
        mx, my = ex * 0.55, ey * 0.55
        px, py = -math.sin(rad) * bw, math.cos(rad) * bw
        p.polygon([(r * 0.14 * math.cos(rad), r * 0.14 * math.sin(rad)),
                   (mx + px, my + py), (ex, ey), (mx - px, my - py)])


def bell(p):
    """Floor-plan bell: hanging loop, dome, base, clapper (box ~29x46)."""
    p.circle(0, -18, 4)                     # hanging loop
    p.arc(-13, -14, 13, 12, -13, 0, 13, 0)  # dome (upper semicircle)
    p.line(-13, -1, -13, 12)
    p.line(13, -1, 13, 12)
    p.line(-13, 12, 13, 12)                 # base line
    p.line(0, 12, 0, 18)
    p.circle(0, 21, 4)                      # clapper


def camera(p):
    """Exterior security camera, side profile (box ~65x24): bracket, body, lens."""
    p.line(-25, 0, -12, 0)                  # wall bracket arm
    p.line(-25, -6, -25, 6)
    p.rect(-12, -10, 15, 10)                # body
    p.polygon([(15, -7), (40, -4), (40, 4), (15, 7)])  # lens hood


def radiation(p, outward):
    """Two parallel 45 arrows at the right (IR). outward=transmit, else receive."""
    for k in (0, 1):
        oy = -18 + k * 24
        if outward:                          # tip away from the box (to +x)
            dl.arrow(p, 100, oy + 14, 168 + k * 2, oy - 14)
        else:                                # tip toward the box (to -x)
            dl.arrow(p, 168 + k * 2, oy - 14, 100, oy + 14)


def aux_supply(p, markings_sine=True):
    """Auxiliary AC-feed block upper-right (extends a 180x144 body to 260x187)."""
    p.rect(90, -115, 170, -40)
    if markings_sine:
        dl.sine(p, 130, -77, half=22, amp=8)


# --- KNX-EIB inner differentiators for the un-marked basic blocks ----------

def knx_inner(p, kind, w, h):
    """Small inner glyph for a KNX box that the spec gives no marking letters.
    Best-guess differentiators (low confidence) -- see hand-off."""
    if kind == "actuator":                   # drives a load: filled down-triangle
        p.polygon([(-16, -14), (16, -14), (0, 14)], fill=True)
    elif kind == "analog":                   # analog output: rising ramp
        p.polyline([(-26, 16), (18, 16), (18, -16)])
        p.line(-26, 16, 18, -16)
    elif kind in ("dimmer", "dimming"):      # variability arrow across the body
        dl.arrow(p, -24, 20, 24, -20)
    elif kind in ("shutter_act", "shutter_sw"):   # up + down arrows (blind)
        dl.arrow(p, -10, 18, -10, -18)
        dl.arrow(p, 10, -18, 10, 18)
    elif kind == "interface":                # two opposed arrows (data both ways)
        dl.arrow(p, -24, -8, 24, -8)
        dl.arrow(p, 24, 10, -24, 10)
    elif kind == "connector":                # plug: two interlocking brackets
        p.polyline([(-6, -22), (-22, -22), (-22, 22), (-6, 22)])
        p.polyline([(6, -22), (22, -22), (22, 22), (6, 22)])
        p.line(-6, 0, 6, 0)
    elif kind == "choke":                    # inductor: three humps (vertical)
        for i in range(3):
            cy = -18 + i * 18
            p.arc(-9, cy - 9, 9, cy + 9, 0, -9, 0, 9)
    elif kind == "bus_access":               # bus tap: a filled dot
        p.dot(0, 0, 6)
    elif kind == "pushbutton":               # a button: small circle + stem
        p.circle(0, -2, 10)
        p.line(0, 8, 0, 20)
    elif kind in ("binary_ac", "binary_dc"): # input bit: ~ (AC) or = (DC)
        if kind == "binary_ac":
            dl.sine(p, 0, 0, half=20, amp=7)
        else:
            p.line(-16, -5, 16, -5)
            p.line(-16, 5, 16, 5)
    elif kind == "psu":                      # power supply: = (DC) + divider
        p.line(-30, -6, 30, -6)
        p.line(-20, 6, 20, 6)
    elif kind == "psu_choke":                # PSU + choke: = plus an inductor hump
        p.line(-40, -8, 0, -8)
        p.line(-30, 6, -4, 6)
        for i in range(3):
            p.arc(10 + i * 18, -9, 28 + i * 18, 9, 9, 0, -9, 0)
