"""Private reference inventory, measurable image properties, and review sheets.

Measurements are evidence for an artist, not an automatic artistic verdict.
No reference image or derived contact sheet belongs in the public repository.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw


SUPPORTED_IMAGES = {".png", ".gif", ".bmp", ".webp", ".jpg", ".jpeg"}
ANALYZER_VERSION = 2


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_upscale_factor(image: Image.Image) -> int:
    """Largest exact integer replication factor; 1 does not prove native scale."""
    image = image.convert("RGBA")
    for scale in range(8, 1, -1):
        if image.width % scale or image.height % scale:
            continue
        small = image.resize((image.width // scale, image.height // scale), Image.Resampling.NEAREST)
        if small.resize(image.size, Image.Resampling.NEAREST).tobytes() == image.tobytes():
            # Constant images have no useful grid evidence.
            if len(image.getcolors(image.width * image.height) or []) > 1:
                return scale
    return 1


def tags_for(path: str) -> list[str]:
    name = path.replace("\\", "/").casefold()
    tags = []
    groups = {
        "vegetation": ("tree", "bush", "grass", "spring", "summer", "fall", "winter", "outdoor", "town"),
        "wood": ("craft", "furniture", "barrel", "shed", "barn", "house", "town", "outdoor"),
        "character": ("character", "farmer"),
        "animal": ("animal", "bird", "fish"),
        "creature": ("monster", "bat", "slime"),
        "environment": ("maps/", "mines/", "buldings/"),
        "ui": ("cursor", "billboard", "controller", "letter", "chat", "boardgame", "font", "menu"),
    }
    for tag, terms in groups.items():
        if any(term in name for term in terms):
            tags.append(tag)
    if any(term in name for term in ("paintmask", "paint_mask", "colormask", "color_mask", "collisionmask", "collision_mask")) or re.search(r"(?:^|[/_\s-])masks?(?:[/_.\s-]|$)", name):
        tags.append("mask")
    stem = Path(name).stem
    if "mannequin" in stem or stem in {"shadow", "swimshadow", "lightrays", "daybg"}:
        tags.append("technical")
    if not tags:
        tags.append("miscellaneous")
    return tags


def image_properties(path: Path) -> dict:
    with Image.open(path) as source:
        image = source.convert("RGBA")
        colors = image.getcolors(image.width * image.height) or []
        opaque = [(count, rgba) for count, rgba in colors if rgba[3] > 0]
        total_visible = sum(count for count, _ in opaque)
        partial = sum(count for count, rgba in colors if 0 < rgba[3] < 255)
        palette = sorted(opaque, key=lambda value: (-value[0], value[1]))[:24]
        factor = exact_upscale_factor(image)
        return {
            "width": image.width, "height": image.height,
            "source_mode": source.mode, "frame_count": getattr(source, "n_frames", 1),
            "visible_pixels": total_visible,
            "transparent_pixels": image.width * image.height - total_visible,
            "partially_transparent_pixels": partial,
            "visible_color_count": len({rgba[:3] for _, rgba in opaque}),
            "exact_replication_factor": factor,
            "grid_interpretation": "exact integer replication" if factor > 1 else "no exact whole-image integer upscale detected",
            "top_colors": [{"rgba": list(rgba), "count": count} for count, rgba in palette],
            "visual_review": "pending; measurements do not establish visual inspection",
        }


def _checker(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGB", size, "#d2cec6")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], 8):
        for x in range(0, size[0], 8):
            if (x // 8 + y // 8) % 2:
                draw.rectangle((x, y, x + 7, y + 7), fill="#bbb7b0")
    return image


def make_contact_sheets(reference_dir: Path, entries: list[dict], output_dir: Path,
                        per_sheet: int = 24, columns: int = 4) -> list[str]:
    """Overview sheets may shrink atlases; inspect native crops for pixel claims."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images = [entry for entry in entries if entry.get("kind") == "image" and "error" not in entry]
    result = []
    cell_w, cell_h = 300, 244
    for page, start in enumerate(range(0, len(images), per_sheet), 1):
        batch = images[start:start + per_sheet]
        canvas = Image.new("RGB", (columns * cell_w, math.ceil(len(batch) / columns) * cell_h), "#f4f0e7")
        draw = ImageDraw.Draw(canvas)
        for index, entry in enumerate(batch):
            x, y = (index % columns) * cell_w, (index // columns) * cell_h
            with Image.open(reference_dir / entry["path"]) as source:
                image = source.convert("RGBA")
                scale = min((cell_w - 12) / image.width, (cell_h - 40) / image.height)
                if scale >= 1:
                    scale = max(1, math.floor(scale))
                preview = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.NEAREST)
                background = _checker(preview.size)
                background.paste(preview, mask=preview.getchannel("A"))
                canvas.paste(background, (x + (cell_w - preview.width) // 2, y + 34))
                label = f"{start + index + 1:03d} {entry['path']}"
                draw.text((x + 5, y + 3), label[:46], fill="#171b24")
                draw.text((x + 5, y + 17), f"{image.width}x{image.height}; overview {scale:.2f}x", fill="#55555c")
        name = f"contact-{page:02d}.png"
        canvas.save(output_dir / name)
        result.append(name)
    return result


def make_palette_sheet(entries: list[dict], path: Path) -> None:
    groups: dict[str, Counter] = {}
    for entry in entries:
        if entry.get("kind") != "image" or "top_colors" not in entry:
            continue
        group = entry["path"].split("/")[0]
        colors = groups.setdefault(group, Counter())
        for color in entry["top_colors"]:
            if color["rgba"][3] == 255:
                colors[tuple(color["rgba"][:3])] += color["count"]
    canvas = Image.new("RGB", (900, max(1, len(groups)) * 85), "#f4f0e7")
    draw = ImageDraw.Draw(canvas)
    for row, (group, colors) in enumerate(sorted(groups.items())):
        y = row * 85
        draw.text((10, y + 3), group + " — most frequent opaque colors, not material ramps", fill="#202030")
        for col, (color, _) in enumerate(colors.most_common(16)):
            x = col * 55 + 10
            draw.rectangle((x, y + 23, x + 49, y + 58), fill=color)
            draw.text((x, y + 62), "#%02x%02x%02x" % color, fill="#202030")
    canvas.save(path)


def analyze(reference_dir: str | Path, output_dir: str | Path) -> dict:
    """Create immutable, content-addressed analysis runs, reusing unchanged stats.

    User-authored visual observations live in separate files and are never
    overwritten. The latest.json pointer changes only after a completed run.
    """
    reference_dir, output_dir = Path(reference_dir).resolve(), Path(output_dir).resolve()
    if not reference_dir.is_dir():
        raise ValueError(f"Reference directory does not exist: {reference_dir}")
    if output_dir == reference_dir or reference_dir in output_dir.parents:
        raise ValueError("Analysis output must be outside the reference directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    old_entries: dict[str, dict] = {}
    pointer = output_dir / "latest.json"
    if pointer.exists():
        previous = json.loads(pointer.read_text(encoding="utf-8"))
        old_manifest = output_dir / previous["run"] / "manifest.json"
        if old_manifest.is_file():
            cached = json.loads(old_manifest.read_text(encoding="utf-8"))
            if cached.get("analyzer_version") == ANALYZER_VERSION:
                old_entries = {entry["path"]: entry for entry in cached["files"]}
    entries, signature = [], hashlib.sha256()
    for path in sorted(reference_dir.rglob("*"), key=lambda value: value.as_posix().casefold()):
        if not path.is_file():
            continue
        relative = path.relative_to(reference_dir).as_posix()
        digest = _sha256(path)
        signature.update(relative.encode("utf-8") + b"\0" + digest.encode("ascii"))
        entry = {"path": relative, "sha256": digest, "bytes": path.stat().st_size,
                 "tags": tags_for(relative)}
        previous = old_entries.get(relative)
        if previous and previous["sha256"] == digest:
            entry = previous.copy()
        else:
            try:
                if path.suffix.casefold() in SUPPORTED_IMAGES:
                    entry.update(kind="image", **image_properties(path))
                elif path.suffix.casefold() == ".json":
                    data = json.loads(path.read_text(encoding="utf-8-sig"))
                    entry.update(kind="metadata", json_type=type(data).__name__)
                    if isinstance(data, dict):
                        entry["top_level_keys"] = sorted(data.keys())
                        content = data.get("content", {})
                        if isinstance(content, dict) and isinstance(content.get("export"), str):
                            entry["export_reference"] = content["export"]
                elif path.suffix.casefold() == ".tbin":
                    entry.update(kind="binary_map", interpretation="inventoried only; no TBIN decoder implemented")
                else:
                    entry.update(kind="unsupported", interpretation="inventoried only")
            except (OSError, ValueError, SyntaxError) as error:
                entry.update(kind="unreadable", error=str(error))
        entries.append(entry)
    run_name = f"v{ANALYZER_VERSION}-{signature.hexdigest()[:16]}"
    run_dir = output_dir / run_name
    if (run_dir / "manifest.json").is_file():
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        sheets = make_contact_sheets(reference_dir, entries, run_dir)
        make_palette_sheet(entries, run_dir / "palettes.png")
        manifest = {
            "schema_version": 1, "analyzer_version": ANALYZER_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(), "run": run_name,
            "privacy": "Private source-derived data. Do not publish this directory.",
            "files": entries, "contact_sheets": sheets,
            "counts": dict(Counter(entry["kind"] for entry in entries)),
            "limitations": ["No automated artistic verdict", "Contact sheets are overview only",
                            "TBIN map files are hashed but not decoded", "Image statistics describe the first frame"],
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    pointer.write_text(json.dumps({"run": run_name}, indent=2), encoding="utf-8")
    return manifest


def select_references(manifest: dict, prompt: str, limit: int = 6) -> list[dict]:
    """Rank local evidence by semantic category; never use pixels as templates."""
    prompt = prompt.casefold()
    query_tags = set(tags_for(prompt)) - {"miscellaneous"}
    for words, tag in [(('bush', 'tree', 'plant', 'куст', 'дерев', 'растен'), 'vegetation'),
                       (('barrel', 'crate', 'wood', 'бочк', 'ящик', 'деревян'), 'wood')]:
        if any(word in prompt for word in words):
            query_tags.add(tag)
    candidates = []
    for entry in manifest.get("files", []):
        if entry.get("kind") != "image" or "error" in entry:
            continue
        # Masks and interface/helper art remain inventoried and visible on sheets,
        # but they are not examples of material rendering for game-world sprites.
        tags = set(entry.get("tags", [])) | set(tags_for(entry.get("path", "")))
        if tags.intersection({"ui", "mask", "technical"}):
            continue
        score = len(query_tags.intersection(tags)) * 10
        if "environment" in tags:
            score += 1
        candidates.append((score, entry["path"], entry))
    return [entry for _, _, entry in sorted(candidates, key=lambda value: (-value[0], value[1]))[:max(0, limit)]]
