"""Stage 12 — assemble the single self-contained HTML deliverable."""
import json, os
head = open("src/viz_head.html").read()
body = open("src/viz_body.html").read()
app  = open("src/viz_app.js").read()
bundle = open("output/bundle.json").read()

out = (head + "\n" + body + "\n"
       + '<script type="application/json" id="bundle">' + bundle + "</script>\n"
       + "<script>\nwindow.__BUNDLE__ = JSON.parse(document.getElementById('bundle').textContent);\n"
       + app + "\n</script>\n")
p = "output/civic_blvd_overlay.html"
open(p, "w").write(out)
print(f"wrote {p}: {os.path.getsize(p)/1e6:.2f} MB")
