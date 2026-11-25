"""Crop Deskmate window from tour screenshots into contact sheets (a/b side by side)."""
import re, sys
from pathlib import Path
from PIL import Image
d = Path(r'C:\Users\jywhy\Desktop\deskmate AI\logs\tour')
log = (d / 'tour.log').read_text(encoding='utf-8-sig').splitlines()
rects, order = {}, []
last = None
for l in log:
    m = re.match(r'wins: (\d+),(\d+),(\d+),(\d+)', l)
    if m: last = tuple(map(int, m.groups()))
    m = re.search(r' (\S+) done', l)
    if m and last:
        rects[m.group(1)] = last; order.append(m.group(1)); last = None
W, H = 220, 465  # half size per crop
per = 4
for s in range(0, len(order), per):
    names = order[s:s + per]
    sheet = Image.new('RGB', (W * 2 * len(names), H + 20), 'white')
    for i, n in enumerate(names):
        for j, k in enumerate('ab'):
            p = d / f'{n}-{k}.png'
            if not p.exists(): continue
            im = Image.open(p).crop(rects[n]).resize((W, H))
            sheet.paste(im, ((i * 2 + j) * W, 20))
        from PIL import ImageDraw
        ImageDraw.Draw(sheet).text((i * 2 * W + 5, 3), n, fill='black')
    sheet.save(d / f'sheet{s // per}.png')
print(order)
