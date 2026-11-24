"""Same-length in-place patch of Deskmate's app.asar so Ollama unloads the model after 5 minutes idle
instead of the hard-coded 30 minutes (src/main/ollama.ts sends keep_alive: '30m' on every request,
which overrides the OLLAMA_KEEP_ALIVE server setting).

Usage:   python patch_keep_alive.py "C:\\Users\\jywhy\\Desktop\\deskmate AI\\app\\resources\\app.asar"
Undo:    copy app.asar.orig back over app.asar (made on first run).
The byte length stays identical, so the asar header offsets remain valid. Re-run after a Deskmate update.
"""
import shutil
import sys
from pathlib import Path

OLD = b'keep_alive: "30m",'
NEW = b'keep_alive: "5m" ,'
assert len(OLD) == len(NEW)

asar = Path(sys.argv[1])
data = asar.read_bytes()
if NEW in data:
    print("already patched")
    sys.exit(0)
count = data.count(OLD)
if count != 1:
    print(f"expected exactly one match, found {count}; not patching")
    sys.exit(1)
backup = asar.with_name(asar.name + ".orig")
if not backup.exists():
    shutil.copy2(asar, backup)
    print(f"backup: {backup}")
asar.write_bytes(data.replace(OLD, NEW))
print("patched keep_alive 30m -> 5m")
