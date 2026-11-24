"""Deskmate patch: keep mic (listening) and watch on/off across restarts (settings.json micOn / watchOn).

  python patch_remember_toggles.py <app.asar>     re-runnable (first run backs up to app.asar.bak-toggles)
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = "// [remember-toggles patch]"

EDITS = [
    # save on every change
    ("async function setWatching(on) {\n\twatching = on;\n",
     "var togglesRestored = false; " + TAG + "\nasync function setWatching(on) {\n\twatching = on;\n\tsettings.set({ watchOn: Boolean(on) }); " + TAG + "\n"),
    ("\tlistening = on;\n\twin?.webContents.send(\"listen:state\", on);\n",
     "\tlistening = on;\n\tsettings.set({ micOn: Boolean(on) }); " + TAG + "\n\twin?.webContents.send(\"listen:state\", on);\n"),
    # restore once per app start: flags first (so the panel buttons load in the right state), timers after load
    ("\tconst shot = process.env.DESKMATE_DEBUG_SHOT;\n",
     "\tif (!togglesRestored) { " + TAG + "\n"
     "\t\ttogglesRestored = true; " + TAG + "\n"
     "\t\tconst saved = settings.get(); " + TAG + "\n"
     "\t\tif (saved.watchOn) watching = true; " + TAG + "\n"
     "\t\tif (saved.micOn && ears) listening = true; " + TAG + "\n"
     "\t\twin.webContents.once(\"did-finish-load\", () => setTimeout(() => { " + TAG + "\n"
     "\t\t\tif (saved.micOn && ears) void setListening(true); " + TAG + "\n"
     "\t\t\tif (saved.watchOn) void setWatching(true); " + TAG + "\n"
     "\t\t}, 4e3)); " + TAG + "\n"
     "\t} " + TAG + "\n"
     "\tconst shot = process.env.DESKMATE_DEBUG_SHOT;\n"),
]


def patch(src: str) -> str:
    if TAG in src:
        src = "".join(l for l in src.splitlines(keepends=True) if TAG not in l)
        # restore the original lines removed above
        src = src.replace("async function setWatching(on) {\n\twatching = on;\n", "async function setWatching(on) {\n\twatching = on;\n")
    for old, new in EDITS:
        if old not in src:
            raise SystemExit(f"anchor not found: {old[:40]!r}")
        src = src.replace(old, new, 1)
    return src


def main(asar_path: str) -> None:
    asar = Path(asar_path)
    backup = asar.with_name(asar.name + ".bak-toggles")
    if not backup.exists():
        shutil.copy2(asar, backup)
    tool = HERE / "asar_tool.py"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "main.js"
        subprocess.run([sys.executable, str(tool), "get", str(asar), "out/main/index.js", str(f)], check=True, capture_output=True)
        src = f.read_text(encoding="utf-8")
        out = patch(src)
        if out == src:
            print("unchanged out/main/index.js")
            return
        f.write_bytes(out.encode("utf-8"))
        subprocess.run([sys.executable, str(tool), "replace", str(asar), "out/main/index.js", str(f)], check=True, capture_output=True)
        print("patched out/main/index.js")


if __name__ == "__main__":
    main(sys.argv[1])
