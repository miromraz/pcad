---
name: proficad-schematic
description: Draw electrical/electronics schematics as real ProfiCAD .sxe files plus PNG/SVG from a JSON spec, using a bundled clean-room EN 60617 symbol library (~960 standard symbols drawn to EN 60617, plus generic ICs). Pure Python; ProfiCAD itself is not needed. Use when asked to draw, generate, render or check a circuit/schematic (resistors, LEDs, transistors, ICs, switches, power, relays, meters, etc.), including schematics for elaborát protocols.
---

# ProfiCAD-format schematic generator

Tools live in the pcad repo root, written `<pcad>/` below: the folder two levels
above this SKILL.md (resolve symlinks; e.g. `~/proficad`). `pcad.py` (stdlib Python, builds `.sxe`
drawings and renders them to PNG/SVG) and `pcadrender.py` (the pure-Python
renderer it uses). No ProfiCAD/Wine is needed at runtime: the symbol library is
bundled under `lib/` and rendering is clean-room Python (Pillow for PNG, stdlib
for SVG).

**Symbols: EN 60617 (clean-room).** The `lib/` symbols are an independent
clean-room drawing of the EN 60617 (= IEC 60617, ČSN EN 60617) standard: drawn
from a facts-only spec (name, clause, ordered pins/pin-number order, size,
inside markings) by separate teams with no access to any third-party library.
Pin positions and pin-number order follow the standard, so wiring carries the
standard's connection numbering. **License:** everything MIT, © 2026 miromraz;
see `lib/NOTICE` for the clean-room process.

**Library layout.** ProfiCAD-style English category tree, e.g.
`electronics/passive/resistors/…`, `electronics/semiconductors/diodes/…`,
`electronics/meters/…`, `electronics/passive/lamps/…` (sources/cells),
`power/switching/…`, `power/machines/motors/…`, `power/power-generation/…`,
`installation/…`, `other/…`, plus our own `misc/junction dot` and `ic/…`
(`.picd` multi-pin ICs). Paths are long — ALWAYS `search`/`pins` first, never
guess. Point at a different ProfiCAD-format library with `PCAD_LIB=…`.

**ProfiCAD's stock symbols** are NOT bundled (they belong to ProfiCAD's author).
If the user has ProfiCAD installed and wants the exact ProfiCAD look, copy them
from their own install: `python3 <pcad>/pcad.py import-lib [SRC] [DEST]` (default
SRC `C:\Users\Public\Documents\ProfiCAD Library` or the Wine equivalent, DEST
`~/.pcad/proficad-lib`), then prefix commands with `PCAD_LIB=~/.pcad/proficad-lib`.
Stock paths differ (e.g. `electronics/measuring devices/ammeter`): `search` again.
Never commit or publish the stock library.

## Workflow

1. **search** for the symbols you need (returns library-relative paths, no ext):
   `python3 <pcad>/pcad.py search resistor`
2. **pins** to learn a symbol's outlet layout (index, x_mm, y_mm):
   `python3 <pcad>/pcad.py pins "electronics/passive/resistors/resistor"`
3. **write a spec** (JSON, coords in mm). Place parts, wire pin-to-pin:
   ```json
   {
     "parts": [
       {"sym": "electronics/passive/resistors/resistor",
        "ref": "R1", "val": "330R", "x": 30, "y": 30, "rot": 0}
     ],
     "wires": [ ["R1.1", [30,20], "D1.2"] ],
     "texts": [ {"x": 10, "y": 5, "text": "note"} ]
   }
   ```
   - `x,y` = part centre in mm. `rot` = degrees (90, -90, 180); omit for 0.
     `"mirror": "x"` flips a part left-right, `"mirror": "y"` top-bottom
     (combinable with `rot`); pins and wires follow the mirror.
   - Wire points are `[x,y]` mm **or** `"REF.pin"`. For a `.ppd` part `pin` is the
     1-based outlet index; for a `.picd` **IC** it is the printed pin **number**
     (`pins` shows these). Prefer pin refs so wires land exactly. Add `[x,y]` corner
     points between pins to route right-angle wires.
   - **Junction dots** are added automatically where a wire end meets another wire
     (T-junction, or 3+ ends/segments at a point). To suppress them on one wire,
     write it as `{"pts": [...], "dots": false}` instead of a bare list.
     ProfiCAD stores dots only at wire ENDS: at every T-junction let one wire END on
     the other; never route two wires through the same bend point (it gets no dot).
   - **Named wires / busbars**: a wire dict may carry `"name": "L1"`. Wires sharing
     a name are one net (like ProfiCAD's L1/L2/L3/N/PE busbars), and a named wire's
     open ends are treated as labelled terminals (not dangling). See
     `examples/breaker_motor.json` (3-phase: three switches, 3-phase motor, L1/L2/L3 busbars).
   - **ICs**: parts whose `sym` is a `.picd` (e.g. `ic/555`) are placed
     as multi-pin IC boxes. `pins <ic>` lists `number  name  x  y`; wire to them by
     number, e.g. `"U1.3"`; an unnumbered position is `"U1.#5"` (1-based position).
     Always run `pins` first: library ICs differ in which field holds numbers.
     Search `ic` for op-amps, logic, timers (555, 741, LM358, 7400, 7805).
   - **Title block**: optional `"title": {"title":..,"author":..,"date":..,"name":..}`
     fills the page summary fields.
4. **build**: `python3 <pcad>/pcad.py build spec.json out.sxe`
5. **render** (pure Python, no Wine, instant):
   `python3 <pcad>/pcad.py render out.sxe out.png`
   Also renders `.sxe`/`.ppd`/`.picd` inputs and `.svg` output. Output matches
   ProfiCAD's PNG export (used part of the document, no frame, 10 px/mm, white
   background). Options: `--page N` (multi-page files), `--scale PX_PER_MM`
   (default 10).
6. **verify** (required before delivering): `python3 <pcad>/pcad.py verify out.sxe` (spec arg
   also accepted). Runs a pure-Python **ERC on the .sxe geometry** (no Wine) and
   prints the nets. Exits non-zero and FAILs on:
   a wire crossing a symbol/IC body, a wire running over a pin without terminating
   there, a dangling wire end, or an unconnected 1-pin symbol (ground/supply).
   Unconnected pins of multi-pin parts are warnings; a wire end near a text label
   is treated as a labelled terminal. (ProfiCAD's own netlist is a paid-edition
   feature, so connectivity comes from the pin/wire geometry.) Fix the spec until
   verify PASSes.
7. **Read the PNG** to verify wires meet pins and labels are legible; fix the spec
   and re-run if not. Iterate.

**inspect** an existing drawing (v7 or v9) to read/edit a user-supplied file:
`python3 <pcad>/pcad.py inspect file.sxe` prints pages, placed
symbols (ref, value, symbol, x/y, rotation), ICs, wire count and texts.

See `<pcad>/examples/led.json` and `examples/ic555.json` (IC demo).

## Limits

- `build`/`pins` support `.ppd` symbols (including composite ones with nested
  `<repo>`/`<elem>` parts, whose internal pins are resolved recursively) and
  `.picd` ICs.
- IC pin geometry is derived (no rotation-specific label layout); `<ic>` placement
  honours `rot` for pin resolution.
- Ref/value labels are placed outside each symbol, away from its leads (right of
  it when pins run vertically, else above/below). Two neighbouring parts can
  still collide; move a part or set `hide_ref` (useful on ground symbols).
- `verify` FAILs any unlabelled open wire end. Installation plans that use bare
  feeder lines need a text label or a named wire at that end.
