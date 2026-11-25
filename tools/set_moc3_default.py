"""Change one parameter's default value inside a .moc3 (e.g. keep a 'hide notice/watermark' toggle on).
Finds the parameter default-value array by its exact float32 contents (pass them as a JSON list) and patches index i.
usage: python -I set_moc3_default.py <model.moc3> <defaults.json> <index> <value>"""
import json, shutil, struct, sys
moc, defs, i, v = sys.argv[1], json.load(open(sys.argv[2])), int(sys.argv[3]), float(sys.argv[4])
data = bytearray(open(moc, "rb").read())
pat = struct.pack(f"<{len(defs)}f", *defs)
hits = []
start = 0
while (k := data.find(pat, start)) != -1:
    hits.append(k); start = k + 4
if len(hits) != 1:
    sys.exit(f"expected 1 match, found {len(hits)}")
shutil.copy2(moc, moc + ".orig")
struct.pack_into("<f", data, hits[0] + 4 * i, v)
open(moc, "wb").write(data)
print("patched", moc, "offset", hits[0] + 4 * i)
