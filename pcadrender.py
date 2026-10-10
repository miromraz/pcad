#!/usr/bin/env python3
"""Clean-room pure-Python renderer for ProfiCAD files (.sxe/.ppd/.picd).

Reproduces ProfiCAD's "Used Part of the Document" PNG export (10 px/mm, no
frame, white bg, aliased vector / antialiased text, ~21 px uniform margin).
SVG output is stdlib-only; PNG needs Pillow (imported lazily). See RE_NOTES.md.

Public entry: render(in_path, out_path, page=0, scale=10.0).
"""
import os, sys, math, base64, binascii, xml.etree.ElementTree as ET
import pcad   # reuse parsers: elem_xform, rotate, ic_pins, _collect_ppds, _csv, IC_P

MARGIN_MM = 2.1          # ~21 px at 10 px/mm (RE_NOTES Q1)
PAD = 400                # oversized-canvas padding in px (pens/text/arrows)
DEF_LW = 2               # geometry/wire default pen width (units=px); absent op-lw
                         # renders 2 px (measured against ProfiCAD refs)


# --- colour (RE_NOTES Q2) -------------------------------------------------

def col_bgr(v, default=(0, 0, 0)):
    """Decimal Windows COLORREF 0x00BBGGRR -> (r,g,b)."""
    if v is None or v == "":
        return default
    try:
        n = int(v)
    except ValueError:
        return default
    return (n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF)


def col_hex(s, default=(0, 0, 0)):
    """Text colour RRGGBB hex -> (r,g,b)."""
    if not s:
        return default
    s = s.strip().lstrip("#")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except (ValueError, IndexError):
        return default


def pen_width(el, default=DEF_LW):
    """op-lw in px; absent -> default. 0 is handled per-caller (hairline/none)."""
    w = el.get("op-lw")
    if w is None or w == "":
        return default
    try:
        return int(round(float(w)))
    except ValueError:
        return default


# --- arc sweep (RE_NOTES Q3) ----------------------------------------------

def arc_angles(bx, by, ex, ey):
    """Radial vectors (start bX/bY, end eX/eY, relative to ellipse centre) ->
    (start_deg, end_deg) for Pillow's clockwise, y-down arc/pieslice/chord.
    ProfiCAD sweeps counter-clockwise (visually) from the start radial to the
    end radial, i.e. Pillow draws clockwise from the END angle round to the
    START angle. [calibrated against golden/ref/probe_arc]."""
    a0 = math.degrees(math.atan2(by, bx))   # start radial
    a1 = math.degrees(math.atan2(ey, ex))   # end radial
    start, end = a1, a0
    while end <= start:
        end += 360.0
    return start, end


# --- font resolution ------------------------------------------------------

_FC_CACHE = {}
_FALLBACKS = [
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]


def _fc_match(face, bold, italic):
    key = (face, bold, italic)
    if key in _FC_CACHE:
        return _FC_CACHE[key]
    style = " ".join(s for s, f in (("Bold", bold), ("Italic", italic)) if f)
    pat = f"{face or 'Arial'}:style={style}" if style else (face or "Arial")
    path = None
    try:
        import subprocess
        r = subprocess.run(["fc-match", "-f", "%{file}", pat],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip() and os.path.isfile(r.stdout.strip()):
            path = r.stdout.strip()
    except Exception:
        pass
    if not path:
        path = next((p for p in _FALLBACKS if os.path.isfile(p)), None)
    _FC_CACHE[key] = path
    return path


def _load_font(face, bold, italic, px):
    from PIL import ImageFont
    px = max(1, int(round(px)))
    path = _fc_match(face, bold, italic)
    if path:
        try:
            return ImageFont.truetype(path, px)
        except Exception:
            pass
    return ImageFont.load_default()


# --- display list ---------------------------------------------------------
# An op is a dict in absolute unit coords; drawn later at scale*unit + offset.

def _pts(el):
    raw = el.get("pts") or ""
    nums = [float(v) for v in raw.split(",") if v.strip() != ""]
    return list(zip(nums[0::2], nums[1::2]))


def _fill_of(el, override):
    """Fill colour (r,g,b) or None. elem op-fd/op-fc override the symbol's."""
    fd = override.get("fd") if override.get("fd") is not None else el.get("op-fd")
    if fd != "1":
        return None
    fc = override.get("fc") if override.get("fc") is not None else el.get("op-fc")
    return col_bgr(fc, (0, 0, 0))


def _line_col(el, override):
    if override.get("c"):
        return col_bgr(override["c"])
    return col_bgr(el.get("op-lc"), (0, 0, 0))


def _box(el):
    return (float(el.get("left")), float(el.get("top")),
            float(el.get("right")), float(el.get("bottom")))


class Builder:
    def __init__(self, fonts, imgs):
        self.ops = []
        self.fonts = fonts        # role -> (size,bold,italic,underline,face,rgb)
        self.imgs = imgs          # guid -> PIL.Image
        self.warned = set()
        self.show_wire_name = False   # set from <NumberingWire ShowWireName>


    def warn(self, tag):
        if tag not in self.warned:
            self.warned.add(tag)
            print(f"pcadrender: skipping unknown element <{tag}>", file=sys.stderr)

    def add(self, **op):
        self.ops.append(op)

    # geometry under a transform T: localpoint -> absolute unit point
    def geom(self, el, T, override):
        tag = el.tag
        lw = pen_width(el)
        lc = _line_col(el, override)
        fill = _fill_of(el, override)
        if tag in ("polyline", "wire"):
            w = pen_width(el, DEF_LW)
            pts = [T(x, y) for x, y in _pts(el)]
            if len(pts) >= 2:
                self.add(k="line", pts=pts, lw=max(w, 1), lc=lc, closed=False)
            if tag == "wire":
                r = 6   # fixed dot radius (~12 px dia at 10 px/mm); measured from refs
                p = _pts(el)
                if el.get("drop1") == "1" and p:
                    self.add(k="disc", c=T(*p[0]), r=r, fill=lc)
                if el.get("drop2") == "1" and p:
                    self.add(k="disc", c=T(*p[-1]), r=r, fill=lc)
                if el.get("name") and self.show_wire_name and len(pts) >= 2:
                    self._wire_name(el.get("name"), pts)
        elif tag == "polygon":
            pts = [T(x, y) for x, y in _pts(el)]
            hatch = el.find("hatch")
            if len(pts) >= 2:
                self.add(k="poly", pts=pts, lw=lw, lc=lc, fill=fill,
                         nostroke=(el.get("op-lw") == "0" and fill is not None),
                         hatch=self._hatch(hatch, lc) if hatch is not None else None)
        elif tag == "rect":
            x0, y0, x1, y1 = _box(el)
            pts = [T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)]
            self.add(k="poly", pts=pts, lw=lw, lc=lc, fill=fill,
                     nostroke=(el.get("op-lw") == "0" and fill is not None),
                     hatch=None)
        elif tag == "roundRect":
            x0, y0, x1, y1 = _box(el)
            rx = float(el.get("rX") or el.get("rx") or 0)
            pts = [T(x0, y0), T(x1, y1)]
            self.add(k="rrect", pts=pts, rx=rx, lw=lw, lc=lc, fill=fill)
        elif tag == "ellipse":
            x0, y0, x1, y1 = _box(el)
            self.add(k="ellipse", pts=[T(x0, y0), T(x1, y1)], lw=lw, lc=lc, fill=fill)
        elif tag == "circle":
            cx, cy = float(el.get("centerx")), float(el.get("centery"))
            tx, ty = float(el.get("tangentx")), float(el.get("tangenty"))
            r = math.hypot(tx - cx, ty - cy)
            self.add(k="ellipse", pts=[T(cx - r, cy - r), T(cx + r, cy + r)],
                     lw=lw, lc=lc, fill=fill)
        elif tag in ("arc", "pie", "chord"):
            x0, y0, x1, y1 = _box(el)
            a0, a1 = arc_angles(float(el.get("bX")), float(el.get("bY")),
                                float(el.get("eX")), float(el.get("eY")))
            self.add(k=tag, pts=[T(x0, y0), T(x1, y1)], a0=a0, a1=a1,
                     lw=lw, lc=lc, fill=fill)
        elif tag == "polybezier":
            pts = _pts(el)
            flat = _flatten_bezier(pts)
            self.add(k="line", pts=[T(x, y) for x, y in flat], lw=lw, lc=lc, closed=False)
        elif tag == "junction":
            self.add(k="disc", c=T(float(el.get("x")), float(el.get("y"))),
                     r=6, fill=lc)
        elif tag == "img":
            self._img(el, T)
        elif tag == "text":
            self._text(el, T)
        elif tag in ("outlet", "hatch", "imgDesc", "defaults", "op", "parameter",
                     "parameters", "cell", "memo", "fixed", "label"):
            pass   # not drawn in export
        elif tag == "elem":
            self._elem(el, T)
        else:
            self.warn(tag)

    def _hatch(self, h, lc):
        return {"type": int(h.get("type", "0") or 0),
                "pen": max(int(float(h.get("penSize", "1") or 1)), 1),
                "spacing": max(float(h.get("spacing", "10") or 10), 1.0),
                "ox": float(h.get("offSetX", "0") or 0),
                "oy": float(h.get("offSetY", "0") or 0), "lc": lc}

    def _text(self, el, T, role=None, forced=None):
        body = forced if forced is not None else (el.text or "")
        if body == "":
            return
        f = (el.get("f") or "").split(",")
        if role and len(f) < 6:
            f = list(self.fonts.get(role, ("70", "0", "0", "0", "Arial", "000000")))
        size = float(f[0]) if f and f[0] else 70
        bold = len(f) > 1 and f[1] == "1"
        italic = len(f) > 2 and f[2] == "1"
        underline = len(f) > 3 and f[3] == "1"
        face = f[4] if len(f) > 4 else "Arial"
        rgb = col_hex(f[5]) if len(f) > 5 else (0, 0, 0)
        ax, ay = T(float(el.get("x")), float(el.get("y")))
        rot = int(el.get("a") or 0) / 10.0
        self.add(k="text", x=ax, y=ay, text=body, size=size, bold=bold,
                 italic=italic, underline=underline, face=face, rgb=rgb,
                 al=int(el.get("al") or 9), rot=rot)

    def _img(self, el, T):
        guid = el.get("lastGuid") or el.get("lG") or el.get("lGuid")
        im = self.imgs.get(guid)
        x0, y0, x1, y1 = _box(el)
        self.add(k="img", pts=[T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)],
                 im=im, keep=el.get("preserveAspect") == "1")

    def _elem(self, el, T, repo=None):
        repo = repo or self.repo
        sub = repo.get(el.get("lG") or el.get("lGuid"))
        if sub is None:
            return
        g = pcad.elem_xform(el)
        ox, oy = float(el.get("x", 0)), float(el.get("y", 0))

        def T2(x, y, _g=g, _ox=ox, _oy=oy, _T=T):
            gx, gy = _g(x, y)
            return _T(_ox + gx, _oy + gy)
        ov = dict(self._ov)
        if el.get("op-fd") is not None:
            ov["fd"] = el.get("op-fd")
        if el.get("op-fc") is not None:
            ov["fc"] = el.get("op-fc")
        if el.get("c"):
            ov["c"] = el.get("c")
        save = self._ov
        self._ov = ov
        self._walk_layers(sub, T2, repo)
        self._ov = save
        self._attributes(el, T)

    def _extent_rect(self, ax, ay, val, role, al):
        """A text's bounding rect (units) that counts toward the used-part bbox
        but is not drawn (hidden attribute). Vertical anchor is middle."""
        fdef = self.fonts.get(role, ("70", "0", "0", "0", "Arial", "000000"))
        f = _load_font(fdef[4], fdef[1] == "1", fdef[2] == "1",
                       float(fdef[0]) * 254.0 / 720.0)
        bb = f.getbbox(val)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        x0 = ax if al == 2 else (ax - w if al == 6 else ax - w / 2)
        self.add(k="erect", pts=[(x0, ay - h / 2), (x0 + w, ay + h / 2)])

    def _label_text(self, ax, ay, val, role, al):
        fdef = self.fonts.get(role, ("70", "0", "0", "0", "Arial", "000000"))
        self.add(k="text", x=ax, y=ay, text=val, size=float(fdef[0]),
                 bold=fdef[1] == "1", italic=fdef[2] == "1",
                 underline=fdef[3] == "1", face=fdef[4], rgb=col_hex(fdef[5]),
                 al=al, rot=0.0)

    def _wire_name(self, name, pts):
        """Draw a named wire's label at both ends (NumberingWire ShowWireName):
        above a horizontal wire (left-aligned at left end, right-aligned at
        right end); beside a vertical wire, rotated to run along it."""
        off = 20   # perpendicular offset from the wire (measured from refs)
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        if abs(x1 - x0) >= abs(y1 - y0):          # horizontal
            (lx, ly), (rx, ry) = ((x0, y0), (x1, y1)) if x0 <= x1 else ((x1, y1), (x0, y0))
            self._wire_label(lx + 2, ly - off, name, 2, 0)
            self._wire_label(rx - 2, ry - off, name, 6, 0)
        else:                                      # vertical: rotate 90 CW, left of wire
            (ty, tx), (by, bx) = ((y0, x0), (y1, x1)) if y0 <= y1 else ((y1, x1), (y0, x0))
            self._wire_label(tx - off, ty + 2, name, 2, 90)
            self._wire_label(bx - off, by - 2, name, 6, 90)

    def _wire_label(self, ax, ay, val, al, rot):
        fdef = self.fonts.get("text", ("70", "0", "0", "0", "Arial", "000000"))
        self.add(k="text", x=ax, y=ay, text=val, size=float(fdef[0]),
                 bold=fdef[1] == "1", italic=fdef[2] == "1", underline=False,
                 face=fdef[4], rgb=col_hex(fdef[5]), al=al, rot=float(rot))

    def _attributes(self, el, T):
        attrs = el.find("attributes")
        if attrs is not None:
            for a in attrs.findall("attribute"):
                if not a.get("value"):
                    continue
                role = {"_ref": "refs", "_type": "type"}.get(a.get("name", ""), "text")
                ax, ay, al = float(a.get("x", 0)), float(a.get("y", 0)), int(a.get("al") or 2)
                if a.get("v") == "0":
                    # hidden: not drawn, but ProfiCAD still counts its rect in the
                    # exported "used part" bbox. Record it as an extent-only op.
                    self._extent_rect(ax, ay, a.get("value"), role, al)
                else:
                    self._label_text(ax, ay, a.get("value"), role, al)
            return
        # legacy (v<7): <ref>/<type>/<value> child elements with x,y,v
        for tag, role in (("ref", "refs"), ("type", "type"), ("value", "text")):
            c = el.find(tag)
            if c is not None and c.get("v") == "1" and (c.text or "").strip():
                self._label_text(float(c.get("x", 0)), float(c.get("y", 0)),
                                 c.text.strip(), role, int(c.get("al") or 2))

    def _containers(self, node):
        """Visible drawable containers: modern <layers><layer v=1> or legacy
        <elements>."""
        layers = node.find("layers")
        if layers is not None:
            return [l for l in layers.findall("layer") if l.get("v") != "0"]
        els = node.find("elements")
        return [els] if els is not None else []

    def _walk_layers(self, node, T, repo=None):
        for layer in self._containers(node):
            for el in layer:
                if el.tag == "elem":
                    self._elem(el, T, repo)
                else:
                    self.geom(el, T, self._ov)

    # IC drawing (RE_NOTES Q7)
    def _ic(self, el, T):
        picd = el.find("picd")
        if picd is None:
            return
        g = pcad.elem_xform(el)
        ox, oy = float(el.get("x", 0)), float(el.get("y", 0))

        def TT(x, y):
            gx, gy = g(x, y)
            return T(ox + gx, oy + gy)
        H = int(picd.get("outlets_hor", "0") or 0)
        V = int(picd.get("outlets_ver", "0") or 0)
        P = pcad.IC_P
        halfW = 3 * P if H < 6 else ((H + 1) * P) // 2
        halfH = (V - 1) * (P // 2) + 2 * P
        fill = _fill_of(el, self._ov)
        lc = _line_col(el, self._ov)
        corners = [TT(-halfW, -halfH), TT(halfW, -halfH), TT(halfW, halfH), TT(-halfW, halfH)]
        self.add(k="poly", pts=corners, lw=2, lc=lc, fill=fill or (255, 255, 255),
                 nostroke=False, hatch=None)
        # mark notch (top-centre semicircle)
        if picd.get("mark") == "1":
            arc = [(-11, -halfH), (-10, -halfH + 12), (10, -halfH + 12), (11, -halfH)]
            self.add(k="line", pts=[TT(x, y) for x, y in _flatten_bezier(arc)],
                     lw=2, lc=lc, closed=False)
        if picd.get("ver_left") == "1":
            self.add(k="line", pts=[TT(-halfW + 44, -halfH), TT(-halfW + 44, halfH)],
                     lw=2, lc=lc, closed=False)
        if picd.get("ver_right") == "1":
            self.add(k="line", pts=[TT(halfW - 44, -halfH), TT(halfW - 44, halfH)],
                     lw=2, lc=lc, closed=False)
        # pins: numbers + names at each outlet, GetVyvody order
        pins, _, _ = pcad.ic_pins(picd)
        nfont = self.fonts.get("type", ("65", "0", "0", "0", "Arial", "000000"))
        onfont = self.fonts.get("outlets", ("70", "0", "0", "0", "Tahoma", "000000"))
        sides = []
        for num, nm, px, py in pins:
            side = "L" if px <= -halfW else ("R" if px >= halfW else ("T" if py <= -halfH else "B"))
            sides.append(side)
            self._pin_label(TT, px, py, side, num if not num.startswith("#") else "",
                            nfont, True)
            if nm:
                self._pin_label(TT, px, py, side, nm, onfont, False)
        # out_n_inv: 1-based pin indices drawn with an inversion circle (r=5) just
        # outside the body edge at that pin [BIN: My_Kruh].
        for s in pcad._csv(picd, "out_n_inv"):
            if s.isdigit() and 1 <= int(s) <= len(pins):
                _, _, px, py = pins[int(s) - 1]
                sd = sides[int(s) - 1]
                cx = px + (-5 if sd == "L" else 5 if sd == "R" else 0)
                cy = py + (-5 if sd == "T" else 5 if sd == "B" else 0)
                self.add(k="ellipse", pts=[TT(cx - 5, cy - 5), TT(cx + 5, cy + 5)],
                         lw=2, lc=lc, fill=None)
        # pos_hor section dividers: a short line from the pin's own body edge
        # inward at that pin's row (index is a global GetVyvody position).
        coords = pcad.ic_pin_coords(H, V)
        for s in pcad._csv(picd, "pos_hor"):
            if s.isdigit() and int(s) < len(coords):
                cx, cy = coords[int(s)]
                xe = -halfW if cx <= 0 else halfW
                self.add(k="line", pts=[TT(xe, cy), TT(xe + (44 if cx <= 0 else -44), cy)],
                         lw=2, lc=lc, closed=False)
        self._attributes(el, T)

    def _pin_label(self, TT, px, py, side, text, fdef, is_num):
        """Pin NUMBERS are drawn just inside the body edge at the pin row;
        pin NAMES just outside the edge, shifted ~P/2 down, in a smaller font
        [observed in ProfiCAD refs; QDocPic::Draw label loops]."""
        if not text:
            return
        size = float(fdef[0]) if is_num else float(fdef[0]) * 0.90   # names ~0.9x smaller than numbers (ref)
        if is_num:
            if side == "L":
                x, y, al = px + 5, py, 2
            elif side == "R":
                x, y, al = px - 5, py, 6
            else:
                x, y, al = px, py + (13 if side == "T" else -13), 9
        else:
            down = pcad.IC_P // 2
            if side == "L":
                x, y, al = px - 5, py + down, 6
            elif side == "R":
                x, y, al = px + 5, py + down, 2
            else:
                x, y, al = px, py + (-14 if side == "T" else 14), 9
        ax, ay = TT(x, y)
        self.add(k="text", x=ax, y=ay, text=text, size=size, bold=fdef[1] == "1",
                 italic=fdef[2] == "1", underline=False, face=fdef[4],
                 rgb=col_hex(fdef[5]), al=al, rot=0.0)

    def _walk_layers_page(self, page):
        for layer in self._containers(page):
            for el in layer:
                if el.tag == "elem":
                    self._elem(el, lambda x, y: (x, y))
                elif el.tag == "ic":
                    self._ic(el, lambda x, y: (x, y))
                else:
                    self.geom(el, lambda x, y: (x, y), {})


def _flatten_bezier(pts, steps=18):
    """Cubic Bézier chain (1 + 3k points) -> polyline."""
    if len(pts) < 4:
        return pts
    out = [pts[0]]
    i = 0
    while i + 3 < len(pts):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for s in range(1, steps + 1):
            t = s / steps
            u = 1 - t
            x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            out.append((x, y))
        i += 3
    return out


# --- document parsing -----------------------------------------------------

def _parse_fonts(root):
    f = root.find("fonts")
    roles = {}
    if f is not None:
        for role, v in f.attrib.items():
            roles[role] = v.split(",")
    return roles


def _parse_imgs(root):
    imgs = {}
    for d in root.iter("imgDesc"):
        guid = d.get("lastGuid") or d.get("lG") or d.get("lGuid")
        if not guid or not d.text:
            continue
        try:
            raw = base64.b64decode(d.text.strip())
            import io
            from PIL import Image
            imgs[guid] = Image.open(io.BytesIO(raw)).convert("RGBA")
        except (binascii.Error, OSError, ValueError):
            pass
    return imgs


def _repo(root):
    """document-wide {lG: <ppd>} for elem resolution (nested repos)."""
    return pcad._collect_ppds(root)


def build_ops(root, page_index):
    b = Builder(_parse_fonts(root), _parse_imgs(root))
    b.repo = _repo(root)
    b._ov = {}
    nw = root.find("NumberingWire")
    b.show_wire_name = nw is not None and nw.get("ShowWireName") == "1"
    dtype = root.get("type", "")
    pages = root.findall(".//page")
    if pages:                                   # modern multi-page .sxe
        b._walk_layers_page(pages[min(page_index, len(pages) - 1)])
    elif "picd" in dtype:                        # standalone IC
        ic = ET.Element("ic", {"x": "0", "y": "0"})
        ic.append(root.find(".//picd"))
        b._ic(ic, lambda x, y: (x, y))
    elif "ppd" in dtype:                         # standalone symbol
        b._walk_layers(root.find(".//ppd") or root, lambda x, y: (x, y), b.repo)
    elif root.find("layers") is not None or root.find("elements") is not None:
        b._walk_layers_page(root)                # legacy v<7 .sxe: page is a
    return b                                      # top-level <layers>/<elements>


# --- PNG rendering --------------------------------------------------------

def _extent(ops):
    xs, ys = [], []
    for op in ops:
        if op["k"] == "text":
            xs.append(op["x"]); ys.append(op["y"])
            continue
        pts = op.get("pts")
        if pts:
            xs += [p[0] for p in pts]; ys += [p[1] for p in pts]
        if op["k"] == "disc":
            cx, cy = op["c"]; xs += [cx - op["r"], cx + op["r"]]; ys += [cy - op["r"], cy + op["r"]]
    if not xs:
        return (0, 0, 1, 1)
    return (min(xs), min(ys), max(xs), max(ys))


def _text_anchor(al):
    """(horizontal, vertical) Pillow anchor letters from ProfiCAD al code.
    Oracle-probed (pcadrun.sh): vertical is always MIDDLE; horizontal is
    left for al=2, right for al=6, centre for al=9 / absent / other."""
    h = "l" if al == 2 else "r" if al == 6 else "m"
    return h, "m"


def render_png(ops, out_path, scale, warned):
    from PIL import Image, ImageDraw, ImageChops
    unit = scale / 10.0
    x0, y0, x1, y1 = _extent(ops)
    W = int((x1 - x0) * unit) + 2 * PAD
    Hh = int((y1 - y0) * unit) + 2 * PAD
    W = max(W, 2); Hh = max(Hh, 2)
    img = Image.new("RGB", (W, Hh), (255, 255, 255))
    d = ImageDraw.Draw(img)

    def P(p):
        return ((p[0] - x0) * unit + PAD, (p[1] - y0) * unit + PAD)

    def W_(w):
        return max(1, int(round(w * unit)))

    for op in ops:
        k = op["k"]
        if k == "line":
            pts = [P(p) for p in op["pts"]]
            d.line(pts, fill=op["lc"], width=W_(op["lw"]),
                   joint="curve" if len(pts) > 2 else None)
        elif k == "poly":
            pts = [P(p) for p in op["pts"]]
            if op.get("fill") is not None:
                d.polygon(pts, fill=op["fill"])
            if op.get("hatch"):
                _draw_hatch(d, img, pts, op["hatch"], unit, W_)
            if not op.get("nostroke"):
                d.line(pts + [pts[0]], fill=op["lc"], width=W_(op["lw"]), joint="curve")
        elif k == "rrect":
            (ax, ay), (bx, by) = P(op["pts"][0]), P(op["pts"][1])
            box = [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)]
            r = op["rx"] * unit
            if op.get("fill") is not None:
                d.rounded_rectangle(box, radius=r, fill=op["fill"])
            d.rounded_rectangle(box, radius=r, outline=op["lc"], width=W_(op["lw"]))
        elif k == "ellipse":
            (ax, ay), (bx, by) = P(op["pts"][0]), P(op["pts"][1])
            box = [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)]
            if op.get("fill") is not None:
                d.ellipse(box, fill=op["fill"])
            d.ellipse(box, outline=op["lc"], width=W_(op["lw"]))
        elif k in ("arc", "pie", "chord"):
            (ax, ay), (bx, by) = P(op["pts"][0]), P(op["pts"][1])
            box = [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)]
            if k == "pie":
                if op.get("fill") is not None:
                    d.pieslice(box, op["a0"], op["a1"], fill=op["fill"])
                d.pieslice(box, op["a0"], op["a1"], outline=op["lc"], width=W_(op["lw"]))
            elif k == "chord":
                if op.get("fill") is not None:
                    d.chord(box, op["a0"], op["a1"], fill=op["fill"])
                d.chord(box, op["a0"], op["a1"], outline=op["lc"], width=W_(op["lw"]))
            else:
                d.arc(box, op["a0"], op["a1"], fill=op["lc"], width=W_(op["lw"]))
        elif k == "disc":
            cx, cy = P(op["c"]); r = op["r"] * unit
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=op["fill"])
        elif k == "img":
            _draw_img(img, op, P)
        elif k == "text":
            _draw_text(img, d, op, P, unit)

    # crop to the used-part bbox + uniform margin. The used part is the drawn ink
    # unioned with extent-only rects (hidden attribute labels ProfiCAD still counts).
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).getbbox()
    if bbox is None:
        bbox = (PAD, PAD, PAD + 1, PAD + 1)
    for op in ops:
        if op["k"] == "erect":
            (ex0, ey0), (ex1, ey1) = P(op["pts"][0]), P(op["pts"][1])
            bbox = (min(bbox[0], ex0), min(bbox[1], ey0),
                    max(bbox[2], ex1), max(bbox[3], ey1))
    bbox = (int(bbox[0]), int(bbox[1]), int(math.ceil(bbox[2])), int(math.ceil(bbox[3])))
    m = int(round(MARGIN_MM * scale))
    crop = img.crop(bbox)
    out = Image.new("RGB", (crop.width + 2 * m, crop.height + 2 * m), (255, 255, 255))
    out.paste(crop, (m, m))
    if out_path.lower().endswith((".jpg", ".jpeg")):
        out.save(out_path, quality=95)
    else:
        out.save(out_path)


def _draw_text(img, d, op, P, unit):
    from PIL import Image, ImageDraw
    px = op["size"] * 254.0 / 720.0 * unit
    font = _load_font(op["face"], op["bold"], op["italic"], px)
    h, v = _text_anchor(op["al"])
    x, y = P((op["x"], op["y"]))
    if abs(op["rot"]) < 0.01:
        d.text((x, y), op["text"], font=font, fill=op["rgb"], anchor=h + v)
        if op["underline"]:
            bb = d.textbbox((x, y), op["text"], font=font, anchor=h + v)
            d.line([bb[0], bb[3], bb[2], bb[3]], fill=op["rgb"], width=max(1, int(px / 14)))
        return
    # rotated (a = clockwise tenths of a degree): render tight, rotate about the
    # align point, paste so that point lands at (x,y).
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = tmp.textbbox((0, 0), op["text"], font=font, anchor="lm")
    pad = 4
    tw, th = int(bb[2] - bb[0]) + 2 * pad, int(bb[3] - bb[1]) + 2 * pad
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((pad - bb[0], pad - bb[1]), op["text"], font=font,
                               fill=op["rgb"] + (255,), anchor="lm")
    # align point in the unrotated layer (left/centre/right, vertical middle)
    apx = pad + (tw - 2 * pad) * (0 if h == "l" else 0.5 if h == "m" else 1)
    apy = pad - bb[1]
    rot = layer.rotate(-op["rot"], expand=True, resample=Image.BICUBIC)
    th_r = math.radians(-op["rot"])
    cx0, cy0 = tw / 2, th / 2
    nax = (apx - cx0) * math.cos(th_r) - (apy - cy0) * math.sin(th_r) + rot.width / 2
    nay = (apx - cx0) * math.sin(th_r) + (apy - cy0) * math.cos(th_r) + rot.height / 2
    img.paste(rot, (int(x - nax), int(y - nay)), rot)


def _draw_img(img, op, P):
    if op.get("im") is None:
        return
    pts = [P(p) for p in op["pts"]]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bw, bh = int(max(xs) - min(xs)), int(max(ys) - min(ys))
    if bw < 1 or bh < 1:
        return
    im = op["im"]
    if op.get("keep"):
        r = min(bw / im.width, bh / im.height)
        nw, nh = max(1, int(im.width * r)), max(1, int(im.height * r))
        im = im.resize((nw, nh))
        ox = int(min(xs) + (bw - nw) / 2); oy = int(min(ys) + (bh - nh) / 2)
    else:
        im = im.resize((bw, bh)); ox, oy = int(min(xs)), int(min(ys))
    img.paste(im, (ox, oy), im)


def _draw_hatch(d, img, pts, h, unit, W_):
    """Fill a polygon with a line pattern, clipped by a polygon mask."""
    from PIL import Image, ImageDraw
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    mask = Image.new("1", img.size, 0)
    ImageDraw.Draw(mask).polygon(pts, fill=1)
    layer = Image.new("RGB", img.size, (255, 255, 255))
    ld = ImageDraw.Draw(layer)
    sp = max(h["spacing"] * unit, 2)
    w = W_(h["pen"])
    t = h["type"]
    if t in (0,):            # horizontal
        yy = y0
        while yy <= y1:
            ld.line([x0, yy, x1, yy], fill=h["lc"], width=w); yy += sp
    if t in (3,):            # vertical
        xx = x0
        while xx <= x1:
            ld.line([xx, y0, xx, y1], fill=h["lc"], width=w); xx += sp
    if t in (1, 4, 5):       # diagonal /
        c = x0 - (y1 - y0)
        while c <= x1 + (y1 - y0):
            ld.line([c, y1, c + (y1 - y0), y0], fill=h["lc"], width=w); c += sp
    if t in (2, 4, 5):       # diagonal \
        c = x0 - (y1 - y0)
        while c <= x1 + (y1 - y0):
            ld.line([c, y0, c + (y1 - y0), y1], fill=h["lc"], width=w); c += sp
    img.paste(layer, (0, 0), mask)


# --- SVG rendering (stdlib only) ------------------------------------------

def render_svg(ops, out_path, scale):
    unit = scale / 10.0
    x0, y0, x1, y1 = _extent(ops)
    m = MARGIN_MM * scale
    W = (x1 - x0) * unit + 2 * m
    Hh = (y1 - y0) * unit + 2 * m

    def P(p):
        return ((p[0] - x0) * unit + m, (p[1] - y0) * unit + m)

    def hexc(c):
        return "#%02x%02x%02x" % c
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{Hh:.0f}" '
           f'viewBox="0 0 {W:.0f} {Hh:.0f}">',
           f'<rect width="{W:.0f}" height="{Hh:.0f}" fill="#ffffff"/>']
    for op in ops:
        k = op["k"]
        sw = max(1, op.get("lw", 1) * unit) if "lw" in op else 1
        lc = hexc(op["lc"]) if "lc" in op else "#000000"
        fill = hexc(op["fill"]) if op.get("fill") is not None else "none"
        if k == "line":
            pts = " ".join(f"{P(p)[0]:.1f},{P(p)[1]:.1f}" for p in op["pts"])
            out.append(f'<polyline points="{pts}" fill="none" stroke="{lc}" '
                       f'stroke-width="{sw:.1f}" stroke-linejoin="round" stroke-linecap="round"/>')
        elif k == "poly":
            pts = " ".join(f"{P(p)[0]:.1f},{P(p)[1]:.1f}" for p in op["pts"])
            st = "none" if op.get("nostroke") else lc
            out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{st}" stroke-width="{sw:.1f}"/>')
        elif k in ("ellipse", "rrect"):
            (ax, ay), (bx, by) = P(op["pts"][0]), P(op["pts"][1])
            x, y, ww, hh = min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)
            if k == "ellipse":
                out.append(f'<ellipse cx="{x+ww/2:.1f}" cy="{y+hh/2:.1f}" rx="{ww/2:.1f}" '
                           f'ry="{hh/2:.1f}" fill="{fill}" stroke="{lc}" stroke-width="{sw:.1f}"/>')
            else:
                r = op["rx"] * unit
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{ww:.1f}" height="{hh:.1f}" '
                           f'rx="{r:.1f}" fill="{fill}" stroke="{lc}" stroke-width="{sw:.1f}"/>')
        elif k in ("arc", "pie", "chord"):
            out.append(_svg_arc(op, P, lc, fill, sw))
        elif k == "disc":
            cx, cy = P(op["c"]); r = op["r"] * unit
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{hexc(op["fill"])}"/>')
        elif k == "text":
            out.append(_svg_text(op, P, unit, hexc))
    out.append("</svg>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def _svg_arc(op, P, lc, fill, sw):
    (ax, ay), (bx, by) = P(op["pts"][0]), P(op["pts"][1])
    cx, cy = (ax + bx) / 2, (ay + by) / 2
    rx, ry = abs(bx - ax) / 2, abs(by - ay) / 2
    a0, a1 = math.radians(op["a0"]), math.radians(op["a1"])
    sx, sy = cx + rx * math.cos(a0), cy + ry * math.sin(a0)
    ex, ey = cx + rx * math.cos(a1), cy + ry * math.sin(a1)
    large = 1 if (op["a1"] - op["a0"]) % 360 > 180 else 0
    path = f"M{sx:.1f},{sy:.1f} A{rx:.1f},{ry:.1f} 0 {large} 1 {ex:.1f},{ey:.1f}"
    if op["k"] == "pie":
        path += f" L{cx:.1f},{cy:.1f} Z"
        return f'<path d="{path}" fill="{fill}" stroke="{lc}" stroke-width="{sw:.1f}"/>'
    if op["k"] == "chord":
        path += " Z"
        return f'<path d="{path}" fill="{fill}" stroke="{lc}" stroke-width="{sw:.1f}"/>'
    return f'<path d="{path}" fill="none" stroke="{lc}" stroke-width="{sw:.1f}"/>'


def _svg_text(op, P, unit, hexc):
    x, y = P((op["x"], op["y"]))
    px = op["size"] * 254.0 / 720.0 * unit
    anchor = {"l": "start", "m": "middle", "r": "end"}[_text_anchor(op["al"])[0]]
    wght = "bold" if op["bold"] else "normal"
    sty = "italic" if op["italic"] else "normal"
    tr = f' transform="rotate({op["rot"]:.1f} {x:.1f} {y:.1f})"' if op["rot"] else ""
    esc = (op["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    lines = esc.split("\n")
    spans = "".join(f'<tspan x="{x:.1f}" dy="{0 if i==0 else px:.1f}">{ln}</tspan>'
                    for i, ln in enumerate(lines))
    deco = ' text-decoration="underline"' if op["underline"] else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{px:.1f}" '
            f'font-family="{op["face"]},sans-serif" font-weight="{wght}" '
            f'font-style="{sty}" fill="{hexc(op["rgb"])}" text-anchor="{anchor}" '
            f'dominant-baseline="central"{deco}{tr}>{spans}</text>')


# --- public entry ---------------------------------------------------------

def render(in_path, out_path, page=0, scale=10.0):
    root = ET.parse(in_path).getroot()
    b = build_ops(root, page)
    ops = b.ops
    if out_path.lower().endswith(".svg"):
        render_svg(ops, out_path, scale)
    else:
        render_png(ops, out_path, scale, b.warned)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--scale", type=float, default=10.0)
    a = ap.parse_args()
    render(a.inp, a.out, a.page, a.scale)
