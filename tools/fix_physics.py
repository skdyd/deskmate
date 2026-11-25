"""Remove physics settings that overwrite the head/body tracking parameters the app drives.

Some VTube Studio rigs (Sparkle, Mita) smooth tracking through physics: an input like Param169 or ParamAngleXIN feeds
an output ParamAngleX. The app writes ParamAngleX directly, the physics then overwrites it from the unused input, so
the head never follows the mouse and taps do not move her. Dropping those settings lets the app's values through.

usage: python -I fix_physics.py <model.physics3.json> [param ...]   (default params: ParamAngleX/Y/Z, ParamBodyAngleX/Y/Z)
"""
import json, shutil, sys
from pathlib import Path

path = Path(sys.argv[1])
targets = set(sys.argv[2:]) or {"ParamAngleX", "ParamAngleY", "ParamAngleZ", "ParamBodyAngleX", "ParamBodyAngleY", "ParamBodyAngleZ"}
backup = path.with_name(path.name + ".orig")
if not backup.exists():
    shutil.copy2(path, backup)
p = json.loads(backup.read_text(encoding="utf-8-sig"))
keep, drop = [], []
for s in p["PhysicsSettings"]:
    # only drop settings whose inputs are not themselves the targets (ParamAngleX -> ParamBodyAngleX is a normal chain)
    outs = {o["Destination"]["Id"] for o in s["Output"]}
    ins = {i["Source"]["Id"] for i in s["Input"]}
    if outs & targets and not ins & targets:
        drop.append(s)
    else:
        keep.append(s)
p["PhysicsSettings"] = keep
ids = {s["Id"] for s in drop}
meta = p["Meta"]
meta["PhysicsSettingCount"] = len(keep)
meta["TotalInputCount"] = sum(len(s["Input"]) for s in keep)
meta["TotalOutputCount"] = sum(len(s["Output"]) for s in keep)
meta["VertexCount"] = sum(len(s["Vertices"]) for s in keep)
if "PhysicsDictionary" in meta:
    meta["PhysicsDictionary"] = [d for d in meta["PhysicsDictionary"] if d["Id"] not in ids]
path.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
print(path, "dropped", len(drop), [sorted({o["Destination"]["Id"] for o in s["Output"]} & targets) for s in drop])
