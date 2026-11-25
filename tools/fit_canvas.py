"""Fit each imported Live2D model's canvas tightly around the drawn character so the app's layout puts her feet
just above the control dots (dots sit at ~94% of the canvas height).

pixi-live2d-display draws the model origin at the canvas centre and ignores CanvasOrigin, so models whose origin is
not centred (Zero, Liveroid, sample0914) were drawn too low and cut off. This script rewrites the canvas info in the
.moc3 (width, height, origin) and adds Layout {CenterX, CenterY} to model.model3.json to undo pixi's centring.

Bounds come from a browser measurement (bounds.json: id -> {ci: canvas info, b: [minx, miny, maxx, maxy] in model
units of the visible drawables}).

usage: python -I fit_canvas.py <bounds.json> [character root]
"""
import json, os, shutil, struct, sys
from pathlib import Path

TOP = 0.03      # empty space above the head, fraction of new canvas height
FEET = 0.935    # where the feet land, fraction of new canvas height (dots at 0.94)
SIDE = 0.06     # extra width on each side, fraction of content width


def main():
    bounds = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(os.environ["APPDATA"]) / "deskmate" / "character"
    for cid, m in bounds.items():
        ci, (minx, miny, maxx, maxy) = m["ci"], m["b"]
        d = root / cid / "model"
        moc = d / "model.moc3"
        orig = d / "model.moc3.canvas-orig"
        if not orig.exists():
            shutil.copy2(moc, orig)
        data = bytearray(orig.read_bytes())
        # keep earlier default-value patches (teto, mita): start from the current file if it differs only there
        cur = bytearray(moc.read_bytes())
        if len(cur) == len(data):
            data = cur
        ppu = ci["ppu"]
        old = struct.pack("<5f", ppu, ci["ox"], ci["oy"], ci["w"], ci["h"])
        k = data.find(old)
        if k < 0 or data.find(old, k + 1) >= 0:
            # already patched? look for ppu followed by anything: search by ppu alone near the start
            print("SKIP", cid, "canvas info not found uniquely")
            continue
        hc = (maxy - miny) * ppu
        wc = (maxx - minx) * ppu
        h = hc / (FEET - TOP)
        w = wc * (1 + 2 * SIDE)
        oy = TOP * h + maxy * ppu          # px from top to the model origin
        ox = SIDE * wc - minx * ppu        # px from left to the model origin
        struct.pack_into("<5f", data, k, ppu, ox, oy, w, h)
        moc.write_bytes(data)
        m3p = d / "model.model3.json"
        m3 = json.loads(m3p.read_text(encoding="utf-8"))
        m3["Layout"] = {"CenterX": round((ox - w / 2) / w, 5), "CenterY": round((h / 2 - oy) / h, 5)}
        m3p.write_text(json.dumps(m3, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{cid}: canvas {ci['w']}x{ci['h']} -> {w:.0f}x{h:.0f}, layout {m3['Layout']}")


if __name__ == "__main__":
    main()
