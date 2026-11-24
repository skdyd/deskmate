"""Cap the Live2D avatar's frame rate (default 30 fps) in Deskmate's app.asar.

Without a cap PixiJS renders at the monitor refresh rate (165 Hz here), which costs about one CPU core
(Electron GPU process + renderer) even while idle. This sets maxFPS on both the avatar's Application ticker
(drawing) and PIXI.Ticker.shared (pixi-live2d-display updates the model's motion/physics on the shared ticker).

Usage:   python patch_live2d_fps.py js "<...>\\app\\resources\\app.asar" [fps]
         python patch_live2d_fps.py ts "<...>\\deskmate-src\\src\\renderer\\live2d.ts" [fps]
Re-running replaces the previous value. Undo: run with fps 0 (0 = no cap in PixiJS).
Touches only the lines right after `new Application({...})` in createLive2DAvatar.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "// [live2d-fps patch]"
ANCHOR = re.compile(r"(function createLive2DAvatar\(canvas(?:: HTMLCanvasElement)?, character(?:: CharacterConfig)?\)[^{]*\{\s*"
                    r"const app = new (?:PIXI\.)?Application\(\{.*?\r?\n([ \t]*)\}\);?\r?\n)", re.S)
OLD_LINE = re.compile(r"[ \t]*app\.ticker\.maxFPS = \d+;[^\n]*" + re.escape(MARK) + r"\r?\n")


def splice(src: str, fps: int, ts: bool) -> str:
    src = OLD_LINE.sub("", src)
    m = ANCHOR.search(src)
    if not m:
        raise SystemExit("createLive2DAvatar / new Application anchor not found; not patching")
    shared = "PIXI.Ticker.shared" if ts else "window.PIXI.Ticker.shared"
    line = f"{m.group(2)}app.ticker.maxFPS = {fps}; {shared}.maxFPS = {fps}; {MARK}" + ("\r\n" if "\r\n" in src else "\n")
    return src[: m.end()] + line + src[m.end():]


def run_tool(*args):
    subprocess.run([sys.executable, str(HERE / "asar_tool.py"), *args], check=True)


def patch_js(asar: Path, fps: int) -> None:
    listing = subprocess.run([sys.executable, "-c",
        "import sys;sys.path.insert(0,r'%s');import asar_tool as a;from pathlib import Path;"
        "r,h,b=a.read(Path(r'%s'));print('\\n'.join(p for p,_ in a.walk(h) if p.startswith('out/renderer/assets/live2d-') and p.endswith('.js')))" % (HERE, asar)],
        capture_output=True, text=True, check=True).stdout.split()
    if len(listing) != 1:
        raise SystemExit(f"expected one renderer live2d bundle, found {listing}")
    inner = listing[0]
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "index.js"
        run_tool("get", str(asar), inner, str(f))
        src = f.read_bytes().decode("utf-8")
        new = splice(src, fps, ts=False)
        if new == src:
            print("already patched with this value")
            return
        f.write_text(new, encoding="utf-8", newline="")
        backup = asar.with_name(asar.name + ".bak-fps")
        shutil.copy2(asar, backup)
        print(f"backup: {backup}")
        run_tool("replace", str(asar), inner, str(f))
    print(f"patched {inner}: Live2D maxFPS = {fps}")


def patch_ts(ts: Path, fps: int) -> None:
    src = ts.read_bytes().decode("utf-8")
    ts.write_text(splice(src, fps, ts=True), encoding="utf-8", newline="")
    print(f"patched {ts}: Live2D maxFPS = {fps}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in ("js", "ts"):
        print(__doc__)
        sys.exit(2)
    fps = int(sys.argv[3]) if len(sys.argv) == 4 else 30
    (patch_js if sys.argv[1] == "js" else patch_ts)(Path(sys.argv[2]), fps)
