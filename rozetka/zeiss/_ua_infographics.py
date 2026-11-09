"""Ukrainian versions of Zeiss infographics (samples) + count tags on multi-pack main photos."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

F = '/tmp/claude-0/-home-claude/bffc3b6a-1a0c-569d-a9cf-e38ebb023b76/scratchpad/fonts/'
def font(w, size):
    return ImageFont.truetype(F + ('FiraSansXC-%s.ttf' % w if w in ('800', '900') else 'FiraSans-%s.ttf' % w), size)

def to_square(im, S=1280):
    im = im.convert('RGB')
    sc = S / max(im.size)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    c = Image.new('RGB', (S, S), 'white')
    c.paste(im, ((S - im.width) // 2, (S - im.height) // 2))
    return c

def fit(draw, text, w, maxsize, minsize=14, weight='400'):
    s = maxsize
    while s > minsize and draw.textlength(text, font=font(weight, s)) > w:
        s -= 1
    return font(weight, s)

# ---------- sample 1: spray «Safe to use on:» (970x600) ----------
def spray_safe(src, out):
    im = Image.open(src).convert('RGB')
    a = np.asarray(im)
    blue = tuple(int(v) for v in a[20, 20])
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 432, im.height), fill=blue)
    x0, y = 34, 128
    d.text((x0, y), 'Безпечний для:', font=font('700', 40), fill='white')
    y += 66
    items = ['Лінз з антиблисковим покриттям', 'Лінз із захистом від синього світла',
             'Окулярів з діоптріями', 'Окулярів для читання', 'Сонцезахисних окулярів',
             "Об'єктивів фотокамер", 'Біноклів', 'Окулярів для плавання і лиж']
    f = fit(d, max(items, key=len), 432 - x0 - 30, 22, weight='400')
    for t in items:
        d.rectangle((x0 + 2, y + 9, x0 + 9, y + 16), fill=(245, 196, 0))
        d.text((x0 + 22, y), t, font=f, fill='white')
        y += 34
    to_square(im).save(out, quality=90)

# ---------- sample 2: wipes «Works on all lens surfaces» (1250x1211) ----------
def wipes_surfaces(src, out):
    im = Image.open(src).convert('RGB')
    a = np.asarray(im).astype(int)
    W, H = im.size
    d = ImageDraw.Draw(im)
    head = tuple(int(v) for v in a[945, 700])
    # icon centres from the icon row
    row = (a[1084:1135].min(axis=2) < 150).any(axis=0)
    lab, n = ndimage.label(ndimage.binary_dilation(row, iterations=12))
    centres = [int(np.mean(np.where(lab == i)[0])) for i in range(1, n + 1)]
    # clear the English text bands (white area under the photo only)
    for y0, y1 in ((905, 978), (988, 1030), (1170, H)):
        d.rectangle((0, y0, W, y1), fill='white')
    t = 'Для всіх оптичних поверхонь'
    f = fit(d, t, W - 120, 52, weight='700')
    d.text((W / 2, 940), t, font=f, fill=head, anchor='mm')
    t = 'Серветки ZEISS Lens Wipes підходять для всіх оптичних лінз:'
    f = fit(d, t, W - 140, 30, weight='400')
    d.text((W / 2, 1008), t, font=f, fill=(40, 40, 40), anchor='mm')
    labels = ['Окуляри', 'Сонцезахисні окуляри', 'Біноклі', "Об'єктиви", 'Окуляри для плавання', 'Гірськолижні маски']
    for cx, t in zip(centres, labels):
        f = font('400', 21)
        words = t.split(' ', 1) if d.textlength(t, font=f) > 170 else [t]
        for k, line in enumerate(words):
            d.text((cx, 1180 + k * 22 - (11 if len(words) == 2 else 0)), line, font=f, fill=(40, 40, 40), anchor='mm')
    # blue circle on the photo (measured: x 899-1069, top y 284): recolour inside, write Ukrainian text
    ccx, ccy, r = 984, 369, 84
    d.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), fill=(4, 137, 214))
    tag = Image.new('RGBA', (2 * r, 2 * r), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    for k, line in enumerate(['Для всіх', 'лінз']):
        td.text((r, r - 17 + k * 36), line, font=font('700', 31), fill='white', anchor='mm')
    tag = tag.rotate(15, resample=Image.BICUBIC)
    im.paste(tag, (ccx - r, ccy - r), tag)
    bx0 = by0 = bx1 = by1 = 0
    to_square(im).save(out, quality=90)
    return centres, (bx0, by0, bx1, by1)

# ---------- count tag on multi-pack main photos ----------
YELLOW = (245, 196, 0)
def count_tag(src_clean, tags, out, S=1280):
    a = np.asarray(Image.open(src_clean).convert('RGB')).astype(int)
    m = a.min(axis=2) < 236
    ys, xs = np.where(m)
    crop = Image.fromarray(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype('uint8'))
    f = font('900', 62)
    d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    widths = [int(d0.textlength(t, font=f)) + 60 for t in tags]
    th, gap, right, bottom = 93, 13, S - 56, 1225
    top_tags = bottom - len(tags) * th - (len(tags) - 1) * gap
    # product box: full width above the tag column; never touches a tag
    box_w, box_h = S - 140, top_tags - 40 - 70
    sc = min(box_w / crop.width, box_h / crop.height)
    crop = crop.resize((round(crop.width * sc), round(crop.height * sc)), Image.LANCZOS)
    c = Image.new('RGB', (S, S), 'white')
    c.paste(crop, ((S - crop.width) // 2, 70 + (box_h - crop.height) // 2))
    d = ImageDraw.Draw(c)
    y = top_tags
    for t, w in zip(tags, widths):
        d.rectangle((right - w, y, right, y + th), fill=YELLOW)
        d.text((right - w / 2, y + th / 2 + 2), t, font=f, fill=(20, 20, 20), anchor='mm')
        y += th + gap
    c.save(out, quality=93)
    return round(sc, 2)


if __name__ == '__main__':
    import json
    spray_safe('prom/6644675902.jpg', 'site/img/ua_safe_spray.jpg')
    print(wipes_surfaces('prom/5083195553.jpeg', 'site/img/ua_surfaces_wipes.jpg'))
    TAGS = {3047099061: ['90 ШТ'], 2919633966: ['300 ШТ'], 3008710945: ['440 ШТ'], 2484481287: ['80 ШТ'],
            2471197512: ['2 × 120 МЛ'], 2470829883: ['2 × 60 МЛ'], 2741833324: ['2 × 60 МЛ'], 2613250123: ['2 × 60 МЛ'],
            2741821450: ['2 × 120 МЛ', '2 СЕРВЕТКИ'], 2741818048: ['2 × 120 МЛ'], 2606788862: ['2 × 120 МЛ', '2 СЕРВЕТКИ'],
            2606783239: ['2 × 120 МЛ'], 2589093253: ['2 ШТ']}
    for pid, t in TAGS.items():
        print(pid, t, count_tag(f'out/main_p{pid}.jpg', t, f'out/main2_p{pid}.jpg'))
    json.dump({str(k): v for k, v in TAGS.items()}, open('tags.json', 'w'), ensure_ascii=False)
