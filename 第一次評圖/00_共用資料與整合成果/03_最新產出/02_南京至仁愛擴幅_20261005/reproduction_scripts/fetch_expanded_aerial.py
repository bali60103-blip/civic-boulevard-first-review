import json,subprocess,hashlib
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image
O=Path(__file__).resolve().parents[2]/'output/a00_expanded_20261005';(O/'imagery').mkdir(exist_ok=True)
url='https://www.historygis.udd.gov.taipei/arcgis/rest/services/Aerial/Ortho_2025/MapServer/export';rows=[]
for col in range(3):
 for row in range(3):
  b=[300935+col*6610/3,2769800+row*2750/3,300935+(col+1)*6610/3,2769800+(row+1)*2750/3];size=[3672,1528];id=f'X{col+1}{row+1}';p=O/'imagery'/f'{id}.jpg'
  args=dict(f='image',bbox=','.join(map(str,b)),bboxSR=3826,imageSR=3826,size=','.join(map(str,size)),format='jpg',layers='show:0',transparent='false',dpi=96)
  if not p.exists():subprocess.run(['curl','-fsS','--connect-timeout','10','--max-time','55',url+'?'+urlencode(args),'-o',str(p)],check=True)
  im=Image.open(p);assert im.size==tuple(size);im.verify()
  rows.append({'id':id,'bbox':b,'file':p.name,'size':size,'source':url,'query':args,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});print(id,flush=True)
(O/'imagery_manifest.json').write_text(json.dumps({'layer':'Ortho_2025','capture_date':'未核實精確拍攝日期','retrieved':'2026-10-05','images':rows},ensure_ascii=False,indent=2))
