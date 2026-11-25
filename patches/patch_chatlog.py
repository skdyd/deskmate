"""[chatlog patch] tray checkbox "대화 기록 보기": a small window listing what you said (typed or spoken) and what she
said (with grammar corrections, which are part of her line), newest at the bottom; last 300 lines of this session.
Closing the window unticks it; the choice is remembered (settings.json chatLogOn).
usage: python patch_chatlog.py <app.asar>   (re-runnable)"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"

MODULE = r'''// [chatlog patch] conversation log window
var chatLog = [];
var chatLogWin = null;
var chatLogOn = settings.get().chatLogOn === true;
var CHATLOG_HTML = '<!doctype html><meta charset="utf-8"><title>대화 기록</title><style>' +
	'body{margin:0;background:#17131f;color:#e9e4f5;font:13px/1.45 "Segoe UI","Malgun Gothic",sans-serif}' +
	'#log{padding:8px 10px}.e{margin:0 0 8px}.h{font-size:11px;color:#8d85a3}.me .w{color:#7fb4ff}.her .w{color:#ff8fc8}' +
	'.w{font-weight:600;margin-right:6px}.x{white-space:pre-wrap;word-break:break-word}' +
	'</style><div id="log"></div><script>' +
	'function add(e){var near=innerHeight+scrollY>=document.body.scrollHeight-40;var d=document.createElement("div");d.className="e "+(e.me?"me":"her");' +
	'var h=document.createElement("div");h.className="h";var w=document.createElement("span");w.className="w";w.textContent=e.who;h.appendChild(w);h.appendChild(document.createTextNode(e.t));' +
	'var x=document.createElement("div");x.className="x";x.textContent=e.text;d.appendChild(h);d.appendChild(x);document.getElementById("log").appendChild(d);' +
	'var l=document.getElementById("log");while(l.children.length>300)l.removeChild(l.firstChild);if(near)scrollTo(0,document.body.scrollHeight)}' +
	'</script>';
function chatLogSend(e) {
	if (chatLogWin && !chatLogWin.isDestroyed()) chatLogWin.webContents.executeJavaScript("add(" + JSON.stringify(e) + ")").catch(() => {});
}
function chatLogAdd(who, text, me) {
	const e = { t: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }), who, text: String(text), me: Boolean(me) };
	chatLog.push(e);
	if (chatLog.length > 300) chatLog.shift();
	chatLogSend(e);
}
function setChatLog(on) {
	chatLogOn = on;
	settings.set({ chatLogOn: on });
	if (on && (!chatLogWin || chatLogWin.isDestroyed())) {
		chatLogWin = new electron.BrowserWindow({ width: 380, height: 520, title: "대화 기록", autoHideMenuBar: true, backgroundColor: "#17131f", webPreferences: { sandbox: true, contextIsolation: true } });
		chatLogWin.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(CHATLOG_HTML));
		chatLogWin.webContents.once("did-finish-load", () => { for (const e of chatLog) chatLogSend(e); });
		chatLogWin.on("closed", () => {
			chatLogWin = null;
			if (chatLogOn) {
				chatLogOn = false;
				settings.set({ chatLogOn: false });
				refreshTray();
			}
		});
	} else if (!on && chatLogWin && !chatLogWin.isDestroyed()) chatLogWin.close();
	refreshTray();
}
async function deliver(reply, source) {'''

EDITS = [
    ("async function deliver(reply, source) {", MODULE),
    ("	console.log(`[say:${source}] ${reply.say.slice(0, 90)}`);\n",
     "	console.log(`[say:${source}] ${reply.say.slice(0, 90)}`);\n	chatLogAdd(source === \"chat\" ? character.name : `${character.name} (${({ observe: \"화면 보고\", touch: \"터치\" })[source] ?? source})`, reply.say, false); // [chatlog patch]\n"),
    ("async function handleChat(rawText, opts = {}) {\n	const text = rawText.slice(0, 2e3).trim();\n",
     "async function handleChat(rawText, opts = {}) {\n	const text = rawText.slice(0, 2e3).trim();\n	if (text && !text.startsWith(\"/\")) chatLogAdd(opts.voice ? \"나 (음성)\" : \"나\", text, true); // [chatlog patch]\n"),
    ('''		{
			label: "캡처에서 숨기기 (OBS·스크린샷에 안 보임)",''', '''		{
			label: "대화 기록 보기",
			type: "checkbox",
			checked: chatLogOn,
			click: (item) => setChatLog(item.checked) // [chatlog patch]
		},
		{
			label: "캡처에서 숨기기 (OBS·스크린샷에 안 보임)",'''),
    ("electron.app.whenReady().then(async () => {\n",
     "electron.app.whenReady().then(async () => {\n	setTimeout(() => { if (chatLogOn) setChatLog(true); }, 1500); // [chatlog patch] reopen if it was on\n"),
]
bak = asar.with_name("app.asar.bak-chatlog")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[chatlog patch]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:60]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
