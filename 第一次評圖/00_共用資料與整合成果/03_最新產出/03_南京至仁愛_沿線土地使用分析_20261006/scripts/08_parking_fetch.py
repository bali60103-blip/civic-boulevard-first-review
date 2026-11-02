# 停車供給：自「北市好停車」（停管處 https://itaipeiparking.pma.gov.taipei/）抓取沿線停車場與路邊汽車格位，統計各設計介入單元
# API：w1/GetParks/{lon}/{lat}/{car|moto}/{類型}；類型 2＝路外停車場（含汽／機車格數），5＝路邊汽車格（每格一多邊形）；每次回傳約半徑 1 km
import json, re, time, csv, collections, http.cookiejar, urllib.request
from pathlib import Path
from shapely.geometry import shape, Point
from shapely import wkt as swkt
from shapely.ops import transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]; D = H / 'data'
BASE = 'https://itaipeiparking.pma.gov.taipei/'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
inv = Transformer.from_crs(3826, 4326, always_xy=True).transform

cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0')]
home = op.open(BASE, timeout=30).read().decode('utf-8', 'ignore')
token = re.search(r'RequestVerificationToken" type="hidden" value="([^"]+)"', home).group(1)
def get(lon, lat, t):
    rq = urllib.request.Request(f'{BASE}w1/GetParks/{lon}/{lat}/car/{t}', headers={'Content-Type': 'application/json', 'X-CSRF-TOKEN': token})
    return json.loads(op.open(rq, timeout=60).read())

axis = shape(json.load(open(D / 'civic_elevated_EPSG3826.json'))['axis'])
samples = [inv(*axis.interpolate(min(t, axis.length)).coords[0]) for t in range(0, int(axis.length) + 400, 400)]
raw = {2: {}, 5: {}}
for lon, lat in samples:
    for t in (2, 5):
        for x in get(round(lon, 6), round(lat, 6), t):
            raw[t].setdefault(f"{x['parkId']}|{x['lon']}|{x['lat']}", x)
        time.sleep(.3)
fetched = time.strftime('%Y-%m-%d %H:%M')
json.dump({'fetched': fetched, 'source': BASE, 'lots': list(raw[2].values()), 'curb': list(raw[5].values())},
          open(D / 'parking_pma_raw.json', 'w'), ensure_ascii=False)

zf = json.load(open(D / 'zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in zf if 'id' in f['properties']]
def zone_of(pt):
    return next((z['id'] for z, g in ZONES if g.contains(pt)), '')
# 路外停車場：入口／代表點落於單元內即計入
lots = []
for x in raw[2].values():
    p = Point(tf(x['lon'], x['lat'])); z = zone_of(p)
    lots.append({'id': x['parkId'], 'name': x['parkName'], 'addr': x['address'], 'E': round(p.x, 1), 'N': round(p.y, 1), 'zone': z,
                 'car': x['carTotalNum'] or 0, 'moto': x['motorTotalNum'] or 0, 'bus': x['busTotalNum'] or 0,
                 'type': x['operationType'] or '', 'civic_ug': '市民大道' in (x['parkName'] or '') and '段停車場' in (x['parkName'] or '')})
# 路邊格：每筆為一格（payex 含「小車」者為汽車格）
curb = []
for x in raw[5].values():
    g = transform(tf, swkt.loads(x['wkt'])) if x.get('wkt') else Point(tf(x['lon'], x['lat']))
    p = g.representative_point()
    curb.append({'name': x['parkName'], 'E': round(p.x, 1), 'N': round(p.y, 1), 'zone': zone_of(p), 'car': '小車' in (x.get('payex') or '')})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'fetched': fetched,
           'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [l['E'], l['N']]}, 'properties': l | {'kind': 'lot'}} for l in lots]
                     + [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [c['E'], c['N']]}, 'properties': c | {'kind': 'curb'}} for c in curb]},
          open(D / 'parking_pma_EPSG3826.geojson', 'w'), ensure_ascii=False)

# 統計：各單元汽車／機車格數、組成、密度、每千平方公尺樓地板（以建物投影×樓層推估，缺樓層以 1 計不採用→改以投影面積）
P = json.load(open(D / 'landuse_pieces_EPSG3826.geojson'))['features']
bld = collections.Counter()
for f in P:
    if f['properties']['zone']: bld[f['properties']['zone']] += f['properties']['area']
rows = []; T = collections.Counter()
for z, g in ZONES:
    zl = [l for l in lots if l['zone'] == z['id']]; zc = [c for c in curb if c['zone'] == z['id']]
    r = {'單元': z['id'], '範圍': f"{z['from']}—{z['to']}", '土地_ha': round(g.area / 1e4, 1),
         '路外停車場_處': len(zl), '路外汽車格': sum(l['car'] for l in zl), '其中市民大道地下停車場汽車格': sum(l['car'] for l in zl if l['civic_ug']),
         '路外機車格': sum(l['moto'] for l in zl), '路邊汽車格': sum(1 for c in zc if c['car']), '公營汽車格': sum(l['car'] for l in zl if l['type'] == '公營停車場')}
    r['汽車格合計'] = r['路外汽車格'] + r['路邊汽車格']
    r['汽車格密度_格每ha'] = round(r['汽車格合計'] / r['土地_ha'], 1)
    r['每千㎡建物投影汽車格'] = round(r['汽車格合計'] / (bld[z['id']] / 1000), 1) if bld[z['id']] else ''
    rows.append(r); T.update({k: v for k, v in r.items() if isinstance(v, int)})
tot_car = sum(r['汽車格合計'] for r in rows); tot_moto = sum(r['路外機車格'] for r in rows)
for r in rows:
    r['占全線汽車格_%'] = round(100 * r['汽車格合計'] / tot_car, 1)
    r['占全線機車格_%'] = round(100 * r['路外機車格'] / tot_moto, 1) if tot_moto else ''
    r['路邊格占汽車格_%'] = round(100 * r['路邊汽車格'] / r['汽車格合計'], 1) if r['汽車格合計'] else ''
with open(D / '統計_停車供給_單元.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('fetched', fetched, 'lots', len(lots), 'curb', len(curb))
for r in rows: print(r)
