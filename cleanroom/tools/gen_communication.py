#!/usr/bin/env python3
"""Generate the communication batch (EN 60617) as .ppd files.

Clean-room: drawn from EN/IEC 60617 knowledge + the spec facts only. Sections:
  09 telecommunications (switching, telegraph apparatus/repeaters, telephone
  sets, transducer type marks, magnetic/recording heads), 10 (antennas, radio
  stations), 11 (CATV distribution). Dispatch is keyed on the EN 60617 item
  code (e.g. 10-04-01) which is stable across the messy English names.

Run: python3 gen_communication.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw_lib as dl
import helpers_communication as H

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = os.path.join(ROOT, "cleanroom", "spec", "batch_communication.json")
LIBDIR = os.path.join(ROOT, "cleanroom", "lib")


def code(rec):
    return rec["standard_normalized"][-8:]        # "NN-NN-NN"


def draw(rec):
    c = code(rec)

    # ---- antennas (10-04 / 10-05) ----
    ant_q = {
        "10-04-01": None,
        "10-04-04": H.q_horizontal,
        "10-04-09": H.q_turnstile,
        "10-04-02": H.q_circular,
        "10-04-03": H.q_rot_azimuth,
        "10-04-05": H.q_rot_elevation,
        "10-04-06": H.q_df,
        "10-04-07": H.q_vertical_dir,
    }
    if c in ant_q:
        p = H.antenna(rec, ant_q[c])
        if rec["markings"]:
            p.marking(rec["markings"], cx=rec["size"]["w"] / 2.0 - 12,
                      cy=0, bodyw=20, bodyh=rec["size"]["h"])
        return p

    pins = [(q["x"], q["y"]) for q in rec["pins"]]
    w, h = rec["size"]["w"], rec["size"]["h"]
    if c == "10-05-05":
        return H.dipole(pins)
    if c == "10-05-06":
        return H.folded_dipole(pins, w, h)
    if c == "10-05-07":
        return H.yagi(pins, w, h)
    if c == "10-05-09":                               # folded dipole + balun/coax
        p = dl.Ppd()
        xr, yr = 62, 18
        p.line(-xr, -yr, xr, -yr)                      # folded dipole loop (top)
        p.line(-xr, yr, xr, yr)
        p.arc(-xr - yr, -yr, -xr + yr, yr, 0, -yr, 0, yr)
        p.arc(xr - yr, -yr, xr + yr, yr, 0, yr, 0, -yr)
        p.line(-10, yr, -10, 60)                       # down to balun
        p.line(10, yr, 10, 60)
        p.circle(0, 72, 12)                            # balun
        p.line(0, 84, pins[0][0], pins[0][1])          # coax feeder
        H.add_outlets(p, pins)
        return p
    if c == "10-05-01":
        return H.loop_antenna(pins, w, h)
    if c == "10-05-03":
        return H.counterpoise(pins, w, h)
    if c == "10-05-08":
        return H.balun(pins, w, h)
    if c == "10-05-11":
        return H.horn_antenna(pins, w, h)
    if c == "10-05-13":
        return H.parabolic(w, h)
    if c == "10-05-14":
        return H.horn_reflector(w, h)
    if c == "10-05-12":
        return H.cheese_reflector(pins, w, h)
    if c == "10-05-02":
        return H.rhombic(pins, w, h)
    if c == "10-05-10":
        return H.slot_antenna(pins, w, h)

    # ---- radio stations (10-06) ----
    rs_mode = {
        "10-06-01": "plain", "10-06-02": "txrx", "10-06-03": "rx",
        "10-06-04": "tx", "10-06-05": "txrx", "10-06-06": "tx",
        "10-06-07": "txrx", "10-06-13": "txrx",
    }
    if c in rs_mode:
        return H.radio_station(rec, rs_mode[c])
    if c == "10-06-08":
        return H.passive_relay(w, h)
    if c == "10-06-09":
        return H.space_station(rec, "plain")
    if c == "10-06-10":
        return H.space_station(rec, "active")
    if c == "10-06-11":
        return H.space_station(rec, "passive")

    # ---- telephone sets (09-05) ----
    tel_feat = {
        "09-05-01": None, "09-05-04": H.f_dial, "09-05-09": H.f_loudspeaker,
        "09-05-10": H.f_amplifier, "09-05-08": H.f_ringer, "09-05-07": H.f_pay,
        "09-05-06": H.f_keys, "09-05-12": H.f_twolines, "09-05-11": None,
        "09-05-03": lambda p, l, t, r, b, w, h: H.f_battery(p, l, t, r, b, w, h, local=False),
        "09-05-02": lambda p, l, t, r, b, w, h: H.f_battery(p, l, t, r, b, w, h, local=True),
    }
    if c in tel_feat:
        return H.telephone(rec, tel_feat[c])

    # ---- heads (09-09) ----
    if c == "09-09-09":                               # transducer head (0 pins)
        return H.head(rec, gaps=1)
    if c == "09-09-13":                               # n tracks
        return H.head(rec, gaps=3)
    if c in ("09-09-12", "09-09-17"):                 # erasing head
        return H.head(rec, gaps=1, extra=H.head_erase_mark)
    if c == "09-09-18":                               # erasing form 2 (simplified)
        return H.head(rec, gaps=1)
    if c == "09-09-10":                               # stylus stereophonic
        return H.head(rec, gaps=2, extra=H.head_stylus)
    if c == "09-09-11":                               # light sensitive
        return H.head(rec, gaps=1, extra=H.head_light)
    if c in ("09-09-15", "09-09-16"):                 # magnetic writing mono
        return H.head(rec, gaps=1)
    if c in ("09-09-19", "09-09-20"):                 # write/read/erase mono
        return H.head(rec, gaps=2)
    if c == "09-09-22":                               # SAW transducer
        return H.saw_transducer(pins, w, h)

    # ---- transducer type marks (09-08) ----
    if c == "09-08-11":                               # SAW
        return H.saw_transducer(pins, w, h)
    if c.startswith("09-08-"):
        return H.type_mark(rec)

    # ---- telegraph apparatus & repeaters (09-01/02/06/07) ----
    if c == "09-01-01":
        return H.connecting_stage(w, h)
    if c == "09-02-01":
        return H.auto_switch(rec)
    if c == "09-06-01":                               # telegraph transmitter
        return H.apparatus(rec, inner=H.inner_keyboard)
    if c == "09-06-02":                               # transmit+receive simplex
        return H.apparatus(rec, inner=H.inner_tape)
    if c == "09-06-03":                               # tape printer + keyboard
        return H.apparatus(rec, inner=H.inner_tape)
    if c == "09-06-04":                               # page-printing receiver
        return H.apparatus(rec, inner=H.inner_printer)
    if c == "09-06-05":                               # facsimile receiver
        return H.apparatus(rec, inner=H.inner_fax)
    if c == "09-06-07":                               # keyboard perforator
        return H.apparatus(rec, inner=H.inner_keyboard)
    if c in ("09-07-01", "09-07-02", "09-07-03", "09-07-04"):
        # telegraph repeater = a large amplifier triangle with its marking(s)
        p = dl.Ppd()
        p.polygon([(-w / 2.0, -h / 2.0), (-w / 2.0, h / 2.0), (w / 2.0, 0)])
        if rec["markings"]:
            p.marking(rec["markings"], cx=-w / 6.0, cy=0, bodyw=w * 0.5, bodyh=h)
        for (x, y) in pins:
            if x < -w / 2.0:
                p.line(-w / 2.0, y, x, y)
            elif x > w / 2.0:
                p.line(w / 2.0, y, x, y)
            p.outlet(x, y)
        return p

    # ---- CATV distribution (11-05 .. 11-10) ----
    if c == "11-06-04":
        return H.amp_triangle(rec, inner_dir="return")
    if c == "11-06-02":
        return H.amp_triangle(rec, inner_dir="bridge")
    if c == "11-06-01":
        return H.bridge_amp(rec)
    if c == "11-05-01":
        return H.head_end(rec, local_antenna=True)
    if c == "11-05-02":
        return H.head_end(rec, local_antenna=False)
    if c == "11-07-01":
        return H.splitter(rec)
    if c == "11-07-03":
        return H.directional_coupler(rec)
    if c == "11-10-01":
        return H.line_power_unit(rec)
    if c == "11-10-03":
        return H.injection_point(rec)
    if c == "11-09-01":                               # equalizer
        return dl.body_rect(rec["markings"], pins, w, h, inner=H.eq_curve("eq"))
    if c == "11-09-02":                               # variable equalizer
        p = dl.body_rect(rec["markings"], pins, w, h, inner=H.eq_curve("eq"))
        from draw_lib import arrow
        arrow(p, -w / 2.0, h / 2.0, w / 2.0, -h / 2.0)
        return p
    if c == "11-09-03":                               # attenuator (map symbol)
        return dl.body_rect(rec["markings"], pins, w, h,
                            inner=H.eq_curve("attenuator"))

    # fallback: plain labelled box
    return dl.body_rect(rec["markings"], pins, w, h)


def main():
    recs = json.load(open(SPEC))
    n = 0
    for rec in recs:
        p = draw(rec)
        xml = p.document(rec["name"], rec["designation"], rec["standard"], rec["id"])
        rel = dl.slug_path(rec["category"], rec["name"])
        out = os.path.join(LIBDIR, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(xml)
        n += 1
    print(f"wrote {n} .ppd files under {LIBDIR}")


if __name__ == "__main__":
    main()
