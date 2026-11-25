"""[compact-panel patch] smaller bottom panel: at most 420 px wide and centred (it used to span the whole window,
880 px when zoomed), tighter padding, smaller input and buttons, the select row may wrap; her floor line moves down
(BOTTOM 100 -> 80) so she stays close to the smaller panel. usage: python patch_compact_panel.py <app.asar>"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
CSS = """
/* [compact-panel patch] */
#panel { left: 50%; right: auto; transform: translateX(-50%); width: min(420px, calc(100% - 16px)); bottom: 6px; padding: 5px 6px; border-radius: 12px; }
#statusrow { flex-wrap: wrap; gap: 4px; margin: 0 2px 4px; }
#status { flex: 1 1 70px; font-size: 10px; }
#chat { gap: 4px; }
#input { padding: 4px 8px; font-size: 12px; border-radius: 8px; }
#chat button { padding: 4px 7px; font-size: 11px; border-radius: 8px; }
"""
_r, header, _b = asar_tool.read(asar)
paths = [p for p, _n in asar_tool.walk(header)]
css = [p for p in paths if re.match(r"out/renderer/assets/index-.*\.css$", p)][0]
l2d = [p for p in paths if re.match(r"out/renderer/assets/live2d-.*\.js$", p)][0]
bak = asar.with_name("app.asar.bak-compact")
if not bak.exists(): shutil.copy2(asar, bak)
tmp = Path(tempfile.mkdtemp())
for inner, fn in ((css, lambda s: s + CSS), (l2d, lambda s: s.replace("var BOTTOM = 100;", "var BOTTOM = 80; // [compact-panel patch]", 1))):
    f = tmp / Path(inner).name; asar_tool.cmd_get(asar, inner, f)
    s = f.read_bytes().decode("utf-8")
    if "[compact-panel patch]" in s: print("already", inner); continue
    n = fn(s)
    if n == s: sys.exit("anchor not found in " + inner)
    f.write_bytes(n.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched", inner)
