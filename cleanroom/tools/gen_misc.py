#!/usr/bin/env python3
"""Generate the misc batch (61 EN/IEC 60617 symbols) as .ppd.

Clean-room: drawn from the EN/IEC 60617 standard + the spec facts only.
Families: busbar-trunking systems (11-17), fault/flashover/magnet markers
(02-17), magnetic devices (05-06), proximity & touch (07-19/07-20), static
switches (07-25), spark gaps / GDT / arresters (07-22), the 3-pole striker
switch (07-21), and electroacoustic transducers (09-09).

Shared primitives: draw_lib.py; batch glyphs: helpers_misc.py (which reuses the
switching team's contact/actuator helpers). Run: python3 gen_misc.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
from draw_lib import Ppd
import helpers_misc as h
import helpers_switching_protection as hsw

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_misc.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def code(rec):
    return rec["standard"].split(":", 1)[1].strip()


def _outlets(p, pins):
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# =========================================================================
# Trunking systems (EN 60617 11-17).  Run = a two-line duct (channel).
# =========================================================================

def t_straight(rec):
    p = Ppd()
    w = rec["size"]["w"]
    h.channel(p, -w / 2.0, w / 2.0)
    return p


def t_assembled(rec):
    p = Ppd()
    w = rec["size"]["w"]
    h.channel(p, -w / 2.0, w / 2.0)
    for x in (-w / 4.0, 0, w / 4.0):               # joint ticks
        p.line(x, -10, x, 10, lw=2)
    return p


def t_adjustable_len(rec):
    p = Ppd()
    w = rec["size"]["w"]
    h.channel(p, -w / 2.0, w / 2.0)
    dl.arrow(p, -20, 0, -w / 2.0 + 6, 0)           # length-adjust double arrow
    dl.arrow(p, 20, 0, w / 2.0 - 6, 0)
    return p


def t_two_systems(rec):
    """Two stacked wiring systems A and B."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    yA, yB = -hh / 2.0 + 8, hh / 2.0 - 8
    h.channel(p, -w / 2.0, w / 2.0, y=yA, hw=8)
    h.channel(p, -w / 2.0, w / 2.0, y=yB, hw=8)
    p.marking(["A"], cx=-w / 2.0 + 16, cy=yA, bodyw=24, bodyh=16)
    p.marking(["B"], cx=-w / 2.0 + 16, cy=yB, bodyw=24, bodyh=16)
    return p


def t_anchored(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    h.channel(p, -w / 2.0, w / 2.0)
    p.polygon([(0, -hh / 2.0), (-10, -hh / 2.0 + 14), (10, -hh / 2.0 + 14)])
    p.polygon([(0, hh / 2.0), (-10, hh / 2.0 - 14), (10, hh / 2.0 - 14)])
    p.line(0, -10, 0, 10, lw=2)
    return p


def t_elbow(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    # a 90 deg bend as a corner duct
    p.polyline([(-a, b - 20), (-a, -b), (a, -b)])
    p.polyline([(-a + 20, b), (-a + 20, -b + 20), (a, -b + 20)])
    return p


def t_tee(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    h.channel(p, -w / 2.0, w / 2.0, y=-hh / 2.0 + 10)
    h.vchannel(p, -hh / 2.0 + 10, hh / 2.0)
    return p


def t_cross(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    h.channel(p, -w / 2.0, w / 2.0)
    h.vchannel(p, -hh / 2.0, hh / 2.0)
    return p


def t_crossing_nc(rec):
    """Crossing without connection: run hops over the other (different levels)."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    p.line(0, -hh / 2.0, 0, hh / 2.0)              # system at other level
    p.line(-w / 2.0, 0, -12, 0)
    p.line(12, 0, w / 2.0, 0)
    h.semicircle(p, 0, 0, 12, 180, 360)            # hop
    return p


def t_crossing_indep(rec):
    """Crossing of two independent systems: two ducts crossing."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    h.channel(p, -w / 2.0, w / 2.0, hw=6)
    h.vchannel(p, -hh / 2.0, hh / 2.0, hw=6)
    return p


def t_phase_transp(rec):
    """Phase transposition: conductors swap over within the run."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    for y in (-b, 0, b):
        p.line(-a, y, -20, y, lw=2)
        p.line(20, y, a, y, lw=2)
    p.line(-20, -b, 20, b, lw=2)                   # transpose crossings
    p.line(-20, b, 20, -b, lw=2)
    p.line(-20, 0, 20, 0, lw=2)
    return p


def t_reduction(rec):
    """Reduction unit: the duct tapers to a smaller section."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    p.polyline([(-a, -b), (0, -10), (a, -10)])
    p.polyline([(-a, b), (0, 10), (a, 10)])
    return p


def t_flexible(rec):
    """Flexible unit: a wavy (serpentine) run."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, amp = w / 2.0, hh / 2.0 - 4
    n = 48
    pts = [(-a + 2 * a * t / n, -amp * math.sin(2 * math.pi * 2 * t / n))
           for t in range(n + 1)]
    p.polyline(pts)
    p.line(-a, 0, -a, 0)
    return p


def t_expansion_cond(rec):
    """Expansion unit for conductors: run with an expansion loop."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    r = b - 1                                       # expansion loop = a ring
    p.circle(0, 0, r)
    p.line(-a, 0, -r, 0)
    p.line(r, 0, a, 0)
    return p


def t_expansion_encl(rec):
    """Expansion unit for enclosure: two interlocking brackets (expansion gap)."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    hw = b - 1
    h.channel(p, -a, -8, hw=hw)                     # left enclosure box walls
    h.channel(p, 8, a, hw=hw)
    p.polyline([(-8, -hw), (-8, -4), (8, -4), (8, -hw)])   # interlock
    p.polyline([(-8, hw), (-8, 4), (8, 4), (8, hw)])
    return p


def t_expansion_both(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, a, hw=b - 4)                  # enclosure walls
    p.line(-a, 0, -22, 0)                          # conductor + loop
    p.line(22, 0, a, 0)
    h.semicircle(p, 0, 0, 20, 180, 360)
    p.line(-22, 0, -20, 0)
    p.line(20, 0, 22, 0)
    p.line(-6, b - 4, -6, -b + 4, lw=2)            # enclosure expansion gap
    p.line(6, b - 4, 6, -b + 4, lw=2)
    return p


def t_equipment_box(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    p.rect(-w / 2.0, -hh / 2.0, w / 2.0, hh / 2.0)
    return p


def t_end_cover(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, a)
    p.line(a, -b, a, b)                            # end plate (sets height)
    p.line(a - 8, -b + 6, a - 8, b - 6, lw=2)     # cover inner line
    _outlets(p, pins_of(rec))                      # pin (-a,0)
    return p


def t_end_feeder(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, 20)
    p.rect(20, -b, a - 16, b)                      # feeder unit body
    h.feeder_arrow(p, a, 0)                        # supply feed
    p.line(a - 16, 0, a, 0)
    _outlets(p, pins_of(rec))
    return p


def t_end_feeder_box(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, -20)
    p.rect(-20, -b, 50, b)                         # feeder unit
    p.rect(55, -b, a, b)                           # equipment box
    _outlets(p, pins_of(rec))
    return p


def t_central_feeder(rec):
    """Central feeder, supply from the top."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    yrun = b - 10
    h.channel(p, -a, a, y=yrun)                    # the run along the bottom
    p.rect(-16, yrun - 34, 16, yrun - 6)           # feeder unit
    p.line(0, yrun - 6, 0, yrun)                   # feeder into the run
    p.line(0, -b, 0, yrun - 34)                    # supply drop from the top
    dl.arrowhead(p, 0, yrun - 34, 90, length=12, halfw=7)   # downward feed
    return p


def t_barrier_fire(rec):
    return _barrier_run(rec, hatch=True)


def t_barrier_pressure(rec):
    return _barrier_run(rec, fill=True)


def _barrier_run(rec, hatch=False, fill=False):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, a)
    h.barrier(p, 0, -b, b, hatch=hatch, fill=fill)
    return p


def t_tapoff_fixed(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a = w / 2.0
    pins = pins_of(rec)
    h.channel(p, -a, a)
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    h.tapoff(p, 0, ytop, ybot)
    _outlets(p, pins)
    return p


def t_tapoff_movable(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    pins = pins_of(rec)
    h.channel(p, -a, a)
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    h.tapoff(p, 0, ytop, ybot)
    dl.arrow(p, -24, -b + 8, 24, -b + 8)           # continuously movable
    dl.arrow(p, 24, b - 8, -24, b - 8)
    return _outlets(p, pins)


def t_tapoff_steps(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    pins = pins_of(rec)
    h.channel(p, -a, a)
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    h.tapoff(p, 0, ytop, ybot)
    # stepped-adjust indicator: a graduated scale beside the tap
    sx = -52
    p.line(sx, -b + 4, sx, b - 4, lw=2)
    for yy in range(-28, 29, 14):                  # step rungs
        p.line(sx - 6, yy, sx + 6, yy, lw=2)
    p.marking(["1m"], cx=40, cy=b - 12, bodyw=40, bodyh=18)
    return _outlets(p, pins)


def t_tapoff_sliding(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    pins = pins_of(rec)
    (px, py) = pins[0]
    h.channel(p, -a, a)
    p.line(px, 0, px, py)                           # tap by movable contact
    p.dot(px, 0, 4)
    dl.arrow(p, px - 24, -8, px + 20, -8)           # sliding movement
    return _outlets(p, pins)


def t_tapoff_fixed_box(rec):
    return _tapoff_box(rec, adjustable=False, socket=False)


def t_tapoff_adj_box(rec):
    return _tapoff_box(rec, adjustable=True, socket=False)


def t_tapoff_socket(rec):
    return _tapoff_box(rec, adjustable=False, socket=True)


def _tapoff_box(rec, adjustable=False, socket=False):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    h.channel(p, -a, a, y=-b + 10)                  # run at the top
    p.line(0, -b + 10, 0, -b + 28)                  # tap drop
    p.dot(0, -b + 10, 4)
    if socket:
        # socket-outlet with protective (earth) contact
        sy = b - 26
        p.line(0, -b + 28, 0, sy)
        h.semicircle(p, 0, sy, 26, 0, 180)          # socket bowl (bulges down)
        p.line(-26, sy, 26, sy)                      # diameter
        p.line(-34, sy, -26, sy)                     # protective contact bars
        p.line(26, sy, 34, sy)
    else:
        p.rect(-w / 3.0, -b + 28, w / 3.0, b)       # equipment box
        if adjustable:
            dl.arrow(p, 0, -b + 20, 0, -b + 40)     # adjustable tap
    return p


# =========================================================================
# Miscellaneous markers (02-17)
# =========================================================================

def m_fault(rec):
    """Fault: a bold (filled) arrow pointing at the fault location."""
    p = Ppd()
    hh = rec["size"]["h"]
    b = hh / 2.0
    p.line(0, -b, 0, b - 18)
    p.polygon([(0, b), (-10, b - 18), (10, b - 18)], fill=True)
    return p


def m_flashover(rec):
    """Flashover / break-through: arrow breaking through a barrier."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    p.line(-a, 0, a, 0)                              # barrier (insulation)
    p.line(0, -b, 0, b - 16)
    p.polygon([(0, b), (-9, b - 16), (9, b - 16)], fill=True)
    return p


def m_magnet(rec):
    """Permanent magnet: a plain bar."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    p.rect(-w / 2.0, -hh / 2.0, w / 2.0, hh / 2.0)
    return p


# =========================================================================
# Magnetic devices (05-06)
# =========================================================================

def m_mag_coupling(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    bl, bt, br, bb = -60, -hh / 2.0, 60, hh / 2.0
    p.rect(bl, bt, br, bb)
    for (x, y) in pins:                             # horizontal leads to corners
        p.line(br if x > 0 else bl, y, x, y)
    # magnetic coupling mark: two facing brackets )(
    h.semicircle(p, -14, 0, 24, 300, 420)
    h.semicircle(p, 14, 0, 24, 120, 240)
    return _outlets(p, pins)


def m_magnetoresistor(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    pins = pins_of(rec)
    p.rect(-15, -30, 15, 30)                         # resistor body
    p.line(0, -b, 0, -30)
    p.line(0, 30, 0, b)
    p.line(-a, b, a, -b)                             # magnetic-dependence oblique
    return _outlets(p, pins)


# =========================================================================
# Spark gaps / GDT / arresters (07-22)
# =========================================================================

def m_spark_gap(rec):
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    p.line(0, -b, 0, -14)
    p.line(0, b, 0, 14)
    h.spark_electrode(p, 0, -14, up=False)          # top electrode tip down
    h.spark_electrode(p, 0, 14, up=True)            # bottom electrode tip up
    return _outlets(p, pins_of(rec))


def m_double_spark_gap(rec):
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    pins = pins_of(rec)
    p.line(0, -b, 0, -22)
    p.line(0, b, 0, 22)
    p.line(-10, 0, 10, 0)                           # middle electrode bar
    p.line(-20, 0, -10, 0)                          # side tap
    h.spark_electrode(p, 0, -22, up=False)
    h.spark_electrode(p, 0, -6, up=True)
    h.spark_electrode(p, 0, 6, up=False)
    h.spark_electrode(p, 0, 22, up=True)
    return _outlets(p, pins)


def m_gdt(rec):
    """Protective gas-discharge tube: spark gap in a circular envelope."""
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    r = 38
    p.circle(0, 0, r)
    p.line(0, -b, 0, -12)
    p.line(0, b, 0, 12)
    p.line(-14, -12, 14, -12)                        # electrode plates
    p.line(-14, 12, 14, 12)
    return _outlets(p, pins_of(rec))


def m_gdt_symmetric(rec):
    """Symmetric protective GDT: envelope with a central tapped electrode."""
    p = Ppd()
    pins = pins_of(rec)
    r = 34
    p.circle(0, 0, r)
    p.line(0, -40, 0, -12)
    p.line(0, 40, 0, 12)
    p.line(-14, -12, 14, -12)
    p.line(-14, 12, 14, 12)
    p.line(-r, 0, -40, 0)                            # central tap to left pin
    p.line(-10, 0, 10, 0)
    return _outlets(p, pins)


def m_surge_diverter(rec):
    """Surge diverter / lightning arrester: box with a diagonal arrow."""
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    a, b = w / 2.0, hh / 2.0
    p.rect(-6, -14, 6, 14)
    p.line(0, -b, 0, -14)
    p.line(0, 14, 0, b)
    dl.arrow(p, -a, 8, a, -8)                        # diversion arrow
    return _outlets(p, pins_of(rec))


# =========================================================================
# Static switches (07-25)
# =========================================================================

def _static_box(p, b):
    p.rect(-19, -19, 19, 19)
    p.line(0, -b, 0, -19)
    p.line(0, 19, 0, b)


def m_static_general(rec):
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    _static_box(p, b)
    p.line(-10, 12, 10, -12)                         # contact blade
    return _outlets(p, pins_of(rec))


def m_static_contactor(rec):
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    _static_box(p, b)
    p.line(-10, 12, 10, -12)
    h.semicircle(p, 0, -4, 8, 0, 180)               # auto-return cup (contactor)
    return _outlets(p, pins_of(rec))


def m_static_dir(rec, up):
    p = Ppd()
    b = rec["size"]["h"] / 2.0
    _static_box(p, b)
    if up:
        p.polygon([(0, -12), (-10, 8), (10, 8)], fill=True)
    else:
        p.polygon([(0, 12), (-10, -8), (10, -8)], fill=True)
    return _outlets(p, pins_of(rec))


# =========================================================================
# Proximity / touch (07-19, 07-20)
# =========================================================================

def m_prox_sensor(rec):
    p = Ppd()
    r = rec["size"]["w"] / 2.0
    pins = pins_of(rec)
    h.diamond(p, 0, 0, r)
    return _outlets(p, pins)                         # pins at top/bottom vertices


def m_touch_sensor(rec):
    p = Ppd()
    r = rec["size"]["w"] / 2.0
    pins = pins_of(rec)
    h.diamond(p, 0, 0, r)
    p.line(-8, 0, 8, 0, lw=2)                        # touch electrode mark
    return _outlets(p, pins)


def m_prox_block(rec):
    p = Ppd()
    r = rec["size"]["w"] / 2.0
    pins = pins_of(rec)
    h.diamond(p, 0, 0, r)                            # vertices at the pins
    return _outlets(p, pins)


def _prox_glyph(p, gx, gy):
    h.diamond(p, gx, gy, 18)


def m_prox_switch_make(rec):
    p = Ppd()
    pins = pins_of(rec)
    cx = pins[0][0]
    yt, yb = min(y for _, y in pins), max(y for _, y in pins)
    h.prox_contact(p, cx, yt, yb, make=True, left=-40, glyph=_prox_glyph)
    return _outlets(p, pins)


def m_prox_switch_magnet(rec):
    p = Ppd()
    w = rec["size"]["w"]
    pins = pins_of(rec)
    cx = pins[0][0]
    yt, yb = min(y for _, y in pins), max(y for _, y in pins)
    lx = cx - w + 2
    h.prox_contact(p, cx, yt, yb, make=True, left=lx, glyph=_prox_glyph)
    p.rect(lx - 2, -8, lx + 18, 8)                  # magnet bar
    return _outlets(p, pins)


def m_prox_switch_iron(rec):
    p = Ppd()
    w = rec["size"]["w"]
    pins = pins_of(rec)
    cx = pins[0][0]
    yt, yb = min(y for _, y in pins), max(y for _, y in pins)
    lx = cx - w + 2
    h.prox_contact(p, cx, yt, yb, make=False, left=lx, glyph=_prox_glyph)
    p.marking(["Fe"], cx=lx, cy=24, bodyw=28, bodyh=18)
    return _outlets(p, pins)


def m_touch_switch(rec):
    p = Ppd()
    pins = pins_of(rec)
    cx = pins[0][0]
    yt, yb = min(y for _, y in pins), max(y for _, y in pins)

    def glyph(p, gx, gy):
        h.diamond(p, gx, gy, 18)
        p.line(gx - 8, gy, gx + 8, gy, lw=2)
    h.prox_contact(p, cx, yt, yb, make=True, left=-40, glyph=glyph)
    return _outlets(p, pins)


def m_rotary_encoder(rec):
    """Rotary encoder: a disc with a rotation arrow + radial marks (4 terminals)."""
    p = Ppd()
    pins = pins_of(rec)
    r = 30
    p.circle(0, 0, r)
    for (x, y) in pins:
        d = math.hypot(x, y)
        p.line(x / d * r, y / d * r, x, y)
    for a in range(0, 360, 45):                      # encoder ticks
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p.line(ca * (r - 8), sa * (r - 8), ca * r, sa * r, lw=2)
    h.semicircle(p, 0, 0, 12, 200, 340)              # rotation arc
    dl.arrowhead(p, 12 * math.cos(math.radians(340)),
                 12 * math.sin(math.radians(340)), 60, length=8, halfw=4)
    return _outlets(p, pins)


# =========================================================================
# 3-pole striker switch (07-21-06)
# =========================================================================

def m_striker_switch(rec):
    p = Ppd()
    w, hh = rec["size"]["w"], rec["size"]["h"]
    pins = pins_of(rec)
    cols = sorted(set(x for x, _ in pins))
    ytop = min(y for _, y in pins)
    ybot = max(y for _, y in pins)
    for cx in cols:
        hsw.v_leads(p, cx, ytop, ybot)              # terminal leads to ±18 zone
        tip = hsw.blade_make(p, cx, 22)             # knife contact
        p.rect(cx + 5, -11, cx + 17, 11)            # fuse on the blade
        p.line(cx + 22, -18, cx + 22, -34)          # striker rod up to trip bar
    hsw.mech_link(p, cols[0] + 22, -34, cols[-1] + 22)   # common striker trip
    p.line(-105, -46, 105, -46, lw=2)               # trip bar (sets width)
    p.line(cols[0] + 22, -34, cols[0] + 22, -46)
    return _outlets(p, pins)


# =========================================================================
# Electroacoustic transducers (09-09)
# =========================================================================

def a_loudspeaker(rec):
    p = Ppd()
    hh = rec["size"]["h"]
    b = hh / 2.0
    pins = pins_of(rec)
    h.speaker(p, 0, 0, boxw=12, boxh=22, horn=22)
    p.line(0, -22, 0, pins[0][1])
    p.line(0, 22, 0, pins[1][1])
    return _outlets(p, pins)


def a_loudspeaker_mic(rec):
    p = Ppd()
    pins = pins_of(rec)
    h.speaker(p, -6, 0, boxw=12, boxh=22, horn=22)
    p.circle(28, 0, 9)                              # microphone diaphragm
    p.line(0, -22, 0, pins[0][1])
    p.line(0, 22, 0, pins[1][1])
    return _outlets(p, pins)


def a_microphone(rec):
    p = Ppd()
    pins = pins_of(rec)
    r = rec["size"]["w"] / 2.0
    p.circle(0, 0, r)
    p.line(-r, -r, -r, r)                           # diaphragm: line tangent to one side
    p.line(0, -r, 0, pins[0][1])
    p.line(0, r, 0, pins[1][1])
    return _outlets(p, pins)


def a_microphone_es(rec):
    p = Ppd()
    pins = pins_of(rec)
    r = rec["size"]["w"] / 2.0
    p.circle(0, 0, r)
    p.line(-5, -r + 6, -5, r - 6)                   # condenser plates
    p.line(5, -r + 6, 5, r - 6)
    p.line(0, -r, 0, pins[0][1])
    p.line(0, r, 0, pins[1][1])
    return _outlets(p, pins)


def a_microphone_pp(rec):
    """Push-pull microphone: two capsules, 3 terminals."""
    p = Ppd()
    pins = pins_of(rec)
    p.circle(-24, 0, 24)
    p.circle(24, 0, 24)
    p.line(-48, -24, -48, 24)                       # left diaphragm (tangent)
    p.line(48, -24, 48, 24)                         # right diaphragm (tangent)
    top = min(pins, key=lambda q: q[1])
    p.line(top[0], -24, top[0], top[1])
    for (x, y) in pins:
        if y == 0:
            p.line(-48 if x < 0 else 48, 0, x, y)
    return _outlets(p, pins)


def a_earphone(rec):
    p = Ppd()
    pins = pins_of(rec)
    w, hh = rec["size"]["w"], rec["size"]["h"]
    h.lens(p, 0, 0, w / 2.0, hh / 2.0 - 2)
    p.line(0, -(hh / 2.0 - 2), 0, pins[0][1])
    p.line(0, hh / 2.0 - 2, 0, pins[1][1])
    return _outlets(p, pins)


def a_headset(rec):
    """Headset with one earphone: an earphone lens + a headband arc."""
    p = Ppd()
    pins = pins_of(rec)
    w, hh = rec["size"]["w"], rec["size"]["h"]
    b = hh / 2.0
    a = w / 2.0
    h.semicircle(p, 0, -22, a, 180, 360)            # headband arc over the top
    p.line(-a, -22, -a, 30)                         # band ends
    p.line(a, -22, a, 30)
    h.lens(p, 0, 28, 16, 24)                        # earphone (lower)
    for (x, y) in pins:
        p.line(0, 10, x, y)
    return _outlets(p, pins)


def a_handset(rec):
    """Handset: handle bar with an earphone (top) and microphone (bottom)."""
    p = Ppd()
    pins = pins_of(rec)
    hh = rec["size"]["h"]
    b = hh / 2.0
    p.line(-15, -b + 10, -15, b - 10)               # handle bar
    h.lens(p, 2, -b + 18, 12, 18)                   # earphone capsule (top)
    p.circle(2, b - 22, 22)                         # microphone capsule (bottom)
    for (x, y) in pins:
        p.line(-15, y, x, y)
    return _outlets(p, pins)


# =========================================================================
# Dispatch
# =========================================================================

TRUNK = {
    "11-17-01": t_straight, "11-17-02": t_assembled, "11-17-03": t_end_cover,
    "11-17-06": t_cross, "11-17-07": t_crossing_nc, "11-17-08": t_crossing_indep,
    "11-17-09": t_adjustable_len, "11-17-10": t_anchored,
    "11-17-11": t_expansion_encl, "11-17-12": t_expansion_cond,
    "11-17-13": t_expansion_both, "11-17-14": t_flexible,
    "11-17-15": t_reduction, "11-17-16": t_barrier_pressure,
    "11-17-17": t_phase_transp, "11-17-18": t_equipment_box,
    "11-17-19": t_barrier_fire, "11-17-20": t_end_feeder,
    "11-17-21": t_central_feeder, "11-17-22": t_end_feeder_box,
    "11-17-24": t_tapoff_fixed, "11-17-26": t_tapoff_movable,
    "11-17-27": t_tapoff_steps, "11-17-28": t_tapoff_sliding,
    "11-17-29": t_tapoff_fixed_box, "11-17-30": t_tapoff_adj_box,
    "11-17-31": t_tapoff_socket, "11-17-32": t_two_systems,
}

MISC = {
    "02-17-01": m_fault, "02-17-02": m_flashover, "02-17-03": m_magnet,
    "05-06-06": m_magnetoresistor, "05-06-07": m_mag_coupling,
    "07-19-01": m_prox_sensor, "07-19-02": m_prox_block, "07-19-04": m_touch_sensor,
    "07-20-01": m_touch_switch, "07-20-02": m_prox_switch_make,
    "07-20-03": m_prox_switch_magnet, "07-20-04": m_prox_switch_iron,
    "07-21-06": m_striker_switch,
    "07-22-01": m_spark_gap, "07-22-02": m_double_spark_gap,
    "07-22-03": m_surge_diverter, "07-22-05": m_gdt_symmetric,
    "07-25-01": m_static_general, "07-25-02": m_static_contactor,
    "07-25-03 NP": lambda r: m_static_dir(r, up=False),
    "07-25-03 PN": lambda r: m_static_dir(r, up=True),
    "09-09-01": a_microphone, "09-09-02": a_microphone_es,
    "09-09-03": a_microphone_pp, "09-09-04": a_earphone,
    "09-09-05": a_headset, "09-09-06": a_handset,
    "09-09-07": a_loudspeaker, "09-09-08": a_loudspeaker_mic,
}


def classify(rec):
    c = code(rec)
    if c in TRUNK:
        return TRUNK[c]
    if c in MISC:
        return MISC[c]
    name = rec["name"].lower()
    # 11-17-04 is reused by the spec for both the elbow and the tee
    if c == "11-17-04":
        return t_tee if "tee" in name else t_elbow
    # 07-22-04 is reused by the spec for both the GDT and the rotary encoder
    if c == "07-22-04":
        return m_rotary_encoder if "encoder" in name else m_gdt
    raise KeyError(f"no draw fn for {c} / {rec['name']}")


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
