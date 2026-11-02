# 產業分布：OSM 店家／機構點 → 14 個產業別、5 個產業特性群；各分區家數、組成與區位商數（LQ）
import json, csv, sys, collections
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
D = H / 'data'
sys.path.insert(0, str(ROOT / '01_輸入資料/資料處理程式'))
from sectors import classify as base_classify  # 沿用前案產業分類（依標籤，不猜店名）

tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

# 產業特性群（族）→ 產業別；色彩同族同色系
FAMILIES = [
    ('LIFE', '日常生活服務', [('餐飲', '#D7263D'), ('便利超市', '#F06C7F'), ('生活服務', '#F4A6B3')]),
    ('RET', '消費零售', [('零售', '#F28C28'), ('3C電子', '#C4610B')]),
    ('URB', '都市型產業（修配／汽機車）', [('汽機車', '#6B4E9B'), ('修配製造', '#A58BD0')]),
    ('PRO', '知識／專業服務', [('商辦金融', '#1F5FA8'), ('醫療', '#3F9AD6'), ('教育', '#8EC3EA')]),
    ('TOUR', '觀光文化休閒', [('旅宿', '#1B8A5A'), ('夜生活', '#2FB67C'), ('文化展演', '#7FD3A8'), ('運動休閒', '#B8E6C9')]),
]
IND = [(n, c, fk) for fk, _, items in FAMILIES for n, c in items]
FAM_OF = {n: fk for n, _, fk in IND}

C3 = {'electronics', 'computer', 'mobile_phone', 'hifi', 'video_games', 'camera', 'telecommunication', 'printer_ink', 'radiotechnics'}
SERV = {'hairdresser', 'beauty', 'massage', 'laundry', 'dry_cleaning', 'tailor', 'copyshop', 'photo', 'pet_grooming', 'tattoo', 'cosmetics', 'nail_salon', 'travel_agency', 'funeral_directors', 'repair'}
CULT_A = {'theatre', 'cinema', 'arts_centre', 'studio', 'events_venue', 'conference_centre', 'exhibition_centre'}
CULT_T = {'museum', 'gallery'}

def classify(t):
    s, a = t.get('shop'), t.get('amenity')
    if s in ('vacant', 'no'): return None
    if s in C3: return '3C電子'
    if s in SERV or a in ('internet_cafe',): return '生活服務'
    if a in CULT_A or t.get('tourism') in CULT_T: return '文化展演'
    if a == 'atm': return None  # ATM 不是一家店
    k = base_classify(t)
    return {'商辦': '商辦金融', '金融': '商辦金融'}.get(k, k) if k in {n for n, _, _ in IND} | {'商辦', '金融'} else None

zf = json.load(open(D / 'zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in zf if 'id' in f['properties']]
frame = shape({'type': 'Polygon', 'coordinates': [[(300935, 2770000), (307545, 2770000), (307545, 2771910), (300935, 2771910), (300935, 2770000)]]})

pts = []
for f in json.load(open(D / 'osm_poi_nodes_4326.geojson'))['features']:
    k = classify(f['properties'])
    if k: pts.append((transform(tf, shape(f['geometry'])), k, f['properties'].get('name', ''), 'node'))
# 以面繪製的店家／機構（百貨、旅館、商辦大樓等）取代表點
for f in json.load(open(ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005/source/expanded_osm.geojson'))['features']:
    p = f['properties']
    if f['geometry']['type'] == 'LineString' or not any(x in p for x in ('shop', 'amenity', 'office', 'tourism', 'craft', 'healthcare', 'leisure')): continue
    k = classify(p)
    if k: pts.append((transform(tf, shape(f['geometry'])).representative_point(), k, p.get('name', ''), 'area'))
pts = [p for p in pts if frame.contains(p[0])]

out = []
for pt, k, nm, src in pts:
    zid = next((z['id'] for z, g in ZONES if g.contains(pt)), '')
    out.append({'type': 'Feature', 'geometry': mapping(pt), 'properties': {'ind': k, 'fam': FAM_OF[k], 'name': nm, 'zone': zid, 'src': src}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': out},
          open(D / 'industry_pois_EPSG3826.geojson', 'w'), ensure_ascii=False)

# 統計：各分區家數、密度、LQ（以全部分區合計為基準；分區取自 zones_EPSG3826.geojson，01 重跑後須重跑本程式）
zids = [z['id'] for z, _ in ZONES]; zarea = {z['id']: g.area / 1e4 for z, g in ZONES}
cnt = {z: collections.Counter() for z in zids}
for f in out:
    if f['properties']['zone']: cnt[f['properties']['zone']][f['properties']['ind']] += 1
tot = collections.Counter(); [tot.update(c) for c in cnt.values()]; T = sum(tot.values())
with open(D / '統計_產業_分區.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['分區', '分區土地_ha', '總家數', '密度_家每ha'] + [f'{n}_家數' for n, _, _ in IND] + [f'{n}_LQ' for n, _, _ in IND])
    for z in zids:
        n = sum(cnt[z].values())
        w.writerow([z, round(zarea[z], 1), n, round(n / zarea[z], 1)] + [cnt[z][k] for k, _, _ in IND]
                   + [round((cnt[z][k] / n) / (tot[k] / T), 2) if n and tot[k] else '' for k, _, _ in IND])
    w.writerow([f'{zids[0]}–{zids[-1]}', round(sum(zarea.values()), 1), T, round(T / sum(zarea.values()), 1)] + [tot[k] for k, _, _ in IND] + [1.0] * len(IND))
print('全幅點數', len(out), '｜分區內', T)
print(open(D / '統計_產業_分區.csv', encoding='utf-8-sig').read())
