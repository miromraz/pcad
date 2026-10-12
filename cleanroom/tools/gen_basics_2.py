#!/usr/bin/env python3
"""Generate the basics_2 batch (everyday EN 60617 schematic basics) as .ppd.

Clean-room: drawn from EN/IEC 60617 knowledge + the spec facts only. Families:
  IEC rectangular logic gates, indicating instruments (meters), connectors &
  construction elements, passive parts (capacitors, inductors, resistors,
  thermistors, battery), discrete semiconductors (bridges, thyristor/triac,
  transils, transistors, tubes, optocouplers), telecom, converters, audio
  signalling, fuses and misc (arresters, op-amp, piezo crystals), trunking.

Reuses draw_lib.py; extra glyphs in helpers_basics_2.py (+ winding/semicircle
helpers shared with the machines & switching teams). Run: python3 gen_basics_2.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import (Ppd, arrow, arrowhead, sine, leads, add_outlets,
                      rect_leads, pin_center)
import helpers_basics_2 as H
from helpers_basics_2 import (winding_bumps_v, winding_along, semicircle,
                              tri_bar_v, tri_bar_h, cap_plates, tube)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_basics_2.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


# =========================================================================
# Logic gates (IEC 60617-12 rectangular / distinctive-shape qualifier)
# =========================================================================

def logic_gate(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    marks = rec["markings"]
    p = Ppd()
    ins = [pt for pt in pins if pt[0] < 0]
    outs = [pt for pt in pins if pt[0] > 0]
    iy = [y for _, y in ins]
    bl, br = -50, 50
    bt, bb = min(iy) - 18, max(iy) + 18
    p.rect(bl, bt, br, bb)
    for (x, y) in ins:
        p.line(bl, y, x, y)
    neg = ("nand" in name) or ("nor" in name) or ("xnor" in name)
    qual = marks[0] if marks else ("&" if "nand" in name else "1")
    p.text(0, (bt + bb) / 2.0, qual, size=60, al=9)
    ox, oy = outs[0]
    if neg:
        p.circle(br + 8, oy, 8)
        p.line(br + 16, oy, ox, oy)
    else:
        p.line(br, oy, ox, oy)
    add_outlets(p, pins)
    return p


def stabilizer(rec):
    pins = pins_of(rec)
    p = Ppd()
    l, t, r, b = -70, -70, 70, 40
    p.rect(l, t, r, b)
    for (x, y) in pins:                 # leads: in(left) out(right) gnd(bottom)
        if x < l:
            p.line(l, y, x, y)
        elif x > r:
            p.line(r, y, x, y)
        elif y > b:
            p.line(x, b, x, y)
    p.text(-42, 0, "in", size=36, al=9)
    p.text(42, 0, "out", size=36, al=9)
    p.text(0, 24, "gnd", size=36, al=9)
    add_outlets(p, pins)
    return p


# =========================================================================
# Meters (indicating instrument circle + quantity letter)
# =========================================================================

def meter_sym(rec):
    marks = rec["markings"]
    joined = ["".join(marks)] if marks else []
    r = rec["size"]["w"] // 2
    p = dl.meter(joined, pins_of(rec), r=r)
    if not marks:                                # indicating instrument pointer
        arrow(p, -r * 0.45, r * 0.5, r * 0.4, -r * 0.45)
    return p


# =========================================================================
# Connectors & construction elements
# =========================================================================

def banana_plug(rec):
    pins = pins_of(rec)
    p = Ppd()
    xs = [x for x, _ in pins]
    p.line(min(xs), 0, max(xs), 0)              # conductor baseline
    p.ellipse(110, -45, 190, 45)                # plug head (spring body)
    p.line(90, 0, 110, 0)
    for yy in (-30, -15, 0, 15, 30):            # banana springs
        p.line(120, yy, 180, yy, lw=2)
    add_outlets(p, pins)
    return p


def power_feeding(rec):
    pins = pins_of(rec)
    p = Ppd()
    p.line(0, -55, 0, -6)                        # male stem (top)
    p.polygon([(0, -6), (-10, -22), (10, -22)], fill=True)   # male contact head
    semicircle(p, 0, 10, 18, 0, 180)            # female socket cup (opens up)
    p.line(0, 10, 0, 55)                         # female stem (bottom)
    add_outlets(p, pins)
    return p


def shielded(rec):
    pins = pins_of(rec)
    p = Ppd()
    p.dot(0, 5, 4)                               # inner contact
    semicircle(p, 0, 5, 20, 180, 360)           # shield arc over it
    p.line(-20, 5, 20, 5)
    add_outlets(p, pins)
    return p


def equipotentiality(rec):
    p = Ppd()
    p.polygon([(0, -20), (-20, 25), (20, 25)])  # triangle (apex at the pin)
    add_outlets(p, pins_of(rec))
    return p


def frame_chassis(rec):
    p = Ppd()
    p.line(0, -13, 0, -3)
    p.line(-15, -3, 15, -3)                      # chassis bar
    for x in (-10, 0, 10):                       # slanted legs
        p.line(x, -3, x - 6, 11)
    add_outlets(p, pins_of(rec))
    return p


def terminal(rec):
    p = Ppd()
    p.circle(0, 0, 8)                            # terminal = small circle
    add_outlets(p, pins_of(rec))
    return p


# =========================================================================
# Thermistors / NTC / PTC
# =========================================================================

def thermistor_sym(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    bh = min(h / 2.0 - 4, 26)
    ext = w / 2.0 - 1
    p.rect(-9, -bh, 9, bh)                       # resistor body
    # non-linear temperature dependency line (oblique with a foot) + theta
    p.line(-ext, bh - 2, ext, -bh + 6)
    if "ptc" in name:
        p.line(-ext, bh - 2, -ext, bh - 12)     # foot up  = +t
    else:
        p.line(-ext, bh - 2, -ext + 8, bh - 2)  # foot along = -t (NTC default)
    p.text(0, -bh - 7, "θ", size=40, al=9)
    for (x, y) in pins:
        if y < -bh:
            p.line(0, -bh, x, y)
        elif y > bh:
            p.line(0, bh, x, y)
    add_outlets(p, pins)
    return p


# =========================================================================
# Capacitors
# =========================================================================

def capacitor_sym(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    hw = w / 2.0 - 2
    if "electrolytic" in name:
        p.line(-hw, -4, hw, -4)                             # + plate (straight)
        curve = [(-hw + 2 * (hw - 1) * i / 16.0,
                  4 + 7 * (1 - ((i / 8.0) - 1) ** 2)) for i in range(17)]
        p.polyline(curve)                                   # - plate (curved, cup up)
        p.text(hw * 0.55, -11, "+", size=34, al=9)
        p.line(0, -4, 0, -4)
        p.line(0, 4, 0, 11)
    else:
        gap = min(h / 2.0, 6)
        cap_plates(p, 0, 0, hw, gap)
        for (x, y) in pins:               # connect each pin to its plate
            p.line(0, -gap if y < 0 else gap, 0, y)
        if "variable" in name:
            arrow(p, -hw, hw, hw, -hw)                       # variability
        elif "adjustable" in name:
            d = hw - 1                                       # trimmer: line + bar
            p.line(-d, d, d, -d)
            p.line(d, -d, d - 8, -d + 2)
    add_outlets(p, pins)
    return p


# =========================================================================
# Inductors (winding = semicircle bumps)
# =========================================================================

def inductor_sym(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]

    if "coils" in name and "star" in name:
        return coils_star(rec)
    if "coils" in name and "triangle" in name:
        return coils_triangle(rec)

    p = Ppd()
    y0, y1 = -30, 30
    if "variable" in name:                       # air core variable
        winding_bumps_v(p, 0, y0, y1, 4, 20)
        p.line(0, -40, 0, y0)
        p.line(0, y1, 0, 40)
        arrow(p, -18, 30, 38, -30)               # variability arrow
    elif "air core" in name:
        winding_bumps_v(p, 0, y0, y1, 4, 20)
        p.line(0, -40, 0, y0)
        p.line(0, y1, 0, 40)
    else:                                        # cored inductors
        winding_bumps_v(p, 0, y0, y1, 4, 14)
        p.line(0, -40, 0, y0)
        p.line(0, y1, 0, 40)
        if "dashed" in name:                     # dashed magnetic core
            for yy in range(-28, 28, 12):
                p.line(18, yy, 18, yy + 7, lw=4)
                p.line(22, yy, 22, yy + 7, lw=4)
        elif "choking" in name:
            p.line(17, y0, 17, y1)               # single solid core line
        else:                                    # solid core
            p.line(18, y0, 18, y1)
            p.line(22, y0, 22, y1)
    add_outlets(p, pins)
    return p


def coils_star(rec):
    pins = pins_of(rec)
    p = Ppd()
    common = pins[0]
    p.dot(common[0], common[1], 4)
    for (x, y) in pins[1:]:
        d = math.hypot(x - common[0], y - common[1])
        ux, uy = (x - common[0]) / d, (y - common[1]) / d
        x0 = common[0] + ux * 14
        y0 = common[1] + uy * 14
        x1 = x - ux * 16
        y1 = y - uy * 16
        winding_along(p, x0, y0, x1, y1, 2, 13)
        p.line(x1, y1, x, y)
    add_outlets(p, pins)
    return p


def coils_triangle(rec):
    pins = pins_of(rec)
    p = Ppd()
    for i in range(3):
        (x0, y0) = pins[i]
        (x1, y1) = pins[(i + 1) % 3]
        d = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / d, (y1 - y0) / d
        winding_along(p, x0 + ux * 10, y0 + uy * 10,
                      x1 - ux * 10, y1 - uy * 10, 2, 13)
    add_outlets(p, pins)
    return p


# =========================================================================
# Battery / cells
# =========================================================================

def battery(rec):
    pins = pins_of(rec)
    p = Ppd()
    p.line(-18, 0, -10, 0)
    for x, half, lw in ((-10, 28, 4), (-4, 12, 6), (4, 28, 4), (10, 12, 6)):
        p.line(x, -half, x, half, lw=lw)
    p.line(10, 0, 18, 0)
    add_outlets(p, pins)
    return p


# =========================================================================
# Resistors (IEC rectangle + qualifiers)
# =========================================================================

def resistor_sym(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()

    if "shunt" in name:                          # EN 4-terminal shunt resistor
        p.rect(-8, -25, 8, 25)                   # current terminals = ends
        for (x, y) in pins:
            if x != 0:                           # voltage-sensing terminals = sides
                p.line(8 if x > 0 else -8, 25 if y > 0 else -25, x, y)
        add_outlets(p, pins)
        return p

    hw, hh = 10, 20
    p.rect(-hw, -hh, hw, hh)
    for (x, y) in pins:                          # axial leads (0, +-25)
        if x == 0 and y < -hh:
            p.line(0, -hh, 0, y)
        elif x == 0 and y > hh:
            p.line(0, hh, 0, y)

    if "light dependent" in name:                # LDR: incident light arrows
        arrow(p, -32, -24, -11, -7)
        arrow(p, -24, -30, -3, -13)
    elif "potentiometer" in name:                # wiper = perpendicular arrow onto body
        tap = [pt for pt in pins if pt[0] != 0][0]
        arrow(p, -28, tap[1], -hw, tap[1])       # arrow onto the left face
    elif "adjustable" in name:                   # rheostat: tap + variability arrow
        for (x, y) in pins:
            if x < -hw:
                p.line(x, y, -hw, y)
        arrow(p, -20, 26, 20, -26)
    elif "variable" in name:                     # variability arrow only
        arrow(p, -18, 28, 18, -28)
    add_outlets(p, pins)
    return p


# =========================================================================
# Discrete semiconductors (section 05)
# =========================================================================

def diode_bridge(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    R = 60
    corners = {"l": (-R, 0), "r": (R, 0), "t": (0, -R), "b": (0, R)}
    # diamond edges
    edges = [("t", "r"), ("r", "b"), ("b", "l"), ("l", "t")]
    for a, c in edges:
        p.line(*corners[a], *corners[c])
    # a diode on each edge, pointing toward the + corner
    if "left" in name:
        plus = "l"
    elif "right" in name:
        plus = "r"
    else:
        plus = "t"
    for a, c in edges:
        mx, my = (corners[a][0] + corners[c][0]) / 2.0, (corners[a][1] + corners[c][1]) / 2.0
        # direction: toward whichever endpoint is the + (or its neighbour)
        toward = corners[plus]
        ang = math.degrees(math.atan2(toward[1] - my, toward[0] - mx))
        _edge_diode(p, mx, my, ang)
    p.text(corners[plus][0] * 0.62, corners[plus][1] * 0.62, "+", size=34, al=9)
    if "round" in name:
        p.circle(0, 0, R + 1)
    add_outlets(p, pins)
    return p


def _edge_diode(p, cx, cy, ang):
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    s = 11
    # triangle pointing along (ux,uy) + cathode bar
    tip = (cx + ux * s, cy + uy * s)
    b1 = (cx - ux * s + px * s, cy - uy * s + py * s)
    b2 = (cx - ux * s - px * s, cy - uy * s - py * s)
    p.polygon([b1, b2, tip])
    p.line(tip[0] + px * s, tip[1] + py * s, tip[0] - px * s, tip[1] - py * s)


def thyristor(rec):
    pins = pins_of(rec)
    p = Ppd()
    tri_bar_h(p, 0, 0, h=14, w=14, flip=True)    # cathode (bar) on the left
    for (x, y) in pins:
        if x > 14:
            p.line(14, 0, x, 0)                   # anode (right)
        elif y == 0 and x < -14:
            p.line(-14, 0, x, 0)                  # cathode terminal
    gate = [pt for pt in pins if pt[1] != 0]
    if gate:
        gx, gy = gate[0]
        p.line(-14, 8, gx, gy)                   # gate from the cathode bar
    add_outlets(p, pins)
    return p


def triac(rec):
    pins = pins_of(rec)
    p = Ppd()
    hh = 34
    p.line(0, -hh, 0, hh)                         # central bar (shared)
    p.polygon([(-20, -hh), (-20, -4), (0, -18)])  # upper triangle -> centre (right)
    p.polygon([(20, hh), (20, 4), (0, 18)])       # lower triangle -> centre (left)
    for (x, y) in pins:
        if y == 0:
            p.line((20 if x > 0 else -20), 0, x, 0)
    gate = [pt for pt in pins if pt[1] != 0]
    if gate:
        gx, gy = gate[0]
        p.line(-20, -hh + 10, gx, gy)
    add_outlets(p, pins)
    return p


def transil(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    if "bidirectional" in name:                  # two zeners back-to-back
        h = 24
        p.line(0, -h, 0, h)                       # shared cathode line
        p.polygon([(-26, -h), (-26, h), (0, 0)])
        p.polygon([(26, -h), (26, h), (0, 0)])
        p.line(0, -h, -8, -h - 3)                 # zener flags
        p.line(0, h, 8, h + 3)
        for (x, y) in pins:
            p.line((26 if x > 0 else -26), 0, x, 0)
    else:                                        # unidirectional (single zener)
        h = 20
        tri_bar_h(p, 0, 0, h=h, w=14)
        p.line(14, -h, 22, -h - 5)               # zener flag
        for (x, y) in pins:
            if x < -14:
                p.line(-14, 0, x, 0)
            elif x > 14:
                p.line(14, 0, x, 0)
    add_outlets(p, pins)
    return p


def trisil(rec):
    pins = pins_of(rec)
    p = Ppd()
    h = 40
    p.line(0, -h, 0, h)                           # central shared bar
    p.polygon([(-18, -h), (-18, -6), (0, -22)])  # upper tri -> centre
    p.polygon([(18, h), (18, 6), (0, 22)])        # lower tri -> centre
    for (x, y) in pins:
        p.line((18 if x > 0 else -18), 0, x, 0) if x != 0 else None
    add_outlets(p, pins)
    return p


def varactor(rec):
    pins = pins_of(rec)
    p = Ppd()
    tri_bar_h(p, 0, 0, h=18, w=14)
    p.line(20, -18, 20, 18)                       # capacitor plate on the cathode
    for (x, y) in pins:
        if x < -14:
            p.line(-14, 0, x, 0)
        elif x > 20:
            p.line(20, 0, x, 0)
    add_outlets(p, pins)
    return p


def varistor(rec):
    pins = pins_of(rec)
    p = Ppd()
    p.rect(-9, -22, 9, 22)
    p.line(-21, 22, 21, -22)                      # voltage-dependency oblique
    p.line(-21, 22, -21, 14)                      # U foot
    for (x, y) in pins:
        if y < -22:
            p.line(0, -22, 0, y)
        elif y > 22:
            p.line(0, 22, 0, y)
    add_outlets(p, pins)
    return p


def diode_special(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    if "laser" in name:                          # vertical diode + emission rays
        tri_bar_v(p, 20, 0, h=12, w=12)
        for (x, y) in pins:
            if y < 0:
                p.line(20, -12, x, y)
            else:
                p.line(20, 12, x, y)
        for yy in (-6, 6):                       # coherent emission to the left
            arrow(p, 8, yy, -70, yy)
    elif "photodiode" in name:                   # diode + incident light (in)
        tri_bar_h(p, 0, 0, h=18, w=14)
        for (x, y) in pins:
            if x < -14:
                p.line(-14, 0, x, 0)
            elif x > 14:
                p.line(14, 0, x, 0)
        arrow(p, -30, -40, -12, -16)
        arrow(p, -18, -42, 0, -18)
    elif "schottki" in name or "schottky" in name:
        tri_bar_h(p, 0, 0, h=18, w=13)
        p.line(13, -18, 13, 18)                   # cathode bar w/ Schottky hooks
        p.line(13, -18, 22, -18)
        p.line(22, -18, 22, -11)
        p.line(13, 18, 4, 18)
        p.line(4, 18, 4, 11)
        for (x, y) in pins:
            if x < -13:
                p.line(-13, 0, x, 0)
            elif x > 13:
                p.line(13, 0, x, 0)
    else:                                        # tunnel / esaki diode
        tri_bar_h(p, 0, 0, h=18, w=13)
        p.line(13, -18, 13, 18)
        p.line(13, -18, 6, -18)                   # tunnel feet
        p.line(13, 18, 6, 18)
        for (x, y) in pins:
            if x < -13:
                p.line(-13, 0, x, 0)
            elif x > 13:
                p.line(13, 0, x, 0)
    add_outlets(p, pins)
    return p


# --- transistors (BJT / MOSFET) ------------------------------------------

def _bjt(p, pins, cx, bar_x, envelope_r, pnp):
    if envelope_r:
        p.circle(cx, 0, envelope_r)
    p.line(bar_x, -22, bar_x, 22)                 # base electrode bar
    base = min(pins, key=lambda q: q[0])          # left-most pin = base
    rights = sorted([pt for pt in pins if pt[0] > bar_x], key=lambda q: q[1])
    p.line(base[0], base[1], bar_x, 0)            # base lead
    if len(rights) >= 2:
        coll, emit = rights[0], rights[1]         # upper=collector, lower=emitter
        p.line(bar_x, -12, coll[0], coll[1])
        p.line(bar_x, 12, emit[0], emit[1])
        if pnp:
            ang = math.degrees(math.atan2(12 - emit[1], bar_x - emit[0]))
            ex, ey = (bar_x + emit[0]) / 2.0, (12 + emit[1]) / 2.0
            arrowhead(p, bar_x + (ex - bar_x) * 0.4, 12 + (ey - 12) * 0.4, ang)
        else:
            ang = math.degrees(math.atan2(emit[1] - 12, emit[0] - bar_x))
            arrowhead(p, emit[0], emit[1], ang)


def transistor_sym(rec):
    name = rec["name"].lower()
    cat = rec["category"]
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    if "mosfet" in cat:
        return mosfet_dep(rec)
    p = Ppd()
    env = w / 2.0 if "without envelope" not in name and "phototran" not in name else 0
    pnp = name.startswith("pnp")
    if "phototran" in name:                      # 2-pin: base is light
        cx = 14
        env = 34
        p.circle(cx, 0, env)
        p.line(cx - 22, -22, cx - 22, 22)        # base bar
        rights = sorted(pins, key=lambda q: q[1])
        p.line(cx - 22, -8, rights[0][0], rights[0][1])
        p.line(cx - 22, 8, rights[1][0], rights[1][1])
        ang = math.degrees(math.atan2(rights[1][1] - 8, rights[1][0] - (cx - 22)))
        arrowhead(p, rights[1][0], rights[1][1], ang)
        arrow(p, -56, -22, -24, -6)              # incident light
        arrow(p, -44, -30, -12, -14)
        add_outlets(p, pins)
        return p
    bar_x = min(x for x, _ in pins) + (32 if env else 12)
    _bjt(p, pins, 0, bar_x, env, pnp)
    add_outlets(p, pins)
    return p


def mosfet_dep(rec):
    pins = pins_of(rec)
    p = Ppd()
    r = rec["size"]["w"] / 2.0
    p.circle(0, 0, r)
    gx = -22
    p.line(gx, -20, gx, 20)                       # gate electrode bar
    ch = -8
    p.line(ch, -20, ch, 20)                       # channel (solid = depletion N)
    gate = min(pins, key=lambda q: q[0])
    p.line(gate[0], gate[1], gx, gate[1] if abs(gate[1]) < 20 else 0)
    rights = [pt for pt in pins if pt[0] > ch]
    for (x, y) in rights:
        if abs(y) < 6:                            # substrate (mid) + arrow
            p.line(ch, 0, x, y)
            arrowhead(p, ch + 16, 0, 180)         # N-channel: points to channel
        else:
            p.line(ch, -16 if y < 0 else 16, x, y)
    add_outlets(p, pins)
    return p


# --- optocouplers ---------------------------------------------------------

def optocoupler(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    L, T, R, B = -62, -36, 62, 36
    p.rect(L, T, R, B)
    # LED on the left (vertical diode between the two left pins), emitting right
    lefts = sorted([pt for pt in pins if pt[0] <= -40], key=lambda q: q[1])
    tri_bar_v(p, -40, 0, h=11, w=10)
    if len(lefts) >= 2:
        p.line(-40, -11, lefts[0][0], lefts[0][1])
        p.line(-40, 11, lefts[1][0], lefts[1][1])
    for yy in (-7, 7):                            # coupling light arrows
        arrow(p, -26, yy, 6, yy)
    # receiver on the right
    rights = sorted([pt for pt in pins if pt[0] >= 55], key=lambda q: q[1])
    extra = [pt for pt in pins if 0 < pt[0] < 55]      # base / darlington tap
    rx = 28
    if "triac" in name:                          # phototriac
        p.line(rx, -28, rx, 28)
        p.polygon([(rx - 14, -24), (rx - 14, -6), (rx, -15)])
        p.polygon([(rx + 14, 24), (rx + 14, 6), (rx, 15)])
        for (x, y) in rights:
            p.line(rx, min(26, max(-26, y)), x, y)
    elif "resistor" in name:                     # photoresistor
        p.rect(rx - 8, -20, rx + 8, 20)
        for (x, y) in rights:
            p.line((rx + 8 if y else rx), min(20, max(-20, y)) if y else 0, x, y)
            p.line(rx, y, x, y) if abs(y) > 20 else None
    elif "diode" in name and "npn" not in name:  # photodiode receiver
        tri_bar_v(p, rx, 0, h=11, w=10)
        for (x, y) in rights:
            p.line(rx, -11 if y < 0 else 11, x, y)
    else:                                        # NPN / darlington / diode+NPN
        bar = rx - 4
        p.line(bar, -18, bar, 18)                # transistor base bar
        p.line(bar - 18, 0, bar, 0)              # base lead (toward the LED)
        if len(rights) >= 2:                     # collector + emitter (w/ arrow)
            coll, emit = rights[0], rights[1]
            p.line(bar, -10, coll[0], coll[1])
            p.line(bar, 10, emit[0], emit[1])
            ang = math.degrees(math.atan2(emit[1] - 10, emit[0] - bar))
            arrowhead(p, (bar + emit[0]) / 2.0, (10 + emit[1]) / 2.0, ang)
        if "darlington" in name:                 # second base bar
            p.line(bar - 10, -12, bar - 10, 12)
    for (x, y) in extra:                          # base/darlington terminal lead
        p.line(rx - 8, 0, x, 0) if abs(y) < 5 else p.line(rx - 8, y * 0.4, x, y)
    add_outlets(p, pins)
    return p


# =========================================================================
# Thermionic tubes (section 05-10/05-11)
# =========================================================================

def tube_sym(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    if "cathode-ray" in name:
        return crt(rec)
    if "double diode" in name:
        return double_diode(rec)
    grids = {"triode": 1, "tetrode": 2, "pentode": 3, "pentagrid": 5}
    g = next((v for k, v in grids.items() if k in name), 1)
    r = max(42, rec["size"]["w"] / 2.0 - 6)
    return tube(pins, r, g, anodes=1)


def double_diode(rec):
    pins = pins_of(rec)
    p = Ppd()
    r = 45
    p.circle(0, 0, r)
    tops = sorted([pt for pt in pins if pt[1] < 0], key=lambda q: q[0])
    bots = sorted([pt for pt in pins if pt[1] > 0], key=lambda q: q[0])
    p.line(-26, -18, -6, -18)                     # two anode plates
    p.line(6, -18, 26, -18)
    for i, (x, y) in enumerate(tops[:2]):
        p.line((-16 if i == 0 else 16), -18, x, y)
    # directly-heated cathode (inverted V) to the bottom pins
    p.line(-10, 20, 0, 8)
    p.line(10, 20, 0, 8)
    for (x, y) in bots:
        p.line((-10 if x < 0 else 10), 20, x, y)
    add_outlets(p, pins)
    return p


def crt(rec):
    pins = pins_of(rec)
    p = Ppd()
    # electron-gun neck (left) widening to the screen (right)
    p.polyline([(-180, -30), (-260, -30), (-260, 30), (-180, 30)])  # base/neck
    p.line(-260, -30, -260, 30)
    p.polyline([(-180, -30), (210, -140), (210, 140), (-180, 30), (-180, -30)])
    p.line(210, -140, 210, 140)                   # screen (faceplate)
    p.line(-240, 0, -180, 0)                      # cathode
    for g, gx in enumerate((-150, -120, -90)):    # control grids
        p.line(gx, -18, gx, 18, lw=2)
    p.line(-40, -40, 40, -40)                     # deflection plates (vertical)
    p.line(-40, 40, 40, 40)
    p.line(-10, -70, -10, -24)                    # deflection plates (horizontal)
    p.line(80, -24, 80, 24)
    add_outlets(p, pins)
    return p


# =========================================================================
# Telecommunications
# =========================================================================

def telecom(rec):
    name = rec["name"].lower()
    cat = rec["category"]
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    if "magnetic head" in name:                  # C-shaped head with a gap
        p.arc(-13, -16, 13, 16, 0, -16, 0, 16)
        p.line(-2, -3, -2, 3)                     # the gap faces
        p.line(2, -3, 2, 3)
        add_outlets(p, pins)
        return p
    if "automatic transmitter" in name:          # perforated-tape reader
        p.rect(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
        for yy in range(-30, 40, 18):             # tape sprocket holes
            p.dot(-20, yy, 4)
            p.line(-10, yy, 30, yy, lw=2)
        return p
    if "telephone set" in name:
        p.rect(-90, 0, 90, 70)                              # base
        semicircle(p, 0, 0, 75, 180, 360)                   # handset arc
        p.circle(-75, 0, 10)
        p.circle(75, 0, 10)
        for (x, y) in pins:
            if y > 0:
                p.line(0, 70, x, y)
            else:
                p.line((-90 if x < 0 else 90), 0, x, y)
        add_outlets(p, pins)
        return p
    # switchboard: rect with crossed patch lines
    p.rect(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    p.line(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    p.line(-w / 2.0, h / 2.0, w / 2.0, -h / 2.0)
    for (x, y) in pins:
        if y > h / 2.0 - 1 or abs(y) < 5:
            p.line(0, 0, x, y) if abs(x) < w / 2.0 else p.line(
                (-w / 2.0 if x < 0 else w / 2.0), y, x, y)
        else:
            p.line((-w / 2.0 if x < 0 else w / 2.0), y, x, y)
    add_outlets(p, pins)
    return p


# =========================================================================
# Transmission converters / terminating sets
# =========================================================================

def converter(rec):
    marks = rec["markings"]
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    cx, cy = pin_center(pins)
    l, t, r, b = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
    p.rect(l, t, r, b)
    name = rec["name"].lower()
    if "pulse inverter" in name:
        p.polyline([(l + 20, b - 24), (l + 20, t + 24),
                    (cx, t + 24), (cx, b - 24), (r - 20, b - 24), (r - 20, t + 24)])
    else:
        p.line(l, t, r, b)                        # input/output divider diagonal
        if marks:
            p.text(l + w * 0.28, t + h * 0.26, marks[0], size=45, al=9)
        if len(marks) > 1:
            p.text(r - w * 0.28, b - h * 0.26, marks[1], size=45, al=9)
        if len(marks) > 2:
            p.text(cx, cy, marks[2], size=45, al=9)
    rect_leads(p, pins, l, t, r, b)
    return p


def terminating_set(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    cx, cy = pin_center(pins)
    l, t, r, b = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
    p.rect(l, t, r, b)
    if "balancing" in name:                      # balance wedge
        k = min(w, h) * 0.22
        p.polygon([(cx - k, cy + k), (cx + k, cy + k), (cx, cy - k)])
        p.line(cx - k * 1.5, cy - k, cx + k * 1.5, cy - k)
    rect_leads(p, pins, l, t, r, b)
    return p


# =========================================================================
# Audio signalling (section 08-07)
# =========================================================================

def audio(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    if "horn" in name:                           # trumpet wedge (vertical)
        p.polyline([(0, -20), (-35, 40), (35, 40), (0, -20)])
        for (x, y) in pins:
            if y < 0:
                p.line(0, -20, x, y)
            else:
                p.line(0, 40, x, y)
        add_outlets(p, pins)
        return p
    if "whistle" in name:                        # tall capsule
        a, b = w / 2.0, 80
        H.semicircle(p, 0, -b + a, a, 180, 360)
        p.line(-a, -b + a, -a, 55)
        p.line(a, -b + a, a, 55)
        p.line(-a, 55, a, 55)
        for (x, y) in pins:
            p.line((-a if x < 0 else a), 55, x, y)
        add_outlets(p, pins)
        return p
    # bell-family: a dome (upper semicircle) on its diameter + clapper
    r = min(w, h) / 2.0 if "siren" not in name else 34
    r = min(r, 40)
    semicircle(p, 0, 0, r, 180, 360)
    p.line(-r, 0, r, 0)
    if "buzzer" in name:
        semicircle(p, 0, 0, r * 0.6, 180, 360)   # inner arc
        p.line(0, 0, 0, 44)                       # clapper stem (tall body)
        p.dot(0, 40, 5)
    elif "single-stroke" in name:
        p.line(18, 0, 30, 24)                     # single hammer
        p.dot(30, 26, 5)
        p.line(0, 0, 0, 30)
        p.dot(0, 30, 4)
    elif "siren" in name:
        p.line(r, 0, 40, 0)                       # small horn stub
        p.line(0, 0, 0, 20)
    else:                                        # bell
        p.line(0, 0, 0, 34)
        p.dot(0, 34, 5)
    for (x, y) in pins:
        p.line(x, 0, x, y)
    add_outlets(p, pins)
    return p


# =========================================================================
# Fuses
# =========================================================================

def fuse(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    hw = w / 2.0 - 1
    by = h / 2.0 - 2
    p.rect(-hw, -by, hw, by)
    p.line(0, -by, 0, by)                         # fuse element
    if "slow" in name:
        p.rect(-hw, -by, hw, -by + 6, fill=True)  # slow-blow end caps
        p.rect(-hw, by - 6, hw, by, fill=True)
    add_outlets(p, pins)
    return p


# =========================================================================
# Miscellaneous (section 06/07/08)
# =========================================================================

def misc(rec):
    name = rec["name"].lower()
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()

    if "operational amplifier" in name:          # big triangle, apex = output
        p.polygon([(-88, -88), (-88, 88), (88, 0)])
        p.text(-62, 40, "+", size=55, al=9)      # inputs on the left
        p.text(-62, -40, "−", size=55, al=9)
        add_outlets(p, pins)
        return p

    if "glow lamp" in name:                      # neon: circle + electrodes + dot
        r = w / 2.0
        p.circle(0, 0, r)
        p.line(-12, -14, -12, 14)                 # electrode plates
        p.line(12, -14, 12, 14)
        p.dot(0, 0, 5)
        for (x, y) in pins:
            if y < 0:
                p.line(0, -r, 0, y)
            else:
                p.line(0, r, 0, y)
        add_outlets(p, pins)
        return p

    if "piezoelectric crystal" in name:
        if "three" in name:
            p.rect(-12, -6, 12, 6)                # crystal
            p.line(-32, -12, -4, -12)             # two top electrodes
            p.line(4, -12, 32, -12)
            p.line(-16, 12, 16, 12)               # bottom electrode
            for (x, y) in pins:
                p.line(x, -12 if y < 0 else 12, x, y)
        else:
            p.rect(-9, -8, 9, 8)                  # crystal
            p.line(-22, -12, 22, -12)             # plates
            p.line(-22, 12, 22, 12)
            for (x, y) in pins:
                if y < 0:
                    p.line(0, -12, 0, y)
                else:
                    p.line(0, 12, 0, y)
        add_outlets(p, pins)
        return p

    # lightning arresters / surge diverters
    if "4p" in name:                             # four arresters side by side
        cols = sorted(set(x for x, _ in pins))
        for cx in cols:
            p.rect(cx - 6, -14, cx + 6, 14)
            arrow(p, cx - 9, 8, cx + 9, -8)
        for (x, y) in pins:
            p.line(x, -14 if y < 0 else 14, x, y)
        add_outlets(p, pins)
        return p
    if "vacuum" in name:                         # arrester in a tube envelope
        p.circle(0, 0, 28)
        p.line(-14, -6, 14, -6)                   # electrode gap plates
        p.line(-14, 6, 14, 6)
        for (x, y) in pins:
            p.line(0, -28 if y < 0 else 28, 0, y)
        add_outlets(p, pins)
        return p
    # single lightning arrester / surge diverter
    p.rect(-6, -14, 6, 14)
    arrow(p, -9, 8, 9, -8)                        # diversion arrow
    for (x, y) in pins:
        if y < 0:
            p.line(0, -14, 0, y)
        else:
            p.line(0, 14, 0, y)
    add_outlets(p, pins)
    return p


def trunk_two(rec):
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    a = w / 2.0
    for y, lab in ((-18, "A"), (18, "B")):
        p.line(-a, y - 10, a, y - 10)
        p.line(-a, y + 10, a, y + 10)
        p.text(-a + 18, y, lab, size=40, al=9)
    return p


# =========================================================================
# Dispatch
# =========================================================================

def draw(rec):
    cat = rec["category"]
    name = rec["name"].lower()
    if cat == "electronics/ic":
        return logic_gate(rec)
    if cat == "electronics/ic/stabilizers":
        return stabilizer(rec)
    if cat == "electronics/meters":
        return meter_sym(rec)
    if cat == "electronics/mechanical":
        return banana_plug(rec)
    if cat == "electronics/mechanical/connectors":
        return power_feeding(rec) if "power feeding" in name else shielded(rec)
    if cat == "electronics/mechanical/construction elements":
        if "equipoten" in name:
            return equipotentiality(rec)
        if "frame" in name:
            return frame_chassis(rec)
        return terminal(rec)
    if cat == "electronics/passive":
        return thermistor_sym(rec)
    if cat == "electronics/passive/capacitors":
        return capacitor_sym(rec)
    if cat == "electronics/passive/inductors":
        return inductor_sym(rec)
    if cat == "electronics/passive/lamps":
        return battery(rec)
    if cat == "electronics/passive/resistors":
        return resistor_sym(rec)
    if cat == "electronics/semiconductors":
        if "bridge" in name:
            return diode_bridge(rec)
        if name == "thyristor":
            return thyristor(rec)
        if name == "triac":
            return triac(rec)
        if "transil" in name:
            return transil(rec)
        if name == "trisil":
            return trisil(rec)
        if name == "varactor":
            return varactor(rec)
        if name == "varistor":
            return varistor(rec)
    if cat == "electronics/semiconductors/diodes":
        return diode_special(rec)
    if cat == "electronics/semiconductors/optocouplers":
        return optocoupler(rec)
    if cat.startswith("electronics/semiconductors/transistors"):
        return transistor_sym(rec)
    if cat == "electronics/semiconductors/tubes":
        return tube_sym(rec)
    if cat.startswith("electronics/telecommunications"):
        return telecom(rec)
    if cat == "electronics/transmission/converters":
        return converter(rec)
    if cat == "electronics/transmission":
        if "converter" in name or "multiplier" in name:
            return converter(rec)
        return terminating_set(rec)
    if cat == "other/miscellaneous/audio":
        return audio(rec)
    if cat == "other/miscellaneous/fuses":
        return fuse(rec)
    if cat == "other/miscellaneous":
        return misc(rec)
    if cat.startswith("other/trunking systems"):
        return trunk_two(rec)
    raise SystemExit("unclassified: " + cat + " / " + rec["name"])


def main():
    recs = json.load(open(SPEC))
    n = 0
    for rec in recs:
        p = draw(rec)
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
