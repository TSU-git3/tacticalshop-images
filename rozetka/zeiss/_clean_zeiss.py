"""Rozetka main photos for Zeiss: our Prom first photo (card template) without the Zeiss logo,
the «DESIGNED IN GERMANY» tag, the black point tags and the yellow count tag.

Only whole card elements are removed, found as separate blobs of non-white pixels:
  - logo: blob inside the top-left corner (x < 330, y < 210)
  - origin tag: dark solid blob in the top band (y1 < 210), right half
  - point / count tags: solid rectangles 70-115 px high in the lower part (y0 > 650)
A blob that touches the product is never cut: if a tag sits within 6 px of product pixels the
file is refused and listed for hand work. The product is then cropped (with its soft shadow)
and centred on white 1280x1280, as large as fits with a 70 px margin.
"""
import sys, json, glob
import numpy as np
from PIL import Image
from scipy import ndimage

S, PAD = 1280, 70


def nonwhite(a, t=236):
    return a.min(axis=2) < t


def clean(src):
    im = Image.open(src).convert('RGB')
    if im.size != (1280, 1280):
        im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.int16)
    H, W = a.shape[:2]
    m = nonwhite(a)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    remove = np.zeros(n + 1, bool)
    card = np.zeros(n + 1, bool)
    why = []
    for i, sl in enumerate(objs, 1):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        fill = sizes[i - 1] / (h * w)
        region = a[sl][lab[sl] == i]
        dark = (region.max(axis=1) < 70).mean()
        yel = ((region[:, 0] > 200) & (region[:, 1] > 160) & (region[:, 2] < 90)).mean()
        if x1 < 330 and y1 < 210:
            remove[i] = True; card[i] = True; why.append(('logo', x0, y0, w, h))
        elif y1 < 210 and x0 > 560 and h >= 50 and dark > 0.5:
            remove[i] = True; card[i] = True; why.append(('origin', x0, y0, w, h))
        elif y0 > 650 and 70 <= h <= 115 and w >= 90 and fill > 0.5 and (dark > 0.55 or yel > 0.55):
            remove[i] = True; card[i] = True; why.append(('tag', x0, y0, w, h))
        elif sizes[i - 1] < 25:
            remove[i] = True  # dust / jpeg specks
    # pieces that sit inside a removed card element (flag, letters, yellow square) go with it
    boxes = [objs[i - 1] for i in range(1, n + 1) if card[i]]
    for i, sl in enumerate(objs, 1):
        if card[i]:
            continue
        for b in boxes:
            if sl[0].start >= b[0].start - 4 and sl[0].stop <= b[0].stop + 4 and sl[1].start >= b[1].start - 4 and sl[1].stop <= b[1].stop + 4:
                remove[i] = True; card[i] = True
                break
    rm = remove[lab]
    keep = m & ~rm
    # safety: removed card elements must not touch product pixels
    near = ndimage.binary_dilation(card[lab] & m, iterations=6) & keep
    if near.sum() > 20:
        ys, xs = np.where(near)
        raise ValueError(f'{why} | tag touches product near x{xs.min()}-{xs.max()} y{ys.min()}-{ys.max()}')
    ys, xs = np.where(keep)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = a.copy()
    out[rm] = 255
    crop = Image.fromarray(out[y0:y1, x0:x1].astype('uint8'))
    sc = min((S - 2 * PAD) / crop.width, (S - 2 * PAD) / crop.height)
    crop = crop.resize((round(crop.width * sc), round(crop.height * sc)), Image.LANCZOS)
    c = Image.new('RGB', (S, S), 'white')
    c.paste(crop, ((S - crop.width) // 2, (S - crop.height) // 2))
    return c, why, sc


if __name__ == '__main__':
    P = json.load(open('prom_items.json'))
    rep = {}
    for p in P:
        iid = p[6][0].split('_')[0]
        src = glob.glob(f'prom/{iid}.*')[0]
        try:
            c, why, sc = clean(src)
            c.save(f'out/main_p{p[0]}.jpg', quality=93)
            rep[p[0]] = {'ok': True, 'removed': why, 'scale': round(sc, 2)}
        except Exception as e:
            rep[p[0]] = {'ok': False, 'err': str(e)}
    json.dump(rep, open('clean_report.json', 'w'), indent=1)
    for k, v in rep.items():
        import collections; print(k, 'OK' if v['ok'] else 'FAIL', v.get('err', '')[-90:], dict(collections.Counter(w[0] for w in v.get('removed', []) if w[3]*w[4]>400)), v.get('scale', ''))
