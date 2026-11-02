import json,collections,csv,os
from shapely.geometry import shape,Polygon
from shapely.ops import unary_union
SRC='/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果/04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/sources_current/'
E='/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果/03_最新產出/02_南京至仁愛擴幅_20261005/'
mask=shape(json.load(open(E+'ten_sheet_mask.geojson'))['features'][0]['geometry'])
meta={}
for f in ['plan_metadata.json','allplans.json']:
    meta.update({m['projnum']:m for m in json.load(open(SRC+f))})
cat={r['計畫編號'][1:]:r['官方分類代碼'] for r in csv.DictReader(open(SRC+'../沿線歷年計畫索引_待效力核對.csv',encoding='utf-8-sig'))}
G=collections.defaultdict(list);PER={}
for n in [0,500,1000,1500,2000,2500,3000]:
  for f in json.load(open(SRC+f'index_{n}.json'))['features']:
    k=f['attributes']['PROJNUM'];PER[k]=f['attributes']['PERIOD']
    G[k].append(Polygon(f['geometry']['rings'][0],f['geometry']['rings'][1:]).buffer(0))
U={k:unary_union(v) for k,v in G.items()}
def base(k):return k.split('-')[0]
def name(k):return meta.get(k,meta.get(base(k),{})).get('projname','?')
def pub(k):return meta.get(k,meta.get(base(k),{})).get('projpubl','')
def kind(k):return cat.get(k,cat.get(base(k),'?'))
