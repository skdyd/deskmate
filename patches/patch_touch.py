"""[touch patch] richer touch reactions.
renderer: 14 touch areas from height + left/right position (character.json "touchLayout": "chibi" for big-head models),
  gestures tap / rapid (3+ taps, sent once) / stroke (rubbing back and forth) / hold (long press) / drag,
  an instant expression per area+gesture.
main: the line for her brain comes from %APPDATA%/deskmate/touch-prompts.json (read on every touch, so edits apply
  at once): area wording, gesture templates, extra notes per area, random style nudges, an "annoyed" note after many
  touches in 90 s, and her last few touch lines so she does not repeat herself.
usage: python patch_touch.py <app.asar>   (re-runnable)"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
MARK = "[touch patch]"

MAIN = [
    ('return `[${t.kind === "drag" ? "They grabbed you, dragged you around the screen for a moment, and put you down somewhere else." : TOUCH_PROMPTS[t.area]}] React out loud in one short line.`;',
     'return touchPrompt(t); // [touch patch]'),
    ("var lastTouchAt = 0;\n", r"""var lastTouchAt = 0;
// [touch patch] the touch line comes from touch-prompts.json in userData (editable, read on every touch)
var touchTimes = [];
var lastTouchLines = [];
function touchPrompt(t) {
	let cfg = {};
	try {
		cfg = JSON.parse((0, node_fs.readFileSync)((0, node_path.join)(USER_DATA, "touch-prompts.json"), "utf8"));
	} catch (err) {
		console.warn("[touch] touch-prompts.json:", err.message);
	}
	const pick = (v) => Array.isArray(v) ? v[Math.floor(Math.random() * v.length)] : v;
	const areaText = pick(cfg.areas?.[t.area]) ?? `your ${t.area}`;
	const fallback = { tap: "They just poked {area}.", rapid: "They poked {area} {count} times in a row.", stroke: "They are gently stroking {area}.", hold: "They pressed on {area} and kept holding it.", drag: "They grabbed you, dragged you around the screen for a moment, and put you down somewhere else." };
	const line = String(pick(cfg.gestures?.[t.kind]) ?? fallback[t.kind] ?? fallback.tap).replaceAll("{area}", areaText).replaceAll("{count}", String(t.count ?? 1));
	const now = Date.now();
	touchTimes = touchTimes.filter((x) => now - x < 9e4);
	touchTimes.push(now);
	const extra = [];
	if (cfg.areaNotes?.[t.area]) extra.push(pick(cfg.areaNotes[t.area]));
	if (touchTimes.length >= (cfg.annoyedAfter ?? 5)) extra.push(String(pick(cfg.annoyed) ?? "They keep touching you ({n} times in the last minute or so). Let it show.").replaceAll("{n}", String(touchTimes.length)));
	if (cfg.styles?.length) extra.push(pick(cfg.styles));
	if (lastTouchLines.length) extra.push(`Say something new; do not repeat or echo your recent lines: ${lastTouchLines.map((s) => JSON.stringify(s)).join(" / ")}.`);
	return `[${line}] ${extra.join(" ")} React out loud in one short line.`;
}
"""),
    ("""		await deliver(await brain.respond({
			kind: "touch",
			touch
		}), "touch");""",
     """		const reply = await brain.respond({
			kind: "touch",
			touch
		});
		if (reply?.say) lastTouchLines = [...lastTouchLines, reply.say].slice(-4); // [touch patch]
		await deliver(reply, "touch");"""),
    ("	if (touching || now - lastTouchAt < 2500) return;", "	if (touching || now - lastTouchAt < 1500) return; // [touch patch] 2.5 s -> 1.5 s (taps are batched in the renderer)"),
]

L2D = [("		setExpression(emotion) {\n", "		fullBounds() { // [touch patch] the whole model, also in the upper-body view\n			if (!model) return null;\n			const b = model.getBounds();\n			return { x: b.x, y: b.y, width: b.width, height: b.height };\n		},\n		setExpression(emotion) {\n")]

OLD_AREA = """function touchArea(y) {
	const b = avatar?.getBounds();
	if (!b) return "body";
	const rel = (y - b.y) / Math.max(1, b.height);
	if (rel < .22) return "head";
	if (rel < .42) return "chest";
	if (rel < .62) return "body";
	return "legs";
}"""
NEW_AREA = """function touchArea(x, y) { // [touch patch] height + distance from her centre line, relative to her height
	const b = avatar?.fullBounds?.() ?? avatar?.getBounds();
	if (!b) return "belly";
	const H = Math.max(1, b.height);
	const ry = (y - b.y) / H;
	const rx = Math.abs(x - (b.x + b.width / 2)) / H;
	if (config?.character?.touchLayout === "chibi") {
		if (ry < .12) return "head";
		if (ry < .45) return rx < .08 ? "face" : rx < .16 ? "cheek" : "hair";
		if (ry < .62) return rx > .12 ? "hand" : "chest";
		if (ry < .75) return "belly";
		if (ry < .86) return "legs";
		return "feet";
	}
	if (ry < .1) return "head";
	if (ry < .19) return rx < .035 ? "face" : rx < .065 ? "cheek" : "hair";
	if (ry < .24) return rx > .07 ? "shoulder" : "neck";
	if (ry < .4) return rx > .09 ? "arm" : "chest";
	if (ry < .56) return rx > .09 ? "hand" : "belly";
	if (ry < .66) return "hips";
	if (ry < .86) return "legs";
	return "feet";
}
/** Instant face for a touch, before her line arrives. */
function touchFace(kind, area) {
	const pick = (a) => a[Math.floor(Math.random() * a.length)];
	if (kind === "stroke") return pick(["happy", "shy", "flirty"]);
	if (kind === "hold") return pick(["surprised", "shy", "annoyed"]);
	if (kind === "rapid") return pick(["annoyed", "angry", "surprised"]);
	if (area === "head" || area === "hair") return pick(["happy", "shy"]);
	if (area === "face" || area === "cheek" || area === "neck") return pick(["shy", "surprised", "flirty"]);
	if (area === "chest" || area === "hips") return pick(["surprised", "shy", "angry"]);
	if (area === "hand" || area === "arm" || area === "shoulder") return pick(["happy", "flirty", "surprised"]);
	return pick(["surprised", "flirty", "smug"]);
}
const tapChain = { count: 0, area: "belly", timer: 0 };
function touchGesture(kind, area) {
	avatar?.kick(kind === "stroke" ? .4 : kind === "hold" ? .6 : 1.2);
	avatar?.setExpression(touchFace(tapChain.count >= 2 && kind === "tap" ? "rapid" : kind, area));
	if (kind === "tap") {
		// taps close together are one reaction: "tap" or "rapid" with the count, sent when the taps stop
		tapChain.count++;
		tapChain.area = area;
		clearTimeout(tapChain.timer);
		tapChain.timer = setTimeout(() => {
			const count = tapChain.count;
			tapChain.count = 0;
			api.react({ kind: count >= 3 ? "rapid" : "tap", area: tapChain.area, count });
		}, 650);
		return;
	}
	api.react({ kind, area });
}"""
IDX = [
    (OLD_AREA, NEW_AREA),
    ('			area: mode === "move" ? "body" : touchArea(e.clientY),\n',
     '			area: mode === "move" ? "body" : touchArea(e.clientX, e.clientY),\n			t0: performance.now(),\n			turns: 0,\n			sx: 0,\n'),
    ("		drag.moved += Math.hypot(dx, dy);\n",
     "		drag.moved += Math.hypot(dx, dy);\n		if (drag.mode === \"tap\" && Math.abs(dx) > 1) { // [touch patch] count back-and-forth for stroking\n			const s = Math.sign(dx);\n			if (drag.sx && s !== drag.sx) drag.turns++;\n			drag.sx = s;\n		}\n"),
    ("""		} else if (d.moved <= 6) {
			avatar?.kick(1.2);
			const quick = d.area === "head" ? ["happy", "shy"] : d.area === "chest" ? [
				"surprised",
				"shy",
				"angry"
			] : ["surprised", "flirty"];
			avatar?.setExpression(quick[Math.floor(Math.random() * quick.length)]);
			api.react({
				kind: "tap",
				area: d.area
			});
		}""",
     """		} else {
			// [touch patch] tap / stroke (rubbing back and forth) / hold (long press)
			const held = performance.now() - d.t0;
			if (d.moved > 25 && d.turns >= 2) touchGesture("stroke", d.area);
			else if (d.moved <= 6) touchGesture(held > 700 ? "hold" : "tap", d.area);
		}"""),
]

_r, header, _b = asar_tool.read(asar)
paths = [p for p, _n in asar_tool.walk(header)]
pick = lambda pat: [p for p in paths if re.match(pat, p)][0]
bak = asar.with_name("app.asar.bak-touch")
if not bak.exists():
    shutil.copy2(asar, bak)
tmp = Path(tempfile.mkdtemp())
for inner, edits in (("out/main/index.js", MAIN), (pick(r"out/renderer/assets/live2d-.*\.js$"), L2D), (pick(r"out/renderer/assets/index-.*\.js$"), IDX)):
    f = tmp / Path(inner).name
    asar_tool.cmd_get(asar, inner, f)
    s = f.read_bytes().decode("utf-8")
    if MARK in s:
        print("already patched", inner); continue
    for a, b in edits:
        if s.count(a) != 1:
            raise SystemExit(f"anchor not found once in {inner}: {a[:70]!r}")
        s = s.replace(a, b)
    f.write_bytes(s.encode("utf-8"))
    asar_tool.cmd_replace(asar, inner, f)
    print("patched", inner)
