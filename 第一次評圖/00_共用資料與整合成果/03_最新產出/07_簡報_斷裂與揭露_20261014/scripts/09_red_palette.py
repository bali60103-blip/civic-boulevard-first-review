# 色票（2026-10-15 使用者：「給我一套從酒紅到正紅的色票」）
#   酒紅＝統一色表 #8E1B3E（特性建築／主角第一級）→ 正紅＝#E60012（CMYK 0/100/100/0 之 sRGB 近似），OKLab 等距 7 階。
#   另附 P15 v5 樓高灰階（越高越白）8 級，與 04_slides.py H_CLASSES 一致。
#   輸出 簡報/色票/：酒紅至正紅_色票.ase（Illustrator「色票」面板 → 開啟色票資料庫 → 其他資料庫）、色票.pdf、色票.csv
import math, struct, csv
from pathlib import Path
import fitz

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報/色票"; OUT.mkdir(parents=True, exist_ok=True)
FL, FM = "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"
WINE, RED, N = (0x8E, 0x1B, 0x3E), (0xE6, 0x00, 0x12), 7
H_CLASSES = [(10, "1–3 層（≤10 m）"), (17, "4–5 層"), (23, "6–7 層"), (33, "8–10 層"), (46, "11–14 層"), (63, "15–19 層"), (96, "20–29 層"), (1e9, "30 層以上（>96 m）")]   # 同 04_slides.py


def s2l(c):
    c /= 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def l2s(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055; return max(0, min(255, round(c * 255)))


def oklab(rgb):
    r, g, b = [s2l(v) for v in rgb]
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(L, a, b):
    l, m, s = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return tuple(l2s(v) for v in (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                                  -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def cmyk(rgb):   # 簡易換算（未經色彩管理），印刷以 Illustrator 轉換為準
    r, g, b = [v / 255 for v in rgb]; k = 1 - max(r, g, b)
    return (0, 0, 0, 100) if k >= 1 else tuple(round(100 * v) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k))


A, B = oklab(WINE), oklab(RED)
ramp = [WINE] + [from_oklab(*[A[j] + (B[j] - A[j]) * i / (N - 1) for j in range(3)]) for i in range(1, N - 1)] + [RED]
rows = []
for i, c in enumerate(ramp, 1):
    nm = "R1 酒紅" if i == 1 else f"R{N} 正紅" if i == N else f"R{i}"
    d = round(100 * math.dist(oklab(c), oklab(ramp[i - 2])), 1) if i > 1 else ""
    rows.append((nm, "#%02X%02X%02X" % c, c, cmyk(c), d))

# CSV
with open(OUT / "色票.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(["名稱", "HEX", "R", "G", "B", "C", "M", "Y", "K（簡易換算）", "與前一階 ΔE（OKLab×100）"])
    for nm, hx, c, k, d in rows:
        w.writerow([nm, hx, *c, *k, d])

# ASE（Adobe Swatch Exchange）：一組「酒紅—正紅」，全域 RGB 色票
def ase_name(s):
    b = (s + "\0").encode("utf-16-be"); return struct.pack(">H", len(b) // 2) + b


blocks = []
g = ase_name("酒紅—正紅"); blocks.append(struct.pack(">HI", 0xC001, len(g)) + g)
for nm, hx, c, k, d in rows:
    body = ase_name(f"{nm} {hx}") + b"RGB " + struct.pack(">fffH", *(v / 255 for v in c), 0)
    blocks.append(struct.pack(">HI", 0x0001, len(body)) + body)
blocks.append(struct.pack(">HI", 0xC002, 0))
(OUT / "酒紅至正紅_色票.ase").write_bytes(b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks)) + b"".join(blocks))

# 色票 PDF
W, H = 1200, 560
doc = fitz.open(); pg = doc.new_page(width=W, height=H)
pg.insert_font(fontname="hl", fontfile=FL); pg.insert_font(fontname="hm", fontfile=FM)
pg.insert_text((48, 56), "酒紅 → 正紅｜OKLab 等距 7 階", fontsize=20, fontname="hm")
pg.insert_text((48, 80), "酒紅 #8E1B3E（統一色表：特性建築／主角第一級）→ 正紅 #E60012（CMYK 0/100/100/0）。相鄰 ΔE≈3.1：當漸層用；當分類色請取 R1、R3、R5、R7。", fontsize=10, fontname="hl", color=(.35, .35, .35))
sw = (W - 96) / N
for i, (nm, hx, c, k, d) in enumerate(rows):
    x = 48 + i * sw
    sh = pg.new_shape(); sh.draw_rect(fitz.Rect(x, 100, x + sw - 8, 250)); sh.finish(color=None, fill=tuple(v / 255 for v in c)); sh.commit()
    for j, t in enumerate([nm, hx, "RGB %d %d %d" % c, "CMYK %d %d %d %d" % k, f"ΔE {d}" if d != "" else ""]):
        pg.insert_text((x, 270 + 15 * j), t, fontsize=11 if j == 0 else 9, fontname="hm" if j == 0 else "hl")
pg.insert_text((48, 380), "P15 樓高灰階（臺北三維模型 2017 量體高度；越高越白、越低越黑）", fontsize=14, fontname="hm")
gw = (W - 96) / len(H_CLASSES)
for i, (hmax, nm) in enumerate(H_CLASSES):
    gv = 0.14 + 0.86 * i / (len(H_CLASSES) - 1); x = 48 + i * gw
    sh = pg.new_shape(); sh.draw_rect(fitz.Rect(x, 395, x + gw - 8, 470)); sh.finish(color=(.6, .6, .6), width=.3, fill=(gv, gv, gv)); sh.commit()
    pg.insert_text((x, 488), nm, fontsize=10, fontname="hl")
    pg.insert_text((x, 502), "灰 %d%%（#%02X%02X%02X）" % (round(gv * 100), *(round(gv * 255),) * 3), fontsize=9, fontname="hl", color=(.35, .35, .35))
doc.subset_fonts(); doc.save(OUT / "色票.pdf", garbage=3, deflate=True)
pg.get_pixmap(dpi=110).save(OUT / "色票.png")
for r in rows:
    print(r[0], r[1], "RGB", r[2], "CMYK", r[3], "ΔE", r[4])
