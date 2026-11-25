"""[watch patch] better screen looks.
- capture only the monitor under the mouse (the one in use) at 1280 px wide instead of all monitors squeezed into
  2048 px (text was unreadable for the small vision model); DESKMATE_CAPTURE_ALL=1 brings back all monitors,
  DESKMATE_CAPTURE_WIDTH still sets the width.
- the foreground window's title and program name go along as text (one short PowerShell call per look).
- the look prompt asks her to talk only about what she can actually see or read, not to guess (no "50 tabs"),
  and lists her last 4 look lines so she does not repeat herself.
usage: python patch_watch.py <app.asar>   (re-runnable)"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
MARK = "[watch patch]"

ACTIVE_WIN = r'''// [watch patch] title + program of the foreground window (Windows), or null
var lastLookLines = [];
var ACTIVE_WIN_PS = `Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class FgW { [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p); }
'@
$h=[FgW]::GetForegroundWindow(); $sb=New-Object Text.StringBuilder 512; [void][FgW]::GetWindowText($h,$sb,512); $p=0; [void][FgW]::GetWindowThreadProcessId($h,[ref]$p)
$n=(Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName
[Console]::OutputEncoding=[Text.Encoding]::UTF8; Write-Output ($n + "|" + $sb.ToString())`;
function activeWindowInfo() {
	if (process.platform !== "win32") return Promise.resolve(null);
	return new Promise((resolve) => {
		require("node:child_process").execFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", ACTIVE_WIN_PS], { windowsHide: true, timeout: 5e3, encoding: "utf8" }, (err, out) => {
			if (err || !out) return resolve(null);
			const line = String(out).trim().split(/\r?\n/).pop() ?? "";
			const i = line.indexOf("|");
			if (i < 0) return resolve(null);
			const app = line.slice(0, i).trim();
			const title = line.slice(i + 1).trim().slice(0, 160);
			resolve(app || title ? { app, title } : null);
		});
	});
}
async function captureScreen() {'''

MAIN = [
    ("async function captureScreen() {", ACTIVE_WIN),
    ("	const displays = electron.screen.getAllDisplays().slice().sort((a, b) => a.bounds.x - b.bounds.x || a.bounds.y - b.bounds.y);\n	const maxWidth = Math.max(640, Number(process.env.DESKMATE_CAPTURE_WIDTH) || 2048);",
     "	// [watch patch] only the monitor in use (under the mouse), unless DESKMATE_CAPTURE_ALL=1\n"
     "	const displays = (process.env.DESKMATE_CAPTURE_ALL === \"1\" ? electron.screen.getAllDisplays() : [electron.screen.getDisplayNearestPoint(electron.screen.getCursorScreenPoint())]).slice().sort((a, b) => a.bounds.x - b.bounds.x || a.bounds.y - b.bounds.y);\n"
     "	const maxWidth = Math.max(640, Number(process.env.DESKMATE_CAPTURE_WIDTH) || (displays.length > 1 ? 2048 : 1280));\n"
     "	const windowInfo = activeWindowInfo();"),
    ("		return {\n			data: jpeg.toString(\"base64\"),\n			mediaType: \"image/jpeg\",\n			monitors\n		};",
     "		win.setOpacity(1); // show her again before waiting for the window title (no long blink)\n		return {\n			data: jpeg.toString(\"base64\"),\n			mediaType: \"image/jpeg\",\n			monitors,\n			window: await windowInfo\n		};"),
    (r"if (stimulus.manual) return `[They just asked you to look at their screen${seen}.]\n${events}\n",
     r"const fg = stimulus.screenshot?.window; // [watch patch]" + "\n"
     r'''		const lookCtx = `${fg ? `\nThe window they are using: "${fg.title}" (${fg.app}).` : ""}\nTalk only about what you can actually see or read in the screenshot or the window title. Do not guess numbers or details you cannot read, and do not bring up browser tabs unless they are clearly what they are doing.${lastLookLines.length ? `\nSay something new; your recent lines were: ${lastLookLines.map((s) => JSON.stringify(s)).join(" / ")}.` : ""}`;''' + "\n"
     r"		if (stimulus.manual) return `[They just asked you to look at their screen${seen}.]\n${events}${lookCtx}\n"),
    (r"return `[You glance at the screen on your own${seen}.]\n${events}\n",
     r"return `[You glance at the screen on your own${seen}.]\n${events}${lookCtx}\n"),
    ("		if (reply.speak && reply.say) await deliver(reply, \"observe\");",
     "		if (reply.speak && reply.say) lastLookLines = [...lastLookLines, reply.say].slice(-4); // [watch patch]\n		if (reply.speak && reply.say) await deliver(reply, \"observe\");"),
]

bak = asar.with_name("app.asar.bak-watch")
if not bak.exists():
    shutil.copy2(asar, bak)
inner = "out/main/index.js"
f = Path(tempfile.mkdtemp()) / "index.js"
asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if MARK in s:
    sys.exit("already patched")
for a, b in MAIN:
    if s.count(a) != 1:
        sys.exit(f"anchor not found once: {a[:70]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8"))
asar_tool.cmd_replace(asar, inner, f)
print("patched", inner)
