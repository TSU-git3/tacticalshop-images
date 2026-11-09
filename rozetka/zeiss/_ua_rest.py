"""Ukrainian versions of the remaining 12 Zeiss infographics.
Each spec: clear English text regions (solid fill or inpaint), redraw badge text, render Ukrainian text.
Coordinates are fractions of the source image (x0, y0, x1, y1)."""
import sys, json
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy import ndimage
sys.path.insert(0, '/tmp/claude-0/-home-claude/bffc3b6a-1a0c-569d-a9cf-e38ebb023b76/scratchpad/zr')
from ua_infographics import font, to_square

SRC = '/tmp/claude-0/-home-claude/bffc3b6a-1a0c-569d-a9cf-e38ebb023b76/scratchpad/zr/prom/'
OUT = '/tmp/claude-0/-home-claude/bffc3b6a-1a0c-569d-a9cf-e38ebb023b76/scratchpad/zr/site/img/'


class Canvas:
    def __init__(self, name):
        self.im = Image.open(SRC + name).convert('RGB')
        self.W, self.H = self.im.size
        self.orig = np.asarray(self.im).copy()

    def px(self, b):
        x0, y0, x1, y1 = b
        return int(x0 * self.W), int(y0 * self.H), int(x1 * self.W), int(y1 * self.H)

    def sample(self, fx, fy):
        return tuple(int(v) for v in self.orig[int(fy * self.H), int(fx * self.W)])

    def ink(self, b, bg):
        """median colour of pixels in box far from bg (the original text colour)."""
        x0, y0, x1, y1 = self.px(b)
        a = self.orig[y0:y1, x0:x1].reshape(-1, 3).astype(int)
        d = np.abs(a - np.array(bg)).sum(1)
        sel = a[d > d.max() * 0.7]
        return tuple(int(v) for v in np.median(sel, 0)) if len(sel) else (0, 0, 0)

    def fill(self, b, color):
        ImageDraw.Draw(self.im).rectangle(self.px(b), fill=color)

    def inpaint(self, b, bg_thresh=60):
        """remove text that differs from local background, keep the photo underneath."""
        x0, y0, x1, y1 = self.px(b)
        a = np.asarray(self.im).copy()
        reg = a[y0:y1, x0:x1].astype(int)
        med = cv2.medianBlur(a, 31)[y0:y1, x0:x1].astype(int)
        m = (np.abs(reg - med).sum(2) > bg_thresh).astype(np.uint8)
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        mask = np.zeros(a.shape[:2], np.uint8)
        mask[y0:y1, x0:x1] = m * 255
        res = cv2.inpaint(a, mask, 7, cv2.INPAINT_TELEA)
        self.im = Image.fromarray(res)

    def fade(self, b, top, right):
        """white overlay with soft top and right edges (fractions of image size)."""
        x0, y0, x1, y1 = self.px(b)
        a = np.asarray(self.im).astype(float)
        ys = np.arange(y0, y1)[:, None]; xs = np.arange(x0, x1)[None, :]
        al = np.clip((ys - y0) / (top * self.H), 0, 1) * np.clip((x1 - xs) / (right * self.W), 0, 1)
        al = al ** 0.8
        reg = a[y0:y1, x0:x1]
        a[y0:y1, x0:x1] = reg * (1 - al[..., None]) + 255 * al[..., None]
        self.im = Image.fromarray(a.astype(np.uint8))

    # ---- text ----
    def para(self, b, runs, size, color, lh=1.3, minsize=14, align='left', valign='top', maxlines=None):
        """runs: list of (text, weight) or a str. Wraps word by word, shrinks until it fits the box."""
        if isinstance(runs, str):
            runs = [(runs, '400')]
        x0, y0, x1, y1 = self.px(b)
        d = ImageDraw.Draw(self.im)
        words = []
        for t, w in runs:
            if t == '\n':
                words.append(('\n', w)); continue
            for wd in t.split(' '):
                if wd:
                    words.append((wd, w))
        s = size
        while True:
            lines, cur, curw = [], [], 0
            sp = d.textlength(' ', font=font('400', s))
            for wd, w in words:
                if wd == '\n':
                    lines.append(cur); cur, curw = [], 0; continue
                ww = d.textlength(wd, font=font(w, s))
                add = ww + (sp if cur else 0)
                if cur and curw + add > x1 - x0:
                    lines.append(cur); cur, curw = [], 0; add = ww
                cur.append((wd, w, ww)); curw += add
            if cur:
                lines.append(cur)
            hgt = len(lines) * s * lh
            ok = hgt <= (y1 - y0) and (maxlines is None or len(lines) <= maxlines)
            if ok or s <= minsize:
                break
            s -= 1
        y = y0 if valign == 'top' else y0 + ((y1 - y0) - hgt) / 2
        for ln in lines:
            lw = sum(t[2] for t in ln) + sp * (len(ln) - 1)
            x = x0 if align == 'left' else x0 + ((x1 - x0) - lw) / 2
            for wd, w, ww in ln:
                d.text((x, y + s * lh / 2), wd, font=font(w, s), fill=color, anchor='lm')
                x += ww + sp
            y += s * lh
        return s

    # ---- badge ----
    def badge(self, b, lines, ty, angle, size, color, weight='700', icon_keep=None):
        """b: box around the circle. Remove ink components whose centroid is below ty (fraction of the
        circle height from its top), then write `lines` rotated by `angle` at their centre."""
        x0, y0, x1, y1 = self.px(b)
        a = np.asarray(self.im).copy()
        reg = a[y0:y1, x0:x1].astype(int)
        # dominant colour = circle colour
        flat = reg.reshape(-1, 3)
        sat = (flat.max(1) - flat.min(1)) > 70
        q = (flat[sat] // 16)
        vals, cnt = np.unique(q, axis=0, return_counts=True)
        ccol_q = vals[np.argmax(cnt)]
        near = (np.abs(reg // 16 - ccol_q).max(2) <= 1)
        ccol = tuple(int(v) for v in np.median(reg[near], 0))
        lab, n = ndimage.label(near)
        big = np.argmax(ndimage.sum(near, lab, range(1, n + 1))) + 1
        disk = ndimage.binary_fill_holes(lab == big)
        ys, xs = np.where(disk)
        cy0, cy1 = ys.min(), ys.max()
        cx = (xs.min() + xs.max()) / 2
        r = (xs.max() - xs.min()) / 2
        cyc = (cy0 + cy1) / 2
        inner = ndimage.binary_erosion(disk, iterations=3)
        ink = inner & ~near
        ink = ndimage.binary_opening(ink, iterations=0) if False else ink
        lab2, n2 = ndimage.label(ink, structure=np.ones((3, 3)))
        thr = cy0 + ty * (cy1 - cy0)
        rem = np.zeros_like(ink)
        for i in range(1, n2 + 1):
            yy, xx = np.where(lab2 == i)
            if DEBUG and len(yy) > 150:
                print('  comp', i, 'yfrac %.2f' % ((yy.mean() - cy0) / (cy1 - cy0)), 'n', len(yy))
            if yy.mean() > thr:
                rem |= lab2 == i
        rem = ndimage.binary_dilation(rem, iterations=3) & inner
        ys2, xs2 = np.where(rem)
        tcx, tcy = xs2.mean(), ys2.mean()
        reg2 = a[y0:y1, x0:x1]
        reg2[rem] = ccol
        a[y0:y1, x0:x1] = reg2
        self.im = Image.fromarray(a)
        # text, rotated
        S = int(2.2 * r)
        tag = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        td = ImageDraw.Draw(tag)
        f = font(weight, size)
        lh = size * 1.05
        for k, ln in enumerate(lines):
            td.text((S / 2, S / 2 + (k - (len(lines) - 1) / 2) * lh), ln, font=f, fill=color, anchor='mm')
        tag = tag.rotate(angle, resample=Image.BICUBIC)
        self.im.paste(tag, (int(x0 + tcx - S / 2), int(y0 + tcy - S / 2)), tag)
        return dict(c=(x0 + cx, y0 + cyc), r=r, ccol=ccol)

    def save(self, out):
        to_square(self.im).save(out, quality=90)


DEBUG = True
WHITE, BLACK, DARK = (255, 255, 255), (20, 20, 20), (45, 45, 45)


def A():  # 5083195552 wipes: Safe to use / COLTS / x100
    c = Canvas('5083195552.jpeg')
    blue = c.ink((0, 0, 0.3, 0.04), WHITE)
    c.fill((0, 0, 0.645, 0.455), WHITE)
    c.para((0.01, 0.0, 0.64, 0.06), [('Безпечні для лінз', '700')], 54, blue)
    c.para((0.01, 0.075, 0.63, 0.44), [('Протирати окуляри одягом зручно, але на тканині часто є абразивний бруд, '
                                       'який дряпає лінзи.', '400'), ('\n', '400'), ('\n', '400'),
                                      ('Серветки ZEISS Lens Wipes', '600'),
                                      ('пройшли незалежні суворі тести COLTS Laboratories і отримали знак '
                                       'якості COLTS Seal of Performance.', '400')], 30, DARK)
    blue2 = c.ink((0.25, 0.52, 0.74, 0.59), WHITE)
    c.fill((0.2, 0.51, 0.8, 0.6), WHITE)
    c.para((0.2, 0.515, 0.8, 0.595), [('Збільшення ×100', '700')], 50, blue2, align='center', valign='mid')
    c.fill((0, 0.862, 0.335, 0.93), WHITE)
    c.para((0.01, 0.866, 0.33, 0.93), 'Лінза після протирання звичайним одягом', 19, DARK)
    c.fill((0.655, 0.932, 1, 1), WHITE)
    c.para((0.67, 0.936, 0.995, 1), 'Лінза після серветок ZEISS Lens Wipes', 19, DARK)
    c.badge((0.84, 0.59, 1.0, 0.76), ['Без', 'подряпин'], 0.5, 18, 22, WHITE)
    c.save(OUT + 'ua_5083195552.jpg')


def B():  # 5083195554 wipes: Easy to use, blue panel
    c = Canvas('5083195554.jpeg')
    blue = c.sample(0.02, 0.48)
    c.fill((0.0, 0.0, 0.41, 0.495), blue)
    c.para((0.035, 0.025, 0.40, 0.085), [('Зручно використовувати', '700')], 44, WHITE)
    c.para((0.035, 0.105, 0.39, 0.48), [('Кожна серветка в окремій упаковці — зручно брати з собою або тримати вдома.', '400'),
                                        ('\n', '400'), ('Серветки ZEISS Lens Wipes', '700'),
                                        ("з м'якої мікрофібри, безпечні для лінз з якісним антиблисковим покриттям.", '400')],
           29, WHITE)
    c.badge((0.78, 0.70, 0.97, 0.87), ["М'яка", 'мікрофібра'], 0.5, 15, 21, BLACK)
    c.save(OUT + 'ua_5083195554.jpg')


def C():  # 5083195555 wipes: Safely and quickly clean lenses
    c = Canvas('5083195555.jpeg')
    blue = c.ink((0.48, 0.64, 1, 0.75), WHITE)
    c.fill((0.47, 0.635, 1, 0.97), WHITE)
    c.para((0.49, 0.645, 0.99, 0.765), [('Швидке і безпечне очищення лінз', '700')], 50, blue)
    c.para((0.49, 0.785, 0.985, 0.97), [('Серветки ZEISS Lens Wipes', '600'),
                                        ('делікатно й ретельно очищують лінзи: видаляють відбитки пальців, пил і плями '
                                         'без подряпин і розводів.', '400')], 27, DARK)
    c.badge((0.81, 0.19, 0.99, 0.38), ['Без', 'розводів'], 0.55, 18, 21, WHITE)
    c.save(OUT + 'ua_5083195555.jpg')


def D():  # 6450947455 spray x2: Gentle and effective
    c = Canvas('6450947455.jpg')
    c.fill((0, 0, 0.555, 0.43), WHITE)
    c.fill((0.03, 0.89, 0.555, 0.94), WHITE)
    c.para((0.01, 0.02, 0.55, 0.24), [('Делікатне та ефективне очищення лінз', '700')], 62, BLACK)
    c.para((0.01, 0.255, 0.55, 0.36), 'Безпечна формула без розводів, яка не пошкоджує лінзи.', 30, DARK)
    blue = c.sample(0.99, 0.5)
    c.fill((0.725, 0.2, 0.995, 0.79), blue)
    labels = [(0.255, 'Видаляє бруд, пил і жир'), (0.38, 'Видаляє відбитки пальців'), (0.485, 'Без розводів'),
              (0.60, 'Без подряпин'), (0.72, 'Без аміаку, нетоксичний')]
    for y, t in labels:
        c.para((0.735, y - 0.05, 0.99, y + 0.05), t, 25, WHITE, valign='mid', maxlines=2)
    c.save(OUT + 'ua_6450947455.jpg')


def E():  # 6451411720 spray: Safe and effective cleaning (blue band)
    c = Canvas('6451411720.jpg')
    blue = c.sample(0.02, 0.98)
    c.fill((0.04, 0.585, 0.64, 0.94), blue)
    c.fill((0.765, 0.6, 0.99, 0.9), blue)
    c.para((0.085, 0.6, 0.63, 0.72), [('Безпечне та ефективне очищення', '700')], 50, WHITE)
    c.para((0.085, 0.75, 0.62, 0.93), [('Спрей ZEISS Lens Spray', '600'),
                                       ('створений для максимально ефективного очищення: без аміаку, з низьким '
                                        'вмістом летких речовин, нетоксичний.', '400')], 27, WHITE)
    for y, t in ((0.657, 'Без аміаку'), (0.757, 'Мало летких речовин'), (0.86, 'Нетоксичний')):
        c.para((0.775, y - 0.04, 0.99, y + 0.04), t, 22, WHITE, valign='mid', maxlines=2)
    c.save(OUT + 'ua_6451411720.jpg')


def F():  # 6623925624 antifog wipes: Fog-free vision / 24 hours
    c = Canvas('6623925624.png')
    blue = c.ink((0.04, 0.69, 0.55, 0.77), WHITE)
    c.fill((0.02, 0.68, 0.565, 0.92), WHITE)
    c.para((0.045, 0.69, 0.56, 0.77), [('Без запотівання', '700')], 56, blue)
    c.para((0.045, 0.785, 0.555, 0.92), [('Серветки ZEISS AntiFOG Wipes', '600'),
                                         ('швидко й ефективно очищують лінзи та захищають їх від запотівання.', '400')],
           26, DARK)
    c.badge((0.46, 0.07, 0.72, 0.33), ['24 години'], 0.55, -20, 27, BLACK)
    c.save(OUT + 'ua_6623925624.jpg')


def G():  # 6623925733 antifog wipes: Safe to use, grey panel
    c = Canvas('6623925733.png')
    grey = c.sample(0.9, 0.85)
    blue = c.ink((0.5, 0.3, 0.97, 0.37), grey)
    c.fill((0.49, 0.28, 0.965, 0.76), grey)
    c.para((0.52, 0.30, 0.96, 0.38), [('Безпечні для лінз', '700')], 54, blue)
    c.para((0.52, 0.405, 0.95, 0.75), [('Серветки ZEISS AntiFOG Wipes', '600'),
                                       ("з м'якої мікрофібри залишають на лінзах тонку плівку, що запобігає "
                                        'запотіванню. Безпечні для лінз з антиблисковим покриттям.', '400')],
           27, DARK, lh=1.55)
    c.badge((0.11, 0.06, 0.36, 0.30), ["М'яка", 'мікрофібра'], 0.5, 15, 28, BLACK)
    c.save(OUT + 'ua_6623925733.jpg')


def H():  # 6623925779 antifog wipes: Easy to use, Streak-free
    c = Canvas('6623925779.png')
    blue = c.ink((0.04, 0.66, 0.5, 0.73), WHITE)
    c.fill((0.02, 0.65, 1, 0.97), WHITE)
    c.para((0.045, 0.665, 0.9, 0.745), [('Зручно використовувати', '700')], 52, blue)
    c.para((0.045, 0.77, 0.98, 0.97), [('Кожна серветка в окремій упаковці — зручно брати з собою або тримати вдома.', '400'),
                                       ('\n', '400'),
                                       ('Протирайте лінзи щодня для чистого й чіткого огляду. Лінзи залишаються без '
                                        'розводів і запотівання до 24 годин.', '400')], 26, DARK, lh=1.45)
    c.badge((0.04, 0.03, 0.33, 0.35), ['Без', 'розводів'], 0.6, 15, 27, BLACK)
    c.save(OUT + 'ua_6623925779.jpg')


def I():  # 6623806088 fog defender: works on all lens surfaces
    c = Canvas('6623806088.png')
    a = c.orig.astype(int)
    H, W = c.H, c.W
    blue = c.ink((0.05, 0.66, 0.95, 0.73), WHITE)
    # icon centres from the icon row
    y0, y1 = int(0.846 * H), int(0.919 * H)
    row = (a[y0:y1].min(axis=2) < 150).any(axis=0)
    lab, n = ndimage.label(ndimage.binary_dilation(row, iterations=12))
    centres = [int(np.mean(np.where(lab == i)[0])) for i in range(1, n + 1)]
    c.fill((0.02, 0.70, 0.98, 0.835), WHITE)
    c.fill((0.02, 0.925, 0.98, 0.975), WHITE)
    c.para((0.04, 0.70, 0.96, 0.775), [('Для всіх оптичних поверхонь', '700')], 52, blue, align='center')
    c.para((0.04, 0.785, 0.96, 0.83), [('ZEISS Fog Defender System', '600'), ('підходить для всіх оптичних лінз:', '400')],
           26, DARK, align='center', maxlines=1)
    labels = ['Окуляри', 'Сонцезахисні окуляри', 'Біноклі', "Об'єктиви", 'Окуляри для плавання', 'Гірськолижні маски']
    d = ImageDraw.Draw(c.im)
    f = font('400', 18)
    for cx, t in zip(centres, labels):
        words = t.split(' ', 1) if d.textlength(t, font=f) > 150 else [t]
        for k, line in enumerate(words):
            d.text((cx, 0.950 * H + k * 20 - (10 if len(words) == 2 else 0)), line, font=f, fill=DARK, anchor='mm')
    print('I centres', len(centres))
    c.save(OUT + 'ua_6623806088.jpg')


def J():  # 6623806109 fog defender: Lift the fog / 72 hours
    c = Canvas('6623806109.png')
    blue = c.ink((0.05, 0.56, 0.5, 0.63), WHITE)
    c.fill((0.03, 0.55, 0.535, 0.93), WHITE)
    c.para((0.05, 0.565, 0.53, 0.645), [('Без запотівання', '700')], 54, blue)
    c.para((0.05, 0.67, 0.525, 0.92), [('ZEISS Fog Defender System', '700'),
                                       ('— простий у використанні спрей-антифог, що захищає лінзи від запотівання '
                                        'до 72 годин.', '400')], 27, DARK, lh=1.55)
    c.badge((0.34, 0.06, 0.59, 0.31), ['72 години'], 0.6, 0, 27, BLACK)
    c.save(OUT + 'ua_6623806109.jpg')


def K():  # 6623806387 fog defender: Safe to use (title over photo)
    c = Canvas('6623806387.png')
    blue = c.ink((0.05, 0.72, 0.4, 0.79), (240, 240, 240))
    c.fade((0.0, 0.66, 0.66, 0.805), top=0.045, right=0.06)
    c.fill((0.02, 0.805, 0.98, 0.98), WHITE)
    c.para((0.05, 0.722, 0.6, 0.795), [('Безпечний для лінз', '700')], 52, blue)
    c.para((0.05, 0.81, 0.93, 0.975), [('Розчин ZEISS Fog Defender System', '600'),
                                       ('залишає на лінзах тонку плівку, що запобігає запотіванню. Безпечний для лінз '
                                        'з антиблисковим покриттям.', '400')], 26, DARK, lh=1.55)
    c.badge((0.66, 0.05, 0.92, 0.33), ['Безпечно'], 0.6, 0, 27, BLACK)
    c.save(OUT + 'ua_6623806387.jpg')


def L():  # 6300027186 70% wipes: contains 70% IPA
    c = Canvas('6300027186.jpg')
    blue = c.sample(0.97, 0.45)
    c.fill((0.5, 0.03, 0.995, 0.4), blue)
    c.para((0.535, 0.06, 0.99, 0.27), [('Містять 70% ізопропілового спирту', '700')], 56, WHITE)
    c.para((0.535, 0.285, 0.97, 0.39), 'Безпечна формула без розводів, яка не пошкоджує лінзи.', 28, WHITE)
    c.save(OUT + 'ua_6300027186.jpg')


if __name__ == '__main__':
    todo = sys.argv[1:] or list('ABCDEFGHIJKL')
    for k in todo:
        try:
            globals()[k]()
            print('ok', k)
        except Exception as e:
            import traceback; traceback.print_exc(); print('FAIL', k)
