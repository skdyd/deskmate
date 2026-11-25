"""[ontop patch] keep Deskmate above normal windows: Windows sometimes drops the topmost flag (after resizing,
focus changes or another topmost app), so every 2 s re-assert it when it is lost. No moveTop(): that covered the
taskbar's tray overflow, tooltips and dropdown lists. usage: python patch_ontop.py <app.asar>   (re-runnable)"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
A = '	win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });\n'
B = A + '''	// [ontop patch] re-assert always-on-top; Windows can lose it
	setInterval(() => {
		if (!win || win.isDestroyed() || !win.isVisible()) return;
		if (!win.isAlwaysOnTop()) win.setAlwaysOnTop(true, "floating");
	}, 2e3);
'''
inner = "out/main/index.js"
bak = asar.with_name("app.asar.bak-ontop")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"
asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[ontop patch]" in s: sys.exit("already patched")
if s.count(A) != 1: sys.exit("anchor not found")
f.write_bytes(s.replace(A, B).encode("utf-8"))
asar_tool.cmd_replace(asar, inner, f)
print("patched", inner)
