"""Clamp a parameter's min/max inside a .moc3 (e.g. ParamAngleZ to +-10 so mouse-follow does not tilt the head 30 deg).

Finds the parameter id slot (64-byte ids table), then the section offset table entry pointing at the ids table; the
next three entries are the max, min and default value arrays (Cubism moc3 layout).

usage: python -I clamp_moc3_param.py <model.moc3> <param id> <index> <limit>
  index: the parameter's index (from the runtime), limit: new range is [-limit, limit] (only narrows)
"""
import shutil, struct, sys
from pathlib import Path

moc, pid, idx, lim = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
data = bytearray(moc.read_bytes())
needle = pid.encode() + b"\x00"
ids_start = None
pos = 0
while (k := data.find(needle, pos)) != -1:
    cand = k - 64 * idx
    table = struct.unpack_from("<160I", data, 64)
    if cand > 0 and cand in table:
        ids_start = cand
        break
    pos = k + 1
if ids_start is None:
    sys.exit(f"{moc}: ids table for {pid} not found")
t = list(struct.unpack_from("<160I", data, 64))
j = t.index(ids_start)
mx_off, mn_off = t[j + 1], t[j + 2]
mx = struct.unpack_from("<f", data, mx_off + 4 * idx)[0]
mn = struct.unpack_from("<f", data, mn_off + 4 * idx)[0]
if not (mn < 0 < mx):
    sys.exit(f"{moc}: unexpected range {mn}..{mx}")
bak = moc.with_name(moc.name + ".clamp-orig")
if not bak.exists():
    shutil.copy2(moc, bak)
struct.pack_into("<f", data, mx_off + 4 * idx, min(mx, lim))
struct.pack_into("<f", data, mn_off + 4 * idx, max(mn, -lim))
moc.write_bytes(data)
print(f"{moc.parts[-3]} {pid}: {mn}..{mx} -> {max(mn, -lim)}..{min(mx, lim)}")
