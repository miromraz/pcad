#!/usr/bin/env python3
"""Extra EN 60617 drawing helpers for the semiconductors_transmission batch.

Owned by this team (draw_lib.py is the style lead's). Covers:
  * discrete semiconductors drawn in a circular envelope (r=50): JFET, UJT,
    MOSFET/IGFET, IGBT, PNIP/PNIN;
  * horizontal diode family (diode/LED/zener/backward/temp/bidirectional/diac);
  * transmission two/four-port inner graphics (filter response curves, limiter/
    clipper transfer characteristics, compander/emphasis curves, misc).

All geometry in 0.1 mm units, y down, origin = insertion point (see STYLE.md).
"""
import math
from draw_lib import Ppd, arrow, arrowhead, sine, add_outlets

ENV_R = 50          # transistor envelope radius (100x100 bodies)


# ---------------------------------------------------------------------------
# Discrete transistors (circular envelope, pins already on the r=50 circle)
# ---------------------------------------------------------------------------

def _env(p):
    p.circle(0, 0, ENV_R)


def jfet(pins, ntype):
    """J-FET: vertical channel bar, gate from left with a junction arrow
    (N-channel arrow points toward the channel, P-channel away), drain/source
    to the right. pins: gate, src, drain (spec order)."""
    p = Ppd()
    _env(p)
    gx = 0
    p.line(gx, -28, gx, 28, lw=6)                 # channel bar
    p.line(gx, -21, 46, -21)                      # upper S/D lead
    p.line(gx, 21, 46, 21)                        # lower S/D lead
    p.line(-46, 21, gx - 2, 21)                   # gate lead to the bar
    arrowhead(p, gx, 21, 0 if ntype else 180, length=12, halfw=6)
    add_outlets(p, pins)
    return p


def unijunction(pins, ntype):
    """Unijunction transistor: channel bar with two bases right, emitter from
    lower-left with a junction arrow (direction encodes the base type)."""
    p = Ppd()
    _env(p)
    bx = 16
    p.line(bx, -30, bx, 30, lw=6)                 # base bar (B2 top .. B1 bottom)
    p.line(bx, -21, 45, -21)                      # B2
    p.line(bx, 21, 45, 21)                        # B1
    # emitter from (-35,35) to the bar, arrow at the junction
    ex, ey = -35, 35
    jx, jy = bx, 12
    p.line(ex, ey, jx, jy)
    ang = math.degrees(math.atan2(jy - ey, jx - ex))
    arrowhead(p, jx, jy, ang if ntype else ang + 180, length=12, halfw=6)
    add_outlets(p, pins)
    return p


def _mos_channel(p, x, broken):
    """Channel at column x: three short bars (enhancement) or a solid bar
    (depletion)."""
    if broken:
        for a, b in ((-20, -8), (-6, 6), (8, 20)):
            p.line(x, a, x, b, lw=6)
    else:
        p.line(x, -20, x, 20, lw=6)


def mosfet(pins, broken, ntype, gates=1):
    """MOSFET/IGFET: insulated gate electrode(s) + channel column + drain/
    source/substrate to the right; substrate arrow encodes N/P. broken=True for
    enhancement (3-segment channel), False for depletion (solid)."""
    p = Ppd()
    _env(p)
    gbar = -22
    ch = -8
    p.line(gbar, -20, gbar, 20, lw=4)             # gate electrode bar
    if gates == 2:
        p.line(gbar, -20, gbar, -2, lw=4)         # split gate (upper)
        p.line(gbar, 2, gbar, 20, lw=4)
    _mos_channel(p, ch, broken)
    # right-side terminals: drain (top), source (bottom), substrate (mid)
    p.line(ch, -18, 46, -21)                      # drain
    p.line(ch, 18, 46, 21)                        # source
    p.line(ch, 0, 50, 0)                          # substrate
    arrowhead(p, ch + 14, 0, 180 if ntype else 0, length=12, halfw=6)
    # gate leads: order of left pins varies, so connect every left-of-centre pin
    for (x, y) in pins:
        if x < gbar:
            p.line(x, y, gbar, max(-18, min(18, y)))
    add_outlets(p, pins)
    return p


def igbt(pins, broken, ntype):
    """IGBT: MOS gate (insulated) driving a bipolar output; emitter lead carries
    the arrow (N/P by direction). pins: gate, then two right (coll/emitter)."""
    p = Ppd()
    _env(p)
    gbar = -20
    ch = -6
    cerail = 8
    p.line(-44, 25, gbar, 18)                     # gate lead
    p.line(gbar, -20, gbar, 20, lw=4)             # gate electrode
    _mos_channel(p, ch, broken)
    p.line(ch, 0, cerail, 0)                      # channel -> C/E rail
    p.line(cerail, -22, cerail, 22, lw=4)         # collector-emitter rail
    p.line(cerail, -18, 24, -43)                  # collector
    # emitter with arrow
    p.line(cerail, 18, 24, 43)
    ang = math.degrees(math.atan2(43 - 18, 24 - cerail))
    arrowhead(p, 24, 43, ang if ntype else ang + 180, length=12, halfw=6)
    add_outlets(p, pins)
    return p


def pnip(pins, ntype):
    """PNIP/PNIN: bipolar-style figure with a base bar fed by the two left pins,
    collector and emitter to the right; emitter arrow direction encodes P/N."""
    p = Ppd()
    _env(p)
    bar = -18
    p.line(bar, -26, bar, 26, lw=6)               # base bar
    # two base connections (left pins) -> bar
    lefts = sorted([pt for pt in pins if pt[0] < bar], key=lambda q: q[1])
    rights = sorted([pt for pt in pins if pt[0] >= bar], key=lambda q: q[1])
    for (x, y) in lefts:
        p.line(x, y, bar, max(-20, min(20, y)))
    # rights: upper = collector, lower = emitter(arrow)
    if len(rights) == 2:
        (ux, uy), (lx, ly) = rights[0], rights[1]
        p.line(bar, -12, ux, uy)                   # collector (upper)
        p.line(bar, 12, lx, ly)                    # emitter (lower)
        ang = math.degrees(math.atan2(ly - 12, lx - bar))
        arrowhead(p, lx, ly, ang if not ntype else ang + 180, length=12, halfw=6)
    add_outlets(p, pins)
    return p


# ---------------------------------------------------------------------------
# Diode family (horizontal axis, anode triangle -> cathode bar)
# ---------------------------------------------------------------------------

def _tri(p, x0, x1, h):
    p.polygon([(x0, -h), (x0, h), (x1, 0)])        # anode triangle (outline)


def diode(pins, h=18, x0=-14, x1=14):
    p = Ppd()
    _tri(p, x0, x1, h)
    p.line(x1, -h, x1, h)                           # cathode bar
    _dlead(p, pins, x0, x1)
    add_outlets(p, pins)
    return p


def _dlead(p, pins, x0, x1):
    for (x, y) in pins:
        if x < x0:
            p.line(x, 0, x0, 0)
        elif x > x1:
            p.line(x1, 0, x, 0)


def zener(pins, h=18, x0=-14, x1=14):
    p = Ppd()
    _tri(p, x0, x1, h)
    p.line(x1, -h, x1, h)
    p.line(x1, -h, x1 - 7, -h - 7)                  # zener flag (bent cathode)
    _dlead(p, pins, x0, x1)
    add_outlets(p, pins)
    return p


def led(pins):
    p = Ppd()
    x0, x1, h = -10, 10, 16
    _tri(p, x0, x1, h)
    p.line(x1, -h, x1, h)
    _dlead(p, pins, x0, x1)
    # two emission arrows pointing away (up-right)
    for sx in (-4, 8):
        arrow(p, sx, -h, sx + 20, -h - 28)
    add_outlets(p, pins)
    return p


def temp_diode(pins):
    p = Ppd()
    x0, x1, h = -13, 13, 20
    _tri(p, x0, x1, h)
    p.line(x1, -h, x1, h)
    _dlead(p, pins, x0, x1)
    p.text(0, -h - 14, "Θ", size=55, al=9)     # theta above
    add_outlets(p, pins)
    return p


def backward_diode(pins):
    p = Ppd()
    x0, x1, h = -14, 14, 18
    _tri(p, x0, x1, h)
    p.line(x1, -h, x1, h)
    p.line(x1, h, x1 - 8, h)                         # short backward stub
    _dlead(p, pins, x0, x1)
    add_outlets(p, pins)
    return p


def breakdown_bidir(pins):
    """Two breakdown (zener) diodes back-to-back; wide body, pins at +/-40."""
    p = Ppd()
    h = 13
    # left triangle -> right, right triangle -> left, shared centre bars
    p.polygon([(-26, -h), (-26, h), (0, 0)])
    p.polygon([(26, -h), (26, h), (0, 0)])
    p.line(0, -h, 0, h)                              # shared cathode line
    p.line(0, -h, -7, -h - 7)                        # zener flags
    p.line(0, h, 7, h + 7)
    for (x, y) in pins:
        if x < -26:
            p.line(x, 0, -26, 0)
        elif x > 26:
            p.line(26, 0, x, 0)
    add_outlets(p, pins)
    return p


def bidirectional_diode(pins):
    """Two antiparallel diodes stacked vertically (tall 40x80)."""
    p = Ppd()
    # upper diode points right, lower diode points left
    p.polygon([(-14, -38), (-14, -14), (12, -26)])
    p.line(12, -38, 12, -14)
    p.polygon([(14, 14), (14, 38), (-12, 26)])
    p.line(-12, 14, -12, 38)
    # side rails connecting to the two terminals
    p.line(-14, -26, -20, -26)
    p.line(-20, -26, -20, 0)
    p.line(12, -26, 12, 0)                           # not needed but harmless
    for (x, y) in pins:
        p.line(x, 0, x * 0.6, 0)
    # vertical bus bars tying both diodes to each terminal
    p.line(-20, -38, -20, 38)
    p.line(20, -38, 20, 38)
    p.line(-20, 0, -14, 0)
    add_outlets(p, pins)
    return p


def diac(pins):
    """Diac = bidirectional trigger diode: two antiparallel triangles with a
    central breakdown bar (tall 40x80)."""
    p = Ppd()
    p.line(0, -34, 0, 34, lw=6)                      # central bar
    p.polygon([(-16, -34), (-16, -6), (0, -20)])     # upper tri -> centre
    p.polygon([(16, 6), (16, 34), (0, 20)])          # lower tri -> centre
    p.line(-20, -20, 0, -20)
    p.line(20, 20, 0, 20)
    p.line(-20, -34, -20, 34)                        # left bus
    p.line(20, -34, 20, 34)                          # right bus
    for (x, y) in pins:
        p.line(x, 0, (20 if x > 0 else -20), 0)
    add_outlets(p, pins)
    return p


# ---------------------------------------------------------------------------
# Transmission inner graphics (drawn inside a dl.body_rect)
# ---------------------------------------------------------------------------

def _poly_rel(p, cx, cy, xw, yh, pts, lw=4):
    p.polyline([(cx + ux * xw, cy + uy * yh) for (ux, uy) in pts], lw)


def filter_curve(kind):
    """Idealised amplitude/frequency characteristic inside the body rect
    (top = pass, bottom = stop; left = low freq)."""
    shapes = {
        "low":  [(-1, -1), (0.1, -1), (0.5, 1), (1, 1)],
        "high": [(-1, 1), (-0.5, 1), (-0.1, -1), (1, -1)],
        "band": [(-1, 1), (-0.5, 1), (-0.2, -1), (0.2, -1), (0.5, 1), (1, 1)],
        "stop": [(-1, -1), (-0.5, -1), (-0.2, 1), (0.2, 1), (0.5, -1), (1, -1)],
    }

    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        xw = min((r - l) * 0.34, 42)
        yh = min((b - t) * 0.26, 34)
        if kind == "gen":
            sine(p, cx, cy, half=xw, amp=yh)
        else:
            _poly_rel(p, cx, cy, xw, yh, shapes[kind])
    return f


def transfer_curve(kind):
    """Input/output transfer characteristic for limiters & clippers, drawn with
    a small reference cross."""
    shapes = {
        "pos":  [(-1, 1), (0.2, -1), (1, -1)],           # clip positive peaks
        "neg":  [(-1, 1), (-0.2, 1), (1, -1)],           # clip negative peaks
        "base": [(-1, 0), (0, 0), (1, -1)],              # base limiter
        "both": [(-1, 1), (-0.5, 1), (0.3, -1), (1, -1)],  # amplitude limiter
        "clip": [(-1, 1), (-0.5, 1), (0.3, -1), (1, -1)],
    }

    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        xw = min((r - l) * 0.32, 40)
        yh = min((b - t) * 0.22, 40)
        p.line(cx - xw, cy, cx + xw, cy, lw=2)           # freq/input axis
        p.line(cx, cy - yh, cx, cy + yh, lw=2)           # amplitude/output axis
        _poly_rel(p, cx, cy, xw, yh, shapes[kind])
    return f


def compander_curve(kind):
    """Compressor/expander and pre/de-emphasis slopes."""
    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        xw = min((r - l) * 0.32, 40)
        yh = min((b - t) * 0.26, 34)
        p.line(cx - xw, cy, cx + xw, cy, lw=2)
        p.line(cx, cy - yh, cx, cy + yh, lw=2)
        if kind == "compress":
            pts = [(-1, 1), (-0.3, -0.5), (1, -1)]       # concave (saturating)
        elif kind == "expand":
            pts = [(-1, 1), (0.3, 0.5), (1, -1)]         # convex
        elif kind == "pre":
            pts = [(-1, 0.6), (0.2, 0.3), (1, -1)]       # rising to HF
        else:  # de-emphasis
            pts = [(-1, -1), (-0.2, 0.3), (1, 0.6)]      # falling to HF
        _poly_rel(p, cx, cy, xw, yh, pts)
    return f


def saw_idt(n_sets):
    """Interdigital-transducer combs for SAW devices."""
    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        yh = (b - t) * 0.30
        p.line(cx - 40, cy - yh, cx - 40, cy + yh, lw=2)   # left bus
        p.line(cx - 20, cy - yh, cx - 20, cy + yh, lw=2)   # right bus of set 1
        for i, yy in enumerate((-yh * 0.5, yh * 0.1, yh * 0.7)):
            bus = cx - 40 if i % 2 else cx - 20
            p.line(bus, cy + yy, bus + (20 if i % 2 else -20), cy + yy, lw=2)
        if n_sets == 2:
            p.line(cx + 20, cy - yh, cx + 20, cy + yh, lw=2)
            p.line(cx + 40, cy - yh, cx + 40, cy + yh, lw=2)
            for i, yy in enumerate((-yh * 0.5, yh * 0.1, yh * 0.7)):
                bus = cx + 20 if i % 2 else cx + 40
                p.line(bus, cy + yy, bus + (20 if i % 2 else -20), cy + yy, lw=2)
    return f


def inner_modulator(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    k = min((r - l), (b - t)) * 0.22
    p.line(cx - k, cy - k, cx + k, cy + k)           # X (mixing)
    p.line(cx - k, cy + k, cx + k, cy - k)
    sine(p, cx, cy - (b - t) * 0.3, half=k, amp=k * 0.5)


def inner_artificial_line(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    # a small L-section: zigzag (inductor) + plate (capacitor)
    xs = [cx - 40, cx - 24, cx - 16, cx, cx + 16, cx + 24, cx + 40]
    ys = [cy, cy - 14, cy + 14, cy - 14, cy + 14, cy - 14, cy]
    p.polyline(list(zip(xs, ys)))
    p.line(cx + 40, cy + 6, cx + 40, cy + 30)
    p.line(cx + 32, cy + 20, cx + 48, cy + 20)       # cap plate
    p.line(cx + 32, cy + 28, cx + 48, cy + 28)


def inner_square(amp_w, amp_h, periods=2):
    """A square-wave pictogram (chopper / pulse regenerator)."""
    def f(p, l, t, r, b):
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        w = min((r - l) * 0.34, amp_w)
        h = min((b - t) * 0.26, amp_h)
        step = 2 * w / (periods * 2)
        x = cx - w
        pts = [(x, cy + h)]
        up = True
        for _ in range(periods * 2 + 1):
            pts.append((x, cy - h if up else cy + h))
            x += step
            pts.append((x, cy - h if up else cy + h))
            up = not up
        p.polyline(pts)
    return f


def inner_balance(p, l, t, r, b):
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    k = min((r - l), (b - t)) * 0.26
    p.polygon([(cx - k, cy + k), (cx + k, cy + k), (cx, cy - k)])  # wedge
    p.line(cx - k * 1.4, cy - k, cx + k * 1.4, cy - k)            # beam


def inner_hybrid(p, cx, cy, r):
    """Hybrid transformer: two opposed winding arcs inside the circle."""
    p.arc(cx - r * 0.6, cy - r * 0.5, cx + 0, cy + r * 0.5,
          0, -r * 0.5, 0, r * 0.5)
    p.arc(cx + 0, cy - r * 0.5, cx + r * 0.6, cy + r * 0.5,
          0, r * 0.5, 0, -r * 0.5)


def generator_box(pins, w, h, wave):
    """Signal generator: rect with 'G' (upper) and its output waveform (lower)."""
    from draw_lib import pin_center, rect_leads
    p = Ppd()
    cx, cy = pin_center(pins)
    l, t, r, b = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
    p.rect(l, t, r, b)
    p.text(cx, cy - h * 0.22, "G", size=60, al=9)
    wy = cy + h * 0.22
    ww = w * 0.3
    if wave == "sine":
        sine(p, cx, wy, half=ww, amp=h * 0.12)
    elif wave == "saw":
        p.polyline([(cx - ww, wy + h * 0.12), (cx - ww * 0.2, wy - h * 0.12),
                    (cx - ww * 0.2, wy + h * 0.12), (cx + ww * 0.6, wy - h * 0.12),
                    (cx + ww * 0.6, wy + h * 0.12)])
    else:  # pulse
        p.polyline([(cx - ww, wy + h * 0.12), (cx - ww, wy - h * 0.12),
                    (cx - ww * 0.3, wy - h * 0.12), (cx - ww * 0.3, wy + h * 0.12),
                    (cx + ww * 0.3, wy + h * 0.12), (cx + ww * 0.3, wy - h * 0.12),
                    (cx + ww, wy - h * 0.12), (cx + ww, wy + h * 0.12)])
    rect_leads(p, pins, l, t, r, b)
    return p
