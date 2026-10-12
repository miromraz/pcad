#!/usr/bin/env python3
"""Clean-room drawing helpers for the misc batch (EN/IEC 60617 sections
11-17 trunking, 02-17/05-06 markers, 07-19..07-25 proximity/static/arresters,
09-09 electroacoustics).

draw_lib.py is owned by the style lead and must not be edited, so batch-specific
glyphs live here. A few section-07 contact/actuator pieces are reused from the
switching team's clean helpers. Pure stdlib; operates on a draw_lib.Ppd. Coords
0.1 mm, y DOWN.
"""
import math
import draw_lib as dl
import helpers_switching_protection as hsw

semicircle = hsw.semicircle          # (p,cx,cy,rad,a0,a1)
mech_link = hsw.mech_link


# --- trunking (section 11-17) --------------------------------------------

def channel(p, x1, x2, y=0, hw=10):
    """Trunking run shown as a duct: two parallel lines hw above/below y."""
    p.line(x1, y - hw, x2, y - hw)
    p.line(x1, y + hw, x2, y + hw)


def vchannel(p, y1, y2, x=0, hw=10):
    p.line(x - hw, y1, x - hw, y2)
    p.line(x + hw, y1, x + hw, y2)


def barrier(p, x, ytop, ybot, hatch=False, fill=False):
    """Internal barrier across the run at column x (ytop..ybot)."""
    p.rect(x - 7, ytop, x + 7, ybot, fill=fill)
    if hatch:
        for yy in range(int(ytop) + 10, int(ybot), 16):
            p.line(x - 7, yy, x + 7, yy - 8, lw=2)


def feeder_arrow(p, x, y, into=1):
    """Feeder supply: a filled triangle feeding the run (into>0 points +x)."""
    s = 16 * into
    p.polygon([(x, y), (x - s, y - 8), (x - s, y + 8)], fill=True)


def tapoff(p, x, ytop, ybot):
    """Perpendicular tap branch through the run at column x."""
    p.line(x, ytop, x, ybot)
    p.dot(x, 0, 4)


def omega(p, cx, r, y=0):
    """Expansion loop (Ω) centred at (cx,y), opening downward."""
    semicircle(p, cx, y - r + 6, r, 0, 360, n=20)


# --- proximity / touch (section 07-19/07-20) -----------------------------

def diamond(p, cx, cy, r):
    p.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def prox_contact(p, cx, y_top, y_bot, make=True, left=-20, glyph=None, fe=False):
    """Vertical proximity/touch contact at column cx with the operating glyph
    to the LEFT. make=True => NO contact, else NC. glyph(p, gx, gy) draws the
    actuator (a diamond-based mark) centred at (gx,0). Returns blade mid-x."""
    g = hsw.GAP
    p.line(cx, y_top, cx, -g)
    p.line(cx, y_bot, cx, g)
    bx = cx - 30                                   # blade reaches left
    if make:
        p.line(cx, g, bx, -g)                      # open make blade
    else:
        p.line(cx, g, bx, -g)                      # blade
        p.line(bx, -g, cx, -g)                     # fixed-contact bar
    gx = left + 16
    mech_link(p, bx, 0, gx + 8)
    if glyph:
        glyph(p, gx, 0)
    return bx


# --- gas-discharge / spark gaps (section 07-22) --------------------------

def spark_electrode(p, x, y, up, half=5, ln=10):
    """A small filled triangle electrode; tip toward the gap (up=True => tip
    points up, base below)."""
    if up:
        p.polygon([(x, y), (x - half, y + ln), (x + half, y + ln)], fill=True)
    else:
        p.polygon([(x, y), (x - half, y - ln), (x + half, y - ln)], fill=True)


# --- electroacoustics (section 09-09) ------------------------------------

def speaker(p, cx, cy, boxw=12, boxh=18, horn=22):
    """Loudspeaker: magnet rectangle + horn trapezoid opening to the right."""
    p.rect(cx - boxw, cy - boxh, cx + boxw, cy + boxh)
    p.polygon([(cx + boxw, cy - boxh), (cx + boxw + horn, cy - boxh - 18),
               (cx + boxw + horn, cy + boxh + 18), (cx + boxw, cy + boxh)])


def lens(p, cx, cy, half_w, half_h, n=10):
    """Receiver/earphone: a pointed oval (two arcs) along the vertical axis."""
    top, bot = (cx, cy - half_h), (cx, cy + half_h)
    left = [(cx - half_w * math.sin(math.pi * t / n),
             cy - half_h * math.cos(math.pi * t / n)) for t in range(n + 1)]
    right = [(cx + half_w * math.sin(math.pi * t / n),
              cy - half_h * math.cos(math.pi * t / n)) for t in range(n + 1)]
    p.polyline(left)
    p.polyline(right)
