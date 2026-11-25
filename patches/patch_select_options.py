"""Make dropdown lists (character, voice) readable: the native popup is white, but options inherited the panel's light text.
Re-runnable: works on the current app.asar, replaces its own block if already present.

  python -I patch_select_options.py [app.asar]
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASAR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "app" / "resources" / "app.asar"
TOOL = HERE / "asar_tool.py"

BLOCK = """
/* deskmate-patch:select-options */
select { color-scheme: dark; }
select option, select optgroup { background: #1e1b2e; color: #f2efff; }
select option:checked { background: #7c5cff; color: #ffffff; }
/* /deskmate-patch:select-options */
"""


def main():
    sys.path.insert(0, str(HERE))
    import asar_tool

    _, header, _ = asar_tool.read(ASAR)
    css = [p for p, _ in asar_tool.walk(header) if re.fullmatch(r"out/renderer/assets/index-[^/]+\.css", p)]
    if len(css) != 1:
        sys.exit(f"expected one renderer css, found {css}")
    inner = css[0]
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "index.css"
        subprocess.run([sys.executable, "-I", str(TOOL), "get", str(ASAR), inner, str(f)], check=True)
        text = f.read_text(encoding="utf-8")
        text = re.sub(r"\n?/\* deskmate-patch:select-options \*/.*?/\* /deskmate-patch:select-options \*/\n?", "", text, flags=re.S)
        f.write_text(text.rstrip("\n") + "\n" + BLOCK, encoding="utf-8")
        backup = ASAR.with_name("app.asar.bak-select")
        if not backup.exists():
            shutil.copy2(ASAR, backup)
        subprocess.run([sys.executable, "-I", str(TOOL), "replace", str(ASAR), inner, str(f)], check=True)
    print("patched", inner)


if __name__ == "__main__":
    main()
