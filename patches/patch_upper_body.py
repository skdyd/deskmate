"""[upper-body patch] Live2D: feet sit right above the panel for every character (bottom-anchored), and a 6th dot
toggles an upper-body view (same size, only the top ~55% of the model is drawn, so she takes less height).

usage: python patch_upper_body.py <app.asar>     (re-runnable; extracts the current bundles itself)
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import asar_tool  # noqa: E402

asar = Path(sys.argv[1])
MARK = "[upper-body patch]"

OLD_LAYOUT = """		layout() {
			if (!model) return;
			const ow = model.internalModel.originalWidth;
			const oh = model.internalModel.originalHeight;
			const availH = app.screen.height - TOP - BOTTOM;
			const scale = Math.min(availH / oh, (app.screen.width - 20) / ow);
			model.scale.set(scale);
			model.anchor.set(.5, 0);
			model.x = app.screen.width / 2;
			model.y = TOP;
		},
		getBounds() {
			if (!model) return null;
			const b = model.getBounds();
			return {
				x: b.x,
				y: b.y,
				width: b.width,
				height: b.height
			};
		},"""

NEW_LAYOUT = """		layout() { // [upper-body patch] feet on the floor line above the panel; upper-body view draws only the top part
			if (!model) return;
			const ow = model.internalModel.originalWidth;
			const oh = model.internalModel.originalHeight;
			const availH = app.screen.height - TOP - BOTTOM;
			const floorY = TOP + availH;
			const scale = Math.min(availH / oh, (app.screen.width - 20) / ow);
			// how much of her (from the top) to show: 1, .8, .6, .4, .2, per character (the 6th dot cycles it)
			const show = Number(localStorage.getItem("deskmate.dots.upper." + character.id)) || 1;
			const upper = show < 1;
			model.scale.set(scale);
			model.anchor.set(.5, 0);
			model.x = app.screen.width / 2;
			model.y = floorY - oh * scale * show;
			// Live2D draws past pixi masks, so clip the canvas itself below the floor line
			canvas.style.clipPath = upper ? `inset(0 0 ${Math.max(0, Math.round(app.screen.height - floorY))}px 0)` : "";
			upperFloor = upper ? floorY : null;
		},
		getBounds() {
			if (!model) return null;
			const b = model.getBounds();
			// upper-body view: report her as ending at the floor line (dots sit at 94% of the height)
			const height = upperFloor == null ? b.height : (upperFloor - b.y) / .94;
			return {
				x: b.x,
				y: b.y,
				width: b.width,
				height
			};
		},"""

DECL_ANCHOR = "	let model = null;\n	let fakeMouth = 0;\n"
DECL_NEW = "	let model = null;\n	let fakeMouth = 0;\n	let upperMask = null; // [upper-body patch]\n	let upperFloor = null;\n	const UPPER_SHOW = .55;\n"

DOT_ANCHOR = 'const dotPanel = makeDot("dot-panel", "대화창 보이기/숨기기");\n'
DOT_NEW = DOT_ANCHOR + '''const dotUpper = makeDot("dot-upper", "보이는 부분 줄이기"); // [upper-body patch]
const upperKey = () => "deskmate.dots.upper." + (config?.character?.id ?? "");
const upperShow = () => Number(localStorage.getItem(upperKey())) || 1;
'''
APPLY_ANCHOR = '	dotPanel.classList.toggle("on", !dotsPanelHidden);\n'
APPLY_NEW = APPLY_ANCHOR + '''	dotUpper.classList.toggle("on", upperShow() < 1);
	dotUpper.title = `보이는 부분 ${Math.round(upperShow() * 5)}/5 (누를 때마다 한 칸씩 줄어듦)`;
'''
CLICK_ANCHOR = 'dotSmaller.addEventListener("click", () => setZoom(dotsZoom - .1));\n'
CLICK_NEW = '''dotUpper.addEventListener("click", () => {
	// full -> 4/5 -> 3/5 -> 2/5 -> 1/5 -> full, remembered per character
	const next = Math.round(upperShow() * 5) - 1;
	localStorage.setItem(upperKey(), String(next >= 1 ? next / 5 : 1));
	avatar?.layout();
	applyDots();
});
''' + CLICK_ANCHOR
BUBBLE_ANCHOR = "	placeBubble(cx);\n}\n"
BUBBLE_NEW = """	placeBubble(cx);
	// [upper-body patch] upper-body view: bubble just above her head instead of at the window top
	dotUpper.classList.toggle("on", upperShow() < 1);
	bubble.style.top = upperShow() < 1 && b ? `${Math.round(Math.max(8, b.y + b.height * .02 - bubble.offsetHeight - 8))}px` : "";
}
"""


def sub_once(s, old, new, what):
    if s.count(old) != 1:
        raise SystemExit(f"anchor for {what} found {s.count(old)} times; not patching")
    return s.replace(old, new)


def main():
    _raw, header, _base = asar_tool.read(asar)
    paths = [p for p, _n in asar_tool.walk(header)]
    l2d = [p for p in paths if re.match(r"out/renderer/assets/live2d-.*\.js$", p)]
    idx = [p for p in paths if re.match(r"out/renderer/assets/index-.*\.js$", p)]
    assert len(l2d) == 1 and len(idx) == 1, (l2d, idx)
    tmp = Path(tempfile.mkdtemp())
    bak = asar.with_name("app.asar.bak-upper")
    if not bak.exists():
        shutil.copy2(asar, bak)
    for inner, edit in ((l2d[0], edit_l2d), (idx[0], edit_idx)):
        f = tmp / Path(inner).name
        asar_tool.cmd_get(asar, inner, f)
        s = f.read_bytes().decode("utf-8")
        if MARK in s:
            print("already patched:", inner)
            continue
        f.write_bytes(edit(s).encode("utf-8"))
        asar_tool.cmd_replace(asar, inner, f)
        print("patched", inner)


def edit_l2d(s):
    s = sub_once(s, OLD_LAYOUT, NEW_LAYOUT, "layout")
    return sub_once(s, DECL_ANCHOR, DECL_NEW, "decl")


def edit_idx(s):
    s = sub_once(s, DOT_ANCHOR, DOT_NEW, "dot")
    s = sub_once(s, APPLY_ANCHOR, APPLY_NEW, "apply")
    s = sub_once(s, CLICK_ANCHOR, CLICK_NEW, "click")
    return sub_once(s, BUBBLE_ANCHOR, BUBBLE_NEW, "bubble")


main()
