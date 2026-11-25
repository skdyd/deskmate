"""Write character.json + persona.md for the imported Live2D models (see import_live2d.py).
Persona and voice are copied from mika-tutor with the name swapped. Existing persona.md files are kept."""
import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root = Path(os.environ["APPDATA"]) / "deskmate" / "character"
base = json.loads((root / "mika-tutor" / "character.json").read_text(encoding="utf-8"))
persona = (root / "mika-tutor" / "persona.md").read_text(encoding="utf-8")
E = ["neutral", "happy", "flirty", "surprised", "annoyed", "angry", "sad", "smug", "shy"]
# id: (name, {emotion: expression name}, license note)
C = {
 "camellya": ("Camellya", dict(flirty="爱心眼", annoyed="黑脸", angry="黑脸", sad="哭", shy="脸红"), "booth 6313490 (shibutani), fan model of Wuthering Waves. No streaming/monetization/resale."),
 "sample0914": ("Hana", dict(happy="v", flirty="heart", annoyed="dark", angry="dark", sad="tear", smug="pero", shy="tere"), "booth free model, check its page"),
 "kitu": ("Kitu", dict(happy="Kirakira", flirty="Cute", surprised="Scared", annoyed="Angry", angry="Angry", smug="Cute", shy="Shy"), "booth free model"),
 "kitu-re": ("Kitu RE", dict(surprised="(Exp)OOFace", annoyed="(Exp)Sweat", angry="(Exp)Angry", sad="Frightened", smug="doya"), "booth free model"),
 "teto": ("Teto", dict(happy="star", flirty="heart", surprised="guruguru", annoyed="sweat", angry="sweat", sad="Tears"), "Kimochi-shiki Kasane Teto, see Readme in the archive"),
 "zero": ("Zero", {}, "booth free model"),
 "liveroid-y01": ("Liveroid Y01", dict(flirty="blush", annoyed="worried", sad="worried", smug="cool", shy="blush"), "LiveroiD (CROWN), see its terms"),
 "liveroid-y02": ("Liveroid Y02", dict(flirty="blush", annoyed="worried", sad="worried", smug="cool", shy="blush"), "LiveroiD (CROWN), see its terms"),
 "maomao": ("Maomao", dict(happy="星星", surprised="wenxiangyan", annoyed="liuhan", angry="shengqiqi", smug="舌头"), "booth free model"),
 "racoon": ("Racoon", {}, "booth free model"),
 "sparkle": ("Sparkle", {}, "fan model of Honkai: Star Rail, see instruction.txt"),
 "tubasa": ("Tubasa", {}, "booth free model"),
 "villhaze": ("Villhaze", {}, "booth free model"),
 "hakuko": ("Hakuko", {}, "Kamiya Hakuko free model, see Read Me & Terms of Use in the archive"),
 "fuwaka": ("Fuwaka", {}, "booth free model"),
 "lisette": ("Lisette", dict(flirty="shy", annoyed="angry", angry="angry", sad="sad", smug="tongue_out", shy="shy"), "see READ_ME.txt in the archive"),
 "mita": ("Mita", dict(happy="星星眼Star Eye", flirty="爱心love", surprised="抽象眼Funny eyes", annoyed="黑脸black face", angry="生气angry", shy="爱心love"), "fan model of MiSide"),
 "vivian": ("Vivian", dict(flirty="害羞", surprised="慌张", annoyed="白眼", angry="黑脸", sad="哭", shy="害羞"), "fan model of Zenless Zone Zero"),
 "jingliu": ("Jingliu", {}, "fan model of Honkai: Star Rail"),
 "changli": ("Changli", dict(flirty="爱心眼", annoyed="白眼", angry="生气", shy="脸红"), "fan model of Wuthering Waves (watermarked)"),
 "furina": ("Furina", dict(happy="XingXing", flirty="HaiXiu", surprised="0_0", annoyed="-_-", angry="HeiLian", smug="-_-", shy="HaiXiu"), "fan model of Genshin Impact"),
 "icegirl": ("Ice Girl", dict(happy="星星眼", flirty="爱心眼", surprised="惊讶", annoyed="白眼", angry="生气", sad="流泪", smug="歪嘴→", shy="脸红"), "booth free model (TianYeLuLu)"),
}
for cid, (name, emo, lic) in C.items():
    d = root / cid
    m3 = d / "model" / "model.model3.json"
    have = {e["Name"] for e in json.loads(m3.read_text(encoding="utf-8"))["FileReferences"].get("Expressions", [])}
    bad = [v for v in emo.values() if v not in have]
    if bad:
        print("MISSING", cid, bad)
    cfg = {
        "id": cid, "name": name,
        "model": m3.as_uri(),
        "note": "Imported from 'deskmate AI/live 2d' by tools/import_live2d.py. Persona copied from mika-tutor.",
        "license": lic,
        "expressions": {e: emo.get(e, "") for e in E},
        "motions": {"idle": "Idle", "react": "Idle"},
        "physics": {"sway": 1.0, "bounce": 1.3},
        "voice": base["voice"],
    }
    (d / "character.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    p = d / "persona.md"
    if not p.exists():
        p.write_text(persona.replace("You are Mika,", f"You are {name},", 1), encoding="utf-8")
    print("ok", cid, cfg["model"][:60])
