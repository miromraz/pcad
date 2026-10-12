#!/usr/bin/env python3
"""Generate the semiconductors_transmission batch (EN 60617) as .ppd files.

Clean-room: drawn from EN/IEC 60617 knowledge + the spec facts only. Families:
  transmission two/four-port networks (filters, attenuators, equalizers,
  correctors, limiters, generators, SAW, modulator), amplifier triangles,
  line-amplification route marks, pulse-modulation pictograms, and discrete
  semiconductors (diodes, JFET/UJT/MOSFET/IGBT/PNIP transistors, diac).

Run: python3 gen_semiconductors_transmission.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd, arrow, add_outlets, pin_center
import helpers_semiconductors_transmission as H

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_semiconductors_transmission.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


# --- transmission network boxes (rect + inner graphic + markings) ----------

def box(rec, inner=None, variable=False):
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = dl.body_rect(rec["markings"], pins_of(rec), w, h, inner=inner)
    if variable:                                   # general variability arrow
        cx, cy = pin_center(pins_of(rec))
        arrow(p, cx - w * 0.5, cy + h * 0.5, cx + w * 0.5, cy - h * 0.5)
    return p


# --- amplifiers (triangle pointing in the signal direction) ----------------

def amplifier(rec):
    name = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    if "both-way" in name or "both way" in name:   # bow-tie (bidirectional)
        hh = h / 2.0
        xr = w / 2.0
        p.polygon([(-xr, -hh), (-xr, hh), (0, 0)])
        p.polygon([(xr, -hh), (xr, hh), (0, 0)])
        add_outlets(p, pins)
        return p
    if "by-pass" in name:
        p.polygon([(-40, -67), (-40, 67), (40, 0)])        # amplifier
        p.line(-80, 0, -40, 0)                             # input lead
        p.line(40, 0, 60, 0)                               # output lead
        p.polyline([(-80, 0), (-80, -67), (60, -67), (60, 0)])  # by-pass path
        add_outlets(p, pins)
        return p
    # plain / adjustable repeater triangle, apex at the right pin
    xl, xr = -w / 2.0, w / 2.0
    hh = min(h / 2.0, w / 2.0)
    if "adjustab" in name:
        hh = h / 2.0 - 10
    px = max(x for x, _ in pins)
    nx = min(x for x, _ in pins)
    p.polygon([(nx, -hh), (nx, hh), (px, 0)])
    if "adjustab" in name:
        arrow(p, -w / 2.0, h / 2.0, w / 2.0, -h / 2.0)
    add_outlets(p, pins)
    return p


# --- line-amplification route marks (no pins) ------------------------------

def line_amp(rec):
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    xr, hh = w / 2.0, h / 2.0
    p.line(-xr, 0, xr, 0)                           # transmission line
    if "both" in rec["name"].lower():
        p.polygon([(-xr * 0.5, -hh), (-xr * 0.5, hh), (0, 0)])
        p.polygon([(xr * 0.5, -hh), (xr * 0.5, hh), (0, 0)])
    else:
        p.polygon([(-hh, -hh), (-hh, hh), (hh, 0)])
    return p


# --- pulse-modulation pictograms (no pins; geometry fills the box) ---------

def pulse_mod(rec):
    name = rec["name"].lower()
    w, h = rec["size"]["w"], rec["size"]["h"]
    xr, base, top = w / 2.0, h / 2.0, -h / 2.0
    p = Ppd()
    p.line(-xr, base, xr, base)                     # baseline

    def bar(x, y0, y1):
        p.line(x, y0, x, y1)

    if "amplitude" in name:                         # varying height bars
        for x, f in ((-xr * 0.7, 0.4), (-xr * 0.25, 1.0),
                     (xr * 0.25, 0.65), (xr * 0.7, 0.9)):
            bar(x, base, base + (top - base) * f)
    elif "duration" in name:                        # varying width pulses
        for x0, x1 in ((-xr * 0.85, -xr * 0.55), (-xr * 0.25, xr * 0.2),
                       (xr * 0.5, xr * 0.85)):
            p.polyline([(x0, base), (x0, top), (x1, top), (x1, base)])
    elif "position" in name or "phase" in name:     # narrow shifted pulses
        for x in (-xr * 0.6, -xr * 0.05, xr * 0.55):
            bar(x, base, top)
    elif "interval" in name:                        # varying gaps (wide)
        for x in (-xr * 0.85, -xr * 0.45, xr * 0.05, xr * 0.75):
            bar(x, base, top)
    elif "frequency" in name:                       # sine over pulse train
        from draw_lib import sine
        sine(p, 0, top + h * 0.22, half=xr * 0.9, amp=h * 0.16)
        for x in (-xr * 0.8, -xr * 0.4, 0, xr * 0.3, xr * 0.55, xr * 0.8):
            bar(x, base, 0)
    else:                                           # pulse-code: two-level train
        lv = [0, 1, 0, 1, 1, 0, 1]
        n = len(lv)
        xs = [-xr + 2 * xr * i / n for i in range(n + 1)]
        pts = []
        for i in range(n):
            y = top if lv[i] else base - (base - top) * 0.45
            pts.append((xs[i], y))
            pts.append((xs[i + 1], y))
        p.polyline(pts)
        if rec["markings"]:
            p.marking(rec["markings"], cx=0, cy=(base + top) / 2, bodyw=w, bodyh=h)
    return p


# --- semiconductors --------------------------------------------------------

def semiconductor(rec):
    name = rec["name"].lower()
    cat = rec["category"]
    pins = pins_of(rec)
    if "/diodes" in cat:
        if name == "led":
            return H.led(pins)
        if "zener" in name:
            return H.zener(pins)
        if "temperature" in name:
            return H.temp_diode(pins)
        if "backward" in name:
            return H.backward_diode(pins)
        if "breakdown" in name and "bidirectional" in name:
            return H.breakdown_bidir(pins)
        if "bidirectional" in name:
            return H.bidirectional_diode(pins)
        return H.diode(pins)
    if "diac" in name:
        return H.diac(pins)
    if "/igbt" in cat:
        return H.igbt(pins, broken="enhancement" in name, ntype="with n" in name)
    if "mosfet" in cat:
        return H.mosfet(pins, broken="enhancement" in name,
                        ntype=name.rstrip().endswith(" n") or "with n" in name,
                        gates=2 if "two gates" in name else 1)
    if "unijunction" in name:
        return H.unijunction(pins, ntype="with n" in name)
    if "j fet" in name:
        return H.jfet(pins, ntype=name.rstrip().endswith(" n"))
    if "pnin" in name or "pnip" in name:
        return H.pnip(pins, ntype=name.rstrip().endswith("n"))
    return dl.body_rect(rec["markings"], pins, rec["size"]["w"], rec["size"]["h"])


# --- dispatch --------------------------------------------------------------

def draw(rec):
    cat = rec["category"]
    name = rec["name"].lower()
    rid = rec["id"]

    if cat.startswith("electronics/semiconductors"):
        return semiconductor(rec)

    # ---- transmission families ----
    if "/amplifiers" in cat:
        return amplifier(rec)
    if "/pulse modulation" in cat:
        return pulse_mod(rec)
    if "line with" in name and "amplification" in name:
        return line_amp(rec)

    # filters
    if name == "filter":
        return box(rec, inner=H.filter_curve("gen"))
    if "low-pass" in name:
        return box(rec, inner=H.filter_curve("low"))
    if "high-pass" in name:
        return box(rec, inner=H.filter_curve("high"))
    if "band-pass" in name:
        return box(rec, inner=H.filter_curve("band"))
    if "band-stop" in name:
        return box(rec, inner=H.filter_curve("stop"))

    # limiters / clippers
    if "amplitude limiter" in name:
        return box(rec, inner=H.transfer_curve("both"))
    if "positive peak" in name:
        return box(rec, inner=H.transfer_curve("pos"))
    if "negative peak" in name:
        return box(rec, inner=H.transfer_curve("neg"))
    if "base limiter" in name:
        return box(rec, inner=H.transfer_curve("base"),
                   variable="preset" in name)
    if name == "clipper":
        return box(rec, inner=H.transfer_curve("clip"))

    # companders / emphasis
    if "compressor" in name:
        return box(rec, inner=H.compander_curve("compress"))
    if "expander" in name:
        return box(rec, inner=H.compander_curve("expand"))
    if "pre-emphasis" in name:
        return box(rec, inner=H.compander_curve("pre"))
    if "de-emphasis" in name:
        return box(rec, inner=H.compander_curve("de"))

    # attenuators / equalizers / correctors (marking-bearing boxes)
    if "attenuator" in name:
        return box(rec, variable="variable" in name)
    if "equalizer" in name or "corrector" in name:
        inner = None
        if name == "distortion corrector":
            inner = H.compander_curve("pre")
        return box(rec, inner=inner)
    if "phase-changing network" in name:
        return box(rec)

    # generators
    if "/generators" in cat:
        wave = ("saw" if "saw" in name else "sine" if "sine" in name else "pulse")
        return H.generator_box(pins_of(rec), rec["size"]["w"], rec["size"]["h"], wave)
    if "pulse regenerator" in name:
        return box(rec, inner=H.inner_square(34, 30, periods=2))

    # SAW devices
    if "surface acoustic wave" in name:
        sets = 2 if ("filter" in name or "delay" in name) else 1
        return box(rec, inner=H.saw_idt(sets))

    # misc networks
    if "modulator" in name:
        return box(rec, inner=H.inner_modulator)
    if "artificial line" in name:
        return box(rec, inner=H.inner_artificial_line)
    if "chopping" in name:
        return box(rec, inner=H.inner_square(34, 30, periods=3))
    if "mixing network" in name:
        return box(rec)
    if "balancing network" in name:
        return box(rec, inner=H.inner_balance)
    if "hybrid transformer" in name:
        p = Ppd()
        p.circle(0, 0, 60)
        H.inner_hybrid(p, 0, 0, 60)
        from draw_lib import leads
        leads(p, pins_of(rec), 60)
        return p

    return box(rec)


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
