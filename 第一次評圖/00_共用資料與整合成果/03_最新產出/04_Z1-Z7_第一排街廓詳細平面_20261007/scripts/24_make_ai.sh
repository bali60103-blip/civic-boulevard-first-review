#!/bin/zsh
# 產生分層 AI：先跑 20（輸出 _ai_layers/），再由 Illustrator 執行 24_assemble_ai.jsx
Z=${1:-Z1}
cd "$(dirname "$0")/.."
OUT="主題圖_南北通行因素與特性建築"
L="$OUT/_ai_layers/$Z"
STEM=$(ls "$OUT" | grep "^${Z}_.*_A1_1-2500.pdf$" | sed 's/.pdf$//')
python3 - "$L" "$PWD/$OUT/${STEM}.ai" "$PWD/$L/ai_log.txt" <<'PY'
import json, sys
lay = json.load(open(sys.argv[1] + '/layers.json'))
json.dump({'w_mm': 841, 'h_mm': 594, 'layers': lay, 'out': sys.argv[2], 'log': sys.argv[3]},
          open('scripts/ai_job.json', 'w'), ensure_ascii=False)
PY
osascript -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$PWD/scripts/24_assemble_ai.jsx\")"
cat "$L/ai_log.txt"
