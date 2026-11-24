"""Deskmate patch: five small dots under her feet are the only handles; everything else clicks through.

  dots, left to right:
    react : touch reactions on/off. On = her body takes clicks (tap -> expression + a line); off = clicks pass through her.
    -     : smaller (10% steps, 60%..130%, feet stay put)
    move  : drag to move the window
    +     : bigger
    panel : show / hide the bottom panel (input, look, watch, mic)
  The panel takes clicks only while shown. Bubble and the old top grip never take clicks (grip hidden).
  react / panel / size are kept in localStorage.

  Moving: only her body (+ dots, + panel while shown, + bubble height) has to stay on the monitor under the cursor,
  so she can stand right on the taskbar or at the screen edge; the transparent margin of the window may go off screen.
  The speech bubble has a fixed width and is placed inside the part of the window that is on the current monitor,
  so it never spills onto the next monitor; its tail keeps pointing at her.

  python patch_dots.py js <app.asar>        patch the installed asar in place (first run backs up to app.asar.bak-dots)
  python patch_dots.py ts <deskmate-src>     same change on the TypeScript source
Re-running replaces an older version of this patch.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "[dots patch]"

# ---------------------------------------------------------------- renderer
# Replaces everything from `function overUi(` (or an older dots block) up to `var LOCAL_COMMANDS` / `// ---- UI`.
RENDERER = r"""// [dots patch] five dots under her feet are the only handles; everything else clicks through.
const DOTS_REACT_KEY = "deskmate.dots.reactive";
const DOTS_PANEL_KEY = "deskmate.dots.panelHidden";
const DOTS_ZOOM_KEY = "deskmate.dots.zoom";
const BUBBLE_W = 280;
let dotsReactive = localStorage.getItem(DOTS_REACT_KEY) === "1";
let dotsPanelHidden = localStorage.getItem(DOTS_PANEL_KEY) === "1";
let dotsZoom = Math.min(1.3, Math.max(.6, Number(localStorage.getItem(DOTS_ZOOM_KEY)) || 1));
const dotsStyle = document.createElement("style");
dotsStyle.textContent = `
#grip { display: none !important; }
#bubble { pointer-events: none; right: auto; width: ${BUBBLE_W}px; max-width: calc(100% - 16px); }
#bubble::after { left: var(--tail, 50%); }
#panel.dots-hidden { display: none; }
#dots { position: absolute; display: flex; align-items: center; gap: 8px; transform: translateX(-50%); z-index: 10; padding: 3px; }
#dots .dot { width: 11px; height: 11px; border-radius: 50%; background: rgba(255,255,255,0.45); box-shadow: 0 0 0 1px rgba(0,0,0,0.45), 0 1px 4px rgba(0,0,0,0.4); cursor: pointer; transition: transform 0.12s, background 0.12s; display: flex; align-items: center; justify-content: center; font: bold 10px/1 system-ui, sans-serif; color: rgba(20,14,40,0.85); user-select: none; }
#dots .dot:hover { transform: scale(1.35); background: rgba(255,255,255,0.85); }
#dots .dot.on { background: var(--accent); }
#dots .dot.size { width: 9px; height: 9px; font-size: 9px; }
#dots #dot-move { cursor: grab; }`;
document.head.appendChild(dotsStyle);
const dots = document.createElement("div");
dots.id = "dots";
const makeDot = (id__T_S, title__T_S, label__T_S = "") => {
	const d = document.createElement("div");
	d.id = id;
	d.className = "dot";
	d.title = title;
	d.textContent = label;
	dots.appendChild(d);
	return d;
};
const dotReact = makeDot("dot-react", "클릭 반응 켜기/끄기");
const dotSmaller = makeDot("dot-smaller", "작게", "−");
const dotMove = makeDot("dot-move", "끌어서 이동");
const dotBigger = makeDot("dot-bigger", "크게", "+");
const dotPanel = makeDot("dot-panel", "대화창 보이기/숨기기");
dotSmaller.classList.add("size");
dotBigger.classList.add("size");
document.body.appendChild(dots);
function applyDots() {
	dotReact.classList.toggle("on", dotsReactive);
	dotPanel.classList.toggle("on", !dotsPanelHidden);
	panel.classList.toggle("dots-hidden", dotsPanelHidden);
	placeDots();
}
/** Keep the dots just under her feet (above the panel while it shows), and the bubble on this monitor. */
function placeDots() {
	const b = avatar?.getBounds();
	const W = window.innerWidth;
	const H = window.innerHeight;
	const floor = (dotsPanelHidden ? H : panel.getBoundingClientRect().top) - 20;
	// Live2D bounds end a little below her shoes (transparent margin): sit the dots right under the shoes.
	const top = b ? b.y + b.height * .94 : floor;
	const cx = b ? b.x + b.width / 2 : W / 2;
	dots.style.top = `${Math.round(Math.max(0, Math.min(top, floor)))}px`;
	dots.style.left = `${Math.round(Math.max(60, Math.min(cx, W - 60)))}px`;
	placeBubble(cx);
}
function placeBubble(cx__T_N) {
	const W = window.innerWidth;
	// the part of this window that lies on the monitor it is on
	const scr = window.screen;
	const availLeft = scr.availLeft ?? 0;
	const visL = Math.max(0, availLeft - window.screenX);
	const visR = Math.min(W, availLeft + scr.availWidth - window.screenX);
	const bw = Math.max(120, Math.min(BUBBLE_W, W - 16, visR - visL - 16));
	bubble.style.width = `${Math.round(bw)}px`;
	let left = cx - bw / 2;
	left = Math.min(left, visR - 8 - bw);
	left = Math.max(left, visL + 8);
	left = Math.max(8, Math.min(left, W - 8 - bw));
	bubble.style.left = `${Math.round(left)}px`;
	bubble.style.setProperty("--tail", `${Math.round(Math.max(16, Math.min(bw - 16, cx - left)))}px`);
}
/** What has to stay on screen while moving: her body, the dots, the panel while shown, and room for the bubble. */
function contentRect() {
	const rs = [];
	const b = avatar?.getBounds();
	// Live2D bounds carry transparent margin around her: let 15% per side go past the screen edge.
	if (b) rs.push({ x: b.x + b.width * .15, y: b.y, w: b.width * .7, h: b.height * .94 });
	const d = dots.getBoundingClientRect();
	rs.push({ x: d.left, y: d.top, w: d.width, h: d.height });
	if (!dotsPanelHidden) {
		const p = panel.getBoundingClientRect();
		rs.push({ x: p.left, y: p.top, w: p.width, h: p.height });
	}
	const x0 = Math.min(...rs.map((r) => r.x));
	const y0 = Math.min(14, ...rs.map((r) => r.y));
	const x1 = Math.max(...rs.map((r) => r.x + r.w));
	const y1 = Math.max(...rs.map((r) => r.y + r.h));
	return { x: Math.round(x0), y: Math.round(y0), w: Math.round(x1 - x0), h: Math.round(y1 - y0) };
}
function setZoom(z__T_N) {
	dotsZoom = Math.round(Math.min(1.3, Math.max(.6, z)) * 10) / 10;
	localStorage.setItem(DOTS_ZOOM_KEY, String(dotsZoom));
	api.setZoom?.(dotsZoom);
}
dotReact.addEventListener("click", () => {
	dotsReactive = !dotsReactive;
	localStorage.setItem(DOTS_REACT_KEY, dotsReactive ? "1" : "0");
	applyDots();
});
dotPanel.addEventListener("click", () => {
	dotsPanelHidden = !dotsPanelHidden;
	localStorage.setItem(DOTS_PANEL_KEY, dotsPanelHidden ? "1" : "0");
	if (dotsPanelHidden && panel.contains(document.activeElement)) document.activeElement.blur();
	applyDots();
});
dotSmaller.addEventListener("click", () => setZoom(dotsZoom - .1));
dotBigger.addEventListener("click", () => setZoom(dotsZoom + .1));
applyDots();
if (dotsZoom !== 1) api.setZoom?.(dotsZoom);
window.setInterval(placeDots, 250);
window.addEventListener("resize", () => {
	// the canvas resizes on the next frame; lay her out after it
	window.setTimeout(() => {
		avatar?.layout();
		placeDots();
	}, 80);
});
function overUi(x__T_N, y__T_N) {
	const el = document.elementFromPoint(x, y);
	return Boolean(el && (dots.contains(el) || (!dotsPanelHidden && panel.contains(el))));
}
function overModel(x__T_N, y__T_N) {
	if (!dotsReactive) return false;
	const b = avatar?.getBounds();
	return Boolean(b && x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height);
}
/** Which part of her was touched, from where the pointer sits inside her bounds. */
function touchArea(y__T_N) {
	const b = avatar?.getBounds();
	if (!b) return "body";
	const rel = (y - b.y) / Math.max(1, b.height);
	if (rel < .22) return "head";
	if (rel < .42) return "chest";
	if (rel < .62) return "body";
	return "legs";
}
function wirePointer() {
	let ignoring = false;
	const setIgnore = (ignore__T_B) => {
		if (ignore !== ignoring) {
			ignoring = ignore;
			api.setIgnoreMouse(ignore);
		}
	};
	const wantsMouse = (x__T_N, y__T_N) => overUi(x, y) || overModel(x, y);
	let drag__T_DRAG = null;
	window.addEventListener("mousemove", (e) => {
		avatar?.pointerMove(e.clientX, e.clientY);
		if (drag) return;
		setIgnore(!wantsMouse(e.clientX, e.clientY));
	});
	window.addEventListener("mouseleave", () => {
		if (!drag) setIgnore(true);
	});
	window.addEventListener("pointerdown", (e) => {
		if (e.button !== 0) return;
		let mode__T_MODE;
		if (e.target === dotMove) mode = "move";
		else if (!overUi(e.clientX, e.clientY) && overModel(e.clientX, e.clientY)) mode = "tap";
		else return;
		drag = {
			mode,
			lastX: e.screenX,
			lastY: e.screenY,
			moved: 0,
			area: mode === "move" ? "body" : touchArea(e.clientY),
			lastKick: 0,
			rect: mode === "move" ? contentRect() : null
		};
		try { document.body.setPointerCapture(e.pointerId); } catch {}
		e.preventDefault();
	});
	window.addEventListener("pointermove", (e) => {
		if (!drag) return;
		const dx = e.screenX - drag.lastX;
		const dy = e.screenY - drag.lastY;
		drag.lastX = e.screenX;
		drag.lastY = e.screenY;
		drag.moved += Math.hypot(dx, dy);
		if (drag.mode === "move" && drag.moved > 3) {
			if (!document.body.classList.contains("dragging")) {
				document.body.classList.add("dragging");
				avatar?.setExpression("surprised");
			}
			api.moveBy(dx, dy, drag.rect);
			const now = performance.now();
			if (now - drag.lastKick > 140) {
				drag.lastKick = now;
				avatar?.kick(.5 + Math.min(1, Math.hypot(dx, dy) / 25));
			}
		}
	});
	const release = (e__T_PE) => {
		if (!drag) return;
		const d = drag;
		drag = null;
		document.body.classList.remove("dragging");
		if (d.mode === "move") {
			if (d.moved > 3) {
				avatar?.kick(1.2);
				api.react({
					kind: "drag",
					area: d.area
				});
			}
		} else if (d.moved <= 6) {
			avatar?.kick(1.2);
			const quick__T_EMO = d.area === "head" ? ["happy", "shy"] : d.area === "chest" ? [
				"surprised",
				"shy",
				"angry"
			] : ["surprised", "flirty"];
			avatar?.setExpression(quick[Math.floor(Math.random() * quick.length)]);
			api.react({
				kind: "tap",
				area: d.area
			});
		}
		placeDots();
		setIgnore(!wantsMouse(e.clientX, e.clientY));
	};
	window.addEventListener("pointerup", release);
	window.addEventListener("pointercancel", release);
}
"""

TS_TYPES = {
    "__T_S": ": string",
    "__T_N": ": number",
    "__T_B": ": boolean",
    "__T_PE": ": PointerEvent",
    "__T_EMO": ": Emotion[]",
    "__T_MODE": ": 'move' | 'tap'",
    "__T_DRAG": ": { mode: 'move' | 'tap'; lastX: number; lastY: number; moved: number; area: Touch['area']; lastKick: number; rect: Rect | null } | null",
}


def renderer(ts: bool) -> str:
    out = RENDERER
    for k, v in TS_TYPES.items():
        out = out.replace(k, v if ts else "")
    if ts:
        out = out.replace("document.activeElement.blur()", "(document.activeElement as HTMLElement).blur()")
        out = out.replace("function contentRect() {", "type Rect = { x: number; y: number; w: number; h: number }\nfunction contentRect(): Rect {")
        out = out.replace("const rs = [];", "const rs: Rect[] = [];")
        for name in ("applyDots", "placeDots", "wirePointer"):
            out = out.replace(f"function {name}() {{", f"function {name}(): void {{")
    return out


def splice_renderer(src: str, end_marker: str, ts: bool) -> str:
    if MARK in src:
        start = src.find("// " + MARK)
    else:
        start = src.find("function overUi(")
        line_start = src.rfind("\n", 0, start - 1) + 1  # take the comment line above overUi along (TS source)
        if start >= 0 and src[line_start:start].lstrip().startswith("//"):
            start = line_start
    end = src.find(end_marker)
    if start < 0 or end < 0 or end < start:
        raise SystemExit("renderer anchors not found; not patching")
    return src[:start] + renderer(ts) + "\n" + src[end:]


# ---------------------------------------------------------------- main process
MAIN_JS = r"""// [dots patch] moving keeps her body (a rect inside the window, from the renderer) on the monitor under the cursor;
// the transparent margin may leave the screen. Zoom resizes the window around her feet.
let dotsMoveAim = null;
let dotsMoveAt = 0;
electron.ipcMain.on("window:move-by", (_event, dx, dy, rect) => {
	const now = Date.now();
	if (!dotsMoveAim || now - dotsMoveAt > 400) {
		const [x, y] = win.getPosition();
		dotsMoveAim = { x, y };
	}
	dotsMoveAt = now;
	dotsMoveAim.x += Number(dx) || 0;
	dotsMoveAim.y += Number(dy) || 0;
	let nx = dotsMoveAim.x;
	let ny = dotsMoveAim.y;
	if (rect && Number.isFinite(rect.w) && Number.isFinite(rect.h)) {
		const wa = electron.screen.getDisplayNearestPoint(electron.screen.getCursorScreenPoint()).workArea;
		nx = Math.min(Math.max(nx, wa.x - rect.x), wa.x + wa.width - rect.x - rect.w);
		ny = Math.min(Math.max(ny, wa.y - rect.y), wa.y + wa.height - rect.y - rect.h);
	}
	win.setPosition(Math.round(nx), Math.round(ny));
});
electron.ipcMain.on("window:zoom", (_event, zoom) => {
	const z = Math.min(1.3, Math.max(.6, Number(zoom) || 1));
	const b = win.getBounds();
	const wa = electron.screen.getDisplayMatching(b).workArea;
	// width stays (room for the bubble); only the height she is fitted into scales (bubble 92 px + panel 100 px stay)
	const w = WIN_W;
	const h = Math.min(Math.round(192 + (Math.min(WIN_H, wa.height - 24) - 192) * z), wa.height);
	const bounds = { x: Math.round(b.x + (b.width - w) / 2), y: b.y + b.height - h, width: w, height: h };
	win.setResizable(true);
	win.setBounds(bounds);
	win.setResizable(false);
	dotsMoveAim = null;
});
"""
MAIN_OLD = """electron.ipcMain.on("window:move-by", (_event, dx, dy) => {
	const [x, y] = win.getPosition();
	win.setPosition(Math.round(x + Number(dx)), Math.round(y + Number(dy)));
});
"""
MAIN_END = 'electron.ipcMain.handle("watch:toggle"'


def splice_main(src: str) -> str:
    if MARK in src:
        start = src.find("// " + MARK)
    else:
        if src.count(MAIN_OLD) != 1:
            raise SystemExit("move-by handler not found; main not patched")
        start = src.find(MAIN_OLD)
    end = src.find(MAIN_END, start)
    if start < 0 or end < 0:
        raise SystemExit("main anchors not found; not patching")
    return src[:start] + MAIN_JS + src[end:]


# ---------------------------------------------------------------- preload
PRELOAD_OLD = 'moveBy: (dx, dy) => electron.ipcRenderer.send("window:move-by", dx, dy),'
PRELOAD_NEW = ('moveBy: (dx, dy, rect) => electron.ipcRenderer.send("window:move-by", dx, dy, rect),\n'
               '\tsetZoom: (z) => electron.ipcRenderer.send("window:zoom", z),')


def splice_preload(src: str) -> str:
    if "window:zoom" in src:
        return src
    if src.count(PRELOAD_OLD) != 1:
        raise SystemExit("preload moveBy not found; not patching")
    return src.replace(PRELOAD_OLD, PRELOAD_NEW)


# ---------------------------------------------------------------- asar plumbing
def asar_paths(asar: Path) -> list:
    sys.path.insert(0, str(HERE))
    import asar_tool
    _, header, _ = asar_tool.read(asar)
    return [p for p, _ in asar_tool.walk(header)]


def edit_in_asar(asar: Path, inner: str, fn) -> None:
    tool = HERE / "asar_tool.py"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "f.js"
        subprocess.run([sys.executable, str(tool), "get", str(asar), inner, str(f)], check=True, capture_output=True)
        src = f.read_text(encoding="utf-8")
        new = fn(src)
        if new == src:
            print(f"unchanged {inner}")
            return
        f.write_text(new, encoding="utf-8")
        subprocess.run([sys.executable, str(tool), "replace", str(asar), inner, str(f)], check=True, capture_output=True)
    print(f"patched {inner}")


def patch_js(asar: Path) -> None:
    paths = asar_paths(asar)
    bundles = [p for p in paths if p.startswith("out/renderer/assets/index-") and p.endswith(".js")]
    if len(bundles) != 1:
        raise SystemExit(f"expected one renderer index bundle, found {bundles}")
    backup = asar.with_name(asar.name + ".bak-dots")
    if not backup.exists():
        shutil.copy2(asar, backup)
        print(f"backup: {backup}")
    edit_in_asar(asar, "out/preload/index.js", splice_preload)
    edit_in_asar(asar, "out/main/index.js", splice_main)
    edit_in_asar(asar, bundles[0], lambda s: splice_renderer(s, "var LOCAL_COMMANDS", ts=False))


# ---------------------------------------------------------------- TypeScript source
TS_MAIN = """// [dots patch] moving keeps her body (a rect inside the window, from the renderer) on the monitor under the cursor;
// the transparent margin may leave the screen. Zoom resizes the window around her feet.
let moveAim: { x: number; y: number } | null = null
let moveAt = 0
ipcMain.on('window:move-by', (_event, dx: number, dy: number, rect?: { x: number; y: number; w: number; h: number }) => {
  const now = Date.now()
  if (!moveAim || now - moveAt > 400) {
    const [x, y] = win.getPosition()
    moveAim = { x, y }
  }
  moveAt = now
  moveAim.x += Number(dx) || 0
  moveAim.y += Number(dy) || 0
  let nx = moveAim.x
  let ny = moveAim.y
  if (rect && Number.isFinite(rect.w) && Number.isFinite(rect.h)) {
    const wa = screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).workArea
    nx = Math.min(Math.max(nx, wa.x - rect.x), wa.x + wa.width - rect.x - rect.w)
    ny = Math.min(Math.max(ny, wa.y - rect.y), wa.y + wa.height - rect.y - rect.h)
  }
  win.setPosition(Math.round(nx), Math.round(ny))
})
ipcMain.on('window:zoom', (_event, zoom: number) => {
  const z = Math.min(1.3, Math.max(0.6, Number(zoom) || 1))
  const b = win.getBounds()
  const wa = screen.getDisplayMatching(b).workArea
  // width stays (room for the bubble); only the height she is fitted into scales (bubble 92 px + panel 100 px stay)
  const w = WIN_W
  const h = Math.min(Math.round(192 + (Math.min(WIN_H, wa.height - 24) - 192) * z), wa.height)
  win.setResizable(true)
  win.setBounds({ x: Math.round(b.x + (b.width - w) / 2), y: b.y + b.height - h, width: w, height: h })
  win.setResizable(false)
  moveAim = null
})
"""
TS_MAIN_OLD = """ipcMain.on('window:move-by', (_event, dx: number, dy: number) => {
  const [x, y] = win.getPosition()
  win.setPosition(Math.round(x + Number(dx)), Math.round(y + Number(dy)))
})
"""


def patch_ts(root: Path) -> None:
    src_dir = root / "src"
    # renderer
    p = src_dir / "renderer" / "main.ts"
    p.write_text(splice_renderer(p.read_text(encoding="utf-8"), "// ---- UI", ts=True), encoding="utf-8")
    # main
    p = src_dir / "main" / "index.ts"
    s = p.read_text(encoding="utf-8")
    if MARK in s:
        start = s.find("// " + MARK)
        end = s.find("ipcMain.handle('watch:toggle'", start)
        s = s[:start] + TS_MAIN + s[end:]
    else:
        assert s.count(TS_MAIN_OLD) == 1, "move-by handler not found in index.ts"
        s = s.replace(TS_MAIN_OLD, TS_MAIN)
    p.write_text(s, encoding="utf-8")
    # preload + api type
    p = src_dir / "preload" / "index.ts"
    s = p.read_text(encoding="utf-8")
    if "window:zoom" not in s:
        s = s.replace("moveBy: (dx, dy) => ipcRenderer.send('window:move-by', dx, dy),",
                      "moveBy: (dx, dy, rect) => ipcRenderer.send('window:move-by', dx, dy, rect),\n"
                      "  setZoom: (z) => ipcRenderer.send('window:zoom', z),")
        p.write_text(s, encoding="utf-8")
    p = src_dir / "shared" / "types.ts"
    s = p.read_text(encoding="utf-8")
    if "setZoom" not in s:
        s = s.replace("  moveBy(dx: number, dy: number): void",
                      "  moveBy(dx: number, dy: number, rect?: { x: number; y: number; w: number; h: number } | null): void\n"
                      "  /** [dots patch] window size factor, 0.6..1.3 */\n  setZoom?(zoom: number): void")
        p.write_text(s, encoding="utf-8")
    print(f"patched TS sources under {src_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("js", "ts"):
        print(__doc__)
        sys.exit(2)
    (patch_js if sys.argv[1] == "js" else patch_ts)(Path(sys.argv[2]))
