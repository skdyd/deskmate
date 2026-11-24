"""Deskmate patch: let her see ALL monitors, not just the primary one.

Every display is captured, scaled to one common height and stitched left-to-right (by screen position) into a
single JPEG whose total width is DESKMATE_CAPTURE_WIDTH (default 2048 px), so the vision cost stays close to the
original single 1280 px frame. The prompt tells the model how many monitors the picture shows.
Nothing is written to disk (the image only lives in memory and goes to the local Ollama over 127.0.0.1).

  python patch_multi_monitor.py ts  <deskmate-src>\\src\\main\\index.ts <deskmate-src>\\src\\main\\brain.ts
  python patch_multi_monitor.py js  <extracted out\\main\\index.js>
"""
import sys
from pathlib import Path

# ---------- shared JS body (works as TS too; types added in the TS variant) ----------
CAPTURE_BODY = r"""
	// [multi-monitor patch] capture every display and stitch them left to right into one picture.
	const displays = __ELECTRON__screen.getAllDisplays().slice().sort((a__T_D, b__T_D) => a.bounds.x - b.bounds.x || a.bounds.y - b.bounds.y);
	const maxWidth = Math.max(640, Number(process.env.DESKMATE_CAPTURE_WIDTH) || 2048);
	const aspectSum = displays.reduce((s__T_N, d__T_D) => s + d.size.width / d.size.height, 0) || 16 / 9;
	const rowHeight = Math.max(240, Math.round(maxWidth / aspectSum));
	const widest = displays.reduce((m__T_N, d__T_D) => Math.max(m, d.size.width / d.size.height), 16 / 9);
	win.setOpacity(0);
	try {
		const sources = await __ELECTRON__desktopCapturer.getSources({
			types: ["screen"],
			thumbnailSize: { width: Math.round(rowHeight * widest), height: rowHeight }
		});
		const shots__T_IMGS = [];
		for (const d of displays) {
			const s = sources.find((x) => x.display_id === String(d.id));
			if (s && !s.thumbnail.isEmpty()) shots.push(s.thumbnail);
		}
		// Some setups report no display_id: fall back to every screen source in the order given.
		if (!shots.length) for (const s of sources) if (!s.thumbnail.isEmpty()) shots.push(s.thumbnail);
		if (!shots.length) {
			console.warn(`[screen] capture came back empty (${sources.length} source(s)); Screen Recording permission is probably stale`);
			status("My eyes are off: screen capture returned nothing. System Settings → Privacy & Security → Screen Recording → switch Deskmate (or Electron) off and on, then restart me.");
			return;
		}
		const parts = shots.map((img) => (img.getSize().height === rowHeight ? img : img.resize({ height: rowHeight, quality: "good" })));
		let thumb = parts[0];
		if (parts.length > 1) {
			const sizes = parts.map((p) => p.getSize());
			const H = Math.max(...sizes.map((z) => z.height));
			const W = sizes.reduce((s__T_N, z) => s + z.width, 0);
			const out = Buffer.alloc(W * H * 4);
			let x0 = 0;
			parts.forEach((p, i) => {
				const w = sizes[i].width;
				const h = sizes[i].height;
				const src = p.toBitmap();
				const stride = Math.floor(src.length / h);
				for (let y = 0; y < h; y++) src.copy(out, (y * W + x0) * 4, y * stride, y * stride + w * 4);
				x0 += w;
			});
			thumb = __ELECTRON__nativeImage.createFromBitmap(out, { width: W, height: H });
		}
		const monitors = parts.length;
		const bmp = thumb.toBitmap();"""

# ---------- index.js (bundled) ----------
JS_OLD_HEAD = """	const display = electron.screen.getPrimaryDisplay();
	const width = 1280;
	const height = Math.round(display.size.height / display.size.width * width);
	win.setOpacity(0);
	try {
		const sources = await electron.desktopCapturer.getSources({
			types: ["screen"],
			thumbnailSize: {
				width,
				height
			}
		});
		const source = sources.find((s) => s.display_id === String(display.id)) ?? sources[0];
		if (!source || source.thumbnail.isEmpty()) {
			console.warn(`[screen] capture came back empty (${sources.length} source(s)); Screen Recording permission is probably stale`);
			status("My eyes are off: screen capture returned nothing. System Settings → Privacy & Security → Screen Recording → switch Deskmate (or Electron) off and on, then restart me.");
			return;
		}
		const bmp = source.thumbnail.toBitmap();"""
JS_OLD_TAIL = """		const jpeg = source.thumbnail.toJPEG(60);
		if (process.env.DESKMATE_DEBUG_SAVE_CAPTURE) (0, node_fs.writeFileSync)(process.env.DESKMATE_DEBUG_SAVE_CAPTURE, jpeg);
		return {
			data: jpeg.toString("base64"),
			mediaType: "image/jpeg"
		};"""
JS_NEW_TAIL = """		const jpeg = thumb.toJPEG(60);
		if (process.env.DESKMATE_DEBUG_SAVE_CAPTURE) (0, node_fs.writeFileSync)(process.env.DESKMATE_DEBUG_SAVE_CAPTURE, jpeg);
		if (process.env.DESKMATE_DEBUG_LOOK) console.log(`[screen] ${monitors} monitor(s) -> ${thumb.getSize().width}x${thumb.getSize().height}, ${jpeg.length} bytes`);
		return {
			data: jpeg.toString("base64"),
			mediaType: "image/jpeg",
			monitors
		};"""

PROMPT_OBSERVE_OLD = '" (screenshot attached)"'
PROMPT_OBSERVE_NEW = '(stimulus.screenshot.monitors > 1 ? ` (screenshot attached: ${stimulus.screenshot.monitors} monitors side by side, left to right)` : " (screenshot attached)")'
PROMPT_CHAT_OLD = "[A screenshot of their screen is attached for context."
PROMPT_CHAT_NEW = "[A screenshot of their screen${stimulus.screenshot.monitors > 1 ? `s (${stimulus.screenshot.monitors} monitors side by side, left to right)` : ''} is attached for context."


def js_body() -> str:
    body = CAPTURE_BODY.lstrip("\n")
    for tag in ("__T_D", "__T_N", "__T_IMGS"):
        body = body.replace(tag, "")
    return body.replace("__ELECTRON__", "electron.")


def ts_body() -> str:
    body = CAPTURE_BODY.lstrip("\n")
    body = body.replace("__T_D", ": Electron.Display").replace("__T_N", ": number").replace("__T_IMGS", ": Electron.NativeImage[]")
    body = body.replace("__ELECTRON__", "")
    # The TS source uses two-space indentation.
    return body.replace("\t", "  ")


def sub(text: str, old: str, new: str, what: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{what}: expected one match, found {text.count(old)}")
    return text.replace(old, new)


def patch_js(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "[multi-monitor patch]" in t:
        print("already patched")
        return
    t = sub(t, JS_OLD_HEAD, js_body(), "capture head")
    t = sub(t, JS_OLD_TAIL, JS_NEW_TAIL, "capture tail")
    t = sub(t, PROMPT_OBSERVE_OLD, PROMPT_OBSERVE_NEW, "observe prompt")
    t = sub(t, PROMPT_CHAT_OLD, PROMPT_CHAT_NEW, "chat prompt")
    path.write_text(t, encoding="utf-8")
    print(f"patched {path}")


TS_OLD_HEAD = """  const display = screen.getPrimaryDisplay()
  const width = 1280
  const height = Math.round((display.size.height / display.size.width) * width)
  win.setOpacity(0)
  try {
    const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width, height } })
    const source = sources.find((s) => s.display_id === String(display.id)) ?? sources[0]
    if (!source || source.thumbnail.isEmpty()) {
      // macOS says "granted" but hands back nothing after the app binary changed (dev reinstall, update):
      // the permission has to be toggled off and on again for this app.
      console.warn(`[screen] capture came back empty (${sources.length} source(s)); Screen Recording permission is probably stale`)
      status('My eyes are off: screen capture returned nothing. System Settings → Privacy & Security → Screen Recording → switch Deskmate (or Electron) off and on, then restart me.')
      return undefined
    }
    // A stale Screen Recording grant (after an app update or a dev reinstall) yields a black frame, not an error.
    const bmp = source.thumbnail.toBitmap()"""
TS_OLD_TAIL = """    const jpeg = source.thumbnail.toJPEG(60)
    if (process.env.DESKMATE_DEBUG_SAVE_CAPTURE) writeFileSync(process.env.DESKMATE_DEBUG_SAVE_CAPTURE, jpeg)
    return { data: jpeg.toString('base64'), mediaType: 'image/jpeg' }"""
TS_NEW_TAIL = """    const jpeg = thumb.toJPEG(60)
    if (process.env.DESKMATE_DEBUG_SAVE_CAPTURE) writeFileSync(process.env.DESKMATE_DEBUG_SAVE_CAPTURE, jpeg)
    if (process.env.DESKMATE_DEBUG_LOOK) console.log(`[screen] ${monitors} monitor(s) -> ${thumb.getSize().width}x${thumb.getSize().height}, ${jpeg.length} bytes`)
    return { data: jpeg.toString('base64'), mediaType: 'image/jpeg', monitors }"""
TS_TYPE_OLD = "  screenshot?: { data: string; mediaType: 'image/jpeg' | 'image/png' }"
TS_TYPE_NEW = "  screenshot?: { data: string; mediaType: 'image/jpeg' | 'image/png'; monitors?: number }"
TS_OBSERVE_OLD = "' (screenshot attached)'"
TS_OBSERVE_NEW = "((stimulus.screenshot.monitors ?? 1) > 1 ? ` (screenshot attached: ${stimulus.screenshot.monitors} monitors side by side, left to right)` : ' (screenshot attached)')"
TS_CHAT_NEW = "[A screenshot of their screen${(stimulus.screenshot.monitors ?? 1) > 1 ? `s (${stimulus.screenshot.monitors} monitors side by side, left to right)` : ''} is attached for context."


def patch_ts(index_ts: Path, brain_ts: Path) -> None:
    t = index_ts.read_text(encoding="utf-8")
    if "[multi-monitor patch]" not in t:
        t = sub(t, "/** One downscaled JPEG of the primary display.", "/** One downscaled JPEG of all displays side by side.", "doc")
        t = sub(t, TS_OLD_HEAD, ts_body().rstrip(), "ts head")
        t = sub(t, TS_OLD_TAIL, TS_NEW_TAIL, "ts tail")
        index_ts.write_text(t, encoding="utf-8")
    b = brain_ts.read_text(encoding="utf-8")
    if "monitors?: number" not in b:
        b = sub(b, TS_TYPE_OLD, TS_TYPE_NEW, "ts type")
        b = sub(b, TS_OBSERVE_OLD, TS_OBSERVE_NEW, "ts observe")
        b = sub(b, PROMPT_CHAT_OLD, TS_CHAT_NEW, "ts chat")
        brain_ts.write_text(b, encoding="utf-8")
    print("patched TS source")


if __name__ == "__main__":
    if sys.argv[1] == "js":
        patch_js(Path(sys.argv[2]))
    else:
        patch_ts(Path(sys.argv[2]), Path(sys.argv[3]))
