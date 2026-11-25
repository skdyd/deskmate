"""[chatlog-pos] the conversation log window opens where it was last closed (position and size), unless that spot is
no longer on any monitor. Applies to an asar with patch_chatlog.py. usage: python patch_chatlog_pos.py <app.asar>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
EDITS = [
    ('		chatLogWin = new electron.BrowserWindow({ width: 380, height: 520, title:',
     '		chatLogWin = new electron.BrowserWindow({ ...chatLogBounds(), title:'),
    ('		chatLogWin.on("closed", () => {',
     '		chatLogWin.on("close", () => { if (chatLogWin && !chatLogWin.isDestroyed()) settings.set({ chatLogBounds: chatLogWin.getBounds() }); }); // [chatlog-pos]\n		chatLogWin.on("closed", () => {'),
    ('function setChatLog(on) {', '''function chatLogBounds() { // [chatlog-pos] last place, if it is still on a monitor
	const b = settings.get().chatLogBounds;
	if (b && electron.screen.getAllDisplays().some((d) => b.x + 40 >= d.workArea.x && b.y + 20 >= d.workArea.y && b.x + 40 <= d.workArea.x + d.workArea.width && b.y + 20 <= d.workArea.y + d.workArea.height)) return { x: b.x, y: b.y, width: Math.max(240, b.width), height: Math.max(200, b.height) };
	return { width: 380, height: 520 };
}
function setChatLog(on) {'''),
]
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[chatlog-pos]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:60]!r}")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
