"""[capture-exclude patch] Windows leaves her window out of every screen capture (setContentProtection ->
WDA_EXCLUDEFROMCAPTURE), so screen looks no longer hide her for a moment (no blink). Side effect (user agreed):
OBS, screenshots and screen sharing do not show her either. usage: python patch_capture_exclude.py <app.asar>"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
EDITS = [
    ('	win.setAlwaysOnTop(true, "floating");\n	win.setVisibleOnAllWorkspaces(',
     '	win.setAlwaysOnTop(true, "floating");\n	win.setContentProtection(true); // [capture-exclude patch] not in screen captures (no hide/blink needed)\n	win.setVisibleOnAllWorkspaces('),
    ('	win.setOpacity(0);\n	try {\n		const sources = await electron.desktopCapturer.getSources({',
     '	// [capture-exclude patch] no setOpacity(0): the window is excluded from captures\n	try {\n		const sources = await electron.desktopCapturer.getSources({'),
]
bak = asar.with_name("app.asar.bak-capexcl")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[capture-exclude patch]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:60]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
