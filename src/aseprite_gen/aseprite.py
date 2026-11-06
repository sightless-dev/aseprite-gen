"""Validated drawing operations executed by Aseprite's Lua runtime.

Python validates requests and manages files. Aseprite owns every source document,
layer, rasterized pixel, and native PNG export; no external raster renderer is used.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from PIL import Image


MAX_SIZE = 512
MAX_OPERATIONS = 20000
COLOR = re.compile(r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")


def normalize_color(value: str) -> str:
    if not isinstance(value, str) or not COLOR.fullmatch(value):
        raise ValueError("Colors must be #RRGGBB or #RRGGBBAA")
    result = value.lower() if len(value) == 9 else value.lower() + "ff"
    if result[-2:] not in {"00", "ff"}:
        raise ValueError("Pixel art operations require binary alpha (00 or FF)")
    return result


def _integer(value: object, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def validate_operations(operations: list, width: int, height: int, palette: list[str]) -> list[dict]:
    """Normalize the fixed operation vocabulary without accepting executable code."""
    if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS:
        raise ValueError(f"operations must be a list of at most {MAX_OPERATIONS} items")
    allowed_colors = {normalize_color(color) for color in palette}
    normalized = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ValueError(f"operation {index} must be an object")
        kind = operation.get("op")
        if kind not in {"pixel", "line", "rect", "ellipse", "polygon"}:
            raise ValueError(f"Unsupported operation: {kind}")
        color = normalize_color(operation.get("color"))
        if color[-2:] != "00" and color not in allowed_colors:
            raise ValueError(f"Operation color {color} is not in the scene palette")
        item = {"op": kind, "color": color}
        expected = {"op", "color"}
        if kind == "polygon":
            points = operation.get("points")
            if not isinstance(points, list) or not 3 <= len(points) <= 256:
                raise ValueError("A polygon needs 3..256 integer coordinate pairs")
            item["points"] = []
            for point in points:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError("Each polygon point must contain x and y")
                item["points"].append([
                    _integer(point[0], 0, width - 1, "x"),
                    _integer(point[1], 0, height - 1, "y"),
                ])
            expected.add("points")
        else:
            item["x"] = _integer(operation.get("x"), 0, width - 1, "x")
            item["y"] = _integer(operation.get("y"), 0, height - 1, "y")
            expected.update({"x", "y"})
            if kind == "line":
                item["x2"] = _integer(operation.get("x2"), 0, width - 1, "x2")
                item["y2"] = _integer(operation.get("y2"), 0, height - 1, "y2")
                expected.update({"x2", "y2"})
            if kind in {"rect", "ellipse"}:
                item["w"] = _integer(operation.get("w"), 1, width - item["x"], "w")
                item["h"] = _integer(operation.get("h"), 1, height - item["y"], "h")
                expected.update({"w", "h"})
        if set(operation) != expected:
            raise ValueError(f"Unexpected/missing fields for {kind}: {set(operation) ^ expected}")
        normalized.append(item)
    return normalized


def validate_scene(scene: dict) -> dict:
    if not isinstance(scene, dict):
        raise ValueError("scene must be an object")
    width = _integer(scene.get("width"), 1, MAX_SIZE, "width")
    height = _integer(scene.get("height"), 1, MAX_SIZE, "height")
    palette = scene.get("palette")
    if not isinstance(palette, list) or not 1 <= len(palette) <= 64:
        raise ValueError("palette must contain 1..64 colors")
    palette = list(dict.fromkeys(normalize_color(color) for color in palette))
    layers = scene.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 32:
        raise ValueError("scene must contain 1..32 layers, ordered bottom to top")
    result = {"width": width, "height": height, "palette": palette, "layers": []}
    names = set()
    count = 0
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("Each layer must be an object")
        name = layer.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError("Layer names must contain 1..80 printable characters")
        if name in names:
            raise ValueError("Layer names must be unique")
        names.add(name)
        operations = validate_operations(layer.get("operations"), width, height, palette)
        count += len(operations)
        result["layers"].append({"name": name, "operations": operations})
    if count > MAX_OPERATIONS:
        raise ValueError(f"Scene exceeds {MAX_OPERATIONS} operations")
    return result


def find_aseprite() -> Path:
    explicit = os.environ.get("ASEPRITE_PATH")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"ASEPRITE_PATH does not exist: {path}")
        return path
    root = Path(__file__).resolve().parents[2]
    candidates = [root / ".local/aseprite/build/bin/aseprite.exe", root / ".local/aseprite/build/bin/aseprite"]
    on_path = shutil.which("aseprite")
    if on_path:
        candidates.insert(0, Path(on_path))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError("Aseprite executable not found. Set ASEPRITE_PATH or run scripts/build-aseprite.ps1")


# This is fixed trusted code. All caller data is decoded from JSON, never interpolated
# into Lua. Bresenham lines, pixel-center ellipses and scanline polygon fills use
# integer writes only. The polygon border includes vertices and horizontal edges.
LUA = r'''
local f = assert(io.open(app.params["payload"], "rb"))
local p = json.decode(f:read("*a")); f:close()
local function rgba(s)
  return app.pixelColor.rgba(tonumber(s:sub(2,3),16), tonumber(s:sub(4,5),16),
                            tonumber(s:sub(6,7),16), tonumber(s:sub(8,9),16))
end
local function line(img,x0,y0,x1,y1,c)
  local dx,dy=math.abs(x1-x0),-math.abs(y1-y0)
  local sx,sy=x0<x1 and 1 or -1,y0<y1 and 1 or -1
  local err=dx+dy
  while true do
    img:drawPixel(x0,y0,c)
    if x0==x1 and y0==y1 then break end
    local e2=2*err
    if e2>=dy then err=err+dy; x0=x0+sx end
    if e2<=dx then err=err+dx; y0=y0+sy end
  end
end
local function draw(img, operations)
  for _,o in ipairs(operations) do
    local c=rgba(o.color)
    if o.op=="pixel" then img:drawPixel(o.x,o.y,c)
    elseif o.op=="line" then line(img,o.x,o.y,o.x2,o.y2,c)
    elseif o.op=="rect" then
      for y=o.y,o.y+o.h-1 do for x=o.x,o.x+o.w-1 do img:drawPixel(x,y,c) end end
    elseif o.op=="ellipse" then
      for y=o.y,o.y+o.h-1 do for x=o.x,o.x+o.w-1 do
        local dx=(2*(x-o.x)+1-o.w)/o.w
        local dy=(2*(y-o.y)+1-o.h)/o.h
        if dx*dx+dy*dy<=1 then img:drawPixel(x,y,c) end
      end end
    elseif o.op=="polygon" then
      local ymin,ymax=img.height,0
      for _,v in ipairs(o.points) do ymin=math.min(ymin,v[2]); ymax=math.max(ymax,v[2]) end
      for y=ymin,ymax do
        local nodes={}; local j=#o.points
        for i=1,#o.points do
          local a,b=o.points[i],o.points[j]
          if (a[2]<=y and b[2]>y) or (b[2]<=y and a[2]>y) then
            nodes[#nodes+1]=a[1]+(y-a[2])*(b[1]-a[1])/(b[2]-a[2])
          end
          j=i
        end
        table.sort(nodes)
        for i=1,#nodes-1,2 do
          for x=math.ceil(nodes[i]),math.floor(nodes[i+1]) do img:drawPixel(x,y,c) end
        end
      end
      for i=1,#o.points do
        local a,b=o.points[i],o.points[i % #o.points+1]
        line(img,a[1],a[2],b[1],b[2],c)
      end
    end
  end
end
local s
if p.action=="render" then
  s=Sprite(p.scene.width,p.scene.height,ColorMode.RGB)
  local palette=Palette(#p.scene.palette+1)
  palette:setColor(0,Color{r=0,g=0,b=0,a=0})
  for i,c in ipairs(p.scene.palette) do palette:setColor(i,rgba(c)) end
  s:setPalette(palette)
  for i,layerData in ipairs(p.scene.layers) do
    local layer=i==1 and s.layers[1] or s:newLayer()
    layer.name=layerData.name
    local img=Image(s.width,s.height,ColorMode.RGB); img:clear()
    draw(img,layerData.operations)
    s:newCel(layer,1,img,Point(0,0))
  end
else
  s=assert(app.open(p.source),"Could not open source sprite")
  assert(#s.frames==1,"Only single-frame sprites are supported")
  assert(s.colorMode==ColorMode.RGB,"Only RGB sprites are supported")
  if p.action=="refine" then
    local layer=nil
    for _,candidate in ipairs(s.layers) do if candidate.name==p.layer then layer=candidate end end
    if not layer then layer=s:newLayer(); layer.name=p.layer end
    assert(not layer.isGroup,"Refine requires an image layer")
    local img=Image(s.width,s.height,ColorMode.RGB); img:clear()
    local cel=layer:cel(1)
    if cel then img:drawImage(cel.image,cel.position) end
    draw(img,p.operations)
    s:newCel(layer,1,img,Point(0,0))
  end
end
if p.aseprite then s:saveAs(p.aseprite) end
if p.png then Image(s):saveAs(p.png) end
local names={}; for _,layer in ipairs(s.layers) do names[#names+1]=layer.name end
local colors={}
for i=0,#s.palettes[1]-1 do
  local c=s.palettes[1]:getColor(i)
  colors[#colors+1]=string.format("#%02x%02x%02x%02x",c.red,c.green,c.blue,c.alpha)
end
local metadata={width=s.width,height=s.height,frames=#s.frames,layer_names=names,
                palette=colors,color_mode="RGBA",aseprite_version=tostring(app.version)}
local out=assert(io.open(p.metadata,"wb")); out:write(json.encode(metadata)); out:close()
s:close()
'''


class AsepriteBackend:
    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir or os.environ.get("ASEPRITE_OUTPUT_DIR", "output")).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def source_path(self, path: str | Path) -> Path:
        source = Path(path)
        source = (source if source.is_absolute() else self.output_dir / source).resolve()
        if not source.is_relative_to(self.output_dir) or source.suffix.lower() != ".aseprite":
            raise ValueError("Source must be an .aseprite file inside ASEPRITE_OUTPUT_DIR")
        if not source.is_file():
            raise FileNotFoundError(f"Sprite does not exist: {source}")
        return source

    @contextmanager
    def _claim(self, name: str):
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise ValueError("output_name must be a plain ASCII name (letters, digits, hyphens, underscores)")
        if name.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}:
            raise ValueError("output_name is a reserved Windows filename")
        targets = {"aseprite": self.output_dir / f"{name}.aseprite", "png": self.output_dir / f"{name}.png"}
        lock = self.output_dir / f".{name}.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise FileExistsError(f"Another generation owns {name}; use a different output_name") from error
        os.close(descriptor)
        try:
            if any(path.exists() for path in targets.values()):
                raise FileExistsError(f"Output {name} already exists; choose a new name to preserve earlier results")
            yield targets
        finally:
            lock.unlink(missing_ok=True)

    def _execute(self, payload: dict, folder: Path) -> dict:
        script = folder / "draw.lua"
        data = folder / "request.json"
        metadata = folder / "metadata.json"
        payload = {**payload, "metadata": metadata.as_posix()}
        script.write_text(LUA, encoding="utf-8")
        data.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        executable = find_aseprite()
        result = subprocess.run(
            [str(executable), "--batch", "--script-param", f"payload={data}", "--script", str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode or not metadata.is_file():
            detail = (result.stderr + "\n" + result.stdout).strip()[-3000:]
            raise RuntimeError(f"Aseprite failed (exit {result.returncode}): {detail}")
        return json.loads(metadata.read_text(encoding="utf-8"))

    def _write(self, action: dict, name: str) -> dict:
        with self._claim(name) as targets, tempfile.TemporaryDirectory(prefix=".aseprite-gen-", dir=self.output_dir) as temp:
            folder = Path(temp)
            ase = folder / "result.aseprite"
            png = folder / "result.png"
            metadata = self._execute({**action, "aseprite": ase.as_posix(), "png": png.as_posix()}, folder)
            if not ase.is_file() or ase.read_bytes()[4:6] != b"\xe0\xa5":
                raise RuntimeError("Aseprite did not produce a valid source file")
            with Image.open(png) as image:
                image.load()
                if image.size != (metadata["width"], metadata["height"]):
                    raise RuntimeError("PNG dimensions differ from the Aseprite document")
            os.replace(ase, targets["aseprite"])
            os.replace(png, targets["png"])
        return {**metadata, "aseprite_path": str(targets["aseprite"]), "png_path": str(targets["png"]),
                "sha256": hashlib.sha256(targets["png"].read_bytes()).hexdigest()}

    def render_scene(self, scene: dict, output_name: str) -> dict:
        return self._write({"action": "render", "scene": validate_scene(scene)}, output_name)

    def inspect_sprite(self, path: str, scale: int = 1) -> tuple[dict, bytes]:
        _integer(scale, 1, 16, "scale")
        source = self.source_path(path)
        with tempfile.TemporaryDirectory(prefix=".aseprite-gen-", dir=self.output_dir) as temp:
            folder = Path(temp)
            png = folder / "inspect.png"
            metadata = self._execute({"action": "inspect", "source": source.as_posix(), "png": png.as_posix()}, folder)
            with Image.open(png) as image:
                image = image.convert("RGBA")
                if scale != 1:
                    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
        return {**metadata, "aseprite_path": str(source), "preview_scale": scale}, buffer.getvalue()

    def refine_sprite(self, path: str, layer: str, operations: list[dict], output_name: str) -> dict:
        source = self.source_path(path)
        if not isinstance(layer, str) or not 1 <= len(layer) <= 80 or any(ord(c) < 32 for c in layer):
            raise ValueError("Layer name must contain 1..80 printable characters")
        metadata, _ = self.inspect_sprite(str(source))
        if layer not in metadata["layer_names"] and len(metadata["layer_names"]) >= 32:
            raise ValueError("A sprite can contain at most 32 layers")
        operations = validate_operations(operations, metadata["width"], metadata["height"], metadata["palette"])
        return self._write({"action": "refine", "source": source.as_posix(), "layer": layer, "operations": operations}, output_name)

    def export_sprite(self, path: str, output_name: str) -> dict:
        return self._write({"action": "export", "source": self.source_path(path).as_posix()}, output_name)
