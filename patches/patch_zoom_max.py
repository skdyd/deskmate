"""[zoom-max patch] size dots: max zoom 1.3 -> 2.0, and the window gets wider too when zoomed above 1
(wide models are fitted by width, so a taller window alone did not make them bigger). Height stays capped by the monitor.
usage: python patch_zoom_max.py <app.asar>   (re-runnable)"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
MAX = "2"
EDITS = {
    "out/main/index.js": [
        ("const z = Math.min(1.3, Math.max(.6, Number(zoom) || 1));", f"const z = Math.min({MAX}, Math.max(.6, Number(zoom) || 1)); // [zoom-max patch]"),
        ("	const w = WIN_W;\n	const h = Math.min(Math.round(192 + (Math.min(WIN_H, wa.height - 24) - 192) * z), wa.height);",
         "	const w = Math.min(Math.round(WIN_W * Math.max(1, z)), wa.width);\n	const h = Math.min(Math.round(192 + (Math.min(WIN_H, wa.height - 24) - 192) * z), wa.height);"),
    ],
    "IDX": [
        ("let dotsZoom = Math.min(1.3, Math.max(.6,", f"let dotsZoom = Math.min({MAX}, Math.max(.6,"),
        ("	dotsZoom = Math.round(Math.min(1.3, Math.max(.6, z)) * 10) / 10;", f"	dotsZoom = Math.round(Math.min({MAX}, Math.max(.6, z)) * 10) / 10; // [zoom-max patch]"),
    ],
}
_raw, header, _b = asar_tool.read(asar)
paths = [p for p, _n in asar_tool.walk(header)]
idx = [p for p in paths if re.match(r"out/renderer/assets/index-.*\.js$", p)][0]
bak = asar.with_name("app.asar.bak-zoom")
if not bak.exists():
    shutil.copy2(asar, bak)
tmp = Path(tempfile.mkdtemp())
for inner, edits in EDITS.items():
    inner = idx if inner == "IDX" else inner
    f = tmp / Path(inner).name
    asar_tool.cmd_get(asar, inner, f)
    s = f.read_bytes().decode("utf-8")
    if "[zoom-max patch]" in s:
        print("already patched", inner); continue
    for a, b in edits:
        if s.count(a) != 1:
            raise SystemExit(f"anchor not found once in {inner}: {a[:60]}")
        s = s.replace(a, b)
    f.write_bytes(s.encode("utf-8"))
    asar_tool.cmd_replace(asar, inner, f)
    print("patched", inner)
