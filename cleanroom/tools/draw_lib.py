#!/usr/bin/env python3
"""Clean-room EN 60617 .ppd drawing helpers (shared by all drawing teams).

Pure stdlib. Builds ProfiCAD .ppd XML (coords in 0.1 mm, y down, origin =
insertion point). See cleanroom/STYLE.md for the house style this encodes.

The `Ppd` builder wraps the primitives the renderer accepts (pcadrender.py):
polyline, polygon, rect, ellipse, circle, arc, text, outlet. Glyph helpers
(meter, energy_meter, converter, winding_*, generator, station, arrows, sine)
compose the EN 60617 families so teams reuse one scaled, pin-compatible set.
"""
import math
import uuid

# Fixed namespace for fG/lG (documented in STYLE.md §11).
NS = uuid.uuid5(uuid.NAMESPACE_DNS, "en60617.cleanroom.proficad")
STD_LW = 4          # standard body pen (0.4 mm)
LEAD = 40           # standard lead length


# Legacy Symbol-font letters still seen in this spec revision -> Greek. Only the
# three unambiguous ones in the meters batch (idempotent once the spec team ships
# real Greek: those tokens are already Greek and pass through unchanged). Do NOT
# add unit letters here (W=watt, h=hour, n, A, V ... must stay Latin).
SYMBOL_TO_GREEK = {"j": "φ", "q": "θ", "l": "λ"}
_GREEK = set("αβγδεηθλμπ"
             "ρστφχψωΩΦΔ")
_GLUE = {"cos", "sin", "tan", "max", "min"} | _GREEK


def marking_lines(tokens):
    """Group spec marking tokens into display lines (see Ppd.marking)."""
    toks = [SYMBOL_TO_GREEK.get(t, t) for t in tokens if t]
    lines = []
    trig = {"cos", "sin", "tan"}
    for t in toks:
        if lines and t in trig and lines[-1] in _GREEK:
            lines[-1] = t + " " + lines[-1]          # "cos φ", not "φ cos"
        elif lines and (t in _GLUE or (len(t) == 1 and t in _GREEK)):
            lines[-1] += " " + t
        else:
            lines.append(t)
    return lines


def lib_guid(rec_id):
    return str(uuid.uuid5(NS, rec_id))


def file_guid(rec_id):
    return str(uuid.uuid5(NS, "file:" + rec_id))


def slug_path(category, name):
    """<category>/<name>.ppd with '/' in the name flattened to '-'."""
    return f"{category}/{name.replace('/', '-')}.ppd"


def _xesc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _i(v):
    return int(round(v))


class Ppd:
    """Accumulates <layer> body elements, then serialises a full .ppd document."""

    def __init__(self):
        self.els = []       # geometry/text XML strings
        self.outs = []      # (x, y) outlets, in order

    # --- primitives -------------------------------------------------------
    def polyline(self, pts, lw=STD_LW):
        s = "".join(f"{_i(x)},{_i(y)}," for x, y in pts)
        self.els.append(f'<polyline pts="{s}" op-lw="{lw}"/>')
        return self

    def line(self, x1, y1, x2, y2, lw=STD_LW):
        return self.polyline([(x1, y1), (x2, y2)], lw)

    def polygon(self, pts, lw=STD_LW, fill=False):
        s = "".join(f"{_i(x)},{_i(y)}," for x, y in pts)
        f = ' op-fd="1"' if fill else ""
        self.els.append(f'<polygon pts="{s}" op-lw="{lw}"{f}/>')
        return self

    def rect(self, l, t, r, b, lw=STD_LW, fill=False):
        f = ' op-fd="1"' if fill else ""
        self.els.append(f'<rect left="{_i(l)}" top="{_i(t)}" right="{_i(r)}" '
                        f'bottom="{_i(b)}" op-lw="{lw}"{f}/>')
        return self

    def ellipse(self, l, t, r, b, lw=STD_LW, fill=False):
        f = ' op-fd="1"' if fill else ""
        self.els.append(f'<ellipse left="{_i(l)}" top="{_i(t)}" right="{_i(r)}" '
                        f'bottom="{_i(b)}" op-lw="{lw}"{f}/>')
        return self

    def circle(self, cx, cy, r, lw=STD_LW, fill=False):
        return self.ellipse(cx - r, cy - r, cx + r, cy + r, lw, fill)

    def dot(self, cx, cy, r=6):
        return self.ellipse(cx - r, cy - r, cx + r, cy + r, lw=2, fill=True)

    def arc(self, l, t, r, b, bX, bY, eX, eY, lw=STD_LW):
        self.els.append(f'<arc left="{_i(l)}" top="{_i(t)}" right="{_i(r)}" '
                        f'bottom="{_i(b)}" bX="{_i(bX)}" bY="{_i(bY)}" '
                        f'eX="{_i(eX)}" eY="{_i(eY)}" op-lw="{lw}"/>')
        return self

    def text(self, x, y, body, size=70, al=9):
        self.els.append(f'<text x="{_i(x)}" y="{_i(y)}" al="{al}" '
                        f'f="{size},0,0,0,Arial,000000">{_xesc(body)}</text>')
        return self

    def outlet(self, x, y):
        self.outs.append((_i(x), _i(y)))
        return self

    # --- centred marking block -------------------------------------------
    def marking(self, tokens, cx=0, cy=0, bodyw=80, bodyh=80, shape="rect"):
        """Lay out spec `markings` centred on (cx,cy), sized as large as fits
        INSIDE the body shape. Symbol-font letters are mapped to Greek; trig
        words and Greek modifiers are joined onto one line ("cos φ", "I sin φ"),
        while distinct quantity symbols stack ("W" / "var"). For shape="circle"
        each line must fit the circle's chord at its own vertical band (so wide
        markings like "cos φ"/"NaCl" never cross the rim). Anchors stay inside
        the body so they never enlarge the measured box (_ppd_box counts the
        anchor point). bodyw/bodyh = the body's full width/height."""
        lines = marking_lines(tokens)
        if not lines:
            return self
        n = len(lines)
        # Real text width in units ~ size * (254/720 px per size) * ~0.55 em/char.
        # The old model under-predicted width (~0.14/char) so wide markings such
        # as "USB" never shrank and overflowed a small rect; 0.20/char matches the
        # rendered Liberation/Arial advance so rect markings fit like circle ones.
        charw = 0.20      # drawn advance per char, in units per size value
        cap = 0.23        # cap height as a fraction of the size value
        size = min(0.80 * bodyh / (0.46 * n), 95.0)
        for _ in range(48):                      # shrink until every line fits
            step = min(size * 0.95, 0.8 * bodyh / n) if n > 1 else 0.0
            fits = True
            for i, s in enumerate(lines):
                y = -step * (n - 1) / 2.0 + i * step
                need = charw * size * len(s)
                if shape == "circle":
                    rr = bodyw / 2.0
                    band = abs(y) + cap * size * 0.5
                    avail = 2.0 * math.sqrt(max(rr * rr - band * band, 0.0)) * 0.80
                else:
                    avail = bodyw * 0.86
                if need > avail:
                    fits = False
                    break
            if fits:
                break
            size *= 0.92
        size = int(max(size, 18))
        step = min(size * 0.95, 0.8 * bodyh / n) if n > 1 else 0.0
        y0 = cy - step * (n - 1) / 2.0
        for i, s in enumerate(lines):
            self.text(cx, y0 + i * step, s, size=size, al=9)
        return self

    # --- serialise --------------------------------------------------------
    def document(self, name, designation, standard, rec_id):
        body = "\n".join(self.els)
        outs = "\n".join(f'<outlet x="{x}" y="{y}"/>' for x, y in self.outs)
        t = _xesc(designation or "")
        return (
            '<document type="ProfiCAD ppd" version="9.0">\n'
            f'<ppd name="{_xesc(name)}" t="{t}" v="" n="{_xesc(standard)}" '
            f'fG="{file_guid(rec_id)}" lG="{lib_guid(rec_id)}">\n'
            '<layers current="0"><layer name="0" v="1">\n'
            f'{body}\n{outs}\n'
            '</layer></layers>\n</ppd>\n</document>\n'
        )


# --- shared glyph helpers -------------------------------------------------

def arrowhead(p, x, y, ang_deg, length=14, halfw=6, lw=STD_LW):
    """Filled triangle head at (x,y) pointing along ang_deg (math angle, y-down)."""
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    bx, by = x - dx * length, y - dy * length
    p.polygon([(x, y), (bx + px * halfw, by + py * halfw),
               (bx - px * halfw, by - py * halfw)], lw=lw, fill=True)


def arrow(p, x1, y1, x2, y2, lw=STD_LW):
    """Shaft from (x1,y1) to (x2,y2) with a filled head at (x2,y2)."""
    p.line(x1, y1, x2, y2, lw)
    arrowhead(p, x2, y2, math.degrees(math.atan2(y2 - y1, x2 - x1)), lw=lw)


def sine(p, cx, cy, half=20, amp=12, lw=STD_LW):
    """Small ~ (one period sine) centred at (cx,cy), running horizontally."""
    pts = [(cx - half + 2 * half * t / 16.0, cy - amp * math.sin(2 * math.pi * t / 16.0))
           for t in range(17)]
    p.polyline(pts, lw)


def leads(p, pins, body_r):
    """Draw a straight lead from the body edge out to each outlet that lies
    beyond `body_r` from the origin along its own direction; always add the
    outlet. Pins on/inside the body radius get no separate lead."""
    for (x, y) in pins:
        d = math.hypot(x, y)
        if d > body_r + 1:
            ux, uy = x / d, y / d
            p.line(ux * body_r, uy * body_r, x, y)
        p.outlet(x, y)


def add_outlets(p, pins):
    for (x, y) in pins:
        p.outlet(x, y)


def pin_center(pins):
    if not pins:
        return 0.0, 0.0
    xs = [x for x, _ in pins]
    ys = [y for _, y in pins]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def rect_leads(p, pins, l, t, r, b):
    """Axis-aligned leads from a rectangle's edge out to each outlet."""
    for (x, y) in pins:
        if x > r + 1:
            p.line(r, y, x, y)
        elif x < l - 1:
            p.line(l, y, x, y)
        if y > b + 1:
            p.line(x, b, x, y)
        elif y < t - 1:
            p.line(x, t, x, y)
        p.outlet(x, y)


def meter(markings, pins, r=40):
    """Indicating instrument: circle r, centred, markings inside, leads to pins."""
    p = Ppd()
    p.circle(0, 0, r)
    leads(p, pins, r)
    p.marking(markings, bodyw=2 * r, bodyh=2 * r, shape="circle")
    return p


def body_rect(markings, pins, w, h, inner=None):
    """Rectangular body = the spec box (w×h) centred on the pin centroid, with
    axis-aligned leads to the pins and markings fitted inside. `inner(p,l,t,r,b)`
    draws extra geometry (dividers, diagonal) within the body."""
    p = Ppd()
    cx, cy = pin_center(pins)
    l, t, r, b = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
    p.rect(l, t, r, b)
    if inner:
        inner(p, l, t, r, b)
    rect_leads(p, pins, l, t, r, b)
    p.marking(markings, cx=cx, cy=cy, bodyw=w, bodyh=h)
    return p


# backwards-compatible name used by the generator
def energy_meter(markings, pins, w, h):
    return body_rect(markings, pins, w, h)
