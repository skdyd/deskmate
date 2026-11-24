"""Deskmate patch: start with the character picked last time (settings.json activeCharacter), not the .env one.

DESKMATE_CHARACTER in .env becomes only the first-run default. Voice and speed are already remembered by
patch_voices.py (localStorage).
  python patch_remember_character.py <app.asar>     re-runnable (first run backs up to app.asar.bak-remember)
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = 'var requested = process.env.DESKMATE_CHARACTER?.trim() || settings.get().activeCharacter || "mika";'
NEW = 'var requested = settings.get().activeCharacter || process.env.DESKMATE_CHARACTER?.trim() || "mika"; // [remember-character patch]'


def main(asar_path: str) -> None:
    asar = Path(asar_path)
    backup = asar.with_name(asar.name + ".bak-remember")
    if not backup.exists():
        shutil.copy2(asar, backup)
    tool = HERE / "asar_tool.py"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "main.js"
        subprocess.run([sys.executable, str(tool), "get", str(asar), "out/main/index.js", str(f)], check=True, capture_output=True)
        src = f.read_text(encoding="utf-8")
        if NEW in src:
            print("unchanged out/main/index.js")
            return
        if OLD not in src:
            raise SystemExit("anchor not found; not patching")
        f.write_bytes(src.replace(OLD, NEW, 1).encode("utf-8"))
        subprocess.run([sys.executable, str(tool), "replace", str(asar), "out/main/index.js", str(f)], check=True, capture_output=True)
        print("patched out/main/index.js")


if __name__ == "__main__":
    main(sys.argv[1])
