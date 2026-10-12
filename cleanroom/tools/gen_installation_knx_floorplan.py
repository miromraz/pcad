#!/usr/bin/env python3
"""Generate the installation_knx_floorplan batch (EN 60617 part 11 installation,
US floor-plan and KNX-EIB building-automation symbols) as .ppd.

Clean-room: drawn from the EN/IEC 60617 standard + architectural / KNX-EIB
drafting convention + the spec facts only. Shared primitives: draw_lib.py;
batch glyphs: helpers_installation_knx_floorplan.py.

Run: python3 gen_installation_knx_floorplan.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd
import helpers_installation_knx_floorplan as h

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec",
                    "batch_installation_knx_floorplan.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def sz(rec):
    return rec["size"]["w"], rec["size"]["h"]


# --- one-line subscripts for floor-plan designations ----------------------
# Multi-token markings like ['S','2'] / ['CO','2'] must read as one baseline
# (S2, CO2, SF, SR, SWP), not two stacked lines. Merge a trailing qualifier
# (digit, or F/R/WP) onto an alphabetic base using Unicode sub/small-cap glyphs
# that the render font (Liberation Sans) carries. Alpha base only, so numeric
# ratio markings (e.g. pulse-meter '10','3','2') are never touched.
# letter qualifiers use modifier small-caps the render font (Liberation Sans)
# actually carries -- U+A730 small-cap F is tofu there, so use U+1DA0/U+1D3F.
_SUB_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUB_LETTER = {"F": "ᶠ", "R": "ᴿ", "WP": "ᵂᴾ"}


def _subscript(tok):
    if tok.isdigit():
        return tok.translate(_SUB_DIGITS)
    return _SUB_LETTER.get(tok)


def subify(marks):
    out = []
    for t in marks:
        s = _subscript(t)
        if out and s is not None and out[-1].isalpha() and len(out[-1]) <= 3:
            out[-1] += s
        else:
            out.append(t)
    return out


# =========================================================================
# connection boxes (EN 60617 11-12) -- a circle; junction box adds a node dot
# =========================================================================

def draw_box(rec):
    p = Ppd()
    r = min(sz(rec)) / 2.0
    p.circle(0, 0, r)
    if "junction" in rec["name"]:
        p.dot(0, 0, 4)
    dl.leads(p, pins_of(rec), r)
    return p


# =========================================================================
# US floor plan -- top level
# =========================================================================

def draw_bell(rec):
    p = Ppd()
    h.bell(p)
    dl.add_outlets(p, pins_of(rec))
    return p


def draw_camera(rec):
    p = Ppd()
    h.camera(p)
    dl.add_outlets(p, pins_of(rec))
    return p


def draw_fan(rec):
    p = Ppd()
    # blade tips reach r*0.92*cos45 ~ 0.65 r; size r from the spec box so the fan
    # fills (not overflows) its stated size instead of a hard-coded radius.
    r = min(sz(rec)) / 2.0 * 1.42
    h.ceiling_fan(p, r=r)
    p.marking(rec["markings"], bodyw=r * 0.3, bodyh=r * 0.3)
    return p


def draw_fire_ext(rec):
    p = Ppd()
    r = min(sz(rec)) / 2.0
    p.circle(0, 0, r)
    p.marking(rec["markings"], bodyw=2 * r, bodyh=2 * r, shape="circle")
    dl.leads(p, pins_of(rec), r)
    return p


def draw_keypad(rec):
    w, ht = sz(rec)
    p = Ppd()
    p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
    p.marking(rec["markings"], bodyw=w, bodyh=ht)
    dl.rect_leads(p, pins_of(rec), -w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
    return p


def draw_pushbutton_us(rec):
    p = Ppd()
    r = min(sz(rec)) / 2.0
    p.circle(0, 0, r)
    p.dot(0, 0, 5)
    dl.leads(p, pins_of(rec), r)
    return p


# =========================================================================
# US floor plan -- lights
# =========================================================================

def draw_light(rec):
    name = rec["name"].lower()
    w, ht = sz(rec)
    p = Ppd()
    pins = pins_of(rec)
    if name == "ceiling mounted light":
        h.circle_cross(p, min(w, ht) / 2.0)
    elif name == "recessed light fixture":
        h.circle_cross(p, 0, square=True, w=w, h=ht)
    elif "fluorescent light fixture" == name:
        p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        p.circle(0, 0, 14)
        h.cross(p, 0, 0, 14)
    elif name == "strip light fixture":
        p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        for x in (-60, -20, 20, 60):
            p.line(x, -ht / 2.0, x, ht / 2.0)
    elif name == "track mounted light fixture":
        p.line(-100, 0, 100, 0)
        for x in (-60, -20, 20, 60):
            p.line(x, -10, x, 10)
    elif name == "wall mounted fluorescent light fixture":
        p.line(-100, -33, 100, -33)             # wall
        p.rect(-100, 10, 100, 30)               # tube
        p.line(0, -33, 0, 10)                   # centre bracket
        p.line(-100, 10, -100, 0)               # stub to left pin
        p.line(100, 10, 100, 0)                 # stub to right pin
    elif name == "wall mounted light fixture":
        p.circle(0, -12, 20)
        h.cross(p, 0, -12, 18)
        p.line(-25, 33, 25, 33)                 # wall
        p.line(0, 8, 0, 33)                     # stem
    else:
        p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
    dl.add_outlets(p, pins)
    return p


# =========================================================================
# US floor plan -- outlets / receptacles
# =========================================================================

def draw_outlet(rec):
    name = rec["name"].lower()
    w, ht = sz(rec)
    p = Ppd()
    pins = pins_of(rec)
    if "tv outlet" in name or "usb outlet" in name:
        p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        p.marking(rec["markings"], bodyw=w, bodyh=ht)
        dl.rect_leads(p, pins, -w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        return p
    n = 1 if "simplex" in name else (4 if "quad" in name else 2)
    square = "infloor" in name
    h.receptacle(p, n, w, ht, square=square)
    dl.add_outlets(p, pins)
    return p


# =========================================================================
# US floor plan -- sensors / switches
# =========================================================================

def draw_us_sensor(rec):
    name = rec["name"].lower()
    w, ht = sz(rec)
    p = Ppd()
    pins = pins_of(rec)
    if "switch" in name or name in ("thermostat",):
        pass
    if "occupancy sensor" in name:
        p.ellipse(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        if "wall" in name:
            p.line(-w / 2.0, ht / 2.0, w / 2.0, ht / 2.0)   # wall mounting line
        p.marking(rec["markings"], bodyw=w, bodyh=ht)
    elif name == "thermostat":
        p.ellipse(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        p.marking(rec["markings"], bodyw=w, bodyh=ht)
    elif name == "daylight sensor":
        p.rect(-w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
        p.marking(rec["markings"], bodyw=w, bodyh=ht)
    elif name == "smoke detector":
        r = ht / 2.0
        p.circle(0, 0, r)
        p.marking(rec["markings"], bodyw=2 * r, bodyh=2 * r, shape="circle")
    else:
        # architectural switch: the 'S' designation (with subscript) only
        p.marking(rec["markings"], bodyw=w, bodyh=ht)
    if name == "daylight sensor":
        dl.rect_leads(p, pins, -w / 2.0, -ht / 2.0, w / 2.0, ht / 2.0)
    else:
        dl.add_outlets(p, pins)
    return p


# =========================================================================
# KNX-EIB -- rectangular bus devices
# =========================================================================

# name -> inner differentiator glyph for the un-marked boxes
KNX_INNER = {
    "actuator": "actuator",
    "analog output": "analog",
    "dimmer": "dimmer",
    "shutter actuator": "shutter_act",
    "interface": "interface",
    "connector": "connector",
    "choke": "choke",
    "bus access unit": "bus_access",
    "dimming sensor": "dimming",
    "push button": "pushbutton",
    "shutter switch": "shutter_sw",
    "binary sensor with {n} channels for ac": "binary_ac",
    "binary sensor with {n} channels for dc": "binary_dc",
}


def draw_knx(rec):
    name = rec["name"].lower()
    w, ht = sz(rec)
    pins = pins_of(rec)

    # oversized composites (aux AC feed extends a 180x144 body to 260x187)
    if name in ("actuator with ac feeding", "sensor with auxiliary voltage"):
        p = dl.body_rect(rec["markings"], pins, 180, 144)
        h.aux_supply(p)
        return p

    # IR radiation pair extends a 180x144 body to ~265 wide
    if name == "ir receiver":
        p = dl.body_rect(rec["markings"], pins, 180, 144)
        h.radiation(p, outward=False)
        return p
    if name == "ir transmitter":
        p = dl.body_rect(rec["markings"], pins, 180, 144)
        h.radiation(p, outward=True)
        return p

    if name == "power supply":
        p = dl.body_rect(rec["markings"], pins, w, ht)
        h.knx_inner(p, "psu", w, ht)
        return p
    if name == "power supply + choke":
        p = dl.body_rect(rec["markings"], pins, w, ht)
        h.knx_inner(p, "psu_choke", w, ht)
        return p

    p = dl.body_rect(rec["markings"], pins, w, ht)
    if not rec["markings"]:
        kind = KNX_INNER.get(name)
        if kind:
            h.knx_inner(p, kind, w, ht)
    return p


# =========================================================================
# Dispatch
# =========================================================================

def classify(rec):
    cat = rec["category"]
    name = rec["name"].lower()
    if cat == "installation/connection boxes":
        return draw_box
    if cat.startswith("installation/knx-eib"):
        return draw_knx
    if cat == "installation/us floor plan/lights":
        return draw_light
    if cat == "installation/us floor plan/outlets":
        return draw_outlet
    if cat == "installation/us floor plan/sensors":
        return draw_us_sensor
    if cat == "installation/us floor plan":
        if name == "bell":
            return draw_bell
        if "camera" in name:
            return draw_camera
        if name == "fan":
            return draw_fan
        if "fire extinguisher" in name:
            return draw_fire_ext
        if "key pad" in name:
            return draw_keypad
        if "push button" in name:
            return draw_pushbutton_us
    raise SystemExit(f"unclassified: {rec['id']}")


def main():
    recs = json.load(open(SPEC))
    n = 0
    for rec in recs:
        rec["markings"] = subify(rec["markings"])
        p = classify(rec)(rec)
        xml = p.document(rec["name"], rec["designation"],
                         rec["standard"], rec["id"])
        rel = dl.slug_path(rec["category"], rec["name"])
        out = os.path.join(LIBDIR, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(xml)
        n += 1
    print(f"wrote {n} .ppd files under {LIBDIR}")


if __name__ == "__main__":
    main()
