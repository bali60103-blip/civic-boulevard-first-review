#!/bin/zsh
# 用 QGIS 4.2.3 內建的 Python 執行 PyQGIS 腳本
C=/Applications/QGIS-final-4_2_3.app/Contents
R=$C/Resources/python3.12
export PYTHONPATH=$R:$R/lib-dynload:$R/site-packages
export PROJ_DATA=$C/Resources/qgis/proj
export QGIS_PREFIX_PATH=$C/MacOS
export QT_QPA_PLATFORM=offscreen
exec $C/MacOS/python3.12 "$@"
