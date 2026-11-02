exec(open('load.py').read())
import fitz,ezdxf
from shapely.geometry import box,mapping
from shapely.ops import unary_union
OUT='/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果/04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/南京仁愛沿線都市計畫範圍_20261006/'
q=json.load(open(E+'qa.json'));bb=q['bounds'];cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2
VIEW=box(*bb)
D=[('大同','110002','109017',(.95,.55,.20)),('萬華','110001','109016',(.60,.45,.75)),('中正','111021','111013',(.25,.55,.85)),
   ('中山','110025','110018',(.30,.70,.40)),('大安','110013','110012',(.90,.75,.15)),('松山','108012','108008',(.85,.35,.55)),('信義','112014','112007',(.45,.75,.80))]
# site plans: >=民國90, corridor-intersecting, grouped when 主要/細部 share a footprint
ks=[k for k in U if U[k].intersects(mask) and U[k].area<3e6 and kind(k) in ('01','02','03','05','06','?','5')
    and int(PER[k])>=90 and not k.startswith('099039') and not k.startswith('101005') and not ('-' in k and base(k) in U)
    and U[k].intersection(mask).area>=1000]
ks+=['082023','082022']  # 臺北車站特定專用區 base plan
groups=[]
for k in sorted(ks,key=lambda k:(int(PER[k]),k)):
  for g in groups:
    a=U[g[0]];i=a.intersection(U[k]).area
    if i/a.union(U[k]).area>0.9:g.append(k);break
  else:groups.append([k])
items=[]
for g in groups:
  geom=unary_union([U[k] for k in g]);rp=geom.intersection(mask).representative_point()
  dis=[d[0] for d in D if U[d[1]].contains(rp)];dper=min([int(PER[d[1]]) for d in D if d[0] in dis] or [0])
  last=max(int(PER[k]) for k in g)
  items.append(dict(codes=['P'+k for k in g],names=[name(k) for k in g],pub=[pub(k) for k in g],kind=[kind(k) for k in g],
    period=last,district='／'.join(dis),geom=geom,rp=rp,ha=geom.area/1e4,ha_in=geom.intersection(mask).area/1e4,
    rel='晚於該區通檢公告' if last>=dper else '早於該區通檢公告，效力待核'))
items.sort(key=lambda it:it['rp'].x)
for i,it in enumerate(items,1):it['no']=i
CITY=[k for k in U if U[k].intersects(mask) and U[k].area>2e8 and int(PER[k])>=100 and kind(k) not in ('10','12')]
# ---------- PDF ----------
src=fitz.open(E+'pdf/A01_A10_Nanjing_Renai_20261005.pdf');doc=fitz.open();doc.insert_pdf(src,from_page=0,to_page=0);p=doc[0]
import re
for x in p.get_contents():
  b=doc.xref_stream(x);i=b.find(b'.78 .06 .4 RG')
  if i<0:continue
  head,tail=b[:i],b[i:]
  tail=re.sub(rb'n [\d.]+ [\d.]+ 215\.4331 144\.5669 re S\n',b'',tail)          # sheet frames
  tail=re.sub(rb'1 1 1 rg\nn [\d.]+ [\d.]+ 48\.18898 19\.84252 re f\*\n',b'',tail)  # label backgrounds
  tail=re.sub(rb'\.1 \.13 \.15 rg\nBT [^\n]*?\((A\d\d)[^\n]*?ET\n',b'',tail)       # A01..A10 labels and list lines
  doc.update_stream(x,head+tail)
H=p.rect.height;K=72/25.4
def P(x,y):return fitz.Point((420.5+(x-cx)/10)*K,H-(365+(y-cy)/10)*K)
def mm(x,y):return fitz.Point(x*K,H-y*K)
FONT='/System/Library/Fonts/STHeiti Light.ttc'
p.insert_font(fontname='cjk',fontfile=FONT)
def T(x,y,t,h=3,col=(.1,.13,.15)):p.insert_text(mm(x,y),t,fontname='cjk',fontsize=h*K,color=col)
def rings(g):
  for poly in getattr(g,'geoms',[g]):
    if poly.geom_type!='Polygon':continue
    yield [poly.exterior]+list(poly.interiors)
def draw(g,stroke,fill=None,fo=0,w=.3,dash=None):
  s=p.new_shape()
  for rs in rings(g):
    for r in rs:s.draw_polyline([P(*c) for c in r.coords])
  s.finish(color=stroke,fill=fill,fill_opacity=fo,width=w*K,dashes=dash,even_odd=True,closePath=True);s.commit()
# white-out old title + bottom legend text (map area untouched)
for r in [(30,525,500,565),(30,15,830,230)]:
  s=p.new_shape();s.draw_rect(fitz.Rect(mm(r[0],r[3]),mm(r[2],r[1])));s.finish(color=None,fill=(1,1,1));s.commit()
T(40,550,'市民大道｜南京西路至仁愛路沿線都市計畫範圍',7)
T(40,535,'A1｜1:10000｜底圖：A01_A10_Nanjing_Renai_20261005 第1頁線稿｜計畫範圍：臺北市都市計畫歷年計畫索引（EPSG:3826）｜2026-10-06',4)
for nm,k,km,col in D:
  g=U[k].intersection(VIEW)
  if g.is_empty:continue
  draw(g,col,col,.13,.35)
  c=U[k].intersection(mask).representative_point() if U[k].intersects(mask) else g.representative_point()
for nm,k,km,col in D:  # district labels on top
  g=U[k].intersection(VIEW);c=g.representative_point() if nm!='萬華' else g.centroid
  pt=P(c.x,c.y);w=len(nm+'區')*4.2+3
  s=p.new_shape();s.draw_rect(fitz.Rect(pt.x-2,pt.y-5.5*K,pt.x+w*K,pt.y+1.2*K));s.finish(color=col,fill=(1,1,1),width=.4*K,fill_opacity=.9);s.commit()
  p.insert_text(pt,nm+'區',fontname='cjk',fontsize=4*K,color=tuple(v*.6 for v in col))
RED=(.80,.05,.05)
for it in items:
  g=it['geom'].intersection(VIEW)
  draw(g,RED,RED,.10,.45 if it['rel'].startswith('晚') else .3,None if it['rel'].startswith('晚') else '[3 1.5] 0')
for it in items:
  c=it['rp'];pt=P(c.x,c.y);r=2.3*K
  s=p.new_shape();s.draw_circle(pt,r);s.finish(color=RED,fill=(1,1,1),width=.3*K);s.commit()
  t=str(it['no']);fs=2.6*K;p.insert_text(fitz.Point(pt.x-len(t)*fs*.28,pt.y+fs*.35),t,fontname='helv',fontsize=fs,color=RED)
# legend
y=222;T(40,y,'圖例',4.2);y-=8
for nm,k,km,col in D:
  s=p.new_shape();s.draw_rect(fitz.Rect(mm(40,y+3),mm(48,y)));s.finish(color=col,fill=col,fill_opacity=.25,width=.35*K);s.commit()
  T(51,y,f'{nm}區通盤檢討細部計畫範圍  P{k}（主要 P{km}）  {pub(k)[:9]}',2.8);y-=6
s=p.new_shape();s.draw_rect(fitz.Rect(mm(40,y+3),mm(48,y)));s.finish(color=RED,fill=RED,fill_opacity=.12,width=.45*K);s.commit();T(51,y,'個案主要／細部計畫範圍（實線：晚於所在區通檢公告）',2.8);y-=6
s=p.new_shape();s.draw_rect(fitz.Rect(mm(40,y+3),mm(48,y)));s.finish(color=RED,fill=RED,fill_opacity=.12,width=.3*K,dashes='[3 1.5] 0');s.commit();T(51,y,'個案範圍（虛線：早於所在區通檢公告，是否被通檢納入或仍單獨適用待核）',2.8);y-=6
y-=3
T(40,y,'全市性計畫（範圍涵蓋全線，不另繪）：',2.8);y-=5.5
for k in sorted(CITY,key=lambda k:int(PER[k])):T(42,y,f'P{k}  {name(k)[:40]}',2.5);y-=4.6
y-=3
for t in ['範圍取自官方「歷年計畫索引」多邊形，非地籍核對界線；分區通檢範圍彼此邊緣略有重疊屬索引精度。',
          '「推定有效」僅依公告先後判斷，未逐案核對後續變更／廢止；法定使用以最新計畫書圖及地籍為準。',
          '「沿線」＝與原 A01–A10 十幅範圍相交（框線已不繪）。已排除：通檢徵求意見公告、都更地區劃定、禁建、廢巷、容積獎勵個案、與十幅相交 <0.1 ha 者。']:
  T(40,y,t,2.5);y-=4.6
# case table, two columns
x0=300;y=222;T(x0,y,f'沿線個案計畫（{len(items)} 處，由西向東編號）',4.2);y-=7.5
col_w=265;n=0
for it in items:
  xx=x0+(n//((len(items)+1)//2))*col_w;yy=y-(n%((len(items)+1)//2))*12.6;n+=1
  T(xx,yy,f"{it['no']:>2}",3,RED)
  T(xx+7,yy,f"{'／'.join(it['codes'])}｜{it['district']}區｜民國{it['period']}｜沿線 {it['ha_in']:.1f} ha｜{it['rel']}",2.4)
  nm=it['names'][-1];nm=nm if len(nm)<=62 else nm[:61]+'…'
  T(xx+7,yy-4.6,nm,2.4,(.3,.3,.3))
T(40,22,'資料：臺北市政府都市發展局 webgis.udd.gov.taipei 歷年計畫索引（查詢 2026-10-05，PERIOD 最大 115）｜底圖 © OpenStreetMap contributors / ODbL｜100% 列印勿縮放',2.5)
doc.save(OUT+'南京仁愛沿線都市計畫範圍_1-10000_A1.pdf',garbage=3,deflate=True)
p.get_pixmap(dpi=60).save('out.png')
# ---------- GeoJSON / CSV / DXF ----------
feats=[]
for nm,k,km,col in D:
  feats.append(dict(type='Feature',properties=dict(layer='district_review',district=nm,code='P'+k,main_code='P'+km,name=name(k),pub=pub(k)),geometry=mapping(U[k])))
for it in items:
  feats.append(dict(type='Feature',properties=dict(layer='site_plan',no=it['no'],codes='／'.join(it['codes']),name=it['names'][-1],pub='／'.join(it['pub']),period=it['period'],district=it['district'],ha_in_corridor=round(it['ha_in'],2),status=it['rel']),geometry=mapping(it['geom'])))
json.dump(dict(type='FeatureCollection',crs=dict(type='name',properties=dict(name='EPSG:3826')),features=feats),open(OUT+'南京仁愛沿線都市計畫範圍_EPSG3826.geojson','w'),ensure_ascii=False)
with open(OUT+'沿線計畫清單.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['編號','類型','計畫編號','行政區','計畫名稱','公告','沿線面積ha','推定狀態','計畫書'])
  for nm,k,km,col in D:w.writerow(['',  '行政區通檢細部計畫','P'+k+'／P'+km,nm,name(k),pub(k),round(U[k].intersection(mask).area/1e4,2),'現行基礎計畫（推定）',f'https://webgis.udd.gov.taipei/book/P{k}.pdf'])
  for it in items:w.writerow([it['no'],'個案','／'.join(it['codes']),it['district'],'／'.join(dict.fromkeys(it['names'])),'／'.join(it['pub']),round(it['ha_in'],2),it['rel'],' '.join(f'https://webgis.udd.gov.taipei/book/{c}.pdf' for c in it['codes'])])
  for k in CITY:w.writerow(['','全市性','P'+k,'全市',name(k),pub(k),'','涵蓋全線',f'https://webgis.udd.gov.taipei/book/P{k}.pdf'])
dx=ezdxf.new('R2018',setup=True);dx.units=6;msp=dx.modelspace()
def addpoly(g,layer):
  for rs in rings(g):
    for r in rs:msp.add_lwpolyline([c[:2] for c in r.coords],close=True,dxfattribs={'layer':layer})
ACI={'大同':30,'萬華':200,'中正':5,'中山':3,'大安':2,'松山':6,'信義':4}
for nm,k,km,col in D:
  L='UP_DISTRICT_'+k;dx.layers.add(L,color=ACI[nm]);addpoly(U[k],L)
  c=U[k].intersection(mask).representative_point();msp.add_text(f'{nm}區 P{k}',dxfattribs={'layer':L,'height':25,'insert':(c.x,c.y)})
dx.layers.add('UP_SITE_PLAN',color=1);dx.layers.add('UP_SITE_PLAN_OLDER',color=1,linetype='DASHED');dx.layers.add('UP_LABEL',color=1);dx.layers.add('UP_CORRIDOR_MASK',color=6,linetype='DASHED')
for it in items:
  addpoly(it['geom'],'UP_SITE_PLAN' if it['rel'].startswith('晚') else 'UP_SITE_PLAN_OLDER')
  msp.add_text(f"{it['no']} {'/'.join(it['codes'])}",dxfattribs={'layer':'UP_LABEL','height':12,'insert':(it['rp'].x,it['rp'].y)})
dx.saveas(OUT+'南京仁愛沿線都市計畫範圍_EPSG3826.dxf')
for it in items:print(it['no'],it['codes'],it['district'],it['period'],round(it['ha_in'],2),it['rel'][:4],it['names'][-1][:40])
print('CITY',[(k,name(k)[:20]) for k in CITY])
