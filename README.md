# pcad — schematic pictures from JSON, in the ProfiCAD file format

`pcad.py` generates electrical/electronics schematics as ProfiCAD `.sxe`
drawings from a small JSON spec, and renders them to PNG/SVG with a clean-room
pure-Python renderer. **ProfiCAD itself is not required** — the symbol library
is bundled under `lib/` and both the writer and the renderer are plain Python.

The symbol library is an **independent clean-room drawing** of the **EN 60617**
(= IEC 60617; Czech ČSN EN 60617) graphical symbols. A facts-only specification
(symbol name, standard clause, ordered connection points and pin-number order,
drawn size, inside markings — no drawing data of any kind) was written from the
standard, and separate drawing teams rendered those facts into ProfiCAD-format
`.ppd` files with no access to any third-party symbol library. Pin positions and
pin-number order follow the standard, so wiring carries the standard's
connection numbering; the geometry is this project's own. The library plus the
`.picd` ICs and the junction dot are MIT-licensed, © 2026 miromraz — see
`lib/NOTICE` for the clean-room process and `lib/LICENSE`.

## Requirements

- Python 3 (standard library only) for `build`, `search`, `pins`, `inspect`,
  `verify`, and SVG rendering.
- [Pillow](https://pypi.org/project/Pillow/) only for PNG rendering.

## Commands

```
python3 pcad.py search <words...>            find library symbols (AND match on path)
python3 pcad.py pins <symbol>                list a symbol's pins/outlets
python3 pcad.py build <spec.json> <out.sxe>  generate a drawing
python3 pcad.py render <in> <out.png|.svg>   render (.sxe/.ppd/.picd; PNG needs Pillow)
python3 pcad.py verify <out.sxe>             ERC on the drawing geometry (nets + checks)
python3 pcad.py inspect <file.sxe>           summarise an existing drawing
python3 pcad.py import-lib [SRC] [DEST]      copy ProfiCAD's stock symbols from your own install
python3 pcad.py selftest                     run internal asserts
```

A `<symbol>` is a library-relative path without extension, e.g.
`electronics/passive/resistors/resistor`, `electronics/meters/ammeter`,
`ic/555`. Use `search` to find the exact path.

### Using ProfiCAD's stock symbols

This repo ships **only** its own clean-room symbols. If you have ProfiCAD
installed and want drawings that look exactly like ProfiCAD's, copy the stock
library from your own install and point `PCAD_LIB` at the copy:

```
python3 pcad.py import-lib                   # finds C:\Users\Public\Documents\ProfiCAD Library (or the Wine equivalent)
python3 pcad.py import-lib "/path/to/ProfiCAD Library" ~/.pcad/proficad-lib
PCAD_LIB=~/.pcad/proficad-lib python3 pcad.py search ammeter
```

The stock library belongs to ProfiCAD's author and stays on your machine; do not
redistribute it. Stock symbol paths differ from the bundled ones, so `search`
again after switching. A built `.sxe` embeds the symbols it uses, so it renders
and opens in ProfiCAD without `PCAD_LIB`.

`PCAD_LIB` accepts any ProfiCAD-format library directory (of `.ppd`/`.picd`
files); it defaults to the bundled `lib/`.

## JSON spec format (coords in mm)

```json
{
  "parts": [
    {"sym": "electronics/passive/resistors/resistor", "ref": "R1", "val": "330R",
     "x": 30, "y": 30, "rot": 90, "mirror": "x", "hide_ref": true}
  ],
  "wires": [
    ["R1.1", [30, 20], "D1.2"],
    {"pts": [[20, 20], [90, 20]], "name": "L1", "dots": false}
  ],
  "texts": [{"x": 10, "y": 5, "text": "note", "size": 70, "color": "008000"}],
  "title": {"title": "...", "author": "...", "date": "...", "name": "..."}
}
```

- `x,y` = part centre in mm. `rot` = degrees (90, -90, 180). `mirror` = `"x"`
  (left-right) or `"y"` (top-bottom); pins and wires follow the mirror.
  `hide_ref` hides the reference label.
- A wire point is `[x,y]` in mm, or `"REF.pin"`: for a `.ppd` part the pin is the
  1-based outlet index (`pins` lists them); for a `.picd` IC it is the printed
  pin number. Add `[x,y]` corners for right-angle routing.
- **Junction dots** are added automatically where a wire end meets another wire.
  Set `"dots": false` on a wire to suppress them for that wire.
- **Named wires** (`"name": "L1"`) are busbars: same-name wires form one net and
  their open ends are treated as labelled terminals.

Workflow: `search` → `pins` → write spec → `build` → `verify` (fix until PASS) →
`render` → look at the PNG → iterate.

## Claude Code skill

`skills/proficad-schematic/SKILL.md` teaches a Claude Code agent the whole
workflow (search, pins, spec, build, verify, render). Install it once:

```
ln -s "$(pwd)/skills/proficad-schematic" ~/.claude/skills/proficad-schematic
```

Every new Claude Code session then picks it up automatically, and other skills
(e.g. a lab-report skill) can tell the agent to draw schematics with it.

## Credits

- Symbol library: an independent clean-room drawing of EN 60617 / IEC 60617
  (ČSN EN 60617), drawn from a facts-only specification by separate drawing
  teams with no access to any third-party symbol library. MIT, © 2026 miromraz.
  See `lib/NOTICE` for the clean-room process.
- Code: MIT, © 2026 miromraz. See `LICENSE`.

ProfiCAD is a trademark of its respective owner. This project is independent and
unaffiliated; it only reads and writes the documented `.sxe`/`.ppd`/`.picd` file
structures (see `RE_NOTES.md`).
