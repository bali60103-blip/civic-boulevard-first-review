# 停車場建物判讀：北市好停車路外停車場（08_parking_fetch.py）就近對應線稿建物
# 依地址判型：建物內（地下／地上層、立體、停車塔）→ 對應建物；平面（空地、旁、對面、巷口）、公共地下（公園、學校、市民大道地下）、橋下 → 不對應建物
import json, re, csv, collections
from pathlib import Path
from shapely.geometry import shape, Point, mapping
from shapely.strtree import STRtree

H = Path(__file__).resolve().parents[1]; D = H / 'data'
MAXD = 30  # 停車場座標多為入口，可能落在騎樓或道路側；30 m 內取最近建物

def lot_type(n, a):
    t = (n or '') + '|' + (a or '')
    if re.search(r'橋下|高架', t): return '橋下'
    if re.search(r'詳附件', a or ''): return '共享車位（多點）'
    if re.search(r'空地|旁$|對面|平面停車場|臨時|巷口|交叉|弄$|巷$', a or '') and not re.search(r'地下|層', a or ''): return '平面'
    if re.search(r'公園|國小|國中|高中|高級中學|地下街|堤外|廢鐵道|市民大道.{0,3}段停車場', n or ''): return '公共地下'  # 公園、學校、地下街下方，名稱優先
    if re.search(r'公園|廣場|市民大道.*地下|地下街|堤外|廢鐵道|段停車場', t) and not re.search(r'大樓|號地下', a or ''): return '公共地下'
    if re.search(r'地下|地上|層|樓|停車塔|立體|號', a or ''): return '建物'
    return '平面'

DB = json.load(open(D / 'drawing_buildings_zone_EPSG3826.geojson'))['features']
G = [shape(f['geometry']) for f in DB]; tree = STRtree(G)
lots = [f for f in json.load(open(D / 'parking_pma_EPSG3826.geojson'))['features'] if f['properties']['kind'] == 'lot']
out, rows = {}, []
for f in lots:
    p = f['properties']; pt = Point(f['geometry']['coordinates']); ty = lot_type(p['name'], p['addr'])
    bid, dist = None, None
    if ty == '建物':
        inside = [int(i) for i in tree.query(pt, predicate='within')]
        if inside:
            bid, dist = max(inside, key=lambda i: G[i].area), 0.0
        else:
            i = tree.query_nearest(pt, max_distance=MAXD)
            if len(i): bid = int(i[0]); dist = round(G[bid].distance(pt), 1)
    rows.append({'停車場': p['name'], '地址': p['addr'], '類型': p['type'], '判型': ty, '汽車格': p['car'], '機車格': p['moto'],
                 '單元': p['zone'], '對應建物bid': '' if bid is None else bid, '距離_m': '' if dist is None else dist,
                 '判讀': ('建物內' if dist == 0 else f'就近 {dist} m') if bid is not None else ('建物內但 30 m 內無線稿建物' if ty == '建物' else '不對應建物')})
    if bid is not None:
        o = out.setdefault(bid, {'lots': [], 'car': 0, 'moto': 0, 'zone': DB[bid]['properties']['zone']})
        o['lots'].append(p['name']); o['car'] += p['car']; o['moto'] += p['moto']
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(G[b]), 'properties': {'bid': b, 'lots': '；'.join(o['lots']), 'car': o['car'],
                                                                                        'moto': o['moto'], 'zone': o['zone']}} for b, o in out.items()]},
          open(D / 'parking_buildings_EPSG3826.geojson', 'w'), ensure_ascii=False)
with open(D / '停車場建物判讀.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
c = collections.Counter(r['判型'] for r in rows); m = collections.Counter(r['判讀'].split(' ')[0] for r in rows if r['判型'] == '建物')
print('判型', dict(c)); print('建物型對應', dict(m)); print('標記建物', len(out), '｜其中 300 m 範圍內', sum(1 for o in out.values() if o['zone']))
