"""把 00_共用資料與整合成果 的最新 GeoJSON 疊成一個 QGIS 專案，並輸出預覽 PNG。
執行：PROJ_DATA=... /Applications/QGIS-final-4_2_3.app/Contents/MacOS/python3.12 build_qgis_project.py
"""
import os
from pathlib import Path

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem,
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol, QgsFillSymbol,
    QgsLineSymbol, QgsMarkerSymbol, QgsMapSettings, QgsMapRendererParallelJob,
    QgsRectangle, QgsReferencedRectangle,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize

ROOT = Path("/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果")
LATEST = ROOT / "03_最新產出"
OUT = LATEST / "05_QGIS整合專案_20261009"
OUT.mkdir(exist_ok=True)

qgs = QgsApplication([], False)
qgs.initQgis()
project = QgsProject.instance()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3826"))
project.setFileName(str(OUT / "南京仁愛_整合.qgz"))  # 先設檔名，圖層路徑才會存成相對路徑

LU = LATEST / "03_南京至仁愛_沿線土地使用分析_20261006/data"
BASE = LATEST / "02_南京至仁愛擴幅_20261005"
CAD = ROOT / "04_其他疊合與排版成果/CAD及官方平面疊合"
UP = CAD / "urban_plan_review/南京仁愛沿線都市計畫範圍_20261006"

# 一樓用途配色（cls 欄位）
LU_COLORS = {
    "RES": ("住宅", "#f2d16b"), "MIX": ("一樓店面（住宅／街屋）", "#f08c3a"),
    "COM": ("商業", "#d7301f"), "OFF": ("辦公", "#b2446b"), "EDU": ("教育", "#4f7fc4"),
    "MED": ("醫療", "#2aa198"), "GOV": ("政府機關", "#7a6fb0"), "HER": ("文化資產", "#8c5a2b"),
    "REL": ("宗教", "#b48ead"), "TRN": ("交通", "#7f7f7f"), "IND": ("工業", "#6b4c9a"),
    "REC": ("休閒", "#5aae61"), "UNK": ("未標示", "#d9d9d9"),
}


def add(group, path, name, geom=None):
    uri = str(path) + (f"|geometrytype={geom}" if geom else "")
    lyr = QgsVectorLayer(uri, name, "ogr")
    if not lyr.isValid():
        print("⚠ 無法載入", path)
        return None
    project.addMapLayer(lyr, False)
    group.addLayer(lyr)
    print(f"✓ {name}: {lyr.featureCount()} 筆")
    return lyr


def fill(lyr, color, outline="#555555", width=0.1, opacity=1.0):
    sym = QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width)})
    sym.setOpacity(opacity)
    lyr.renderer().setSymbol(sym)


def outline_only(lyr, color, width=0.5, style="solid"):
    sym = QgsFillSymbol.createSimple({"style": "no", "outline_color": color,
                                      "outline_width": str(width), "outline_style": style})
    lyr.renderer().setSymbol(sym)


root = project.layerTreeRoot()
g_ref = root.addGroup("官方／都市計畫參照")
g_an = root.addGroup("沿線一樓使用分析")
g_base = root.addGroup("線稿底圖（擴幅 20261005）")

# 參照
if (l := add(g_ref, CAD / "正式地號界線_EPSG3826.geojson", "正式地號界線")):
    outline_only(l, "#e7298a", 0.8)
if (l := add(g_ref, UP / "都更案基地與剪影_U04-U09_EPSG3826.geojson", "都更案基地 U04–U09")):
    outline_only(l, "#c51b7d", 0.5, "dash")
if (l := add(g_ref, UP / "南京仁愛沿線都市計畫範圍_EPSG3826.geojson", "都市計畫範圍")):
    outline_only(l, "#3182bd", 0.4, "dot")
if (l := add(g_ref, CAD / "官方宗地參照_55筆_EPSG3826.geojson", "官方宗地 55 筆")):
    outline_only(l, "#984ea3", 0.25)

# 分析
if (l := add(g_an, LU / "zones_EPSG3826.geojson", "分區 Z1–Z7（界線）", "LineString")):
    l.renderer().setSymbol(QgsLineSymbol.createSimple({"color": "#08519c", "width": "0.6", "line_style": "dash"}))
if (l := add(g_an, LU / "zones_EPSG3826.geojson", "分區 Z1–Z7（範圍）", "Polygon")):
    outline_only(l, "#08519c", 0.4)
if (l := add(g_an, LU / "underbridge_EPSG3826.geojson", "橋下空間")):
    sym = QgsFillSymbol.createSimple({"style": "b_diagonal", "color": "#e377c2", "outline_color": "#e377c2"})
    l.renderer().setSymbol(sym)
if (l := add(g_an, LU / "green_EPSG3826.geojson", "公園綠地")):
    fill(l, "#a6d96a", "#1a9641", 0.2, 0.7)
if (l := add(g_an, LU / "landuse_pieces_EPSG3826.geojson", "建物一樓用途", "Polygon")):
    cats = []
    for code, (label, color) in LU_COLORS.items():
        sym = QgsSymbol.defaultSymbol(l.geometryType())
        sym.setColor(QColor(color))
        sym.symbolLayer(0).setStrokeColor(QColor("#666666"))
        sym.symbolLayer(0).setStrokeWidth(0.05)
        cats.append(QgsRendererCategory(code, sym, label))
    l.setRenderer(QgsCategorizedSymbolRenderer("cls", cats))

# 底圖
if (l := add(g_base, BASE / "ten_sheet_mask.geojson", "十幅範圍")):
    outline_only(l, "#000000", 0.6, "dash")
if (l := add(g_base, BASE / "building_fill_TWD97.geojson", "建物（線稿）")):
    fill(l, "#bdbdbd", "#737373", 0.05)
if (l := add(g_base, BASE / "context_buildings_TWD97.geojson", "周邊建物")):
    fill(l, "#e0e0e0", "#bdbdbd", 0.05)
if (l := add(g_base, BASE / "road_surfaces_TWD97.geojson", "道路面")):
    fill(l, "#ffffff", "#9e9e9e", 0.1)

# 產業 POI 點量大，預設關閉
if (l := add(g_an, LU / "industry_pois_EPSG3826.geojson", "產業 POI（8,258 點）")):
    l.renderer().setSymbol(QgsMarkerSymbol.createSimple({"color": "#252525", "size": "0.8", "outline_style": "no"}))
    root.findLayer(l.id()).setItemVisibilityChecked(False)
# 都市計畫範圍、官方宗地預設關閉，避免和一樓用途搶畫面
for name in ("都市計畫範圍", "官方宗地 55 筆"):
    for lyr in project.mapLayersByName(name):
        root.findLayer(lyr.id()).setItemVisibilityChecked(False)

# 全圖範圍：以分析範圍為準
lu = project.mapLayersByName("建物一樓用途")[0]
extent = QgsRectangle(lu.extent())
extent.scale(1.05)
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))

project.write()
print("已存專案：", project.fileName())

# 預覽 PNG（依圖層樹順序、只畫勾選的圖層）
visible = [n.layer() for n in root.findLayers() if n.isVisible()]
ms = QgsMapSettings()
ms.setLayers(visible)
ms.setDestinationCrs(project.crs())
ms.setBackgroundColor(QColor("white"))
w = 4000
h = int(w * extent.height() / extent.width())
ms.setOutputSize(QSize(w, h))
ms.setExtent(extent)
job = QgsMapRendererParallelJob(ms)
job.start()
job.waitForFinished()
png = OUT / "整合預覽.png"
job.renderedImage().save(str(png))
print("已輸出預覽：", png, f"{w}x{h}")

qgs.exitQgis()
