"""[capture-toggle patch] tray menu checkbox "캡처에서 숨기기": on = window excluded from captures (no blink, not in
OBS/screenshots); off = visible in captures, and her own screen looks hide her briefly like before. Remembered in
settings.json (captureHide, default on). Needs patch_capture_exclude.py first. usage: python patch_capture_toggle.py <asar>"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
EDITS = [
    ('	win.setContentProtection(true); // [capture-exclude patch] not in screen captures (no hide/blink needed)\n',
     '	win.setContentProtection(captureHidden); // [capture-toggle patch] tray checkbox, remembered\n'),
    ('	// [capture-exclude patch] no setOpacity(0): the window is excluded from captures\n',
     '	// [capture-toggle patch] excluded from captures -> no need to hide her; otherwise hide her for the shot\n	if (!captureHidden) win.setOpacity(0);\n'),
    ('''		{
			label: "Start at login",''', '''		{
			label: "캡처에서 숨기기 (OBS·스크린샷에 안 보임)",
			type: "checkbox",
			checked: captureHidden,
			click: (item) => { // [capture-toggle patch]
				captureHidden = item.checked;
				settings.set({ captureHide: captureHidden });
				win?.setContentProtection(captureHidden);
				refreshTray();
			}
		},
		{
			label: "Start at login",'''),
    ('function refreshTray() {', 'var captureHidden = settings.get().captureHide !== false; // [capture-toggle patch]\nfunction refreshTray() {'),
]
bak = asar.with_name("app.asar.bak-captoggle")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[capture-toggle patch]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:60]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
