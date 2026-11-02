# 市民大道諾利圖（二）：A1 橫式滿版、1:8,000、無圖例（使用者 2026-10-14「做一張市民大道範圍的諾利圖，範圍填滿 A1 不用圖例」）
#   範圍：淡水河堤（E301030）—基隆路（E307400）置中，圖框 6,728 × 4,752 m，中心 E304240／N2771130，北朝上。
#   諾利圖表現（Nolli 1748 羅馬圖之圖底關係）：
#     私有建物＝黑；街道、廣場、公園、街廓內空地＝白；公共室內（可自由進入之建物內部）＝白底＋黑外框（以外框代替諾利原圖之牆體 poché）。
#     水域＝細橫線。
#   2026-10-14 再修訂（使用者「取消暖黃和材質，下方留白要有比例和指北針」）：恢復白底、無紙紋（PAPER_ON＝False，程式保留可再開啟）；
#     地圖改為上、左、右滿版，下方留白 30 mm 放比例尺（1:8,000，0–1,000 m）與指北針；比例不變，南北範圍隨之縮為約 4.5 km。
#   （前一版）2026-10-14 修訂（使用者「底圖加一些紋理，不要純白，稍微一點暖黃」）：白底改為暖黃米色紙紋（#F5ECD7；細顆粒＋低頻斑駁＋纖維，150 dpi JPEG，置於最底層）；
#     公共室內改為透明（只留外框），紙紋連續透出——街道與公共室內同為一個「地」，更貼近諾利原意。
#   建物來源：市民大道線稿帶（E300935–307545、N2770000–2771910，02_南京至仁愛擴幅 building_outlines_TWD97）用線稿；帶外用 OSM。
#     銜接：以建物代表點判定——代表點落在線稿帶內縮 25 m 範圍者用線稿，其餘用 OSM（避免帶緣被切斷之線稿殘片與 OSM 重疊）。
#   公共室內判定（OSM 2026-09-08）：建物（線稿建物以重疊 ≥ 50% 之 OSM 建物面對應）具下列標籤，或建物內含下列 POI 點——
#     building＝train_station／transportation／church／cathedral／chapel／temple／shrine／mosque／stadium；
#     amenity＝place_of_worship／library／marketplace／theatre／arts_centre／concert_hall／exhibition_centre（建物面另含 post_office）；
#     shop＝mall／department_store；tourism＝museum／gallery；leisure＝stadium／sports_centre（限建物面）；railway／public_transport＝station（限建物面）。
#   輸出：諾利圖_A1_1-8000.pdf（向量）、_預覽.png、_ai_layers/（分層 PDF，03_make_ai.sh 組 AI）
import json, sys, collections
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.path import Path as MPath
from matplotlib.collections import PathCollection
from matplotlib.patches import PathPatch
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
SCALE = 8000
W, Hh = 841.0, 594.0                               # A1 橫式（mm）
MM = 1 / 25.4
CX, CY = 304240.0, 2771130.0
FOOT = 30.0                                        # 下方留白（mm）：比例尺＋指北針（使用者 2026-10-14）
MAP_HMM = Hh - FOOT                                # 地圖高 564 mm
FW, FH = W / 1000 * SCALE, MAP_HMM / 1000 * SCALE  # 6,728 × 4,512 m
FRAME = box(CX - FW / 2, CY - FH / 2, CX + FW / 2, CY + FH / 2)
BAND = box(300935, 2770000, 307545, 2771910)       # 線稿帶
INNER = BAND.buffer(-25)
plt.rcParams['pdf.fonttype'] = 42; plt.rcParams['font.family'] = 'Arial'; plt.rcParams['hatch.linewidth'] = .25
PAPER_ON = False                                   # 紙紋底色（暖黃）：使用者 2026-10-14 取消；改 True 即恢復
PAPER_HEX = '#F5ECD7'                              # 暖黃米色（紙紋平均色）
TEX = H / 'data/paper_texture_A1_150dpi.jpg'
def make_texture(path, dpi=150, seed=20261014):
    # 紙紋：低頻斑駁（紙張厚薄不均，三種尺度）＋細顆粒＋纖維（短曲線，略深／略淺），以亮度乘在 PAPER_HEX 上；固定亂數種子可重現
    from scipy.ndimage import gaussian_filter, zoom
    from PIL import Image, ImageDraw
    rng = np.random.default_rng(seed)
    w, h = int(round(W / 25.4 * dpi)), int(round(Hh / 25.4 * dpi))
    lum = np.zeros((h, w), np.float32)
    for sc, amp in ((260, .020), (90, .015), (28, .010)):
        n = gaussian_filter(rng.standard_normal((h // 4 + 2, w // 4 + 2)).astype(np.float32), sc / 4)
        lum += amp * zoom(n / (n.std() + 1e-9), 4, order=1)[:h, :w]
    g = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), .7); lum += .026 * g / g.std()
    fib = Image.new('L', (w, h), 128); dr = ImageDraw.Draw(fib)
    for _ in range(w * h // 2500):
        x, y = rng.uniform(0, w), rng.uniform(0, h); ang = rng.uniform(0, np.pi); ln = rng.uniform(15, 70); pts = [(x, y)]
        for _k in range(6):
            ang += rng.normal(0, .25); x += np.cos(ang) * ln / 6; y += np.sin(ang) * ln / 6; pts.append((x, y))
        dr.line(pts, fill=int(128 + rng.choice([-1, 1]) * rng.uniform(10, 28)), width=1)
    lum += .05 * gaussian_filter((np.asarray(fib, np.float32) - 128) / 128, .6)
    base = np.array([int(PAPER_HEX[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    Image.fromarray(np.clip(base[None, None, :] * (1 + lum[..., None]), 0, 255).astype(np.uint8)).save(path, quality=88, subsampling=0)
def add_paper(pdf_path):
    # 紙紋置於頁面最底（PyMuPDF overlay=False；JPEG 直接嵌入，避免 matplotlib 以無損方式嵌入造成檔案過大）
    import fitz
    if not TEX.exists(): make_texture(TEX)
    d = fitz.open(pdf_path); d[0].insert_image(d[0].rect, filename=str(TEX), overlay=False)
    tmp = str(pdf_path) + '.tmp'; d.save(tmp, garbage=3, deflate=True); d.close(); Path(tmp).replace(pdf_path)

def polys(g):
    if g is None or g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [q for q in getattr(g, 'geoms', []) if isinstance(q, Polygon)] + [r for q in getattr(g, 'geoms', []) if isinstance(q, MultiPolygon) for r in q.geoms]

# ---------- 建物 ----------
LINE = shape(json.load(open(ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005/building_outlines_TWD97.geojson'))['features'][0]['geometry'])
A = [p for p in polys(LINE) if p.area > 4 and INNER.contains(p.representative_point())]
OF = json.load(open(H / 'data/osm_nolli_EPSG3826.geojson'))['features']
OB = [(shape(f['geometry']).buffer(0), f['properties']) for f in OF if f['properties']['kind'] == 'building']
OB = [(g, p) for g, p in OB if not g.is_empty and g.intersects(FRAME.buffer(50))]
B = [(g, p) for g, p in OB if not INNER.contains(g.representative_point())]
POI = [(shape(f['geometry']), f['properties']) for f in OF if f['properties']['kind'] == 'poi']
WATER = unary_union([shape(f['geometry']).buffer(0) for f in OF if f['properties']['kind'] == 'water']).intersection(FRAME.buffer(20))

PUB_BLD = {'train_station', 'transportation', 'church', 'cathedral', 'chapel', 'temple', 'shrine', 'mosque', 'stadium'}
PUB_AM = {'place_of_worship', 'library', 'marketplace', 'theatre', 'arts_centre', 'concert_hall', 'exhibition_centre'}
def tag_public(p, polygon=True):
    if p.get('building') in PUB_BLD: return 'building=' + p['building']
    if p.get('amenity') in PUB_AM or (polygon and p.get('amenity') == 'post_office'): return 'amenity=' + p['amenity']
    if p.get('shop') in ('mall', 'department_store'): return 'shop=' + p['shop']
    if p.get('tourism') in ('museum', 'gallery'): return 'tourism=' + p['tourism']
    if polygon and p.get('leisure') in ('stadium', 'sports_centre'): return 'leisure=' + p['leisure']
    if polygon and (p.get('railway') == 'station' or p.get('public_transport') == 'station'): return 'station'
    return None
# 公共室內判定（先判 OSM 建物，再對應到線稿建物）：
#   OSM 建物自身標籤符合 → 公共；或建物內含公共 POI 點，且（建物 ≤ 5,000 ㎡，或 POI 為商場／百貨／市場——整棟為公共使用）→ 公共
#     （避免大型綜合建物因內含單一點位〔如醫院內圖書館、市府內展館〕整棟變白）。
#   線稿建物：與公共 OSM 建物之交集 ≥ 50% → 整棟公共；交集 ≥ 50 ㎡ 但未達半數（線稿合併多棟）→ 只把交集部分畫為公共；
#     不在任何 OSM 建物內之公共 POI，落在 ≤ 3,000 ㎡ 之線稿建物內 → 該棟公共。
PT = STRtree([g for g, _ in POI]) if POI else None
WHOLE = {'shop=mall', 'shop=department_store', 'amenity=marketplace'}
MAINUSE = {'hospital', 'clinic', 'school', 'university', 'college', 'government', 'office', 'residential', 'apartments', 'dormitory'}   # 主用途非公共之大型建物（如臺大醫院東址內之商場點）不整棟變白
def osm_public(g, p):
    w_ = tag_public(p)
    if w_: return w_ + (f"（{p['name']}）" if p.get('name') else '')
    if PT is not None:
        for i in PT.query(g):
            if g.contains(POI[i][0]):
                w2 = tag_public(POI[i][1], polygon=False)
                if w2 and (g.area <= 5000 or (w2 in WHOLE and not MAINUSE & {p.get('building'), p.get('amenity')})): return w2 + (f"（{POI[i][1].get('name')}）" if POI[i][1].get('name') else '') + '・點'
    return None
OBP = [(g, p, osm_public(g, p)) for g, p in OB]
PUBO = [(g, w) for g, p, w in OBP if w]
PO_T = STRtree([g for g, _ in PUBO]) if PUBO else None
OB_U = unary_union([g for g, _ in OB])
POI_FREE = [(g, p) for g, p in POI if not OB_U.contains(g) and tag_public(p, polygon=False)]
PRIV, PUB, LOG = [], [], []
for g in A:
    hits = [(PUBO[i][0].intersection(g), PUBO[i][1]) for i in PO_T.query(g)] if PO_T is not None else []
    hits = [(q, w) for q, w in hits if q.area > 0]
    pu = unary_union([q for q, _ in hits]) if hits else None
    if pu is not None and pu.area >= .5 * g.area:
        PUB.append(g); LOG.append(('線稿', round(g.area), max(hits, key=lambda h: h[0].area)[1])); continue
    if pu is not None and pu.area >= 50:
        PRIV += polys(g.difference(pu)); PUB += [q for q in polys(pu) if q.area > 5]
        LOG.append(('線稿（部分）', round(pu.area), max(hits, key=lambda h: h[0].area)[1])); continue
    pf = next((p for q, p in POI_FREE if g.contains(q)), None) if g.area <= 3000 else None
    if pf is not None:
        PUB.append(g); LOG.append(('線稿', round(g.area), tag_public(pf, polygon=False) + (f"（{pf.get('name')}）" if pf.get('name') else '') + '・點')); continue
    PRIV.append(g)
for (g, p), (_, _, w_) in zip(OB, OBP):
    if INNER.contains(g.representative_point()): continue
    g = g.intersection(FRAME.buffer(30))
    if g.is_empty: continue
    for q in polys(g): (PUB if w_ else PRIV).append(q)
    if w_: LOG.append(('OSM', round(g.area), w_))

# ---------- 繪圖 ----------
def ppath(g):
    vs, cs = [], []
    for ring in [g.exterior] + list(g.interiors):
        c = np.asarray(ring.coords)
        if len(c) < 3: continue
        vs.append(c); cs.append(np.r_[MPath.MOVETO, np.full(len(c) - 2, MPath.LINETO), MPath.CLOSEPOLY])
    return MPath(np.concatenate(vs), np.concatenate(cs)) if vs else None
def coll(gs, **kw):
    ps = [q for q in (ppath(g) for g in gs) if q is not None]
    return PathCollection(ps, **kw)
LAYERS = ([('PAPER', '紙紋底色（暖黃）')] if PAPER_ON else []) + [('WATER', '水域（細橫線）'), ('PRIV', '建物（私有，黑）'),
          ('PUB', '公共室內（外框，透出紙紋）' if PAPER_ON else '公共室內（白＋外框）'), ('SCALE', '比例尺・指北針（下方留白）')]
def build(pdf, png, only=None):
    keys = [k for k, _ in LAYERS] if only is None else list(only)
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    ax = fig.add_axes([0, FOOT / Hh, 1, MAP_HMM / Hh]); ax.set_xlim(FRAME.bounds[0], FRAME.bounds[2]); ax.set_ylim(FRAME.bounds[1], FRAME.bounds[3])
    ax.set_aspect('equal'); ax.axis('off'); ax.patch.set_alpha(0)
    if 'WATER' in keys:
        for q in polys(WATER):
            pp = ppath(q)
            if pp is not None: ax.add_patch(PathPatch(pp, facecolor='none', edgecolor='black', lw=0, hatch='-' * 6))
    if 'PRIV' in keys: ax.add_collection(coll(PRIV, facecolors='black', edgecolors='none'))
    if 'PUB' in keys: ax.add_collection(coll(PUB, facecolors='none', edgecolors='black', linewidths=.45))
    if 'SCALE' in keys:   # 下方留白：地圖下緣細線、比例尺（0–1,000 m；前 500 m 每 100 m 分格）＋比例＋指北針，靠右
        paper = PAPER_HEX if PAPER_ON else 'white'
        fig.add_artist(plt.Line2D([0, 1], [FOOT / Hh] * 2, transform=fig.transFigure, color='black', lw=.5))
        u = 1000 / SCALE                                  # 每 m 之圖紙 mm
        x1 = W - 20; x0 = x1 - 1000 * u; yb = 13.0; hb = 2.2
        segs = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500), (500, 1000)]
        for i, (a_, b_) in enumerate(segs):
            fig.add_artist(plt.Rectangle(((x0 + a_ * u) / W, yb / Hh), ((b_ - a_) * u) / W, hb / Hh, transform=fig.transFigure,
                                         facecolor='black' if i % 2 == 0 else paper, edgecolor='black', lw=.5))
        for v in (0, 100, 200, 500, 1000):
            fig.text((x0 + v * u) / W, (yb + hb + 1.2) / Hh, f'{v:,}' + (' m' if v == 1000 else ''), fontsize=8, ha='center', va='bottom')
        fig.text((x0 + 500 * u) / W, (yb - 2.2) / Hh, f'1:{SCALE:,}', fontsize=9, ha='center', va='top')
        nx, ny = x0 - 22, 8.5                              # 指北針：底 ny、高 12 mm
        fig.add_artist(plt.Polygon([(nx / W, (ny + 12) / Hh), ((nx - 2.6) / W, ny / Hh), (nx / W, (ny + 2.4) / Hh)], closed=True, transform=fig.transFigure, facecolor='black', edgecolor='black', lw=.5))
        fig.add_artist(plt.Polygon([(nx / W, (ny + 12) / Hh), ((nx + 2.6) / W, ny / Hh), (nx / W, (ny + 2.4) / Hh)], closed=True, transform=fig.transFigure, facecolor=paper, edgecolor='black', lw=.5))
        fig.text(nx / W, (ny + 13) / Hh, 'N', fontsize=10, ha='center', va='bottom')
    if pdf is not None: pdf.savefig(fig, transparent=PAPER_ON or only is not None)   # 紙紋開啟時底色由 add_paper 提供
    plt.close(fig)

if __name__ == '__main__':
    stem = H / f'市民大道_諾利圖_A1_1-{SCALE}'
    import fitz
    if PAPER_ON and not TEX.exists(): make_texture(TEX)
    with PdfPages(f'{stem}.pdf') as pdf: build(pdf, None)
    if PAPER_ON: add_paper(f'{stem}.pdf')
    fitz.open(f'{stem}.pdf')[0].get_pixmap(dpi=100).save(f'{stem}_預覽.png')
    L = H / '_ai_layers'; L.mkdir(exist_ok=True)
    for f in L.glob('*.pdf'): f.unlink()
    files = []
    for i, (k, nm) in enumerate(LAYERS):
        fn = L / f'{i:02d}_{k}.pdf'
        if k == 'PAPER':   # 紙紋層：只含 JPEG 之 A1 頁
            d = fitz.open(); pg = d.new_page(width=W * 72 / 25.4, height=Hh * 72 / 25.4); pg.insert_image(pg.rect, filename=str(TEX)); d.save(str(fn)); d.close()
        else:
            with PdfPages(fn) as pdf: build(pdf, None, only=[k])
        files.append((nm, str(fn)))
    json.dump(files, open(L / 'layers.json', 'w'), ensure_ascii=False, indent=1)
    c = collections.Counter(w.split('（')[0].split('・')[0] for _, _, w in LOG)
    json.dump([{'來源': s, '面積_m2': a, '依據': w} for s, a, w in sorted(LOG, key=lambda r: -r[1])], open(H / 'data/公共室內判定.json', 'w'), ensure_ascii=False, indent=0)
    print('私有', len(PRIV), '公共室內', len(PUB), '｜線稿', len(A), 'OSM', len(B), '｜水域 ha', round(WATER.area / 1e4, 1))
    print(dict(c.most_common()))
    print('最大公共室內', [(s, a, w) for s, a, w in sorted(LOG, key=lambda r: -r[1])[:15]])
