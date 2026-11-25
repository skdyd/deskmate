"""[ears-queue patch] while she is still answering, keep the newest utterance (one slot) and answer it right after,
instead of dropping it. usage: python patch_ears_queue.py <app.asar>   (re-runnable)"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
EDITS = [
    ('''	if (hearing) {
		console.log("[ears] still answering the last one; dropped an utterance");
		return;
	}''', '''	if (hearing) { // [ears-queue patch] keep the newest one and answer it next
		if (pendingUtterance) console.log("[ears] replaced a waiting utterance with a newer one");
		pendingUtterance = [bytes, ms];
		return;
	}'''),
    ('''	} finally {
		hearing = false;
	}
}
electron.ipcMain.handle("listen:set"''', '''	} finally {
		hearing = false;
		if (pendingUtterance && listening) { // [ears-queue patch]
			const [b, m] = pendingUtterance;
			pendingUtterance = null;
			void onUtterance(b, m);
		} else pendingUtterance = null;
	}
}
var pendingUtterance = null;
electron.ipcMain.handle("listen:set"'''),
]
inner = "out/main/index.js"
bak = asar.with_name("app.asar.bak-earsq")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"
asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[ears-queue patch]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:50]!r}")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8"))
asar_tool.cmd_replace(asar, inner, f)
print("patched", inner)
