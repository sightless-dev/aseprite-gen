"""Small art-directed grammars. They plan scenes; only Aseprite renders pixels."""
from __future__ import annotations

import hashlib
import json
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
    if profile.get("schema_version") != 1:
        raise ValueError("Unsupported style profile schema")
    for key, minimum in [("foliage", 6), ("autumn", 6), ("wood", 6), ("metal", 4), ("berries", 3)]:
        ramp = profile.get("palette", {}).get(key, [])
        if len(ramp) < minimum or any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in ramp):
            raise ValueError(f"Invalid {key} material ramp")
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


def leaf(s, x, y, size, dark, mid, light, highlight=True):
    """One connected, tapered leaf wedge; the light never outlines every edge."""
    s.poly([(x,y+2),(x+size-3,y),(x+size,y+1),(x+size-1,y+4),(x+2,y+6),(x,y+4)], dark)
    s.poly([(x+1,y+2),(x+size-3,y+1),(x+size-1,y+1),(x+size-2,y+3),(x+2,y+5)], mid)
    if highlight:
        s.line(x+1,y+2,x+size-3,y+1,light)


def foliage(s, x, y, w, h, colors, rng, detail):
    d, shadow, mid, green, light, sun = colors
    # Unequal stepped lobe contour; the lower edge drops into pointed tufts.
    pts=[(x+2,y+h*.37),(x+w*.16,y+h*.37),(x+w*.14,y+h*.22),(x+w*.29,y+h*.16),
         (x+w*.38,y+1),(x+w*.57,y),(x+w*.67,y+h*.13),(x+w*.8,y+h*.16),
         (x+w*.82,y+h*.3),(x+w*.94,y+h*.38),(x+w-1,y+h*.65),(x+w*.9,y+h*.7),
         (x+w*.88,y+h*.9),(x+w*.73,y+h*.85),(x+w*.64,y+h-1),(x+w*.5,y+h*.9),
         (x+w*.34,y+h),(x+w*.26,y+h*.85),(x+w*.1,y+h*.9),(x+w*.12,y+h*.73),(x,y+h*.64)]
    s.poly(pts,d)
    s.poly([(x+2,y+h*.4),(x+w*.25,y+h*.23),(x+w*.45,y+2),(x+w*.64,y+3),
            (x+w*.86,y+h*.38),(x+w*.89,y+h*.65),(x+w*.68,y+h*.84),
            (x+w*.36,y+h*.87),(x+w*.14,y+h*.73)],shadow)
    s.poly([(x+3,y+h*.44),(x+w*.3,y+h*.24),(x+w*.45,y+2),(x+w*.63,y+3),
            (x+w*.78,y+h*.43),(x+w*.65,y+h*.63),(x+w*.32,y+h*.72),(x+4,y+h*.63)],mid)
    # Curated, staggered rows follow the lobe volume. Seed moves clusters, never sprinkles noise.
    sites=[(.34,.18,6),(.51,.12,6),(.2,.32,7),(.42,.32,7),(.63,.29,6),
           (.11,.5,6),(.3,.5,7),(.53,.49,6),(.73,.46,6),(.21,.68,5),(.43,.67,6),(.64,.66,5)]
    for i,(u,v,size) in enumerate(sites):
        if not detail and i % 2:
            continue
        lx=x+u*w+rng.choice([-1,0,0,1]); ly=y+v*h+rng.choice([0,0,1])
        size=max(4,round(size*w/30))
        bright = u < .6 and v < .55
        leaf(s,lx,ly,size,shadow,green if bright else mid,light if v>.2 else sun,bright)


def finish_scene(s, kind, f, wood, metal):
    """Corrections identified by viewing the first Aseprite exports, kept reusable."""
    s.layer("art direction")
    if kind=="bush":
        for x,y in [(15,9),(21,7),(10,15),(23,15),(31,12)]:
            s.poly([(x,y+1),(x+3,y),(x+5,y+1),(x+3,y+3),(x+1,y+4)],f[3])
            s.line(x,y+1,x+3,y,f[4])
        # A silhouette leaf interrupts the overly triangular crown.
        s.poly([(13,9),(12,6),(15,7),(17,10)],f[1])
        s.line(13,7,15,9,f[3])
        s.poly([(27,22),(30,20),(33,20),(31,23),(28,24)],f[2])
    elif kind=="tree":
        for x,y in [(20,14),(28,10),(15,22),(25,23),(34,18),(12,32),(33,36),(40,40),(27,44)]:
            s.poly([(x,y+1),(x+3,y),(x+6,y+1),(x+4,y+3),(x+2,y+5)],f[3])
            s.line(x,y+1,x+3,y,f[4])
        s.poly([(18,13),(15,10),(18,10),(21,13)],f[1])
        s.line(16,10,19,12,f[3])
        s.line(31,57,32,62,wood[1]);s.line(32,62,31,66,wood[1])
        s.line(29,61,28,66,wood[4]);s.line(31,70,28,73,wood[2])
        s.line(35,67,38,71,wood[3])
    else:
        # Broken highlights describe the curve; don't ring the whole object.
        s.line(9,7,13,6,wood[4]);s.line(8,9,8,11,wood[4])
        s.line(11,14,15,15,wood[2]);s.line(16,15,20,14,wood[1])
        s.line(10,17,12,17,metal[2]);s.line(11,32,14,33,metal[2])
        s.line(16,24,16,26,wood[2]);s.line(22,22,22,25,wood[2])


def plan(prompt: str, *, kind=None, width=None, height=None, seed=0, profile=None, detail=True, finish=True):
    spec = parse_prompt(prompt, kind)
    p = load_profile(profile)
    ramps=p["palette"]
    f=ramps["autumn"] if spec["autumn"] else ramps["foliage"]
    wood, metal, berry = ramps["wood"],ramps["metal"],ramps["berries"]
    base={"bush":(48,32),"tree":(64,80),"barrel":(32,40)}[spec["kind"]]
    width, height = base[0] if width is None else width, base[1] if height is None else height
    if not (24 <= width <= 256 and 24 <= height <= 256):
        raise ValueError("Preset canvases must be between 24 and 256 pixels per axis")
    palette=list(dict.fromkeys(f+wood+metal+berry))
    s=Scene(width,height,base,palette)
    rng=random.Random(seed)
    if spec["kind"] == "bush":
        s.layer("woody stems")
        s.poly([(16,27),(20,18),(26,18),(29,27),(25,28),(22,24),(20,28)],wood[0])
        s.line(22,26,23,20,wood[3])
        s.layer("foliage masses")
        foliage(s,3,9,26,18,f,rng,detail)
        foliage(s,20,8,24,19,f,rng,detail)
        foliage(s,11,3,28,23,f,rng,detail)
        if spec["berries"]:
            s.layer("berry accents")
            for x,y in [(13,17),(26,13),(33,22)]:
                s.rect(x,y,3,3,berry[0]);s.rect(x,y,2,2,berry[1]);s.rect(x,y,1,1,berry[2])
    elif spec["kind"] == "tree":
        s.layer("trunk and roots")
        s.poly([(27,38),(38,38),(38,58),(41,69),(46,73),(40,75),(34,72),(29,77),
                (25,76),(27,70),(20,74),(18,72),(24,66),(28,54)],wood[0])
        s.poly([(29,40),(36,40),(34,58),(37,68),(40,72),(33,69),(28,74),(30,66),(25,70),(29,57)],wood[2])
        s.poly([(29,43),(32,42),(31,61),(33,68),(28,72),(30,62)],wood[3])
        s.line(30,45,30,57,wood[4]);s.line(35,52,34,63,wood[1]);s.line(36,64,37,68,wood[1])
        s.poly([(28,54),(19,44),(20,41),(31,49),(36,46),(42,35),(45,36),(40,49),(34,56)],wood[1])
        s.line(22,44,29,50,wood[3])
        s.layer("rear crown")
        foliage(s,24,7,31,30,f,rng,detail)
        foliage(s,4,22,32,30,f,rng,detail)
        s.layer("front crown")
        foliage(s,23,27,35,31,f,rng,detail)
        foliage(s,12,5 if not spec["young"] else 13,36,36 if not spec["young"] else 28,f,rng,detail)
    else:
        s.layer("stave body")
        s.poly([(8,7),(23,7),(26,11),(28,21),(27,29),(24,34),(19,36),(11,36),(6,33),(4,26),(4,17),(6,11)],wood[0])
        s.poly([(8,10),(22,9),(25,13),(26,22),(25,29),(22,33),(13,34),(8,32),(6,26),(6,17)],wood[1])
        s.poly([(8,12),(20,11),(22,17),(22,29),(20,33),(12,33),(8,30),(7,23)],wood[2])
        s.poly([(10,12),(15,12),(15,33),(11,32),(9,26),(9,18)],wood[3])
        s.line(10,17,10,25,wood[4]);s.line(15,17,15,32,wood[1]);s.line(20,17,21,30,wood[1]);s.line(7,18,7,26,wood[0])
        if detail:
            for x,y,h in [(12,20,4),(17,26,3),(18,18,3),(11,29,2),(23,21,4)]:
                x+=rng.choice([0,1]);y+=rng.choice([-1,0,1])
                s.line(x,y,x,y+h,wood[1] if spec["weathered"] else wood[2])
            s.line(17,22,18,23,wood[1]);s.line(18,23,17,24,wood[1])
        s.layer("iron hoops")
        for y in (13,28):
            s.poly([(5,y),(8,y+2),(14,y+3),(22,y+2),(26,y),(26,y+3),(22,y+5),(13,y+6),(7,y+4),(5,y+3)],metal[0])
            s.poly([(6,y+1),(9,y+3),(15,y+4),(23,y+3),(25,y+1),(25,y+3),(21,y+4),(13,y+5),(8,y+3)],metal[1])
            s.line(8,y+2,13,y+3,metal[2]);s.rect(9,y+3,1,1,metal[3])
        s.layer("lid and rim")
        s.ellipse(6,4,20,12,wood[0]);s.ellipse(7,5,18,10,wood[3]);s.ellipse(9,6,14,7,wood[1]);s.ellipse(10,6,12,6,wood[3])
        s.line(10,7,18,7,wood[4]);s.line(11,9,21,9,wood[2]);s.line(13,11,19,11,wood[2])
        bung=17+rng.randrange(3)
        s.rect(bung,8,3,2,wood[0]);s.rect(bung,8,2,1,wood[4])
    if detail and finish:
        finish_scene(s,spec["kind"],f,wood,metal)
    scene=s.export()
    used={op["color"] for layer in scene["layers"] for op in layer["operations"]}
    scene["palette"]=[c for c in palette if c in used]
    metadata={"schema_version":1,"spec":spec,"seed":seed,"style":p["id"],"profile_revision":p["revision"],
              "profile_sha256":hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest(),
              "construction":p["construction"][spec["kind"]],"detail":detail,"refinement_applied":detail and finish,"visual_review":"pending"}
    return scene,metadata
