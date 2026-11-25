"""Import downloaded Live2D (VTube Studio style) models into deskmate characters.

For each archive in SRC: extract, find every .model3.json, copy the model into
%APPDATA%/deskmate/character/<id>/model/ with ASCII file names, and write a clean
model3.json (expressions listed, LipSync/EyeBlink groups, Idle motion group).
Writes a report (report.json) used to fill in character.json afterwards.

usage: python -I import_live2d.py <src dir> <staging dir>
"""
import json, os, re, shutil, struct, subprocess, sys, zipfile
from pathlib import Path

SEVEN = r"C:\Program Files\7-Zip\7z.exe"

# archive -> list of (id, display name, model3 path filter or None)
ARCHIVES = {
    "11月椿.zip": [("camellya", "Camellya", None)],
    "20220914_sample__2_.zip": [("sample0914", "Hana", None)],
    "KITU15.zip": [("kitu", "Kitu", None)],
    "KITU_RE23.zip": [("kitu-re", "Kitu RE", None)],
    "Kimochi-shiki_Kasane_Teto_v1.1.zip": [("teto", "Teto", None)],
    "L2DZero_V1.02.zip": [("zero", "Zero", None)],
    "LiveroiD_A_1.2.zip": [("liveroid-y01", "Liveroid Y01", "Y01"), ("liveroid-y02", "Liveroid Y02", "Y02")],
    "MAOMAO.zip": [("maomao", "Maomao", None)],
    "RACOON01.zip": [("racoon", "Racoon", None)],
    "Sparkle.zip": [("sparkle", "Sparkle", None)],
    "TUBASA_014.zip": [("tubasa", "Tubasa", None)],
    "Villhaze.zip": [("villhaze", "Villhaze", None)],
    "_FREE無料__live2dモデルlive2d_mode神宫白子Kamiyahakuko.zip": [("hakuko", "Hakuko", None)],
    "fuwaka.zip": [("fuwaka", "Fuwaka", None)],
    "lisette_v2.zip": [("lisette", "Lisette", None)],
    "little_mita.zip": [("mita", "Mita", None)],
    "薇薇安__3_.zip": [("vivian", "Vivian", None)],
    "镜流.zip": [("jingliu", "Jingliu", None)],
    # 镜流_Jingliu_.zip is the same model as 镜流.zip (identical moc3), skipped
    "长离带水印.zip": [("changli", "Changli", None)],
    "Furina.rar": [("furina", "Furina", None)],
    "IceGirl_Live2d.rar": [("icegirl", "Ice Girl", None)],
}


def decode_name(info: zipfile.ZipInfo, enc: str) -> str:
    if info.flag_bits & 0x800:
        return info.filename
    return info.filename.encode("cp437").decode(enc, "replace")


def choose_encoding(z: zipfile.ZipFile) -> str:
    """Pick the legacy name encoding under which the model3.json's own (UTF-8) references exist."""
    infos = z.infolist()
    for enc in ("utf-8", "gbk", "cp932"):
        try:
            names = [decode_name(i, enc).replace("\\", "/") if i.flag_bits & 0x800 else i.filename.encode("cp437").decode(enc).replace("\\", "/") for i in infos]
        except UnicodeDecodeError:
            continue
        ok = True
        for info, n in zip(infos, names):
            if n.endswith(".model3.json") and not n.startswith("__MACOSX"):
                try:
                    moc = json.loads(z.read(info).decode("utf-8-sig"))["FileReferences"]["Moc"]
                except Exception:
                    continue
                base = n.rsplit("/", 1)[0] + "/" if "/" in n else ""
                if (base + moc).replace("\\", "/") not in names:
                    ok = False
        if ok:
            return enc
    return "gbk"


def extract(archive: Path, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            enc = choose_encoding(z)
            for info in z.infolist():
                name = decode_name(info, enc).replace("\\", "/")
                if name.startswith("__MACOSX") or name.endswith("/"):
                    continue
                parts = [p for p in name.split("/") if p not in ("", ".", "..")]
                out = dest.joinpath(*parts)
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    else:
        subprocess.run([SEVEN, "x", "-y", f"-o{dest}", str(archive)], check=True, stdout=subprocess.DEVNULL)


def png_size(p: Path):
    with open(p, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def find_param(moc: bytes, candidates):
    for c in candidates:
        if c.encode() + b"\x00" in moc:
            return c
    return None


def import_model(model3: Path, cid: str, name: str, out_root: Path):
    src_dir = model3.parent
    m = json.loads(model3.read_text(encoding="utf-8-sig"))
    fr = m.get("FileReferences", {})
    dest = out_root / cid / "model"
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "textures").mkdir(parents=True)
    (dest / "exp").mkdir()
    (dest / "motions").mkdir()

    new = {"Version": 3, "FileReferences": {}}
    nfr = new["FileReferences"]

    shutil.copy2(src_dir / fr["Moc"], dest / "model.moc3")
    nfr["Moc"] = "model.moc3"
    moc = (dest / "model.moc3").read_bytes()

    tex = []
    sizes = []
    for i, t in enumerate(fr.get("Textures", [])):
        n = f"textures/texture_{i:02d}.png"
        shutil.copy2(src_dir / t, dest / n)
        tex.append(n)
        sizes.append(png_size(dest / n))
    nfr["Textures"] = tex

    for key, fname in (("Physics", "model.physics3.json"), ("Pose", "model.pose3.json"), ("DisplayInfo", "model.cdi3.json")):
        if fr.get(key) and (src_dir / fr[key]).exists():
            shutil.copy2(src_dir / fr[key], dest / fname)
            nfr[key] = fname

    # expressions: listed ones first, then any other exp3.json in the folder tree
    exps = []
    seen = set()
    for e in fr.get("Expressions", []) or []:
        p = (src_dir / e["File"]).resolve()
        if p.exists():
            exps.append((e["Name"], p))
            seen.add(p)
    for p in sorted(src_dir.rglob("*.exp3.json")):
        if p.resolve() not in seen:
            exps.append((p.name[: -len(".exp3.json")], p.resolve()))
            seen.add(p.resolve())
    nexp = []
    used = set()
    for i, (ename, p) in enumerate(exps):
        n = f"exp/exp_{i:02d}.exp3.json"
        shutil.copy2(p, dest / n)
        en = ename
        k = 2
        while en in used:
            en = f"{ename}_{k}"
            k += 1
        used.add(en)
        nexp.append({"Name": en, "File": n})
    if nexp:
        nfr["Expressions"] = nexp

    # motions: keep listed groups; unlisted clips go to group "Extra"
    motions = {}
    seenm = set()
    i = 0
    for group, items in (fr.get("Motions") or {}).items():
        for it in items:
            p = (src_dir / it["File"]).resolve()
            if not p.exists():
                continue
            n = f"motions/motion_{i:02d}.motion3.json"
            i += 1
            shutil.copy2(p, dest / n)
            motions.setdefault(group, []).append({**it, "File": n})
            seenm.add(p)
    for p in sorted(src_dir.rglob("*.motion3.json")):
        if p.resolve() in seenm:
            continue
        n = f"motions/motion_{i:02d}.motion3.json"
        i += 1
        shutil.copy2(p, dest / n)
        motions.setdefault("Extra", []).append({"File": n, "_orig": p.name})
        seenm.add(p.resolve())
    motions.setdefault("Idle", [])
    for items in motions.values():
        for it in items:
            it.pop("_orig", None)
    nfr["Motions"] = motions

    mouth = find_param(moc, ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y", "ParamMouthOpen"])
    eyes = [p for p in (find_param(moc, ["ParamEyeLOpen", "PARAM_EYE_L_OPEN"]), find_param(moc, ["ParamEyeROpen", "PARAM_EYE_R_OPEN"])) if p]
    groups = [g for g in m.get("Groups", []) if g.get("Name") not in ("LipSync", "EyeBlink")]
    if eyes:
        groups.append({"Target": "Parameter", "Name": "EyeBlink", "Ids": eyes})
    if mouth:
        groups.append({"Target": "Parameter", "Name": "LipSync", "Ids": [mouth]})
    new["Groups"] = groups
    if m.get("HitAreas"):
        new["HitAreas"] = m["HitAreas"]
    if m.get("Layout"):
        new["Layout"] = m["Layout"]

    (dest / "model.model3.json").write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")

    extra = [p.name for p in src_dir.iterdir() if p.suffix.lower() in (".txt", ".md")]
    return {
        "id": cid,
        "name": name,
        "source": str(model3),
        "expressions": [e["Name"] for e in nexp],
        "motion_groups": {g: len(v) for g, v in motions.items()},
        "mouth": mouth,
        "eyes": eyes,
        "textures": sizes,
        "readme": extra,
        "size_mb": round(sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1e6, 1),
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    src, staging = Path(sys.argv[1]), Path(sys.argv[2])
    out_root = Path(os.environ["APPDATA"]) / "deskmate" / "character"
    report = []
    for arc, entries in ARCHIVES.items():
        ap = src / arc
        if not ap.exists():
            report.append({"archive": arc, "error": "missing"})
            continue
        ex = staging / re.sub(r"[^\w.-]", "_", ap.stem)
        try:
            extract(ap, ex)
            models = sorted(ex.rglob("*.model3.json"))
            for cid, name, filt in entries:
                cands = [p for p in models if (filt is None or filt in str(p))]
                if not cands:
                    report.append({"archive": arc, "id": cid, "error": "no model3.json"})
                    continue
                r = import_model(cands[0], cid, name, out_root)
                r["archive"] = arc
                r["other_models"] = [str(p.relative_to(ex)) for p in models if p != cands[0]]
                report.append(r)
                print("ok", cid, r["mouth"], len(r["expressions"]), r["textures"])
        except Exception as e:  # keep going
            report.append({"archive": arc, "error": repr(e)})
            print("FAIL", arc, e)
    (staging / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
