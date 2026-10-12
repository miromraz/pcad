#!/usr/bin/env python3
"""Generate the meters_sources pilot batch (98 EN 60617 symbols) as .ppd files.

Draws from the EN/IEC 60617 standard + the spec facts only (clean-room).
Families: indicating meters (circle), energy meters (rect), counters, clocks,
windings, converters/rectifiers, generators, power stations. Reusable glyph
helpers live in draw_lib.py. Run: python3 gen_meters_sources.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd, arrow, arrowhead, sine, leads, add_outlets, rect_leads

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_meters_sources.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def dashed_circle(p, cx, cy, r, n=16, lw=dl.STD_LW):
    """A broken (dashed) circle from short chords, for 'projected' stations."""
    for k in range(0, n, 2):
        a0 = 2 * math.pi * k / n
        a1 = 2 * math.pi * (k + 1) / n
        pts = [(cx + r * math.cos(a0 + (a1 - a0) * t / 4.0),
                cy + r * math.sin(a0 + (a1 - a0) * t / 4.0)) for t in range(5)]
        p.polyline(pts, lw)


def dashed_segment(p, x1, y1, x2, y2, dash=14, lw=dl.STD_LW):
    """A straight segment drawn as a broken (dashed) line."""
    d = math.hypot(x2 - x1, y2 - y1)
    n = max(int(d / dash), 1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    t = 0.0
    while t < d:
        a, b = t, min(t + dash * 0.6, d)
        p.line(x1 + ux * a, y1 + uy * a, x1 + ux * b, y1 + uy * b, lw)
        t += dash


def ngon(cx, cy, r, n, rot=-math.pi / 2):
    return [(cx + r * math.cos(rot + 2 * math.pi * i / n),
             cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


# =========================================================================
# Family drawers
# =========================================================================

def _q_galvanometer(p, r):          # moving-pointer indicating instrument
    arrow(p, 0, r * 0.5, r * 0.34, -r * 0.5)
def _q_waveform(p, r):              # oscilloscope: displayed waveform
    sine(p, 0, 0, half=r * 0.6, amp=r * 0.34)
def _q_oscillograph(p, r):         # recording instrument: waveform + stylus line
    sine(p, 0, -r * 0.12, half=r * 0.6, amp=r * 0.3)
    p.line(-r * 0.55, r * 0.55, r * 0.55, r * 0.55, lw=2)
def _q_synchroscope(p, r):         # rotating phasor pointer
    arrow(p, 0, 0, r * 0.62, -r * 0.62)
def _q_synchronous(p, r):          # synchronous machine: phasor arrow
    arrow(p, 0, r * 0.1, 0, -r * 0.6)
def _q_gyro(p, r):                 # gyroscope: spin axis through the body
    p.line(-r * 0.7, 0, r * 0.7, 0, lw=2)
    p.line(-r * 0.7, -r * 0.18, -r * 0.7, r * 0.18, lw=2)
    p.line(r * 0.7, -r * 0.18, r * 0.7, r * 0.18, lw=2)

QUALIFIER = {
    "galvanometer": _q_galvanometer,
    "oscilloscope": _q_waveform,
    "oscillograph": _q_oscillograph,
    "synchronoskope": _q_synchroscope,
    "synchronous device, general symbol": _q_synchronous,
    "gyro": _q_gyro,
}


def draw_meter(rec):
    """Indicating instrument: circle, markings inside, leads to pins; blank
    instruments get their EN 60617 qualifying sign (QUALIFIER)."""
    r = min(rec["size"]["w"], rec["size"]["h"]) // 2
    p = dl.meter(rec["markings"], pins_of(rec), r=r)
    q = QUALIFIER.get(rec["name"])
    if q and not rec["markings"]:
        q(p, r)
    return p


def draw_energy(rec):
    """Integrating/energy meter: upright rectangle, markings inside."""
    return dl.energy_meter(rec["markings"], pins_of(rec),
                           rec["size"]["w"], rec["size"]["h"])


def draw_counter(rec):
    """Pulse/counter: rectangle = spec box centred on the pin centroid."""
    return dl.body_rect(rec["markings"], pins_of(rec),
                        rec["size"]["w"], rec["size"]["h"])


def draw_clock(rec):
    """Clock: circle with hour+minute hands; 4 terminals on the circle."""
    r = min(rec["size"]["w"], rec["size"]["h"]) // 2
    p = Ppd()
    p.circle(0, 0, r)
    p.line(0, 0, 0, -r * 0.62)          # minute hand (up)
    p.line(0, 0, r * 0.45, 0)           # hour hand (right)
    name = rec["name"]
    if "master" in name:
        p.dot(0, 0, 5)
    if "contact" in name:
        p.line(r * 0.45, 0, r * 0.75, -r * 0.3)   # contact blade off hour hand
    leads(p, pins_of(rec), r)
    return p


def fit_box(p_segs, w, h, pad=0.0):
    """Scale a list of point-segments so their bbox fills (w×h) centred on 0."""
    pts = [pt for seg in p_segs for pt in seg]
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    bw = (max(xs) - min(xs)) or 1.0
    bh = (max(ys) - min(ys)) or 1.0
    cx = (max(xs) + min(xs)) / 2.0
    cy = (max(ys) + min(ys)) / 2.0
    sx = (w - pad) / bw
    sy = (h - pad) / bh
    return [[((x - cx) * sx, (y - cy) * sy) for (x, y) in seg] for seg in p_segs]


def draw_winding(rec):
    """Phase-winding connection pictograms (star/delta/V/T/zigzag/polygon).
    Built in a unit frame, then scaled to fill the spec box (STYLE.md §9)."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    R = 10.0
    polylines, polygons = [], []

    def star(n, rot=-math.pi / 2):
        for i in range(n):
            a = rot + 2 * math.pi * i / n
            polylines.append([(0, 0), (R * math.cos(a), R * math.sin(a))])

    if "two-phase" in name:                     # right angle (two 90° windings)
        polylines += [[(0, R), (0, 0)], [(0, 0), (R, 0)]]
    elif "four-phase" in name:                  # cross (+)
        star(4, rot=0)
    elif "zigzag" in name or "interconnected" in name:
        n = 6 if "6-phase" in name else 3
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / n
            mx, my = R * 0.5 * math.cos(a), R * 0.5 * math.sin(a)
            a2 = a + 0.7
            polylines.append([(0, 0), (mx, my),
                              (mx + R * 0.6 * math.cos(a2), my + R * 0.6 * math.sin(a2))])
    elif "double delta" in name:                # two opposed triangles
        polygons += [ngon(0, 0, R, 3, -math.pi / 2), ngon(0, 0, R, 3, math.pi / 2)]
    elif "polygon" in name:                     # hexagon
        polygons.append(ngon(0, 0, R, 6))
    elif "delta" in name and "open" in name:    # open delta = V (two sides)
        a, b, c = ngon(0, 0, R, 3, math.pi / 2)
        polylines.append([a, b, c])
    elif "delta" in name:                       # closed triangle
        polygons.append(ngon(0, 0, R, 3, -math.pi / 2))
    elif name.rstrip().endswith(", v"):         # V winding
        polylines += [[(-R, -R), (0, R)], [(R, -R), (0, R)]]
    elif name.rstrip().endswith(", t"):         # T winding
        polylines += [[(-R, -R), (R, -R)], [(0, -R), (0, R)]]
    elif "star" in name:                        # Y, 3 or 6 phase
        star(6 if "6-phase" in name else 3)
    else:
        star(3)

    segs = polylines + polygons
    fitted = fit_box(segs, w, h)
    p = Ppd()
    for i, seg in enumerate(fitted):
        if i < len(polylines):
            p.polyline(seg)
        else:
            p.polygon(seg)
    add_outlets(p, pins_of(rec))
    return p


def draw_generator(rec):
    """Rotating-machine generator: circle with G (+ adjustability / sine / PV)."""
    name = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    if "thermionic" in name or "thermoelectric" in name:
        return draw_thermo_generator(rec)
    if "photovoltaic" in name:
        return draw_pv_generator(rec)
    p = Ppd()
    r = 60
    p.circle(0, 0, r)
    p.marking(["G"], bodyw=2 * r, bodyh=2 * r, shape="circle")
    if "adjustable" in name:
        arrow(p, -(r + 12), r + 12, r + 12, -(r + 12))      # variability arrow
    if "sine-wave" in name:
        sine(p, 0, r * 0.55, half=22, amp=10)
    if "mains power supply" in name:
        p.line(-18, r * 0.5, 18, r * 0.5)                   # = (DC)
        sine(p, 0, -r * 0.55, half=16, amp=8)               # ~ (AC)
    leads(p, pins, r)
    return p


def draw_pv_generator(rec):
    """Photovoltaic generator: generator circle + two radiation arrows at it."""
    p = Ppd()
    r = 60
    p.circle(0, 0, r)
    p.marking(["G"], bodyw=120, bodyh=120, shape="circle")
    leads(p, pins_of(rec), r)
    # two parallel light arrows pointing in from the upper-left
    for off in (-22, 22):
        x1, y1 = -107, -44 + off
        x2, y2 = -50, 13 + off
        arrow(p, x1, y1, x2, y2)
    return p


def draw_thermo_generator(rec):
    """Thermoelectric / thermionic generator: heat-source block on top, a
    generator circle (G) below, terminals top/bottom/left-right per spec."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    p = Ppd()
    # generator circle (lower)
    gr = 60
    gcy = 60
    p.circle(0, gcy, gr)
    p.marking(["G"], cy=gcy, bodyw=120, bodyh=120, shape="circle")
    # heat-source square (upper)
    hs_half = 50
    hcy = -90
    p.rect(-hs_half, hcy - hs_half, hs_half, hcy + hs_half)
    heat_glyph(p, name, 0, hcy, hs_half)
    if "non-ionizing radiation" in name:        # radiation arrows set the width
        for off in (-20, 20):
            arrow(p, -107, hcy - 18 + off, -52, hcy + 4 + off)
    # link between them
    p.line(0, hcy + hs_half, 0, gcy - gr)
    add_outlets(p, pins_of(rec))
    return p


def heat_glyph(p, name, cx, cy, half):
    """Inner mark for a heat source block."""
    if "radio-isotope" in name:
        p.text(cx, cy, "Ra", size=45, al=9)                   # radio-isotope
    elif "combustion" in name:
        p.polyline([(cx - 12, cy + 18), (cx, cy - 18), (cx + 12, cy + 18)])  # flame-ish
    # non-ionizing radiation arrows are added by the caller (they set the width)
    # general: no inner glyph


def draw_converter(rec):
    """Converter / rectifier / inverter / DC-AC substation: square (spec box)
    with a diagonal + AC(~)/DC(=) marks in the two triangles."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()

    if "bridge" in name or "full wave" in name:        # diamond bridge
        half = min(w, h) / 2.0
        p.polygon([(0, -half), (half, 0), (0, half), (-half, 0)])
        sine(p, 0, -half * 0.42, half=14, amp=7)       # ~ near top (AC)
        p.line(-14, half * 0.46, 14, half * 0.46)
        p.line(-10, half * 0.60, 10, half * 0.60)      # = near bottom (DC)
        add_outlets(p, pins)
        return p

    cx, cy = dl.pin_center(pins)
    l, t, r, b = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
    if "projected" in name:                             # broken outline = planned
        dashed_segment(p, l, t, r, t); dashed_segment(p, r, t, r, b)
        dashed_segment(p, r, b, l, b); dashed_segment(p, l, b, l, t)
    else:
        p.rect(l, t, r, b)
    p.line(l, b, r, t)                                  # diagonal (LL -> UR)
    qx = (r - l) * 0.27
    qy = (b - t) * 0.27

    def dc(ax, ay):
        p.line(ax - 14, ay - 5, ax + 14, ay - 5); p.line(ax - 14, ay + 5, ax + 14, ay + 5)

    def ac(ax, ay):
        sine(p, ax, ay, half=14, amp=7)

    ll = (cx - qx, cy + qy)     # lower-left triangle centre
    ur = (cx + qx, cy - qy)     # upper-right triangle centre
    if "dc-dc" in name:
        dc(*ll); dc(*ur)
    elif "rectifier" in name and "inverter" in name:
        ac(*ll); ac(*ur)
    elif "rectifier" in name or "dc to ac" in name:    # AC in -> DC out
        ac(*ll); dc(*ur)
    elif "inverter" in name:                           # DC in -> AC out
        dc(*ll); ac(*ur)
    elif "closed-loop controller" in name:
        p.text(cx, cy, "A", size=45, al=9)
    # converter general: bare square + diagonal
    rect_leads(p, pins, l, t, r, b)
    return p


def draw_heat_source(rec):
    """Heat source (general/combustion/radio-isotope): rectangle + inner glyph."""
    name = rec["name"].lower()
    return dl.body_rect([], pins_of(rec), rec["size"]["w"], rec["size"]["h"],
                        inner=lambda p, l, t, r, b: heat_glyph(
                            p, name, (l + r) / 2.0, (t + b) / 2.0, min(r - l, b - t) / 2.0))


def draw_station(rec):
    """Power/generating station: circle (broken if 'projected'); inner glyph by
    primary energy type; substation = inner diamond."""
    name = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    projected = "projected" in name
    p = Ppd()
    r = 60
    # combined electric+heat station is wider (asymmetric right pin)
    cx = 0
    if dashed := projected:
        dashed_circle(p, cx, 0, r)
    else:
        p.circle(cx, 0, r)

    if "substation" in name:
        p.polygon([(cx, -42), (42, 0), (cx, 42), (-42, 0)])   # inner diamond
    elif "nuclear" in name:
        p.dot(cx, 0, 5)
        p.ellipse(cx - 40, -16, cx + 40, 16, lw=2)            # electron orbit
    elif "solar" in name:
        for a in range(0, 360, 45):                            # sun rays
            rad = math.radians(a)
            p.line(cx + 22 * math.cos(rad), 22 * math.sin(rad),
                   cx + 40 * math.cos(rad), 40 * math.sin(rad), lw=2)
    elif "hydro" in name:
        p.polyline([(cx - 35, 10), (cx - 12, -10), (cx + 12, 10), (cx + 35, -10)], lw=2)
    elif "wind" in name:
        for a in (0, 120, 240):                                # three blades
            rad = math.radians(a - 90)
            p.line(cx, 0, cx + 38 * math.cos(rad), 38 * math.sin(rad), lw=2)
    elif "geothermic" in name:
        for dx in (-18, 0, 18):                                # rising heat lines
            p.polyline([(cx + dx, 30), (cx + dx + 8, 8), (cx + dx, -14)], lw=2)
    elif "thermoelectric" in name:
        p.line(cx - 30, 0, cx + 30, 0, lw=2); p.line(cx, -30, cx, 30, lw=2)
    elif "plasma" in name or "mhd" in name:
        p.text(cx, 0, "MHD", size=38, al=9)
    elif "combined" in name:
        p.line(cx - 30, -18, cx + 30, -18, lw=2)
        sine(p, cx, 18, half=28, amp=9)
    # general generating station: bare circle
    leads(p, pins, r)
    return p


# =========================================================================
# Dispatch
# =========================================================================

ENERGY_KW = ("watt-hour", "var-hour", "ampere-hour", "hour meter", "excess watt")
CONVERTER_KW = ("converter", "rectifier", "inverter", "dc-dc", "closed-loop")


def classify(rec):
    cat = rec["category"]
    name = rec["name"].lower()
    if "winding" in name:
        return draw_winding
    if "dc to ac" in name:                     # DC->AC converter substation
        return draw_converter
    if "/clocks" in cat:
        return draw_clock
    if "counting device" in cat or "pulse meter" in name or "counting device" in name:
        return draw_counter
    if "/generators" in cat or "/power supplies" in cat or name.startswith("generat"):
        return draw_generator
    if "power stations" in cat or "generating station" in name or "substation" in name:
        return draw_station
    if "heat source" in name:
        return draw_heat_source
    if any(k in name for k in CONVERTER_KW):
        return draw_converter
    if "/watt-hour meters" in cat or any(k in name for k in ENERGY_KW):
        return draw_energy
    return draw_meter


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
