"""[accessories patch] a "소품" dropdown next to the character dropdown lists the Live2D model's own expressions
(the model author's toggles: apron, glasses, hair variants...); picking one turns it on/off. They are applied every frame
on top of motions and emotion expressions, and remembered per character (localStorage deskmate.acc.<id>).
Hidden for models without expressions (and for non-Live2D renderers).
usage: python patch_accessories.py <app.asar>   (re-runnable)"""
import re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1])
MARK = "[accessories patch]"

L2D = [
    ("				if (fakeMouth > 0) core.setParameterValueById(\"ParamMouthOpenY\", fakeMouth);\n",
     "				if (fakeMouth > 0) core.setParameterValueById(\"ParamMouthOpenY\", fakeMouth);\n"
     "				for (const a of accOn) for (const p of a.params) { // [accessories patch]\n"
     "					if (p.Blend === \"Overwrite\") core.setParameterValueById(p.Id, p.Value);\n"
     "					else if (p.Blend === \"Multiply\") core.multiplyParameterValueById(p.Id, p.Value);\n"
     "					else core.setParameterValueById(p.Id, core.getParameterDefaultValue(core.getParameterIndex(p.Id)) + p.Value);\n"
     "				}\n"),
    ("		setFakeMouth(v) {\n",
     "		async accessories() { // [accessories patch] the model's expressions, with their parameter lists\n"
     "			if (!model) return [];\n"
     "			const s = model.internalModel.settings;\n"
     "			const out = [];\n"
     "			for (const e of s.expressions ?? []) {\n"
     "				try {\n"
     "					const j = await (await fetch(s.resolveURL(e.File))).json();\n"
     "					if (j.DeskmateHidden) continue; // checked: no visible effect in this model\n"
     "					out.push({ name: e.Name, params: (j.Parameters ?? []).map((p) => ({ ...p, Value: Number(p.Value) })).filter((p) => Number.isFinite(p.Value)) });\n"
     "				} catch (err) { console.warn(\"[accessories]\", e.File, err); }\n"
     "			}\n"
     "			return out;\n"
     "		},\n"
     "		setAccessories(list) {\n"
     "			// turned-off ones go back to their default (the runtime keeps the last frame's values otherwise)\n"
     "			const core = model?.internalModel.coreModel;\n"
     "			if (core) for (const a of accOn) if (!list.includes(a)) for (const p of a.params) {\n"
     "				const i = core.getParameterIndex(p.Id);\n"
     "				if (i < 0) continue;\n"
     "				const d = core.getParameterDefaultValue(i);\n"
     "				core.setParameterValueByIndex(i, d);\n"
     "				if (core._savedParameters) core._savedParameters[i] = d;\n"
     "			}\n"
     "			accOn = list;\n"
     "		},\n"
     "		setFakeMouth(v) {\n"),
    ("	let fakeMouth = 0;\n", "	let fakeMouth = 0;\n	let accOn = []; // [accessories patch]\n"),
]
IDX = [
    ("	wirePointer();\n", """	wirePointer();
	// [accessories patch] "소품" dropdown: the model's own toggles, on/off per character
	try {
		const accs = await avatar.accessories?.() ?? [];
		if (accs.length) {
			const ACC_KEY = "deskmate.acc." + config.character.id;
			const on = new Set(JSON.parse(localStorage.getItem(ACC_KEY) || "[]"));
			const sel = document.createElement("select");
			sel.id = "acc";
			sel.title = "소품 켜기/끄기 (고르면 켜지고, 다시 고르면 꺼짐)";
			const st = document.createElement("style");
			st.textContent = "#acc { font-size: 11px; padding: 2px 4px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.08); color: var(--ink); outline: none; max-width: 84px; }";
			document.head.appendChild(st);
			const draw = () => {
				sel.innerHTML = "";
				const head = document.createElement("option");
				head.value = "";
				head.textContent = on.size ? `소품 ${on.size}` : "소품";
				sel.appendChild(head);
				for (const a of accs) {
					const o = document.createElement("option");
					o.value = a.name;
					o.textContent = (on.has(a.name) ? "✓ " : "　") + a.name;
					sel.appendChild(o);
				}
				sel.value = "";
			};
			const apply = () => {
				avatar.setAccessories(accs.filter((a) => on.has(a.name)));
				localStorage.setItem(ACC_KEY, JSON.stringify([...on].filter((n) => accs.some((a) => a.name === n))));
			};
			sel.addEventListener("change", () => {
				const n = sel.value;
				if (n) on.has(n) ? on.delete(n) : on.add(n);
				apply();
				draw();
			});
			draw();
			apply();
			characterSelect.insertAdjacentElement("afterend", sel);
		}
	} catch (err) {
		console.warn("[accessories]", err);
	}
"""),
]
_r, header, _b = asar_tool.read(asar)
paths = [p for p, _n in asar_tool.walk(header)]
pick = lambda pat: [p for p in paths if re.match(pat, p)][0]
bak = asar.with_name("app.asar.bak-accessories")
if not bak.exists():
    shutil.copy2(asar, bak)
tmp = Path(tempfile.mkdtemp())
for inner, edits in ((pick(r"out/renderer/assets/live2d-.*\.js$"), L2D), (pick(r"out/renderer/assets/index-.*\.js$"), IDX)):
    f = tmp / Path(inner).name
    asar_tool.cmd_get(asar, inner, f)
    s = f.read_bytes().decode("utf-8")
    if MARK in s:
        print("already patched", inner); continue
    for a, b in edits:
        if s.count(a) != 1:
            raise SystemExit(f"anchor not found once in {inner}: {a[:60]!r}")
        s = s.replace(a, b)
    f.write_bytes(s.encode("utf-8"))
    asar_tool.cmd_replace(asar, inner, f)
    print("patched", inner)
