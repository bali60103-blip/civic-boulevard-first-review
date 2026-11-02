# QGIS 匯出（二）：以 QGIS 內建 Python（PyQGIS）將 21 輸出之圖層寫入 GeoPackage，套用圖面樣式與標註，存成 QGIS 專案（.qgz）
#   執行（macOS，QGIS 4.2.3）：
#   Q=/Applications/QGIS-final-4_2_3.app/Contents
#   PYTHONNOUSERSITE=1 PYTHONHOME=$Q/Resources PYTHONPATH=$Q/Resources/python3.12:$Q/Resources/python3.12/lib-dynload:$Q/Resources/python3.12/site-packages \
#     QT_QPA_PLATFORM=offscreen $Q/MacOS/python3.12 -s scripts/22_qgis_project.py Z1
import sys, json
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsProject, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransformContext, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsRuleBasedRenderer, QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling,
                       QgsLinePatternFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer, QgsUnitTypes, QgsReferencedRectangle, QgsRectangle,
                       QgsField, QgsFeature, QgsLayerTreeGroup, QgsExpressionContextUtils, Qgis)
from qgis.PyQt.QtGui import QColor, QFont, QPainter
from qgis.PyQt.QtCore import QVariant, Qt

ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
H = Path(__file__).resolve().parents[1]
OUT = H / f'QGIS_{ZONE}_南北通行因素與特性建築'; LD = OUT / '_layers'
GPKG = OUT / f'{ZONE}_南北通行因素與特性建築_EPSG3826.gpkg'
QGZ = OUT / f'{ZONE}_南北通行因素與特性建築.qgz'
RED, MAG, GRAY, BLK, BLUE = '#DF9134', '#8E1B3E', '#C4C4C4', '#141414', '#1A9BD7'
FONT = 'Hiragino Sans GB'

QgsApplication.setPrefixPath('/Applications/QGIS-final-4_2_3.app/Contents/MacOS', True)
app = QgsApplication([], False); app.initQgis()
crs = QgsCoordinateReferenceSystem('EPSG:3826')
if GPKG.exists(): GPKG.unlink()

# ---------- 1. 寫入 GeoPackage ----------
names = sorted(p.stem for p in LD.glob('*.geojson'))
for i, nm in enumerate(names):
    src = QgsVectorLayer(str(LD / f'{nm}.geojson'), nm, 'ogr')
    o = QgsVectorFileWriter.SaveVectorOptions()
    o.driverName = 'GPKG'; o.layerName = nm; o.fileEncoding = 'UTF-8'
    o.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile if i == 0 else QgsVectorFileWriter.CreateOrOverwriteLayer
    err = QgsVectorFileWriter.writeAsVectorFormatV3(src, str(GPKG), QgsCoordinateTransformContext(), o)
    if err[0] != QgsVectorFileWriter.NoError: print('write error', nm, err)
# 參數表（無幾何）
pt = QgsVectorLayer('None', '90_參數', 'memory')
pr = pt.dataProvider()
pr.addAttributes([QgsField(f, QVariant.String) for f in ('項目', '數值', '單位', '說明', '來源')]); pt.updateFields()
for r in json.load(open(LD / 'params.json')):
    f = QgsFeature(pt.fields()); [f.setAttribute(k, r[k]) for k in ('項目', '數值', '單位', '說明', '來源')]; pr.addFeature(f)
o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = 'GPKG'; o.layerName = '90_參數'
o.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
QgsVectorFileWriter.writeAsVectorFormatV3(pt, str(GPKG), QgsCoordinateTransformContext(), o)

# ---------- 2. 樣式 ----------
def fill(color, outline='no', ow=0.0, alpha=1.0, ostyle='solid'):
    s = QgsFillSymbol.createSimple({'color': color, 'outline_color': outline if outline != 'no' else color,
                                     'outline_style': 'no' if outline == 'no' else ostyle, 'outline_width': str(ow), 'outline_width_unit': 'MM'})
    s.setOpacity(alpha); return s
def line(color, w, style='solid', alpha=1.0, dash=None, cap='flat'):
    s = QgsLineSymbol.createSimple({'line_color': color, 'line_width': str(w), 'line_width_unit': 'MM', 'line_style': style,
                                     'capstyle': cap})
    if dash:
        sl = s.symbolLayer(0); sl.setUseCustomDashPattern(True); sl.setCustomDashVector(dash); sl.setCustomDashPatternUnit(QgsUnitTypes.RenderMillimeters)
    s.setOpacity(alpha); return s
def marker(shape_, color, size, outline='#ffffff', ow=0.15):
    return QgsMarkerSymbol.createSimple({'name': shape_, 'color': color, 'size': str(size), 'size_unit': 'MM',
                                          'outline_color': outline, 'outline_width': str(ow)})
def hatch(color, spacing=1.2, w=0.12, outline=None):
    # 斜線填充＋外框（各 symbol layer 直接建立，不從暫存 symbol 複製）
    lp = QgsLinePatternFillSymbolLayer(); lp.setLineAngle(45); lp.setDistance(spacing); lp.setDistanceUnit(QgsUnitTypes.RenderMillimeters)
    lp.setColor(QColor(color)); lp.setLineWidth(w)
    layers = [lp]
    if outline:
        ol = QgsSimpleFillSymbolLayer(); ol.setBrushStyle(Qt.BrushStyle.NoBrush); ol.setStrokeColor(QColor(outline)); ol.setStrokeWidth(0.15)
        layers.append(ol)
    return QgsFillSymbol(layers)
def label(layer, expr, color, size=7.0, bold=False, placement=None, buffer=True, is_expr=True, dist=1.0):
    t = QgsTextFormat(); f = QFont(FONT); f.setBold(bold); t.setFont(f); t.setSize(size); t.setSizeUnit(QgsUnitTypes.RenderPoints)
    t.setColor(QColor(color))
    if buffer:
        b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.7); b.setColor(QColor('white')); t.setBuffer(b)
    s = QgsPalLayerSettings(); s.fieldName = expr; s.isExpression = is_expr; s.setFormat(t); s.dist = dist
    if placement is not None: s.placement = placement
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s)); layer.setLabelsEnabled(True)

STYLE = {
 '00_單元範圍': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill('#ffffff', 'no', 0, 0.0))),
 '01_範圍外淡化遮罩': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill('#ffffff', 'no', 0, 0.7))),
 '02_單元界線': lambda L: L.setRenderer(QgsSingleSymbolRenderer(line(BLUE, 0.35, dash=[2.1, 1.05]))),
 '18_地面_可通過路口_路徑較深': lambda L: (L.setRenderer(QgsSingleSymbolRenderer(fill('#EAEAEA'))),
                     L.setBlendMode(QPainter.CompositionMode.CompositionMode_Multiply)),   # 疊於 03_路徑 上＝#D0D0D0（2026-10-14）
 '03_路徑': lambda L: (L.setRenderer(QgsSingleSymbolRenderer(fill('#E3E3E3'))),
                     L.setBlendMode(QPainter.CompositionMode.CompositionMode_Multiply)),   # 色彩增值：地下層透出
 '04_建物': lambda L: L.setRenderer(QgsRuleBasedRenderer(_bld_rules()) if L.fields().indexOf('級') >= 0 else QgsSingleSymbolRenderer(fill(BLK))),   # 2026-10-15 依樓高 5 級灰
 '16_+1_市民高架匝道_高架段': lambda L: L.setRenderer(QgsSingleSymbolRenderer(hatch('#666666', 0.7, 0.1, outline='#666666'))),   # 白底斜線（同 20）
 '17_地面_市民高架匝道_落地段': lambda L: L.setRenderer(QgsSingleSymbolRenderer(xhatch('#333333', 0.7, 0.1, outline='#333333'))),
 '05_市民高架中心線': lambda L: L.setRenderer(QgsSingleSymbolRenderer(line('#9a9a9a', 0.16, dash=[2.1, 0.5, 0.5, 0.5]))),
 '10_建國高架中心線': lambda L: L.setRenderer(QgsSingleSymbolRenderer(line('#9a9a9a', 0.16, dash=[2.1, 0.5, 0.5, 0.5]))),   # Z6 起
 '11_B2_台北地下街_機捷月台': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(RED))),
 '12_B1_北門站_車站地下通廊_機捷站體': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(RED))),
 '13_地面_捷運地下街出入口': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(RED))),
 '14_+1_人行天橋': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(RED))),
 '30_特性建築剪影': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(MAG))),
 '06_路徑碎塊判讀': lambda L: L.setRenderer(QgsRuleBasedRenderer(_isl_rules())),
 '31_特性基地範圍_不上圖': lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill('rgba(142,27,62,20)', MAG, 0.38, 1.0, 'dash'))),
}
BLD_GRAYS = ['#A4A4A4', '#7E7E7E', '#585858', '#353535', '#141414']; FLOOR_LABELS = ['0–5 層', '6–11 層', '12–19 層', '20–29 層', '30 層以上']   # 同 20
def _bld_rules():
    root = QgsRuleBasedRenderer.Rule(None)
    for k in range(4, -1, -1): root.appendChild(QgsRuleBasedRenderer.Rule(fill(BLD_GRAYS[k]), 0, 0, f'"級" = {k}', '建物 ' + FLOOR_LABELS[k]))
    return root
def xhatch(color, spacing=1.2, w=0.12, outline=None):
    # 交叉斜線（45°＋135°）＋白底＋外框
    bg = QgsSimpleFillSymbolLayer(); bg.setColor(QColor('white')); bg.setStrokeStyle(Qt.PenStyle.NoPen)
    layers = [bg]
    for ang in (45, 135):
        lp = QgsLinePatternFillSymbolLayer(); lp.setLineAngle(ang); lp.setDistance(spacing); lp.setDistanceUnit(QgsUnitTypes.RenderMillimeters)
        lp.setColor(QColor(color)); lp.setLineWidth(w); layers.append(lp)
    if outline:
        ol = QgsSimpleFillSymbolLayer(); ol.setBrushStyle(Qt.BrushStyle.NoBrush); ol.setStrokeColor(QColor(outline)); ol.setStrokeWidth(0.15); layers.append(ol)
    return QgsFillSymbol(layers)
def _isl_rules():
    root = QgsRuleBasedRenderer.Rule(None)
    root.appendChild(QgsRuleBasedRenderer.Rule(fill('rgba(0,170,255,90)', '#0077cc', 0.2), 0, 0, '"decision" = \'fill\'', '補齊（非分隔島）'))
    root.appendChild(QgsRuleBasedRenderer.Rule(fill('rgba(0,0,0,0)', '#cc00cc', 0.3), 0, 0, '"decision" = \'keep\'', '保留（分隔島／綠地）'))
    return root
LABELS = {'06_路徑碎塊判讀': ('"id"', '#0077cc', 5.0, False)}
HIDDEN = {'31_特性基地範圍_不上圖', '00_單元範圍', '06_路徑碎塊判讀', '13_地面_捷運地下街出入口'}
GROUPS = [('單元範圍與界線', ['01_範圍外淡化遮罩', '02_單元界線', '00_單元範圍']),     # 由上而下＝高程由高至低
          ('+2 高架', ['05_市民高架中心線']),
          ('+1 天橋', ['14_+1_人行天橋']),
          ('±0 地面', ['30_特性建築剪影', '31_特性基地範圍_不上圖', '04_建物', '13_地面_捷運地下街出入口', '03_路徑']),
          ('檢核', ['06_路徑碎塊判讀']),
          ('B1 地下一層', ['12_B1_北門站_車站地下通廊_機捷站體']),
          ('B2 地下二層', ['11_B2_台北地下街_機捷月台']),
          ('參數', ['90_參數'])]

# 圖層群組、預設關閉、單色填色：優先讀 21 寫出之 meta.json（各單元圖層不同），無則用上方預設（Z1）
meta = json.load(open(LD / 'meta.json'))
if 'groups' in meta: GROUPS = [(g, ns) for g, ns in meta['groups']]
if 'hidden' in meta: HIDDEN = set(meta['hidden'])
for nm_, c_ in meta.get('fills', {}).items():
    if nm_ not in STYLE: STYLE[nm_] = (lambda c: (lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill(c)))))(c_)
def _mk_style(cfg):
    # 點狀記號（Z5 起）：hollow＝空心圓、size_expr＝資料定義尺寸（mm）；by＝依欄位分記號（規則式）
    from qgis.core import QgsProperty, QgsSymbolLayer
    def one(shape_, color, size, hollow=False):
        m = marker(shape_, color, size, outline=color if hollow else '#ffffff', ow=0.3 if hollow else 0.15)
        if hollow: m.symbolLayer(0).setFillColor(QColor(0, 0, 0, 0))
        return m
    def apply(L):
        if 'by' in cfg:
            root = QgsRuleBasedRenderer.Rule(None)
            for val, shp in cfg['shapes'].items():
                root.appendChild(QgsRuleBasedRenderer.Rule(one(shp, cfg['color'], cfg['size']), 0, 0, f'"{cfg["by"]}" = \'{val}\'', val))
            L.setRenderer(QgsRuleBasedRenderer(root))
        else:
            m = one(cfg['shape'], cfg['color'], 3.0, cfg.get('hollow', False))
            if cfg.get('size_expr'): m.setDataDefinedSize(QgsProperty.fromExpression(cfg['size_expr']))
            L.setRenderer(QgsSingleSymbolRenderer(m))
    return apply
for nm_, cfg_ in meta.get('markers', {}).items():
    STYLE[nm_] = _mk_style(cfg_)
for nm_, cfg_ in meta.get('hatches', {}).items():   # 斜線填充＋外框（41 可通過之路口標記，2026-10-14）
    STYLE[nm_] = (lambda c: (lambda L: L.setRenderer(QgsSingleSymbolRenderer(hatch(c['color'], c.get('spacing', 1.2), c.get('width', .12), c['color'])))))(cfg_)
STYLE.setdefault('07_基地內現有建物_拆除改建', lambda L: L.setRenderer(QgsSingleSymbolRenderer(fill('#BDBDBD', '#888888', 0.15, 0.6))))

# ---------- 3. 專案 ----------
proj = QgsProject.instance(); proj.clear()
proj.setCrs(crs); proj.setTitle(f'{ZONE} 影響南北通行之因素與特性建築')
proj.writeEntryBool('Paths', '/Absolute', False)   # 相對路徑：專案與 gpkg 一起搬移即可開啟
tree = proj.layerTreeRoot()
for gname, lnames in GROUPS:
    lnames = [nm for nm in lnames if nm in names or nm == '90_參數']      # 本單元未輸出之圖層略過
    if not lnames: continue
    grp = tree.addGroup(gname)
    for nm in lnames:
        L = QgsVectorLayer(f'{GPKG}|layername={nm}', nm[3:], 'ogr')
        if not L.isValid(): print('invalid', nm); continue
        if nm in STYLE: STYLE[nm](L)
        if nm in LABELS:
            ex, c, sz, bd = LABELS[nm]; label(L, ex, c, sz, bd)
        try:   # 樣式同存 gpkg（layer_styles），單獨拖入 QGIS 也帶樣式
            L.saveStyleToDatabaseV2(nm, f'{ZONE} 圖面樣式（20_ns_factors_sheet 同表現）', True, '')
        except Exception as e: print('style db', nm, e)
        proj.addMapLayer(L, False); node = grp.addLayer(L)
        if nm in HIDDEN: node.setItemVisibilityChecked(False)
QgsExpressionContextUtils.setProjectVariable(proj, 'zone', ZONE)
b = meta['view']
proj.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(b[0], b[1], b[2], b[3]), crs))
proj.write(str(QGZ))
print('gpkg', GPKG.name, 'layers', len(names) + 1)
print('qgz', QGZ.name)
app.exitQgis()
