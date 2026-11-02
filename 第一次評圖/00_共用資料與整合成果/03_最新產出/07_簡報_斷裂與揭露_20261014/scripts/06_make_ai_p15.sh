#!/bin/zsh
# P15 膜桌面編輯專案：先跑 python3 04_slides.py desktop（寫 ai_job.json 與 ~/Desktop/膜_P15_編輯專案_20261014/layers/），再由 Illustrator 組分層 AI
cd "$(dirname "$0")"
osascript -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$PWD/06_assemble_layers.jsx\")"
