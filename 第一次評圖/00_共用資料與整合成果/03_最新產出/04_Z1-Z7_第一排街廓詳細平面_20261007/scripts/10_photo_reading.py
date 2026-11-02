# 照片判讀紀錄：每張原始照片之定位方式、所在單元、判讀內容與用途 → data/photos/photo_reading.csv
# iPhone：EXIF GPS（水平誤差多為 10–15 m）＋方位角；Sony（ILCE-6400）：無 GPS、相機時鐘未設（2019-01-01），
# 依路牌、門牌、地標與拍攝序號判讀位置（僅到單元／路段）。
import json, csv
from pathlib import Path
H = Path(__file__).resolve().parents[1]
rows = json.load(open(H / 'data/photos/photo_index.json'))

# Sony 序號區間判讀（資料夾／起訖序號、單元、依據、判讀內容、用於）
SONY = [
    ('A/D', 8744, 8788, 'Z4', '「市民大道地下停車場 4號樓梯出入口」標牌（DSC08765，林金段）；南側華山／中央藝文公園綠地',
     '雙柱＋帽梁門形墩；分隔島綠籬、喬木、石雕（DSC08752 分隔島穿越口）；地下停車場樓梯雨遮；候車亭；機車格；停車場入口標誌',
     '橋墩柱型（門形）、分隔島植栽、候車亭與停車場出入口核實'),
    ('B/D', 8441, 8457, 'Z5', '「商務電腦展售中心」招牌（光華商圈）；前方可見新生高架（DSC08449）',
     '大型矩形單柱；分隔島綠籬；人行道消防栓、機車格', '橋墩柱型（矩形單柱）、分隔島植栽'),
    ('B/D', 8460, 8500, 'Z4–Z5', '新生高架交叉結構（DSC08468、08492 藍色鋼構門架）；「上城若水」看板',
     '葫蘆雕塑（DSC08460）；橋下鋪面廣場與座椅、泰式佛塔壁畫柱（DSC08492–08494）；YouBike（DSC08471、08473）',
     '公共藝術、YouBike 核實；橋下廣場（位置未能精確定位，未補繪）'),
    ('B/D', 8503, 8512, 'Z6–Z7', '「安東街 40」路牌（DSC08508、08510）', '方形單柱；分隔島植栽與景石；遠方彩虹柱（DSC08512）',
     '單元界線核對、分隔島植栽'),
    ('B/D', 8703, 8743, 'Z5', '「市民大道三段5號」門牌（DSC08708）、「八德路二段」路牌（DSC08713）',
     '大型矩形單柱連續排列；機車格（DSC08710、08715）；橋下 YouBike（DSC08706）；新設口袋公園與體健設施（DSC08720–08724）',
     '橋墩柱型（矩形單柱）、YouBike 核實'),
    ('C', 8514, 8568, 'Z6', '彩虹漆圓柱（與 IMG_4675–4680 同段）；橋下通風建物與百葉',
     '圓形單柱彩虹漆；分隔島內通風建物、地下停車場樓梯（DSC08558–08561）；機車格；YouBike（DSC08568）',
     '橋墩柱型（圓形單柱）、通風建物核對（線稿已有）'),
    ('C', 8574, 8700, 'Z7', '淡粉色圓柱；分隔島大型金屬雕塑（DSC08603–08628）；候車亭（DSC08688）',
     '圓形單柱；分隔島綠籬；機車格（DSC08598、08609、08687）；地下停車場出入口（DSC08641「4」號）；東段壁畫柱（DSC08697–08700）',
     '橋墩柱型（圓形單柱）、公共藝術與候車亭核實'),
]
IPH = {  # iPhone 照片中判讀並用於補繪者（其餘 iPhone 照片僅定位，用於效果圖）
    'IMG_4585': '大型單柱（錐形帽梁）、石砌坡道擋牆、國光客運候車棚 → Z2 柱型、候車亭核實',
    'IMG_4586': '同上', 'IMG_4591': '大型單柱、北門側黃色槽化線 → Z2 柱型', 'IMG_4592': '同上',
    'IMG_4589': '地下街出入口 → 捷運／地下街出入口核實',
    'IMG_4594': '雙柱門形墩、綠籬分隔島 → Z3 柱型', 'IMG_4595': '同上', 'IMG_4596': '同上',
    'IMG_4597': '雙柱門形墩、分隔島 → Z4 柱型', 'IMG_4598': '同上', 'IMG_4599': '同上',
    'IMG_4634': '圍籬後舊鐵道（原臺北車站地下化專案引道）→ 舊鐵道引道核實', 'IMG_4635': '同上', 'IMG_4636': '同上', 'IMG_4637': '同上',
    'IMG_4675': '彩虹漆圓形單柱、分隔島通風建物、南側人行道機車格 → Z6 柱型、機車停車列',
    'IMG_4676': '同上（機車停車列定位依據）', 'IMG_4677': 'YouBike → 核實', 'IMG_4678': '彩虹柱、分隔島綠籬', 'IMG_4679': '同上',
    'IMG_4680': '彩虹柱、機車停車列（定位依據）',
}
def sony_key(r):
    parts = r['file'].split('/')
    fold = parts[1] if parts[1] == 'C' else parts[1] + '/' + parts[2]
    try: n = int(r['id'][3:])
    except ValueError: n = -1
    return fold, n
out = []
for r in rows:
    base = {'檔案': r['file'], '相機': r['camera'] or '', '拍攝時間（EXIF）': r['time'] or ''}
    if 'x' in r:
        out.append(base | {'定位方式': f"EXIF GPS（誤差約 {r['gps_err_m']:.0f} m）" if r.get('gps_err_m') else 'EXIF GPS',
                           '單元': r.get('zone', ''), 'E_3826': r['x'], 'N_3826': r['y'], '方位角': r.get('heading', ''),
                           '判讀內容與用途': IPH.get(r['id'], '僅定位（效果圖底圖）')})
        continue
    fold, n = sony_key(r)
    hit = next((s for s in SONY if s[0] == fold and s[1] <= n <= s[2]), None)
    if hit:
        out.append(base | {'定位方式': f'內容判讀：{hit[4]}', '單元': hit[3], 'E_3826': '', 'N_3826': '', '方位角': '',
                           '判讀內容與用途': f'{hit[5]} → {hit[6]}'})
    else:
        out.append(base | {'定位方式': '未定位（夜間照片，同 A／B 區路線）' if fold.endswith(('/n', '/N')) else '未定位',
                           '單元': {'A': 'Z4', 'B': 'Z5–Z6', 'C': 'Z6–Z7'}.get(fold[0], ''), 'E_3826': '', 'N_3826': '', '方位角': '',
                           '判讀內容與用途': '未用於補繪'})
with open(H / 'data/photos/photo_reading.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
import collections
print(len(out), collections.Counter(o['定位方式'].split('：')[0].split('（')[0] for o in out))
print(collections.Counter(o['單元'] for o in out))
