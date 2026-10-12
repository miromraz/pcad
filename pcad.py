#!/usr/bin/env python3
"""Schematic picture generator for AI agents, on top of ProfiCAD's symbol library.

Subcommands:
  search <words...>        find library symbols (AND match on relative path)
  pins <symbol>            list a symbol's pins (.ppd: index,x,y; .picd: num,name,x,y)
  build <spec.json> <out.sxe>   generate a .sxe drawing from a JSON spec
  inspect <file.sxe>       summarise an existing ProfiCAD drawing (v7-v14)
  verify <spec.json> <file.sxe> | verify <file.sxe>
                           wiring check (ERC) on the drawing's geometry
  render <in.sxe|.ppd|.picd> <out.png|.svg> [--page N] [--scale PX_PER_MM]
                           draw it like ProfiCAD's export (PNG needs Pillow)
  import-lib [SRC] [DEST]  copy the stock symbol library from YOUR OWN ProfiCAD
                           install (default SRC: its "ProfiCAD Library" folder,
                           DEST: ~/.pcad/proficad-lib), then use it via PCAD_LIB
  selftest                 run internal asserts

A <symbol> is a library-relative path WITHOUT extension, e.g.
  "electronics/passive/resistors/resistor"  (use `search` to find the path)
  "ic/555"                                  (a .picd multi-pin IC)
The library root is the bundled lib/, or $PCAD_LIB if set.

Spec JSON (coords in mm):
  {
    "parts": [{"sym": "...", "ref": "R1", "val": "10k", "x": 40, "y": 20, "rot": 90}],
    "wires": [["R1.1", [40,10], "Q1.2"]],        # or {"pts":[...], "dots": false}
    "texts": [{"x": 10, "y": 5, "text": "note"}],
    "title": {"title": "...", "author": "...", "date": "...", "name": "..."}
  }
  "hide_ref": true on a part hides its ref label.
  "mirror": "x" flips a part left-right, "y" top-bottom (combinable with "rot").
  A wire dict may carry "name": "L1" (busbar; same-name wires are one net).
Wire points are [x_mm,y_mm] or "REF.pin": for a .ppd part "pin" is the 1-based
outlet index; for a .picd IC it is the printed pin NUMBER (out_d). Junction dots
are added automatically where a wire end meets another wire; "dots": false on a
wire disables them for that wire.

.ppd composite symbols (nested <repo>+<elem>) build with the repo copied verbatim;
their nested pins are resolved recursively (QDocPpd::GetOutlets order).
"""
import sys, os, json, math, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
# Symbol library. PCAD_LIB env var points at any ProfiCAD-format library
# (directory of .ppd/.picd); default = the bundled lib/ next to this script.
LIB = os.environ.get("PCAD_LIB") or os.path.join(HERE, "lib")
IC_P = 40   # IC pin pitch unit (0.1 mm), from decompiled QDocPic::GetVyvody

# Minimal ProfiCAD .sxe document header (our own; only the fields the renderer
# and ProfiCAD's loader need: font roles, white page, wire-name display).
HEADER = r'''<document type="ProfiCAD sxe" version="9.0">
<fonts letter="125,0,0,0,Arial,000000" text="70,0,0,0,Arial,000000" type="65,0,0,0,Arial,000000" refs="65,0,0,0,Arial,000000" cross_refs="70,0,0,0,Tahoma,000000" outlets="70,0,0,0,Tahoma,000000" reports="70,0,0,0,Tahoma,000000"/>
<PageSettings bgColor="FFFFFF" pgsHor="1" pgsVer="1" frame="YES" rastr="20"/>
<NumberingWire ShowWireName="1" Vertically="1"/>
<summary/>'''

# Page <summary> fields written to each page; values come from the spec "title".
SUMMARY_FIELDS = [
    ("title", ""), ("author", ""), ("date", ""), ("name", ""),
    ("revision", ""), ("subject", ""), ("keywords", ""), ("sheet", ""),
]


def page_summary(title):
    title = title or {}
    lines = ["<summary>"]
    for name, dflt in SUMMARY_FIELDS:
        lines.append(f'<field name="{name}" value="{xesc(title.get(name, dflt))}"/>')
    lines.append("</summary>")
    return "\n".join(lines)


def xesc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def resolve(sym):
    """Return absolute path to the .ppd/.picd for a library-relative symbol."""
    for ext in (".ppd", ".picd"):
        p = os.path.join(LIB, sym + ext)
        if os.path.isfile(p):
            return p
    sys.exit(f"error: symbol not found: {sym} (searched {LIB})")


def load_ppd(sym):
    """Parse a .ppd symbol -> (root, outlets[(x,y)], path)."""
    path = resolve(sym)
    if path.endswith(".picd"):
        sys.exit(f"error: {sym} is a .picd (IC) symbol; use IC pin numbers")
    doc = ET.parse(path).getroot()
    # Real ProfiCAD format wraps the symbol in <document><ppd>...; the simplified
    # bundled form puts <layers> directly on <document>. Use the <ppd> if present.
    root = doc if doc.find("ppd") is None else doc.find("ppd")
    outlets, _ = _ppd_box(root)   # walks all layers + nested composite parts
    return root, outlets, path


# --- IC (.picd) geometry --------------------------------------------------

def ic_pin_coords(H, V):
    """Pin positions (0.1 mm, relative to <ic> x,y) for positions k=0..2V+2H-1.
    Decompiled QDocPic::GetVyvody (common.dll); verified against the L200T sample.
    C integer division (truncate toward zero); all values here are non-negative."""
    P = IC_P
    halfW = 3 * P if H < 6 else ((H + 1) * P) // 2
    halfH = (V - 1) * (P // 2) + 2 * P
    pts = []
    for i in range(1, V + 1):            # left
        pts.append((-halfW, (i + 1) * P - halfH))
    for j in range(1, H + 1):            # bottom
        pts.append((j * P - halfW, halfH))
    for i in range(V, 0, -1):            # right
        pts.append((halfW, (i + 1) * P - halfH))
    for j in range(H, 0, -1):            # top
        pts.append((j * P - halfW, -halfH))
    return pts


def _csv(el, tag):
    """Comma-separated child text as a positional list ('' entries preserved)."""
    c = el.find(tag)
    txt = c.text if (c is not None and c.text) else ""
    return [v.strip() for v in txt.split(",")] if txt else []


def ic_pins(picd):
    """Return (pins, H, V): pins = [(number, name, x, y)], coords in 0.1 mm
    relative to the ic x,y. ProfiCAD's GetVyvody makes EVERY one of the 2V+2H
    positions a connection point; labels are display only. Library files are
    inconsistent about which of out_n/out_d holds the pin numbers, so the
    all-numeric one is the number list. A position with no number is
    addressable as "#<position>" (1-based)."""
    H = int(picd.get("outlets_hor", "0"))
    V = int(picd.get("outlets_ver", "0"))
    coords = ic_pin_coords(H, V)
    n, d = _csv(picd, "out_n"), _csv(picd, "out_d")
    isnum = lambda l: any(v for v in l) and all(v.isdigit() for v in l if v)
    nums, names = (n, d) if isnum(n) and not isnum(d) else (d, n)
    pins = []
    for k, (x, y) in enumerate(coords):
        num = nums[k] if k < len(nums) and nums[k] else f"#{k + 1}"
        name = names[k] if k < len(names) else ""
        pins.append((num, name, x, y))
    return pins, H, V


# --- geometry helpers -----------------------------------------------------

def rotate(x, y, deg):
    """ProfiCAD rotation: a=+900 maps outlet (0,4)->(4,0). Clockwise form."""
    if not deg:
        return x, y
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c + y * s, -x * s + y * c


def on_seg_interior(P, A, B):
    """True if integer point P lies strictly inside segment A-B (not an endpoint)."""
    px, py = P
    ax, ay = A
    bx, by = B
    if P == A or P == B:
        return False
    if (bx - ax) * (py - ay) - (by - ay) * (px - ax) != 0:   # not collinear
        return False
    return (min(ax, bx) <= px <= max(ax, bx)) and (min(ay, by) <= py <= max(ay, by))


def compute_drops(wires_pts, allow):
    """Per-wire (drop1, drop2): junction dot at a wire end where >=3 wire
    branches meet (a segment ending at the point = 1 branch, a segment passing
    through it = 2). Covers T-joins on a segment or on another wire's corner.
    allow[i]=False skips that wire."""
    segs = [(a, b) for pts in wires_pts for a, b in zip(pts, pts[1:]) if a != b]

    def dot(P):
        return sum(1 if P in (a, b) else 2 if on_seg_interior(P, a, b) else 0
                   for a, b in segs) >= 3

    return [(dot(pts[0]), dot(pts[-1])) if ok else (False, False)
            for pts, ok in zip(wires_pts, allow)]


def inner_xml(root):
    """Serialize the <repo>(if non-empty)+<layers> children of a ppd document."""
    out = []
    repo = root.find("repo")
    if repo is not None and len(repo):
        out.append(ET.tostring(repo, encoding="unicode"))
    layers = root.find("layers")
    if layers is not None:
        out.append(ET.tostring(layers, encoding="unicode"))
    return "".join(out)


# --- subcommands ----------------------------------------------------------

def cmd_search(words):
    words = [w.lower() for w in words]
    hits = []
    for dirpath, _, files in os.walk(LIB):
        for fn in files:
            if not fn.endswith((".ppd", ".picd")):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), LIB)
            relnoext = os.path.splitext(rel)[0].replace(os.sep, "/")
            if all(w in relnoext.lower() for w in words):
                hits.append(relnoext)
    for h in sorted(hits):
        print(h)
    if not hits:
        print("(no matches)", file=sys.stderr)


def cmd_pins(sym):
    path = resolve(sym)
    if path.endswith(".picd"):
        picd = ET.parse(path).getroot().find("picd")
        pins, _, _ = ic_pins(picd)
        if not pins:
            print("(IC has no numbered pins)", file=sys.stderr)
        for num, name, x, y in pins:
            print(f"{num}\t{name}\t{x/10:g}\t{y/10:g}")
    else:
        _, outlets, _ = load_ppd(sym)
        if not outlets:
            print("(symbol has no outlets)", file=sys.stderr)
        for i, (x, y) in enumerate(outlets, 1):
            print(f"{i}\t{x/10:g}\t{y/10:g}")


def cmd_build(spec_path, out_path):
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    parts = spec.get("parts", [])
    repo_ppds = {}   # lG -> (sym_name, root_attrib, inner_xml)
    placed = {}      # ref -> dict(kind=ppd|ic, ...)
    for p in parts:
        ref = p["ref"]
        path = resolve(p["sym"])
        if path.endswith(".picd"):
            picd = ET.parse(path).getroot().find("picd")
            pins, H, V = ic_pins(picd)
            placed[ref] = {"kind": "ic", "p": p, "picd": picd, "H": H, "V": V,
                           "pins": pins, "nummap": {n: (x, y) for n, _, x, y in pins}}
        else:
            root, outlets, _ = load_ppd(p["sym"])
            lg = root.get("lG")
            if not lg:
                sys.exit(f"error: symbol {p['sym']} has no lG GUID")
            if lg not in repo_ppds:
                repo_ppds[lg] = (p["sym"].replace("/", "\\") + ".ppd",
                                 root.attrib, inner_xml(root))
            placed[ref] = {"kind": "ppd", "p": p, "outlets": outlets, "lg": lg,
                           "box": _ppd_box(root)[1]}

    # --- repo block (ppd symbols only; ICs are inline) ---
    repo_lines = ["<repo>"]
    for lg, (name, attrib, inner) in repo_ppds.items():
        a = [f'name="{xesc(name)}"']
        for k in ("t", "v", "n", "m", "fG", "lG"):
            if attrib.get(k) is not None:
                a.append(f'{k}="{xesc(attrib[k])}"')
        repo_lines.append(f"<ppd {' '.join(a)}>{inner}</ppd>")
    repo_lines.append("</repo>")

    # --- elements ---
    def xy01(p):
        return int(round(p["x"] * 10)), int(round(p["y"] * 10))

    elem_lines = []
    for p in parts:
        e = placed[p["ref"]]
        x, y = xy01(p)
        rot = p.get("rot", 0)
        a_attr = f' a="{int(round(rot * 10))}"' if rot else ""
        mir = p.get("mirror")
        m_attr = ' v="1"' if mir == "x" else (' h="1"' if mir == "y" else "")
        val = p.get("val", "")
        vt = "1" if val else "0"
        rv = "0" if p.get("hide_ref") else "1"
        if e["kind"] == "ic":
            halfW = 3 * IC_P if e["H"] < 6 else ((e["H"] + 1) * IC_P) // 2
            halfH = (e["V"] - 1) * (IC_P // 2) + 2 * IC_P
            rx, ry = x - halfW, y - halfH - 25     # ref above-left of the box
            tx, ty = x - halfW, y + halfH + 10     # type below-left
            picd_xml = ET.tostring(e["picd"], encoding="unicode").strip()
            elem_lines.append(
                f'<ic name="" x="{x}" y="{y}"{a_attr}{m_attr}>\n'
                f'<attributes>\n'
                f'<attribute name="_ref" value="{xesc(p["ref"])}" v="{rv}" custom="" al="2" x="{rx}" y="{ry}"/>\n'
                f'<attribute name="_type" value="{xesc(val)}" v="{vt}" custom="" al="2" x="{tx}" y="{ty}"/>\n'
                f'</attributes>\n{picd_xml}\n</ic>')
        else:
            # Labels go just outside the drawn symbol, away from its leads:
            # right of it when the pins run vertically, else above/below.
            rx, ry, tx, ty = x + 20, y - 20, x + 20, y + 20
            if e["box"]:
                xe = {"a": a_attr and str(int(round(rot * 10))),
                      "v": "1" if mir == "x" else None, "h": "1" if mir == "y" else None}
                f = elem_xform(xe)
                bx0, by0, bx1, by1 = _xform_box(e["box"], x, y, f)
                op = [f(ox, oy) for ox, oy in e["outlets"]]
                vertical = (not op or max(py for _, py in op) - min(py for _, py in op)
                            >= max(px for px, _ in op) - min(px for px, _ in op))
                if vertical:
                    rx = tx = int(bx1) + 15
                else:
                    rx, ry, tx, ty = int(bx0), int(by0) - 25, int(bx0), int(by1) + 10
            elem_lines.append(
                f'<elem lGuid="{e["lg"]}" x="{x}" y="{y}"{a_attr}{m_attr}>\n'
                f'<attributes>\n'
                f'<attribute name="_ref" value="{xesc(p["ref"])}" v="{rv}" custom="" al="2" x="{rx}" y="{ry}"/>\n'
                f'<attribute name="_type" value="{xesc(val)}" v="{vt}" custom="" al="2" x="{tx}" y="{ty}"/>\n'
                f'</attributes>\n</elem>')

    # --- wires ---
    def pin_pos(ref, suf):
        if ref not in placed:
            sys.exit(f"error: wire references unknown part '{ref}'")
        e = placed[ref]
        p = e["p"]
        if e["kind"] == "ic":
            if suf not in e["nummap"]:
                sys.exit(f"error: IC {ref} has no pin '{suf}' "
                         f"(pins: {','.join(sorted(e['nummap']))})")
            ox, oy = e["nummap"][suf]
        else:
            idx = int(suf)
            outs = e["outlets"]
            if idx < 1 or idx > len(outs):
                sys.exit(f"error: {ref} has {len(outs)} pins; pin {idx} out of range")
            ox, oy = outs[idx - 1]
        mir = p.get("mirror")          # match elem_xform: mirror (v/h) then rotate
        fx, fy = (-1 if mir == "x" else 1), (-1 if mir == "y" else 1)
        rx, ry = rotate(ox * fx, oy * fy, p.get("rot", 0))
        return int(round(p["x"] * 10 + rx)), int(round(p["y"] * 10 + ry))

    def resolve_pt(pt):
        if isinstance(pt, str):
            ref, _, i = pt.rpartition(".")
            return pin_pos(ref, i)
        return int(round(pt[0] * 10)), int(round(pt[1] * 10))

    wire_specs = spec.get("wires", [])
    wires_pts, allow, wnames = [], [], []
    for w in wire_specs:
        isd = isinstance(w, dict)
        pts_in = w["pts"] if isd else w
        allow.append(w.get("dots", True) if isd else True)
        wnames.append(w.get("name") if isd else None)
        wires_pts.append([resolve_pt(pt) for pt in pts_in])

    drops = compute_drops(wires_pts, allow) if wires_pts else []
    wire_lines = []
    for pts, (d1, d2), nm in zip(wires_pts, drops, wnames):
        s = "".join(f"{x},{y}," for x, y in pts)
        attr = (' drop1="1"' if d1 else "") + (' drop2="1"' if d2 else "")
        if nm:
            attr += f' name="{xesc(nm)}"'
        wire_lines.append(f'<wire pts="{s}"{attr}/>')

    # --- texts (optional) ---
    text_lines = []
    for t in spec.get("texts", []):
        tx, ty = int(round(t["x"] * 10)), int(round(t["y"] * 10))
        text_lines.append(
            f'<text x="{tx}" y="{ty}" f="{int(t.get("size", 70))},0,0,0,Arial,{t.get("color", "000000")}" al="9">{xesc(t["text"])}</text>')

    body = "\n".join(repo_lines + [
        '<pages current="0">', '<page name="1">', '<tb use="1"/>',
        page_summary(spec.get("title")),
        '<layers current="1">', '<layer name="0" v="1">',
    ] + elem_lines + wire_lines + text_lines + [
        '</layer>', '</layers>', '</page>', '</pages>', '</document>'])

    content = HEADER + "\n" + body + "\n"
    with open(out_path, "w", encoding="utf-8", newline="\r\n") as f:   # ProfiCAD: UTF-8 CRLF
        f.write(content)
    ics = sum(1 for p in parts if placed[p["ref"]]["kind"] == "ic")
    print(f"wrote {out_path}: {len(parts)} parts ({ics} ICs), "
          f"{len(wires_pts)} wires, {len(repo_ppds)} symbols")


# --- inspect --------------------------------------------------------------

def _elem_label(e):
    ref = val = ""
    attrs = e.find("attributes")
    if attrs is not None:
        for a in attrs.findall("attribute"):
            if a.get("name") == "_ref":
                ref = a.get("value", "")
            elif a.get("name") == "_type":
                val = a.get("value", "")
    else:   # v7: <ref>/<type> child text
        r, t = e.find("ref"), e.find("type")
        if r is not None and r.text:
            ref = r.text
        if t is not None and t.text:
            val = t.text
    return ref, val


def _rot(e):
    a = e.get("a")
    return f" rot={int(a)/10:g}" if a else ""


def cmd_inspect(path):
    root = ET.parse(path).getroot()
    names = {}
    repo = root.find("repo")
    if repo is not None:
        for ppd in repo.findall("ppd"):
            if ppd.get("lG"):
                names[ppd.get("lG")] = ppd.get("name", "?")
    print(f"{os.path.basename(path)}  format {root.get('version')}  "
          f"symbols-in-repo {len(names)}")
    pages = root.findall(".//page")
    print(f"pages: {len(pages)}")
    for pi, page in enumerate(pages, 1):
        elems = page.findall(".//elem")
        ics = page.findall(".//ic")
        wires = page.findall(".//wire")
        texts = page.findall(".//text")
        print(f"  page {pi} ({page.get('name', '')}): "
              f"{len(elems)} symbols, {len(ics)} ICs, {len(wires)} wires, {len(texts)} texts")
        for e in elems:
            ref, val = _elem_label(e)
            sym = names.get(e.get("lGuid"), e.get("lGuid", "?"))
            print(f"    {ref or '-':<6} {val or '':<10} {sym}  "
                  f"@({int(e.get('x', 0))/10:g},{int(e.get('y', 0))/10:g})mm{_rot(e)}")
        for e in ics:
            ref, val = _elem_label(e)
            picd = e.find("picd")
            npins = len([n for n in _csv(picd, "out_d") if n]) if picd is not None else 0
            print(f"    IC {ref or '-':<6} {val or '':<10} {npins} pins  "
                  f"@({int(e.get('x', 0))/10:g},{int(e.get('y', 0))/10:g})mm{_rot(e)}")
        for t in texts:
            if t.text:
                print(f"    text @({int(t.get('x', 0))/10:g},{int(t.get('y', 0))/10:g})mm: {t.text!r}")


# --- ERC on .sxe geometry -------------------------------------------------

def elem_xform(e):
    """Local symbol coords -> offset from the elem origin: scale (sX/sY),
    mirror (v="1" flips x, h="1" flips y), then rotate (a, tenths of a degree)."""
    sx, sy = float(e.get("sX") or 1), float(e.get("sY") or 1)
    fx = -1 if e.get("v") == "1" else 1
    fy = -1 if e.get("h") == "1" else 1
    a = int(e.get("a") or 0) / 10.0
    return lambda x, y: rotate(x * sx * fx, y * sy * fy, a)


def _xform_box(box, ox, oy, f):
    """Axis-aligned bbox of a local box after elem_xform f + translation (0.1 mm)."""
    x0, y0, x1, y1 = box
    xs, ys = [], []
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        rx, ry = f(cx, cy)
        xs.append(ox + rx)
        ys.append(oy + ry)
    return (min(xs), min(ys), max(xs), max(ys))


def _collect_ppds(node):
    """{lG: <ppd>} for every <ppd> anywhere under node (nested repos); first wins."""
    m = {}
    for ppd in node.iter("ppd"):
        if ppd.get("lG"):
            m.setdefault(ppd.get("lG"), ppd)
    return m


def _geom_extent(el, xs, ys):
    """Accumulate a drawn element's extent into xs/ys (symbol-local 0.1 mm)."""
    g = el.get
    if g("pts"):
        nums = [int(float(v)) for v in g("pts").split(",") if v.strip() != ""]
        xs += nums[0::2]; ys += nums[1::2]
    for a in ("left", "right", "x1", "x2", "x", "cx"):
        if g(a) is not None:
            try: xs.append(int(g(a)))
            except ValueError: pass
    for a in ("top", "bottom", "y1", "y2", "y", "cy"):
        if g(a) is not None:
            try: ys.append(int(g(a)))
            except ValueError: pass
    if g("r") is not None and g("cx") is not None:
        try:
            r, cx, cy = int(g("r")), int(g("cx")), int(g("cy"))
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        except ValueError: pass


def _ppd_box(node, repo=None, depth=0):
    """(ordered outlets, drawn-bbox) of a <ppd>/<document> in symbol-local 0.1 mm.
    Mirrors QDocPpd::GetOutlets: walk ALL objects of ALL <layer>s in document
    order; an <outlet> adds its point; a nested <elem lGuid|lG=..> references a
    <ppd> in repo (its own/ancestor <repo>, possibly nested) and contributes that
    inner symbol's outlets+box recursively, transformed by the elem placement."""
    if repo is None:
        repo = _collect_ppds(node)
    outs, xs, ys = [], [], []
    layers = node.find("layers")
    if layers is not None:
        for layer in layers.findall("layer"):
            for el in layer:
                if el.tag == "outlet":
                    x, y = int(el.get("x")), int(el.get("y"))
                    outs.append((x, y)); xs.append(x); ys.append(y)
                elif el.tag == "elem" and depth < 16:
                    sub = repo.get(el.get("lGuid") or el.get("lG"))
                    if sub is None:
                        continue
                    so, sb = _ppd_box(sub, repo, depth + 1)
                    f = elem_xform(el)   # scale (trunc for int scale) -> mirror -> rotate
                    ox, oy = int(el.get("x", 0)), int(el.get("y", 0))
                    for lx, ly in so:
                        rx, ry = f(lx, ly)
                        outs.append((ox + int(round(rx)), oy + int(round(ry))))
                    if sb:
                        bx = _xform_box(sb, ox, oy, f)
                        xs += [bx[0], bx[2]]; ys += [bx[1], bx[3]]
                else:
                    _geom_extent(el, xs, ys)
    box = (min(xs), min(ys), max(xs), max(ys)) if xs and ys else None
    return outs, box


def _load_geometry(sxe):
    """Parse an .sxe into (parts, wires). parts: {ref, pins[(num,x,y)], box, npins};
    wires: list of point lists. All coords in 0.1 mm absolute."""
    root = ET.parse(sxe).getroot()
    repo = {}
    r = root.find("repo")
    if r is not None:
        allppd = _collect_ppds(root)   # document-wide, so nested parts resolve
        for ppd in r.findall("ppd"):
            if ppd.get("lG"):
                repo[ppd.get("lG")] = _ppd_box(ppd, allppd)
    parts, wires, texts, wnames = [], [], [], []
    page = root.find(".//page")
    if page is None:
        return parts, wires, texts, wnames
    for e in page.findall(".//elem"):
        x, y, f = int(e.get("x")), int(e.get("y")), elem_xform(e)
        ref, _ = _elem_label(e)
        outs, box = repo.get(e.get("lGuid") or e.get("lG"), ([], None))
        pins = [(str(i), x + int(round(f(ox, oy)[0])),
                 y + int(round(f(ox, oy)[1]))) for i, (ox, oy) in enumerate(outs, 1)]
        parts.append({"ref": ref or "?", "pins": pins,
                      "box": _xform_box(box, x, y, f) if box else None, "npins": len(outs)})
    for e in page.findall(".//ic"):
        x, y, f = int(e.get("x")), int(e.get("y")), elem_xform(e)
        ref, _ = _elem_label(e)
        picd = e.find("picd")
        pr, H, V = ic_pins(picd)
        pins = [(num, x + int(round(f(ox, oy)[0])),
                 y + int(round(f(ox, oy)[1]))) for num, _, ox, oy in pr]
        halfW = 3 * IC_P if H < 6 else ((H + 1) * IC_P) // 2
        halfH = (V - 1) * (IC_P // 2) + 2 * IC_P
        parts.append({"ref": ref or "IC", "pins": pins,
                      "box": _xform_box((-halfW, -halfH, halfW, halfH), x, y, f),
                      "npins": len(pr)})
    for w in page.findall(".//wire"):
        nums = [int(float(v)) for v in w.get("pts").split(",") if v.strip() != ""]
        wires.append(list(zip(nums[0::2], nums[1::2])))
        wnames.append(w.get("name"))   # named busbar -> labelled terminals + net merge
    texts += [(int(t.get("x", 0)), int(t.get("y", 0)))
              for t in page.findall(".//text") if (t.text or "").strip()]
    # Scaled symbols (sX/sY) put pins on fractional coords; ProfiCAD snaps
    # wires to them, so treat a wire vertex within 0.1 mm as exactly on the pin.
    # ponytail: O(pins*vertices) scan, fine for school-sized drawings.
    verts = [p for pts in wires for p in pts]
    for pt in parts:
        pt["pins"] = [(num, *next(((vx, vy) for vx, vy in verts
                                   if abs(vx - x) <= 1 and abs(vy - y) <= 1), (x, y)))
                      for num, x, y in pt["pins"]]
    return parts, wires, texts, wnames


def _seg_crosses_box(A, B, box, inset=1.0):
    """True if segment A-B overlaps the (inset) interior of box with positive length.
    Liang-Barsky clip against the inset rectangle."""
    x0, y0, x1, y1 = box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset
    if x1 <= x0 or y1 <= y0:
        return False
    ax, ay = A; dx, dy = B[0] - ax, B[1] - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                if t > t1: return False
                t0 = max(t0, t)
            else:
                if t < t0: return False
                t1 = min(t1, t)
    return t1 > t0


def _nets(parts, wires, wnames=None):
    """Nets (lists of REF.pin) connected through the wire geometry. Wires sharing
    a `name=` (busbars like L1/L2/L3) are one net, as in ProfiCAD."""
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    segs = []
    for pts in wires:
        for a, b in zip(pts, pts[1:]):
            if a != b:
                parent[find(a)] = find(b); segs.append((a, b))
    verts = {p for pts in wires for p in pts}
    for q in verts:
        for a, b in segs:
            if on_seg_interior(q, a, b):
                parent[find(q)] = find(a)
    byname = {}   # merge wires of the same name into one net
    for wi, pts in enumerate(wires):
        nm = wnames[wi] if wnames else None
        if nm and pts:
            byname.setdefault(nm, []).append(pts[0])
    for reps in byname.values():
        for p in reps[1:]:
            parent[find(reps[0])] = find(p)
    groups = {}
    for pt in parts:
        for num, x, y in pt["pins"]:
            P = (x, y)
            key = find(P) if P in verts else next(
                (find(a) for a, b in segs if on_seg_interior(P, a, b)), None)
            if key is not None:
                groups.setdefault(key, []).append(f"{pt['ref']}.{num}")
    return [sorted(set(v)) for v in groups.values()]


def _erc(parts, wires, texts=(), wnames=None):
    """Electrical-rule check on .sxe geometry. Returns (fails, warns, notes)."""
    fails, warns, notes = [], [], []
    LABEL_D = 100   # a wire end within 10 mm of a text label is a labelled terminal
    segs = [(wi, a, b) for wi, pts in enumerate(wires)
            for a, b in zip(pts, pts[1:]) if a != b]
    verts = [(wi, p, k in (0, len(pts) - 1))
             for wi, pts in enumerate(wires) for k, p in enumerate(pts)]
    allpins = [(pt["ref"], num, (x, y)) for pt in parts for (num, x, y) in pt["pins"]]
    pinset = {xy for _, _, xy in allpins}

    # (c) dangling wire ends: an end must touch a pin or another wire
    for wi, pts in enumerate(wires):
        for E in (pts[0], pts[-1]):
            if E in pinset:
                continue
            if any(swi != wi and p == E for swi, p, _ in verts):
                continue
            if any(swi != wi and on_seg_interior(E, a, b) for swi, a, b in segs):
                continue
            if any(abs(tx - E[0]) <= LABEL_D and abs(ty - E[1]) <= LABEL_D
                   for tx, ty in texts):
                notes.append(f"open terminal at ({E[0]/10:g},{E[1]/10:g}) "
                             "(near a text label)")
                continue
            if wnames and wnames[wi]:
                notes.append(f"open terminal at ({E[0]/10:g},{E[1]/10:g}) "
                             f"(named wire {wnames[wi]!r})")
                continue
            fails.append(f"dangling wire end at ({E[0]/10:g},{E[1]/10:g}) "
                         "(no pin or wire there)")

    # (b) a wire runs over a pin without terminating there
    for wi, pts in enumerate(wires):
        wends = {pts[0], pts[-1]}
        internal = set(pts[1:-1])
        wsegs = [(a, b) for a, b in zip(pts, pts[1:]) if a != b]
        for ref, num, P in allpins:
            if P in wends:
                continue
            if P in internal or any(on_seg_interior(P, a, b) for a, b in wsegs):
                fails.append(f"wire crosses pin {ref}.{num} at "
                             f"({P[0]/10:g},{P[1]/10:g}) without connecting there")

    # (a) a foreign wire crosses a symbol body (one it does not connect to).
    # Skip pin-less decorations (junction dots, logos) -- wires may sit on them.
    for pt in parts:
        if not pt["box"] or not pt["pins"]:
            continue
        ppins = [(x, y) for _, x, y in pt["pins"]]
        for wi, a, b in segs:
            # a wire touching any of this part's pins is connecting to it, not crossing
            if any(p == a or p == b or on_seg_interior(p, a, b) for p in ppins):
                continue
            if _seg_crosses_box(a, b, pt["box"]):
                fails.append(f"wire crosses {pt['ref']} body "
                             f"(segment ({a[0]/10:g},{a[1]/10:g})-({b[0]/10:g},{b[1]/10:g}))")
                break

    # (d) a wire END that lands inside a symbol's body but not on one of its pins
    # (e.g. a wire stopped next to a resistor instead of on its pin).
    for pt in parts:
        if not pt["box"] or not pt["pins"]:
            continue
        ppins = {(x, y) for _, x, y in pt["pins"]}
        x0, y0, x1, y1 = pt["box"][0] + 1, pt["box"][1] + 1, pt["box"][2] - 1, pt["box"][3] - 1
        for pts in wires:
            for E in (pts[0], pts[-1]):
                if E in ppins:
                    continue
                if x0 < E[0] < x1 and y0 < E[1] < y1:
                    fails.append(f"wire ends inside {pt['ref']} body at "
                                 f"({E[0]/10:g},{E[1]/10:g}) (not on a pin)")

    # unconnected pins: warn, but fail for a 1-pin symbol (ground/supply must connect)
    for pt in parts:
        unconn = []
        for num, x, y in pt["pins"]:
            P = (x, y)
            if any(p == P for _, p, _ in verts) or \
               any(on_seg_interior(P, a, b) for _, a, b in segs):
                continue
            unconn.append(f"{pt['ref']}.{num}")
        if unconn and pt["npins"] == 1:
            fails.append(f"1-pin symbol {unconn[0]} is unconnected")
        elif unconn:
            warns.append(f"{' '.join(unconn)} unconnected")
    return fails, warns, notes


def cmd_render(args):
    import argparse
    ap = argparse.ArgumentParser(prog="pcad.py render")
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--scale", type=float, default=10.0, help="px per mm (default 10)")
    a = ap.parse_args(args)
    import pcadrender
    pcadrender.render(a.inp, a.out, a.page, a.scale)


def cmd_verify(args):
    if len(args) == 2:
        _, sxe = args              # spec arg accepted but ERC uses the .sxe geometry
    elif len(args) == 1:
        sxe = args[0]
    else:
        sys.exit("usage: pcad.py verify <spec.json> <file.sxe> | verify <file.sxe>")
    if not os.path.exists(sxe):
        sys.exit(f"error: not found: {sxe}")

    fails, notes = [], []

    # ERC on the actual .sxe geometry (pure Python; no ProfiCAD/Wine needed)
    parts, wires, texts, wnames = _load_geometry(sxe)
    erc_fails, warns, erc_notes = _erc(parts, wires, texts, wnames)
    fails += erc_fails
    notes += erc_notes
    nets = _nets(parts, wires, wnames)
    print(f"ERC: {len(parts)} parts, {len(wires)} wires, {len(nets)} nets")
    for n in nets:
        print(f"  net: {', '.join(n)}")
    notes.append("ProfiCAD netlist is a paid-edition feature; connectivity from "
                 ".sxe pin/wire geometry")

    ok = not fails
    print("PASS" if ok else "FAIL")
    for f in fails:
        print(f"  FAIL: {f}")
    for w in warns:
        print(f"  warn: {w}")
    for n in notes:
        print(f"  note: {n}")
    sys.exit(0 if ok else 1)


# --- selftest -------------------------------------------------------------

def cmd_selftest():
    def rr(x, y, d):
        return tuple(round(v, 6) for v in rotate(x, y, d))
    assert rr(0, 4, 90) == (4.0, 0.0), rr(0, 4, 90)
    assert rr(0, 4, -90) == (-4.0, 0.0), rr(0, 4, -90)
    assert rr(0, 4, 0) == (0.0, 4.0)
    assert rr(2, 0, 180) == (-2.0, 0.0), rr(2, 0, 180)

    # IC pin geometry reproduces the L200T sample (origin 1160,380).
    coords = ic_pin_coords(5, 3)
    exp = {0: (1040, 340), 3: (1080, 500), 7: (1240, 500), 8: (1280, 420), 10: (1280, 340)}
    for k, (ex, ey) in exp.items():
        x, y = coords[k]
        assert (1160 + x, 380 + y) == (ex, ey), (k, 1160 + x, 380 + y)
    # 555: H=0,V=4 -> 8 pins on left/right only
    assert len(ic_pin_coords(0, 4)) == 8
    # IC rotation sign: 'two decades counter.sxe' IC at (700,620) a=900 (rot 90);
    # its first left pin k0=(-120,-120) must land on that wire endpoint (580,740).
    ox, oy = ic_pin_coords(3, 7)[0]
    rx, ry = rotate(ox, oy, 90)
    assert (700 + round(rx), 620 + round(ry)) == (580, 740), (ox, oy, rx, ry)

    # junction dots: T-junction, 3-way, and override
    T = [[(0, 0), (200, 0)], [(100, 0), (100, 100)]]
    d = compute_drops(T, [True, True])
    assert d[1][0] is True and d[0] == (False, False), d       # wire2 end on wire1 mid
    assert compute_drops(T, [True, False])[1] == (False, False)
    three = [[(0, 0), (100, 0)], [(100, 0), (100, 100)], [(100, 0), (200, 0)]]
    d3 = compute_drops(three, [True, True, True])
    assert d3[0][1] and d3[1][0] and d3[2][0], d3              # 3 ends meet -> dot
    corner = [[(0, 0), (100, 0)], [(100, 0), (100, 100)]]      # 2 ends = bend, no dot
    assert compute_drops(corner, [True, True]) == [(False, False), (False, False)]
    # pin numbers may live in out_n (7447 in 'two decades counter.sxe'): every
    # position is a pin; VCC "16" is position 18 (top side, middle).
    pc = ET.fromstring('<picd outlets_hor="3" outlets_ver="7"><out_n>7,1,2,6,,5,4,,,8,'
                       '14,15,9,10,11,12,13,16</out_n><out_d>A,B,C,D</out_d></picd>')
    pr, _, _ = ic_pins(pc)
    assert len(pr) == 20 and pr[17][0] == "16" and pr[4][0] == "#5", pr
    assert pr[17][2:] == (0, -200), pr[17]

    # composite pins (QDocPpd::GetOutlets): a repo pole (outlets (0,-60),(0,60))
    # placed by 3 nested <elem> at x=-40,0,40 -> 6 outlets, top-then-bottom per
    # pole in document order. (inline so the test needs no library file)
    comp = ET.fromstring(
        '<document><repo><ppd lG="POLE"><layers><layer>'
        '<outlet x="0" y="-60"/><outlet x="0" y="60"/>'
        '</layer></layers></ppd></repo><layers><layer>'
        '<elem lGuid="POLE" x="-40" y="0"/><elem lGuid="POLE" x="0" y="0"/>'
        '<elem lGuid="POLE" x="40" y="0"/></layer></layers></document>')
    br, _ = _ppd_box(comp)
    assert br == [(-40, -60), (-40, 60), (0, -60), (0, 60), (40, -60), (40, 60)], br

    # mirror: v="1" negates local x, h="1" negates y (elem_xform / build pin_pos).
    mf = elem_xform(ET.fromstring('<elem v="1"/>'))
    assert tuple(mf(4, 1)) == (-4, 1), mf(4, 1)
    mh = elem_xform(ET.fromstring('<elem h="1"/>'))
    assert tuple(mh(4, 1)) == (4, -1), mh(4, 1)

    corner = [[(0, 0), (100, 0), (100, 100)], [(100, 0), (200, 0)]]
    assert compute_drops(corner, [True, True])[1] == (True, False), corner

    # --- renderer pure functions (pcadrender) ---
    import xml.etree.ElementTree as _ET
    import pcadrender as R
    # colour: decimal COLORREF 0x00BBGGRR -> (R,G,B)
    assert R.col_bgr("255") == (255, 0, 0), R.col_bgr("255")
    assert R.col_bgr("65280") == (0, 255, 0)
    assert R.col_bgr("16711680") == (0, 0, 255)
    assert R.col_bgr(None) == (0, 0, 0)
    assert R.col_hex("FF0000") == (255, 0, 0)          # text colour is RRGGBB hex
    assert R.col_hex("008000") == (0, 128, 0)
    # pen width: default 2, explicit honoured, numeric string rounded
    assert R.pen_width(_ET.fromstring('<polyline/>')) == 2
    assert R.pen_width(_ET.fromstring('<polyline op-lw="10"/>')) == 10
    assert R.pen_width(_ET.fromstring('<rect op-lw="4.2"/>')) == 4
    # arc sweep: start radial east (bX>0), end radial south (eY>0) -> ProfiCAD
    # sweeps the long way; Pillow draws from end angle (90) round to start+360.
    s, e = R.arc_angles(10000, 0, 0, 10000)
    assert round(s) == 90 and round(e) == 360, (s, e)
    assert e > s, (s, e)

    print("selftest ok")


# Where ProfiCAD installs its symbol library (Windows, then Wine prefixes).
PROFICAD_LIB_DIRS = [
    r"C:\Users\Public\Documents\ProfiCAD Library",
    "~/.wine/drive_c/users/Public/Documents/ProfiCAD Library",
    "~/.wine/drive_c/users/Public/Documents/ProfiCAD library",
]


def cmd_import_lib(args):
    """Copy .ppd/.picd symbols from a local ProfiCAD install. The stock library
    is ProfiCAD's property: it is copied for your own use, never bundled here."""
    import shutil
    if len(args) > 2:
        sys.exit("usage: pcad.py import-lib [SRC] [DEST]")
    if args:
        src = os.path.expanduser(args[0])
    else:
        src = next((os.path.expanduser(d) for d in PROFICAD_LIB_DIRS
                    if os.path.isdir(os.path.expanduser(d))), None)
        if not src:
            sys.exit("ProfiCAD library not found; pass its folder as SRC "
                     "(normally C:\\Users\\Public\\Documents\\ProfiCAD Library)")
    if not os.path.isdir(src):
        sys.exit(f"not a directory: {src}")
    dest = os.path.expanduser(args[1] if len(args) > 1 else "~/.pcad/proficad-lib")
    n = 0
    for d, _, fs in os.walk(src):
        for f in fs:
            if f.endswith((".ppd", ".picd")):
                out = os.path.join(dest, os.path.relpath(d, src))
                os.makedirs(out, exist_ok=True)
                shutil.copy2(os.path.join(d, f), out)
                n += 1
    if not n:
        sys.exit(f"no .ppd/.picd symbols under {src}")
    print(f"copied {n} symbols from {src} to {dest}")
    print(f"use them with:  PCAD_LIB=\"{dest}\" python3 pcad.py search ...")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "search":
        if len(sys.argv) < 3:
            sys.exit("usage: pcad.py search <words...>")
        cmd_search(sys.argv[2:])
    elif cmd == "pins":
        if len(sys.argv) != 3:
            sys.exit("usage: pcad.py pins <symbol>")
        cmd_pins(sys.argv[2])
    elif cmd == "build":
        if len(sys.argv) != 4:
            sys.exit("usage: pcad.py build <spec.json> <out.sxe>")
        cmd_build(sys.argv[2], sys.argv[3])
    elif cmd == "inspect":
        if len(sys.argv) != 3:
            sys.exit("usage: pcad.py inspect <file.sxe>")
        cmd_inspect(sys.argv[2])
    elif cmd == "render":
        cmd_render(sys.argv[2:])
    elif cmd == "verify":
        cmd_verify(sys.argv[2:])
    elif cmd == "import-lib":
        cmd_import_lib(sys.argv[2:])
    elif cmd == "selftest":
        cmd_selftest()
    else:
        sys.exit(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
