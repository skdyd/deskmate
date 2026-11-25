"""[version patch] shows "Deskmate 패치 버전 X.Y.Z" (from deskmate AI\VERSION) as the first, disabled tray menu line.
Re-run after bumping VERSION; it replaces the old number. usage: python patch_version.py <app.asar> [version]"""
import re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"
ver = sys.argv[2] if len(sys.argv) > 2 else (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
line = f'\t\t{{ label: "Deskmate 패치 버전 {ver}", enabled: false }}, // [version patch]\n'
if "[version patch]" in s:
    s = re.sub(r'\t\t\{ label: "Deskmate 패치 버전 [^"]*", enabled: false \}, // \[version patch\]\n', line, s)
else:
    a = "	return electron.Menu.buildFromTemplate([\n"
    if s.count(a) != 1: sys.exit("anchor not found")
    s = s.replace(a, a + line)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("version", ver)
