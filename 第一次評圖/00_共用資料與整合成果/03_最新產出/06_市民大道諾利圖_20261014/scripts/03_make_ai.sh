#!/bin/zsh
# 諾利圖分層 AI：先跑 02_nolli.py（輸出 _ai_layers/），再由 Illustrator 執行 03_assemble_ai.jsx
cd "$(dirname "$0")/.."
STEM="市民大道_諾利圖_A1_1-8000"
python3 - "$PWD/_ai_layers" "$PWD/${STEM}.ai" "$PWD/_ai_layers/ai_log.txt" <<'PY'
import json, sys
lay = json.load(open(sys.argv[1] + '/layers.json'))
json.dump({'w_mm': 841, 'h_mm': 594, 'layers': lay, 'out': sys.argv[2], 'log': sys.argv[3]},
          open('scripts/ai_job.json', 'w'), ensure_ascii=False)
PY
osascript -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$PWD/scripts/03_assemble_ai.jsx\")"
cat "_ai_layers/ai_log.txt"
