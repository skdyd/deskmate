"""1.0.1: remove the periodic moveTop() from the on-top patch (it put her above the taskbar tray overflow, tooltips
and dropdown lists); only re-assert always-on-top when Windows dropped it. usage: python patch_ontop_nomove.py <asar>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
A = "		if (!win.isFocused()) win.moveTop(); // not while she has focus: it would cover her own dropdown lists\n"
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if A not in s: sys.exit("nothing to do")
f.write_bytes(s.replace(A, "").encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("removed moveTop")
