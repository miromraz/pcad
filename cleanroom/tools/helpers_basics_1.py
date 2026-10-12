#!/usr/bin/env python3
"""Clean-room drawing helpers for the basics_1 batch (the most-used school
symbols: contacts, push buttons, switches, breakers, RCDs, machines,
transformers, logic gates).

Drawn from EN/IEC 60617 + the spec facts only. Builds on draw_lib.py (owned by
the style lead; not edited) and REUSES the switching_protection and
machines_power batch helpers so this family keeps the same look:
  * contacts / actuators / breaker-cross / disconnector-bar -> helpers_switching_protection
  * winding bumps / rotating-machine radius               -> helpers_machines_power
Pure stdlib. Coords 0.1 mm, y DOWN, origin = insertion point.
"""
import math
import draw_lib as dl
from draw_lib import Ppd
import helpers_switching_protection as sw
import helpers_machines_power as mp


# ---------------------------------------------------------------------------
# small shared primitives
# ---------------------------------------------------------------------------

def dashed_rect(p, l, t, r, b, dash=9, lw=2):
    """A rectangle outline drawn as a dash pattern (assembly / enclosure box)."""
    def seg(x0, y0, x1, y1):
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(length / dash))
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        d = 0.0
        while d < length:
            a = d
            bq = min(d + dash * 0.6, length)
            p.line(x0 + ux * a, y0 + uy * a, x0 + ux * bq, y0 + uy * bq, lw=lw)
            d += dash
    seg(l, t, r, t)
    seg(r, t, r, b)
    seg(r, b, l, b)
    seg(l, b, l, t)


def vdash(p, x, y0, y1, dash=9, lw=2):
    """Vertical dashed mechanical-coupling line from y0 to y1 at column x."""
    lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
    t = lo
    while t < hi:
        p.line(x, t, x, min(t + dash * 0.6, hi), lw=lw)
        t += dash


def thermal_hook(p, cx, cy, s=7, lw=dl.STD_LW):
    """EN thermal-effect mark: a right-angle bimetal hook inside the body."""
    p.line(cx - s, cy - s, cx + s, cy - s)
    p.line(cx + s, cy - s, cx + s, cy + s)


def pair_cols(pins):
    """Group pins into pole columns keyed by x; each -> (x, ytop, ybot)."""
    cols = {}
    for (x, y) in pins:
        cols.setdefault(x, []).append(y)
    out = []
    for x in sorted(cols):
        ys = cols[x]
        out.append((x, min(ys), max(ys)))
    return out


def gap_for(h):
    """Contact-zone half-height: 18 like the switching batch for h<=140,
    scaled up for the oversized (One Pole Switch, reed) symbols."""
    return 18 if h <= 150 else int(round(h * 0.14))


# ---------------------------------------------------------------------------
# contacts (single + multi pole), vertical orientation, pins top & bottom
# ---------------------------------------------------------------------------

def _pole_contact(p, cx, ytop, ybot, reach, gap, kind, is_break):
    """One vertical contact at column cx. kind in {make,break,breaker,
    disconnector,fuse_disc,contactor}. Returns the blade tip."""
    sw.v_leads(p, cx, ytop, ybot, top=-gap, bot=gap)
    if is_break:
        tip = sw.blade_break(p, cx, reach, top=-gap, bot=gap)
    else:
        tip = sw.blade_make(p, cx, reach, top=-gap, bot=gap)
    mx = cx + reach / 2.0
    if kind == "breaker":
        sw.breaker_cross(p, *tip)
    elif kind == "disconnector":
        sw.disconnector_bar(p, *tip)
    elif kind == "fuse_disc":
        sw.disconnector_bar(p, *tip)
        p.rect(mx - 7, -12, mx + 7, 12)          # fuse body on the blade
    elif kind == "contactor":
        sw.contactor_cup(p, *tip, down=not is_break)
    return tip


RIGHT_EXT = {"breaker": 8, "disconnector": 12, "fuse_disc": 12, "contactor": 0,
             "make": 0, "break": 0}


def contact(pins, w, h, kind="make", is_break=False, link=True, max_reach=None):
    """Generic 1..n pole vertical contact. Blade reach is chosen so the drawn
    box width equals the spec width; multiple poles get a dashed mechanical
    link across the blade tips. If max_reach is given and a full-width blade
    would exceed it (very wide single-pole switches), the blade keeps a clean
    ~30 deg angle and a right-hand operating handle fills the remaining width."""
    p = Ppd()
    cols = pair_cols(pins)
    xs = [c[0] for c in cols]
    span = max(xs) - min(xs)
    rext = RIGHT_EXT.get(kind, 0)
    reach = max(14, w - span - rext)
    handle_x = None
    if max_reach and reach > max_reach:
        reach = max_reach
        handle_x = min(xs) + w - 14
    gap = gap_for(h)
    tips = []
    for (cx, ytop, ybot) in cols:
        tips.append(_pole_contact(p, cx, ytop, ybot, reach, gap, kind, is_break))
    if handle_x is not None:
        sw.act_manual(p, handle_x, 0)
        sw.mech_link(p, tips[-1][0], 0, handle_x)
    elif link and len(cols) > 1:
        sw.mech_link(p, tips[0][0], tips[0][1], tips[-1][0])
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def actuated_contact(pins, w, h, actuator, hw, is_break=False):
    """Single-pole contact with an operating element (push/pull/turn/roller) on
    the LEFT, placed so the drawn box width equals the spec width."""
    p = Ppd()
    cx = pins[0][0]
    ys = [y for _, y in pins]
    gap = gap_for(h)
    reach = 22
    sw.v_leads(p, cx, min(ys), max(ys), top=-gap, bot=gap)
    if is_break:
        sw.blade_break(p, cx, reach, top=-gap, bot=gap)
    else:
        sw.blade_make(p, cx, reach, top=-gap, bot=gap)
    ax = cx + reach + hw - w                      # span == w
    sw.mech_link(p, cx, 0, ax)
    actuator(p, ax, -8)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def hpushbutton(pins, w, h, is_break):
    """Horizontal push-button contact: two terminals on one y-line, a make/break
    blade between them and a push-button head above. Extents tuned to spec box."""
    p = Ppd()
    xs = sorted(x for x, _ in pins)
    yc = pins[0][1]
    lx, rx = xs[0], xs[-1]
    gx = 13
    p.line(lx, yc, -gx, yc)                       # left terminal lead
    p.line(rx, yc, gx, yc)                        # right terminal lead
    if is_break:
        p.line(-gx, yc, gx, yc)                   # closed blade (horizontal)
        p.line(gx, yc - 8, gx, yc + 8)            # fixed-contact bar
        linky = yc
        bottom = yc + 8
    else:
        p.line(-gx, yc, gx - 4, yc - 16)          # open make blade (~30 deg)
        p.line(gx, yc - 9, gx, yc + 1)            # fixed contact
        linky = yc - 8
        bottom = yc
    # push-button head above, dashed linkage, sized so (top..bottom) == h
    top = bottom - h
    p.line(-10, top, 10, top)                      # button cap (topmost)
    p.line(0, top, 0, top + 10)                    # button stem
    p.line(-16, top + 10, 16, top + 10)            # button plate
    vdash(p, 0, top + 10, linky)                   # dashed mechanical linkage
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def reed(pins, w, h):
    """Reed switch: NO blade inside a glass-capsule ellipse."""
    p = Ppd()
    cx = pins[0][0]
    ys = [y for _, y in pins]
    gap = gap_for(h)
    sw.v_leads(p, cx, min(ys), max(ys), top=-gap, bot=gap)
    sw.blade_make(p, cx, max(8, int(w * 0.3)), top=-gap, bot=gap)
    p.ellipse(cx - w / 2.0, -gap - 14, cx + w / 2.0, gap + 14)   # glass capsule
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# change-over (SPDT)
# ---------------------------------------------------------------------------

def changeover(pins, w, h):
    """SPDT: common on one side, two throws on the other; blade to one throw."""
    p = Ppd()
    ys = [y for _, y in pins]
    cy = (min(ys) + max(ys)) / 2.0
    gap = gap_for(h)
    common = [(x, y) for (x, y) in pins if y > cy]
    throws = [(x, y) for (x, y) in pins if y < cy]
    if len(common) != 1:                          # fall back: pick the lone side
        common = [min(pins, key=lambda q: abs(q[0]))]
        throws = [q for q in pins if q not in common]
    cx = common[0][0]
    p.line(common[0][0], common[0][1], cx, gap)
    p.dot(cx, gap, 5)
    for (x, y) in throws:
        p.line(x, y, x, -gap)
    tgt = min(throws, key=lambda t: t[0])
    p.line(cx, gap, tgt[0], -gap)                 # blade to the left throw
    xs = [x for x, _ in pins]
    if w - (max(xs) - min(xs)) > 20:             # wide form: operating handle
        hx = min(xs) + w - 14
        sw.act_manual(p, hx, 0)
        sw.mech_link(p, cx, 0, hx)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def mom_off_mom(pins, w, h):
    """Momentary centre-off change-over: a single blade standing in the neutral
    centre between the two fixed contacts, with spring-return triangles at both
    momentary ends (consistent with the centre-off change-over)."""
    p = Ppd()
    ys = [y for _, y in pins]
    cy = (min(ys) + max(ys)) / 2.0
    gap = 14
    top = sorted([q for q in pins if q[1] < cy])  # two fixed contacts
    bot = sorted([q for q in pins if q[1] > cy])  # two commons -> pivot
    cxm = (min(x for x, _ in pins) + max(x for x, _ in pins)) / 2.0
    pivy = cy + gap
    for (x, y) in bot:                             # commons into the pivot
        p.line(x, y, cxm, pivy)
    p.dot(cxm, pivy, 4)
    p.line(cxm, pivy, cxm, cy - gap + 8)           # neutral blade (centre-off)
    for q in top:                                  # fixed contacts angled in
        sx = cxm + (9 if q[0] > cxm else -9)
        p.line(q[0], q[1], sx, cy - gap + 6)
        sw.auto_return(p, sx, cy - gap + 2)         # return spring at each end
    # operating knob above, sized so the box reaches spec height
    topy = max(ys) - h
    vdash(p, cxm, cy - gap + 8, topy + 2)
    p.line(cxm - 13, topy, cxm + 13, topy)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# rotary and slide switches
# ---------------------------------------------------------------------------

def rotary(pins, w, h):
    """Rotary selector: hub at the common terminal, open-circle fixed contacts
    at each way, a wiper arrow to the first way and an operating spindle sized
    so the drawn box fills the spec."""
    p = Ppd()
    common = pins[-1] if pins[-1] == (0, 0) else min(pins, key=lambda q: math.hypot(*q))
    ways = [q for q in pins if q != common]
    cxo, cyo = common
    p.dot(cxo, cyo, 3)
    for (x, y) in ways:                           # fixed-contact tick, inward
        d = math.hypot(x - cxo, y - cyo) or 1
        ux, uy = (cxo - x) / d, (cyo - y) / d
        p.line(x, y, x + ux * 9, y + uy * 9)
    w0 = ways[0]
    d = math.hypot(w0[0] - cxo, w0[1] - cyo) or 1
    dl.arrow(p, cxo, cyo, cxo + (w0[0] - cxo) * (d - 8) / d,
             cyo + (w0[1] - cyo) * (d - 8) / d)
    # spindle to the opposite (lower-right) quadrant, length set to fill the box
    xs = [x for x, _ in pins]
    ys = [y for _, y in pins]
    ex = min(xs) + 0.97 * w
    ey = min(ys) + 0.97 * h
    p.line(cxo, cyo, ex, ey, lw=2)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def slide(pins, w, h):
    """Multi-position slide switch: a terminal tick per pole, a slider rail and
    a sliding knob."""
    p = Ppd()
    ys = sorted(y for _, y in pins)
    px = pins[0][0]
    railx = 6
    for (x, y) in pins:
        p.line(x, y, railx, y)                    # terminal tick
    p.line(railx, ys[0], railx, ys[-1])           # rail
    midy = (ys[0] + ys[-1]) / 2.0
    p.rect(railx - 4, midy - 16, railx + 2, midy + 16)   # slider knob
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# logic gates (EN 60617-12)
# ---------------------------------------------------------------------------

def gate(pins, w, h, qual, negate=False):
    """Rectangular logic element: inputs on the left, output on the right,
    qualifying symbol centred, optional output negation bubble (NAND/INVERTOR)."""
    p = Ppd()
    out = max(pins, key=lambda q: q[0])
    ins = [q for q in pins if q != out]
    hw = 50
    bt, bb = -h / 2.0 + 10, h / 2.0 - 10
    p.rect(-hw, bt, hw, bb)
    for (x, y) in ins:
        p.line(x, y, -hw, y)
    if negate:
        p.circle(hw + 8, out[1], 8)
        p.line(hw + 16, out[1], out[0], out[1])
    else:
        p.line(hw, out[1], out[0], out[1])
    p.text(0, 0, qual, size=70, al=9)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# rotating machines, transformers, instrument transformers
# ---------------------------------------------------------------------------

def machine(pins, w, h, letter, current=None):
    """Rotating machine: circle with the machine letter; optional current-type
    sign (~ AC, = DC) below the letter."""
    p = Ppd()
    r = mp.pick_r(pins, w, h)
    p.circle(0, 0, r)
    dl.leads(p, pins, r)
    p.text(0, -18, letter, size=70, al=9)
    if current == "ac":
        dl.sine(p, 0, 24, half=16, amp=7)
    elif current == "dc":
        p.line(-16, 20, 16, 20)
        p.line(-16, 28, 16, 28)
    return p


def current_transformer(pins):
    """Ring-core current/pulse transformer: primary conductor through a toroid
    core circle, secondary terminal on the rim."""
    p = Ppd()
    ys = [y for _, y in pins]
    r = 40
    p.line(0, min(ys), 0, max(ys))               # primary conductor
    p.circle(0, 0, r)                            # core ring
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def transformer_2w_screen(pins):
    """Single-phase transformer, two windings (form 2 = linked semicircles) with
    an electrostatic screen between them."""
    p = Ppd()
    y0, y1 = -18, 18
    mp.winding_bumps_v(p, -14, y1, y0, 3, -10)   # left winding (bulge left)
    mp.winding_bumps_v(p, 14, y1, y0, 3, 10)     # right winding (bulge right)
    for (x, y) in pins:                          # leads from terminals to coil
        ax = -14 if x < 0 else 14
        p.line(x, y, ax, y)
    p.line(0, y0, 0, y1)                         # electrostatic screen
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def ssr(pins, w, h, markings):
    """Solid-state relay: a square with an isolation barrier, an input emitter
    (LED) and an output switch, terminal numbers by the pins."""
    p = Ppd()
    hw = w / 2.0
    hh = h / 2.0
    p.rect(-hw, -hh, hw, hh)
    p.line(0, -hh, 0, hh)                        # isolation barrier
    # input side: LED / diode emitter (triangle + cathode bar)
    p.polygon([(-50, -18), (-50, 22), (-20, 2)])
    p.line(-20, -18, -20, 22)
    # output side: a switch blade
    p.line(20, 24, 50, -24)
    p.line(20, 24, 20, 40)
    p.line(50, -24, 50, -40)
    # terminal numbers near each pin (markings follow pin order)
    for (x, y), m in zip(pins, markings):
        tx = x - 14 if x > 0 else x + 14
        p.text(tx, y, m, size=40, al=9)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# thermal overload relay / heater
# ---------------------------------------------------------------------------

def thermal(pins, w, h):
    """Thermal overload release (single element): a rectangle body (the heated
    element) in line with the terminals."""
    p = Ppd()
    cx = pins[0][0]
    ys = [y for _, y in pins]
    hw = max(13, min(w, 26) / 2.0)
    bt, bb = min(ys) + 8, max(ys) - 8
    p.rect(cx - hw, bt, cx + hw, bb)
    p.line(cx, min(ys), cx, bt)
    p.line(cx, bb, cx, max(ys))
    thermal_hook(p, cx, (bt + bb) / 2.0, s=min(hw - 3, 8))
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def thermal_multi(pins, w, h):
    """Thermal overload relay, n elements across an enclosing frame."""
    p = Ppd()
    cols = pair_cols(pins)
    ys = [y for _, y in pins]
    hw = w / 2.0
    p.rect(-hw, min(ys), hw, max(ys))
    for (cx, ytop, ybot) in cols:
        p.rect(cx - 10, ytop + 10, cx + 10, ybot - 10)
        p.line(cx, ytop, cx, ytop + 10)
        p.line(cx, ybot - 10, cx, ybot)
        thermal_hook(p, cx, (ytop + ybot) / 2.0, s=7)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


# ---------------------------------------------------------------------------
# RCD / RCBO module blocks and residual-current qualifier labels
# ---------------------------------------------------------------------------

def module_block(pins, w, h, magneto_thermal=False, markings=None):
    """Residual-current / combined RCBO block: dashed assembly enclosure sized
    to the spec box, a pole line per column through a differential sensing
    toroid, optional thermal+magnetic trip glyphs, terminal markings."""
    p = Ppd()
    cx0, cy0 = dl.pin_center(pins)
    l, t, r, b = cx0 - w / 2.0, cy0 - h / 2.0, cx0 + w / 2.0, cy0 + h / 2.0
    dashed_rect(p, l, t, r, b)
    cols = pair_cols(pins)
    xs = [c[0] for c in cols]
    for (cx, ytop, ybot) in cols:
        p.line(cx, ytop, cx, ybot)
        if magneto_thermal:
            p.rect(cx - 9, -26, cx + 9, -6)           # thermal element
            sw.semicircle(p, cx, 20, 11, 0, 180)      # magnetic release
    # differential sensing toroid crossing all poles
    if len(xs) > 1:
        p.ellipse(min(xs) - 12, -14, max(xs) + 12, 14, lw=2)
    if markings:
        for (x, y), m in zip(pins, markings):
            p.text(x, (t + 18) if y < cy0 else (b - 18), m, size=36, al=9)
    for (x, y) in pins:
        p.outlet(x, y)
    return p


def rcd_label(w, h, markings=None, kind=None):
    """A residual-current qualifier field: a frame with a centred marking, or a
    type-waveform pictogram (type AC / A / B)."""
    p = Ppd()
    l, t, r, b = -w / 2.0, -h / 2.0, w / 2.0, h / 2.0
    p.rect(l, t, r, b)
    if kind == "ac":                              # ~
        dl.sine(p, 0, 0, half=min(w * 0.33, 34), amp=14)
    elif kind == "a":                             # ~ over half-wave
        dl.sine(p, 0, -16, half=min(w * 0.33, 30), amp=10)
        _halfwave(p, 0, 16, min(w * 0.33, 30))
    elif kind == "b":                             # ~ / half-wave / DC
        dl.sine(p, -52, 0, half=22, amp=10)
        _halfwave(p, 0, 0, 22)
        p.line(44, -5, 84, -5)
        p.line(44, 5, 84, 5)
    elif markings:
        p.marking(markings, bodyw=w, bodyh=h)
    return p


def _halfwave(p, cx, cy, half):
    """Positive-only rectified humps (pulsating-DC qualifier)."""
    pts = []
    n = 24
    for i in range(n + 1):
        t = i / n
        x = cx - half + 2 * half * t
        s = math.sin(2 * math.pi * t * 2)
        y = cy - abs(s) * 11
        pts.append((x, y))
    p.polyline(pts)


# ---------------------------------------------------------------------------
# conductors / ducts (section 03)
# ---------------------------------------------------------------------------

def conductor(w, h):
    """General conductor: a single line segment filling the box diagonally."""
    p = Ppd()
    p.line(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    return p


def cable_duct(w, h):
    """Cable duct / conduit: a short channel (rectangle) with the conductor."""
    p = Ppd()
    p.rect(-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    p.line(-w / 2.0, 0, w / 2.0, 0)
    return p
