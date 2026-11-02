# 各段代表照片紅色疊圖（2026-10-15）：黑白底圖；只有高架與主角建築以紅色覆蓋——紅依明暗疊色（陰影深者紅較深）
#   2026-10-15 使用者修改：取消圖塊外框紅線；紅色彩度降低（SAT）
#   選片：每段三張透視清楚者（Z3 僅一處拍攝點；Z1、Z8 無照片）
#   範圍：data/photos/red_masks.json（elevated 高架、protagonist 主角建築；人工判讀多邊形，主角依 workflow 第三節＋GPS 方位核對）
#   python3 43_photo_red.py [check DIR]：check 只出範圍檢核圖（原色照片＋綠框）
import json, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageChops
H = Path(__file__).resolve().parents[1]
SRC = Path.home() / 'Desktop/civic photo'
OUT = H / '現場照片_紅色疊圖_各段三張'
IDX = {r['id']: r for r in json.load(open(H / 'data/photos/photo_index.json'))}
MASK = json.load(open(H / 'data/photos/red_masks.json'))
TR = MASK
RED_D, RED_M, RED_L = (58, 0, 10), (196, 22, 42), (255, 226, 228)    # 疊色：陰影 → 中間調 → 亮部（明暗跟照片走）
SAT = 0.55                                                            # 紅色彩度（1＝原飽和紅；與同明暗灰混合降彩度）

def bw(im):
    g = ImageOps.autocontrast(im.convert('L'), cutoff=1)
    return Image.blend(g, ImageOps.equalize(g), .35)                  # 黑白底圖：自動對比＋等化 35%

def red_fill(g):
    # 遮罩內再拉一次對比（陰影更深、亮部更亮），讓紅色明暗跟著結構陰影走
    g2 = ImageOps.autocontrast(g, cutoff=2)
    red = ImageOps.colorize(g2, black=RED_D, mid=RED_M, white=RED_L, midpoint=120)
    gray = Image.merge('RGB', [red.convert('L')] * 3)                  # 同明度之灰：混合只降彩度、不改明暗
    return Image.blend(gray, red, SAT)

def render(im, m):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    pw = 1500 if im.width >= im.height else 900; k = im.width / pw
    polys = [Polygon(p) for p in m['elevated']] + [Polygon(q['poly']) for q in m['protagonist']]
    U = unary_union([p.buffer(0) for p in polys])
    g = bw(im); base = g.convert('RGB')
    mask = Image.new('L', im.size, 0); d = ImageDraw.Draw(mask)
    for p in getattr(U, 'geoms', [U]):
        d.polygon([(x * k, y * k) for x, y in p.exterior.coords], fill=255)
        for r in p.interiors: d.polygon([(x * k, y * k) for x, y in r.coords], fill=0)
    return Image.composite(red_fill(g), base, mask)

if __name__ == '__main__':
    check = 'check' in sys.argv[1:]
    scratch = Path(sys.argv[2]) if check and len(sys.argv) > 2 else None
    if not check: OUT.mkdir(exist_ok=True)
    for z, photos in MASK.items():
        if z.startswith('_'): continue
        for i, (pid, m) in enumerate(photos.items(), 1):
            im = ImageOps.exif_transpose(Image.open(SRC / IDX[pid]['file'])).convert('RGB')
            if check:
                im.thumbnail((1500, 1600)); dr = ImageDraw.Draw(im)
                for p in m['elevated']: dr.line([tuple(c) for c in p] + [tuple(p[0])], fill=(0, 255, 0), width=3)
                for q in m['protagonist']: dr.line([tuple(c) for c in q['poly']] + [tuple(q['poly'][0])], fill=(255, 0, 255), width=3)
                im.save(scratch / f'{z}_{pid}.jpg', quality=80); continue
            render(im, m).save(OUT / f'{z}_{i}_{pid}_紅色疊圖.jpg', quality=92, dpi=(300, 300))
            print(z, pid)

# ---------- 總覽 PDF（A3 橫式，每段一頁：三張照片＋編號／判讀依據）與說明 ----------
def overview():
    import csv, fitz, io
    rd = {Path(r['檔案']).stem: r for r in csv.DictReader(open(H / 'data/photos/photo_reading.csv', encoding='utf-8-sig'))}
    ZP = {f['properties']['id']: f['properties'] for f in json.load(open(H.parent / '03_南京至仁愛_沿線土地使用分析_20261006/data/zones_EPSG3826.geojson'))['features'] if 'id' in f['properties']}
    FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
    mm = 72 / 25.4; W, Hh = 420 * mm, 297 * mm
    doc = fitz.open()
    for z, photos in TR.items():
        if z.startswith('_'): continue
        pg = doc.new_page(width=W, height=Hh); pg.insert_font(fontname='hg', fontfile=FONT)
        zp = ZP[z]
        pg.insert_text((14 * mm, 16 * mm), f"{z}　{zp['from']}—{zp['to']}｜現場照片紅色疊圖", fontname='hg', fontsize=15)
        pg.insert_text((14 * mm, 22 * mm), f"{zp['info']}｜黑白底圖；紅＝高架與主角建築，依明暗疊色（陰影越深紅越深），低彩度、無外框｜主角：" + ('、'.join(sorted({q['name'].split('（')[0] for m in photos.values() for q in m['protagonist']})) or '照片中無可確認之主角建築'),
                       fontname='hg', fontsize=7, color=(.3, .3, .3))
        n = len(photos); gap = 6 * mm; x0 = 14 * mm; top = 30 * mm; avail_w = W - 28 * mm; avail_h = Hh - top - 16 * mm
        CAP = 15 * mm                                                      # 每列圖說高
        files = sorted(OUT.glob(f'{z}_*_紅色疊圖.jpg'))
        asp = [Image.open(f).size[0] / Image.open(f).size[1] for f in files]
        # 排法：所有依序分列方式（例 3 張：3／2+1／1+2／1+1+1），每列等高填滿寬度，整體不超出可用高時等比縮小；取照片面積最大者
        def parts(k):
            if k == 0: yield []; return
            for i in range(1, k + 1):
                for rest in parts(k - i): yield [i] + rest
        best = None
        for pt in parts(n):
            rows_, i = [], 0
            for c in pt: rows_.append(list(range(i, i + c))); i += c
            hs = [(avail_w - gap * (len(r) - 1)) / sum(asp[j] for j in r) for r in rows_]
            fixed = CAP * len(rows_) + gap * (len(rows_) - 1)
            k_ = min(1.0, (avail_h - fixed) / sum(hs)); hs = [h * k_ for h in hs]
            area = sum(h * h * sum(asp[j] for j in r) for h, r in zip(hs, rows_))
            if best is None or area > best[0]: best = (area, rows_, hs)
        _, rows_, hs = best
        y = top + max(0, (avail_h - sum(hs) - CAP * len(rows_) - gap * (len(rows_) - 1)) / 2)
        for r, hgt in zip(rows_, hs):
            tot = sum(hgt * asp[j] for j in r) + gap * (len(r) - 1); x = x0 + (avail_w - tot) / 2
            for j in r:
                f = files[j]; ww = hgt * asp[j]
                im = Image.open(f); im.thumbnail((int(ww / mm / 25.4 * 300), int(hgt / mm / 25.4 * 300)))
                b = io.BytesIO(); im.save(b, 'JPEG', quality=85)
                pg.insert_image(fitz.Rect(x, y, x + ww, y + hgt), stream=b.getvalue())
                pid = f.stem.split('_', 2)[2].replace('_紅色疊圖', '')
                rr = rd.get(pid, {})
                loc = rr.get('定位方式', ''); loc = loc.replace('內容判讀：', '依 ') if loc else ''
                pg.insert_text((x, y + hgt + 4.5 * mm), pid, fontname='hg', fontsize=8.5, color=(142 / 255, 27 / 255, 62 / 255))
                pg.insert_textbox(fitz.Rect(x, y + hgt + 6 * mm, x + ww, y + hgt + CAP),
                                  f"{rr.get('相機', '')}｜{rr.get('拍攝時間（EXIF）', '')[:10].replace(':', '-') if rr.get('相機') == 'iPhone 17 Pro' else '時鐘未設'}"
                                  f"｜位置：{loc[:70]}", fontname='hg', fontsize=6.2, color=(.3, .3, .3))
                x += ww + gap
            y += hgt + CAP + gap
        pg.insert_text((14 * mm, Hh - 10 * mm), '來源：~/Desktop/civic photo 原始照片；選片＝各段透視清楚者三張（Z3 僅一處拍攝點，Z1、Z8 無照片）｜程式 scripts/43_photo_red.py｜範圍 data/photos/red_masks.json',
                       fontname='hg', fontsize=6, color=(.4, .4, .4))
    doc.save(OUT / '現場照片紅色疊圖_各段總覽_A3.pdf', garbage=3, deflate=True)
    (OUT / '說明.txt').write_text(
        '現場照片紅色疊圖｜各段三張｜2026-10-15\n\n'
        '檔名：{單元}_{序}_{照片編號}_紅色疊圖.jpg（原圖解析度，300 dpi）；現場照片紅色疊圖_各段總覽_A3.pdf（每段一頁）。\n'
        '處理：黑白底圖（自動對比＋等化 35%）；只有高架（橋面、柱、帽梁；照片中可見之建國高架一併）與主角建築覆蓋紅色，\n'
        '  紅依明暗疊色（遮罩內再拉對比）：陰影 #3A000A → 中間調 #C4162A → 亮部 #FFE2E4，再與同明度灰混合降彩度（SAT＝0.55）；不畫外框線。\n'
        '主角建築（workflow 第三節，照片中可確認者）：Z2 臺北轉運站（IMG_4585、4591，GPS 方位核對）、京站時尚廣場（IMG_4587）；\n'
        '  Z5 建國啤酒廠煙囪（DSC08738）；Z6 懷生國小（DSC08512，使用者指定之滲透場所）。\n'
        '  Z3（U17）、Z4（華山）、Z7（夜間餐飲帶）所選照片中無可確認之主角建築，只疊高架。\n'
        '選片：Z2 IMG_4585、4591、4587｜Z3 IMG_4594｜Z4 DSC08746、08776、IMG_4622｜Z5 DSC08715、08729、08738｜\n'
        '  Z6 DSC08512、08526、08534｜Z7 DSC08592、08648、08695（Z1、Z8 無現場照片）。\n'
        '範圍：data/photos/red_masks.json（人工判讀多邊形）。重現：python3 scripts/43_photo_red.py（需 ~/Desktop/civic photo）。\n'
        '舊版（負片反紅）見 _舊版_反紅/。\n'
        'A4/：每段一頁 A4 橫式（頁緣 22 mm、照片間距 7 mm），頁面只標段落名稱；Z2–Z7 各一檔＋現場照片紅色疊圖_A4_合併.pdf（6 頁），照片 300 dpi。\n',
        encoding='utf-8')
    print('overview', OUT / '現場照片紅色疊圖_各段總覽_A3.pdf')

if __name__ == '__main__' and 'check' not in sys.argv[1:]:
    overview()

# ---------- A4（2026-10-15 使用者：16 張分進 A4、不要文字只要段落）：A4 每段一頁，只標段落名稱 ----------
#   同日修改：一律橫式 A4；留白加大（頁緣 22 mm、照片間距 7 mm）
def a4():
    import fitz, io
    ZP = {f['properties']['id']: f['properties'] for f in json.load(open(H.parent / '03_南京至仁愛_沿線土地使用分析_20261006/data/zones_EPSG3826.geojson'))['features'] if 'id' in f['properties']}
    FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
    mm = 72 / 25.4; M = 22 * mm; gap = 7 * mm; top = M + 9 * mm
    D = OUT / 'A4'; D.mkdir(exist_ok=True)
    alldoc = fitz.open()
    for z, photos in MASK.items():
        if z.startswith('_'): continue
        files = sorted(OUT.glob(f'{z}_*_紅色疊圖.jpg')); asp = [Image.open(f).size[0] / Image.open(f).size[1] for f in files]
        def parts(k):
            if k == 0: yield []; return
            for i in range(1, k + 1):
                for rest in parts(k - i): yield [i] + rest
        best = None
        for W, Hh in ((297 * mm, 210 * mm),):
          avail_w, avail_h = W - 2 * M, Hh - top - M
          for pt in parts(len(files)):
            rows_, i = [], 0
            for c in pt: rows_.append(list(range(i, i + c))); i += c
            hs = [(avail_w - gap * (len(r) - 1)) / sum(asp[j] for j in r) for r in rows_]
            k_ = min(1.0, (avail_h - gap * (len(rows_) - 1)) / sum(hs)); hs = [h * k_ for h in hs]
            area = sum(h * h * sum(asp[j] for j in r) for h, r in zip(hs, rows_))
            if best is None or area > best[0] * 1.02: best = (area, rows_, hs, W, Hh)   # 面積差 < 2% 時保留先試之橫式
        _, rows_, hs, W, Hh = best; avail_w, avail_h = W - 2 * M, Hh - top - M
        doc = fitz.open(); pg = doc.new_page(width=W, height=Hh); pg.insert_font(fontname='hg', fontfile=FONT)
        zp = ZP[z]
        pg.insert_text((M, M + 4 * mm), f"{z}　{zp['from']}—{zp['to']}", fontname='hg', fontsize=10)
        y = top + (avail_h - sum(hs) - gap * (len(rows_) - 1)) / 2
        for r, hgt in zip(rows_, hs):
            tot = sum(hgt * asp[j] for j in r) + gap * (len(r) - 1); x = M + (avail_w - tot) / 2
            for j in r:
                ww = hgt * asp[j]; im = Image.open(files[j])
                im.thumbnail((int(ww / mm / 25.4 * 300), int(hgt / mm / 25.4 * 300)))
                b = io.BytesIO(); im.save(b, 'JPEG', quality=88)
                pg.insert_image(fitz.Rect(x, y, x + ww, y + hgt), stream=b.getvalue())
                x += ww + gap
            y += hgt + gap
        doc.save(D / f"{z}_{zp['from'].split('（')[0]}-{zp['to'].split('（')[0]}_A4.pdf", garbage=3, deflate=True)
        alldoc.insert_pdf(doc)
    alldoc.save(D / '現場照片紅色疊圖_A4_合併.pdf', garbage=3, deflate=True)
    print('A4', sorted(p.name for p in D.iterdir()))

if __name__ == '__main__' and 'check' not in sys.argv[1:]:
    a4()
