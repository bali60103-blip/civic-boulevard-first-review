# 沿線步行經驗剖面（2026-10-13 使用者：「有什麼統計能代替沿街走路的經驗」→「先做沿線剖面圖」）
#   取樣：沿市民大道中心線（02 S.center，西→東，里程 0＝起點）每 5 m 一站，向北、南各打垂直射線，
#     第一個碰到的「第一排街廓」（01 frontage_blocks＋frontage_blocks_full）邊緣＝路緣 F（街廓含人行道）；人行道後緣（04 street_detail sw，
#     無資料者取 F＋4 m）向內 8 m 內（容騎樓 3.64 m 與小退縮）：
#     先碰到圍籬（OSM barrier_*）＝圍籬；有建物且該建物有一樓店面＝活躍；有建物無店面＝無店建物；皆無＝開放地（退縮、廣場、公園、停車）；
#     射線未碰到第一排街廓＝巷口／路口（開口）。
#   六項指標（每 100 m、南北分列；後台 CSV 另存每 5 m 取樣）：
#     1 出入口密度＝臨大道面 25 m 內之一樓店面門牌數（稅籍 27 定位；店面型行業 47／48〔487 除外〕、56、86、93、96；一樓、地下或未載樓層；
#       同一完整地址 ≥ 3 家＝借址登記不計；同一門牌只算一個門）。參考：Gehl 好的立面每 100 m 約 15–25 個出入口。
#     2 活躍立面比例＝臨大道面（不含開口）中「活躍」之長度比例。
#     3 最長無出入段＝連續非活躍、非開口之長度（圍籬、無店建物、開放地；沿線無處可進出、也無巷可轉）。
#     4 行道樹＝人行道帶（臨大道面向外 20 m 內）之樹穴數（04 street_detail tree_pit）。
#     5 橋面＝大道剖面（北側 F 至南側 F）位於高架橋面投影（02 S.deck）下之比例；另記人行道（F 外 2.5 m）是否在橋面下。
#     6 繞行＝到正對面同一里程之點須多走的距離＝2 × 至最近穿越點（各單元 19 統計之平面穿越＋跨越大道之人行天橋）的里程差；
#       地下可穿越範圍（地下街、車站地下通廊、捷運站體與中心線相交者）另以色帶標示，不計入繞行。
#   限制：臨大道面依第一排街廓與線稿建物；店面為稅籍登記（下限）；圍籬依 OSM；橋面投影為推估；樹穴僅含 04 街道細部範圍之人行道樹穴（公園、園區內樹木未計）；Z8 中心線止於 E307105，基隆路側約 100 m 未取樣，
#     且 Z8 地面道路沿臺北機廠北緣偏離高架、中心線穿過機廠：取樣點離高架 > 25 m 者改以最近之高架點為起點（沿高架走），里程仍依中心線。
import sys, json, csv, re, importlib.util, collections
from pathlib import Path
import numpy as np
from shapely.geometry import shape, Point, LineString
from shapely.ops import unary_union, transform, substring, nearest_points
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
STEP, BIN, RAY, DEPTH = 5.0, 100.0, 250.0, 12.0
OUTD = H / 'data'

def load():
    argv = sys.argv; sys.argv = [argv[0], 'A1']
    spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
    S.VARIANT['full'] = True
    spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py'); F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
    sys.argv = argv
    return S, F

def compute(S, F):
    C = S.center; L = C.length
    cut_s = [C.project(g.intersection(C) if g.intersection(C).geom_type == 'Point' else g.intersection(C).centroid) for g in F.CUT_G]
    s0 = cut_s[0]
    tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
    # 第一排街廓（南北分開）
    FB = json.load(open(OUTD / 'frontage_blocks_EPSG3826.geojson'))['features'] + json.load(open(OUTD / 'frontage_blocks_full_EPSG3826.geojson'))['features']   # Z1–Z8（150 m 截斷）＋整塊版（Z4、Z6–Z8）
    # 射線碰到哪個第一排街廓即以之為臨大道面（不依 01 之 side 標記：Z8 機廠被標為南側）
    ALLB = [shape(f['geometry']).buffer(0) for f in FB]
    blk = {'N': ALLB, 'S': ALLB}; tAll = STRtree(ALLB); tblk = {'N': tAll, 'S': tAll}
    ELEV = unary_union([S.elev])
    # 建物（逐棟）＋店面
    B = [b for b in S.polys(S.bld) if b.area > 4]; tB = STRtree(B)
    rows = list(csv.DictReader(open(OUTD / 'official_shops_geocoded_EPSG3826.csv', encoding='utf-8-sig')))
    addr_n = collections.Counter(r['營業地址'] for r in rows)
    def storefront(code): return (code[:2] in ('47', '48') and not code.startswith('487')) or code[:2] in ('56', '86', '93', '96')
    shops = [r for r in rows if r['樓層'] in ('1F', 'B', '未載') and storefront(r['行業代號']) and addr_n[r['營業地址']] < 3]
    doors = {}
    for r in shops:
        m = re.match(r'^(.*?號)', r['營業地址']); key = m.group(1) if m else r['營業地址']
        doors.setdefault(key, Point(float(r['E']), float(r['N'])))
    active = set()
    for p in doors.values():
        for i in tB.query(p.buffer(6)):
            if B[i].distance(p) <= 6: active.add(int(i))
    # 圍籬
    BAR = [transform(tf, shape(f['geometry'])) for f in json.load(open(OUTD / 'osm_furniture_4326.geojson'))['features'] if f['properties']['kind'].startswith('barrier_')]
    BAR = [g for g in BAR if g.distance(C) < 400]; tBAR = STRtree(BAR) if BAR else None
    # 樹穴
    SD = json.load(open(OUTD / 'street_detail_EPSG3826.geojson'))['features']
    trees = [shape(f['geometry']).centroid for f in SD if f['properties'].get('kind') == 'tree_pit']
    SW = [shape(f['geometry']).buffer(0) for f in SD if f['properties'].get('kind') in ('sw', 'sw_marked', 'sw_setback')]; tSW = STRtree(SW)
    deck = S.deck
    # 穿越點（各單元 19 統計，15 m 內合併）＋跨越大道之人行天橋；地下可穿越範圍
    xs, fb, ug = [], [], []
    for z in ['Z%d' % i for i in range(1, 9)]:
        d = json.load(open(OUTD / f'{z}_ns_factors_EPSG3826.geojson'))
        xs += [float(v) for v in d['stats'].get('crossings', [])]
        for f in d['features']:
            p = f['properties']; g = shape(f['geometry'])
            if p['cls'] != 'pass_area': continue
            if p['type'] == '人行天橋' and g.intersects(C):
                fb.append((C.project(g.intersection(C).centroid), p.get('name', '')))
            if p['type'] in ('地下街', '車站地下通廊', '捷運／車站站體') and g.intersects(C.buffer(8)):
                seg = g.intersection(C.buffer(8)); ss = [C.project(Point(c)) for q in getattr(seg, 'geoms', [seg]) for c in q.exterior.coords] if seg.geom_type in ('Polygon', 'MultiPolygon') else []
                if ss: ug.append((min(ss), max(ss), p.get('name', '')))
    xs = sorted(xs); xm = []
    for v in xs:
        if not xm or v - xm[-1] > 15: xm.append(v)
    fbm = sorted({round(s): (s, n) for s, n in fb}.values())
    allx = np.array(sorted(xm + [s for s, _ in fbm]))
    # ---- 逐站 ----
    st = []
    for s in np.arange(s0, L - 1, STEP):
        p = C.interpolate(s); a, b = C.interpolate(max(0, s - 3)), C.interpolate(min(L, s + 3))
        if p.distance(ELEV) > 25: p = nearest_points(ELEV, p)[0]   # Z8：地面道路偏離高架，中心線穿過機廠 → 改沿高架取樣（里程仍依中心線）
        t = np.array([b.x - a.x, b.y - a.y]); t /= np.linalg.norm(t); nrm = np.array([-t[1], t[0]])   # 左＝北（西→東）
        rec = {'s': round(s, 1)}; Fpt = {}
        for sd, sg in (('N', 1), ('S', -1)):
            ray = LineString([(p.x, p.y), (p.x + sg * nrm[0] * RAY, p.y + sg * nrm[1] * RAY)])
            dmin = None
            for i in tblk[sd].query(ray):
                g = blk[sd][i].intersection(ray)
                if g.is_empty: continue
                dd = min(ray.project(Point(c)) for q in getattr(g, 'geoms', [g]) for c in q.coords)
                dmin = dd if dmin is None else min(dmin, dd)
            if dmin is None:
                rec[f'type_{sd}'] = 'opening'; rec[f'd_{sd}'] = np.nan; rec[f'back_{sd}'] = np.nan; rec[f'sw_{sd}'] = np.nan; rec[f'udeck_{sd}'] = False; continue
            Fpt[sd] = ray.interpolate(dmin)
            iv = []
            for i in tSW.query(substring(ray, max(0, dmin - 2), dmin + 40)):
                g = SW[i].intersection(ray)
                for q in getattr(g, 'geoms', [g]):
                    if not q.is_empty and q.geom_type == 'LineString': iv.append(sorted(ray.project(Point(c)) for c in q.coords)[::len(q.coords) - 1])
            back = dmin + 4.0
            for a_, b_ in sorted(iv):
                if a_ <= back + 1.0 and b_ > dmin - 2: back = max(back if a_ > dmin + 4 else dmin, b_)
            back = max(back, dmin + 1.5)
            seg = substring(ray, max(0, dmin - 3), back + 8.0)
            db, bi = None, None
            for i in tB.query(seg):
                g = B[i].intersection(seg)
                if g.is_empty: continue
                dd = min(ray.project(Point(c)) for q in getattr(g, 'geoms', [g]) for c in q.coords)
                if db is None or dd < db: db, bi = dd, int(i)
            dfn = None
            if tBAR is not None:
                for i in tBAR.query(substring(ray, max(0, dmin - 4), back + 8.0)):
                    g = BAR[i].intersection(substring(ray, max(0, dmin - 4), back + 8.0))
                    if g.is_empty: continue
                    dd = min(ray.project(Point(c)) for q in getattr(g, 'geoms', [g]) for c in q.coords)
                    dfn = dd if dfn is None else min(dfn, dd)
            if dfn is not None and (db is None or dfn < db - .5): ty = 'fence'
            elif db is not None: ty = 'active' if bi in active else 'blank'
            else: ty = 'open'
            rec[f'type_{sd}'] = ty; rec[f'd_{sd}'] = round(dmin, 1); rec[f'back_{sd}'] = round(back, 1); rec[f'sw_{sd}'] = round(back - dmin, 1)
            rec[f'udeck_{sd}'] = bool(deck.contains(ray.interpolate((dmin + back) / 2)))
        if 'N' in Fpt and 'S' in Fpt:
            sec = LineString([Fpt['S'], Fpt['N']]); rec['deck_share'] = round(sec.intersection(deck).length / sec.length, 3) if sec.length > 1 else np.nan
            rec['width'] = round(sec.length, 1)
        else: rec['deck_share'] = np.nan; rec['width'] = np.nan
        k = np.abs(allx - s).min() if len(allx) else np.nan
        rec['detour'] = round(2 * k, 1)
        rec['underground'] = any(a_ <= s <= b_ for a_, b_, _ in ug)
        st.append(rec)
    # 店門、樹穴歸站：投影至中心線、依側別與 F 距離篩選
    sarr = np.array([r['s'] for r in st])
    dser = {sd: np.array([r[f'd_{sd}'] for r in st], float) for sd in ('N', 'S')}
    bser = {sd: np.array([r[f'back_{sd}'] for r in st], float) for sd in ('N', 'S')}
    for ser in (dser, bser):   # 開口處以前後站內插
        for sd in ser:
            v = ser[sd]; ok = ~np.isnan(v)
            if ok.any(): ser[sd] = np.interp(sarr, sarr[ok], v[ok])
    def assign(pts, lo, hi):
        out = {'N': [], 'S': []}
        for p in pts:
            s = C.project(p)
            if s < s0 or s > sarr[-1] + STEP: continue
            q = C.interpolate(s); a, b = C.interpolate(max(0, s - 3)), C.interpolate(min(L, s + 3))
            side = 'N' if (b.x - a.x) * (p.y - q.y) - (b.y - a.y) * (p.x - q.x) > 0 else 'S'
            dist = p.distance(q); dF = np.interp(s, sarr, dser[side]); dB = np.interp(s, sarr, bser[side])
            if dF + lo <= dist <= dB + hi: out[side].append(s)
        return out
    door_s = assign(list(doors.values()), -5, 20)     # 路緣內 5 m（避開分隔島）至人行道後緣外 20 m
    tree_s = assign(trees, -4, 2)                     # 人行道帶（路緣內 4 m 至後緣外 2 m）
    return dict(st=st, s0=s0, L=L, cut_s=cut_s, xm=xm, fb=fbm, ug=ug, door_s=door_s, tree_s=tree_s,
                n_doors=len(doors), n_trees=len(trees), n_bar=len(BAR))

def runs(st, sd):
    # 最長無出入段：連續之圍籬、無店建物、開放地（活躍或開口即中斷）
    out, cur = [], None
    for r in st:
        bad = r[f'type_{sd}'] in ('fence', 'blank', 'open')
        if bad and cur is None: cur = [r['s'], r['s']]
        elif bad: cur[1] = r['s']
        elif cur is not None: out.append((cur[0], cur[1] + STEP)); cur = None
    if cur: out.append((cur[0], cur[1] + STEP))
    return out

def bins(R):
    st, s0 = R['st'], R['s0']; edges = np.arange(s0, R['L'] + BIN, BIN); out = []
    rn = {sd: runs(st, sd) for sd in ('N', 'S')}
    for b0, b1 in zip(edges[:-1], edges[1:]):
        sub = [r for r in st if b0 <= r['s'] < b1]
        if not sub: continue
        ln = len(sub) * STEP; row = {'s0': round(b0), 's1': round(min(b1, R['L'])), 'len': ln}
        for sd in ('N', 'S'):
            fr = [r for r in sub if r[f'type_{sd}'] != 'opening']; fl = max(len(fr), 1)
            row[f'doors_{sd}'] = round(sum(b0 <= s < b1 for s in R['door_s'][sd]) * 100 / ln, 1)
            row[f'active_{sd}'] = round(100 * sum(r[f'type_{sd}'] == 'active' for r in fr) / fl, 1)
            row[f'blank_{sd}'] = round(100 * sum(r[f'type_{sd}'] in ('blank', 'fence') for r in fr) / fl, 1)
            row[f'fence_{sd}'] = round(100 * sum(r[f'type_{sd}'] == 'fence' for r in fr) / fl, 1)
            row[f'open_{sd}'] = round(100 * sum(r[f'type_{sd}'] == 'open' for r in fr) / fl, 1)
            row[f'opening_{sd}'] = round(100 * (len(sub) - len(fr)) / len(sub), 1)
            row[f'run_{sd}'] = max([b - a for a, b in rn[sd] if a < b1 and b > b0] or [0])
            row[f'trees_{sd}'] = round(sum(b0 <= s < b1 for s in R['tree_s'][sd]) * 100 / ln, 1)
            row[f'udeck_{sd}'] = round(100 * sum(r[f'udeck_{sd}'] for r in sub) / len(sub), 1)
        ds = [r['deck_share'] for r in sub if not np.isnan(r['deck_share'])]
        row['deck_share'] = round(100 * float(np.mean(ds)), 1) if ds else np.nan
        row['detour_mean'] = round(float(np.mean([r['detour'] for r in sub])), 0)
        row['detour_max'] = round(float(np.max([r['detour'] for r in sub])), 0)
        row['underground'] = round(100 * sum(r['underground'] for r in sub) / len(sub), 1)
        out.append(row)
    return out, rn

if __name__ == '__main__' and '--chart' not in sys.argv:
    S, F = load()
    R = compute(S, F)
    BN, RN = bins(R)
    with open(OUTD / 'walk_profile_stations.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(R['st'][0].keys())); w.writeheader(); w.writerows(R['st'])
    with open(OUTD / 'walk_profile_100m.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(BN[0].keys())); w.writeheader(); w.writerows(BN)
    json.dump({k: v for k, v in R.items() if k not in ('st', 'door_s', 'tree_s')} | {'runs': RN,
              'door_s': R['door_s'], 'tree_s': R['tree_s']}, open(OUTD / 'walk_profile_meta.json', 'w'), ensure_ascii=False, default=float)
    c = collections.Counter(r[f'type_{sd}'] for r in R['st'] for sd in ('N', 'S'))
    print('stations', len(R['st']), 'types', dict(c), '| doors', R['n_doors'], 'assigned', {k: len(v) for k, v in R['door_s'].items()},
          '| trees', R['n_trees'], 'assigned', {k: len(v) for k, v in R['tree_s'].items()}, '| barriers', R['n_bar'])
    print('crossings', len(R['xm']), 'footbridges', [(round(s), n) for s, n in R['fb']], 'underground', [(round(a), round(b), n) for a, b, n in R['ug']])
    for sd in ('N', 'S'):
        top = sorted(RN[sd], key=lambda ab: ab[0] - ab[1])[:6]
        print(sd, 'longest runs', [(round(a), round(b), round(b - a)) for a, b in top])

# ======================= 剖面圖（A1 橫式） =======================
RUN_NAMES = {('S', 5382): '光復南路—基隆路南側（松菸・大巨蛋）', ('S', 1952): '華山南側（大草原・B01）', ('N', 5627): '臺北機廠南緣',
             ('S', 52): '淡水河堤—塔城街南側', ('S', 702): '延平北路—承德路南側（雙子星工地・機捷）', ('S', 3297): '建國高架以東南側（忠泰美術館・瑠公圳公園）'}
def chart():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Rectangle
    S, F = load()
    BN = list(csv.DictReader(open(OUTD / 'walk_profile_100m.csv', encoding='utf-8-sig')))
    ST = list(csv.DictReader(open(OUTD / 'walk_profile_stations.csv', encoding='utf-8-sig')))
    M = json.load(open(OUTD / 'walk_profile_meta.json'))
    num = lambda v: float(v) if v not in ('', 'nan', 'None') else np.nan
    x0, x1 = M['s0'], M['L']; cuts = M['cut_s']
    RED, BLD, PATH, GRN, TEAL, ZC, BAR_C = '#DF9134', '#141414', '#E3E3E3', '#91D099', '#12A594', S.ZONE_C, '#4D4D4D'
    plt.rcParams['hatch.color'] = BLD; plt.rcParams['hatch.linewidth'] = .45
    FW, FH, MMI = 841, 594, 1 / 25.4; PX0, PX1 = 74, 818
    fig = plt.figure(figsize=(FW * MMI, FH * MMI))
    fig.add_artist(Rectangle((10 / FW, 10 / FH), (FW - 20) / FW, (FH - 20) / FH, transform=fig.transFigure, fill=False, lw=.8))
    fig.text(22 / FW, 1 - 26 / FH, 'Z1–Z8 沿線步行經驗剖面｜市民大道兩側臨大道面（每 100 m）', fontsize=20, va='top')
    fig.text(22 / FW, 1 - 37 / FH, '沿市民大道中心線每 5 m 取樣，向南北打射線至第一排街廓之臨大道面（人行道後緣向內 8 m）；北側畫在基線上方、南側畫在下方。'
             f'取樣 {len(ST)} 站 × 2 側；出入口＝稅籍一樓店面門牌，樹＝樹穴，圍籬＝OSM，橋面＝高架橋面投影（推估）。', fontsize=8, va='top', color='#555')
    edges = [(num(r['s0']), num(r['s1'])) for r in BN]
    rows = [('comp', '臨大道面組成', '各類占取樣長度 %', 74), ('doors', '出入口密度', '一樓店面門牌數／100 m', 54), ('run', '最長無出入段', '連續無店面、無巷口之長度 m', 56),
            ('trees', '行道樹', '人行道帶樹穴數／100 m', 44), ('sw', '人行道寬', '路緣至人行道後緣 m（每 100 m 中位數）', 44),
            ('deck', '橋面覆蓋', '大道剖面（兩側路緣間）位於高架橋面下 %', 38), ('detour', '到正對面多走', '至最近穿越點往返之距離 m（平均）', 56)]
    ytop = FH - 84; axes = {}
    k_ = (ytop - 48 - 7 * (len(rows) - 1)) / sum(r[3] for r in rows)    # 依可用高度等比放大各列
    rows = [(a, b, c, d * k_) for a, b, c, d in rows]
    for key, ttl, sub, h in rows:
        ax = fig.add_axes([PX0 / FW, (ytop - h) / FH, (PX1 - PX0) / FW, h / FH]); axes[key] = ax
        ax.set_xlim(x0, x1)
        for sp in ('top', 'right', 'left'): ax.spines[sp].set_visible(False)
        ax.spines['bottom'].set_visible(False); ax.tick_params(axis='x', length=0, labelbottom=False); ax.tick_params(axis='y', labelsize=6, length=2, colors='#666')
        for c in cuts[1:]: ax.axvline(c, color=ZC, lw=.7, ls=(0, (6, 3)), zorder=6)
        fig.text(22 / FW, (ytop - 3) / FH, ttl, fontsize=10, fontweight='bold', va='top', color='#222')
        for i, ln in enumerate(N_wrap(sub, 13)): fig.text(22 / FW, (ytop - 9.5 - i * 3.6) / FH, ln, fontsize=6.3, va='top', color='#666')
        if key not in ('deck', 'detour'):
            fig.text((PX0 - 13) / FW, (ytop - h * .25) / FH, '北', fontsize=7.5, ha='right', va='center', color='#333')
            fig.text((PX0 - 13) / FW, (ytop - h * .75) / FH, '南', fontsize=7.5, ha='right', va='center', color='#333')
        ytop -= h + 7
    def mirror(ax, key, lim, fmt=lambda v: f'{abs(v):g}'):
        for (a, b), r in zip(edges, BN):
            for sd, sg in (('N', 1), ('S', -1)):
                v = num(r[f'{key}_{sd}'])
                if not np.isnan(v) and v > 0: ax.bar(a, sg * min(v, lim), width=b - a, align='edge', color=BAR_C, lw=0, zorder=2)
        ax.axhline(0, color='#999', lw=.5, zorder=1); ax.set_ylim(-lim, lim)
        ax.set_yticks([-lim, -lim / 2, 0, lim / 2, lim]); ax.set_yticklabels([fmt(v) for v in (-lim, -lim / 2, 0, lim / 2, lim)])
    # 1 組成
    ax = axes['comp']; cats = [('active', TEAL, None, '活躍（一樓有店面）'), ('blank', BLD, None, '無店建物'), ('fence', 'white', '////', '圍牆／圍籬'),
                              ('open', GRN, None, '開放地（退縮、廣場、公園、工地、停車）'), ('opening', PATH, None, '巷口／路口')]
    for (a, b), r in zip(edges, BN):
        for sd, sg in (('N', 1), ('S', -1)):
            op = num(r[f'opening_{sd}']); f_ = 1 - op / 100; cum = 0
            vals = {'active': num(r[f'active_{sd}']) * f_, 'blank': (num(r[f'blank_{sd}']) - num(r[f'fence_{sd}'])) * f_,
                    'fence': num(r[f'fence_{sd}']) * f_, 'open': num(r[f'open_{sd}']) * f_, 'opening': op}
            for k, col, hat, _ in cats:
                v = vals[k]
                if v > 0: ax.bar(a, sg * v, bottom=sg * cum, width=b - a, align='edge', color=col, hatch=hat, lw=0, zorder=2); cum += v
    ax.axhline(0, color='#999', lw=.5); ax.set_ylim(-100, 100); ax.set_yticks([-100, -50, 0, 50, 100]); ax.set_yticklabels(['100', '50', '0', '50', '100'])
    # 2 出入口
    ax = axes['doors']; mirror(ax, 'doors', 16)
    for y in (15, -15): ax.axhline(y, color='#888', lw=.6, ls=(0, (2, 2)), zorder=1)
    ax.text(x1, 15.5, 'Gehl：好的立面每 100 m 約 15–25 個出入口', fontsize=6.3, ha='right', va='bottom', color='#666')
    # 3 最長無出入段
    ax = axes['run']; mirror(ax, 'run', 900)
    for sd, sg in (('N', 1), ('S', -1)):
        for a, b in M['runs'][sd]:
            nm = RUN_NAMES.get((sd, int(round(a))))
            if nm: ax.text((a + b) / 2, sg * (b - a + 25), f'{nm} {b - a:,.0f} m', fontsize=6.3, ha='center', va='bottom' if sg > 0 else 'top', color='#222', zorder=4,
                           bbox=dict(boxstyle='square,pad=.15', fc='white', ec='none', alpha=.85))
    # 4 行道樹
    mirror(axes['trees'], 'trees', 20)
    # 5 人行道寬（每 100 m 中位數）
    ax = axes['sw']; sarr = np.array([num(r['s']) for r in ST])
    for (a, b) in edges:
        m = (sarr >= a) & (sarr < b)
        for sd, sg in (('N', 1), ('S', -1)):
            v = np.array([num(r[f'sw_{sd}']) for r in np.array(ST)[m]]); v = v[~np.isnan(v)]
            if len(v): ax.bar(a, sg * min(np.median(v), 16), width=b - a, align='edge', color=BAR_C, lw=0, zorder=2)
    ax.axhline(0, color='#999', lw=.5); ax.set_ylim(-16, 16); ax.set_yticks([-16, -8, 0, 8, 16]); ax.set_yticklabels(['16', '8', '0', '8', '16'])
    # 6 橋面覆蓋
    ax = axes['deck']
    for (a, b), r in zip(edges, BN):
        v = num(r['deck_share'])
        if not np.isnan(v): ax.bar(a, v, width=b - a, align='edge', color=BAR_C, lw=0, zorder=2)
    ax.set_ylim(0, 100); ax.set_yticks([0, 50, 100]); ax.axhline(0, color='#999', lw=.5)
    # 7 到正對面多走
    ax = axes['detour']
    for (a, b), r in zip(edges, BN): ax.bar(a, num(r['detour_mean']), width=b - a, align='edge', color=BAR_C, lw=0, zorder=2)
    for a, b, nm in M['ug']: ax.add_patch(Rectangle((a, -150), b - a, 130, color=RED, alpha=.35, lw=0, zorder=1))
    for x in M['xm']: ax.plot([x, x], [-150, -20], color=RED, lw=1.1, zorder=3)
    for x, nm in M['fb']: ax.plot(x, -85, marker='^', color=RED, ms=5, zorder=4)
    ax.axhline(0, color='#999', lw=.5); ax.set_ylim(-160, 1100); ax.set_yticks([0, 500, 1000])
    ax.tick_params(axis='x', labelbottom=True, labelsize=6.5, colors='#555'); ax.set_xticks(np.arange(0, x1, 500))
    ax.set_xlabel('里程 m（市民大道中心線，自西端起）', fontsize=7, color='#555')
    # 單元標示＋各單元摘要
    yb = FH - 62
    for i, z in enumerate(['Z%d' % k for k in range(1, 9)]):
        a = cuts[i]; b = cuts[i + 1] if i + 1 < len(cuts) else x1
        xa = PX0 + (a - x0) / (x1 - x0) * (PX1 - PX0); xb = PX0 + (b - x0) / (x1 - x0) * (PX1 - PX0); xc = (xa + xb) / 2
        sub = [r for r in ST if a <= num(r['s']) < b]; n = max(len(sub), 1); lg = n * STEP
        fr = [(r, sd) for r in sub for sd in 'NS' if r[f'type_{sd}'] != 'opening']
        act = 100 * sum(r[f'type_{sd}'] == 'active' for r, sd in fr) / max(len(fr), 1)
        dr = sum(a <= s_ < b for sd in 'NS' for s_ in M['door_s'][sd]) * 100 / (2 * lg)
        tr = sum(a <= s_ < b for sd in 'NS' for s_ in M['tree_s'][sd]) * 100 / (2 * lg)
        rmax = max([min(bb, b) - max(aa, a) for sd in 'NS' for aa, bb in M['runs'][sd] if aa < b and bb > a] or [0])
        fig.add_artist(plt.Line2D([(xa + .8) / FW, (xb - .8) / FW], [(yb + 3) / FH] * 2, transform=fig.transFigure, color=ZC, lw=1.4))
        fig.text(xc / FW, (yb + 1) / FH, f"{z} {S.short(S.ZP[z]['from'])}—{S.short(S.ZP[z]['to'])}" if xb - xa > 60 else z, fontsize=7.5 if xb - xa > 60 else 8, fontweight='bold', ha='center', va='top', color=ZC)
        txt = [f'門 {dr:.1f}／100 m・活躍 {act:.0f}%', f'最長 {rmax:,.0f} m・樹 {tr:.1f}／100 m'] if xb - xa > 60 else [f'門 {dr:.1f}', f'活躍 {act:.0f}%', f'最長 {rmax:,.0f} m', f'樹 {tr:.1f}']
        for j, t in enumerate(txt): fig.text(xc / FW, (yb - 4.5 - j * 3.3) / FH, t, fontsize=5.8, ha='center', va='top', color='#333')
    # 圖例與說明
    ly = 24
    lx = 22
    for k, col, hat, lab in cats:
        fig.add_artist(Rectangle((lx / FW, (ly - 1.6) / FH), 7 / FW, 3.4 / FH, transform=fig.transFigure, facecolor=col, hatch=hat, edgecolor=BLD if hat else 'none', lw=.3 if hat else 0))
        fig.text((lx + 9) / FW, ly / FH, lab, fontsize=7, va='center'); lx += 13 + len(lab) * 2.55
    fig.add_artist(plt.Line2D([lx / FW, (lx + 6) / FW], [ly / FH] * 2, transform=fig.transFigure, color=RED, lw=1.2)); fig.text((lx + 8) / FW, ly / FH, '平面穿越點', fontsize=7, va='center'); lx += 30
    fig.add_artist(plt.Line2D([(lx + 3) / FW], [ly / FH], transform=fig.transFigure, marker='^', color=RED, ms=5)); fig.text((lx + 8) / FW, ly / FH, '跨越大道之人行天橋', fontsize=7, va='center'); lx += 40
    fig.add_artist(Rectangle((lx / FW, (ly - 1.6) / FH), 7 / FW, 3.4 / FH, transform=fig.transFigure, facecolor=RED, alpha=.35, lw=0)); fig.text((lx + 9) / FW, ly / FH, '地下可穿越（地下街、車站通廊、捷運站體）', fontsize=7, va='center'); lx += 92
    fig.add_artist(plt.Line2D([lx / FW, (lx + 7) / FW], [ly / FH] * 2, transform=fig.transFigure, color=ZC, lw=.8, ls=(0, (6, 3)))); fig.text((lx + 9) / FW, ly / FH, '單元界線', fontsize=7, va='center')
    fig.text(22 / FW, 15 / FH, '限制：臨大道面依第一排街廓與線稿建物；店面為稅籍登記之下限（門牌在側街之轉角店計入）；圍籬依 OSM；橋面投影為推估；'
             'Z8 地面道路偏離高架，該段沿高架取樣；Z8 中心線止於 E307105，基隆路側約 100 m 未取樣。資料：data/walk_profile_*.csv（scripts/39_walk_profile.py）。', fontsize=6, va='center', color='#666')
    out = H / '主題圖_沿線步行經驗剖面'; out.mkdir(exist_ok=True)
    stem = 'Z1-Z8_沿線步行經驗剖面_A1'
    with PdfPages(out / f'{stem}.pdf') as pdf: pdf.savefig(fig)
    fig.savefig(out / f'{stem}_預覽.png', dpi=110); plt.close(fig)
    print(stem)

def N_wrap(t, n):
    return [t[i:i + n] for i in range(0, len(t), n)]

if __name__ == '__main__' and '--chart' in sys.argv:
    chart()
