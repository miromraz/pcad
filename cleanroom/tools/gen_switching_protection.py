#!/usr/bin/env python3
"""Generate the switching_protection batch (120 EN/IEC 60617 symbols) as .ppd.

Clean-room: drawn from the EN/IEC 60617 standard + the spec facts only.
Families: fuses (07-21), appliance protection classes (02-15), switching
contacts (07-02..07-09, 07-13), relays (07-15, 07-18) and the ANSI/IEC
protective devices, circuit breakers and switch/contactor set (IEC 9.x).

Shared primitives: draw_lib.py; batch glyphs: helpers_switching_protection.py.
Run: python3 gen_switching_protection.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd
import helpers_switching_protection as h

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_switching_protection.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def code(rec):
    s = rec["standard"]
    if s.startswith("EN 60617"):
        return s.split(":", 1)[1].strip()        # '07-02-02'
    return s                                      # 'IEC:9.2'


# =========================================================================
# Fuses
# =========================================================================

def draw_fuse_general(rec):
    """Fuse: narrow rectangle with the conductor passing through it."""
    p = Ppd()
    (x1, y1), (x2, y2) = pins_of(rec)[0], pins_of(rec)[1]
    ytop, ybot = min(y1, y2), max(y1, y2)
    w = rec["size"]["w"]
    hw = min(w, 16) / 2.0
    bt, bb = ytop + 4, ybot - 4
    p.rect(-hw, bt, hw, bb)
    p.line(0, ytop, 0, ybot)                       # element through the body
    thick = "thick line" in rec["name"] or "remains live" in rec["name"] \
        or "supply side" in rec["name"]
    if thick:
        p.line(-hw, bb, hw, bb, lw=10)             # heavy line = live/supply side
    for (x, y) in pins_of(rec):
        p.outlet(x, y)
    return p


def draw_fuse_form2(rec):
    """ANSI fuse form 2: a wider rectangle (square box) with the element."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    ys = [y for _, y in pins]
    ytop, ybot = min(ys), max(ys)
    p.rect(-w / 2.0, ytop + 4, w / 2.0, ybot - 4)
    p.line(0, ytop, 0, ybot)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_fuse_striker(rec):
    """Striker fuse: fuse body + a striker pin to the side (07-21-03)."""
    p = Ppd()
    w = rec["size"]["w"]
    p.rect(-8, -20, 8, 20)
    p.line(0, -24, 0, 24)
    p.line(8, 0, w - 8, 0)                          # striker rod
    p.line(w - 8, -8, w - 8, 8)                     # striker head
    for (x, y) in pins_of(rec):
        p.outlet(x, y)
    return p


def draw_fuse_alarm(rec):
    """Fuse with alarm contact(s): fuse body + a make contact to pin(s) at x=60."""
    p = Ppd()
    p.rect(-8, -20, 8, 20)
    p.line(0, -24, 0, 24)
    pins = pins_of(rec)
    extra = [(x, y) for (x, y) in pins if x != 0]
    # alarm contact: a small make contact from body to each extra terminal
    for (x, y) in extra:
        sy = -1 if y < 0 else 1
        p.line(8, sy * 8, 34, sy * 8)              # tap off the body
        h.blade_make  # noqa (kept import parity)
        p.line(34, sy * 8, 50, sy * 30)            # blade
        p.line(60, y, 50, y - sy * 10)             # lead to terminal
        p.line(50, y - sy * 10, 50, sy * 30)       # fixed side
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_fuse_switch(rec):
    """Fuse-switch / fuse switch-disconnector: a knife blade carrying a fuse."""
    p = Ppd()
    disc = "disconnector" in rec["name"]
    # vertical knife contact, pins at (0,+-40)
    p.line(0, 40, 0, 18)                            # bottom lead + pivot
    p.line(0, -40, 0, -18)                          # top lead
    # blade carrying a fuse rectangle, tilted
    p.line(0, 18, 14, -18)                          # blade
    p.rect(-6, -12, 6, 12)                          # fuse box on the line
    if disc:
        h.disconnector_bar(p, 0, -18, s=9)
    for (x, y) in pins_of(rec):
        p.outlet(x, y)
    return p


# =========================================================================
# Appliance protection classes (02-15)
# =========================================================================

def draw_class(rec):
    name = rec["name"].lower()
    p = Ppd()
    if "class ii" in name and "iii" not in name:          # double insulation
        p.rect(-28, -28, 28, 28)
        p.rect(-18, -18, 18, 18)
    elif "class iii" in name:                             # SELV rhombus + III
        p.polygon([(0, -38), (38, 0), (0, 38), (-38, 0)])
        for dx in (-9, 0, 9):
            p.line(dx, -11, dx, 11)
    else:                                                 # class I = protective earth
        p.line(0, -20, 0, 8)
        p.line(-30, 8, 30, 8)
        p.line(-19, 21, 19, 21)
        p.line(-9, 34, 9, 34)
    for (x, y) in pins_of(rec):
        p.outlet(x, y)
    return p


# =========================================================================
# Vertical contacts (make / break + modifiers), pins top & bottom
# =========================================================================

MAKE_CODES = {"07-02-02", "07-06-01", "07-06-02", "07-04-01", "07-04-02",
              "07-05-01", "07-05-02", "07-05-05", "07-03-01", "07-03-02",
              "07-03-03", "07-09-01"}
BREAK_CODES = {"07-02-03", "07-06-03", "07-04-03", "07-04-04", "07-05-03",
               "07-05-04", "07-09-02"}


def draw_vcontact(rec):
    """A single-pole vertical contact with the EN 60617 modifier for its code."""
    c = code(rec)
    name = rec["name"].lower()
    pins = pins_of(rec)
    cx = pins[0][0]
    W = rec["size"]["w"]
    is_break = c in BREAK_CODES or "brake" in name or c in (
        "07-13-04", "07-13-06", "07-13-05")
    # blade reaches right so that (body span) == W. Modifiers at the blade TIP
    # extend the box by `rext`; tip-internal modifiers do not.
    RIGHT_EXT = {"07-13-02": 9, "07-13-04": 9, "07-13-03": 9,
                 "07-13-08": 11, "07-13-09": 11, "07-13-06": 11, "07-13-05": 7}
    rext = RIGHT_EXT.get(c, 0)
    reach = max(14, W - rext)          # min_x==cx cancels: span = reach + rext
    p = Ppd()
    h.v_leads(p, cx, pins[0][1], pins[1][1])
    if is_break:
        tip = h.blade_break(p, cx, reach)
    else:
        tip = h.blade_make(p, cx, reach)
    mx, my = (cx + reach / 2.0, 0)                  # blade midpoint

    # --- modifiers -------------------------------------------------------
    if c in ("07-13-02", "07-13-04"):              # contactor main contact
        h.contactor_cup(p, *tip, down=not is_break)
    elif c == "07-13-05":                          # circuit breaker (EN)
        h.breaker_cross(p, *tip)
    elif c in ("07-13-06",):                        # disconnector / fuse-disc
        h.disconnector_bar(p, *tip)
        if "fuse" in name:
            p.rect(mx - 6, -11, mx + 6, 11)         # fuse box on the blade
    elif c == "07-13-08":                           # switch-disconnector
        h.disconnector_bar(p, *tip)
        h.semicircle(p, mx, my, 9, 0, 180)
    elif c == "07-13-09":                           # switch-disc + auto trip
        h.disconnector_bar(p, *tip)
        p.rect(cx + reach - 10, -10, cx + reach + 6, 10)
    elif c == "07-13-03":                           # contactor + auto trip
        h.contactor_cup(p, *tip, down=True)
        p.rect(cx + reach - 10, -10, cx + reach + 6, 10)
    elif c == "07-06-01":                           # make, automatic return
        h.auto_return(p, mx, my - 10)
    elif c == "07-06-02":                           # make, no automatic return
        p.line(mx - 8, my - 12, mx + 8, my - 12)   # bar = no auto return
    elif c == "07-06-03":                           # break, automatic return
        h.auto_return(p, mx, my - 10)
    elif c == "07-04-01":                           # make, early to close
        h.early_late(p, mx, my, early=True)
    elif c == "07-04-02":                           # make, late to close
        h.early_late(p, mx, my, early=False)
    elif c == "07-04-04":                           # break, early to open
        h.early_late(p, mx, my, early=True)
    elif c == "07-04-03":                           # break, late to open
        h.early_late(p, mx, my, early=False)
    elif c in ("07-05-01", "07-05-03"):            # delayed on activate
        h.delay_cup(p, mx, my, opening_up=False)
    elif c in ("07-05-02", "07-05-04"):            # delayed on de-activate
        h.delay_cup(p, mx, my, opening_up=True)
    elif c == "07-05-05":                           # delayed both
        h.delay_cup(p, mx, my - 10, opening_up=False)
        h.delay_cup(p, mx, my + 10, opening_up=True)
    elif c == "07-03-01":                           # passing, on actuate
        h.passing_tri(p, mx, my, up=True)
    elif c == "07-03-02":                           # passing, on release
        h.passing_tri(p, mx, my, up=False)
    elif c == "07-03-03":                           # passing, both
        h.passing_tri(p, mx, my - 8, up=True)
        h.passing_tri(p, mx, my + 8, up=False)
    elif c in ("07-09-01", "07-09-02"):            # temperature sensitive
        pass                                       # theta marking added below

    if rec["markings"]:
        p.marking(rec["markings"], cx=mx, cy=0, bodyw=28, bodyh=40)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# --- actuated switches (push-button, pull, turn, emergency, manual, limit) ---

ACTUATOR = {        # code -> (glyph, half-width)
    "07-07-03": (h.act_pull, 8),
    "07-07-04": (h.act_turn, 12),
    "07-07-05": (h.act_pushbutton, 14),
    "07-07-06": (h.act_mushroom, 20),
    "07-08-04": (h.act_roller, 7),
}


def draw_actuated(rec):
    """Push/pull/turn/emergency/position switch: a contact + operating glyph.
    The operating element sits to the LEFT; its centre `ax` is chosen so the
    drawn box spans exactly W (blade tip at cx+reach, glyph edge at ax-hw)."""
    c = code(rec)
    name = rec["name"].lower()
    pins = pins_of(rec)
    cx = pins[0][0]
    W = rec["size"]["w"]
    is_break = ("07-08" in c) or (c == "07-07-06"
                                  and rec["category"].endswith("break-contacts")) \
        or "brake" in name
    p = Ppd()
    h.v_leads(p, cx, pins[0][1], pins[1][1])
    reach = 22
    if is_break:
        h.blade_break(p, cx, reach)
    else:
        h.blade_make(p, cx, reach)
    act, hw = ACTUATOR.get(c, (h.act_manual, 14))
    ax = cx + reach + hw - W                        # span == W
    h.mech_link(p, cx, 0, ax)
    act(p, ax, -8)
    if "positive" in name:
        p.circle(ax, -8 - 18, 4)                   # positive-operation mark
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_manual_switch(rec):
    """Manually operated switch, 1..4 poles (07-07-01). Ganged make contacts."""
    name = rec["name"].lower()
    pins = pins_of(rec)
    cols = sorted(set(x for x, _ in pins))
    p = Ppd()
    reach = 22
    tips = []
    for cx in cols:
        h.v_leads(p, cx, -60, 60)
        tips.append(h.blade_make(p, cx, reach))
    # push-button variant (single pole, pin column offset)
    if "push button" in name and len(cols) == 1:
        ax = 0
        h.mech_link(p, cols[0], 0, ax + 14)
        h.act_pushbutton(p, ax, -8)
    elif "pull switch" in name:
        ax = 0
        h.mech_link(p, cols[0], 0, ax + 14)
        h.act_pull(p, ax, -8)
    else:
        # general manual: a handle at the left + dashed coupling across blades
        W = rec["size"]["w"]
        if len(cols) == 1:                 # single pole: fill width via handle
            ax = cols[0] + reach + 14 - W
        else:                              # multi-pole: columns already span W
            ax = cols[0] - 34
        h.act_manual(p, ax, -8)
        h.mech_link(p, ax, -8, tips[-1][0])
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# =========================================================================
# Change-over / multi-throw contacts
# =========================================================================

def draw_changeover(rec):
    """SPDT change-over: common at bottom, two throws at top."""
    c = code(rec)
    name = rec["name"].lower()
    pins = pins_of(rec)
    W = rec["size"]["w"]
    # identify common (bottom, y>0) and throws (top)
    common = [(x, y) for (x, y) in pins if y > 0][0]
    throws = [(x, y) for (x, y) in pins if y < 0]
    p = Ppd()
    cx = common[0]
    p.line(common[0], common[1], cx, h.GAP)        # common lead + pivot
    for (x, y) in throws:
        p.line(x, y, x, -h.GAP)                     # throw leads
    center_off = "centre" in name or "center" in name
    if center_off:                                  # EN change-over, centre-off:
        p.dot(cx, h.GAP, 4)                         # pivot
        p.line(cx, h.GAP, cx, -h.GAP + 8)           # blade: neutral middle position
        for (x, y) in throws:                       # two fixed contacts angled in,
            sx = cx + (7 if x > cx else -7)         # leaving a gap to the neutral blade
            p.line(x, -h.GAP, sx, -h.GAP + 8)
    else:                                           # blade to the left throw
        tgt = min(throws, key=lambda t: t[0])
        p.line(cx, h.GAP, tgt[0], -h.GAP)
    if "make before break" in name:                 # wider bridging contact
        p.line(cx - 6, -h.GAP, cx + 6, -h.GAP)
    if "auto" in name and "return" in name:
        h.auto_return(p, cx, 0)
    # fill width (plain change-over is wide): right-hand operating handle
    xs = [x for x, _ in pins]
    span = max(xs) - min(xs)
    if W - span > 12:
        hx = W - 14 + min(xs)
        h.act_manual(p, hx, 0)
        h.mech_link(p, cx, 0, hx)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_multi_make_break(rec):
    """Contact with 2 makes / 2 brakes (bridging), 3 terminals."""
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    common = [(x, y) for (x, y) in pins if y > 0][0]
    tops = [(x, y) for (x, y) in pins if y < 0]
    xmin = min(x for x, _ in tops)
    xmax = max(x for x, _ in tops)
    p.line(common[0], common[1], common[0], h.GAP)     # common lead
    for (x, y) in tops:
        p.line(x, y, x, -h.GAP)
    # moving bridge bar near the top spanning both fixed contacts (+ overhang)
    bary = -h.GAP + 6
    p.line(xmin - 12, bary, xmax + 12, bary)
    p.line(common[0], h.GAP, (xmin + xmax) / 2.0, bary)  # link to common
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_intermediate(rec):
    """Intermediate (crossover) switch: two change-over contacts crossed."""
    pins = pins_of(rec)
    W = rec["size"]["w"]
    p = Ppd()
    for (x, y) in pins:
        sy = h.GAP if y > 0 else -h.GAP
        p.line(x, y, x, sy)
    # two crossed blades in the central zone
    xs = sorted(set(x for x, _ in pins))
    left, right = xs[0], xs[-1]
    p.line(left, -h.GAP, right, h.GAP)
    p.line(left, h.GAP, right, -h.GAP)
    # fill width with a right-hand operating handle
    if W - (right - left) > 20:
        hx = W - 14 + left
        h.act_manual(p, hx, 0)
        h.mech_link(p, right, 0, hx)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# =========================================================================
# Relay coils (07-15) and gas / auto-close relays (07-18)
# =========================================================================

def draw_coil(rec):
    """Operating device / relay coil: rectangle (full terminal height) + mark."""
    c = code(rec)
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, hh = rec["size"]["w"], rec["size"]["h"]
    ys = [y for _, y in pins]
    ytop, ybot = min(ys), max(ys)
    l, r, t, b = -w / 2.0, w / 2.0, ytop, ybot
    p = Ppd()
    p.rect(l, t, r, b)
    if c == "07-15-04" and len(pins) == 4:            # two separated windings
        p.line(0, t, 0, b)
    elif c == "07-15-08":                             # slow-operating: left bar
        p.rect(l, t, l + 7, b, fill=True)
    elif c == "07-15-07":                             # slow-releasing: right bar
        p.rect(r - 7, t, r, b, fill=True)
    elif c == "07-15-09":                             # slow op + slow rel
        p.rect(l, t, l + 7, b, fill=True)
        p.rect(r - 7, t, r, b, fill=True)
    elif c == "07-15-10":                             # high-speed: two diagonals
        p.line(l + 6, b - 4, l + 18, t + 4)
        p.line(r - 18, b - 4, r - 6, t + 4)
    elif c == "07-15-12":                             # AC relay: ~
        dl.sine(p, 0, 0, half=min(w * 0.3, 20), amp=7)
    elif c == "07-15-11":                             # unaffected by AC: =
        p.line(-14, -5, 14, -5)
        p.line(-14, 5, 14, 5)
    elif c == "07-15-13":                             # mechanically resonant
        dl.sine(p, 0, 0, half=min(w * 0.3, 24), amp=7)
        p.line(-6, -10, -6, 10)
        p.line(6, -10, 6, 10)
    elif c == "07-15-14":                             # mechanically latched
        p.line(-6, -8, 6, -8)
        p.line(6, -8, 6, 8)                           # latch hook
    elif c == "07-15-15":                             # polarized
        p.line(-10, 0, 10, 0)
        p.polygon([(10, 0), (3, -5), (3, 5)], fill=True)
    elif c == "07-15-19":                             # remanent
        p.rect(-w / 4.0, -5, w / 4.0, 5, fill=True)
    elif c == "07-15-21":                             # thermal relay device
        p.polyline([(-10, 8), (0, 8), (0, -8), (10, -8)])
    for (x, y) in pins:
        p.line(x, y, x, b if y > 0 else t) if False else None
        p.outlet(x, y)
    return p


def draw_gas_relay(rec):
    """Buchholz / gas relay (07-18-01): body with gas-collection dome, 4 pins."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    # a rounded dome on a rectangle (gas chamber)
    p.rect(-40, -20, 40, 40)
    h.semicircle(p, 0, -20, 40, 180, 360)
    for (x, y) in pins_of(rec):
        # lead from the body toward each terminal
        if x < 0:
            p.line(-40, 0, x, y)
        elif x > 0:
            p.line(40, 0, x, y)
        elif y > 0:
            p.line(0, 40, x, y)
        else:
            p.line(0, -60, x, y)
        p.outlet(x, y)
    return p


def draw_autoclose(rec):
    """Device for auto-closing / auto-close relay (07-18-02): square + marks."""
    p = Ppd()
    p.rect(-30, -30, 30, 30)
    p.line(-30, 30, 30, -30)                          # diagonal
    h.semicircle(p, 0, 0, 12, 180, 360)              # auto-return cup
    for (x, y) in pins_of(rec):
        d = math.hypot(x, y)
        if d > 30:
            ux, uy = x / d, y / d
            p.line(ux * 30, uy * 30, x, y)
        p.outlet(x, y)
    return p


# =========================================================================
# ANSI / IEC protective devices (vertical, pins top & bottom)
# =========================================================================

def draw_protective(rec):
    name = rec["name"].lower()
    W = rec["size"]["w"]
    p = Ppd()
    pins = pins_of(rec)
    ytop, ybot = -60, 60
    half = max(W / 2.0, 3)
    if "lightning arrester" in name or "multigap" in name:
        # very narrow: a line with small gap mark(s)
        p.line(0, ytop, 0, -8)
        p.line(0, 8, 0, ybot)
        if "multigap" in name:
            for yy in (-6, 0, 6):
                p.line(-half, yy, half, yy)
        else:
            p.polygon([(0, 2), (-half, -8), (half, -8)], fill=True)   # small arrow
    elif "protective gap" in name or "sphere gap" in name or "horn gap" in name:
        p.line(0, ytop, 0, -14)
        p.line(0, 14, 0, ybot)
        if "sphere" in name:
            p.circle(0, -half + 8, half)
            p.circle(0, half - 8, half)
        elif "horn" in name:
            h.semicircle(p, 0, -14, half, 200, 340)
            h.semicircle(p, 0, 14, half, 20, 160)
        else:
            p.polygon([(-half, -26), (half, -26), (0, -12)], fill=True)
            p.polygon([(-half, 26), (half, 26), (0, 12)], fill=True)
    elif "carbon block" in name or "current limiter" in name \
            or "electrolytic" in name or "valve" in name or "film" in name:
        p.line(0, ytop, 0, -12)
        p.line(0, 12, 0, ybot)
        if "valve" in name or "film" in name or "current limiter" in name:
            p.rect(-half, -12, half, 12)
        else:
            h.plates(p, 0, half, gap=12)
        if "electrolytic" in name:
            p.line(0, -12, 0, 12)
    elif "network protector" in name:
        # a breaker in a box
        p.rect(-W / 2.0, -40, W / 2.0, 40)
        p.line(0, ytop, 0, -40)
        p.line(0, 40, 0, ybot)
        h.breaker_cross(p, 0, 0)
    else:
        p.line(0, ytop, 0, ybot)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# =========================================================================
# ANSI circuit breakers (IEC 9.4.x), vertical, optional 3-pole
# =========================================================================

def _ansi_breaker_pole(p, cx, ytop, ybot, hw, overload=None):
    """One ANSI breaker pole, body within [cx-hw, cx+0.6*hw]."""
    p.line(cx, ytop, cx, ytop + 30)
    p.line(cx, ybot, cx, ybot - 30)
    # breaker contact = a small concave arc on the moving contact
    p.line(cx, ybot - 30, cx + 0.6 * hw, ytop + 45)
    h.semicircle(p, cx, ytop + 40, min(0.5 * hw, 10), 180, 360)
    if overload == "thermal":
        p.polyline([(cx - hw, ybot - 34), (cx - hw, ybot - 12),
                    (cx - 0.2 * hw, ybot - 12)])     # bimetal hook
    elif overload == "magnetic":
        for k in range(3):                           # inductor humps
            h.semicircle(p, cx - hw + (k + 0.5) * (hw / 3.0), ybot - 20,
                         hw / 6.0, 180, 360)
    else:
        p.line(cx - hw, ytop + 40, cx, ytop + 40)        # fixed-contact bar


def draw_ansi_breaker(rec):
    name = rec["name"].lower()
    W = rec["size"]["w"]
    pins = pins_of(rec)
    ys = [y for _, y in pins]
    ytop, ybot = min(ys), max(ys)
    cols = sorted(set(x for x, _ in pins))
    overload = "thermal" if "thermal" in name else (
        "magnetic" if "magnetic" in name else None)
    span = cols[-1] - cols[0]
    hw = max((W - span) / 1.6, 10)                    # pole half-width to fill W
    p = Ppd()
    for cx in cols:
        _ansi_breaker_pole(p, cx, ytop, ybot, hw, overload)
    if len(cols) > 1:                                # ganged mechanical link
        h.mech_link(p, cols[0], 0, cols[-1])
    if "drawout" in name:                            # drawout chevrons
        for cx in cols:
            p.polyline([(cx - 8, ytop + 10), (cx, ytop + 2), (cx + 8, ytop + 10)])
            p.polyline([(cx - 8, ybot - 10), (cx, ybot - 2), (cx + 8, ybot - 10)])
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# =========================================================================
# ANSI switches & contactors (IEC 9.2), horizontal, pins left & right
# =========================================================================

def _is_nc(rec):
    name = rec["name"].lower()
    return "nc" in name or "/opening" in rec["category"] or "held open" in name


def draw_ansi_hcontact(rec):
    """ANSI switch/contact. Dispatches odd pin layouts, else a horizontal
    contact whose vertical features fill the spec height."""
    name = rec["name"].lower()
    cat = rec["category"]
    pins = pins_of(rec)
    W, H = rec["size"]["w"], rec["size"]["h"]
    if len(pins) >= 6 or "manually operated contactor" in name:
        return draw_ansi_multi(rec)
    if len(pins) == 3 or "transfer" in name:
        return draw_ansi_transfer(rec)
    if len(pins) == 8 or "two circuit" in name:
        return draw_ansi_multi(rec)
    if len(pins) == 4:
        return draw_ansi_pushbutton4(rec)
    A, B = sorted(pins)
    if not (abs(A[1] - B[1]) <= 4 and abs(A[0] - B[0]) >= 40):
        return draw_ansi_oddcontact(rec)              # vertical / diagonal
    # --- horizontal 2-terminal contact, height == H -----------------------
    hh = H / 2.0
    p = Ppd()
    lx, rx = A[0], B[0]
    p.line(lx, 0, -16, 0)
    p.line(rx, 0, 16, 0)
    if _is_nc(rec):
        p.line(-16, 0, 16, 0)                         # closed (conducting)
        p.line(2, -hh, 2, hh)                         # fixed plate (sets H)
    else:
        p.line(16, hh, -12, -hh)                      # open blade (sets H)
    # actuator glyph near the top
    if "pushbutton" in name:
        p.line(0, -hh + 10, 0, -hh)
        p.line(-10, -hh, 10, -hh)
    elif "foot" in name:
        p.polyline([(-10, -hh + 6, ), (10, -hh), (10, -hh + 6)]) if False else \
            p.polyline([(-10, -hh + 6), (10, -hh), (10, -hh + 6)])
        p.line(0, -hh + 10, 0, -hh + 6)
    elif "limit" in cat or "held" in name:
        p.circle(0, -hh + 7, 6)                       # roller
    elif "safety interlock" in name:
        p.rect(-8, -hh, 8, -hh + 12)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_ansi_oddcontact(rec):
    """ANSI contact with vertical or diagonal terminals (NC form 1/2 ...).
    A blade runs between the two terminals; perpendicular fixed bars extend
    the drawn box to the full W x H."""
    pins = pins_of(rec)
    W, H = rec["size"]["w"], rec["size"]["h"]
    A, B = sorted(pins, key=lambda q: q[1])            # top, bottom
    p = Ppd()
    cx, cy = (A[0] + B[0]) / 2.0, (A[1] + B[1]) / 2.0
    pbw = abs(A[0] - B[0])
    pbh = abs(A[1] - B[1])
    if _is_nc(rec):
        p.line(A[0], A[1], B[0], B[1])                 # closed blade
    else:
        p.line(A[0], A[1], B[0] + 10, B[1])            # open (offset) blade
    if W - pbw > 6:                                    # horizontal fixed plate
        p.line(cx - W / 2.0, cy, cx + W / 2.0, cy)
    if H - pbh > 6:                                    # vertical operating rod
        p.line(cx, cy - H / 2.0, cx, cy + H / 2.0)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_ansi_pushbutton4(rec):
    """ANSI push-button with a 2-terminal contact (4 pins = contact + tap)."""
    pins = pins_of(rec)
    W, H = rec["size"]["w"], rec["size"]["h"]
    is_nc = _is_nc(rec)
    outer = sorted(pins, key=lambda q: -abs(q[0]))[:2]
    inner = [q for q in pins if q not in outer]
    row_y = (outer[0][1] + outer[1][1]) / 2.0
    hh = H / 2.0
    lx = min(x for x, _ in outer)
    rx = max(x for x, _ in outer)
    p = Ppd()
    p.line(lx, row_y, -16, row_y)
    p.line(rx, row_y, 16, row_y)
    if is_nc:
        p.line(-16, row_y, 16, row_y)                 # closed
        p.line(2, row_y - hh, 2, row_y + hh)          # fixed plate (sets H)
    else:
        p.line(16, row_y + hh, -12, row_y - hh)       # open blade (sets H)
    for (x, y) in inner:                              # taps to the inner pins
        p.line(x, y, x, row_y)
    # push-button cap on the far side of the contact row
    cap_y = row_y - hh if row_y >= 0 else row_y + hh
    p.line(0, row_y, 0, cap_y)
    p.line(-10, cap_y, 10, cap_y)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_ansi_transfer(rec):
    """ANSI transfer (SPDT), 3 terminals; height/width fill the box."""
    pins = pins_of(rec)
    H = rec["size"]["h"]
    common = min(pins, key=lambda q: q[0])
    throws = [q for q in pins if q != common]
    p = Ppd()
    hh = H / 2.0
    p.line(common[0], common[1], -16, 0)
    for (x, y) in throws:
        ty = hh if y > 0 else -hh
        p.line(x, y, 16, ty)                          # throw leads to ±hh
    tgt = min(throws, key=lambda t: t[1])
    p.line(-16, 0, 16, hh if tgt[1] > 0 else -hh)     # blade to one throw
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_ansi_multi(rec):
    """ANSI multi-pole / two-circuit pushbutton / manual contactor 3P."""
    name = rec["name"].lower()
    pins = pins_of(rec)
    W, H = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    cols = sorted(set(x for x, _ in pins))
    if "manually operated contactor" in name or len(pins) == 6:   # 3 vert poles
        ys = [y for _, y in pins]
        ytop, ybot = min(ys), max(ys)
        bt, bb = -H / 2.0, H / 2.0                   # blades span full height
        for cx in cols:
            p.line(cx, ytop, cx, bb)
            p.line(cx, ybot, cx, bb)
            p.line(cx, bb, cx + 16, bt)              # open blade
        h.mech_link(p, cols[0], 0, cols[-1])
        h.act_manual(p, cols[0] - 20, 0)
        for (x, y) in pins:
            p.outlet(x, y)
        return p
    # two-circuit pushbutton: two stacked horizontal contact pairs
    top = [(x, y) for (x, y) in pins if y <= 10]
    bot = [(x, y) for (x, y) in pins if y > 10]
    hh = H / 2.0
    for grp, ny in ((top, -hh + 18), (bot, hh - 18)):
        xs = [x for x, _ in grp if abs(x) > 40]
        if len(xs) >= 2:
            p.line(min(xs), ny, -12, ny)
            p.line(max(xs), ny, 12, ny)
            p.line(-12, ny, 12, ny - 8)
    p.line(0, -hh + 18, 0, hh - 18)                  # push stem linking both
    p.line(-12, -hh, 12, -hh)                        # button
    p.line(0, -hh, 0, -hh + 10)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def draw_ansi_coil(rec):
    """ANSI relay coil: a plain rectangle."""
    return draw_coil(rec)


# =========================================================================
# Misc
# =========================================================================

def draw_starter(rec):
    """Glow starter for a fluorescent lamp (07-09-04): circle with a contact."""
    p = Ppd()
    r = 46
    p.circle(0, 0, r)
    # internal break contact with bimetal dots
    p.line(0, -50, 0, -r)
    p.line(0, 50, 0, r - 2)
    p.line(-12, -10, 12, 10)                          # bimetal blade
    p.dot(-12, -10, 4)
    p.dot(12, 10, 4)
    for (x, y) in pins_of(rec):
        p.outlet(x, y)
    return p


# =========================================================================
# Dispatch
# =========================================================================

def classify(rec):
    c = code(rec)
    name = rec["name"].lower()
    cat = rec["category"]

    if "/fuses" in cat:
        if "striker" in name or "mechanical linkage" in name:
            return draw_fuse_striker
        if "alarm" in name or "separate alarm" in name:
            return draw_fuse_alarm
        if "fuse-switch" in name or "fuse switch-disconnector" in name:
            return draw_fuse_switch
        return draw_fuse_general
    if "appliance protection" in cat:
        return draw_class

    # fuses living under the ANSI protective-devices category
    if "fuse (form 2)" in name:
        return draw_fuse_form2
    if "fuse (form 1)" in name or "supply side" in name:
        return draw_fuse_general

    if "ansi" in cat:
        if "/circuit breakers" in cat:
            return draw_ansi_breaker
        if "/protective devices" in cat:
            return draw_protective
        if "switches and contactors" in cat:
            if name == "make contact":
                return draw_vcontact
            return draw_ansi_hcontact

    # EN switching
    if "starter for fluorescent" in name:
        return draw_starter
    if "/relays" in cat:
        if "buchholz" in name or "gas relay" in name:
            return draw_gas_relay
        if "auto-clos" in name:
            return draw_autoclose
        return draw_coil
    if "fuse (form 2)" in name:
        return draw_fuse_form2
    if "fuse (form 1)" in name or "supply side" in name:
        return draw_fuse_general
    if "intermediate switch" in name:
        return draw_intermediate
    if "change-over" in name or "change over" in cat or "2 way" in name \
            or "two-way disconnector" in name or "off-position in the centre" in name:
        return draw_changeover
    if "2 makes" in name or "2 brakes" in name:
        return draw_multi_make_break
    if c == "07-07-01":                              # manual / push / pull / multi
        return draw_manual_switch
    if c in ("07-07-03", "07-07-04", "07-07-05", "07-07-06", "07-08-04"):
        return draw_actuated
    return draw_vcontact


def main():
    recs = json.load(open(SPEC))
    n = 0
    for rec in recs:
        p = classify(rec)(rec)
        xml = p.document(rec["name"], rec["designation"], rec["standard"], rec["id"])
        rel = dl.slug_path(rec["category"], rec["name"])
        out = os.path.join(LIBDIR, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(xml)
        n += 1
    print(f"wrote {n} .ppd files under {LIBDIR}")


if __name__ == "__main__":
    main()
