# ProfiCAD File-Format & PNG-Rendering Specification (clean-room RE notes)

Target: ProfiCAD 14.1.2 Home, `app/common.dll` (drawing + I/O) and `app/ProfiCAD.exe`
(UI, export command `0x8058` = Outputs -> Export to PNG). Goal: a clean-room Python
renderer that reproduces ProfiCAD's exported PNGs from the files the user owns.

Method key:
- **[BIN]** = decompiled from `common.dll` via Ghidra (REA). Addresses are RVA-style
  `0x180…` as reported by Ghidra.
- **[PROBE]** = measured empirically by rendering a hand-written `.sxe` with
  `pcadrun.sh png` (Wine, null graphics driver) and measuring the PNG with Pillow.
  Probe files/scripts in `/tmp/claude-1000/re_probe/`.
- **[XML]** = observed structurally across the 43 shipped sample `.sxe` files and the
  `.ppd/.picd` library.
- **[KNOWN]** = already established (pcad.py / MEMORY), cited not re-derived.

All coordinates in files are **0.1 mm units** unless noted. PNG export is **10 px/mm**,
so **1 file unit = 1 px**. [KNOWN]/[PROBE]

--------------------------------------------------------------------------------
## 1. Export pipeline (bounding box, margin, scale, background, AA, GDI)

- **Pixel scale = 10 px/mm = 1 px per 0.1 mm unit.** A `rect` of width 1000 units
  renders 1000 px of content. [PROBE: B rect 1000u -> ink width 1004 incl. 4u line]
- **Background = solid white** (`PageSettings/@bgColor="FFFFFF"`, COLORREF). Corner
  pixel (0,0) = (255,255,255). The page is opaque RGB (no alpha). [PROBE]
- **"Used part" bounding box + margin.** Export range in `pcadrun.sh` defaults to the
  Export dialog "Used Part of the Document" radio (control id 180; 179 = whole page,
  185 = whole + frame). The exported image = tight bounding box of **drawn ink**
  (including line half-widths) enlarged by a **uniform margin of ~21 px (≈2.1 mm)** on
  every side. [PROBE: solid 500x300 -> image 542x342, ink at px 21..520 and 21..320,
  i.e. 21 px each side]. Note the bbox is of rendered ink, so a thick pen pushes the
  bbox outward by half the pen width before the 21 px margin is added.
- **Antialiasing:** **Lines/strokes/fills are NOT antialiased** (aliased, hard pixels);
  **text IS antialiased** (ClearType/grayscale). [PROBE: 45° polyline -> 0 % non-
  black/white pixels; "Hg" text -> 43 % gray edge pixels]. A clean-room renderer should
  draw all vector geometry with antialiasing OFF and render glyphs with AA ON.
- **GDI, not GDI+.** All drawing is classic GDI on an MFC `CDC`: `CreatePen`,
  `CreateSolidBrush`, `CreatePolygonRgn`/`FillRgn`, `MoveTo`/`LineTo`, `Rectangle`,
  `Ellipse`, `PolyBezier`, `TextOut`. No `Graphics`/`GdiplusStartup` in the draw paths.
  This is why strokes are aliased. [BIN: `QDocPic::DrawOutlet`, `QUtilsDraw::Sipka*`,
  `QUtilsCElem::My_*` all call GDI `CDC` methods]
- Thumbnail/snippet path is `QuickPainter::Path2Image` [BIN 0x1800ce310], which
  dispatches on extension (`.ppd` / `.picd` / `.sxe`) and renders into a `CDC`; for
  `.sxe` it draws the current page (`+10` unit inset in that code path). The full-page
  PNG export uses the same page-draw virtuals.

--------------------------------------------------------------------------------
## 2. Pen, colour, fill, line type, arrows

### Pen width (`op-lw`)
- `op-lw` is a width in **0.1 mm units = pixels** at export scale. [PROBE]
  | op-lw | rendered stroke px |
  |-|-|
  | 2  | 2 |
  | 4  | 4 |
  | 10 | 10 |
  | 20 | 20 |
- **Default (attribute absent) = 2 (0.2 mm -> 2 px).** [PROBE: polyline w/o op-lw -> 2 px;
  rect w/o op-lw -> 2 px border]
- **`op-lw="0"`**: a *polyline* draws a 1 px cosmetic hairline; a *rect/closed-shape
  outline* with `op-lw="0"` draws **no border** (NULL pen). [PROBE: C rect lw0 -> no ink;
  LW0 polyline -> 1 px]. Treat 0 as "min hairline for open paths / no stroke for shape
  outlines"; a renderer can safely map 0 -> 1 px for open paths and skip the outline for
  filled shapes when the fill is present.
- IC body pen width = `round(2 * zoom_double)` where the zoom double lives at
  `param_3+0x30`; at export zoom this yields the symbol's nominal width. [BIN:
  `QDocPic::Draw` `CreatePen(0,width,color)`]

### Colour (`op-lc` line, `op-fc` fill)
- **Decimal Windows COLORREF (0x00BBGGRR).** Decode: `R = v & 0xFF`,
  `G = (v>>8) & 0xFF`, `B = (v>>16) & 0xFF`. [PROBE, exact]
  | op-fc | colour |
  |-|-|
  | 255 (0x0000FF) | red (255,0,0) |
  | 65280 (0x00FF00) | green (0,255,0) |
  | 16711680 (0xFF0000) | blue (0,0,255) |
- Default line colour when `op-lc` absent = **black (0)**. Fill colour default when
  `op-fc` absent but filled = black. [XML/PROBE]

### Fill (`op-fd`, `op-fc`)
- **`op-fd="1"` = filled** (the only value present); absent = not filled. When filled, a
  `CreateSolidBrush(op-fc)` is used; when not filled a NULL/hollow brush. [XML; BIN
  `QDocPic::Draw` branch on `param_5[8]` fill flag -> `CreateSolidBrush` vs stock brush]
- `op-fd` on `elem` (symbol instance) overrides the symbol's fill; `op-fc` on `elem`
  overrides fill colour (per-instance recolour). [XML: `elem … op-fd op-fc`]

### Line type (`op-at`) and `op-line-scale`
- `op-at` selects a dashed/line style; observed values `1,5,6,8,10,11,12`.
  `op-line-scale` (e.g. `0.200`..`2.000`) is the dash-period multiplier.
- **UNRESOLVED exactly:** at export resolution my probes rendered `op-at` 5/6/8/10/11/12
  (even at `op-line-scale` 2–5 and 1-px width) as **solid or near-solid** lines
  (longest black run ≈ full length). So either the dash period is large relative to the
  test line, or `op-at` dashing is applied through a path not exercised by a bare
  top-level polyline. Treat `op-at` as a dash-style id with `op-line-scale` as its
  period scale; **exact on/off pattern per id = unknown** (see §Unknowns). [PROBE D1–D4]

### `op-contour2`
- Not present in any shipped sample and not resolved in the pen path. Likely a
  double/contour outline flag. **UNKNOWN.** [XML: 0 occurrences]

### Line ends / arrows (`end`, `arrow_scale_x`, `arrow_scale_y`)
- On ordinary polylines/wires the only `end` values seen are `1` (1323x, the default)
  and `2` (96x). Probe polylines with `end=1,2,3,4,5,6` (even with `arrow_scale_x/y=4`)
  **all render as a plain line with NO arrowhead** -> **`end=` on a polyline/wire is NOT
  the ArrowType selector**; it is a plain line-ending/connection flag (default 1).
  Arrowheads come from dimension lines / `DimStyle` (and connector symbols), not from a
  polyline `end`. [PROBE AE2..AE6 all height ≈3 px]
- The real arrowhead geometry is `QUtilsDraw::SipkaFromPropertiesPanel` [BIN 0x1800d4f80]
  -> `SipkaWithoutStem` [BIN 0x1800d50c0], driven by an **ArrowType enum (5..13)** plus
  `arrow_scale_x` (longitudinal) and `arrow_scale_y` (lateral). The head is built from
  integer offsets scaled by the two factors and oriented by `RotateAndScale` along the
  line direction (defaults scale = 1.0 long, 0.5 lateral):
  | ArrowType | shape | key dimensions |
  |-|-|-|
  | 0 | none | — |
  | 5 | single barb (half arrow) | len 24·sx, lat 10·sy |
  | 6 / 13 | **filled solid triangle** (`CreatePolygonRgn`+`FillRgn`, line colour) | len 24·sx, barb 26·sx, lat via 24·sx |
  | 7 | open "crow’s-foot"/double stroke | len 6/10·sy, 40·sx |
  | 8 | long barb | 40·sx |
  | 9 | short barb | 14·sx |
  | 10 | **hollow triangle** (polygon filled WHITE then outlined) | 26·sx, lat 10·sy |
  | 11 | offset dimension tick/slash (far from endpoint, ±120/160) | 40·sx |
  | 12 | single tick | lat 14·sy |
  sx = `arrow_scale_x`, sy = `arrow_scale_y` (both default 1.0; barb-group default 0.5).
  **UNRESOLVED:** the XML attribute that carries ArrowType for a given primitive (the
  plain `end=1/2` seen on polylines is not it); arrowheads are used mainly on dimension
  lines and specific connectors. [BIN, exact geometry; XML mapping partial]

### Caps / joins
- GDI default (`PS_SOLID` cosmetic/geometric pens via `CreatePen`): **flat/round
  implementation-default caps, mitre joins**. No explicit `SetMiterLimit`/`ExtCreatePen`
  cap control in the common polyline path. [BIN: pens made with `CreatePen`, not
  `ExtCreatePen`]

--------------------------------------------------------------------------------
## 3. Geometry primitives (page layer or inside a symbol `<layer>`)

Raw primitives live in `<page><layers><layer>…</layer>`; the same tags also appear in
symbol defs under `<repo><ppd>`. Each element draws with the `op-*` pen/fill above.

- **`rect`** `left top right bottom` (axis-aligned box). GDI `Rectangle`. [XML]
- **`ellipse`** `left top right bottom` (bounding box). GDI `Ellipse`. [XML]
- **`roundRect`** `left top right bottom rX rY` — rounded rectangle; `rX`,`rY` are the
  corner ellipse radii (units). GDI `RoundRect(…,2·rX,2·rY)` semantics. [XML:
  `rX="40" rY="40"`]
- **`circle`** `centerx centery tangentx tangenty` — centre plus a point on the circle;
  **radius = hypot(tangentx-centerx, tangenty-centery)**. [XML: centre (60,0), tangent
  (75,13) -> r=√(15²+13²)≈19.8]
- **`polygon`** `pts="x,y,x,y,…,"` (trailing comma) — closed filled/stroked polygon. [XML]
- **`polyline`** `pts="x,y,…,"` — open polyline (not auto-closed). [XML]
- **`polybezier`** `pts="x0,y0, c1x,c1y, c2x,c2y, x1,y1, …"` — cubic Bézier(s); points
  are [anchor, control, control, anchor, (control, control, anchor)…], GDI `PolyBezier`
  layout (1 start + multiples of 3). [XML: 4 points = one cubic segment; chains share the
  previous anchor]. Drawer `QUtilsCElem::My_Bezier` [BIN 0x1800d0110].
- **`arc` / `pie` / `chord`** `left top right bottom bX bY eX eY` — bounding ellipse box
  plus **start radial (bX,bY)** and **end radial (eX,eY)** given as vectors relative to
  the ellipse centre. `arc` = stroked open arc; `pie` = filled wedge (centre→start→arc→
  centre); `chord` = arc closed by a straight chord. Sweep direction: **counter-clockwise
  from start to end** (GDI `Arc/Pie/Chord` convention with the given box). [XML: arc box
  70..1930, bX/bY,eX/eY vectors; pie with op-fd/op-fc fill]. Czech drawer names
  `My_Oblouk` (arc) / `My_Kruh` (circle). [BIN 0x1800214d0 / 0x1800d0040]
- **`arc_3p`** three-point arc variant (rare). **structure partial.** [XML]
- **`hatch`** `type penSize spacing offSetX offSetY` — crosshatch/fill pattern applied to
  the parent shape. `type` = pattern id (observed 0..5), `penSize` = hatch line width
  (units), `spacing` = line spacing (units), `offSetX/Y` = phase offset. Observed:
  type 0 = (none/solid phase), 1,2 = single-direction hatch at an angle, 3 = ?, 4,5 =
  cross/alt. **Exact angle per type id = partial** (needs the hatch drawer). [XML:
  `type` 0–5, `penSize` 0–10, `spacing` 2–46]
- **`img` / `imgDesc`** — embedded raster.
  - `<imgDesc lG="GUID" imgType="N">BASE64…</imgDesc>` is the image **store**: the body
    is the **Base64 of the raw image file**. `imgType`: **4 = PNG** (payload starts
    `iVBORw0KGgo` = PNG magic), 2/3 = other formats (BMP/JPEG — infer from magic bytes
    after Base64-decode). [XML: decoded head = PNG signature]
  - `<img lG="GUID" preserveAspect="1" left top right bottom/>` is the **placement**:
    draw the bitmap identified by matching `lG` into the box `left,top,right,bottom`;
    `preserveAspect="1"` = keep aspect ratio (letterbox within box). [XML]

--------------------------------------------------------------------------------
## 4. Text (`<text>` and attribute labels)

`<text x y f="…" al a l tws t turns link>…body…</text>`

- **`f="size,bold,italic,underline,face,RRGGBB"`** (6 CSV fields, in this order):
  1. **size** — font size (see calibration below).
  2. **bold** — 0/1.
  3. **italic** — 0/1.
  4. **underline** — 0/1.
  5. **face** — font family name (e.g. `Arial`, `Tahoma`, `Arial Narrow`).
  6. **colour** — **RRGGBB hex** (note: *text* colour is hex RGB here, unlike the decimal
     BGR of `op-lc`/`op-fc`). [XML: `f="100,1,0,0,Arial,008000"` = green bold]
- **Size unit -> pixels.** [PROBE]: a cap "H" at `size=100` renders ~23 px tall; at
  `size=200` ~47 px. Approximately linear through the origin:
  **cap-height px ≈ 0.23·size**, full line/em ≈ 0.33–0.35·size px. Consistent with the
  size being **tenths of a point rendered at the export DPI** (254 dpi = 10 px/mm):
  `lfHeight_px ≈ MulDiv(size/10, 254, 72) ≈ 0.35·size`. The document `<fonts>` element
  gives the default sizes per role: `letter=125 text=70 type=65 refs=65 cross_refs=70
  outlets=70 reports=70`. [calibration = measured; exact rounding partial]
- **`al` = text alignment / anchor code.** Observed values `2` (ref/type labels), `6`
  (most common), `9`. Probed with a cross marker fixed at the text anchor:
  **`al` controls HORIZONTAL anchoring; the vertical anchor is constant across 2/6/9**
  (text top stayed fixed). `al=9` draws the text to the **left** of the anchor
  (right-aligned); `al=2` and `al=6` extend to the **right** of the anchor
  (left/centre-aligned). So the low digit of `al` ≈ horizontal L(2)/C(6)/R(9); the family
  spans a 3×3 (horizontal × vertical) anchor grid, values 0..10+. **Exact full table
  = partial** (vertical variants not isolated). [PROBE ALM2/6/9: al9 image 92 px wide &
  text ends at anchor; al2/6 image 112 px with text past anchor]
- **`a` = rotation in tenths of a degree, clockwise** (same convention as `elem/@a`),
  about the text anchor. Text rotates with the symbol. [PROBE: a=900 -> text drawn
  vertical]. See §5 for text inside mirrored/rotated symbols.
- **`l`** line-spacing/leading; **`tws`** word/tracking spacing; **`t`** a type/flag;
  **`turns`** multi-segment/curved-text turn count; **`link`** a hyperlink/reference
  target. [XML, low-confidence semantics — all optional]
- **Multi-line:** body text with embedded newlines renders as stacked lines using `l`
  leading; alignment `al` applies per block. [XML]

--------------------------------------------------------------------------------
## 5. Symbols in drawings (`<elem>`, attributes, outlets, layers)

- **`<elem lG|lGuid="GUID" x y [a] [v] [h] [sX] [sY] [t] [c] [sbm] [op-fd] [op-fc]>`** is
  a placed instance of a repository symbol (looked up in `<repo>` by GUID). Reader must
  accept **both `lGuid` (older, ≤ v9) and `lG` (v10+)**. [XML]
- **Instance transform `QPivot::PrevodBodu`** [KNOWN, BIN]: scale by `sX`/`sY` with
  **int truncation**; `v="1"` negates x (mirror L-R); `h="1"` negates y (mirror T-B);
  then rotate by `a` in tenths of a degree (e.g. `a=900` -> `(x,y)->(y,-x)`). Applied to
  every point of the symbol's geometry and to its attribute label positions.
- **Per-instance fields:** `t` = rotation/placement type code; `c` = colour override;
  `sbm` = sub-mirror/symbol-branch mirror; `op-fd`/`op-fc` = fill override. [XML]
- **`<attributes>` / `<attribute name value v custom al x y [t]>`** — text labels
  attached to the instance:
  - `name` e.g. `_ref` (reference designator), `_type` (value/type), or any custom name.
  - `value` = displayed string.
  - **`v="1"` visible, `v="0"` hidden** (hidden attributes are NOT drawn). [XML:
    `_ref … v="0"` on hidden terminals]
  - `al` = alignment (same codes as `<text>`); `x y` = label position **absolute in page
    units** (already transformed; samples store absolute coords, not relative to elem).
  - `custom` = custom-text override (empty = use library default); `t` = type flag.
  - **Fonts by role** come from the document `<fonts>` entry: `_ref` uses `refs`,
    `_type` uses `type`, generic free text uses `text`/`letter`, outlet labels use
    `outlets`, cross-references use `cross_refs`, wire names use (wire-name font). [XML +
    `<fonts>` roles]
- **Outlets in export:** symbol connection points (`<outlet x y>`) are **NOT drawn in the
  PNG export**. The outlet nub drawer is gated: `QDocPic::DrawOutlet` (orange pen width 6,
  colour 0x0080FF) is only called when the "emphasize/edit" flag is set; `Path2Image`
  explicitly sets `CDrawObj::m_bEmphasizeOutlets = false` before drawing. [BIN
  `QDocPic::Draw` `if (param_4 != 0) DrawOutlet(...)`; `Path2Image` 0x1800ce4d0]
- **Layers:** `<layers current="k">` with `<layer name v>`; **`v="1"` visible, `v="0"`
  hidden** — hidden layers are skipped in export. Draw order = document order within the
  layer; layers drawn in file order. [XML]
- Composite `.ppd` symbols (nested `<repo>`+`<elem>`): nested outlets collected by
  `QDocPpd::GetOutlets` (all layers, doc order, recursive). [KNOWN]

--------------------------------------------------------------------------------
## 6. Wires

- **`<wire [name] [op-lw] [op-lc] [op-at] [cable] [sloping] pts="x,y,…,">`.**
  - Pen: same `op-lw`/`op-lc` as geometry; default width for wires in samples is `6`
    (0.6 mm) and default colour black (0) or a bus colour. [XML]
  - `name` = wire/net label (bus): same-name wires are one net; the label is rendered per
    `NumberingWire` settings.
  - `cable` = cable grouping id; `sloping` = allow non-orthogonal segments.
- **Junction dots.** Two kinds: explicit `<junction x y/>` elements, and auto "drop"
  dots where a wire end meets another wire (`drop1`/`drop2`). Rendered as a **filled disc
  at the junction**. [KNOWN drop1/drop2 = junction dots; XML `<junction x y>`]. Dot
  radius not isolated by probe here — **measure from a sample** (≈ wire-width-scaled
  filled circle; partial).
- **Wire-name labels** controlled by document `<NumberingWire>`:
  `Prefill, Digits, TypeRenumbering, ShowWireName (1=show), WireLabelDist_a/_b/_c`
  (offset distances of the label from the wire), `Vertically` (1 = stack vertically).
  [XML header]

--------------------------------------------------------------------------------
## 7. IC drawing (`.picd` / `<ic>`): `QDocPic::Draw` [BIN 0x180063900]

Data (`.picd`): `<picd ver_left ver_right mark outlets_hor outlets_ver name>` with
children `<out_n>` (pin NAMES, CSV), `<out_d>` (pin NUMBERS, CSV, aligned to GetVyvody
order), `<out_n_inv>` (overbar flag/list), `<desc>`, `<pos_hor>` (CSV of pin rows that
get an internal section-divider line). `outlets_ver = V`, `outlets_hor = H`. [XML:
PIC16F887.picd]

Geometry (pitch **P = 40** = `this+0x190`) [BIN + KNOWN GetVyvody]:
- **Body half-width** `halfW = (H < 6) ? 3·P : ((H+1)·P)/2`.
- **Body half-height** `halfH = (V-1)·(P/2) + 2·P`.
- Body rect = `(cx-halfW, cy-halfH)` .. `(cx+halfW, cy+halfH)` drawn by
  `QUtilsCElem::My_Rotated_Filled_Rectangle` (filled with `op-fc` if filled, stroked with
  the body pen).
- **Pins are flush with the body edge** (pin tip x = ±halfW), i.e. ProfiCAD ICs have no
  protruding stub; the connection point sits on the rectangle border. `DrawOutlet`
  (orange nub) only in edit mode -> not in export.
- **Pin numbers** (`out_d`) and **pin names** (`out_n`) are drawn inside the body next to
  each pin by `QDocPic::QText`, in GetVyvody order: left column (V, top→bottom), bottom
  row (H, left→right), right column (V, bottom→top), top row (H, right→left). Numbers use
  the `type` font role, names the `outlets`/name font. [BIN loops at this+0x178=out_d,
  this+0x188=out_n]
- **`out_n_inv` overbar:** names flagged by `out_n_inv` are drawn with an overline (active-
  low). Rendered inside `QText`. [XML flag; BIN QText — overbar draw partial]
- **`mark` notch:** `mark="1"` draws a small **semicircular notch at top-centre** of the
  body as a cubic Bézier, span ≈ ±11 units, depth 12 (`My_Bezier`, control pts
  cx±10/±11, top, top+12). [BIN this[0x150] branch]
- **`ver_left` / `ver_right`:** full vertical divider lines inset **44 units (0x2c)** from
  the left / right body edge. [BIN this[0x151]/[0x152]]
- **`pos_hor`:** for each listed pin index, a horizontal section-divider line is drawn
  from the body edge inward 44 units at that pin's row (`y = top + (idx+1)·P + P/2`).
  [BIN tail loop, this+0x170]
- `pos_hor` placement uses pitch `P=40`; `P/2=20` offsets centre the dividers between
  pins. [BIN]

--------------------------------------------------------------------------------
## 8. File-format versions (sxe loader) and sibling formats

- Root: `<document type="ProfiCAD sxe" version="V">`. `V` seen: `1.0, 5.0, 6.0, 7.0,
  8.0, 9.0, 10.0, 11.0, 12, 14`. The loader stores `version×10` as an int. [BIN]
- **Master version gate** `FUN_180106830` (called from
  `QCollectionPages::LoadFromXmlFile`): `if (version_int < 0x46 /*70 = v7.0*/)` take the
  **legacy** parse path (`FUN_1801074d0`, single current-page index defaulted to "1");
  **else (≥ v7.0)** take the **modern** multi-page path (`FUN_1801073a0` +
  `QCollectionPages::RecalculatePageSize`). So the hard structural split is **< v7.0
  (legacy) vs ≥ v7.0 (modern)**. [BIN, exact]
- Observed serialization deltas a reader must tolerate (from sample diffing) [XML]:
  - **Symbol GUID attribute:** `lGuid` in older files (≤ v9), **`lG`** from ~v10 onward.
    Accept both.
  - **Attribute serialization:** v9 writes `v custom al x y` (with empty `custom=""`);
    v12/v14 write `v x y al` (no `custom`). Reader should key by attribute name, not
    position.
  - Legacy (older) library/report files use `<type>`/`<value>` child elements and
    `id=`/`t=` attributes on elements; modern sxe uses attribute form. [KNOWN]
  - Core element vocabulary (`rect, ellipse, polyline, polygon, arc, pie, text, elem,
    wire, outlet, hatch, img/imgDesc`) is stable across v7..v14; later versions ADD tags
    (`CableSymbol`, dimensioning `dim_line`/`DimStyle`, report grids) rather than change
    old ones. The generic element loop `QDocShared::LoadFromXmlElements` dispatches per
    tag name via a vtable (`this+0x38`), so unknown tags are skipped gracefully. [BIN
    0x18006a970]
- **Per-version field table beyond the v7 cut and the lG/lGuid + attribute-order deltas
  is NOT exhaustively enumerated** (would require decompiling each of FUN_1801073a0 /
  per-tag loaders). Marked partial.

**Sibling top-level formats:**
- **`.ppd`** (symbol): `<document type="ProfiCAD ppd" …><ppd name t v n fG lG><layers>
  <layer v><…geometry…><outlet x y>…`. `t`=type letter (R/C/Q…), `v`=default value,
  `n`=standard/norm ref, `fG`/`lG`=file/library GUIDs. Loader `QDocPpd::LoadFromXml*`.
- **`.picd`** (IC): `<document type="ProfiCAD picd" version><picd …>` as §7. Loader
  `QDocPic::LoadFromXmlFile` 0x1800654f0.
- **`.ptb`** (title block / border): `QDocPtb::LoadFromXmlFile` 0x180069fa0; same
  layer/geometry/text vocabulary, used as the page frame + title-block template; its text
  uses `{field}` placeholders filled from the page `<summary>` fields. [XML: block
  diagram `{title}` etc.]

--------------------------------------------------------------------------------
## 9. What else the export draws

- **Title block / page frame:** only in a **whole-page export** (`PCAD_WHOLE_PAGE=1`,
  range 185, `PCAD_FRAME=1`). The `.ptb` named in `<tb use="1" name="…standard4.ptb"/>`
  is drawn with `{placeholder}` fields substituted from the page `<summary>` (`title`,
  `author`, `date`, `name`, `_po/_pc` page numbers, etc.). The default "Used Part"
  export (range 180) **excludes** the frame and title block. [KNOWN pcadrun.sh; XML]
- **Grid (`PageSettings/@rastr`, `RefGridSettings`) is NOT exported** — editor aid only.
- **Reference grid labels / cross-reference tables** are report/editor features, not part
  of a plain schematic PNG.
- Page background honours `PageSettings/@bgColor` (white in all samples).

--------------------------------------------------------------------------------
## Confidence / unknowns

**Fully answered (high confidence, BIN+PROBE):**
- Pixel scale 10 px/mm, white opaque bg, ~21 px used-part margin, lines aliased / text AA,
  GDI (not GDI+). (Q1)
- `op-lw` px mapping incl. default 2 and the 0-special case; `op-lc`/`op-fc` decimal
  COLORREF decode; `op-fd` fill. (Q2)
- Geometry semantics for rect/ellipse/roundRect/circle/polygon/polyline/polybezier/
  arc/pie/chord and img/imgDesc Base64 PNG encoding + placement. (Q3)
- `f=` field order + size calibration; `a` rotation; outlets-not-in-export. (Q4/Q5)
- `elem` transform, attribute visibility/fonts/positions, layer visibility. (Q5)
- IC `QDocPic::Draw`: body size formula, pitch 40, pins flush, numbers/names order,
  mark notch, ver_left/right (±44), pos_hor dividers. (Q7)
- Loader master version gate at v7.0 (version×10 vs 70); `.ppd/.picd/.ptb` structure;
  lG/lGuid + attribute-order tolerance. (Q8)
- Title block only in whole-page export; grid not exported. (Q9)

**Partial:**
- Arrow geometry (ArrowType 5..13 + arrow_scale_x/y) is fully derived from the binary.
  Confirmed that polyline/wire **`end=` is NOT ArrowType** (end=1..6 all render headless);
  arrowheads are used by dimension lines/`DimStyle`. The exact XML attribute carrying
  ArrowType for dimension/connector elements is not pinned down. (Q2)
- `text` `al` exact code table (values 2/6/9 observed; 3×3 anchor model inferred, not
  verified); minor fields `l,tws,t,turns,link` semantics low-confidence. (Q4)
- `hatch` exact angle/pattern per `type` id (0..5); `op-line-scale` exact dash period.
- Wire junction dot radius (needs a sample measurement).
- `out_n_inv` overbar exact rendering (in `QDocPic::QText`, not fully decompiled).
- Per-version field deltas beyond the v7 cut + lG/lGuid + attribute order. (Q8)

**Unknown:**
- `op-at` dash on/off patterns: probes rendered observed `op-at` values near-solid at
  export scale; exact dash tables unresolved.
- `op-contour2`: no samples, not located in the pen path.
- `arc_3p` three-point-arc parameterisation (rare tag).

**Evidence artifacts:** probe `.sxe`/`.png` in `/tmp/claude-1000/re_probe/`;
`QDocPic::Draw` pseudocode saved at `/tmp/claude-1000/re_probe/QDocPicDraw.c`. Binary
addresses are Ghidra RVAs in `common.dll`
(sha256 d92e596241a151ddbdf2660c70c17df0445a0b3d371753afc8b614c7587bd936).
