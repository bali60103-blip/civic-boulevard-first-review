#!/bin/zsh
# 一鍵重建 QGIS 專案：./scripts/22_run_qgis.sh Z1（需先跑 13、17、19）
Z=${1:-Z1}
cd "$(dirname "$0")/.."
python3 scripts/21_export_qgis_layers.py $Z || exit 1
Q=/Applications/QGIS-final-4_2_3.app/Contents
export PROJ_DATA=$Q/Resources/qgis/proj GDAL_DATA=$Q/Resources/qgis/gdal PYTHONNOUSERSITE=1 PYTHONHOME=$Q/Resources \
  PYTHONPATH=$Q/Resources/python3.12:$Q/Resources/python3.12/lib-dynload:$Q/Resources/python3.12/site-packages QT_QPA_PLATFORM=offscreen
rm -f "QGIS_${Z}_南北通行因素與特性建築/${Z}_南北通行因素與特性建築_EPSG3826.gpkg"
$Q/MacOS/python3.12 -s scripts/22_qgis_project.py $Z
