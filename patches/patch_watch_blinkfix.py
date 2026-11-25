"""One-off fix on an asar that already has the first patch_watch.py: restore opacity before awaiting the window title.
(patch_watch.py itself now includes this.) usage: python patch_watch_blinkfix.py <app.asar>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
A = '		return {\n			data: jpeg.toString("base64"),\n			mediaType: "image/jpeg",\n			monitors,\n			window: await windowInfo\n		};'
B = '		win.setOpacity(1); // show her again before waiting for the window title (no long blink)\n' + A
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "no long blink" in s: sys.exit("already fixed")
if s.count(A) != 1: sys.exit("anchor not found")
f.write_bytes(s.replace(A, B).encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("fixed")
