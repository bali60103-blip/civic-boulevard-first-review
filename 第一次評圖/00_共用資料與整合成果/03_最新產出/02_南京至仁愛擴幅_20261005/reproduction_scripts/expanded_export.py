"""Expanded overview delivery. Never modifies the source v2 package."""
import json,sys,shutil,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'output/a00_expanded_20261005';S=R/'output/a01_a10_unified_v2_20261004'
read=lambda p:json.loads(p.read_text())
q=read(O/'qa.json');bb=q['bounds'];cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2
def xy(x,y):return 420.5+(x-cx)/10,365+(y-cy)/10
def polys(g):
 if g['type']=='Polygon':yield g['coordinates']
 elif g['type']=='MultiPolygon':yield from g['coordinates']
def geos(n):return [f['geometry'] for f in read(O/n)['features']]
stem='A01_A10_Nanjing_Renai_20261005'
if sys.argv[1] in ['review','cad']:
 from shapely.geometry import shape,box,mapping
 from shapely.ops import unary_union,transform
 def parts(g,kind):
  if g.geom_type==kind:yield g
  elif hasattr(g,'geoms'):
   for v in g.geoms:yield from parts(v,kind)
 road=unary_union([shape(g) for g in geos('road_surfaces_TWD97.geojson')]);build=unary_union([shape(g) for g in geos('building_outlines_TWD97.geojson')])
 if sys.argv[1]=='review':
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from PIL import Image
  imgs=read(O/'imagery_manifest.json')['images'];marks=read(O/'building_conflicts.json')
  for group in range(4):
   fig,axes=plt.subplots(2,3,figsize=(18,12),dpi=120)
   for ax,m in zip(axes.flat,marks[group*6:group*6+6]):
    g=shape(m['geometry']);x,y=g.centroid.coords[0];b=box(x-45,y-40,x+45,y+40)
    for im in imgs:
     v=im['bbox']
     if b.intersects(box(*v)):ax.imshow(Image.open(O/'imagery'/im['file']),extent=[v[0],v[2],v[1],v[3]])
    for geo,col in [(road,'cyan'),(build,'#ffdf40')]:
     for p in parts(geo.intersection(b),'Polygon'):
      for ring in [p.exterior]+list(p.interiors):ax.plot(*ring.xy,color=col,lw=1)
    for p in parts(g,'Polygon'):ax.plot(*p.exterior.xy,color='#ff3080',lw=1,ls='--')
    ax.set_xlim(x-45,x+45);ax.set_ylim(y-40,y+40);ax.set_title(m['id']+' / cut '+str(round(m['ratio']*100))+'%');ax.axis('off')
   fig.tight_layout();fig.savefig(O/f'CONFLICTS_{group+1}.png');plt.close(fig)
  for view in read(O/'review_views.json'):
   b=view['bounds'];clip=box(*b);fig,ax=plt.subplots(figsize=(18,8),dpi=120)
   for im in imgs:
    v=im['bbox']
    if clip.intersects(box(*v)):ax.imshow(Image.open(O/'imagery'/im['file']),extent=[v[0],v[2],v[1],v[3]])
   for geo,col in [(road,'cyan'),(build,'#ffdf40')]:
    for p in parts(geo.intersection(clip),'Polygon'):
     for ring in [p.exterior]+list(p.interiors):ax.plot(*ring.xy,color=col,lw=.35)
   for s in q['sheets']:
    for p in parts(box(*s['bounds']).intersection(clip),'Polygon'):ax.plot(*p.exterior.xy,color='#ff3090',lw=1)
   ax.set_xlim(b[0],b[2]);ax.set_ylim(b[1],b[3]);ax.axis('off');ax.set_title(view['id']+' | cyan road / yellow building / pink existing sheet extents');fig.tight_layout();fig.savefig(O/(view['id']+'.png'));plt.close(fig)
  sys.exit()
 # Local translation makes tiny shared-edge subtraction numerically stable.
 local=lambda g:transform(lambda x,y:(x-cx,y-cy),g)
 back=lambda g:transform(lambda x,y:(x+cx,y+cy),g)
 edges=back(local(build).boundary.difference(local(road).boundary.buffer(0.00001)))
 (O/'building_display_edges.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':mapping(edges)}]}))
 import ezdxf
 d=ezdxf.readfile(S/'A01_A10_unified_v2.dxf');ms=d.modelspace()
 for e in list(ms):
  if e.dxf.layer in ['ROAD_ENVELOPE_EST','BUILDING_OUTLINE','BUILDING_CLOSED_REF']:ms.delete_entity(e)
 counts={}
 for g,layer in [(road,'ROAD_ENVELOPE_EST'),(build,'BUILDING_CLOSED_REF')]:
  n=0
  for p in parts(g,'Polygon'):
   for ring in [p.exterior]+list(p.interiors):
    assert ring.is_simple and ring.is_ring
    ms.add_lwpolyline(list(ring.coords)[:-1],close=True,dxfattribs={'layer':layer});n+=1
  counts[layer]=n
 for l in parts(edges,'LineString'):ms.add_lwpolyline(l.coords,dxfattribs={'layer':'BUILDING_OUTLINE'})
 if 'CONTEXT_REVIEW' not in d.layers:d.layers.new('CONTEXT_REVIEW',dxfattribs={'color':6})
 for m in read(O/'building_conflicts.json'):
  p=shape(m['geometry']).centroid;ms.add_circle((p.x,p.y),12,dxfattribs={'layer':'CONTEXT_REVIEW'});ms.add_text(m['id'],dxfattribs={'insert':(p.x+14,p.y),'height':3,'layer':'CONTEXT_REVIEW'})
 d.layers.get('CONTEXT_REVIEW').off()
 d.layouts.delete('A00_INDEX');lay=d.layouts.new('A00_INDEX');lay.page_setup(size=(841,594),margins=(0,0,0,0),units='mm',scale=(1,1),name='ISO_A1',device='')
 for v in lay.query('VIEWPORT'):v.dxf.layer='0'
 vp=lay.add_viewport(center=(420.5,365),size=(760,250),view_center_point=(cx,cy),view_height=2500,dxfattribs={'layer':'VIEWPORT_FRAME','flags':16384})
 vp.freeze('REVIEW');vp.freeze('CONTEXT_REVIEW')
 for s in q['sheets']:vp.freeze('ORTHO_'+s['id'])
 def text(x,y,t,h=3):lay.add_text(t,dxfattribs={'insert':(x,y),'height':h,'layer':'PAPER_ANNOTATION'})
 def rect(x,y,w,h,col=7):lay.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,dxfattribs={'layer':'PAPER_ANNOTATION','color':col})
 rect(10,10,821,574);text(40,550,'CIVIC | NANJING - RENAI EXPANDED OVERVIEW',7);text(40,535,'A1 / INDEX 1:10000 / TEN DETAIL SHEETS 1:1000 / 2026-10-05',4)
 for i,s in enumerate(q['sheets']):
  x,y=xy(*s['bounds'][:2]);rect(x,y,76,51,6);text(x+32,y+53,s['id'],5)
  text(40+(i//5)*400,215-(i%5)*17,s['id']+' | 1:1000 | 760 x 510 m | EXISTING EXTENT',3.5)
 text(40,100,'Black building fill ONLY within the original ten sheet footprints; context is outline only.',3.5)
 text(40,86,'2026-09-08 local OSM + auxiliary widths + 2025 aerial. Estimated, not measured.',3.5)
 text(40,72,'24 major building cuts marked in separate review images; existing 211 pending IDs retained.',3.5)
 text(40,58,'North: Nanjing E. / W. Rd.   South: Renai Rd. (no invented eastward extension).',3.5)
 for label,x,y in [('NANJING W. RD.',301650,2771850),('NANJING E. RD.',304700,2771775),('RENAI RD.',304800,2770035)]:text(*xy(x,y),label,3)
 for i in range(4):rect(655+i*25,36,25,3)
 for i in [0,2,4]:text(655+i*25,30,str(i*250),2.5)
 text(760,30,'m');text(780,550,'GRID N',2.5);lay.add_line((795,532),(795,550),dxfattribs={'layer':'PAPER_ANNOTATION'})
 d.layouts.set_active_layout('A00_INDEX');d.saveas(O/(stem+'.dxf'));shutil.copytree(S/'images',O/'images',dirs_exist_ok=True)
 (O/'convert.scr').write_text('FILEDIA\n0\n_.DXFIN\n"'+str(O/(stem+'.dxf'))+'"\n_.SAVEAS\n2018\n"'+str(O/(stem+'.dwg'))+'"\n_.QUIT\n')
 shutil.copyfile(S/'audit.scr',O/'audit.scr')
 q.update({'cad_stem':stem,'closed_ring_counts':counts,'dxf_audit_errors':len(d.audit().errors),'visible_shared_edge_m':edges.intersection(road.boundary).length,'road_valid':road.is_valid,'building_valid':build.is_valid})
 (O/'qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2));print(q)
elif sys.argv[1]=='pdf':
 from reportlab.pdfgen import canvas
 from reportlab.lib.units import mm
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.ttfonts import TTFont
 from pypdf import PdfReader,PdfWriter
 pdfmetrics.registerFont(TTFont('CJK','/System/Library/Fonts/STHeiti Light.ttc',subfontIndex=0));(O/'pdf').mkdir(exist_ok=True)
 tmp=O/'pdf/index_only.pdf';c=canvas.Canvas(str(tmp),pagesize=(841*mm,594*mm))
 def text(x,y,t,h=3):c.setFillColorRGB(.1,.13,.15);c.setFont('CJK',h*mm);c.drawString(x*mm,y*mm,t)
 def rect(x,y,w,h):c.rect(x*mm,y*mm,w*mm,h*mm,stroke=1,fill=0)
 def plot(g,fill=False):
  for rings in polys(g):
   p=c.beginPath()
   for ring in rings:
    a=[xy(*v[:2]) for v in ring];p.moveTo(a[0][0]*mm,a[0][1]*mm)
    for x,y in a[1:]:p.lineTo(x*mm,y*mm)
    p.close()
   c.drawPath(p,stroke=not fill,fill=fill,fillMode=0)
 c.setLineWidth(.25*mm);rect(10,10,821,574)
 text(40,550,'市民大道｜南京路至仁愛路擴幅索引',7);text(40,535,'A1｜索引 1:10000｜原十幅 1:1000 範圍不變｜2026-10-05',4)
 c.setFillColorRGB(.4,.4,.4)
 for g in geos('building_fill_TWD97.geojson'):plot(g,True)
 c.setStrokeColorRGB(.18,.18,.18);c.setLineWidth(.085*mm)
 for g in geos('building_display_edges.geojson'):
  lines=g['coordinates'] if g['type']=='MultiLineString' else [g['coordinates']]
  for line in lines:
   p=c.beginPath();a=[xy(*v[:2]) for v in line];p.moveTo(a[0][0]*mm,a[0][1]*mm)
   for x,y in a[1:]:p.lineTo(x*mm,y*mm)
   c.drawPath(p)
 c.setStrokeColorRGB(0,.4,.48);c.setLineWidth(.13*mm)
 for g in geos('road_surfaces_TWD97.geojson'):plot(g)
 c.setStrokeColorRGB(.78,.06,.4);c.setLineWidth(.3*mm)
 for i,s in enumerate(q['sheets']):
  x,y=xy(*s['bounds'][:2]);rect(x,y,76,51)
  c.setFillColorRGB(1,1,1);c.rect((x+30)*mm,(y+52)*mm,17*mm,7*mm,stroke=0,fill=1);text(x+32,y+53,s['id'],5)
  text(40+(i//5)*400,215-(i%5)*17,s['id']+'｜1:1000｜760 × 510 m｜沿用原分幅',3.5)
 for label,x,y in [('南京西路',301650,2771850),('南京東路',304700,2771775),('仁愛路',304800,2770035)]:
  x,y=xy(x,y);c.setFillColorRGB(1,1,1);c.rect(x*mm,(y-1)*mm,20*mm,5*mm,stroke=0,fill=1);text(x,y,label,3)
 text(40,100,'僅粉色十張圖框內建物黑色填色、透明度 40%；新增周邊僅畫道路與建物輪廓，不填色。',3.5)
 text(40,86,'第 2-21 頁沿用 v2 原圖不變；東西界不變。南京路西端接南京西路，仁愛路不虛構東延。',3.5)
 text(40,72,'道路依 OSM 為主、路寬檔為輔；青線優先。24 處較大建物裁切另附編號航照預覽，仍待審。',3.5)
 text(40,58,'本地 OSM 2026-09-08 檔＋2025 航照概估，未逐棟實測／逐車道核定／街景查核；非 50 cm 剖切。',3.5)
 c.setStrokeColorRGB(.1,.1,.1)
 for i in range(4):c.setFillColorRGB(*((.1,.1,.1) if i%2==0 else (1,1,1)));c.rect((655+i*25)*mm,36*mm,25*mm,3*mm,stroke=1,fill=1)
 for i in [0,2,4]:text(655+i*25,30,str(i*250),2.5)
 text(760,30,'m');text(780,550,'格網北',2.5);c.line(795*mm,532*mm,795*mm,548*mm);p=c.beginPath();p.moveTo(795*mm,550*mm);p.lineTo(793*mm,545*mm);p.lineTo(797*mm,545*mm);p.close();c.drawPath(p,stroke=1,fill=1)
 text(40,22,'© OpenStreetMap contributors / ODbL｜臺北市 2025 航照供概估核對｜100% 列印勿縮放',2.7);c.save()
 src=S/'pdf/A01_A10_A1_1000_unified_v2.pdf';final=O/'pdf'/(stem+'.pdf');w=PdfWriter();w.append(tmp);w.append(src,pages=(1,21))
 with final.open('wb') as f:w.write(f)
 a=PdfReader(src);b=PdfReader(final);assert len(b.pages)==21
 unchanged=[a.pages[i].get_contents().get_data()==b.pages[i].get_contents().get_data() for i in range(1,21)];assert all(unchanged)
 (O/'pdf_qa.json').write_text(json.dumps({'pages':21,'size_mm':[841,594],'detail_content_streams_unchanged':unchanged,'index_scale':10000,'detail_scale':1000},indent=2));print(final)
