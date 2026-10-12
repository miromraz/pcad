#!/usr/bin/env python3
"""Glyph helpers for the installation_house batch (EN/IEC 60617-11 house wiring).

Clean-room: drawn from the EN 60617 part-11 installation-plan conventions and the
spec facts only. Families: socket outlets (11-13 / 211-07), luminaires (11-15 /
211-06), installation switches (11-14), appliance blocks (211-10) and automatic
switches (211-07). Reuses draw_lib primitives; extra shapes live here.
"""
import math
import draw_lib as dl
from draw_lib import Ppd

LW = dl.STD_LW


# --- generic arc (sampled polyline, robust across the renderer) -----------
def arc_poly(p, cx, cy, r, a0, a1, lw=LW, n=16):
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * t / n)),
            cy + r * math.sin(math.radians(a0 + (a1 - a0) * t / n)))
           for t in range(n + 1)]
    p.polyline(pts, lw)


# =========================================================================
# Sockets  (semicircle = socket face; stem from the diameter midpoint)
# =========================================================================
def socket(p, px, py, r=15, H=None):
    """Half-disc socket. Dome points AWAY from the pin; the stem runs from the
    diameter midpoint (near the pin) to the pin. Returns (diam_y, dome_tip_y)."""
    up = py < 0                                  # pin above -> diameter on top
    if H is None:
        H = abs(py) + r + 5
    if up:
        cy0 = py + (H - r)                       # diameter y (near pin)
        arc_poly(p, px, cy0, r, 0, 180)          # dome hangs below
        tip = cy0 + r
    else:
        cy0 = py - (H - r)
        arc_poly(p, px, cy0, r, 180, 360)        # dome rises above
        tip = cy0 - r
    p.line(px - r, cy0, px + r, cy0)             # diameter (socket face)
    p.line(px, cy0, px, py)                      # stem to pin
    return cy0, tip


def earth_bar(p, cx, cy, halfw):
    """Protective-earth contact: the diameter line extended past the dome."""
    p.line(cx - halfw, cy, cx + halfw, cy, lw=LW)


def aerial(p, cx, cy, up=True, scale=1.0):
    """Antenna/aerial glyph: a mast with two diverging top strokes (Y)."""
    h = 18 * scale
    s = 12 * scale
    dy = -1 if up else 1
    p.line(cx, cy, cx, cy + dy * h)
    p.line(cx, cy + dy * h, cx - s, cy + dy * (h + s))
    p.line(cx, cy + dy * h, cx + s, cy + dy * (h + s))


# =========================================================================
# Luminaires
# =========================================================================
def lamp(p, cx, cy, r):
    """Lamp / luminaire: circle with an internal cross (×)."""
    p.circle(cx, cy, r)
    d = r * 0.70
    p.line(cx - d, cy - d, cx + d, cy + d)
    p.line(cx - d, cy + d, cx + d, cy - d)


def emergency_lamp(p, cx, cy, r):
    """Emergency luminaire: lamp circle with two opposite quadrants filled."""
    lamp(p, cx, cy, r)
    for a0 in (0, 180):                          # fill two opposite sectors
        pts = [(cx, cy)]
        for t in range(0, 91, 15):
            a = math.radians(a0 + t)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        p.polygon(pts, lw=2, fill=True)


def beam_lamp(p, cx, cy, r, ang_deg, spread_deg, length, filled=True):
    """Projector/flood/spot: a (filled) lamp with a beam of two rays + reflector."""
    if filled:
        p.dot(cx, cy, r)
    else:
        p.circle(cx, cy, r)
    a = math.radians(ang_deg)
    # reflector bar behind the lamp
    px, py = -math.sin(a), math.cos(a)
    bx, by = cx - r * math.cos(a), cy - r * math.sin(a)
    p.line(bx + px * r * 1.3, by + py * r * 1.3,
           bx - px * r * 1.3, by - py * r * 1.3)
    for s in (+1, -1):                           # two beam rays
        aa = math.radians(ang_deg + s * spread_deg / 2.0)
        p.line(cx + r * math.cos(aa), cy + r * math.sin(aa),
               cx + length * math.cos(aa), cy + length * math.sin(aa))


# =========================================================================
# Installation switches (EN 60617-11-14): a small circle = the switch body,
# with an oblique actuator stroke ending in a short perpendicular tick. The four
# spec pins (a cross at +-15) lie ON the circle (r=15), so no cross arms are
# drawn; larger pin rings get short conductor leads. Variant qualifiers (two
# ticks, opposite/crossed strokes, lamp, key, pull-cord, time, arrows) mark the
# kind. The oblique stroke is sized to make the drawn box reach the spec size.
# =========================================================================
SW_R = 15


def sw_body(p, pins, r=SW_R):
    """Switch body circle + conductor leads to any off-rim pin; emits outlets in
    spec order. Pins on the rim (distance r) get no separate lead."""
    p.circle(0, 0, r)
    dl.leads(p, pins, r)


def sw_diag(p, W, H, ticks=1, ticklen=7):
    """Oblique actuator stroke across the body, from the lower-left to the
    upper-right box corner (so the drawn box fills the spec W x H), ending in
    `ticks` short perpendicular contact tick(s) inset from the corner."""
    x0, y0 = -W / 2.0, H / 2.0
    x1, y1 = W / 2.0, -H / 2.0
    p.line(x0, y0, x1, y1)
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    px, py = -uy, ux
    for k in range(ticks):
        cx = x1 - ux * (ticklen + 4) * (k + 0.6)
        cy = y1 - uy * (ticklen + 4) * (k + 0.6)
        p.line(cx - px * ticklen, cy - py * ticklen,
               cx + px * ticklen, cy + py * ticklen)


def sw_lamp(p, W, H):
    """Pilot-lamp qualifier (x-in-circle) in the lower-left, clear of the lever."""
    lamp(p, -0.26 * W, 0.26 * H, min(W, H) * 0.11)


def sw_key(p, W, H):
    """Key-operated qualifier: a small key (ring + bit) left of the body."""
    cx, cy = -0.30 * W, 0.0
    p.circle(cx, cy, 6)
    p.line(cx + 6, cy, cx + 16, cy)
    p.line(cx + 13, cy, cx + 13, cy + 5)


def sw_pull(p, W, H):
    """Pull-cord qualifier: a cord with a knob hanging below the body."""
    p.line(0.0, SW_R, 0.0, 0.30 * H)
    p.circle(0.0, 0.30 * H + 5, 4)


# =========================================================================
# Installation switches (wiring cross + an open make-contact blade)  [legacy]
# =========================================================================
def wiring_cross(p, pins, W, H, gap=10):
    """Conductors from each pin to the central node, leaving a `gap` square in
    the middle for the contact. Conductors reach the box edge (±W/2, ±H/2) so
    the drawn box matches the spec size. Returns the four reach points."""
    l, t, r, b = -W / 2.0, -H / 2.0, W / 2.0, H / 2.0
    # horizontal + vertical conductors with a central break
    p.line(l, 0, -gap, 0)
    p.line(gap, 0, r, 0)
    p.line(0, t, 0, -gap)
    p.line(0, gap, 0, b)
    return l, t, r, b


def switch_blade(p, gap=10, up_left=True):
    """Open blade across the central gap (break between the horizontal arms)."""
    p.dot(-gap, 0, 4)                            # pivot on the left arm
    tx, ty = (gap, -gap - 6) if up_left else (gap, gap + 6)
    p.line(-gap, 0, tx, ty)                      # open blade


def inst_switch(pins, W, H, modifier=None, markings=None):
    """Base installation switch: wiring cross + open blade, modifier glyph on top.
    `modifier` is a callable(p, W, H) drawing the extra element."""
    p = Ppd()
    wiring_cross(p, pins, W, H)
    switch_blade(p)
    if modifier:
        modifier(p, W, H)
    for (x, y) in pins:
        p.outlet(x, y)
    if markings:
        p.marking(markings, cx=W / 2.0 - 12, cy=-H / 2.0 + 12, bodyw=24, bodyh=24)
    return p


# =========================================================================
# Appliance / apparatus blocks
# =========================================================================
def block(pins, W, H, shape="rect", inner=None, markings=None, cx=0.0, cy=0.0):
    """Body (rect or circle) centred on (cx,cy) with axis leads to each pin and
    an optional inner pictogram + centred markings."""
    p = Ppd()
    l, t, r, b = cx - W / 2.0, cy - H / 2.0, cx + W / 2.0, cy + H / 2.0
    if shape == "circle":
        p.circle(cx, cy, min(W, H) / 2.0)
    else:
        p.rect(l, t, r, b)
    if inner:
        inner(p, l, t, r, b)
    for (x, y) in pins:
        if x > r + 1:
            p.line(r, y, x, y)
        elif x < l - 1:
            p.line(l, y, x, y)
        if y > b + 1:
            p.line(x, b, x, y)
        elif y < t - 1:
            p.line(x, t, x, y)
        p.outlet(x, y)
    if markings:
        p.marking(markings, cx=cx, cy=cy, bodyw=W * 0.9, bodyh=H * 0.9,
                  shape="circle" if shape == "circle" else "rect")
    return p
