"""Minimal asar reader/writer (no Node needed).

  python asar_tool.py get     <app.asar> <inner/path> <out_file>        extract one file
  python asar_tool.py replace <app.asar> <inner/path> <new_file>        replace one file, rewrite offsets + integrity

Format: [4-byte uint32 = 4][uint32 header pickle size][uint32 payload size][uint32 json length][json][pad to 4] then
the file contents back to back; each file node has "offset" (string) and "size" relative to the content start.
Unpacked files ("unpacked": true) live outside the archive and are left alone.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

BLOCK = 4 * 1024 * 1024


def read(asar: Path):
    raw = asar.read_bytes()
    header_size = struct.unpack_from("<I", raw, 4)[0]
    json_len = struct.unpack_from("<I", raw, 12)[0]
    header = json.loads(raw[16:16 + json_len].decode("utf-8"))
    base = 8 + header_size
    return raw, header, base


def node_for(header, inner: str):
    node = header
    for part in inner.replace("\\", "/").split("/"):
        node = node["files"][part]
    return node


def walk(node, prefix=""):
    for name, child in node.get("files", {}).items():
        path = f"{prefix}/{name}" if prefix else name
        if "files" in child:
            yield from walk(child, path)
        else:
            yield path, child


def integrity(data: bytes) -> dict:
    blocks = [hashlib.sha256(data[i:i + BLOCK]).hexdigest() for i in range(0, max(len(data), 1), BLOCK)]
    return {"algorithm": "SHA256", "hash": hashlib.sha256(data).hexdigest(), "blockSize": BLOCK, "blocks": blocks}


def cmd_get(asar, inner, out):
    raw, header, base = read(Path(asar))
    n = node_for(header, inner)
    off = base + int(n["offset"])
    Path(out).write_bytes(raw[off:off + n["size"]])
    print(f"extracted {inner} ({n['size']} bytes)")


def cmd_replace(asar, inner, new_file):
    asar = Path(asar)
    raw, header, base = read(asar)
    target = node_for(header, inner)
    new_data = Path(new_file).read_bytes()
    # Collect every packed file's bytes in archive order, then lay them out again.
    files = [(p, n) for p, n in walk(header) if not n.get("unpacked") and "link" not in n]
    files.sort(key=lambda pn: int(pn[1]["offset"]))
    payload = bytearray()
    for _path, n in files:
        if n is target:
            data = new_data
            n["integrity"] = integrity(data)
        else:
            off = base + int(n["offset"])
            data = raw[off:off + n["size"]]
        n["offset"] = str(len(payload))
        n["size"] = len(data)
        payload += data
    js = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pad = (4 - len(js) % 4) % 4
    pickle_payload = struct.pack("<I", len(js)) + js + b"\0" * pad
    header_pickle = struct.pack("<I", len(pickle_payload)) + pickle_payload
    out = struct.pack("<II", 4, len(header_pickle)) + header_pickle + bytes(payload)
    asar.write_bytes(out)
    print(f"replaced {inner}: {len(new_data)} bytes; archive {len(out)} bytes")


if __name__ == "__main__":
    {"get": cmd_get, "replace": cmd_replace}[sys.argv[1]](*sys.argv[2:])
