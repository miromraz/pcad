#!/usr/bin/env python3
"""Verify a clean-room .ppd batch against its spec and render a contact sheet.

For every record in a batch_*.json:
  * the .ppd exists at the expected path (STYLE.md §12),
  * it parses and is accepted by pcad.load_ppd (no error),
  * outlet count / order / positions equal the spec pins exactly,
  * the drawn bounding box (pcad._ppd_box) is within +/-15% of spec size,
  * it renders via pcadrender.
Then it builds two contact-sheet PNGs (symbols, and a pin-debug overlay with
spec pins as red dots) and prints a pass/fail table.

Renders are SEQUENTIAL (this box OOMs with parallel renders).

Usage: python3 check_batch.py <batch.json> [--out DIR]
"""
import argparse
import json
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)      # pcad.py / pcadrender.py
sys.path.insert(0, HERE)      # draw_lib.py
import pcad
import pcadrender
import draw_lib as dl
from PIL import Image, ImageDraw, ImageFont

LIBDIR = os.path.join(ROOT, "cleanroom", "lib")
TOL = 0.15


def ppd_node(path):
    root = ET.parse(path).getroot()
    node = root.find(".//ppd")
    return root, node if node is not None else root


def check_record(rec):
    """Return dict with per-check booleans + details."""
    rel = dl.slug_path(rec["category"], rec["name"])
    path = os.path.join(LIBDIR, rel)
    res = {"rel": rel, "path": path, "exists": False, "load": False,
           "pins": False, "size": False, "render": False, "msg": ""}
    if not os.path.isfile(path):
        res["msg"] = "missing file"
        return res
    res["exists"] = True

    # accepted by pcad.load_ppd (no exception). pcad.LIB is bound at import time,
    # so point it at our library directly (env var alone is too late).
    old = pcad.LIB
    try:
        pcad.LIB = LIBDIR
        pcad.load_ppd(rel[:-4])            # strip .ppd
        res["load"] = True
    except SystemExit as e:
        res["msg"] = f"load_ppd rejected: {e}"
    except Exception as e:
        res["msg"] = f"load_ppd error: {e}"
    finally:
        pcad.LIB = old

    # outlets + box from the <ppd> node (same path the spec was extracted with)
    try:
        _, node = ppd_node(path)
        outs, box = pcad._ppd_box(node)
    except Exception as e:
        res["msg"] = f"parse/_ppd_box error: {e}"
        return res

    want = [(p["x"], p["y"]) for p in rec["pins"]]
    if outs == want:
        res["pins"] = True
    else:
        res["msg"] = f"pins {outs} != spec {want}"

    sw, sh = rec["size"]["w"], rec["size"]["h"]
    if box is None:
        gw = gh = 0
    else:
        gw, gh = box[2] - box[0], box[3] - box[1]
    res["gw"], res["gh"] = gw, gh

    def within(got, want):
        if want == 0:
            return got == 0
        return abs(got - want) <= TOL * want
    if within(gw, sw) and within(gh, sh):
        res["size"] = True
    elif res["pins"]:
        res["msg"] = res["msg"] or f"size {gw}x{gh} != spec {sw}x{sh}"
    return res


def render_png(path, out_png, debug_pins=None):
    """Render a .ppd to PNG. If debug_pins, inject red dots at those coords."""
    src = path
    if debug_pins:
        txt = open(path).read()
        dots = "".join(
            f'<ellipse left="{x-8}" top="{y-8}" right="{x+8}" bottom="{y+8}" '
            f'op-lw="2" op-fd="1" op-fc="255"/>' for (x, y) in debug_pins)
        txt = txt.replace("</layer>", dots + "</layer>", 1)
        fd, src = tempfile.mkstemp(suffix=".ppd")
        with os.fdopen(fd, "w") as f:
            f.write(txt)
    try:
        pcadrender.render(src, out_png)
    finally:
        if debug_pins and src != path:
            os.unlink(src)


def contact_sheet(records, results, out_png, title, debug=False):
    cell, pad, labelh = 200, 10, 24
    inner = cell - 2 * pad
    cols = int(math.ceil(math.sqrt(len(records))))
    rows = int(math.ceil(len(records) / cols))
    W, H = cols * cell, rows * (cell + labelh)
    sheet = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
    tmpdir = tempfile.mkdtemp()
    for i, (rec, res) in enumerate(zip(records, results)):
        cx, cy = (i % cols) * cell, (i // cols) * (cell + labelh)
        ok = res["exists"] and res["pins"] and res["size"] and res["render"]
        if res["exists"] and res["render"]:
            png = os.path.join(tmpdir, f"{i}.png")
            try:
                dp = [(p["x"], p["y"]) for p in rec["pins"]] if debug else None
                render_png(res["path"], png, dp)
                im = Image.open(png).convert("RGB")
                im.thumbnail((inner, inner))
                sheet.paste(im, (cx + (cell - im.width) // 2,
                                 cy + (inner - im.height) // 2 + pad))
            except Exception as e:
                draw.text((cx + pad, cy + pad), f"render err\n{e}"[:40], fill="red", font=font)
        # border + name
        border = (200, 200, 200) if ok else (220, 0, 0)
        draw.rectangle([cx, cy, cx + cell - 1, cy + cell + labelh - 1], outline=border)
        nm = rec["name"]
        nm = nm if len(nm) <= 34 else nm[:33] + "…"
        draw.text((cx + 4, cy + cell + 4), nm, fill="black", font=font)
    sheet.save(out_png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--out", default=os.path.join(ROOT, "cleanroom", "out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    records = json.load(open(a.batch))
    bname = os.path.splitext(os.path.basename(a.batch))[0]

    results = []
    for rec in records:
        res = check_record(rec)
        # render check (sequential)
        if res["exists"]:
            try:
                tmp = os.path.join(a.out, "_probe.png")
                pcadrender.render(res["path"], tmp)
                res["render"] = True
                os.path.exists(tmp) and os.unlink(tmp)
            except Exception as e:
                res["msg"] = res["msg"] or f"render error: {e}"
        results.append(res)

    # table
    cols = ("exists", "load", "pins", "size", "render")
    npass = 0
    print(f"\n{'name':52} " + " ".join(f"{c:7}" for c in cols) + " note")
    print("-" * 120)
    for rec, res in zip(records, results):
        ok = all(res[c] for c in cols)
        npass += ok
        marks = " ".join(f"{'ok' if res[c] else 'FAIL':7}" for c in cols)
        print(f"{rec['name'][:52]:52} {marks} {res['msg'][:40]}")
    print("-" * 120)
    print(f"PASS {npass}/{len(records)}   FAIL {len(records) - npass}/{len(records)}")

    sheet = os.path.join(a.out, f"{bname}_sheet.png")
    debug = os.path.join(a.out, f"{bname}_pins.png")
    contact_sheet(records, results, sheet, bname, debug=False)
    contact_sheet(records, results, debug, bname + " (pins)", debug=True)
    print(f"contact sheet: {sheet}")
    print(f"pin overlay:   {debug}")
    return 0 if npass == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
