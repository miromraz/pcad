#!/usr/bin/env python3
"""Convert QElectroTech .elmt symbols to ProfiCAD .ppd symbols (stdlib only).

QElectroTech elements (https://github.com/qelectrotech/qelectrotech-elements,
CC-BY 3.0) are XML with px coordinates. ProfiCAD .ppd uses 0.1 mm units. See
../RE_NOTES.md for the .ppd document structure.

Scale factor: SCALE = 2.0 units per QET px. QET draws on a 10 px grid, so
10 px -> 20 units = ProfiCAD's 2 mm grid. Terminal points are snapped to the
nearest 20 units (2 mm) so every outlet lands on that grid even when QET places
a terminal 1 px beyond the lead; a short lead is drawn to bridge any residual
gap to the symbol body. Font point sizes map to ProfiCAD size via
size = round(pt * SCALE * 3.78) so text stays proportional to the scaled body.

Primitive mapping:
  <line>          -> <polyline> (2 pts)
  <rect>          -> <rect>  (left/top/right/bottom; rounded -> roundRect)
  <ellipse>       -> <ellipse>
  <circle>        -> <ellipse>
  <polygon>       -> <polygon> (closed) / <polyline> (closed="false")
  <arc>           -> <arc> (Qt start/angle -> ProfiCAD bX,bY,eX,eY radials)
  <text>          -> <text>
  <terminal>      -> <outlet> (ordered by QET document order)
  dynamic_text, uuid -> skipped

style: filling:black/white -> op-fd/op-fc ; line-weight -> op-lw ; color -> op-lc.

Usage:
  qet2ppd.py <src.elmt> <dst.ppd> [name]     convert one element
  qet2ppd.py --batch <manifest.tsv> <qetroot> <libroot>
        manifest lines: <src-relpath>\\t<dst-relpath-no-ext>\\t<name>
"""
import sys, os, math, uuid, xml.etree.ElementTree as ET

SCALE = 4.0                       # 0.1 mm units per QET px (10 px -> 4 mm; stays on
                                  # the 2 mm grid and matches ProfiCAD symbol sizes,
                                  # e.g. a 20 px meter circle -> 8 mm diameter)
GRID = 20                         # 2 mm outlet snap grid, in 0.1 mm units
NS = uuid.UUID("5d9b2a7e-1c3f-4a0b-9e8d-7f6a5b4c3d2e")   # for deterministic GUIDs

# Windows COLORREF (0x00BBGGRR) for op-lc/op-fc from a QET #RRGGBB / name.
_NAMED = {"black": 0, "white": 0xFFFFFF, "red": 0x0000FF, "green": 0x008000,
          "blue": 0xFF0000, "none": None}


def _colorref(qcolor):
    if not qcolor:
        return 0
    qcolor = qcolor.strip()
    if qcolor.lower() in _NAMED:
        return _NAMED[qcolor.lower()]
    if qcolor.startswith("#") and len(qcolor) >= 7:
        r = int(qcolor[1:3], 16); g = int(qcolor[3:5], 16); b = int(qcolor[5:7], 16)
        return (b << 16) | (g << 8) | r
    return 0


def _sc(v):
    """Scale a QET coord to 0.1 mm units, rounded to int."""
    return int(round(float(v) * SCALE))


def _snap(v, grid=GRID):
    return int(round(v / float(grid)) * grid)


def _style(el):
    """Parse QET style= into ProfiCAD op-* attribute string."""
    s = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            s[k.strip()] = v.strip()
    attrs = []
    # line colour
    lc = _colorref(s.get("color", "black"))
    if lc != 0:
        attrs.append(f'op-lc="{lc}"')
    # line weight -> op-lw (0.1 mm px). normal ~ default (2). thin/hair ~1, none ~0.
    lw = s.get("line-weight", "normal")
    wmap = {"none": "0", "thin": "1", "hair": "1", "normal": None, "normale": None}
    opw = wmap.get(lw, None)
    if lw not in wmap:              # numeric or 'eleve'/'bold'
        opw = "4" if lw in ("eleve", "bold", "thick") else None
    if opw is not None:
        attrs.append(f'op-lw="{opw}"')
    # fill
    fill = s.get("filling", "none")
    if fill and fill != "none":
        fc = _colorref(fill)
        if fc is not None:
            attrs.append('op-fd="1"')
            attrs.append(f'op-fc="{fc}"')
    return (" " + " ".join(attrs)) if attrs else ""


def _ptlist(coords):
    return "".join(f"{x},{y}," for x, y in coords)


def convert(src_path, name=None, standard=""):
    """Return (ppd_xml_string, n_outlets). Deterministic GUIDs from src relpath."""
    root = ET.parse(src_path).getroot()
    desc = root.find("description")
    if desc is None:
        raise ValueError(f"{src_path}: no <description>")
    body = []
    outlets = []          # (order, x, y) in 0.1 mm, pre-snap
    vertices = []         # all drawn geometry endpoints (for lead bridging)

    def addv(pts):
        vertices.extend(pts)

    for el in desc:
        tag = el.tag
        st = _style(el)
        if tag == "line":
            p = [(_sc(el.get("x1")), _sc(el.get("y1"))),
                 (_sc(el.get("x2")), _sc(el.get("y2")))]
            body.append(f'<polyline{st} pts="{_ptlist(p)}"/>')
            addv(p)
        elif tag == "rect":
            x, y = _sc(el.get("x")), _sc(el.get("y"))
            w, h = _sc(el.get("width")), _sc(el.get("height"))
            rx = float(el.get("rx") or 0)
            if rx > 0:
                body.append(f'<roundRect{st} left="{x}" top="{y}" right="{x+w}" '
                            f'bottom="{y+h}" rX="{_sc(el.get("rx"))}" rY="{_sc(el.get("ry") or el.get("rx"))}"/>')
            else:
                body.append(f'<rect{st} left="{x}" top="{y}" right="{x+w}" bottom="{y+h}"/>')
            addv([(x, y), (x + w, y + h)])
        elif tag == "ellipse":
            x, y = _sc(el.get("x")), _sc(el.get("y"))
            w, h = _sc(el.get("width")), _sc(el.get("height"))
            body.append(f'<ellipse{st} left="{x}" top="{y}" right="{x+w}" bottom="{y+h}"/>')
            addv([(x, y), (x + w, y + h)])
        elif tag == "circle":
            x, y = _sc(el.get("x")), _sc(el.get("y"))
            d = _sc(el.get("diameter"))
            body.append(f'<ellipse{st} left="{x}" top="{y}" right="{x+d}" bottom="{y+d}"/>')
            addv([(x, y), (x + d, y + d)])
        elif tag == "polygon":
            pts = []
            i = 1
            while el.get(f"x{i}") is not None:
                pts.append((_sc(el.get(f"x{i}")), _sc(el.get(f"y{i}"))))
                i += 1
            closed = (el.get("closed") != "false")
            body.append(f'<{"polygon" if closed else "polyline"}{st} pts="{_ptlist(pts)}"/>')
            addv(pts)
        elif tag == "arc":
            body.append(_arc(el, st))
            x, y = _sc(el.get("x")), _sc(el.get("y"))
            w, h = _sc(el.get("width")), _sc(el.get("height"))
            addv([(x, y), (x + w, y + h)])
        elif tag == "text":
            body.append(_text(el))
        elif tag == "terminal":
            outlets.append((len(outlets), _sc(el.get("x")), _sc(el.get("y")),
                            el.get("orientation", "n")))
        # dynamic_text, uuid, input, names, etc. -> skipped
    # outlets: snap to the 2 mm grid, but keep the raw point when snapping would
    # merge two distinct terminals (e.g. a lamp with both leads 4 px apart).
    snapped = [(_snap(ox), _snap(oy)) for _, ox, oy, _ in outlets]
    seen = {}
    for i, p in enumerate(snapped):
        seen.setdefault(p, []).append(i)
    out_xml = []
    for i, (_, ox, oy, ori) in enumerate(outlets):
        if len(seen[snapped[i]]) > 1:          # collision -> use raw scaled point
            sx, sy = ox, oy
        else:
            sx, sy = snapped[i]
        out_xml.append(f'<outlet x="{sx}" y="{sy}"/>')
        g = _nearest(vertices, (sx, sy))
        if g and g != (sx, sy) and math.hypot(g[0] - sx, g[1] - sy) <= 60:
            body.append(f'<polyline pts="{sx},{sy},{g[0]},{g[1]},"/>')
    rel = os.path.relpath(src_path)
    fG = uuid.uuid5(NS, "fG:" + rel)
    lG = uuid.uuid5(NS, "lG:" + rel)
    nm = name or _elem_name(root) or os.path.splitext(os.path.basename(src_path))[0]
    info = standard or _info(root)
    n_attr = f' n="{_xesc(info)}"' if info else ""
    head = (f'<document type="ProfiCAD ppd" version="10.0" t=""{n_attr} '
            f'fG="{fG}" lG="{lG}">')
    xml = "\n".join([head, '<layers current="0">', '<layer name="0" v="1">']
                    + body + out_xml + ['</layer>', '</layers>', '</document>', ''])
    return xml, len(outlets), nm


def _nearest(verts, pt):
    best, bd = None, 1e18
    for v in verts:
        d = (v[0] - pt[0]) ** 2 + (v[1] - pt[1]) ** 2
        if d < bd:
            best, bd = v, d
    return best


def _arc(el, st):
    """QET arc (bbox x,y,w,h + Qt start/angle deg) -> ProfiCAD arc with radials."""
    x, y = float(el.get("x")), float(el.get("y"))
    w, h = float(el.get("width")), float(el.get("height"))
    start = float(el.get("start", "0"))
    span = float(el.get("angle", "0"))
    cx, cy = x + w / 2, y + h / 2
    rx, ry = w / 2, h / 2

    def pt(theta):
        t = math.radians(theta)
        return (cx + rx * math.cos(t), cy - ry * math.sin(t))   # Qt: +angle CCW, y-down
    psx, psy = pt(start)
    pex, pey = pt(start + span)
    L, T = _sc(x), _sc(y)
    R, B = _sc(x + w), _sc(y + h)
    scx, scy = cx * SCALE, cy * SCALE
    bX, bY = int(round(psx * SCALE - scx)), int(round(psy * SCALE - scy))
    eX, eY = int(round(pex * SCALE - scx)), int(round(pey * SCALE - scy))
    return (f'<arc{st} left="{L}" top="{T}" right="{R}" bottom="{B}" '
            f'bX="{bX}" bY="{bY}" eX="{eX}" eY="{eY}"/>')


def _text(el):
    txt = el.get("text", "")
    if not txt:
        return ""
    xq, yq = float(el.get("x")), float(el.get("y"))
    font = (el.get("font") or "Arial,9").split(",")
    face = font[0] if font else "Arial"
    try:
        pt = float(font[1])
    except (IndexError, ValueError):
        pt = 9.0
    # QET glyphs are larger relative to their symbol than ProfiCAD's; this factor
    # scales a QET point size to a ProfiCAD size that matches (e.g. a meter "V"
    # ~3.4 mm in an 8 mm circle, like the old ProfiCAD voltmeter f="95").
    size = max(10, int(round(pt * SCALE * 2.0)))
    col = _colorref(el.get("color", "#000000"))
    hexc = "%06X" % ((col & 0xFF) << 16 | (col & 0xFF00) | (col >> 16))  # BGR->RRGGBB
    rot = el.get("rotation", "0")
    a = f' a="{int(round(float(rot) * 10))}"' if float(rot) else ""
    # QET static <text> (xq,yq) is Qt drawText's LEFT-BASELINE anchor (point size pt,
    # ~96 dpi). pcadrender anchors al=9 at the glyph box CENTRE with vertical middle,
    # so compute that centre: half the advance right of the left edge, ~0.35 em above
    # the baseline. (Advance ~0.6 em/char is a mono-ish estimate; good for 1-3 chars.)
    em = pt * 96.0 / 72.0
    cx = xq + 0.30 * em * len(txt)
    cy = yq - 0.35 * em
    x, y = int(round(cx * SCALE)), int(round(cy * SCALE))
    return f'<text x="{x}" y="{y}" f="{size},0,0,0,{face},{hexc}" al="9"{a}>{_xesc(txt)}</text>'


def _elem_name(root):
    names = root.find("names")
    if names is None:
        return None
    en = names.find("name[@lang='en']")
    if en is not None and en.text:
        return en.text
    first = names.find("name")
    return first.text if first is not None else None


def _info(root):
    inf = root.find("informations")
    if inf is not None and inf.text and "60617" in inf.text:
        return inf.text.strip().splitlines()[0]
    return ""


def _xesc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def convert_to(src_path, dst_path, name=None):
    xml, nout, nm = convert(src_path, name)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(xml)
    return nout, nm


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--batch":
        manifest, qetroot, libroot = sys.argv[2], sys.argv[3], sys.argv[4]
        ok = fail = 0
        with open(manifest, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                src = os.path.join(qetroot, parts[0])
                dst = os.path.join(libroot, parts[1] + ".ppd")
                name = parts[2] if len(parts) > 2 else None
                try:
                    n, nm = convert_to(src, dst, name)
                    print(f"OK  {parts[1]}  ({n} pins)")
                    ok += 1
                except Exception as e:
                    print(f"FAIL {parts[0]}: {e}", file=sys.stderr)
                    fail += 1
        print(f"\n{ok} converted, {fail} failed")
        return
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    n, nm = convert_to(src, dst, name)
    print(f"wrote {dst}: {n} outlets, name={nm!r}")


if __name__ == "__main__":
    main()
