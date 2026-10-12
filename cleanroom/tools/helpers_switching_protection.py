#!/usr/bin/env python3
"""Clean-room drawing helpers for the switching_protection batch.

Extra glyph builders (contacts, actuators, spark gaps, coil marks) that are
specific to EN/IEC 60617 section 07 switchgear + fuses/relays. draw_lib.py is
owned by the style lead and must not be edited, so batch-specific pieces live
here. Pure stdlib; operates on a draw_lib.Ppd instance. Coords 0.1 mm, y down.
"""
import math
import draw_lib as dl

CY = 0            # contact zone centre
GAP = 18          # half-height of the contact zone (fixed/moving contacts at +-18)


def semicircle(p, cx, cy, rad, a0, a1, lw=dl.STD_LW, n=14):
    """Arc as a sampled polyline (robust across the renderer). Angles in deg,
    math convention but y is DOWN, so +angle sweeps clockwise on screen."""
    pts = [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * t / n)),
            cy + rad * math.sin(math.radians(a0 + (a1 - a0) * t / n)))
           for t in range(n + 1)]
    p.polyline(pts, lw)


def v_leads(p, cx, y_top=-60, y_bot=60, top=-GAP, bot=GAP):
    """Two vertical terminal leads down to the contact zone."""
    p.line(cx, y_top, cx, top)
    p.line(cx, y_bot, cx, bot)


def blade_make(p, cx, reach, top=-GAP, bot=GAP):
    """NO blade: pivot at bottom (cx,bot), free tip up-right. Fixed contact =
    the top lead end (cx,top); open horizontal gap of `reach`. Returns tip."""
    p.line(cx, bot, cx + reach, top)
    return (cx + reach, top)


def blade_break(p, cx, reach, top=-GAP, bot=GAP):
    """NC blade: diagonal blade closed against a short fixed-contact bar at the
    top; the top lead jogs across to the bar. Returns the fixed-contact point."""
    tipx = cx + reach
    p.line(cx, bot, tipx, top)             # moving blade
    p.line(cx, top, tipx, top)             # fixed-contact bar (top lead jog)
    p.line(tipx, top - 7, tipx, top + 7)   # small perpendicular contact cap
    return (tipx, top)


def contactor_cup(p, x, y, down=True):
    """Small half-ring (contactor main contact) opening toward the gap."""
    if down:
        semicircle(p, x, y + 7, 9, 180, 360)
    else:
        semicircle(p, x, y - 7, 9, 0, 180)


def breaker_cross(p, x, y, s=7):
    """'x' at a fixed contact = circuit breaker."""
    p.line(x - s, y - s, x + s, y + s)
    p.line(x - s, y + s, x + s, y - s)


def disconnector_bar(p, x, y, s=11):
    """Short line across the fixed contact = disconnector (isolator)."""
    p.line(x - s, y, x + s, y)


def delay_cup(p, x, y, opening_up=True, rad=11):
    """Time-delay 'parachute/cup' on the blade."""
    if opening_up:
        semicircle(p, x, y, rad, 180, 360)   # ∪
    else:
        semicircle(p, x, y, rad, 0, 180)     # ∩


def auto_return(p, x, y):
    """Spring/automatic-return mark: a small open triangle (push-return)."""
    p.polyline([(x - 7, y + 8), (x, y - 6), (x + 7, y + 8)])


def passing_tri(p, x, y, up=True):
    """Passing/momentary contact mark: small filled triangle on the blade."""
    if up:
        p.polygon([(x, y - 8), (x - 6, y + 5), (x + 6, y + 5)], fill=True)
    else:
        p.polygon([(x, y + 8), (x - 6, y - 5), (x + 6, y - 5)], fill=True)


def early_late(p, x, y, early=True):
    """Lead/lag mark (07-04): short line parallel to the contact plane."""
    if early:
        p.line(x - 10, y - 4, x + 10, y - 4)
    else:
        p.line(x - 10, y + 4, x + 10, y + 4)


# --- operating-mechanism actuators (drawn at the top of the moving contact) --

def act_manual(p, x, y):
    """General manual control: a 'T' bar."""
    p.line(x - 14, y, x + 14, y)
    p.line(x, y, x, y + 14)


def act_pushbutton(p, x, y):
    """Push-button: two short bars (the button) on a stem."""
    p.line(x, y, x, y + 10)
    p.line(x - 14, y, x + 14, y)
    p.line(x - 14, y - 7, x + 14, y - 7)


def act_pull(p, x, y):
    """Pull switch: a circle on a stem."""
    p.circle(x, y - 8, 8)
    p.line(x, y, x, y + 10)


def act_turn(p, x, y):
    """Turn/rotary switch: a shallow arc with a stem."""
    semicircle(p, x, y - 2, 12, 200, 340)
    p.line(x, y, x, y + 10)


def act_mushroom(p, x, y):
    """Emergency-stop mushroom head: a wide cap with a concave top."""
    semicircle(p, x, y - 4, 20, 180, 360)   # cup (mushroom head underside)
    p.line(x - 20, y - 4, x + 20, y - 4)
    p.line(x, y - 4, x, y + 12)             # stem


def act_roller(p, x, y):
    """Position/limit switch: small circle (roller) on a stem."""
    p.circle(x, y - 9, 7)
    p.line(x, y - 2, x, y + 10)


def act_foot(p, x, y):
    """Foot-operated: a small pedal (open box tilted)."""
    p.polyline([(x - 14, y - 2), (x + 14, y - 10), (x + 14, y - 2)])
    p.line(x, y - 6, x, y + 10)


def mech_link(p, x1, y, x2):
    """Dashed mechanical coupling line between operating element and blade."""
    dl_ = 10
    t = x1
    step = 1 if x2 >= x1 else -1
    while (step > 0 and t < x2) or (step < 0 and t > x2):
        b = t + step * min(dl_ * 0.6, abs(x2 - t))
        p.line(t, y, b, y, lw=2)
        t += step * dl_


# --- spark gaps / arresters (ANSI protective devices, vertical) --------------

def gap_triangles(p, cx, gap=10):
    """Two filled triangles pointing at each other across a gap (spark gap)."""
    p.polygon([(cx - 16, -gap - 14), (cx + 16, -gap - 14), (cx, -gap)], fill=True)
    p.polygon([(cx - 16, gap + 14), (cx + 16, gap + 14), (cx, gap)], fill=True)


def plates(p, cx, half, gap=10):
    """Two parallel bars with a gap (capacitor-like block)."""
    p.line(cx - half, -gap, cx + half, -gap)
    p.line(cx - half, gap, cx + half, gap)
