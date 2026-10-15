# Use ProfiCAD's stock symbol library locally

The stock symbol shapes come from ProfiCAD's own `.ppd` and `.picd` files.
This repository provides the generator, renderer, agent skill, and an independent
symbol library. It does **not** distribute ProfiCAD's stock library.

You obtain the stock files directly from ProfiCAD, extract or copy them on your
machine, and select that local folder with `PCAD_LIB`. No conversion of the
symbols is needed. ProfiCAD and Wine are not needed to build or render drawings
afterward. The Python renderer uses those symbol shapes; fonts and unsupported
features may differ from ProfiCAD's native export.

## 1. Get the library from ProfiCAD

### Option A: extract the official portable ZIP (Windows, Linux, macOS)

1. Open the official [ProfiCAD download page](https://www.proficad.com/download.aspx).
2. Under **Portable Version**, download the ZIP using the link marked
   **does not contain installer**. Use the current link on that page rather than
   an unofficial mirror or a version-specific URL copied from an old tutorial.
3. Extract the ZIP **outside this Git checkout**, for example into
   `Downloads/proficad-portable`. Windows Explorer's **Extract All**, a desktop
   archive manager, or Python can do this. You do not need to run `ProfiCAD.exe`.
4. Locate the `ProfiCAD Library` directory in the extracted files. It contains
   category subdirectories with `.ppd` symbols and `.picd` IC definitions. This
   directory, rather than an individual category, is your source library root.

For example, on Linux/macOS, if you saved the ZIP as
`~/Downloads/proficad-portable.zip`:

```bash
python3 -m zipfile -e "$HOME/Downloads/proficad-portable.zip" "$HOME/Downloads/proficad-portable"
```

On Windows PowerShell, Python can extract it too:

```powershell
py -3 -m zipfile -e "$HOME\Downloads\proficad-portable.zip" "$HOME\Downloads\proficad-portable"
```

The portable ZIP checked for this tutorial contained `ProfiCAD Library` at its
root. If a later release changes that layout, find the directory containing the
symbol categories instead of assuming the old layout.

### Option B: copy from your installed ProfiCAD

In ProfiCAD, press **F12 → Paths** to find the configured symbol library folder.
The [official download page](https://www.proficad.com/download.aspx#symbols)
describes this setting. A typical Windows path is:

```text
C:\Users\Public\Documents\ProfiCAD Library
```

With Wine, the corresponding path is typically:

```text
~/.wine/drive_c/users/Public/Documents/ProfiCAD Library
```

A custom Wine prefix uses a different path. Pass that path explicitly; automatic
detection only checks the standard Windows location and the default `~/.wine`
prefix (with `Library` or `library` spelling).

## 2. Import into a private local folder

Clone this repository if needed, then run commands from its root. Keep the
import destination outside the checkout; the default is `~/.pcad/proficad-lib`.
The importer copies only `.ppd` and `.picd` files and preserves category paths.
It does not download files, run ProfiCAD, or modify the source library.

Linux/macOS, using the portable ZIP extracted above:

```bash
cd "$HOME/pcad"
python3 pcad.py import-lib "$HOME/Downloads/proficad-portable/ProfiCAD Library"
export PCAD_LIB="$HOME/.pcad/proficad-lib"
python3 pcad.py search resistor
```

Windows PowerShell:

```powershell
Set-Location "$HOME\pcad"
py -3 pcad.py import-lib "$HOME\Downloads\proficad-portable\ProfiCAD Library"
$env:PCAD_LIB = "$HOME\.pcad\proficad-lib"
py -3 pcad.py search resistor
```

For an installed copy, let the importer detect a standard location:

```bash
python3 pcad.py import-lib
```

Or pass an explicit source and optional destination:

```bash
python3 pcad.py import-lib "/path/to/ProfiCAD Library" "$HOME/.pcad/proficad-lib"
```

Expect `copied N symbols ...`, with a nonzero count. Reimporting into the same
destination overwrites matching symbol files but does not delete obsolete ones.
For a clean version switch, import into a new directory and point `PCAD_LIB`
there. Do not import into this repository's `lib/`.

You can also skip copying and set `PCAD_LIB` directly to the extracted
`ProfiCAD Library` folder, provided you keep that folder available.

## 3. Check the selected symbols and make a drawing

`PCAD_LIB` replaces the bundled library; it does not merge the two. Stock paths
and pin layouts can differ from the bundled examples. Search first, then inspect
pins. Do not guess a path or reuse bundled-example paths blindly.

In the same Linux/macOS shell as the `export` above:

```bash
python3 pcad.py search resistor
python3 pcad.py pins "electronics/passive components/resistors/resistor"
```

The path above exists in the portable library checked for this tutorial. If your
version or language differs, use a path returned by your own search, without
`.ppd` or `.picd`. The checked resistor has pin 1 at `(0, -2.5)` mm and pin 2 at
`(0, 2.5)` mm relative to its center.

Save this as `stock-resistor.json` **in a work directory outside the repository**,
substituting your own resistor path if necessary:

```json
{
  "parts": [
    {"sym": "electronics/passive components/resistors/resistor",
     "ref": "R1", "val": "1k", "x": 30, "y": 30}
  ],
  "wires": [
    [[30, 20], "R1.1"],
    ["R1.2", [30, 40]]
  ],
  "texts": [
    {"x": 26, "y": 18, "text": "IN"},
    {"x": 26, "y": 44, "text": "OUT"}
  ]
}
```

With the repository cloned at `~/pcad`, run from that work directory:

```bash
export PCAD_LIB="$HOME/.pcad/proficad-lib"
python3 "$HOME/pcad/pcad.py" build stock-resistor.json stock-resistor.sxe
python3 "$HOME/pcad/pcad.py" verify stock-resistor.sxe
python3 "$HOME/pcad/pcad.py" render stock-resistor.sxe stock-resistor.svg
```

`verify` should report `PASS`. Open the SVG and check the resistor shape, labels,
and wire connections. PNG output also works if Pillow is installed:

```bash
python3 -m pip install Pillow
python3 "$HOME/pcad/pcad.py" render stock-resistor.sxe stock-resistor.png
```

On Windows, use `py -3` instead of `python3`, `$env:PCAD_LIB` as above, and the
Windows path to `pcad.py`. A generated `.sxe` embeds the symbols it uses, so it
can be rendered later without the external library.

## 4. Give an agent the local setup

Install the [agent skill](../README.md#agent-skill-codex-and-claude-code), or ask
the agent to read `skills/proficad-schematic/SKILL.md` in your checkout.
Then give it the absolute checkout and library paths, for example:

> Use the proficad-schematic skill in /home/alex/pcad. Draw using the stock
> library at /home/alex/.pcad/proficad-lib. Set PCAD_LIB to that directory for
> every search, pins, and build command. Search the stock paths, inspect the
> pins, build the schematic, run verify until it passes, render it, and inspect
> the image. Save outputs outside the pcad checkout.

Environment variables set in one terminal do not automatically reach an
already-running agent or a later tool invocation. On POSIX shells the agent can
prefix each command explicitly:

```bash
PCAD_LIB="$HOME/.pcad/proficad-lib" python3 "$HOME/pcad/pcad.py" search resistor
```

On PowerShell, set `$env:PCAD_LIB` in the same invocation as the Python command.
To return to the bundled library, use `unset PCAD_LIB` on POSIX shells or
`Remove-Item Env:PCAD_LIB` on PowerShell.

## Troubleshooting

- **Library not found / no symbols copied:** locate the folder containing the
  `.ppd`/`.picd` category tree and pass its full path as the source. `import-lib`
  cannot extract an installer EXE or ZIP by itself; extract the ZIP first.
- **Search returns nothing:** confirm `PCAD_LIB` points to the imported library,
  is set in this invocation, and uses an absolute path. Search uses AND matching
  on paths; start with a single word appropriate to your library's language.
- **Symbol not found:** use the exact library-relative path returned by `search`,
  without its extension. Stock and bundled paths differ.
- **Wires miss pins / verification fails:** run `pins` against the same library
  used for `build`, wire with `REF.pin` endpoints, and reroute around symbol
  bodies. Do not assume another library's pin numbering or dimensions.

## Keep the stock files local

Do not commit or upload the ZIP, installer, extracted library, or imported stock
files to this repository. This project's MIT license does not relicense those
files. ProfiCAD's [license terms](https://www.proficad.com/eula.aspx) govern its
software and supplied assets.

Generated `.sxe` drawings contain embedded symbol definitions: do not publish
stock-based `.sxe` files here as examples either. Use the bundled library for
repository examples. This tutorial publishes instructions and a JSON spec,
without publishing the stock symbol files.
