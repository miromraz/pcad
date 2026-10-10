#!/usr/bin/env python3
"""Compare a reference schematic picture with a recreated one.

usage: compare.py <original.png> <ours.png> <panel_out.png>

Both images are cropped to their ink (non-white) bounding box and scaled to the
same size, then ink pixels are matched with a small tolerance. Prints:
  match  = F1 of ink pixels (1.0 = every line/label lands on the original's)
  scale  = ours/original bbox size (shows if the export zoom differs)
and writes a panel: original | ours | overlay (black=both, red=original only,
blue=ours only).
"""
import sys
from PIL import Image, ImageFilter, ImageChops

TOL = 5   # MaxFilter size in px -> ~2 px slack for antialiasing/rounding


def ink(im):
    """1-bit mask of drawn pixels (dark or coloured) on a white background."""
    g = im.convert("RGB")
    lum = g.convert("L").point(lambda v: 255 if v < 200 else 0)
    r, gg, b = g.split()
    sat = ImageChops.difference(ImageChops.lighter(ImageChops.lighter(r, gg), b),
                                ImageChops.darker(ImageChops.darker(r, gg), b))
    col = sat.point(lambda v: 255 if v > 60 else 0)
    return ImageChops.lighter(lum, col).convert("1")


def crop(im):
    m = ink(im)
    box = m.getbbox()
    return im.crop(box), m.crop(box)


def count(m):
    return m.convert("L").histogram()[255]


def main(a, b, out):
    A, B = Image.open(a), Image.open(b)
    Ai, Am = crop(A)
    Bi, Bm = crop(B)
    size = Am.size
    Bi = Bi.resize(size, Image.LANCZOS)
    Bm = ink(Bi)
    Ad = Am.convert("L").filter(ImageFilter.MaxFilter(TOL)).convert("1")
    Bd = Bm.convert("L").filter(ImageFilter.MaxFilter(TOL)).convert("1")
    a_hit = count(ImageChops.logical_and(Am, Bd))
    b_hit = count(ImageChops.logical_and(Bm, Ad))
    na, nb = count(Am), count(Bm)
    recall, prec = a_hit / max(na, 1), b_hit / max(nb, 1)
    f1 = 2 * recall * prec / max(recall + prec, 1e-9)
    print(f"match={f1:.3f}  recall={recall:.3f}  precision={prec:.3f}  "
          f"scale={crop(B)[1].size[0] / size[0]:.2f}x{crop(B)[1].size[1] / size[1]:.2f}")

    # overlay: black both, red original-only, blue ours-only
    ov = Image.new("RGB", size, "white")
    px = ov.load()
    am, bm, ad, bd = Am.load(), Bm.load(), Ad.load(), Bd.load()
    for y in range(size[1]):
        for x in range(size[0]):
            if am[x, y] and bd[x, y] or bm[x, y] and ad[x, y]:
                px[x, y] = (0, 0, 0)
            elif am[x, y]:
                px[x, y] = (230, 0, 0)
            elif bm[x, y]:
                px[x, y] = (0, 80, 255)
    pad = 20
    W, H = size
    panel = Image.new("RGB", (3 * W + 4 * pad, H + 2 * pad), (235, 235, 235))
    for i, im in enumerate((Ai.convert("RGB"), Bi.convert("RGB"), ov)):
        panel.paste(im, (pad + i * (W + pad), pad))
    panel.save(out)
    return f1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
