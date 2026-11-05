"""First-photo cards for Kiborg / Militex listings (style = live ESS/Zeiss/sleeping-bag cards)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

S = 1280
M = 56            # margin
TAG_H = 93
GAP = 13
BOTTOM = 1225
FD = '/home/claude/kb/fonts/'
F900 = {s: ImageFont.truetype(FD + f'fsec-{s}-900.ttf', 62) for s in ('latin', 'cyrillic')}
F900_56 = {s: ImageFont.truetype(FD + f'fsec-{s}-900.ttf', 56) for s in ('latin', 'cyrillic')}
FLOGO = {s: ImageFont.truetype(FD + f'fsec-{s}-900.ttf', 96) for s in ('latin', 'cyrillic')}
BLACK = (17, 17, 17)
YEL = (245, 196, 0)
WHITE = (255, 255, 255)


def is_cyr(ch):
    return 'Ѐ' <= ch <= 'ӿ'


def runs(text):
    out = []
    for ch in text:
        k = 'cyrillic' if is_cyr(ch) else 'latin'
        if out and out[-1][0] == k:
            out[-1][1] += ch
        else:
            out.append([k, ch])
    return out


def text_w(text, fonts):
    return sum(fonts[k].getlength(t) for k, t in runs(text))


def draw_text(d, xy, text, fonts, fill):
    x, y = xy
    for k, t in runs(text):
        d.text((x, y), t, font=fonts[k], fill=fill, anchor='ls')
        x += fonts[k].getlength(t)


def point_tag(d, x, y_top, text):
    w = 73 + int(text_w(text, F900)) + 30
    d.rectangle([x, y_top, x + w, y_top + TAG_H], fill=BLACK)
    d.rectangle([x + 30, y_top + 36, x + 30 + 23, y_top + 36 + 22], fill=YEL)
    draw_text(d, (x + 73, y_top + 69), text, F900, WHITE)
    return w


def origin_tag(d, img):
    text = 'MADE IN UKRAINE'
    tw = int(text_w(text, F900_56))
    flag_w, flag_h = 54, 36
    w = 30 + flag_w + 18 + tw + 30
    x1 = S - M
    x0 = x1 - w
    d.rectangle([x0, 68, x1, 161], fill=BLACK)
    fy = 68 + (93 - flag_h) // 2
    d.rectangle([x0 + 30, fy, x0 + 30 + flag_w, fy + flag_h // 2], fill=(0, 87, 183))
    d.rectangle([x0 + 30, fy + flag_h // 2, x0 + 30 + flag_w, fy + flag_h], fill=(255, 215, 0))
    draw_text(d, (x0 + 30 + flag_w + 18, 68 + 66), text, F900_56, WHITE)
    return x0


def count_tag(d, text):
    w = 30 + int(text_w(text, F900)) + 30
    x1 = S - M
    d.rectangle([x1 - w, BOTTOM - TAG_H, x1, BOTTOM], fill=YEL)
    draw_text(d, (x1 - w + 30, BOTTOM - TAG_H + 69), text, F900, BLACK)
    return x1 - w


def place_logo(img, brand):
    if brand == 'kiborg':
        lg = Image.open('/home/claude/kb/assets/kiborg_logo.png')
        w = 320
        lg = lg.resize((w, round(lg.height * w / lg.width)), Image.LANCZOS)
        img.paste(lg, (M, 52 + (93 - lg.height) // 2 + 16), lg)
        return 52 + 93 + 16
    # Militex: owner's logo file (5 Nov), centred on the origin tag's line
    lg = Image.open('/home/claude/kb/assets/militex_logo.png')
    w = 300
    lg = lg.resize((w, round(lg.height * w / lg.width)), Image.LANCZOS)
    y = 114 - lg.height // 2
    img.paste(lg, (M, y), lg)
    return y + lg.height


def fit(prod, box):
    x0, y0, x1, y1 = box
    sc = min((x1 - x0) / prod.width, (y1 - y0) / prod.height)
    return sc


def make(pid, brand, points, count=None, out_dir='/home/claude/kb/out'):
    img = Image.new('RGB', (S, S), WHITE)
    d = ImageDraw.Draw(img)
    header_bottom = place_logo(img, brand)
    origin_tag(d, img)
    # tags bottom-left, last tag ends at BOTTOM
    n = len(points)
    y = BOTTOM - n * TAG_H - (n - 1) * GAP
    tags_top = y
    tag_right = 0
    for p in points:
        w = point_tag(d, M, y, p)
        tag_right = max(tag_right, M + w)
        y += TAG_H + GAP
    count_left = S
    if count:
        count_left = count_tag(d, count)
    prod = Image.open(f'/home/claude/kb/cut/{pid}.png').convert('RGBA')
    top = max(header_bottom, 161) + 30
    # A: full width between header and tags (centred on the card)
    boxA = (M, top, S - M, tags_top - 30 if not count else min(tags_top, BOTTOM - TAG_H) - 30)
    # B: centred column that keeps clear of tags on both sides, down to the bottom
    half = max(tag_right - S / 2, (S - count_left) - S / 2 if count else 0, 0)
    side = S / 2 - (tag_right if tag_right > S / 2 else 0)
    colw = 2 * min(S / 2 - tag_right - 30, (count_left - 30) - S / 2) if tag_right < S / 2 else 0
    boxB = (S / 2 - colw / 2, top, S / 2 + colw / 2, BOTTOM) if colw > 200 else None
    best = boxA
    if boxB and fit(prod, boxB) > fit(prod, boxA):
        best = boxB
    sc = fit(prod, best)
    pw, ph = round(prod.width * sc), round(prod.height * sc)
    pr = prod.resize((pw, ph), Image.LANCZOS)
    x = (S - pw) // 2
    yb = best[1] + ((best[3] - best[1]) - ph) // 2
    img.paste(pr, (x, yb), pr)
    os.makedirs(out_dir, exist_ok=True)
    img.save(f'{out_dir}/p{pid}.jpg', quality=92)
    return img


CARDS = [
    ('3238301182', 'militex', ['CORDURA ORIGINAL USA', 'ПЛИТИ SAPI / ESAPI M'], None, 'Плитоноска Militex Pro Series S-M'),
    ('3238301227', 'kiborg', ['ПЛИТИ 25х30 СМ', 'CORDURA 1000D'], None, 'Плитоноска Kiborg GU Gen.1'),
    ('3238301109', 'militex', ['ЗБІЛЬШЕНА ПЛОЩА ЗАХИСТУ', 'CORDURA ORIGINAL USA'], None, 'Плитоноска Militex Modular X-1'),
    ('3238301581', 'militex', ['ЗБІЛЬШЕНА ПЛОЩА ЗАХИСТУ', 'CORDURA ORIGINAL USA'], None, 'Militex Modular X-1 без підсумків'),
    ('3238300136', 'kiborg', ['КИШЕНІ ПІД БАЛІСТИЧНІ ПАКЕТИ', 'ШВИДКИЙ СКИД'], '2 ШТ', 'Камербанди Kiborg Gen.2'),
    ('3238295956', 'kiborg', ['ЖОРСТКІ СТІНКИ', 'CORDURA 1000D'], None, 'Підсумок Kiborg GU Single Mag'),
    ('3238300056', 'kiborg', ['КРІПЛЕННЯ ДЛЯ НОЖИЦЬ І МАРКЕРА', 'ВІДКРИВАЄТЬСЯ ОДНІЄЮ РУКОЮ'], None, 'Підсумок для турнікету Kiborg'),
    ('3238300062', 'kiborg', ['ЖОРСТКІ СТІНКИ', 'ПІД 1 МАГАЗИН'], None, 'Підсумок для магазину Kiborg M-1'),
    ('3238301114', 'militex', ['ДО 8 МАГАЗИНІВ', 'СКЛАДАЄТЬСЯ ДО 25х7 СМ'], None, 'Підсумок для скидання Militex'),
    ('3238301119', 'militex', ['КРІПЛЕННЯ ДЛЯ НОЖИЦЬ І МАРКЕРА', 'СТРОПА MURDOCK USA'], None, 'Підсумок для турнікету Militex'),
    ('3238300077', 'kiborg', ['ПЛИТИ 25х30 СМ', 'ЗНІМНА MOLLE-ПАНЕЛЬ'], None, 'Плитоноска Kiborg GU Gen.2'),
]

if __name__ == '__main__':
    for pid, brand, pts, cnt, _ in CARDS:
        make(pid, brand, pts, cnt)
        print('ok', pid)
