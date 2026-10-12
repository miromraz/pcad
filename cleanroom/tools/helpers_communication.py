#!/usr/bin/env python3
"""Extra EN 60617 drawing helpers for the communication batch.

Owned by this team (draw_lib.py is the style lead's). Covers the
telecommunication families of IEC/EN 60617 sections 09, 10, 11:

  * antennas (10-04 / 10-05): the "Y" antenna glyph + qualifiers, dipoles,
    folded dipoles / Yagi, loop, horn, parabolic, rhombic, slot, balun,
    counterpoise;
  * radio stations (10-06): antenna over a station base, tx/rx arrows, space
    and earth stations;
  * telephone sets (09-05): instrument body + handset, with per-feature marks;
  * magnetic / recording heads (09-09) and transducer type marks (09-08);
  * telegraph apparatus & repeaters (09-01/02/06/07);
  * CATV distribution (11-05..11-10): amplifier triangles, head ends,
    splitters/couplers, equalizers, attenuator, power units.

All geometry in 0.1 mm units, y down, origin = insertion point (STYLE.md).
Pictograms for the obscure section-09 heads/types and the CATV two-ports are
best-guess EN-style depictions (see hand-off notes); the well-known antenna,
dipole, telephone-handset and radio-station glyphs are high confidence.
"""
import math
from draw_lib import Ppd, arrow, arrowhead, sine, add_outlets, leads, pin_center


# ---------------------------------------------------------------------------
# Antennas (10-04 / 10-05)
# ---------------------------------------------------------------------------

def antenna_glyph(p, feed=(0, 28), h=68, arm_half=20, apex_frac=0.45):
    """The EN 60617 antenna symbol: a mast from the feed point up to an apex,
    then two arms diverging upward (the open "Y"). Returns (apex_y, top_y)."""
    fx, fy = feed
    top = fy - h
    apex_y = top + h * apex_frac
    p.line(fx, fy, fx, apex_y)                 # mast / feed line
    p.line(fx, apex_y, fx - arm_half, top)     # left arm
    p.line(fx, apex_y, fx + arm_half, top)     # right arm
    return apex_y, top


def antenna(rec, qualifier=None):
    """Base antenna + an optional qualifier mark reaching the spec width."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    px, py = rec["pins"][0]["x"], rec["pins"][0]["y"]
    p = Ppd()
    apex_y, top = antenna_glyph(p, feed=(px, py), h=h)
    cy = (py + top) / 2.0
    if qualifier:
        qualifier(p, w, h, px, py, apex_y, top, cy)
    add_outlets(p, [(px, py)])
    return p


def q_horizontal(p, w, h, px, py, apex_y, top, cy):
    """Horizontal-polarization bar through the arms (fixed in azimuth)."""
    half = w / 2.0
    y = (apex_y + top) / 2.0
    p.line(px - half, y, px + half, y)


def q_vertical_dir(p, w, h, px, py, apex_y, top, cy):
    """Directional, vertically polarized: a short vertical stroke below apex +
    a wide base (horizontal polar diagram)."""
    p.line(px, apex_y, px, apex_y + 18, lw=6)
    half = w / 2.0
    p.line(px - half, py - 6, px + half, py - 6)


def q_circular(p, w, h, px, py, apex_y, top, cy):
    """Circular polarization: an elliptical rotation arrow around the mast foot
    (flat enough to fit the wide, short body)."""
    rx = w / 2.0 - 4
    ry = 22
    yc = (apex_y + py) / 2.0 + 4
    # near-closed arc with a gap and an arrowhead showing the sense of rotation
    p.arc(px - rx, yc - ry, px + rx, yc + ry,
          rx * 0.45, -ry * 0.9, rx * 0.45, ry * 0.9)
    arrowhead(p, px + rx * 0.45, yc - ry * 0.9, -20, length=10, halfw=5)


def q_rot_azimuth(p, w, h, px, py, apex_y, top, cy):
    """Variable in azimuth: a curved (rotation) arrow under the antenna."""
    r = w / 2.0 - 4
    yb = py - 2
    p.arc(px - r, yb - 14, px + r, yb + 14, -r, 0, r, 0)
    arrowhead(p, px + r, yb, 90, length=10, halfw=5)


def q_rot_elevation(p, w, h, px, py, apex_y, top, cy):
    """Variable in elevation: a curved arrow in the vertical plane."""
    r = 24
    cxx = px + 4
    p.arc(cxx - r, cy - r, cxx + r, cy + r, 0, -r, r, 0)
    arrowhead(p, cxx + r, cy, 90, length=10, halfw=5)


def q_turnstile(p, w, h, px, py, apex_y, top, cy):
    """Turnstile: a second, crossed antenna V (perpendicular pair)."""
    half = w / 2.0
    p.line(px, apex_y, px - half, apex_y - 6)
    p.line(px, apex_y, px + half, apex_y - 6)


def q_df(p, w, h, px, py, apex_y, top, cy):
    """Direction-finding antenna: a wide goniometer loop at the mast foot."""
    rx = w / 2.0 - 2
    ry = min(rx, 16)
    yc = apex_y + 8 + ry
    p.ellipse(px - rx, yc - ry, px + rx, yc + ry)


def dipole(pins):
    """Two collinear rods with a central feed gap, leads down to the pins."""
    p = Ppd()
    p.line(-70, 0, -8, 0)                       # left rod
    p.line(8, 0, 70, 0)                         # right rod
    for (x, y) in pins:
        inner = -8 if x < 0 else 8
        p.line(inner, 0, x, y)
    add_outlets(p, pins)
    return p


def folded_dipole(pins, w=140, h=40):
    """Elongated loop (racetrack) with a central bottom feed."""
    p = Ppd()
    xr, yr = w / 2.0 - 8, 18
    p.line(-xr, -yr, xr, -yr)                   # top bar
    p.line(-xr, yr, xr, yr)                     # bottom bar
    p.arc(-xr - yr, -yr, -xr + yr, yr, 0, -yr, 0, yr)   # left cap
    p.arc(xr - yr, -yr, xr + yr, yr, 0, yr, 0, -yr)     # right cap
    for (x, y) in pins:
        p.line(x, yr, x, y)
    add_outlets(p, pins)
    return p


def yagi(pins, w=180, h=70):
    """Folded dipole with a reflector (left) and 3 directors (right) on a boom."""
    p = Ppd()
    xl, xr = -w / 2.0, w / 2.0
    p.line(xl, 0, xr, 0)                        # boom
    p.line(xl, -35, xl, 35)                     # reflector (longest)
    # folded dipole just right of the reflector
    dx = xl + 36
    p.line(dx, -26, dx + 24, -26)
    p.line(dx, 26, dx + 24, 26)
    p.line(dx, -26, dx, 26)
    p.line(dx + 24, -26, dx + 24, 26)
    for i, dd in enumerate((0.15, 0.45, 0.75)):          # 3 directors
        x = xl + (xr - xl) * (0.5 + dd * 0.5)
        L = 26 - i * 3
        p.line(x, -L, x, L)
    for (x, y) in pins:
        p.line(x, 0, x, y)
    add_outlets(p, pins)
    return p


def loop_antenna(pins, w=120, h=140):
    """Frame (loop) antenna: a loop with two feed leads to the pins."""
    p = Ppd()
    r = min(w, h) / 2.0 - 2
    cyc = -h / 2.0 + r + 6
    p.circle(0, cyc, r)
    for (x, y) in pins:
        p.line(x, cyc + r, x, y)
    add_outlets(p, pins)
    return p


def counterpoise(pins, w=80, h=20):
    """Elevated earth: a horizontal conductor with short down-strokes, fed up."""
    p = Ppd()
    px, py = pins[0]
    p.line(-w / 2.0, 0, w / 2.0, 0)            # main conductor
    for x in (-w / 4.0, 0, w / 4.0):           # down-strokes
        p.line(x, 0, x - 6, 10)
    p.line(px, 0, px, py)                       # feed up
    add_outlets(p, pins)
    return p


def balun(pins, w=80, h=24):
    """Balanced-unbalanced transformer: two coils (semicircle bumps) facing a
    central core; single unbalanced port left, two balanced ports right."""
    p = Ppd()
    yr = h / 2.0
    p.line(-2, -yr, -2, yr)                     # core
    p.line(2, -yr, 2, yr)
    for cy in (-5, 5):                          # left winding bumps
        p.arc(-16, cy - 5, -6, cy + 5, -5, 0, 5, 0)
    for cy in (-5, 5):                          # right winding bumps
        p.arc(6, cy - 5, 16, cy + 5, 5, 0, -5, 0)
    p.line(-11, 0, -16, 0)                      # unbalanced lead-in bus
    for (x, y) in pins:
        bx = 16 if x > 0 else -16
        p.line(bx, max(-yr, min(yr, y)), x, y)
    add_outlets(p, pins)
    return p


def horn_antenna(pins, w=80, h=40):
    """Horn feed: a trapezoid flaring from a left throat to a right mouth."""
    p = Ppd()
    px, py = pins[0]
    throat, mouth = -20, w / 2.0
    p.line(throat, -4, mouth, -h / 2.0)
    p.line(throat, 4, mouth, h / 2.0)
    p.line(mouth, -h / 2.0, mouth, h / 2.0)
    p.line(throat, -4, throat, 4)
    p.line(px, 0, throat, 0)                    # feed
    add_outlets(p, pins)
    return p


def parabolic(w=80, h=160):
    """Parabolic reflector (vertical dish) fed by a rectangular waveguide."""
    p = Ppd()
    xr = w / 2.0
    # dish: a left-opening arc on the right half, spanning most of the height
    p.arc(0, -h / 2.0, xr, h / 2.0, -xr / 2.0, -h / 2.0, -xr / 2.0, h / 2.0)
    # waveguide feeder (two parallel lines) from the left to the focus
    p.line(-xr, -6, 0, -6)
    p.line(-xr, 6, 0, 6)
    p.line(0, -6, 0, 6)
    return p


def horn_reflector(w=200, h=64):
    """Horn-reflector antenna: a horn flare feeding a curved reflector."""
    p = Ppd()
    # horn on the left
    p.line(-w / 2.0, -6, -w / 4.0, -h / 2.0)
    p.line(-w / 2.0, 6, -w / 4.0, h / 2.0)
    p.line(-w / 2.0, -6, -w / 2.0, 6)
    p.line(-w / 4.0, -h / 2.0, -w / 4.0, h / 2.0)
    # reflector arc on the right
    p.arc(w / 4.0 - 20, -h / 2.0, w / 2.0, h / 2.0,
          -20, -h / 2.0, -20, h / 2.0)
    return p


def cheese_reflector(pins, w=190, h=40):
    """Cheese-box reflector with a horn feed and a waveguide feeder."""
    p = Ppd()
    px, py = pins[0]
    p.line(px, 0, -40, 0)                       # waveguide feeder
    # small horn
    p.line(-40, -4, -16, -h / 2.0)
    p.line(-40, 4, -16, h / 2.0)
    p.line(-16, -h / 2.0, -16, h / 2.0)
    # cheese reflector: a shallow vertical arc on the right
    xr = w / 2.0 + px / 1.0   # keep width ~ spec
    p.arc(70, -h / 2.0, 110, h / 2.0, -20, -h / 2.0, -20, h / 2.0)
    add_outlets(p, pins)
    return p


def rhombic(pins, w=169, h=150):
    """Rhombic antenna: a diamond of wires, fed at the left, terminated by a
    resistor at the right apex."""
    p = Ppd()
    A = (-90, 0)                                # feed apex (left)
    B = (-14, -74)                             # top
    C = (58, 0)                                # termination apex (right)
    D = (-14, 74)                              # bottom
    for (x1, y1), (x2, y2) in ((A, B), (B, C), (C, D), (D, A)):
        p.line(x1, y1, x2, y2)
    for (x, y) in pins:                        # feed leads
        p.line(x, y, A[0], A[1])
    # terminating resistor at C + ground stub
    p.rect(C[0] - 4, -7, C[0] + 14, 7)
    p.line(C[0] + 14, 0, C[0] + 20, 0)
    p.line(C[0] + 20, -7, C[0] + 20, 7)
    add_outlets(p, pins)
    return p


def slot_antenna(pins, w=100, h=100):
    """Slot antenna: a rectangular waveguide face with a radiating slot."""
    p = Ppd()
    px, py = pins[0]
    p.rect(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    p.rect(-6, -h / 2.0 + 16, 6, h / 2.0 - 16)        # the slot
    p.line(px, h / 2.0, px, py)                       # feed
    add_outlets(p, pins)
    return p


# ---------------------------------------------------------------------------
# Radio stations (10-06)
# ---------------------------------------------------------------------------

def radio_station(rec, mode="plain"):
    """Antenna over a station base. mode: plain / tx / rx / txrx."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    cx, _ = pin_center(pins)
    yb = max(y for _, y in pins) if pins else h / 2.0
    top = yb - h
    p = Ppd()
    apex_y = top + h * 0.30
    arm = min(w / 2.0, 50)
    p.line(cx, apex_y, cx, yb - 20)                   # mast
    p.line(cx, apex_y, cx - arm, top)                 # arms
    p.line(cx, apex_y, cx + arm, top)
    for (x, y) in pins:                               # station base leads
        p.line(cx, yb - 20, x, y)
    midy = (apex_y + yb) / 2.0
    if mode in ("tx", "txrx"):
        arrow(p, cx + arm * 0.5, midy, cx + arm * 1.1, midy - 26)
    if mode in ("rx", "txrx"):
        arrow(p, cx - arm * 1.1, midy - 26, cx - arm * 0.5, midy)
    add_outlets(p, pins)
    return p


def space_station(rec, kind="plain"):
    """Satellite: a central body, four axis leads, and solar-panel wings that
    fill the spec box. kind: plain / active / passive."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    r = 18
    p.circle(0, 0, r)
    if kind == "active":
        p.text(0, 0, "~", size=40, al=9)
    for (x, y) in pins:
        d = math.hypot(x, y)
        ux, uy = x / d, y / d
        p.line(ux * r, uy * r, x, y)
    # panels: extend along the longer axis to reach the box
    xr, yr = w / 2.0, h / 2.0
    if yr > 55:                                       # tall -> vertical panels
        for s in (-1, 1):
            p.rect(-16, s * 44, 16, s * yr)
            p.line(0, s * 44, 0, s * yr)
    if xr > 55:                                       # wide -> horizontal panels
        for s in (-1, 1):
            p.rect(s * 44, -16, s * xr, 16)
    add_outlets(p, pins)
    return p


def passive_relay(w=160, h=140):
    """Passive relay (reflector) station: two back-to-back reflector arcs."""
    p = Ppd()
    cxo = w / 2.0 - 16
    for s in (-1, 1):
        cx = s * cxo
        p.arc(cx - 16, -h / 2.0 + 6, cx + 16, h / 2.0 - 6,
              s * -16, -h / 2.0 + 6, s * -16, h / 2.0 - 6)
    p.line(-cxo, 0, cxo, 0)                           # feeder between them
    return p


# ---------------------------------------------------------------------------
# Telephone sets (09-05)
# ---------------------------------------------------------------------------

def telephone(rec, feature=None):
    """Instrument body + handset; `feature` adds the distinguishing mark."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    L, T, R, B = -w / 2.0 + 2, -h / 2.0 + 24, w / 2.0 - 2, h / 2.0 - 10
    p.rect(L, T, R, B)                                 # instrument body
    # handset resting on top: a bar with an earpiece at each end
    hy = T - 18
    p.line(L + 30, hy, R - 30, hy)
    for ex in (L + 30, R - 30):
        p.line(ex, hy, ex, T)
        p.line(ex - 8, T, ex + 8, T)
    if feature:
        feature(p, L, T, R, B, w, h)
    # pin leads from the nearest body edge
    for (x, y) in pins:
        if x <= L:
            p.line(L, y, x, y)
        elif x >= R:
            p.line(R, y, x, y)
        p.outlet(x, y)
    return p


def f_dial(p, L, T, R, B, w, h):
    cx, cy = R - 34, (T + B) / 2.0
    p.circle(cx, cy, 20)
    for a in range(0, 360, 36):
        rad = math.radians(a)
        p.dot(cx + 14 * math.cos(rad), cy + 14 * math.sin(rad), r=2)


def f_loudspeaker(p, L, T, R, B, w, h):
    cx, cy = R - 36, (T + B) / 2.0
    p.rect(cx - 6, cy - 10, cx + 2, cy + 10)
    p.polyline([(cx + 2, cy - 10), (cx + 18, cy - 20),
                (cx + 18, cy + 20), (cx + 2, cy + 10)])


def f_amplifier(p, L, T, R, B, w, h):
    cx, cy = R - 40, (T + B) / 2.0
    p.polygon([(cx - 16, cy - 16), (cx - 16, cy + 16), (cx + 18, cy)])


def f_ringer(p, L, T, R, B, w, h):
    cx, cy = R - 36, (T + B) / 2.0
    p.circle(cx, cy, 18)
    sine(p, cx, cy, half=11, amp=7)


def f_pay(p, L, T, R, B, w, h):
    cx, cy = R - 34, T + 14
    p.line(cx - 8, cy, cx + 8, cy)                     # coin slot
    p.circle(cx, cy + 20, 12)                          # coin


def f_keys(p, L, T, R, B, w, h):
    cy = (T + B) / 2.0 + 10
    for i in range(3):
        x = R - 60 + i * 20
        p.rect(x, cy - 7, x + 12, cy + 7)              # buttons


def f_twolines(p, L, T, R, B, w, h):
    for y in (-10, 10):                                # two line pairs on the left
        p.line(L, (T + B) / 2.0 + y, L - 0, (T + B) / 2.0 + y)
    p.text((L + R) / 2.0, (T + B) / 2.0, "n", size=60, al=9)


def f_battery(p, L, T, R, B, w, h, local=True):
    cx, cy = R - 40, (T + B) / 2.0
    p.line(cx, cy - 16, cx, cy + 16)                   # long plate (+)
    p.line(cx + 12, cy - 8, cx + 12, cy + 8)           # short plate (-)
    if local:
        p.line(cx - 10, cy, cx, cy)


# ---------------------------------------------------------------------------
# Heads (09-09) & transducer type marks (09-08)
# ---------------------------------------------------------------------------

def head(rec, gaps=1, extra=None):
    """Magnetic / recording head: an oval core with a radial working gap facing
    the medium, a lead to the connection pin. `gaps` = number of track gaps."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    simplified = w < 80
    if simplified:
        px = pins[0][0] if pins else w / 2.0
        r = min(13.0, h / 2.0 - 2)
        cxc = px - w + r + 6                            # fill the box to the left
        p.circle(cxc, 0, r)
        p.line(cxc - r, -4, cxc - r - 6, -4)           # gap notch
        p.line(cxc - r, 4, cxc - r - 6, 4)
        if pins:
            p.line(cxc + r, 0, px, pins[0][1])
    else:
        xl = -w / 2.0 + 4
        xr = 16 if pins else w / 2.0 - 4               # 0-pin cores fill the box
        yr = h / 2.0 - 2
        p.ellipse(xl, -yr, xr, yr)                      # core
        # working gap(s) on the left face
        for i in range(gaps):
            gy = 0 if gaps == 1 else -yr * 0.5 + i * (yr / max(gaps - 1, 1))
            p.line(xl, gy - 3, xl - 6, gy - 3)
            p.line(xl, gy + 3, xl - 6, gy + 3)
        if pins:
            p.line(xr, 0, pins[0][0], pins[0][1])
        if extra:
            extra(p, xl, xr, yr)
    add_outlets(p, pins)
    return p


def head_erase_mark(p, xl, xr, yr):
    p.line(-10, -8, 6, 8)                               # cross = erase
    p.line(-10, 8, 6, -8)


def head_stylus(p, xl, xr, yr):
    p.line(xl - 18, yr + 6, xl + 2, 0)                 # stylus to the gap
    arrowhead(p, xl + 2, 0, math.degrees(math.atan2(-yr - 6, 20)),
              length=9, halfw=4)


def head_light(p, xl, xr, yr):
    for sx in (-14, 2):                                # two short light arrows in
        p.line(sx - 6, -yr - 5, sx, -yr + 1)
        arrowhead(p, sx, -yr + 1, math.degrees(math.atan2(6, 6)),
                  length=7, halfw=3)


def type_mark(rec):
    """Small transducer 'type' pictograms (09-08)."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    code = rec["standard_normalized"][-8:]
    p = Ppd()
    if code == "09-08-01":                             # magnetic: a coil
        for x in (-20, -12, -4, 4, 12, 20):
            p.arc(x - 5, -23, x + 5, 23, 0, -23, 0, 23)
    elif code == "09-08-02":                           # moving coil/ribbon
        p.rect(-24, -12, 24, 12)
        p.line(0, -12, 0, 12, lw=6)
    elif code == "09-08-03":                           # moving iron
        p.rect(-24, -12, 24, 12)
        p.line(-9, -12, -9, 12, lw=6)
        p.line(9, -12, 9, 12, lw=6)
    elif code == "09-08-04":                           # stereo: two channels
        for cx in (-16, 16):
            p.circle(cx, 0, 24)
    elif code == "09-08-05":                           # disc
        p.circle(0, 0, h / 2.0 - 4)
        p.circle(0, 0, 5)
        p.line(0, -5, 0, -(h / 2.0 - 4))               # stylus radius
    elif code == "09-08-06":                           # tape/film: two reels
        cx0 = w / 2.0 - 22
        for cx in (-cx0, cx0):
            p.circle(cx, 0, 22)
            p.circle(cx, 0, 5)
        p.line(-cx0, -22, cx0, -22)                     # tape
    elif code == "09-08-07":                           # drum (cylinder)
        p.rect(-w / 2.0 + 2, -h / 2.0 + 10, w / 2.0 - 2, h / 2.0 - 10)
        p.ellipse(-w / 2.0 + 2, -h / 2.0, w / 2.0 - 2, -h / 2.0 + 20)
        p.ellipse(-w / 2.0 + 2, h / 2.0 - 20, w / 2.0 - 2, h / 2.0)
    elif code in ("09-08-08", "09-08-09"):             # record (or/and) reproduce
        p.line(-w / 2.0, 0, w / 2.0, 0)
        arrowhead(p, w / 2.0, 0, 0, length=8, halfw=5)
        if code == "09-08-09":                         # "and": double arrow
            arrowhead(p, -w / 2.0, 0, 180, length=8, halfw=5)
    elif code == "09-08-10":                           # erasing
        p.line(-10, -10, 10, 10)
        p.line(-10, 10, 10, -10)
    else:
        p.rect(-w / 2.0 + 2, -h / 2.0 + 2, w / 2.0 - 2, h / 2.0 - 2)
    return p


def saw_transducer(pins, w=80, h=24):
    """Surface-acoustic-wave interdigital transducer (two combs)."""
    p = Ppd()
    yr = h / 2.0
    p.line(-20, -yr, -20, yr)                          # left bus
    p.line(20, -yr, 20, yr)                            # right bus
    for i, yy in enumerate((-6, 2, 8)):
        bus = -20 if i % 2 == 0 else 20
        p.line(bus, yy, bus + (14 if bus < 0 else -14), yy)
    for (x, y) in pins:
        p.line((20 if x > 0 else -20), 0, x, y)
    add_outlets(p, pins)
    return p


# ---------------------------------------------------------------------------
# Telegraph apparatus & repeaters (09-01/02/06/07)
# ---------------------------------------------------------------------------

def apparatus(rec, inner=None):
    """A 0-pin apparatus box centred on the origin, optional inner pictogram +
    markings."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    l, t, r, b = -w / 2.0, -h / 2.0, w / 2.0, h / 2.0
    p.rect(l, t, r, b)
    if inner:
        inner(p, l, t, r, b)
    if rec["markings"]:
        p.marking(rec["markings"], cx=0, cy=0, bodyw=w, bodyh=h)
    return p


def connecting_stage(w=149, h=100):
    """Switching/connecting stage: a trapezoid (wide input, narrow output)."""
    p = Ppd()
    l, r = -w / 2.0, w / 2.0
    tb = h / 2.0
    p.polygon([(l, -tb), (l, tb), (r, tb * 0.45), (r, -tb * 0.45)])
    return p


def auto_switch(rec):
    """Automatic switching equipment: a box with an internal switch matrix."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    p = Ppd()
    l, t, r, b = -w / 2.0, -h / 2.0, w / 2.0, h / 2.0
    p.rect(l, t, r, b)
    # crossbar matrix: horizontal & vertical rails + contact dots
    for yy in (-h / 4.0, 0, h / 4.0):
        p.line(l + 20, yy, r - 20, yy)
    for xx in (-w / 4.0, 0, w / 4.0):
        p.line(xx, t + 16, xx, b - 16)
    for yy in (-h / 4.0, 0, h / 4.0):
        for xx in (-w / 4.0, 0, w / 4.0):
            p.dot(xx, yy, r=4)
    return p


def inner_keyboard(p, l, t, r, b):
    for row in (b - 34, b - 20):
        for i in range(5):
            p.dot(l + 20 + i * (r - l - 40) / 4.0, row, r=4)


def inner_printer(p, l, t, r, b):
    for i, yy in enumerate((t + 20, t + 34, t + 48)):
        p.line(l + 16, yy, r - 16 - i * 8, yy)


def inner_fax(p, l, t, r, b):
    for xx in range(int(l) + 16, int(r) - 10, 14):
        p.line(xx, t + 14, xx + 10, b - 14)


def inner_tape(p, l, t, r, b):
    p.line(l + 14, b - 16, r - 14, b - 16)             # tape strip
    inner_keyboard(p, l, t, r, b - 18)


# ---------------------------------------------------------------------------
# CATV distribution (11-05 .. 11-10)
# ---------------------------------------------------------------------------

def amp_triangle(rec, inner_dir=None):
    """CATV amplifier triangle (apex at the right output) with the many edge
    taps as outlets, and an optional small inner return/bridge triangle."""
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.polygon([(-20, -30), (-20, 30), (30, 0)])        # main amplifier
    if inner_dir == "return":                          # left-pointing return amp
        p.polygon([(14, -9), (14, 9), (-4, 0)])
    elif inner_dir == "bridge":                        # right-pointing bridge amp
        p.polygon([(-6, -9), (-6, 9), (12, 0)])
    add_outlets(p, pins)
    return p


def bridge_amp(rec):
    w, h = rec["size"]["w"], rec["size"]["h"]
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.polygon([(-w / 2.0, -25), (-w / 2.0, 25), (w / 2.0, 0)])
    add_outlets(p, pins)
    return p


def head_end(rec, local_antenna=False):
    """CATV head end: a circle with 12 distribution taps on its rim and a source
    triangle (plus a small antenna glyph when it has a local antenna)."""
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    r = 40
    p.circle(0, 0, r)
    p.polygon([(-16, -12), (-16, 12), (8, 0)])         # signal source
    if local_antenna:
        p.line(18, -2, 18, -20)                        # small antenna
        p.line(18, -20, 10, -28)
        p.line(18, -20, 26, -28)
    leads(p, pins, r)
    return p


def splitter(rec):
    """CATV splitter: an input wedge feeding several tapped outputs."""
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.polygon([(-20, 0), (26, -40), (26, 40)])
    add_outlets(p, pins)
    return p


def directional_coupler(rec):
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.rect(-40, -40, 40, 40)
    arrow(p, -30, -14, 30, -14)                        # main through path
    arrow(p, -24, 14, 24, 14)                          # coupled path
    p.line(0, 14, 0, 40)                               # coupled port down
    add_outlets(p, pins)
    return p


def line_power_unit(rec):
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.rect(-40, -40, 40, 40)
    p.line(-20, -10, 20, -10)                          # "=" (DC feed)
    p.line(-20, 0, 20, 0)
    p.line(-20, 10, 20, 10)
    add_outlets(p, pins)
    return p


def injection_point(rec):
    pins = [(p["x"], p["y"]) for p in rec["pins"]]
    p = Ppd()
    p.rect(-40, -40, 40, 40)
    p.circle(0, 0, 14)
    for (x, y) in pins:
        d = math.hypot(x, y)
        ux, uy = x / d, y / d
        p.line(ux * 14, uy * 14, ux * 40, uy * 40)
    arrow(p, 0, 36, 0, 10)                             # power injected inward
    add_outlets(p, pins)
    return p


def eq_curve(kind):
    """Equalizer/attenuator inner graphic."""
    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        xw = min((r - l) * 0.32, 30)
        yh = min((b - t) * 0.28, 22)
        if kind == "attenuator":                       # a pad: >< triangles
            p.polygon([(cx - xw, cy - yh), (cx - xw, cy + yh), (cx - 2, cy)],
                      fill=True)
            p.polygon([(cx + xw, cy - yh), (cx + xw, cy + yh), (cx + 2, cy)],
                      fill=True)
        else:                                          # equalizer slope
            p.line(cx - xw, cy, cx + xw, cy, lw=2)
            p.line(cx, cy - yh, cx, cy + yh, lw=2)
            p.polyline([(cx - xw, cy + yh), (cx, cy), (cx + xw, cy - yh)])
    return f
