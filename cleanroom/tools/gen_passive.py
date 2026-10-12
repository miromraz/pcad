#!/usr/bin/env python3
"""Generate the 'passive' clean-room EN 60617 batch (.ppd files).

Families: ANSI zig-zag resistors, IEC rectangle resistors, lamps/signalling +
sources + thermocouples + cells, microwave transmission paths / cross-sections,
microwave one-and-two-port devices, and mechanical construction elements
(earth, contacts). Draws from EN/IEC 60617 + the spec facts only (clean-room).
Reuses draw_lib.py; extra geometry helpers in helpers_passive.py.

Run: python3 gen_passive.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd, arrow, arrowhead, sine, leads, add_outlets, rect_leads
import helpers_passive as hp

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_passive.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


# =========================================================================
# ANSI zig-zag resistors (electronics/passive/resistors-ansi)
# =========================================================================

def draw_ansi(rec):
    low = rec["name"].lower()
    pins = pins_of(rec)
    w = rec["size"]["w"]
    W2 = w / 2.0
    p = Ppd()
    hp.zigzag_v(p, -20, 20, 10)

    if low == "resistor with adjustable contact and off position":
        # single bottom terminal; top end is the (open) off position
        p.line(0, 20, 0, 30)
        p.outlet(0, 30)
        p.line(0, -20, 0, -26)        # wiper travel end
        p.line(-7, -26, 7, -26)       # off-position stop bar
        arrow(p, -W2, W2, W2, -W2)    # adjustability
        return p

    # standard axial terminals (0, +/-30), in spec order
    for (x, y) in pins:
        if x == 0 and abs(y) == 30:
            p.line(0, 20 if y > 0 else -20, 0, y)
            p.outlet(x, y)

    if low in ("adjustable resistor", "resistor with adjustable contact"):
        arrow(p, -W2, W2, W2, -W2)                     # variability arrow
    elif low == "nonliner resistor":
        p.line(-W2, W2, W2, -W2)                       # dependency line (varistor)
    elif low == "magnetoresistor":
        p.line(-W2, W2, W2, -W2)
        p.text(-W2 * 0.60, W2 * 0.64, "B", size=38, al=9)   # magnetic qualifier
    elif low.startswith("thermistor"):
        p.line(-W2, W2, W2, -W2)
        p.text(-W2 * 0.60, W2 * 0.64, "θ", size=38, al=9)  # theta
        if "nonlinear" in low:
            p.line(W2, -W2, W2 - 12, -W2 + 2)          # non-linearity foot
    elif low == "symmetrical photoconductive transducer":
        arrow(p, -40, -18, -14, 8)                     # two incident-light arrows
        arrow(p, -30, -28, -4, -2)

    # side taps (tapped resistor): any non-axial pin
    for (x, y) in pins:
        if x != 0:
            p.line(0, y, x, y)
            p.outlet(x, y)
    return p


# =========================================================================
# IEC rectangle resistors (electronics/passive/resistors)
# =========================================================================

def draw_iec_resistor(rec):
    pins = pins_of(rec)
    w = rec["size"]["w"]
    p = Ppd()
    l, t, r, b = -w / 2.0, -15, w / 2.0, 15     # 4:1-ish rectangle, leads to pins
    p.rect(l, t, r, b)
    rect_leads(p, pins, l, t, r, b)
    return p


# =========================================================================
# Lamps / signalling / sources / thermocouples / cells
# =========================================================================

def _lamp_glyph(p, r):
    p.circle(0, 0, r)
    d = r * math.cos(math.radians(45))
    p.line(-d, -d, d, d)
    p.line(-d, d, d, -d)


def draw_lamp(rec):
    p = Ppd()
    _lamp_glyph(p, 25)
    add_outlets(p, pins_of(rec))
    return p


def draw_signal_lamp(rec):
    p = Ppd()
    _lamp_glyph(p, 25)
    arrow(p, 0, -25, 0, -40)       # flashing emission rays (vertical)
    arrow(p, 0, 25, 0, 40)
    add_outlets(p, pins_of(rec))
    return p


def draw_indicator_lamp_transformer(rec):
    p = Ppd()
    _lamp_glyph(p, 25)
    sine(p, -36, 0, half=11, amp=8)    # built-in transformer windings, flanking
    sine(p, 36, 0, half=11, amp=8)
    add_outlets(p, pins_of(rec))
    return p


def draw_annunciator(rec):
    p = Ppd()
    p.rect(-25, -25, 25, 25)
    p.line(-25, -25, 25, 25)           # diagonal (drop-flag indicator)
    add_outlets(p, pins_of(rec))
    return p


def draw_cell(rec):
    p = Ppd()
    p.line(-2, -30, -2, 30)            # long plate (+)
    p.line(3, -14, 3, 14, lw=6)        # short thick plate (-)
    p.line(-5, 0, -2, 0)
    p.line(3, 0, 5, 0)
    add_outlets(p, pins_of(rec))
    return p


def draw_photovoltaic_cell(rec):
    p = Ppd()
    p.line(-3, -40, -3, 40)            # long plate (+)
    p.line(4, -20, 4, 20, lw=6)        # short plate (-)
    p.line(-5, 0, -3, 0)
    p.line(4, 0, 5, 0)
    arrow(p, -40, -30, -12, -2)        # incident light
    arrow(p, -32, -40, -4, -12)
    add_outlets(p, pins_of(rec))
    return p


def draw_solar_cell(rec):
    p = Ppd()
    p.line(-10, -4, 10, -4)            # long plate (+)
    p.line(-6, 4, 6, 4, lw=6)          # short plate (-)
    p.line(0, -31, 0, -4)
    p.line(0, 4, 0, 31)
    p.line(-9, -22, -3, -10)           # incident light rays
    p.line(-3, -24, 3, -12)
    add_outlets(p, pins_of(rec))
    return p


def draw_source(rec):
    """Circular source: generic / AC (~) / DC (=)."""
    low = rec["name"].lower()
    w = rec["size"]["w"]
    r = w // 2
    p = Ppd()
    p.circle(0, 0, r)
    if low.startswith("ac"):
        sine(p, 0, 0, half=r * 0.55, amp=r * 0.30)
    elif low.startswith("dc"):
        p.line(-r * 0.4, -6, r * 0.4, -6)                     # solid (=)
        for x in range(int(-r * 0.4), int(r * 0.4), 12):      # dashed
            p.line(x, 6, x + 7, 6)
    else:
        p.line(-r, 0, r, 0)                                   # general source
    leads(p, pins_of(rec), r)
    return p


def draw_ideal_source(rec):
    """Ideal voltage (line perpendicular to flow) / current (line along flow)."""
    low = rec["name"].lower()
    p = Ppd()
    r = 20
    p.circle(0, 0, r)
    if "current" in low:
        p.line(0, -r, 0, r)        # along the leads
    else:
        p.line(-r, 0, r, 0)        # perpendicular
    add_outlets(p, pins_of(rec))
    return p


def draw_ideal_gyrator(rec):
    p = Ppd()
    p.rect(-40, -20, 40, 20)       # corners == pins
    p.circle(0, 0, 11)             # gyration glyph
    arrow(p, -22, 0, 22, 0)
    add_outlets(p, pins_of(rec))
    return p


def draw_hall(rec):
    p = Ppd()
    p.rect(-8, -25, 8, 25)
    p.line(-8, -25, 8, 25)         # Hall cross
    p.line(-8, 25, 8, -25)
    add_outlets(p, pins_of(rec))
    return p


def draw_thermocouple(rec):
    p = Ppd()
    p.line(-40, -80, 0, 2)         # two dissimilar wires -> measuring junction
    p.line(40, -80, 0, 2)
    p.dot(0, 2, 4)
    add_outlets(p, pins_of(rec))
    return p


def draw_thermocouple_heater(rec, insulated):
    p = Ppd()
    p.line(-40, -80, 0, 0)         # thermocouple wires
    p.line(40, -80, 0, 0)
    p.dot(0, 0, 4)
    if insulated:
        p.line(-41, 80, 41, 80)                    # heater bar, not touching junction
    else:
        p.line(-41, 80, 0, 0)                      # heater touches the junction
        p.line(41, 80, 0, 0)
    add_outlets(p, pins_of(rec))
    return p


LAMP_DISPATCH = {
    "lamp": draw_lamp,
    "signal lamp, flashing type": draw_signal_lamp,
    "indicator lamp energized by a built-in transformer": draw_indicator_lamp_transformer,
    "electromechanical indicator, annunciator element": draw_annunciator,
    "cell": draw_cell,
    "photovoltaic cell": draw_photovoltaic_cell,
    "solar cell": draw_solar_cell,
    "ac voltage source": draw_source,
    "dc voltage source": draw_source,
    "voltage source": draw_source,
    "ideal voltage source": draw_ideal_source,
    "ideal current source": draw_ideal_source,
    "ideal gyrator": draw_ideal_gyrator,
    "hall generator with four connections": draw_hall,
    "thermocouple": draw_thermocouple,
    "thermocouple with insulated heating element":
        lambda r: draw_thermocouple_heater(r, True),
    "thermocouple with non-insulated heating element":
        lambda r: draw_thermocouple_heater(r, False),
}


def draw_lamp_family(rec):
    return LAMP_DISPATCH[rec["name"].lower()](rec)


# =========================================================================
# Microwave transmission paths / cross-sections
# =========================================================================

def _fill_rect(p, w, h, cx=0, cy=0):
    p.rect(cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)


def draw_optical(rec):
    """Optical fibre: path line (full width) + refractive-index profile glyph."""
    low = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    p.line(-w / 2.0, 0, w / 2.0, 0)             # fibre path
    gx = -w / 2.0 + 8
    gh = h / 2.0 - 2
    gw = 22
    p.line(gx, -gh, gx, gh)                     # profile axis (n)
    p.line(gx, gh, gx + gw, gh)                 # radius axis
    if "graded" in low:
        pts = [(gx + gw * t / 8.0,
                gh - (gh + gh) * (1 - (t / 8.0 - 1) ** 2)) for t in range(9)]
        p.polyline(pts)
    elif "single mode" in low:
        p.polyline([(gx, gh), (gx, -gh * 0.2), (gx + gw * 0.3, -gh * 0.2),
                    (gx + gw * 0.3, gh)])       # narrow step
    elif "multimode" in low:
        p.polyline([(gx, gh), (gx, -gh * 0.6), (gx + gw * 0.7, -gh * 0.6),
                    (gx + gw * 0.7, gh)])       # wide step
    else:
        p.circle(0, 0, min(w, h) / 2.0 - 2)     # general fibre: core circle
    return p


def draw_mw_path(rec):
    low = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()

    if "optical fibre" in low:
        return draw_optical(rec)
    if low == "circular waveguide":
        p.circle(0, 0, w / 2.0)
    elif low == "coaxial waveguide":
        p.circle(0, 0, w / 2.0)
        p.circle(0, 0, w / 6.0)
        p.dot(0, 0, 3)
    elif low == "rectangular waveguide" or low == "waveguide":
        _fill_rect(p, w, h)
    elif low == "ridged waveguide":
        _fill_rect(p, w, h)
        p.line(0, -h / 2.0, 0, -h / 2.0 + 10)     # ridges
        p.line(0, h / 2.0, 0, h / 2.0 - 10)
    elif low == "goubau line":
        p.line(-w / 2.0, 0, w / 2.0, 0)
        p.circle(0, 0, h / 2.0 - 2)
    elif low == "stripline with 2 conductors":
        p.line(-w / 2.0, -h / 2.0, w / 2.0, -h / 2.0)
        p.line(-w / 2.0, h / 2.0, w / 2.0, h / 2.0)
    elif low == "stripline with 3 conductors":
        p.line(-w / 2.0, -h / 2.0 + 2, w / 2.0, -h / 2.0 + 2)
        p.line(-w / 2.0, 0, w / 2.0, 0)
        p.line(-w / 2.0, h / 2.0 - 2, w / 2.0, h / 2.0 - 2)
    elif "pair of symmetrical waveguide connectors" in low:
        p.line(-6, -h / 2.0, -6, h / 2.0)
        p.line(6, -h / 2.0, 6, h / 2.0)
        p.line(-10, 0, -6, 0)
        p.line(6, 0, 10, 0)
    elif "pair of asymmetric waveguide connectors" in low:
        p.line(-18, -h / 2.0, -18, h / 2.0)       # full flange
        p.line(18, -h / 4.0, 18, h / 4.0)         # short (asymmetric) flange
        p.line(-18, 0, 18, 0)
    elif low == "mode suppression":
        _fill_rect(p, w, h)
        a, c = w / 2.0, h / 2.0                                 # suppression hatch
        p.line(-a, -c, a, c, lw=2)
        p.line(-a, 0, 0, c, lw=2)
        p.line(0, -c, a, 0, lw=2)
    elif "rotatable joint" in low:
        p.circle(0, 0, 22)
        arrow(p, -14, -10, 14, -10)                # rotation
        p.line(-20, -33, 20, -33)                  # flanges
        p.line(-20, 33, 20, 33)
        p.line(0, -22, 0, -33)
        p.line(0, 22, 0, 33)
    elif "reflector, reflecting totally" in low:
        p.line(-8, -h / 2.0, -8, h / 2.0)          # solid surface
        hp.hatch_wall(p, -8, -h / 2.0 + 4, h / 2.0, 20)
    elif "reflector, reflecting partially" in low:
        hp.dashed_v(p, -18, -h / 2.0, h / 2.0)     # broken surface = partial
        hp.hatch_wall(p, -18, -h / 2.0 + 4, h / 2.0, 36)
    elif "flexible waveguide" in low:
        hp.accordion_h(p, -30, 30, 18)
    elif "twisted waveguide" in low:
        p.line(-30, 0, -8, 0)
        p.line(-8, -18, 8, 18)                     # crossover twist
        p.line(-8, 18, 8, -18)
        p.line(8, 0, 30, 0)
    elif "resonator" in low:
        p.circle(0, 0, w / 2.0)                    # resonator cavity
        p.line(-w / 4.0, 0, w / 4.0, 0)
    else:
        _fill_rect(p, w, h)
    add_outlets(p, pins)
    return p


# =========================================================================
# Microwave one-and-two-port devices
# =========================================================================

def _mark(p, tokens, cx, cy):
    if not tokens:
        return
    txt = " ".join(tokens)
    size = 70 if len(txt) <= 1 else 55
    p.text(cx, cy, txt, size=size, al=9)


def draw_mw_2port(rec):
    low = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    marks = rec["markings"]
    pins = pins_of(rec)
    p = Ppd()
    cx, cy = dl.pin_center(pins) if pins else (0.0, 0.0)
    L, R = cx - w / 2.0, cx + w / 2.0
    T, B = cy - h / 2.0, cy + h / 2.0

    # --- special shapes -------------------------------------------------
    if "e-h tuner" in low:
        p.line(L, cy, R, cy)
        p.line(cx, T, cx, B)
        _mark(p, [marks[0]] if marks else [], cx + 18, T + 22)   # E
        _mark(p, [marks[1]] if len(marks) > 1 else [], cx + 18, cy + 20)  # H
        add_outlets(p, pins)
        return p
    if "multi-stub tuner" in low:
        p.line(L, cy, R, cy)
        for sx in (cx - 36, cx, cx + 36):
            p.line(sx, T, sx, B)                  # three stubs (full height)
            p.rect(sx - 6, B - 20, sx + 6, B)
        add_outlets(p, pins)
        return p
    if "slide screw tuner" in low:
        p.line(L, cy, R, cy)
        p.line(cx, cy, cx, B - 10)               # one adjustable stub
        p.rect(cx - 7, B - 30, cx + 7, B - 4)
        arrow(p, cx - 30, T + 14, cx + 30, T + 14)   # slide adjustability
        add_outlets(p, pins)
        return p
    if "band-pass filter switched by gas discharge" in low:
        p.line(-60, 0, 60, 0)                    # path
        p.rect(-30, -52, 30, 10)                 # filter cavity
        p.circle(0, 100, 30)                     # gas-discharge tube
        p.line(0, 10, 0, 70)
        p.line(-40, 80, -15, 80)                 # electrodes from bottom pins
        p.line(40, 80, 15, 80)
        add_outlets(p, pins)
        return p
    if low == "short circuit":
        p.line(-40, 0, 42, 0)
        p.line(42, -40, 42, 40)                  # short bar
        hp.hatch_wall(p, 42, -34, 40, 10)
        add_outlets(p, pins)
        return p
    if low == "sliding short circuit":
        p.line(-40, 0, 10, 0)
        p.rect(10, -45, 50, 45)                  # sliding plunger
        arrow(p, 0, -52, 55, -52)                # slide direction
        add_outlets(p, pins)
        return p
    if "cavity resonator" in low:
        p.ellipse(L, T, R, B)
        return p
    if low == "transition":
        p.polygon([(L, T), (R, 0), (L, B)])      # generic transition wedge
        return p
    if "taper transition" in low:
        r = 25
        p.circle(L + r, 0, r)                     # circular end (left)
        p.rect(6, T, R, B)                        # rectangular end (right), full height
        p.line(L + 2 * r, -h / 4.0, 6, T)         # long tapered walls
        p.line(L + 2 * r, h / 4.0, 6, B)
        return p
    if "transition from circular to rectangular" in low:
        r = h / 2.0 - 2
        p.circle(L + r, 0, r)                     # circular end (left)
        p.rect(6, T + 6, R, B - 6)                # rectangular end (right)
        p.line(L + 2 * r, -h / 4.0, 6, T + 6)
        p.line(L + 2 * r, h / 4.0, 6, B - 6)
        return p
    if low == "attenuator - other form":
        _fill_rect(p, w, h)                      # small attenuator glyph
        return p

    # --- generic device in a transmission path --------------------------
    p.line(L, cy, R, cy)                         # path, full width
    dw = min(w * 0.55, 84)
    p.rect(cx - dw / 2.0, T, cx + dw / 2.0, B)   # device envelope, full height

    if "capacitive" in low:
        p.line(cx - 16, cy - 6, cx + 16, cy - 6)         # shunt capacitor plates
        p.line(cx - 16, cy + 6, cx + 16, cy + 6)
    elif "resonant" in low:
        p.circle(cx, cy - 14, 12)                        # L
        p.line(cx - 14, cy + 16, cx + 14, cy + 16)       # C
        p.line(cx - 14, cy + 26, cx + 14, cy + 26)
    elif "isolator" in low:
        arrow(p, cx - 24, cy, cx + 24, cy)               # one-way
    elif "mode filter" in low:
        for dy in (-18, 0, 18):
            p.line(cx - 22, cy + dy, cx + 22, cy + dy)
    elif "variable" in low or "matching" in low:
        arrow(p, cx - dw / 2.0, B, cx + dw / 2.0, T)     # variability
    else:
        _mark(p, marks, cx, cy)
    add_outlets(p, pins)
    return p


# =========================================================================
# Mechanical construction elements
# =========================================================================

def draw_earth(rec):
    p = Ppd()
    p.line(0, -20, 0, 0)
    p.line(-20, 0, 20, 0)
    p.line(-13, 7, 13, 7)
    p.line(-6, 14, 6, 14)
    add_outlets(p, pins_of(rec))
    return p


def draw_protective_earth(rec):
    p = Ppd()
    p.circle(0, 7, 30)                 # earth inside a circle
    p.line(0, -20, 0, -8)
    p.line(-16, -8, 16, -8)
    p.line(-10, 0, 10, 0)
    p.line(-4, 8, 4, 8)
    add_outlets(p, pins_of(rec))
    return p


def draw_noiseless_earth(rec):
    p = Ppd()
    p.polygon([(0, -20), (30, 0), (0, 20), (-30, 0)])    # earth inside a diamond
    p.line(-13, 0, 13, 0)
    p.line(-8, 6, 8, 6)
    p.line(-3, 12, 3, 12)
    add_outlets(p, pins_of(rec))
    return p


def draw_female_contact(rec):
    p = Ppd()
    p.line(-18, 0, 6, 0)
    p.arc(-5, -11, 17, 11, 0, -11, 0, 11)   # socket cup (left-opening semicircle)
    add_outlets(p, pins_of(rec))
    return p


def draw_male_contact(rec):
    p = Ppd()
    p.line(-18, 0, 18, 0)                    # h=0: strictly on the axis
    add_outlets(p, pins_of(rec))
    return p


CONSTRUCTION = {
    "earth, ground": draw_earth,
    "protective earth, protective ground": draw_protective_earth,
    "noiceless earth, noiceless ground": draw_noiseless_earth,
    "female contact (socket)": draw_female_contact,
    "male contact": draw_male_contact,
}


def draw_construction(rec):
    return CONSTRUCTION[rec["name"].lower()](rec)


# =========================================================================
# Dispatch
# =========================================================================

def classify(rec):
    cat = rec["category"]
    if cat == "electronics/passive/resistors-ansi":
        return draw_ansi
    if cat == "electronics/passive/resistors":
        return draw_iec_resistor
    if cat == "electronics/passive/lamps":
        return draw_lamp_family
    if cat == "electronics/mechanical/construction elements":
        return draw_construction
    if "one and two port" in cat:
        return draw_mw_2port
    if cat == "electronics/microwave" or "transmission paths" in cat:
        return draw_mw_path
    raise SystemExit("unclassified: " + cat)


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
