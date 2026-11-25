"""One-off: on an asar that already has patch_ontop.py, stop moveTop() while Deskmate is focused (it covered the
native <select> popups). usage: python patch_ontop_fix.py <app.asar>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
A = "		win.moveTop();\n	}, 2e3);"
B = "		if (!win.isFocused()) win.moveTop(); // not while she has focus: it would cover her own dropdown lists\n	}, 2e3);"
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "cover her own dropdown" in s: sys.exit("already fixed")
if s.count(A) != 1: sys.exit("anchor not found")
f.write_bytes(s.replace(A, B).encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("fixed")
