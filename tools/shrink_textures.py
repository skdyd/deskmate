"""Downscale Live2D textures under %APPDATA%/deskmate/character/*/model/textures so the longest side is <= MAX (default 2048).
Keeps VRAM low while gaming. usage: python -I shrink_textures.py [max] [character id ...]"""
import os, sys
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
mx = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
ids = sys.argv[2:]
root = Path(os.environ["APPDATA"]) / "deskmate" / "character"
for tex in sorted(root.glob("*/model/textures/*.png")):
    cid = tex.parts[-4]
    if ids and cid not in ids:
        continue
    im = Image.open(tex)
    w, h = im.size
    if max(w, h) <= mx:
        continue
    s = mx / max(w, h)
    im.convert("RGBA").resize((round(w * s), round(h * s)), Image.LANCZOS).save(tex, optimize=False)
    print(cid, tex.name, (w, h), "->", (round(w * s), round(h * s)))
