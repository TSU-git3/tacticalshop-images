"""Rozetka main photos v2 (owner 8 Nov: v1 left white blocks over products).

Kiborg/Militex: our Prom card; remove ONLY the known card elements:
  - header band y < 180 (maker logo + «MADE IN UKRAINE» tag; the card script puts the
    product at y >= 191, checked per file below),
  - the solid tag rectangles that start at y >= 1000 (point tags, count tag).
  Each removed area is checked: no product pixels may touch it, else the file is refused.
Level 7 / Carinthia: the raw product photo (Prom photo 2, no tags at all); boots that are
  not sold with the item are cut off along the trouser hem (hand-traced polylines).
Then the product is cropped and placed centred, as large as fits, on white 1280x1280.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

S, PAD = 1280, 60


def nonwhite(a):
    return np.minimum(np.minimum(a[..., 0], a[..., 1]), a[..., 2]) < 238


def place(a, out):
    m = ndimage.binary_opening(nonwhite(a), iterations=1)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 30])
    ys, xs = np.where(keep)
    crop = Image.fromarray(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype('uint8'))
    sc = min((S - 2 * PAD) / crop.width, (S - 2 * PAD) / crop.height)
    crop = crop.resize((round(crop.width * sc), round(crop.height * sc)), Image.LANCZOS)
    c = Image.new('RGB', (S, S), 'white')
    c.paste(crop, ((S - crop.width) // 2, (S - crop.height) // 2))
    c.save(out, quality=93)


def card(src, out):
    a = np.asarray(Image.open(src).convert('RGB')).astype(int)
    nw = nonwhite(a)
    # header: product must not reach into it
    if nw[180:190].any():
        raise SystemExit(f'{src}: product reaches the header band')
    a[:180] = 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    blackish = (r < 40) & (g < 40) & (b < 40)
    yellow = (r > 220) & (g > 170) & (g < 220) & (b < 60)
    removed = 0
    for m in (blackish, yellow):
        lab, n = ndimage.label(m)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            if y0 < 1000 or not (80 <= y1 - y0 <= 110 and x1 - x0 >= 90) or (lab[sl] == i).mean() < 0.55:
                continue
            Y0, Y1, X0, X1 = max(y0 - 12, 0), min(y1 + 12, S), max(x0 - 12, 0), min(x1 + 12, S)
            ring = nonwhite(a[Y0:Y1, X0:X1]).copy()
            ring[y0 - Y0 - 3:y1 - Y0 + 3, x0 - X0 - 3:x1 - X0 + 3] = False
            if ring.sum():
                raise SystemExit(f'{src}: tag at {x0},{y0} touches the product')
            a[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = 255
            removed += 1
    place(a, out)
    return removed


def cut_below(a, poly, x_from, x_to, feather=2):
    """White out everything below the hem polyline between x_from and x_to."""
    xs = np.array([p[0] for p in poly], float)
    ys = np.array([p[1] for p in poly], float)
    for x in range(x_from, x_to):
        y = int(round(np.interp(x, xs, ys)))
        a[y:, x] = 255
        for k in range(1, feather + 1):            # soft edge, no hard white step
            if y - k >= 0:
                a[y - k, x] = (a[y - k, x] * (k / (feather + 1)) + 255 * (1 - k / (feather + 1))).astype(int)
    return a


def raw(src, out, cuts=()):
    a = np.asarray(Image.open(src).convert('RGB')).astype(int)
    for poly, x_from, x_to in cuts:
        a = cut_below(a, poly, x_from, x_to)
    place(a, out)
