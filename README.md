# pcad — schematic pictures from JSON, in the ProfiCAD file format

`pcad.py` generates electrical/electronics schematics as ProfiCAD `.sxe`
drawings from a small JSON spec, and renders them to PNG/SVG with a clean-room
pure-Python renderer. **ProfiCAD itself is not required** — the symbol library
is bundled under `lib/` and both the writer and the renderer are plain Python.

The symbol library is converted from the open-source
[QElectroTech elements collection](https://github.com/qelectrotech/qelectrotech-elements)
(CC-BY 3.0), plus a handful of symbols and ICs drawn from scratch. See
`lib/NOTICE` for attribution and `tools/qet2ppd.py` for the converter.

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
python3 pcad.py selftest                     run internal asserts
```

A `<symbol>` is a library-relative path without extension, e.g.
`passive/resistor`, `meters/ammeter`, `ic/555`.

### Using a different library

Set `PCAD_LIB` to point `pcad.py` at any ProfiCAD-format library directory
(of `.ppd`/`.picd` files); it defaults to the bundled `lib/`.

```
PCAD_LIB=/path/to/other/library python3 pcad.py search resistor
```

## JSON spec format (coords in mm)

```json
{
  "parts": [
    {"sym": "passive/resistor", "ref": "R1", "val": "330R",
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

## Credits

- Symbol library derived from the QElectroTech elements collection,
  © The QElectroTech team, https://qelectrotech.org, CC-BY 3.0. See `lib/NOTICE`.
- Code: MIT, © 2026 miromraz. See `LICENSE`.

ProfiCAD is a trademark of its respective owner. This project is independent and
unaffiliated; it only reads and writes the documented `.sxe`/`.ppd`/`.picd` file
structures (see `RE_NOTES.md`).
