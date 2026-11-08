"""Small art-directed grammars. They plan scenes; only Aseprite renders pixels."""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sys
from pathlib import Path


def load_profile(path: str | Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "profiles/cozy-rpg.json"
        if not path.is_file():
            path = Path(sys.prefix) / "share/aseprite-gen/profiles/cozy-rpg.json"
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    if profile.get("schema_version") != 2:
        raise ValueError("Use style profile schema 2; historical scene JSON remains renderable")
    for key, minimum in [("foliage", 8), ("tree_foliage", 8), ("autumn", 8), ("wood", 8), ("barrel_wood", 8), ("metal", 4), ("berries", 3)]:
        ramp = profile.get("palette", {}).get(key, [])
        if len(ramp) < minimum or any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in ramp):
            raise ValueError(f"Invalid {key} material ramp")
    try:
        for kind in ("bush", "tree", "barrel"):
            geometry=profile["geometry"][kind]
            canvas=geometry["canvas"]
            if len(canvas)!=2 or any(type(v) is not int or not 24<=v<=256 for v in canvas):
                raise ValueError("Invalid profile canvas")
            if kind!="barrel":
                crown=geometry["crown"]
                if len(crown)!=4 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in crown):
                    raise ValueError("Invalid crown geometry")
        leaf=profile["leaf_clusters"]
        if not 2.5<=leaf["spacing"]<=6:
            raise ValueError("Leaf spacing must be 2.5..6 native pixels")
        for field in ("width","length"):
            low,high=leaf[field]
            if type(low) is not int or type(high) is not int or not 3<=low<=high<=9:
                raise ValueError("Invalid leaf size range")
    except (KeyError,TypeError) as error:
        raise ValueError("Profile requires geometry and leaf-cluster settings") from error
    return profile


def parse_prompt(prompt: str, kind: str | None = None) -> dict:
    text = prompt.casefold()
    candidates = {"bush": ("bush", "shrub", "куст"), "tree": ("tree", "oak", "дерев", "дуб"),
                  "barrel": ("barrel", "cask", "боч")}
    if kind is None:
        # Wood adjectives must not accidentally make a barrel into a tree.
        found = [k for k, words in candidates.items() if any(w in text for w in words)]
        if "barrel" in found:
            found = ["barrel"]
        if len(found) != 1:
            raise ValueError("Describe one bush, tree or barrel (куст, дерево, бочка), or set --kind")
        kind = found[0]
    if kind not in candidates:
        raise ValueError("Supported preset kinds: bush, tree, barrel. Use scene JSON for other shapes.")
    return {"kind": kind, "autumn": any(w in text for w in ("autumn", "fall", "осенн")),
            "berries": any(w in text for w in ("berry", "berries", "ягод")),
            "young": any(w in text for w in ("young", "sapling", "молод")),
            "weathered": any(w in text for w in ("weathered", "old", "стар", "worn")),
            "prompt": prompt,
            "interpretation": "Bounded procedural grammar; only listed modifiers affect geometry. Codex can author arbitrary scene operations."}


class Scene:
    def __init__(self, width, height, base, palette):
        self.width, self.height = width, height
        self.scale = min(width / base[0], height / base[1])
        self.ox, self.oy = (width - base[0] * self.scale) / 2, (height - base[1] * self.scale) / 2
        self.layers, self.palette = [], palette
        self.ops = []

    def layer(self, name):
        self.ops = []
        self.layers.append({"name": name, "operations": self.ops})

    def point(self, x, y):
        return [min(self.width-1, max(0, round(self.ox + x*self.scale))),
                min(self.height-1, max(0, round(self.oy + y*self.scale)))]

    def poly(self, points, color):
        self.ops.append({"op": "polygon", "color": color, "points": [self.point(x,y) for x,y in points]})

    def rect(self, x, y, w, h, color):
        a, b = self.point(x,y), self.point(x+w-1,y+h-1)
        self.ops.append({"op": "rect", "color": color, "x": a[0], "y": a[1], "w": b[0]-a[0]+1, "h": b[1]-a[1]+1})

    def line(self, x, y, x2, y2, color):
        a, b = self.point(x,y), self.point(x2,y2)
        self.ops.append({"op": "line", "color": color, "x": a[0], "y": a[1], "x2": b[0], "y2": b[1]})

    def ellipse(self, x, y, w, h, color):
        self.rect(x,y,w,h,color)
        self.ops[-1]["op"] = "ellipse"

    def export(self):
        return {"width": self.width, "height": self.height, "palette": self.palette, "layers": self.layers}



def plan(prompt: str, *, kind=None, width=None, height=None, seed=0, profile=None, detail=True):
    from . import drawing
    spec=parse_prompt(prompt,kind)
    p=load_profile(profile)
    base=p["geometry"][spec["kind"]]["canvas"]
    width,height=base[0] if width is None else width,base[1] if height is None else height
    if not (24 <= width <= 256 and 24 <= height <= 256):
        raise ValueError("Preset canvases must be between 24 and 256 pixels per axis")
    palette=list(dict.fromkeys(c for ramp in p["palette"].values() for c in ramp))
    s=Scene(width,height,base,palette)
    getattr(drawing,spec["kind"])(s,p,random.Random(seed),spec,detail)
    scene=s.export()
    used={op["color"] for layer in scene["layers"] for op in layer["operations"]}
    scene["palette"]=[c for c in palette if c in used]
    metadata={"schema_version":1,"spec":spec,"seed":seed,"style":p["id"],"profile_revision":p["revision"],
              "profile_sha256":hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest(),
              "construction":p["construction"][spec["kind"]],"detail":detail,"visual_review":"pending",
              "algorithm":"overlapping pointed leaves and projected convex staves"}
    return scene,metadata
