"""Deskmate patch: a separate English check after each chat reply (local Ollama brain only).

The 4B model does not correct the user while it is also chatting, so after the normal reply a second short call
asks the same model only "is there a real mistake in this message?" (JSON: has_mistake, correction) and the
correction sentence is appended to what she says. It runs only for typed/spoken chat that has Latin letters and
no Hangul. The correction is added after the turn is written to memory, so her own past lines stay clean and
she does not start imitating corrections. Takes about 0.3 s on the RX 9070 XT.
Turn off with DESKMATE_GRAMMAR_CHECK=0 in %APPDATA%\\deskmate\\.env.

  python patch_grammar_check.py js <extracted out\\main\\index.js>
"""
import sys
from pathlib import Path

JS_OLD = """		reply.say = trimSpoken(reply.say, stimulus.kind === "task" || stimulus.page ? 5 : helpAsked ? 8 : 3);
		this.commit(stimulus, reply);
		return reply;
	}"""

JS_NEW = """		reply.say = trimSpoken(reply.say, stimulus.kind === "task" || stimulus.page ? 5 : helpAsked ? 8 : 3);
		this.commit(stimulus, reply);
		// [grammar-check patch] separate English check, appended after the turn is stored in memory.
		const userText = (stimulus.text ?? "").trim();
		if (stimulus.kind === "chat" && process.env.DESKMATE_GRAMMAR_CHECK !== "0" && /[A-Za-z]{2}/.test(userText) && !/[\\u3131-\\u318E\\uAC00-\\uD7A3]/.test(userText) && userText.length <= 400) {
			try {
				const t0 = Date.now();
				const raw = await ollamaChat({
					model: this.ollamaModel,
					messages: [{ role: "system", content: GRAMMAR_CHECK_PROMPT }, { role: "user", content: userText }],
					schema: GRAMMAR_CHECK_SCHEMA,
					numPredict: 120,
					temperature: .2
				});
				const obj = JSON.parse(raw.trim().replace(/^```(?:json)?\\s*/i, "").replace(/\\s*```$/, ""));
				const fix = typeof obj.correction === "string" ? obj.correction.trim() : "";
				if (obj.has_mistake === true && fix && !/[\\u3131-\\u318E\\uAC00-\\uD7A3]/.test(fix)) {
					reply.say = `${reply.say} ${trimSpoken(fix, 2)}`.trim();
					reply.speak = true;
				}
				console.log(`[grammar] ${Date.now() - t0} ms, mistake=${obj.has_mistake === true}${fix ? `: ${fix.slice(0, 120)}` : ""}`);
			} catch (err) {
				console.warn("[grammar] check failed:", err instanceof Error ? err.message : err);
			}
		}
		return reply;
	}"""

JS_DEFS_ANCHOR = "function trimSpoken(say, maxSentences) {"
JS_DEFS = """// [grammar-check patch] prompt and schema for the separate English check.
const GRAMMAR_CHECK_PROMPT = `You check the English of a Korean learner who is chatting by voice. Look at their message only.
A real mistake is: wrong grammar (verb tense, verb form, agreement, missing or wrong article or preposition), a wrong word (a word that means something else, like 'boring' for 'bored'), or a phrase no native speaker would say.
Ignore capital letters, punctuation, spelling typos, filler words, slang and casual short forms. If the message is fine or not in English, has_mistake is false and correction is "".
If there is a mistake, write correction as one or two short, friendly spoken English sentences: give the natural way to say it and the quick reason in plain words, no grammar terms. Only the most important mistake. Example: "Oh, we say 'I feel bored', not 'boring'. 'Boring' is for things that make you bored."
Never use Korean.`;
const GRAMMAR_CHECK_SCHEMA = {
	type: "object",
	properties: { has_mistake: { type: "boolean" }, correction: { type: "string" } },
	required: ["has_mistake", "correction"]
};
function trimSpoken(say, maxSentences) {"""


def patch_js(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    if "[grammar-check patch]" in src:
        print("already patched")
        return
    for old, label in ((JS_OLD, "respondLocal tail"), (JS_DEFS_ANCHOR, "trimSpoken")):
        n = src.count(old)
        if n != 1:
            sys.exit(f"{label}: expected one match, found {n}; not patching")
    src = src.replace(JS_OLD, JS_NEW).replace(JS_DEFS_ANCHOR, JS_DEFS)
    path.write_text(src, encoding="utf-8")
    print(f"patched {path}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "js":
        sys.exit(__doc__)
    patch_js(Path(sys.argv[2]))
