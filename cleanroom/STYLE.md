# Clean-room EN 60617 .ppd house style (the contract for all 9 teams)

This is the drawing contract. Draw only from the EN/IEC 60617 standard and general
drafting knowledge + the facts in `cleanroom/spec/*.json`. Never open any ProfiCAD
reference drawing (see the clean-room rule in the brief). `.ppd` format and primitive
semantics: `../RE_NOTES.md`. Primitive XML names are verified against `pcad.py` /
`pcadrender.py` (the renderer we check with).

## 1. Units, axes, origin
- All coordinates and sizes are **0.1 mm integer units** (ProfiCAD internal unit;
  1 unit = 1 px at the 10 px/mm export scale).
- **y points DOWN.** +x right, +y down.
- **Origin (0,0) = the symbol insertion point.** Draw symmetric symbols centred on it.

## 2. Grid
- Connection points sit on a **20-unit (2 mm) grid** — that is how the spec `pins`
  are given (±20, ±40, ±60, ±80, ±100 …). Keep all outlets on that grid.
- Keep body geometry on a **10-unit (1 mm) grid** where practical; curves may use
  finer coordinates.

## 3. Pens, fill, colour
- **Standard body line width `op-lw="4"`** (0.4 mm). Use it for every outline,
  lead and glyph stroke unless a heavier accent is wanted (then `op-lw="6"`).
  Fine detail (hatch, small ticks) may use `op-lw="2"`.
- Default colour is black; omit `op-lc`/`op-fc` to get black. (`op-lc`/`op-fc` are
  **decimal COLORREF 0x00BBGGRR**, not needed for this library — everything is black.)
- **Filled** shapes (solid dots, filled arrowheads/triangles): add `op-fd="1"`
  (`op-fc` omitted → black). Open shapes: no `op-fd`.
- Line width does **not** affect the measured bounding box (`_ppd_box` reads raw
  coordinates, not half-widths), so pen weight is free to choose.

## 4. Leads / stubs
- A connection **lead** is a straight `polyline` from the body edge out to the
  outlet point. Standard lead length is **40 units (4 mm)**; use whatever length
  makes the outlet land exactly on its spec coordinate.
- When a spec pin already lies on the body outline (e.g. a meter circle r=40 with a
  pin at (±40,0)), put the outlet on the outline with **no separate lead**.

## 5. Standard element geometry (IEC 60617 proportions)
- **Indicating/measuring instrument (circle)** — a circle centred on the origin,
  radius = half the smaller body dimension (meters: r = 40 for an 80×80 body). The
  quantity letter(s) sit centred inside. Pins on the horizontal (and, for 4-terminal
  instruments, vertical) axis, on the circle or on short leads.
- **Integrating / energy meter, counter, converter block (rectangle/square)** — an
  axis-aligned `rect` matching the body box. Energy meters (Wh, varh, Ah, hour) are
  **upright rectangles**; converters/rectifiers/stations are **squares**.
- **Resistor-type rectangle (reference proportion for other teams)** — IEC 60617
  resistor is a rectangle of ratio **≈ 4:1** (e.g. 100×40 units), leads on the long
  axis centre. Fuse = same rectangle. Capacitor = two parallel plates, gap ≈ 20.
- **Diamond / bridge** — a square rotated 45° (points on the axes) for bridge
  rectifiers; terminals at the four points.
- **Rotating machine** — circle with the machine letter inside (`G` generator,
  `M` motor); r = half the body.

## 6. Contacts & switches (convention for other teams)
- Contact blade drawn at a **≈30° open angle** from the fixed contact; pivot on one
  terminal, free end a **gap of ≈20 units** short of the other terminal.
- Hinge point and fixed contact both land on the 20-unit grid.

## 7. Arrowheads & radiation
- **Adjustable / variable** (general variability arrow): a straight `polyline`
  drawn diagonally across the element at ≈45°, with a small **filled triangle**
  (`polygon`, `op-fd="1"`) head, overall length ~1.4× the body. Used for adjustable
  generators, variable components.
- **Radiation / energy arrows** (light, non-ionizing radiation — PV cells, radiation
  heat sources): **two parallel arrows** pointing *at* the device, each a short
  `polyline` shaft + small filled-triangle head, spaced ~15 units, at ≈45°.
  Nuclear/radio-isotope heat is marked with the inner glyph, not arrows.
- Arrowhead size: shaft ~30 units, head length ~14, half-width ~6. Build the head
  as a `polygon` of 3 points (tip + two barbs), filled black.

## 8. Text / markings
- Markings are the letters the standard puts **inside** the symbol (spec `markings`).
- **Centred marking**: one `text` at the glyph centre with **`al="9"`** — the
  renderer anchors al=9 as middle/middle (centre both ways). (`al="2"` = left,
  `al="6"` = right; see RE_NOTES §4.)
- **Font size** (first field of `f=`): single letter **`70`** (≈16 px / 1.6 mm cap);
  2–3 char markings **`60`**; 4+ char markings **`45`** so they fit the body.
  Font `f="SIZE,0,0,0,Arial,000000"` (size,bold,italic,underline,face,hexRGB — note
  text colour is **hex RGB**, unlike op-* decimal BGR).
- Stack multiple markings vertically, centred, ~`size*1.1` apart, block centred on
  the origin.
- Do **not** add reference designators or value text to a library symbol; markings
  only.

## 9. Honouring the spec size
- Aim for the drawn bounding box within **±15 %** of `size.w`×`size.h`.
- The measured box is `_ppd_box` = min/max over **all geometry AND all outlets**.
  Since outlets are included, pins at the extremes already set much of the box;
  make the body geometry fill the remaining width/height so the box reaches the
  stated size (e.g. an 80×120 meter is a tall rectangle, not an 80×80 circle).
- Assume the body is **centred on the origin** (box = [-w/2,w/2]×[-h/2,h/2]) unless
  the pins are asymmetric, in which case include the pins and keep the body where the
  pins imply (e.g. a long lead to one far pin).

## 10. Pins (outlets) — exact and ordered
- Emit one `<outlet x y>` per spec pin, **in spec order** (outlet order = pin number).
  Coordinates must equal the spec `x,y` **exactly** (integers, on the 20-unit grid).
- A symbol with 0 spec pins gets **no** `<outlet>` elements.
- Outlets are not drawn in the PNG export (RE_NOTES §5) — they are connection points
  only; still place them precisely.

## 11. File template
Real ProfiCAD `.ppd` layout (RE_NOTES §8), ProfiCAD-loadable and accepted by our
tools (`pcadrender.render`; `pcad._ppd_box` on the `<ppd>` node gives outlets/box;
`pcad.load_ppd` parses it without error):

```xml
<document type="ProfiCAD ppd" version="9.0">
<ppd name="NAME" t="DESIGNATION" v="" n="STANDARD" fG="FILE-UUID" lG="LIB-UUID">
<layers current="0"><layer name="0" v="1">
  ...geometry (polyline/rect/ellipse/polygon/arc/text)...
  <outlet x="X1" y="Y1"/>   <!-- pin 1 -->
  <outlet x="X2" y="Y2"/>   <!-- pin 2 -->
</layer></layers>
</ppd>
</document>
```

Header attributes:
- `type="ProfiCAD ppd"`, `version="9.0"` (≥ v7 modern loader path, RE_NOTES §8).
- `<ppd>` attributes: `name` = spec `name`; `t` = spec `designation` (`""` if null);
  `v` = `""` (no default value); `n` = spec `standard` **verbatim**
  (e.g. `EN 60617: 08-02-01`).
- **`fG` / `lG` = uuid5 of the record id under a fixed namespace.**
  - Fixed namespace UUID: **`2e3a1058-9dc9-5832-a41a-9e09806514fe`**
    (`uuid.uuid5(uuid.NAMESPACE_DNS, "en60617.cleanroom.proficad")`).
  - `lG = uuid5(NS, id)` — the library/symbol GUID (used to reference the symbol).
  - `fG = uuid5(NS, "file:" + id)` — the file GUID (distinct from lG).

## 12. File naming
- `cleanroom/lib/<category path>/<name>.ppd`, where `<category path>` is the spec
  `category` (already a POSIX sub-path, e.g. `electronics/meters`) and `<name>` is the
  spec `name` with any `/` replaced by `-` (slug keeps spaces, commas, parentheses).
- One `.ppd` per spec record; the id → path is deterministic so `check_batch.py`
  recomputes it.

## 13. Reusable building blocks (`cleanroom/tools/draw_lib.py`)
Reuse and extend these so symbols stay pin-compatible and consistently scaled.

- `Ppd()` — builder; methods `polyline/line/polygon/rect/ellipse/circle/dot/arc/
  text/outlet`, plus `marking(...)` and `document(name,designation,standard,id)`.
- `Ppd.marking(tokens, cx, cy, bodyw, bodyh)` — lays out spec `markings`: maps
  Symbol-font letters to Greek, joins trig/Greek parts onto one line
  ("cos φ", "I sin φ"), stacks distinct quantities ("W"/"var"), and sizes text as
  large as fits the body (anchors stay inside, so the box is unaffected).
- `marking_lines(tokens)` / `SYMBOL_TO_GREEK` — the grouping + Greek map (see §8).
- `lib_guid(id)` / `file_guid(id)` — the fixed-namespace uuid5s (§11).
- `slug_path(category, name)` — the file path (§12).
- `pin_center(pins)` — centroid of the pin bounding box.
- `rect_leads(p, pins, l,t,r,b)` / `leads(p, pins, body_r)` — axis-aligned /
  radial leads from a rect edge / circle to each outlet, and emit the outlet.
- `add_outlets(p, pins)` — emit outlets only (no leads).
- `meter(markings, pins, r)` — indicating-instrument circle.
- `body_rect(markings, pins, w, h, inner=None)` — rectangular body = spec box
  centred on the pin centroid, with leads, markings, and optional `inner` geometry
  (dividers/diagonal). `energy_meter(...)` is an alias.
- `arrow(p, x1,y1,x2,y2)` / `arrowhead(p, x,y, deg)` — filled-triangle arrows
  (adjustability, radiation). `sine(p, cx,cy, half, amp)` — AC tilde / waveform.

## 14. Team checklist (every batch)
1. `python3 tools/gen_<batch>.py` (reuse `draw_lib`; one `.ppd` per spec record).
2. `python3 tools/check_batch.py spec/<batch>.json` — must print `PASS N/N`.
3. **Read the contact sheet** `out/<batch>_sheet.png` and the pin overlay
   `out/<batch>_pins.png`; fix anything that is not a correct EN 60617 depiction,
   is inconsistent with other symbols, or whose pins miss their red dots.
4. Re-run until clean. List every symbol you were unsure about (and why) in your
   hand-off and, if it is a standing judgement call, under §15.

## 15. Open questions / judgement calls (meters_sources pilot)
- **Greek vs Symbol-font markings.** This spec revision still encodes some Greek
  letters as Latin Symbol-font letters; `SYMBOL_TO_GREEK` maps only the three
  unambiguous ones here (j→φ, q→θ, l→λ). When the spec team ships real Greek the
  map is a no-op. Never map unit letters (W, h, n, A, V…).
- **Station outline = circle.** EN 60617 §06: a generating station / substation is a
  **circle**; planned ("projected") installations use a **broken (dashed)** outline,
  in-service a solid one. Confirmed for this batch by geometry: the substation corner
  pins (±42,±42) lie exactly on the r=60 circle (60·cos45°≈42), so the outline is a
  circle, not a square. A DC→AC converter substation is a **square** (converter block).
- **Station inner type-glyphs** (nuclear atom, solar rays, wind blades, hydro wave,
  geothermic lines, thermoelectric cross, MHD text, combined ~/=) are my best-guess
  differentiators; the exact IEC inner pictograms could not be verified clean-room.
  The circle + solid/dashed convention is the standard part; the inner marks are not.
- **Qualifying signs** added to blank instruments: oscilloscope/oscillograph =
  waveform (high confidence; oscillograph also gets a stylus line as a recording
  instrument); galvanometer = moving-pointer arrow (medium); synchroscope &
  synchronous device = rotating phasor arrow (medium); **gyro = spin-axis line
  (low confidence)**. Revisit if a standard reference becomes available.
- **closed-loop controller**: not a 60617-08 converter; drawn as square+diagonal+"A"
  placeholder — low confidence.
- **counting device, cam driven**: drawn as a plain counter rectangle with its
  marking; the cam/contact detail is omitted.
