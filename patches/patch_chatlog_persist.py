"""1.0.2 [chatlog-persist] the conversation log window saves its position/size whenever it is moved or resized (not
only on close, which a killed app never reaches), and the log itself is kept in %APPDATA%\deskmate\chatlog.json
(last 300 lines) so it survives restarts; each start adds a "새 실행" separator line.
Needs patch_chatlog.py + patch_chatlog_pos.py. usage: python patch_chatlog_persist.py <app.asar>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
EDITS = [
    ("var chatLog = [];\n", r'''var CHATLOG_FILE = (0, node_path.join)(USER_DATA, "chatlog.json"); // [chatlog-persist]
var chatLog = (() => {
	try {
		return JSON.parse((0, node_fs.readFileSync)(CHATLOG_FILE, "utf8")).slice(-300);
	} catch {
		return [];
	}
})();
chatLog.push({ t: new Date().toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }), who: "── 새 실행 ──", text: "", me: false });
var chatLogSaveT = 0;
var chatLogBoundsT = 0;
function chatLogSave() {
	clearTimeout(chatLogSaveT);
	chatLogSaveT = setTimeout(() => {
		try {
			(0, node_fs.writeFileSync)(CHATLOG_FILE, JSON.stringify(chatLog.slice(-300)));
		} catch (err) {
			console.warn("[chatlog] save:", err.message);
		}
	}, 800);
}
'''),
    ("	chatLogSend(e);\n}", "	chatLogSend(e);\n	chatLogSave(); // [chatlog-persist]\n}"),
    ('		chatLogWin.on("closed", () => {',
     '''		const saveBounds = () => { // [chatlog-persist] remember the spot as soon as it is moved or resized
			clearTimeout(chatLogBoundsT);
			chatLogBoundsT = setTimeout(() => { if (chatLogWin && !chatLogWin.isDestroyed()) settings.set({ chatLogBounds: chatLogWin.getBounds() }); }, 400);
		};
		chatLogWin.on("moved", saveBounds);
		chatLogWin.on("resized", saveBounds);
		chatLogWin.on("closed", () => {'''),
]
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[chatlog-persist]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:50]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
