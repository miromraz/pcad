#!/usr/bin/env python3
"""Generate the installation_house batch (EN/IEC 60617-11 house wiring, 73 syms).

Clean-room: drawn from EN 60617 part-11 installation-plan conventions + the spec
facts only. Families:
  sockets        (11-13 / 211-07) -- half-disc socket outlets + variants
  lightings      (11-15 / 211-06) -- luminaires, emergency, projectors
  switches       (11-14)          -- installation switches (open make-contact)
  switches/appl. (211-07)         -- automatic switches, breakers, contactor
  other/kitchen  (211-10, 11-16)  -- appliance / apparatus blocks

Shared primitives: draw_lib.py; batch glyphs: helpers_installation_house.py.
Run: python3 gen_installation_house.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd
import helpers_installation_house as h

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_installation_house.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def code(rec):
    s = rec["standard"]
    return s.split(":", 1)[1].strip() if ":" in s else s


# =========================================================================
# Sockets
# =========================================================================
def draw_socket(rec):
    name = rec["name"].lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    px, py = pins[0]
    p = Ppd()
    r = 15
    up = py < 0

    if "antenna" in name:
        # antenna / coaxial-antenna outlet: socket + wide aerial(s)
        cy0, tip = h.socket(p, px, py, r, H=16)
        dy = -1 if py > 0 else 1                    # away from the pin
        masts = (-W / 4.0, W / 4.0) if "coax" in name else (px,)
        spread = (W / 2.0 - abs(masts[0])) if len(masts) > 1 else W / 2.0
        for mx in masts:
            top = tip + dy * 16
            p.line(mx, tip, mx, top)               # mast
            p.line(mx, top, mx - spread, top + dy * 6)   # wide strokes
            p.line(mx, top, mx + spread, top + dy * 6)
        for xy in pins:
            p.outlet(*xy)
        return p

    # body height for the half-disc (socket sits near the pin)
    bodyH = min(H, 35)
    cy0, tip = h.socket(p, px, py, r, H=bodyH)

    if "combined protective" in name or "4p" in name:
        # 3-phase 4-pole: earth bar + contact ticks, tall body
        h.earth_bar(p, px, cy0, W / 2.0 + 2)
        for i, dx in enumerate((-9, -3, 3, 9)):    # four contact ticks
            p.line(dx, cy0 + 2, dx, tip - 2)
        # extend downward to reach the tall box
        foot = py + (H if up else -H)
        p.line(px, tip, px, foot)
        p.line(px - 8, foot, px + 8, foot)
    elif "211-07-26" in rec["standard"]:           # non-interchangeable: keyed notch
        p.line(px - 5, (cy0 + tip) / 2.0, px + 5, (cy0 + tip) / 2.0)
        p.line(px, cy0, px, tip)
    elif "protective contact" in name:
        h.earth_bar(p, px, cy0, W / 2.0)
    elif "shutter" in name:
        h.earth_bar(p, px, cy0, W / 2.0)            # face plate
        p.line(px - 6, (cy0 + tip) / 2.0, px + 6, (cy0 + tip) / 2.0)   # shutter
    elif "telecommunications" in name:
        p.polygon([(px, tip), (px - 8, cy0 + 4), (px + 8, cy0 + 4)], fill=True)
    elif "interlocked switch" in name or "single-pole switch" in name:
        # socket (left) + an open switch (right) spanning the box
        sx = W / 2.0 - 6
        sy = cy0
        p.line(px + r, sy, sx - 2, sy)              # link socket -> switch
        p.line(-W / 2.0 + 2, sy, px - r, sy)        # grow left
        p.dot(sx - 2, sy, 4)                        # switch pivot
        p.line(sx - 2, sy, sx - 20, -H / 2.0 + 3)   # open blade (up, fills H)
        p.line(px, tip, px, H / 2.0 - 3)            # conductor down (fills H)
        if "interlocked" in name:
            p.line(sx - 13, sy - 10, sx - 13, sy + 8)   # interlock bar
    elif "isolating transformer" in name:
        # socket + isolating (2-winding) transformer below
        tcy = py + (H - 14 if up else -(H - 14))
        p.circle(px, tcy - 5, 7)
        p.circle(px, tcy + 5, 7)
        p.line(px, tip, px, tcy - 12)
    for xy in pins:
        p.outlet(*xy)
    return p


# =========================================================================
# Lightings
# =========================================================================
def draw_lighting(rec):
    name = rec["name"].lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()

    if name == "luminaire":                         # fluorescent batten
        p.rect(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
        p.line(-W / 2.0 + 6, 0, W / 2.0 - 6, 0)     # tube centre line
        for xy in pins:
            p.outlet(*xy)
        return p

    if "separate circuits" in name:                 # two-tube luminaire
        p.rect(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
        p.line(0, -H / 2.0, 0, H / 2.0)             # circuit divider
        for xy in pins:
            d = math.hypot(*xy)
            if d > max(W, H) / 2.0 - 1:
                pass
            p.outlet(*xy)
        return p

    if "flood" in name or "spot" in name or "projector" in name \
            or "headlight" in name:
        # directional luminaire: filled lamp + reflector bar + two beam rays
        lx = -0.44 * W
        r = 8
        p.dot(lx, 0, r)
        p.line(lx - 3, -r * 1.5, lx - 3, r * 1.5)   # reflector bar
        p.line(lx + r, 0, 0.46 * W, -0.44 * H)       # two beam rays (fill box)
        p.line(lx + r, 0, 0.46 * W, 0.44 * H)
        if "flood" in name:                          # wide-beam outer arc
            h.arc_poly(p, lx, 0, 0.5 * W, -40, 40)
        elif "spot" in name:                         # concentrated inner rays
            p.line(lx + r, 0, 0.42 * W, -0.22 * H)
            p.line(lx + r, 0, 0.42 * W, 0.22 * H)
        if "motion sensor" in name:                 # sensor arcs
            h.arc_poly(p, 0.30 * W, -0.30 * H, 8, -60, 60)
        for xy in pins:
            p.outlet(*xy)
        return p

    if "gas discharge" in name:
        r = min(W, H) / 2.0 - 6
        h.lamp(p, 0, 0, r)
        p.line(-W / 2.0 + 2, -8, -W / 2.0 + 2, 8)   # electrode bars
        p.line(W / 2.0 - 2, -8, W / 2.0 - 2, 8)
        for xy in pins:
            p.outlet(*xy)
        return p

    if "lamp with switch" in name:
        r = H / 2.0 - 2
        h.lamp(p, -W / 4.0, 0, r)
        p.line(-W / 4.0 + r, 0, W / 2.0 - 10, 0)    # link to switch
        p.dot(W / 2.0 - 10, 0, 4)
        p.line(W / 2.0 - 10, 0, W / 2.0 - 2, -H / 2.0 + 2)   # open blade (fills H)
        for xy in pins:
            p.outlet(*xy)
        return p

    if "emergency" in name:
        if "led" in name:                            # housed LED module
            p.rect(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
            h.emergency_lamp(p, 0, 0, min(W, H) / 2.0 - 7)
        else:
            h.emergency_lamp(p, 0, 0, min(W, H) / 2.0 - 2)
        for xy in pins:
            p.outlet(*xy)
        return p

    # generic luminaire / headlight fallback: lamp circle
    r = min(W, H) / 2.0 - 2
    h.lamp(p, 0, 0, r)
    for xy in pins:
        p.outlet(*xy)
    return p


# =========================================================================
# Installation switches  (big open make-contact fills the box)
# =========================================================================
def _switch_body(p, W, H, a=0.46):
    """Big diagonal open make-contact through the origin node: fixed contact to
    the lower-left, open blade to the upper-right. Returns the pivot (origin)."""
    fx, fy = -a * W, a * H
    bx, by = a * W, -a * H
    p.line(fx, fy, 0, 0)                            # fixed contact -> node
    p.dot(0, 0, 4)                                  # pivot node
    p.line(0, 0, bx * 0.82, by * 0.82)             # open blade
    p.line(bx, by, bx * 0.80, by * 0.80)           # far terminal stub
    return 0.0, 0.0


def _pin_stubs(p, pins, px=0.0, py=0.0):
    """Join every connection point to the central node."""
    for (x, y) in pins:
        if math.hypot(x - px, y - py) > 2:
            p.line(x, y, px, py)
        p.outlet(x, y)


def mod_lamp(p, W, H):
    h.lamp(p, -0.22 * W, -0.22 * H, min(W, H) * 0.12)


def draw_inst_switch(rec):
    name = rec["name"].lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    h.sw_body(p, pins)                               # circle body + outlets (+leads)

    if "intermediate" in name:                       # crossed form: an X of blades
        p.line(-W / 2.0, H / 2.0, W / 2.0, -H / 2.0)
        p.line(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
        return p
    if "two-way" in name:                            # changeover: two throws (a V)
        p.line(0, H / 2.0, 0, h.SW_R)                # common conductor (bottom)
        p.line(0, h.SW_R, -W / 2.0, -H / 2.0)        # throw to the upper-left
        p.line(0, h.SW_R, W / 2.0, -H / 2.0)         # throw to the upper-right
        return p
    if "multiposition" in name:                      # oblique blade + fan of positions
        h.sw_diag(p, W, H, ticks=1)
        for ex in (-0.40 * W, -0.12 * W, 0.16 * W):
            p.dot(ex, -H / 2.0 + 4, 3)
        return p
    if "twilight" in name:                           # switch + light-in arrows
        h.sw_diag(p, W, H, ticks=1)
        dl.arrow(p, -0.42 * W, 0.0, -0.16 * W, -0.28 * H)
        dl.arrow(p, -0.24 * W, 0.08 * H, 0.02 * W, -0.20 * H)
        return p

    ticks = 2 if "two pole" in name else 1
    h.sw_diag(p, W, H, ticks=ticks)
    if "pilot light" in name:
        h.sw_lamp(p, W, H)
    elif "key-operated" in name:
        h.sw_key(p, W, H)
    elif "pull-cord" in name or "pull cord" in name:
        h.sw_pull(p, W, H)
    if rec["markings"]:                              # period-limiting time 't'
        p.marking(rec["markings"], cx=-0.28 * W, cy=0.28 * H, bodyw=20, bodyh=20)
    return p


# =========================================================================
# Switches / appliances (automatic switches, breakers, contactor)
# =========================================================================
def _oper_element(p, W, H, kind):
    """Operating element below the contact, linked to the pivot."""
    ex, ey = 0.0, 0.40 * H
    p.line(0.0, 0.10 * H, ex, ey - 8)               # mech link (dashed-ish)
    if kind == "float":
        p.circle(ex, ey, 7)
    elif kind == "pressure":
        h.arc_poly(p, ex, ey, 9, 180, 360)
        p.line(ex - 9, ey, ex + 9, ey)
    elif kind == "centrifugal":
        p.circle(ex, ey, 7)
        p.dot(ex - 5, ey, 3)
        p.dot(ex + 5, ey, 3)
    elif kind == "remote":
        p.rect(ex - 10, ey - 6, ex + 10, ey + 6)
    elif kind == "thermostat":
        p.polyline([(ex - 9, ey + 4), (ex - 3, ey - 4),
                    (ex + 3, ey + 4), (ex + 9, ey - 4)])    # bimetal zig


OPER = {"Centrifugal switch": "centrifugal", "Float switch": "float",
        "pressure switch": "pressure", "thermostat 1P": "thermostat",
        "remotely controlled switch or servo-contact": "remote"}


def draw_appl_switch(rec):
    name = rec["name"]
    low = name.lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)

    if "circuit breaker" in low:
        return draw_breaker(rec)
    if "contactor" in low:
        p = Ppd()
        px, py = _switch_body(p, W, H)
        h.arc_poly(p, (px + 0.46 * W * 0.82) / 2.0, (py - 0.46 * H * 0.82) / 2.0,
                   9, 180, 360)                     # contactor cup
        _pin_stubs(p, pins, px, py)
        return p
    if "indicator light" in low:
        p = Ppd()
        px, py = _switch_body(p, W, H)
        mod_lamp(p, W, H)
        if "3p" in low:
            p.line(px + 6, py - 6, 0.46 * W * 0.82 + 6, -0.46 * H * 0.82 - 6)
        _pin_stubs(p, pins, px, py)
        return p
    if "push-button control" in low:
        return draw_pushbutton_control(rec)

    kind = OPER.get(name)
    p = Ppd()
    px, py = _switch_body(p, W, H)
    if kind:
        _oper_element(p, W, H, kind)
    _pin_stubs(p, pins, px, py)
    return p


def draw_breaker(rec):
    low = rec["name"].lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    poles = 3 if "3p" in low else 1
    px, py = _switch_body(p, W, H)
    # breaker cross (×) at the moving-contact tip
    tx, ty = 0.46 * W * 0.82, -0.46 * H * 0.82
    p.line(tx - 7, ty - 7, tx + 7, ty + 7)
    p.line(tx - 7, ty + 7, tx + 7, ty - 7)
    if poles == 3:                                  # two more ganged blades
        for off in (-0.16 * H, 0.16 * H):
            p.line(px, py + off, tx * 0.9, ty * 0.9 + off)
        p.polyline([(px, py), (px, py + 0.16 * H)])         # gang link (dashed-ish)
    _pin_stubs(p, pins, px, py)
    return p


def draw_pushbutton_control(rec):
    """Push-button control with two buttons (+ indicator lights)."""
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    lamps = "indicator light" in rec["name"].lower() or "211-07-48" in rec["standard"]
    p = Ppd()
    p.rect(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
    # two push-buttons (small circles) side by side
    p.circle(-W * 0.18, 0, 8)
    p.circle(W * 0.18, 0, 8)
    p.line(-W * 0.18, -8, -W * 0.18, -H / 2.0)      # plungers
    p.line(W * 0.18, -8, W * 0.18, -H / 2.0)
    if lamps:
        h.lamp(p, -W * 0.18, H * 0.26, 7)
        h.lamp(p, W * 0.18, H * 0.26, 7)
    for (x, y) in pins:
        d = math.hypot(x, y)
        l, t, r, b = -W / 2.0, -H / 2.0, W / 2.0, H / 2.0
        if x > r + 1:
            p.line(r, y, x, y)
        elif x < l - 1:
            p.line(l, y, x, y)
        elif y > b + 1:
            p.line(x, b, x, y)
        elif y < t - 1:
            p.line(x, t, x, y)
        p.outlet(x, y)
    return p


# =========================================================================
# Appliance / apparatus blocks (other, kitchen)
# =========================================================================
def heat_waves(p, l, t, r, b):
    for yy in (-6, 6):
        dl.sine(p, 0, (t + b) / 2.0 + yy, half=(r - l) * 0.33, amp=4)


def drum(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    p.circle(cx, cy, min(r - l, b - t) * 0.28)


def fridge(p, l, t, r, b):
    cx = (l + r) / 2.0
    p.line(cx, t + 4, cx, b - 4)                     # door split
    p.line(l + 5, (t + b) / 2.0, r - 5, (t + b) / 2.0)   # compartment shelf


def snowflake(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    s = min(r - l, b - t) * 0.22
    for a in range(0, 180, 60):
        rad = math.radians(a)
        p.line(cx - s * math.cos(rad), cy - s * math.sin(rad),
               cx + s * math.cos(rad), cy + s * math.sin(rad))


def airflow(p, l, t, r, b):
    for yy in (-7, 0, 7):
        dl.sine(p, 0, (t + b) / 2.0 + yy, half=(r - l) * 0.34, amp=3)


def burners(p, l, t, r, b):
    for dx in (-0.22, 0.22):
        for dy in (-0.22, 0.22):
            p.circle((l + r) / 2.0 + dx * (r - l), (t + b) / 2.0 + dy * (b - t),
                     min(r - l, b - t) * 0.12)


def boiler(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    p.circle(cx, cy, min(r - l, b - t) * 0.26)
    dl.sine(p, cx, cy, half=min(r - l, b - t) * 0.18, amp=3)


def coil_humps(p, l, t, r, b):
    cy = (t + b) / 2.0
    w = r - l
    for k in range(3):
        h.arc_poly(p, l + w * (0.3 + 0.2 * k), cy, 6, 180, 360)


def bell(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    h.arc_poly(p, cx, cy + 6, 10, 180, 360)
    p.line(cx - 10, cy + 6, cx + 10, cy + 6)
    p.dot(cx, cy + 10, 2)


def clock(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    rr = min(r - l, b - t) * 0.30
    p.circle(cx, cy, rr)
    p.line(cx, cy, cx, cy - rr * 0.8)
    p.line(cx, cy, cx + rr * 0.55, cy)


def lock_glyph(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    p.rect(cx - 12, cy - 2, cx + 12, cy + 14)
    h.arc_poly(p, cx, cy - 2, 7, 180, 360)          # shackle
    p.dot(cx, cy + 6, 2)


def dot_center(p, l, t, r, b):
    p.dot((l + r) / 2.0, (t + b) / 2.0, 6)


INNER = {
    "air conditioner": airflow, "washing machine": drum, "dish washer": drum,
    "freezer": snowflake, "refrigerator": fridge, "fridge with freezer": fridge,
    "heater": heat_waves, "heating": heat_waves, "heating with a motor": None,
    "water heater": boiler, "electric steamer": boiler, "frying pan, fryer": burners,
    "microwave oven": drum, "electric hot plate, heating plate": burners,
    "auxiliary apparatus for discharge lamp": coil_humps,
    "audio intercommunication equipment (entry phone)": bell,
    "consumers terminal": dot_center, "electric lock": lock_glyph,
    "time clock, time recorder": clock, "time switch": clock,
}


def draw_block(rec):
    name = rec["name"]
    low = name.lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)

    if "dimmer" in low:
        p = Ppd()
        h.sw_body(p, pins)                           # circle body + outlets
        dl.arrow(p, -W / 2.0, H / 2.0, W / 2.0, -H / 2.0)   # variability (dimmer) arrow
        return p
    if "push-button" in low:
        return draw_pushbutton(rec)
    if name == "distribution centre":
        return h.block(pins, W, H, inner=None)
    if "heating with a motor" in low:
        def mot(p, l, t, r, b):
            p.circle((l + r) / 2.0, (t + b) / 2.0, min(r - l, b - t) * 0.30)
        return h.block(pins, W, H, inner=mot, markings=rec["markings"] or None)
    if "timer" in low or name == "time switch":
        inner = clock if name == "time switch" else None
        return h.block(pins, W, H, inner=inner, markings=rec["markings"] or None)

    inner = INNER.get(name)
    return h.block(pins, W, H, inner=inner, markings=rec["markings"] or None)


def draw_pushbutton(rec):
    """Installation push-button: circle body + a button mark (EN 60617-11).
    Illuminated variant = lamp mark; protected variant = break-glass cover."""
    low = rec["name"].lower()
    W, H = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    p = Ppd()
    r = round(math.hypot(*pins[0]))                  # pins sit on the button circle
    p.circle(0, 0, r)
    dl.leads(p, pins, r)
    if "indicator lamp" in low:
        h.lamp(p, 0, 0, r * 0.6)                     # illuminated push-button
    else:
        p.dot(0, 0, 5)                               # button mark
    if "unintentional" in low:                       # break-glass protective cover
        p.rect(-W / 2.0, -H / 2.0, W / 2.0, H / 2.0)
    return p


# =========================================================================
# Dispatch
# =========================================================================
def classify(rec):
    cat = rec["category"]
    if cat == "installation/sockets":
        return draw_socket
    if cat == "installation/lightings":
        return draw_lighting
    if cat == "installation/switches":
        return draw_inst_switch
    if cat == "installation/switches/appliances":
        return draw_appl_switch
    return draw_block            # other, kitchen


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
