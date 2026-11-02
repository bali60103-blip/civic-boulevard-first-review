# 植物名牌 6×4 cm，A4 直式 3 欄 × 7 列，蘋方-繁
# 用法：python3 make_plant_tags.py <植物名錄.rtf> <字型資料夾> <輸出.pdf>
# 字型資料夾內放 PingFangTC-Regular.otf、PingFangTC-Medium.otf
# （由系統 PingFang.ttc 第 2、6 號字型抽出）
import os
import re
import sys
import fitz

RTF, FONT_DIR, OUT = sys.argv[1:4]
MM = 72 / 25.4
W, H = 60, 40                     # 名牌尺寸 mm
COLS, ROWS = 3, 7
PAGE_W, PAGE_H = 210, 297
MX = (PAGE_W - COLS * W) / 2      # 15 mm
MY = (PAGE_H - ROWS * H) / 2      # 8.5 mm
PAD = 5                           # 四周留白
INNER = W - 2 * PAD               # 50 mm
SCI_MAX = 44                      # 學名一行超過此寬度就換行，兩側再多留 3 mm

# 字級層級（pt）、字距（em）、顏色
TITLE = dict(size=18, track=0.15, weight='Medium', color=(0.1, 0.1, 0.1))
SCI = dict(size=7.5, track=0.03, weight='Regular', color=(0.15, 0.15, 0.15))
LABEL = dict(size=6.5, track=0.2, weight='Regular', color=(0.3, 0.3, 0.3))
ATTR = dict(size=6.5, track=0.2, weight='Regular', color=(0.5, 0.5, 0.5))
SCI_LEAD = 1.8                    # 學名兩行時的行距（倍）
TITLE_GAP = 4.2                   # 中文名基線下緣到學名頂的間距 mm
RULE_Y = 9.8                      # 細線位置 mm（自名牌頂起算）

HABIT = {'H': '草本', 'T': '喬木', 'S': '灌木', 'C': '藤本'}
ORIGIN = {'V': '原生', 'E': '特有', 'R': '歸化', 'D': '栽培'}
INFRA = {'var.', 'subsp.', 'ssp.', 'f.'}

fonts = {w: fitz.Font(fontfile=os.path.join(FONT_DIR, f'PingFangTC-{w}.otf'))
         for w in ('Regular', 'Medium')}


def parse(path):
    src = open(path, encoding='latin-1').read()
    body = src[src.index('\\f0\\fs24'):]
    body = body.replace('\\uc0', '')
    body = re.sub(r'\\u(\d+) ?', lambda m: chr(int(m.group(1))), body)
    body = body.replace('\\f0\\fs24 \\cf0 ', '').replace('\\\n', '\n').rstrip('}')
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    plants, family = [], None
    pat = re.compile(r'^(\d+)\.\s+(.+?)\s+(\S+)\s+\((\w),\s*(\w),\s*(\w)\)$')
    for l in lines:
        m = pat.match(l)
        if not m:
            family = l
            continue
        no, sci, zh, habit, origin, _ = m.groups()
        plants.append(dict(no=no, sci=sci, zh=zh, family=family,
                           attr=f'{HABIT[habit]}・{ORIGIN[origin]}'))
    return plants


def width(text, st):
    """含字距的寬度 mm（末字後不加字距，置中才準）"""
    f, size = fonts[st['weight']], st['size']
    adv = sum(f.text_length(ch, fontsize=size) for ch in text)
    return (adv + st['track'] * size * (len(text) - 1)) / MM


def put(page, x, y, text, st, italic=False):
    """x, y 為 mm（左側基線）；逐字排以加字距；斜體以 12° 錯切模擬
    錯切矩陣作用在 PDF 的 y 向上座標，正值才是右傾"""
    f, size = fonts[st['weight']], st['size']
    tw = fitz.TextWriter(page.rect)
    px = x * MM
    for ch in text:
        tw.append(fitz.Point(px, y * MM), ch, font=f, fontsize=size)
        px += f.text_length(ch, fontsize=size) + st['track'] * size
    morph = (fitz.Point(x * MM, y * MM), fitz.Matrix(1, 0, 0.21, 1, 0, 0)) if italic else None
    tw.write_text(page, color=st['color'], morph=morph)


def sci_segments(sci):
    """屬名、種小名、種下名斜體，命名人與 var. 等正體"""
    toks = sci.split()
    segs, italic_next = [], False
    for i, t in enumerate(toks):
        segs.append((t, i < 2 or italic_next))
        italic_next = t in INFRA
    return segs


def sci_width(segs):
    return width(' '.join(t for t, _ in segs), SCI)


def put_sci_line(page, cx, y, segs):
    x = cx - sci_width(segs) / 2
    space = width(' ', SCI) + SCI['track'] * SCI['size'] / MM
    for t, italic in segs:
        put(page, x, y, t, SCI, italic=italic)
        x += width(t, SCI) + space


def draw_tag(page, x0, y0, p):
    page.draw_rect(fitz.Rect(x0 * MM, y0 * MM, (x0 + W) * MM, (y0 + H) * MM),
                   color=(0.7, 0.7, 0.7), width=0.25)

    # 上列：科名（左）、習性・屬性（右），字頂齊留白線
    label_em = LABEL['size'] / MM
    ly = y0 + PAD + 0.88 * label_em
    put(page, x0 + PAD, ly, p['family'], LABEL)
    put(page, x0 + W - PAD - width(p['attr'], ATTR), ly, p['attr'], ATTR)
    page.draw_line(fitz.Point((x0 + PAD) * MM, (y0 + RULE_Y) * MM),
                   fitz.Point((x0 + W - PAD) * MM, (y0 + RULE_Y) * MM),
                   color=(0.75, 0.75, 0.75), width=0.3)

    # 學名：一行放不下就拆成「二名」／「命名人」兩行
    segs = sci_segments(p['sci'])
    sci_lines = [segs] if sci_width(segs) <= SCI_MAX else [segs[:2], segs[2:]]

    # 中文名＋學名整塊在細線下方垂直置中（以字面高度計，不含行高空白）
    t_em = TITLE['size'] / MM
    s_em = SCI['size'] / MM
    lead = SCI_LEAD * s_em
    block = t_em + TITLE_GAP + 0.72 * s_em + lead * (len(sci_lines) - 1) + 0.2 * s_em
    top = y0 + RULE_Y + (H - RULE_Y - PAD - block) / 2
    cx = x0 + W / 2

    ty = top + 0.88 * t_em
    put(page, cx - width(p['zh'], TITLE) / 2, ty, p['zh'], TITLE)

    y = ty + 0.12 * t_em + TITLE_GAP + 0.72 * s_em
    for line in sci_lines:
        put_sci_line(page, cx, y, line)
        y += lead


def main():
    plants = parse(RTF)
    doc = fitz.open()
    per_page = COLS * ROWS
    for i, p in enumerate(plants):
        if i % per_page == 0:
            page = doc.new_page(width=PAGE_W * MM, height=PAGE_H * MM)
        k = i % per_page
        draw_tag(page, MX + (k % COLS) * W, MY + (k // COLS) * H, p)
    doc.subset_fonts()
    doc.save(OUT, garbage=4, deflate=True)
    print(f'{len(plants)} 張名牌，{len(doc)} 頁 → {OUT}')


main()
