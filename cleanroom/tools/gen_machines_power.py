#!/usr/bin/env python3
"""Generate the machines_power batch (98 EN 60617 symbols) as .ppd files.

Clean-room: draws only from the EN/IEC 60617 standard + general drafting
knowledge + the spec facts (cleanroom/spec/batch_machines_power.json). Families:
outdoor-installation pictograms, line/wiring marks, transformers (form 1 = winding
loops, form 2 = circles), current & auto transformers, rotating machines (circle +
machine letter), motor starters. Reuses draw_lib.py + helpers_machines_power.py.

Run: python3 gen_machines_power.py
Check: python3 check_batch.py ../spec/batch_machines_power.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd, arrow, sine, add_outlets
from helpers_machines_power import (pick_r, winding_bumps_v, coil_h, sine_path)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_machines_power.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


# =========================================================================
# Rotating machines  (STYLE.md 5: circle with the machine letter inside)
# =========================================================================

def ac_markings(rec):
    """Spec letters + the EN 60617 AC qualifier '~' on the phase number for AC
    machines (e.g. 'M','3' -> 'M','3~').  DC machines keep their plain marking."""
    marks = list(rec["markings"])
    name = rec["name"].lower()
    # "shunt"/"compound" describe the excitation, not the machine type: a
    # synchronous machine stays AC even when shunt/compound excited, so it must
    # carry the AC/phase qualifier like the other synchronous machines (this is
    # why the shunt-excited synchronous converter showed a bare 'C 1').
    synchronous = "synchronous" in name
    dc = (("dc" in name or "shunt" in name or "compound" in name
           or "magneto" in name or "stepping" in name) and not synchronous)
    ac = (any(k in name for k in ("induction", "synchronous", "repulsion"))
          or "motor ac" in name or "series motor, 1 phase" in name
          or "series motor, 3 phase" in name or "replusion" in name)
    if ac and not dc:
        # trust the stated phase count over a stray phase digit in the marking
        phase = "3" if "3 phase" in name else ("1" if "1 phase" in name else None)
        if phase and any(t in ("1", "3", "6") for t in marks):
            marks = [phase if t in ("1", "3", "6") else t for t in marks]
        if any(t in ("1", "3", "6") for t in marks):
            marks = [t + "~" if t in ("1", "3", "6") else t for t in marks]
        elif "3 phase" in name:
            marks.append("3~")
        elif "1 phase" in name:
            marks.append("1~")
        else:
            marks.append("~")
    return marks


def draw_machine(rec):
    name = rec["name"].lower()
    if "choke" in name or "reactor" in name:
        return draw_choke(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    r = pick_r(pins, w, h, lo=40)
    p = Ppd()
    p.circle(0, 0, r)
    dl.leads(p, pins, r)
    # fill a deficient box dimension with a short shaft / terminal stub
    exx = max([r] + [abs(x) for x, _ in pins])
    exy = max([r] + [abs(y) for _, y in pins])
    if "hand-generator" in name or exx < w * 0.45:
        p.line(-w / 2.0, 0, -exx, 0)
        p.line(exx, 0, w / 2.0, 0)
    if exy < h * 0.45:
        p.line(0, -h / 2.0, 0, -exy)
        p.line(0, exy, 0, h / 2.0)
    p.marking(ac_markings(rec), bodyw=1.5 * r, bodyh=1.5 * r)
    return p


def _single_winding(p, w, h, pins, tap=False):
    """One EN 60617 winding (column of bumps) with the magnetic core drawn as a
    straight line beside it; top & bottom buses to the centre terminals. Used by
    choke/reactor and the auto-transformer form-1 family."""
    hw = w / 2.0
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    y0, y1 = ytop + 16, ybot - 16
    bulge = min(24, hw * 0.55)
    ax = hw - bulge                                   # bumps bulge right to +hw
    winding_bumps_v(p, ax, y0, y1, 4, bulge)
    p.line(-hw, y0, -hw, y1)                           # magnetic core line (left)
    p.line(-hw, y0, ax, y0)                            # top bus
    p.line(-hw, y1, ax, y1)                            # bottom bus
    if tap:
        p.line(hw, 0, hw + 6, 0)
    for (x, y) in pins:
        wy = y0 if y < 0 else y1
        p.line(x, wy, x, y)
        p.outlet(x, y)


def draw_choke(rec):
    """Choke / reactor (06-09-08): a winding beside a straight core line."""
    p = Ppd()
    _single_winding(p, rec["size"]["w"], rec["size"]["h"], pins_of(rec))
    return p


# =========================================================================
# Transformers
# =========================================================================

ADJ_KW = ("variable", "tap changer", "regulation", "induction regulator")


def _adjustable(name):
    return any(k in name for k in ADJ_KW)


def draw_transformer(rec):
    return draw_tf_form2(rec) if "form 2" in rec["name"].lower() else draw_tf_form1(rec)


def draw_tf_form1(rec, single=False):
    """Form 1 (detailed) transformer: EN 60617 winding representation - two
    windings as columns of semicircular loops facing each other, the core shown
    as parallel straight lines between them.  Terminals via top/bottom buses."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    pins = pins_of(rec)
    if single:
        p = Ppd()
        _single_winding(p, w, h, pins, tap=True)
        if _adjustable(name):
            arrow(p, -w * 0.4, h * 0.44, w * 0.4, -h * 0.44)
        return p
    p = Ppd()
    hw = w / 2.0
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    y0, y1 = ytop + 16, ybot - 16
    bulge = min(24, hw * 0.42)
    xoff = hw - bulge
    winding_bumps_v(p, -xoff, y0, y1, 4, -bulge)      # left winding, faces core
    winding_bumps_v(p, xoff, y0, y1, 4, bulge)        # right winding, faces core
    p.line(-4, y0, -4, y1)                            # core: two parallel lines
    p.line(4, y0, 4, y1)
    p.line(-xoff, y0, xoff, y0)                       # top & bottom buses
    p.line(-xoff, y1, xoff, y1)
    if "screen" in name:                             # electrostatic screen + earth
        p.line(-xoff, 0, xoff, 0)
        p.line(0, 0, 0, 16)
        p.line(-8, 16, 8, 16)
    for (x, y) in pins:
        if y <= y0 or y >= y1:                        # a terminal (above/below)
            p.line(x, y0 if y < 0 else y1, x, y)
        else:                                         # a side tap on a winding
            p.line(hw if x >= 0 else -hw, y, x, y)
        p.outlet(x, y)
    if _adjustable(name):
        arrow(p, -hw * 0.9, h * 0.44, hw * 0.9, -h * 0.44)
    p.marking(rec["markings"], cx=0, cy=0, bodyw=w * 0.4, bodyh=26)
    return p


def _columns(pins):
    xs = sorted(set(x for x, _ in pins))
    cols, last = [], None
    for x in xs:
        if last is None or x - last > 25:
            cols.append(x); last = x
    return cols


def draw_tf_form2(rec):
    """Form 2 transformer: windings drawn as circles.  Tall multi-row specs =
    three-phase columns of stacked circles; otherwise a horizontal row."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    ys = [y for _, y in pins]
    tall = (max(ys) - min(ys)) > 100
    if tall:
        cols = _columns(pins)
        colspan = (max(cols) - min(cols)) if len(cols) > 1 else 0
        r = int(max(10, min(55, (w - colspan) / 2.0)))
        cyU, cyL = -h * 0.17, h * 0.17
        for cx in cols:
            p.circle(cx, cyU, r)
            p.circle(cx, cyL, r)
        # star / delta connection buses along the two rows
        p.line(min(cols), cyU, max(cols), cyU)
        p.line(min(cols), cyL, max(cols), cyL)
        for (x, y) in pins:
            cy = cyU if y < 0 else cyL
            edge = cy - r if y < 0 else cy + r
            p.line(x, edge, x, y)
            p.outlet(x, y)
    else:
        cols = _columns(pins)
        ncirc = max(2, len(cols))
        r = min(20, int(w / 4))
        span = max(w / 2.0 - r, r)
        centers = [0.0] if ncirc == 1 else [-span + 2 * span * i / (ncirc - 1)
                                            for i in range(ncirc)]
        maxx = max(abs(x) for x, _ in pins) or span
        p.line(-maxx, 0, maxx, 0)                  # winding baseline
        for cx in centers:
            p.circle(cx, 0, r)
        for (x, y) in pins:
            if abs(y) > 2:
                p.line(x, 0, x, y)
            p.outlet(x, y)
        if _adjustable(name):
            arrow(p, -w * 0.4, h * 0.48, w * 0.4, -h * 0.48)
    p.marking(rec["markings"], cx=0, cy=0, bodyw=40, bodyh=24)
    return p


def draw_current_transformer(rec):
    """Current transformer: a core ring with the primary conductor passing
    straight through, secondary winding(s) led out to the side terminals."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    r = pick_r(pins, w, h, lo=10)
    p.circle(0, 0, r)
    ps = set(pins)
    # primary = a symmetric opposite pair (straight conductor through the core)
    prim = []
    for (x, y) in pins:
        if (x, y) != (0, 0) and (-x, -y) in ps:
            prim = [(x, y), (-x, -y)]
            break
    if prim:
        # draw the primary conductor spanning the full box along its axis
        if abs(prim[0][0]) >= abs(prim[0][1]):          # horizontal primary
            p.line(-w / 2.0, 0, w / 2.0, 0)
        else:                                           # vertical primary
            p.line(0, -h / 2.0, 0, h / 2.0)
    for (x, y) in pins:
        if (x, y) not in prim:
            d = math.hypot(x, y) or 1.0
            p.line(x * r / d, y * r / d, x, y)     # secondary lead from the ring
        p.outlet(x, y)
    p.marking(rec["markings"], cx=0, cy=0, bodyw=1.4 * r, bodyh=1.4 * r)
    return p


def draw_auto_transformer(rec):
    if "form 2" in rec["name"].lower():
        return draw_auto_form2(rec)
    return draw_tf_form1(rec, single=True)          # single-winding bumps + core


def draw_auto_form2(rec):
    """Auto-transformer form 2: flat tapped winding (a horizontal coil) or a
    three-phase columnar set for the wide 7-terminal variant."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    ys = [y for _, y in pins]
    if (max(ys) - min(ys)) > 80:
        return draw_tf_form2(rec)
    p = Ppd()
    yax = min(ys)                                    # winding hangs below the pins
    coil_h(p, -w * 0.45, w * 0.45, yax, 4, min(22, h * 0.95))
    for (x, y) in pins:
        p.line(x, yax, x, y)
        p.outlet(x, y)
    if "regulation" in rec["name"].lower():
        arrow(p, 0, yax + 6, 0, yax + h)             # vertical regulating arrow
    return p


# =========================================================================
# Starters  (square control box, four terminals on the edges)
# =========================================================================

def draw_starter(rec):
    w, h = rec["size"]["w"], rec["size"]["h"]
    name = rec["name"].lower()
    pins = pins_of(rec)
    p = Ppd()
    half = 40
    p.rect(-half, -half, half, half)
    if "star-delta" in name:
        p.polyline([(-20, 12), (-12, 4), (-12, -8)])
        p.polyline([(-12, 4), (-4, 12)])
        p.polygon([(6, -8), (22, -8), (14, 12)])
    elif "step" in name:
        p.polyline([(-20, 12), (-7, 12), (-7, 0), (6, 0), (6, -12), (20, -12)])
    elif "reversing" in name:
        arrow(p, -16, -12, 16, -12)
        arrow(p, 16, 12, -16, 12)
    elif "auto-transformer" in name:
        coil_h(p, -20, 20, 2, 3, 14)
    elif "thyristor" in name:
        p.polygon([(-12, -10), (12, -10), (0, 8)])
        p.line(-14, 8, 14, 8)
    elif "regulator" in name:
        arrow(p, -18, 16, 18, -16)
    if h > 90:                                       # starter-regulator: taller
        ye = h / 2.0
        arrow(p, -28, ye, 28, -ye)
    add_outlets(p, pins)
    return p


# =========================================================================
# Outdoor installation + line/wiring pictograms  (mostly 0 pins)
# =========================================================================

def _wave(p, x0, x1, y, amp, humps=2):
    sine_path(p, x0, x1, y, y, amp, humps=humps)


def od(rec):                                         # dispatch by name
    name = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    hw, hh = w / 2.0, h / 2.0

    if "amplifying point" in name:                   # enclosure + amplifier
        p.rect(-hw, -hh, hw, hh)
        p.polygon([(-30, -30), (-30, 30), (35, 0)])
    elif "overground weather-proof enclosure" in name:
        p.rect(-hw, -hh, hw, hh)
        p.line(-hw, -hh + 16, hw, -hh + 16)
    elif "anti-creepage" in name:
        p.line(-hw, 0, hw, 0)
        for x in (-8, 8):
            p.polyline([(x - 7, 14), (x, -14), (x + 7, 14)])
    elif "cable sealing end" in name:
        p.polygon([(-18, 30), (18, 30), (0, -30)])
        p.line(0, 30, 0, 40)
        p.line(0, -30, 0, -40)
    elif "combined protective and neutral" in name:  # PEN conductor
        p.line(-17, 13, 17, 13)
        p.line(-17, -8, 17, -8)
        for x in (-12, 0, 12):
            p.line(x, -3, x - 6, -18)
    elif "cross connection point" in name:
        r = min(hw, hh)
        p.circle(0, 0, r)
        for a in range(0, 360, 30):
            rad = math.radians(a)
            p.line(r * 0.5 * math.cos(rad), r * 0.5 * math.sin(rad),
                   r * math.cos(rad), r * math.sin(rad), lw=2)
        add_outlets(p, pins)
        return p
    elif "end of conductor" in name:
        (px, py) = pins[0]
        p.line(px, py, 30, py)
        p.line(30, -20, 30, 20)                      # open-end bar
        if "insulated" in name:
            p.line(36, -16, 36, 16)                  # second bar = insulated
        p.outlet(px, py)
        return p
    elif "flexible connection" in name:
        (ax, _), (bx, _) = pins[0], pins[-1]
        sine_path(p, min(ax, bx), max(ax, bx), 0, 0, hh, humps=2)
        add_outlets(p, pins)
        return p
    elif "junction requiring" in name:
        p.polygon([(0, -hh + 2), (hw - 2, 0), (0, hh - 2), (-hw + 2, 0)])
        p.dot(0, 0, 6)
    elif "line concentrator" in name:
        p.polygon([(-hw, -hh + 2), (-hw, hh - 2), (hw, 0)])
    elif "anode" in name:                            # protective / Mg anode
        (px, py) = pins[0]
        p.line(px, py, 0, 0)
        p.rect(-hw, 0, hw, hh - 6)
        if rec["markings"]:
            p.marking(rec["markings"], cx=0, cy=(hh - 6) / 2.0, bodyw=w * 0.8, bodyh=hh)
        p.outlet(px, py)
        return p
    elif "neutral conductor" in name:
        p.circle(0, 0, min(hw, hh) - 1)
    elif "pressure-tight bulkhead" in name:
        p.line(0, -hh, 0, hh)
        for y in (-hh * 0.55, 0, hh * 0.55):
            p.line(-hw, y, hw, y)
            p.rect(-7, y - 7, 7, y + 7)
    elif "protective conductor" in name:
        p.line(-hw + 1, 8, hw - 1, 8)
        for x in (-8, 0, 8):
            p.line(x - 4, -2, x + 4, -10)
    elif "straight-through joint box" in name:
        p.line(-hw, 0, hw, 0)
        p.ellipse(-hw * 0.6, -hh * 0.92, hw * 0.6, hh * 0.92)
    elif "twisted connection" in name:
        p.polyline([(-hw, -hh), (-12, -hh), (12, hh), (hw, hh)])
        p.polyline([(-hw, hh), (-12, hh), (12, -hh), (hw, -hh)])
    elif "wiring under the plaster" in name:
        p.line(-hw, 0, hw, 0)
        for x in (-16, 0, 16):
            p.line(x - 5, 12, x + 5, -12)

    # ---- line / wiring family ----
    elif "ac power feeding" in name:
        p.circle(0, 0, 14)
        sine(p, 0, 0, 9, 5)
        p.line(0, -hh, 0, -14); p.line(0, 14, 0, hh)
        p.line(-hw + 1, 0, -14, 0); p.line(14, 0, hw - 1, 0)
    elif "dc power feeding" in name:
        p.circle(0, 0, 14)
        p.line(-8, -4, 8, -4); p.line(-8, 4, 8, 4)
        p.line(-hw + 1, 0, -14, 0); p.line(14, 0, hw - 1, 0)
    elif "access chamber" in name:
        p.line(-hw, 0, hw, 0)
        p.ellipse(-hw * 0.72, -hh * 0.95, hw * 0.72, hh * 0.95)
    elif "burried joint" in name or "buried joint" in name:
        p.line(-hw, -6, hw, -6)
        p.dot(0, -6, 6)
        for x in (-16, 0, 16):
            p.line(x - 6, 8, x + 6, 8)
    elif "block by-pass" in name:
        p.line(-hw, 0, -8, 0); p.line(8, 0, hw, 0)   # line with a gap (block)
        p.polyline([(-8, 0), (-8, -hh + 2), (8, -hh + 2), (8, 0)])
        p.polyline([(-8, 0), (-8, hh - 2), (8, hh - 2), (8, 0)])
    elif "gas or oil block" in name:                 # 0-width: pure vertical
        p.line(0, -hh, 0, -6)
        p.line(0, 6, 0, hh)
    elif "stop valve" in name:
        p.line(-hw, 0, -14, 0); p.line(14, 0, hw, 0)
        p.polygon([(-14, -hh + 2), (-14, hh - 2), (0, 0)])
        p.polygon([(14, -hh + 2), (14, hh - 2), (0, 0)])
    elif "overhead line" in name:
        p.line(-hw, hh - 8, hw, hh - 8)
        p.circle(0, -6, 18)
    elif "submarine line" in name:
        sine_path(p, -hw, hw, 0, 0, hh + 1, humps=2)
    elif "underground line" in name:
        p.line(-hw, -6, hw, -6)
        p.line(-hw * 0.6, 6, hw * 0.6, 6)
    elif "going downwards" in name:
        p.circle(0, 0, hw - 2)
        arrow(p, 0, -(hh - 6), 0, hh)
    elif "going upwards" in name:
        p.circle(0, 0, hw - 2)
        arrow(p, 0, (hh - 6), 0, -hh)
    elif "passing through vertically" in name:
        p.circle(0, 0, min(hw, hh))
        p.line(0, -hh, 0, hh)
    else:
        p.rect(-hw, -hh, hw, hh)                      # fallback outline
    add_outlets(p, pins)
    return p


# =========================================================================
# Dispatch
# =========================================================================

def classify(rec):
    cat = rec["category"]
    if "current transformer" in cat:
        return draw_current_transformer
    if "auto-transformer" in cat:
        return draw_auto_transformer
    if "/transformers" in cat:
        return draw_transformer
    if "/starters" in cat:
        return draw_starter
    if "/motors" in cat or cat == "power/machines":
        return draw_machine
    return od                                         # power/outdoor + /wiring


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
