"""[fullheight patch] when the window is as tall as the monitor, drop the 92 px reserved for the bubble above her, so
her head can reach the top of the screen; the bubble always sits just above her head (or over it near the top).
Needs patch_upper_body.py applied first. usage: python patch_fullheight.py <app.asar>   (re-runnable)"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
MARK = "[fullheight patch]"
L2D = [(
    "			const availH = app.screen.height - TOP - BOTTOM;\n			const floorY = TOP + availH;\n",
    "			// [fullheight patch] window as tall as the monitor: no bubble room above her, the bubble overlaps instead\n"
    "			const top = app.screen.height >= window.screen.availHeight - 8 ? 8 : TOP;\n"
    "			const availH = app.screen.height - top - BOTTOM;\n			const floorY = top + availH;\n",
)]
IDX = [(
    "	bubble.style.top = upperShow() < 1 && b ?",
    "	bubble.style.top = /* [fullheight patch] always just above her head */ b ?",
)]
MAIN = [(
    "	const bounds = { x: Math.round(b.x + (b.width - w) / 2), y: b.y + b.height - h, width: w, height: h };",
    "	const bounds = { x: Math.round(b.x + (b.width - w) / 2), y: Math.max(wa.y, Math.min(b.y + b.height - h, wa.y + wa.height - h)), width: w, height: h }; // [fullheight patch] stay on the monitor",
)]
_r, header, _b = asar_tool.read(asar)
paths = [p for p, _n in asar_tool.walk(header)]
pick = lambda pat: [p for p in paths if re.match(pat, p)][0]
bak = asar.with_name("app.asar.bak-fullheight")
if not bak.exists():
    shutil.copy2(asar, bak)
tmp = Path(tempfile.mkdtemp())
for inner, edits in (("out/main/index.js", MAIN), (pick(r"out/renderer/assets/live2d-.*\.js$"), L2D), (pick(r"out/renderer/assets/index-.*\.js$"), IDX)):
    f = tmp / Path(inner).name
    asar_tool.cmd_get(asar, inner, f)
    s = f.read_bytes().decode("utf-8")
    if MARK in s:
        print("already patched", inner); continue
    for a, b in edits:
        if s.count(a) != 1:
            raise SystemExit(f"anchor not found once in {inner}: {a[:60]}")
        s = s.replace(a, b)
    f.write_bytes(s.encode("utf-8"))
    asar_tool.cmd_replace(asar, inner, f)
    print("patched", inner)
