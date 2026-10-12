#!/usr/bin/env python3
"""Generate the basics_1 batch (the most-used EN/IEC 60617 school symbols) as
.ppd files under cleanroom/lib/.

Clean-room: drawn from the EN/IEC 60617 standard + the spec facts only.
Families: rotating machines (06-04), instrument transformers (06-09),
conductors/ducts (03), switching contacts / push buttons / rotary + slide
switches / change-over (07-02..07-08), make/break/contactor contacts (07-13-02),
circuit breakers (07-13-08), disconnectors (07-12), RCD/RCBO blocks and
qualifier labels (07-13-10), thermal overload relays (07-21), logic gates (12).

Shared primitives: draw_lib.py; batch glyphs: helpers_basics_1.py (which reuses
helpers_switching_protection + helpers_machines_power so the look matches).
Run: python3 gen_basics_1.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
import helpers_switching_protection as sw
import helpers_basics_1 as hb

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_basics_1.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def pins_of(rec):
    return [(p["x"], p["y"]) for p in rec["pins"]]


def code(rec):
    return rec["standard"].split(":", 1)[1].strip()


def draw(rec):
    name = rec["name"].lower()
    cat = rec["category"]
    c = code(rec)
    pins = pins_of(rec)
    w, h = rec["size"]["w"], rec["size"]["h"]
    mk = rec["markings"]

    # --- section 03: conductors / ducts ---------------------------------
    if c == "03-01-01":
        return hb.conductor(w, h)
    if c == "03-04-01":
        return hb.cable_duct(w, h)

    # --- section 06: rotating machines ----------------------------------
    if c == "06-04-01":
        letter = "G" if "generator" in name else "M"
        cur = "ac" if " ac" in name or name.endswith("ac") or "ac," in name else \
              ("dc" if "dc" in name else None)
        p = hb.machine(pins, w, h, letter, cur)
        if "motor ac" in name:                       # 1-phase mark, above the ~
            p.text(0, 4, "1", size=46, al=9)
        return p
    if c == "06-09-05":
        return hb.current_transformer(pins)
    if c == "06-09-01":
        return hb.transformer_2w_screen(pins)

    # --- logic gates (section 12) ---------------------------------------
    if c in ("12-05-01", "12-05-02", "12-09-01"):
        negate = c in ("12-05-02", "12-09-01")       # NAND / INVERTOR
        qual = "1" if c == "12-09-01" else "&"
        return hb.gate(pins, w, h, qual, negate=negate)

    # --- SSR -------------------------------------------------------------
    if name == "ssr":
        return hb.ssr(pins, w, h, mk)

    # --- thermal overload relays (07-21-08) -----------------------------
    if c == "07-21-08":
        if len(pins) > 2:
            return hb.thermal_multi(pins, w, h)
        return hb.thermal(pins, w, h)

    # --- RCD / RCBO (07-13-10) ------------------------------------------
    if c == "07-13-10":
        if not pins:                                 # qualifier labels
            kind = ("ac" if name.startswith("type ac") else
                    "a" if name.startswith("type a") else
                    "b" if name.startswith("type b") else None)
            return hb.rcd_label(w, h, markings=mk, kind=kind)
        mag = "magneto" in name
        return hb.module_block(pins, w, h, magneto_thermal=mag, markings=mk)

    # --- disconnectors (07-12-01) ---------------------------------------
    if c == "07-12-01":
        kind = "fuse_disc" if "fuse" in name else "disconnector"
        return hb.contact(pins, w, h, kind=kind)

    # --- circuit breakers (07-13-08) ------------------------------------
    if c == "07-13-08":
        return hb.contact(pins, w, h, kind="breaker")

    # --- contactor main contact (07-13-02) ------------------------------
    if c == "07-13-02":
        return hb.contact(pins, w, h, kind="contactor")

    # --- change-over (07-02-04) -----------------------------------------
    if c == "07-02-04":
        return hb.changeover(pins, w, h)

    # --- flasher / self-interrupting (07-05-05) -------------------------
    if c == "07-05-05":
        p = hb.contact(pins, w, h, kind="make")
        sw.delay_cup(p, pins[0][0] + max(14, w) / 2.0, 0, opening_up=False)
        return p

    # --- reed switch (07-05-01) -----------------------------------------
    if c == "07-05-01":
        return hb.reed(pins, w, h)

    # --- rotary / slide switches (07-02-01) -----------------------------
    if c == "07-02-01":
        if "rotary" in name:
            return hb.rotary(pins, w, h)
        if "slide" in name:
            return hb.slide(pins, w, h)
        if "mom-off-mom" in name:
            return hb.mom_off_mom(pins, w, h)

    # --- push buttons -----------------------------------------------------
    if c in ("07-07-01", "07-07-02"):
        is_break = c == "07-07-02"
        if "pushbutton switch" in name:              # horizontal 2-terminal form
            return hb.hpushbutton(pins, w, h, is_break)
        if "push button" in name:                    # vertical form + button glyph
            return hb.actuated_contact(pins, w, h, sw.act_pushbutton, 14,
                                       is_break=is_break)

    # --- position / limit switches (07-08) ------------------------------
    if c in ("07-08-01", "07-08-02"):
        is_break = c == "07-08-02" or "brake" in name
        return hb.actuated_contact(pins, w, h, sw.act_roller, 7, is_break=is_break)

    # --- pull / turn switches, make/break (07-02-02 / 07-02-03) ---------
    if "pull switch" in name:
        return hb.actuated_contact(pins, w, h, sw.act_pull, 8,
                                   is_break="break" in name or "brake" in name)
    if "turn switch" in name:
        return hb.actuated_contact(pins, w, h, sw.act_turn, 12,
                                   is_break="break" in name or "brake" in name)

    # --- plain make / break contacts ------------------------------------
    is_break = c == "07-02-03" or "break" in name or "brake" in name
    # very wide single-pole switches keep a clean ~30 deg blade + handle
    mr = 48 if (len(pins) == 2 and w > 160) else None
    return hb.contact(pins, w, h, kind="make", is_break=is_break, max_reach=mr)


def main():
    recs = json.load(open(SPEC))
    collisions = []
    written = 0
    # Never clobber another batch's file. A file at our path is "ours" (safe to
    # overwrite) only if its lG GUID == lib_guid(our id); anything else is a
    # real collision with another batch and is reported, not overwritten.
    for rec in recs:
        rel = dl.slug_path(rec["category"], rec["name"])
        out = os.path.join(LIBDIR, rel)
        if os.path.exists(out):
            m = re.search(r'lG="([^"]+)"', open(out).read())
            if not m or m.group(1) != dl.lib_guid(rec["id"]):
                collisions.append(rel)
                continue
        p = draw(rec)
        xml = p.document(rec["name"], rec["designation"], rec["standard"], rec["id"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(xml)
        written += 1
    print(f"wrote {written}/{len(recs)} .ppd files under {LIBDIR}")
    if collisions:
        print(f"PATH COLLISIONS with other batches ({len(collisions)}):")
        for rel in collisions:
            print("  ", rel)


if __name__ == "__main__":
    main()
