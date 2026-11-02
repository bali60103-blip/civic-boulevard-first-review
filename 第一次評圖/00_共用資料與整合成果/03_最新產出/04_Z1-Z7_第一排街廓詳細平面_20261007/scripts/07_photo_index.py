# 照片索引：讀 ~/Desktop/civic photo 原始照片 EXIF（拍攝時間、GPS、方位角），iPhone 有 GPS 者轉 EPSG:3826 並判定所在單元
import json, glob, os
from pathlib import Path
from PIL import Image, ExifTags
from pyproj import Transformer
from shapely.geometry import Point, shape
H = Path(__file__).resolve().parents[1]
SRC = Path.home() / 'Desktop/civic photo'
tf = Transformer.from_crs(4326, 3826, always_xy=True)
LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006'
ZF = json.load(open(LU / 'data/zones_EPSG3826.geojson'))['features']
ZON = [(f['properties']['id'], shape(f['geometry'])) for f in ZF if 'id' in f['properties']]
def dms(v): return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
rows = []
for f in sorted(glob.glob(str(SRC / 'origin photo*/**/*.[jJ][pP]*[gG]'), recursive=True)):
    im = Image.open(f); ex = im.getexif(); e2 = im._getexif() or {}
    gps = {ExifTags.GPSTAGS.get(k, k): v for k, v in (ex.get_ifd(0x8825) or {}).items()}
    r = {'file': os.path.relpath(f, SRC), 'id': Path(f).stem, 'camera': ex.get(272), 'time': e2.get(36867) or ex.get(306),
         'w': im.size[0], 'h': im.size[1], 'focal35': e2.get(41989)}
    if 'GPSLatitude' in gps:
        lat, lon = dms(gps['GPSLatitude']), dms(gps['GPSLongitude'])
        x, y = tf.transform(lon, lat)
        r |= {'lat': lat, 'lon': lon, 'x': round(x, 1), 'y': round(y, 1), 'heading': round(float(gps.get('GPSImgDirection', 'nan')), 1),
              'gps_err_m': float(gps['GPSHPositioningError']) if 'GPSHPositioningError' in gps else None}
        p = Point(x, y)
        r['zone'] = next((z for z, g in ZON if g.contains(p)), min(ZON, key=lambda zg: zg[1].distance(p))[0] + '?')
    rows.append(r)
json.dump(rows, open(H / 'data/photos/photo_index.json', 'w'), ensure_ascii=False, indent=1)
import collections
print(collections.Counter((os.path.dirname(r['file']), r.get('zone')) for r in rows))
