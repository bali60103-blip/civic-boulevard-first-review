#!/bin/zsh
# 簡報 AI：先跑 04_slides.py（輸出 簡報/_ai_layers/），再由 Illustrator 執行 05_assemble_ai.jsx
cd "$(dirname "$0")/.."
python3 - "$PWD/簡報" <<'PY'
import json, sys
d = sys.argv[1]
order = json.load(open(d + '/_ai_layers/order.json'))['order']
names = [f'{i + 1:02d} ' + ('封面' if o == 'cover' else o) for i, o in enumerate(order)]
json.dump({'w': 1920, 'h': 1080, 'pages': len(order), 'names': names,
           'layers': [['底色', d + '/_ai_layers/00_底色.pdf'], ['圖', d + '/_ai_layers/01_圖.pdf'], ['圖說與頁碼', d + '/_ai_layers/02_文字.pdf']],
           'out': d + '/事件痕跡場域_簡報.ai', 'log': d + '/_ai_layers/ai_log.txt'},
          open('scripts/ai_job_slides.json', 'w'), ensure_ascii=False)
PY
osascript -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$PWD/scripts/05_assemble_ai.jsx\")"
cat "簡報/_ai_layers/ai_log.txt"
