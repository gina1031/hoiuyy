import math, sys, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from multiprocessing import Pool

W, H, FPS, DUR = 1920, 1080, 30, 60.0
BASE = os.path.dirname(os.path.abspath(__file__))
FD = '/usr/share/fonts/opentype/inter/'
NAVY = (13, 27, 46); GOLD = (234, 186, 76); GOLD2 = (255, 214, 120); WHITE = (255, 255, 255)

def F(name, size): return ImageFont.truetype(FD + name, size)

# ---------------- scenes ----------------
# rects are in storyboard panel-local px (x, y, w); h derived as w*9/16
SCENES = [  # (start, end)
    (0.0, 5.0), (5.0, 9.5), (9.5, 16.3), (16.3, 24.3), (24.3, 30.1),
    (30.1, 37.1), (37.1, 46.5), (46.5, 53.9), (53.9, 60.0)]
# shots: (scene, t0, t1, panel, rect_start, rect_end)
SHOTS = [
    (1, 0.0, 5.0, 1, (0, 4, 318), (40, 22, 250)),
    (2, 5.0, 9.5, 2, (0, 2, 345), (172, 2, 345)),
    (3, 9.5, 16.3, 3, (0, 14, 300), (48, 4, 262)),
    (4, 16.3, 24.3, 4, (150, 0, 334), (140, 10, 290)),
    (5, 24.3, 30.1, 5, (0, 0, 334), (24, 22, 290)),
    (6, 30.1, 34.9, 6, (2, 0, 255), (40, 10, 215)),
    (6, 34.9, 37.1, 6, (340, 0, 179), (362, 10, 150)),
    (7, 37.1, 46.5, 7, (0, 10, 285), (10, 22, 250)),
    (8, 46.5, 53.9, 'blur', None, None),
    (9, 53.9, 60.0, 9, (0, 0, 320), (26, 16, 276)),
]
XF = 0.32  # crossfade length

def ease_io(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

SRC = {}
def load_sources():
    for i in [1, 2, 3, 4, 5, 6, 7, 9]:
        im = Image.open(f'{BASE}/crops/up{i}.png').convert('RGB')
        im = ImageEnhance.Contrast(im).enhance(1.06)
        im = ImageEnhance.Color(im).enhance(1.08)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        SRC[i] = im
    b = Image.open(f'{BASE}/crops/up2.png').convert('RGB').resize((W, H), Image.BICUBIC)
    b = b.filter(ImageFilter.GaussianBlur(28))
    b = ImageEnhance.Brightness(b).enhance(0.55)
    SRC['blur'] = b

def shot_frame(sh, t):
    sc, t0, t1, p, r0, r1 = sh
    if p == 'blur':
        z = 1.0 + 0.05 * (t - t0) / (t1 - t0)
        im = SRC['blur']
        cw, ch = W / z, H / z
        return im.transform((W, H), Image.AFFINE, (cw / W, 0, (W - cw) / 2, 0, ch / H, (H - ch) / 2), Image.BICUBIC)
    k = ease_io((t - t0) / (t1 - t0))
    x = r0[0] + (r1[0] - r0[0]) * k; y = r0[1] + (r1[1] - r0[1]) * k; w = r0[2] + (r1[2] - r0[2]) * k
    # punch-in on entry
    punch = 1 + 0.07 * (1 - ease_out((t - t0) / 0.45))
    cx, cy = x + w / 2, y + w * 9 / 32
    w = w / punch
    x, y = cx - w / 2, cy - w * 9 / 32
    s = 4 * w / W
    return SRC[p].transform((W, H), Image.AFFINE, (s, 0, x * 4, 0, s, y * 4), Image.BICUBIC)

def background(t):
    cur = [s for s in SHOTS if s[1] - XF / 2 <= t < s[2] + XF / 2]
    if len(cur) == 1:
        return shot_frame(cur[0], t)
    a, b = cur[0], cur[1]
    m = ease_io((t - (b[1] - XF / 2)) / XF)
    return Image.blend(shot_frame(a, t), shot_frame(b, t), m)

# ---------------- drawing helpers (supersampled) ----------------
SS = 3
def canvas(w, h): return Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
def down(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)

def icon(name, size, color=GOLD, lw=None):
    S = size * SS; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    u = S / 100; lw = int((lw or 7) * u)
    if name == 'pin':
        d.ellipse((22 * u, 6 * u, 78 * u, 62 * u), fill=color)
        d.polygon([(26 * u, 46 * u), (74 * u, 46 * u), (50 * u, 94 * u)], fill=color)
        d.ellipse((38 * u, 22 * u, 62 * u, 46 * u), fill=(0, 0, 0, 0))
    elif name == 'check':
        d.line([(20 * u, 52 * u), (42 * u, 74 * u), (82 * u, 28 * u)], fill=color, width=int(13 * u), joint='curve')
    elif name == 'house':
        d.line([(12 * u, 50 * u), (50 * u, 16 * u), (88 * u, 50 * u)], fill=color, width=lw, joint='curve')
        d.line([(24 * u, 42 * u), (24 * u, 86 * u), (76 * u, 86 * u), (76 * u, 42 * u)], fill=color, width=lw, joint='curve')
        d.rectangle((42 * u, 60 * u, 58 * u, 86 * u), outline=color, width=lw)
    elif name == 'm2':
        d.rounded_rectangle((14 * u, 14 * u, 86 * u, 86 * u), radius=8 * u, outline=color, width=lw)
        f = F('Inter-Bold.otf', int(34 * u)); d.text((50 * u, 54 * u), 'm²', font=f, fill=color, anchor='mm')
    elif name == 'family':
        for cx, r, top in [(28, 9, 26), (72, 9, 26), (50, 8, 38)]:
            d.ellipse(((cx - r) * u, (top - r) * u, (cx + r) * u, (top + r) * u), fill=color)
        d.rounded_rectangle((15 * u, 40 * u, 41 * u, 84 * u), radius=10 * u, fill=color)
        d.rounded_rectangle((59 * u, 40 * u, 85 * u, 84 * u), radius=10 * u, fill=color)
        d.rounded_rectangle((39 * u, 50 * u, 61 * u, 84 * u), radius=9 * u, fill=color, outline=(0, 0, 0, 0))
    elif name == 'school':
        d.polygon([(50 * u, 18 * u), (94 * u, 38 * u), (50 * u, 58 * u), (6 * u, 38 * u)], fill=color)
        d.chord((26 * u, 30 * u, 74 * u, 82 * u), 0, 180, fill=color)
        d.line([(86 * u, 40 * u), (86 * u, 70 * u)], fill=color, width=lw)
    elif name == 'cart':
        d.line([(6 * u, 20 * u), (20 * u, 20 * u), (30 * u, 66 * u), (80 * u, 66 * u), (90 * u, 32 * u), (24 * u, 32 * u)], fill=color, width=lw, joint='curve')
        for cx in (36, 74): d.ellipse(((cx - 7) * u, 74 * u, (cx + 7) * u, 88 * u), fill=color)
    elif name == 'road':
        d.polygon([(34 * u, 10 * u), (66 * u, 10 * u), (92 * u, 90 * u), (8 * u, 90 * u)], fill=color)
        for y0 in (16, 42, 68): d.rectangle((47 * u, y0 * u, 53 * u, (y0 + 16) * u), fill=(0, 0, 0, 0))
    elif name == 'tree':
        d.ellipse((20 * u, 6 * u, 80 * u, 66 * u), fill=color)
        d.rectangle((44 * u, 56 * u, 56 * u, 94 * u), fill=color)
    elif name == 'bed':
        d.rectangle((8 * u, 22 * u, 18 * u, 84 * u), fill=color)
        d.rounded_rectangle((18 * u, 48 * u, 92 * u, 70 * u), radius=4 * u, fill=color)
        d.rounded_rectangle((24 * u, 34 * u, 46 * u, 48 * u), radius=5 * u, fill=color)
        d.rectangle((84 * u, 60 * u, 92 * u, 84 * u), fill=color)
    elif name == 'phone':
        d.rounded_rectangle((28 * u, 6 * u, 72 * u, 94 * u), radius=10 * u, fill=color)
        d.rounded_rectangle((34 * u, 16 * u, 66 * u, 78 * u), radius=3 * u, fill=(0, 0, 0, 0))
        d.ellipse((45 * u, 82 * u, 55 * u, 90 * u), fill=(0, 0, 0, 0))
    elif name == 'window':
        d.rounded_rectangle((14 * u, 14 * u, 86 * u, 86 * u), radius=6 * u, outline=color, width=lw)
        d.line([(50 * u, 14 * u), (50 * u, 86 * u)], fill=color, width=lw)
        d.line([(14 * u, 50 * u), (86 * u, 50 * u)], fill=color, width=lw)
    elif name == 'layers':
        for i, y in enumerate((22, 40, 58)):
            d.polygon([(50 * u, y * u), (88 * u, (y + 14) * u), (50 * u, (y + 28) * u), (12 * u, (y + 14) * u)],
                      outline=color, width=lw, fill=None)
    return im.resize((size, size), Image.LANCZOS)

def shadowed(im, blur=18, off=(0, 8), alpha=150):
    pad = blur * 3
    out = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].point(lambda a: a * alpha // 255))
    out.paste(sh, (pad + off[0], pad + off[1]), sh)
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    out.info['pad'] = pad
    return out

def pill(text, font, fg, bg, padx=34, pady=18, ico=None, ico_color=None, radius=None, outline=None):
    tw = font.getbbox(text)[2]; asc, desc = font.getmetrics(); th = asc
    isz = int(th * 1.15) if ico else 0
    gap = int(isz * 0.45) if ico else 0
    w = tw + padx * 2 + isz + gap; h = th + pady * 2
    c = canvas(w, h); d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=(radius if radius is not None else h // 2) * SS, fill=bg,
                        outline=outline, width=3 * SS if outline else 0)
    fs = ImageFont.truetype(font.path, font.size * SS)
    d.text(((padx + isz + gap) * SS, h * SS / 2), text, font=fs, fill=fg, anchor='lm')
    im = down(c)
    if ico:
        ic = icon(ico, isz, ico_color or fg); im.alpha_composite(ic, (padx, (h - isz) // 2))
    return shadowed(im)

def text_sprite(lines, stroke=0, shadow=True, align='left', spacing=6):
    # lines: [(text, font, color)]
    hs = [f.getmetrics()[0] + f.getmetrics()[1] // 2 for _, f, _ in lines]
    ws = [f.getbbox(t)[2] + stroke * 2 for t, f, _ in lines]
    w = max(ws) + 10; h = sum(hs) + spacing * (len(lines) - 1) + stroke * 2 + 10
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = stroke + 4
    for (t, f, col), lh, lw_ in zip(lines, hs, ws):
        x = {'left': stroke + 4, 'right': w - lw_ + stroke - 6, 'center': (w - lw_) // 2 + stroke}[align]
        d.text((x, y), t, font=f, fill=col, stroke_width=stroke, stroke_fill=(10, 14, 22))
        y += lh + spacing
    return shadowed(im, blur=14, off=(0, 6), alpha=170) if shadow else im

def card(title_lines, ico, w=560, fsize=40):
    f = F('Inter-Bold.otf', fsize)
    lh = f.getmetrics()[0] + 10; h = max(lh * len(title_lines) + 46, 116)
    c = canvas(w, h); d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=22 * SS, fill=(13, 27, 46, 215), outline=(234, 186, 76, 150), width=2 * SS)
    cs = 80; cx0 = 22; cy0 = (h - cs) // 2
    d.ellipse((cx0 * SS, cy0 * SS, (cx0 + cs) * SS, (cy0 + cs) * SS), fill=(234, 186, 76, 40), outline=GOLD, width=3 * SS)
    fs = ImageFont.truetype(f.path, fsize * SS)
    ty = h / 2 - lh * len(title_lines) / 2 + lh / 2
    for i, tl in enumerate(title_lines):
        d.text(((cx0 + cs + 26) * SS, (ty + i * lh) * SS), tl, font=fs, fill=WHITE, anchor='lm')
    im = down(c); ic = icon(ico, 46); im.alpha_composite(ic, (cx0 + 17, cy0 + 17))
    return shadowed(im)

def check_card(text, w=560):
    f = F('Inter-Bold.otf', 42); h = 104
    c = canvas(w, h); d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=20 * SS, fill=(13, 27, 46, 215), outline=(234, 186, 76, 150), width=2 * SS)
    d.rounded_rectangle((26 * SS, 24 * SS, 82 * SS, 80 * SS), radius=10 * SS, fill=None, outline=GOLD, width=4 * SS)
    d.text((108 * SS, h * SS / 2), text, font=ImageFont.truetype(f.path, 42 * SS), fill=WHITE, anchor='lm')
    return shadowed(down(c))

def paste(frame, spr, x, y, alpha=1.0, scale=1.0, anchor='lt'):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.005:
        nw, nh = max(1, int(spr.width * scale)), max(1, int(spr.height * scale))
        spr2 = spr.resize((nw, nh), Image.BILINEAR)
    else:
        spr2 = spr
    pad = spr.info.get('pad', 0) * scale
    if anchor == 'c':
        px, py = x - spr2.width / 2, y - spr2.height / 2
    elif anchor == 'rt':
        px, py = x - spr2.width + pad, y - pad
    else:
        px, py = x - pad, y - pad
    if alpha < 0.999:
        a = spr2.split()[3].point(lambda v: int(v * alpha)); spr2 = spr2.copy(); spr2.putalpha(a)
    frame.alpha_composite(spr2, (int(round(px)), int(round(py))))

def anim(t, t_in, dur=0.45):
    return ease_out((t - t_in) / dur)

# ---------------- captions ----------------
VO = [
    (0.4, "Introducing a double storey terrace house, located at Shah Alam Sek 30."),
    (5.35, "A modern and practical home, designed for comfortable family living."),
    (9.85, "Featuring a modern facade, contemporary design, and large windows that bring in natural light."),
    (16.65, "A spacious ground floor with a welcoming living area, and a well-planned dining space. Perfect for family time and entertaining."),
    (24.65, "A practical kitchen with ample storage, and good ventilation, for everyday convenience."),
    (30.45, "Upstairs, find comfortable bedrooms that offer privacy, and a relaxing space for the whole family."),
    (37.45, "Enjoy a strategic location in Shah Alam Sek 30, with easy access to schools, shopping and dining, major highways, and recreational areas."),
    (46.85, "A double storey terrace house in Shah Alam Sek 30. A practical, family-friendly home, in a great location."),
    (54.25, "Interested in this home? Contact us today to find out more, or arrange a viewing."),
]
GOLDWORDS = {'double', 'storey', 'terrace', 'house', 'shah', 'alam', 'sek', '30', 'modern', 'practical', 'natural', 'light',
             'spacious', 'ground', 'floor', 'kitchen', 'storage', 'ventilation', 'bedrooms', 'privacy', 'location',
             'schools', 'highways', 'family-friendly', 'contact', 'today', 'viewing', 'whole', 'family', 'facade', 'windows',
             'dining', 'living', 'shopping'}

import json as _json
def words_of(i):
    a = _json.load(open(f'{BASE}/el/{i}.json'))
    ch, st, en = a['characters'], a['character_start_times_seconds'], a['character_end_times_seconds']
    out, cur, cs = [], '', None
    for c, a0, a1 in zip(ch, st, en):
        if c.isspace():
            if cur: out.append((cur, cs, pe)); cur = ''
            continue
        if not cur: cs = a0
        cur += c; pe = a1
    if cur: out.append((cur, cs, pe))
    return out

WORDS = {i: words_of(i) for i in range(1, 10)}
def wt(scene, word, nth=0):
    """local time (relative to scene start) when `word` starts being spoken"""
    st = VO[scene - 1][0]; hits = [w for w in WORDS[scene] if w[0].lower().strip('.,?').startswith(word)]
    return st + hits[nth][1] - SCENES[scene - 1][0]

def build_captions():
    caps = []
    for i, (st, _) in enumerate(VO, 1):
        ws = [(w.replace('Section', 'Sek'), a, b) for w, a, b in WORDS[i]]
        chunks, cur = [], []
        for w_ in ws:
            cur.append(w_)
            txt = ' '.join(x[0] for x in cur)
            if len(txt) >= 16 or (w_[0].endswith(('.', ',', '?')) and len(cur) >= 2):
                chunks.append(cur); cur = []
        if cur:
            if chunks and len(cur) == 1: chunks[-1] += cur
            else: chunks.append(cur)
        for k, c in enumerate(chunks):
            a = st + c[0][1] - 0.05
            b = st + (chunks[k + 1][0][1] - 0.05 if k + 1 < len(chunks) else c[-1][2] + 0.35)
            caps.append((a, b, [x[0] for x in c]))
    return caps

def caption_sprite(words):
    f = F('InterDisplay-Black.otf', 66); stroke = 7
    toks = [w_.rstrip('.,?') for w_ in words]
    toks = [w_.upper() for w_ in toks]
    sp = f.getbbox(' ')[2] + 4
    ws = [f.getbbox(t)[2] for t in toks]
    w = sum(ws) + sp * (len(toks) - 1) + stroke * 2 + 20; h = 66 + stroke * 2 + 34
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = stroke + 10
    for t, tw, raw in zip(toks, ws, words):
        key = raw.rstrip('.,?').lower()
        col = GOLD2 if key in GOLDWORDS else WHITE
        d.text((x, stroke + 8), t, font=f, fill=col, stroke_width=stroke, stroke_fill=(8, 12, 20))
        x += tw + sp
    return shadowed(im, blur=10, off=(0, 5), alpha=160)

# ---------------- static sprites ----------------
SP = {}
def build_sprites():
    SP['caps'] = [(a, b, caption_sprite(c)) for a, b, c in build_captions()]
    # S1
    SP['t1a'] = text_sprite([("DOUBLE STOREY", F('InterDisplay-Black.otf', 118), WHITE)])
    SP['t1b'] = text_sprite([("TERRACE HOUSE", F('InterDisplay-ExtraBold.otf', 92), GOLD2)])
    SP['p1'] = pill("Shah Alam Sek 30", F('Inter-ExtraBold.otf', 46), NAVY, GOLD, ico='pin', ico_color=NAVY)
    # persistent
    SP['loc'] = pill("Shah Alam Sek 30", F('Inter-Bold.otf', 30), WHITE, (13, 27, 46, 200), padx=24, pady=12, ico='pin', ico_color=GOLD, outline=(234, 186, 76, 160))
    # S2
    SP['c2'] = pill("EXTERIOR  ·  FRONT VIEW", F('Inter-Bold.otf', 30), NAVY, GOLD, padx=26, pady=12)
    SP['t2'] = text_sprite([("Modern & Practical", F('InterDisplay-Black.otf', 104), WHITE),
                            ("designed for family living", F('InterDisplay-SemiBold.otf', 52), GOLD2)])
    # S3
    SP['c3'] = pill("EXTERIOR DETAILS", F('InterDisplay-Black.otf', 52), NAVY, GOLD, padx=36, pady=18, radius=14)
    SP['f3'] = [card(["Modern Facade"], 'house'), card(["Contemporary Design"], 'layers', w=600), card(["Large Windows", "& Natural Light"], 'window')]
    # S4
    SP['tag4'] = pill("GROUND FLOOR", F('InterDisplay-Black.otf', 52), NAVY, GOLD, padx=36, pady=18, radius=14)
    SP['f4'] = [card(["Welcoming", "Living Area"], 'house', w=500), card(["Well-planned", "Dining Space"], 'family', w=500)]
    # S5
    SP['tag5'] = pill("KITCHEN", F('InterDisplay-Black.otf', 52), NAVY, GOLD, padx=36, pady=18, radius=14)
    SP['f5'] = [check_card("Functional Layout"), check_card("Ample Storage"), check_card("Good Ventilation")]
    SP['tick'] = icon('check', 54, GOLD2)
    # S6
    SP['tag6'] = pill("FIRST FLOOR", F('InterDisplay-Black.otf', 52), NAVY, GOLD, padx=36, pady=18, radius=14)
    SP['f6'] = card(["Comfortable Bedrooms", "for the Whole Family"], 'bed', w=640, fsize=40)
    # S7
    SP['tag7'] = pill("LOCATION & AMENITIES", F('InterDisplay-Black.otf', 44), NAVY, GOLD, padx=32, pady=16, radius=14)
    SP['f7'] = [card(["Nearby Schools"], 'school', w=640), card(["Shopping & Dining"], 'cart', w=640),
                card(["Easy Highway Access", "KESAS · Federal Highway"], 'road', w=640), card(["Parks & Recreation"], 'tree', w=640)]
    # S8
    SP['t8'] = text_sprite([("KEY HIGHLIGHTS", F('InterDisplay-Black.otf', 64), GOLD2)])
    hl = []
    for ico, lab in [('house', ["Double", "Storey"]), ('m2', ["Terrace", "House"]), ('family', ["Family-", "Friendly"]), ('pin', ["Shah Alam", "Sek 30"])]:
        D = 230; c = canvas(D, D); d = ImageDraw.Draw(c)
        d.ellipse((0, 0, D * SS - 1, D * SS - 1), fill=(13, 27, 46, 225), outline=GOLD, width=5 * SS)
        d.ellipse((14 * SS, 14 * SS, (D - 14) * SS, (D - 14) * SS), outline=(234, 186, 76, 90), width=2 * SS)
        im = down(c); ic = icon(ico, 118, GOLD2, lw=6); im.alpha_composite(ic, ((D - 118) // 2, (D - 118) // 2))
        lbl = text_sprite([(lab[0], F('InterDisplay-ExtraBold.otf', 46), WHITE), (lab[1], F('InterDisplay-ExtraBold.otf', 46), WHITE)], align='center', shadow=False)
        full = Image.new('RGBA', (max(D, lbl.width), D + 24 + lbl.height), (0, 0, 0, 0))
        full.alpha_composite(im, ((full.width - D) // 2, 0)); full.alpha_composite(lbl, ((full.width - lbl.width) // 2, D + 24))
        hl.append(shadowed(full))
    SP['f8'] = hl
    # S9
    SP['t9'] = text_sprite([("Interested in", F('InterDisplay-Black.otf', 104), WHITE), ("this home?", F('InterDisplay-Black.otf', 104), WHITE)], align='right')
    SP['btn'] = pill("Contact Us Today", F('InterDisplay-ExtraBold.otf', 60), NAVY, GOLD, padx=48, pady=26, ico='phone', ico_color=NAVY)
    SP['sub9'] = text_sprite([("Find out more or arrange a viewing", F('Inter-SemiBold.otf', 38), (235, 235, 235))])
    # overlays
    g = np.zeros((H, W), np.float32)
    yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
    vig = np.clip((np.sqrt(xx ** 2 * 0.8 + ((yy - 0.5) * 2) ** 2 * 0.8) - 0.55) / 0.8, 0, 1) * 0.55
    bot = np.clip((yy - 0.68) / 0.32, 0, 1) ** 1.4 * 0.7
    top = np.clip((0.16 - yy) / 0.16, 0, 1) * 0.35
    a = np.clip(vig + bot + top + g, 0, 0.85)
    ov = np.zeros((H, W, 4), np.uint8); ov[..., 3] = (a * 255).astype(np.uint8)
    SP['vig'] = Image.fromarray(ov, 'RGBA')
    def side(right=True, strength=0.72, start=0.45):
        x = np.linspace(0, 1, W)[None, :].repeat(H, 0)
        a = np.clip((x - start) / (1 - start), 0, 1) if right else np.clip(((1 - x) - start) / (1 - start), 0, 1)
        a = (a ** 0.9) * strength
        o = np.zeros((H, W, 4), np.uint8); o[..., :3] = NAVY; o[..., 3] = (a * 255).astype(np.uint8)
        return Image.fromarray(o, 'RGBA')
    SP['gradR'] = side(True); SP['gradL'] = side(False, 0.6, 0.5)

def scene_alpha(t, i):
    s, e = SCENES[i - 1]
    return min(ease_out((t - s) / 0.25), 1 - ease_io((t - (e - 0.25)) / 0.25))

def render(fi):
    t = fi / FPS
    fr = background(t).convert('RGBA')
    sc = next(i for i, (s, e) in enumerate(SCENES, 1) if s <= t < e or (i == 9 and t >= s))
    s0 = SCENES[sc - 1][0]; lt = t - s0; A = scene_alpha(t, sc)
    fr.alpha_composite(SP['vig'])
    # side gradients for text legibility
    gr = {1: 'gradR', 3: 'gradR', 4: 'gradR', 5: 'gradR', 6: 'gradR', 7: 'gradL', 9: 'gradR', 2: 'gradL'}.get(sc)
    if gr:
        g = SP[gr]
        if A < 0.999:
            g = g.copy(); g.putalpha(g.split()[3].point(lambda v: int(v * A)))
        fr.alpha_composite(g)

    if sc == 1:
        a = anim(lt, 0.35, 0.5); paste(fr, SP['t1a'], 1840 + 0 * (1 - a), 300 - 40 * (1 - a), a * A, anchor='rt')
        a = anim(lt, 0.7, 0.5); paste(fr, SP['t1b'], 1840 + 60 * (1 - a), 440, a * A, anchor='rt')
        a = anim(lt, 1.6, 0.45); paste(fr, SP['p1'], 1840, 590, min(1, a * 2) * A, scale=0.6 + 0.4 * ease_back((lt - 1.6) / 0.45), anchor='rt')
        # gold underline wipe
        a = anim(lt, 1.0, 0.6)
        if a > 0:
            d = ImageDraw.Draw(fr); x1 = 1840; x0 = x1 - int(520 * a)
            d.rectangle((x0, 562, x1, 568), fill=GOLD + (int(255 * A),))
    elif sc == 2:
        a = anim(lt, 0.2); paste(fr, SP['c2'], 80, 110, a * A)
        a = anim(lt, 0.45, 0.55); paste(fr, SP['t2'], 80 - 50 * (1 - a), 190, a * A)
    elif sc == 3:
        a = anim(lt, 0.2, 0.45); paste(fr, SP['c3'], 80, 110, min(1, a * 2) * A, scale=0.7 + 0.3 * ease_back((lt - 0.2) / 0.45))
        for k, ti in enumerate([wt(3, 'modern'), wt(3, 'contemporary'), wt(3, 'large')]):
            a = anim(lt, ti, 0.5); paste(fr, SP['f3'][k], 1840 + 200 * (1 - a), 290 + k * 170, a * A, anchor='rt')
    elif sc == 4:
        a = anim(lt, 0.2, 0.45); paste(fr, SP['tag4'], 80, 110, min(1, a * 2) * A, scale=0.7 + 0.3 * ease_back((lt - 0.2) / 0.45))
        for k, ti in enumerate([wt(4, 'welcoming'), wt(4, 'well-planned')]):
            a = anim(lt, ti, 0.5); paste(fr, SP['f4'][k], 1840 + 200 * (1 - a), 330 + k * 180, a * A, anchor='rt')
    elif sc == 5:
        a = anim(lt, 0.2, 0.45); paste(fr, SP['tag5'], 80, 110, min(1, a * 2) * A, scale=0.7 + 0.3 * ease_back((lt - 0.2) / 0.45))
        for k, ti in enumerate([wt(5, 'practical') + 0.3, wt(5, 'ample'), wt(5, 'good')]):
            a = anim(lt, ti, 0.45); y = 300 + k * 150
            paste(fr, SP['f5'][k], 1820 + 200 * (1 - a), y, a * A, anchor='rt')
            b = (lt - ti - 0.3) / 0.3
            if b > 0:
                x0 = 1820 - 560 + 26
                paste(fr, SP['tick'], x0 + 28, y + 52, A, scale=0.5 + 0.5 * ease_back(b), anchor='c')
    elif sc == 6:
        a = anim(lt, 0.2, 0.45); fade = 1 - ease_io((lt - 4.5) / 0.3)
        paste(fr, SP['tag6'], 80, 110, min(1, a * 2) * A * fade, scale=0.7 + 0.3 * ease_back((lt - 0.2) / 0.45))
        a = anim(lt, 4.95, 0.55); paste(fr, SP['f6'], 1840 + 220 * (1 - a), 330, a * A, anchor='rt')
    elif sc == 7:
        # pulsing rings at baked pin
        sh = SHOTS[7]; k = ease_io(lt / (sh[2] - sh[1]))
        x = sh[4][0] + (sh[5][0] - sh[4][0]) * k; y = sh[4][1] + (sh[5][1] - sh[4][1]) * k; w = sh[4][2] + (sh[5][2] - sh[4][2]) * k
        punch = 1 + 0.07 * (1 - ease_out(lt / 0.45)); cx, cy = x + w / 2, y + w * 9 / 32; w /= punch; x, y = cx - w / 2, cy - w * 9 / 32
        px = (150 - x) * W / w; py = (113 - y) * W / w
        ring = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
        for ph in (0, 0.5):
            p = ((lt * 0.8 + ph) % 1.0); r = 30 + 170 * p; al = int(220 * (1 - p) * A)
            d.ellipse((px - r, py - r * 0.55, px + r, py + r * 0.55), outline=GOLD2 + (al,), width=5)
        fr.alpha_composite(ring)
        a = anim(lt, 0.2, 0.45); paste(fr, SP['tag7'], 80, 110, min(1, a * 2) * A, scale=0.7 + 0.3 * ease_back((lt - 0.2) / 0.45))
        for k, ti in enumerate([wt(7, 'schools'), wt(7, 'shopping'), wt(7, 'major'), wt(7, 'recreational')]):
            a = anim(lt, ti, 0.5); paste(fr, SP['f7'][k], 80 - 220 * (1 - a), [235, 380, 525, 700][k], a * A)
    elif sc == 8:
        a = anim(lt, 0.15, 0.5); paste(fr, SP['t8'], W / 2, 175 - 30 * (1 - a), a * A, anchor='c')
        d = ImageDraw.Draw(fr)
        for k, ti in enumerate([wt(8, 'double'), wt(8, 'terrace'), wt(8, 'family-friendly'), wt(8, 'great')]):
            cx = 420 + k * 360
            b = (lt - ti) / 0.5
            if b > 0: paste(fr, SP['f8'][k], cx, 500, min(1, b * 2) * A, scale=0.5 + 0.5 * ease_back(b), anchor='c')
            if k < 3:
                c = anim(lt, ti + 0.3, 0.4)
                if c > 0: d.line((cx + 180, 500 - 120 * c, cx + 180, 500 + 120 * c), fill=(234, 186, 76, int(160 * A)), width=3)
    elif sc == 9:
        a = anim(lt, 0.25, 0.55); paste(fr, SP['t9'], 1840 + 60 * (1 - a), 250, a * A, anchor='rt')
        tb = wt(9, 'contact'); b = (lt - tb) / 0.5
        if b > 0:
            pulse = 1 + 0.035 * math.sin(max(0, lt - tb - 0.6) * 2 * math.pi * 1.4) * (lt > tb + 0.6)
            paste(fr, SP['btn'], 1840 - SP['btn'].width / 2 + SP['btn'].info['pad'], 600, min(1, b * 2) * A,
                  scale=(0.5 + 0.5 * ease_back(b)) * pulse, anchor='c')
        a = anim(lt, wt(9, 'find'), 0.5); paste(fr, SP['sub9'], 1840, 710, a * A, anchor='rt')

    # persistent location chip (after intro)
    if t >= 5.0:
        a = anim(t, 5.2, 0.5); paste(fr, SP['loc'], 1860, 40, a, anchor='rt')
    # captions
    for a0, a1, spr in SP['caps']:
        if a0 <= t < a1 + 0.02:
            p = (t - a0) / 0.14
            paste(fr, spr, W / 2, 965, min(1, p * 1.5), scale=0.85 + 0.15 * ease_back(p), anchor='c')
            break
    # progress bar
    d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, W, 7), fill=(255, 255, 255, 60))
    d.rectangle((0, 0, int(W * t / DUR), 7), fill=GOLD + (255,))
    out = fr.convert('RGB')
    # fade from/to black
    fade = min(ease_out(t / 0.35), 1 - ease_io((t - (DUR - 0.5)) / 0.5))
    if fade < 0.999: out = ImageEnhance.Brightness(out).enhance(max(0, fade))
    return out.tobytes()

def init():
    load_sources(); build_sprites()

if __name__ == '__main__':
    out = sys.argv[1]
    frames = range(int(DUR * FPS))
    if len(sys.argv) > 2:  # preview specific seconds as PNG
        init()
        for s in sys.argv[2:]:
            Image.frombytes('RGB', (W, H), render(int(float(s) * FPS))).save(f'{out}_{s}.png')
        sys.exit()
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, b in enumerate(pool.imap(render, frames, chunksize=4)):
            ff.stdin.write(b)
            if i % 150 == 0: print('frame', i, flush=True)
    ff.stdin.close(); ff.wait()
