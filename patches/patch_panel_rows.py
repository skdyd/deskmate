"""[panel-rows patch] fixed 3-row panel: row 1 status / what she heard (full width), row 2 all dropdowns sharing one
line (they shrink instead of wrapping), row 3 input + buttons. Needs patch_compact_panel.py first.
usage: python patch_panel_rows.py <app.asar>"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
CSS = """
/* [panel-rows patch] */
#statusrow { flex-wrap: wrap; }
#status { flex: 1 0 100%; padding: 0 2px; }
#statusrow select { flex: 1 1 0; min-width: 0; max-width: none; }
"""
_r, header, _b = asar_tool.read(asar)
css = [p for p, _n in asar_tool.walk(header) if re.match(r"out/renderer/assets/index-.*\.css$", p)][0]
bak = asar.with_name("app.asar.bak-rows")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "x.css"; asar_tool.cmd_get(asar, css, f)
s = f.read_bytes().decode("utf-8")
if "[panel-rows patch]" in s: sys.exit("already")
f.write_bytes((s + CSS).encode("utf-8")); asar_tool.cmd_replace(asar, css, f); print("patched")
