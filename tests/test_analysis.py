import json

from PIL import Image

from aseprite_gen.analysis import analyze, exact_upscale_factor, select_references, tags_for


def test_reference_selection_excludes_masks_ui_and_helpers_even_in_old_manifests():
    paths = [
        "Buldings/wood_house_PaintMask.png", "LooseSprites/wood_menu.png",
        "LooseSprites/shadow.png", "Farmer/farmer_base_mannequin.png",
        "Maps/summer_trees.png", "LooseSprites/wood_furniture.png",
    ]
    # Cached v1 manifests have no mask/helper tag, so selection must also look at
    # paths rather than allowing old analysis to silently reintroduce auxiliaries.
    manifest = {"files": [{"path": path, "kind": "image", "tags": ["wood", "vegetation"]} for path in paths]}
    selected = select_references(manifest, "wooden barrel under a tree", limit=20)
    assert {entry["path"] for entry in selected} == set(paths[-2:])
    assert "environment" in tags_for("Maps\\summer_trees.png")
    assert "mask" in tags_for("Buldings/wood_house_PaintMask.png")
    assert "technical" not in tags_for("Monsters/Shadow Brute.png")
    assert "ui" not in tags_for("Monsters/Squid Kid.png")


def test_reanalysis_preserves_prior_runs_and_visual_observations(tmp_path):
    references = tmp_path / "references"
    references.mkdir()
    image_path = references / "bush.png"
    Image.new("RGBA", (4, 4), (48, 92, 60, 255)).save(image_path)
    (references / "map.tbin").write_bytes(b"not-decoded-binary-map")
    (references / "bush.json").write_text(json.dumps({"content": {"export": "bush.png"}}))
    destination = tmp_path / "analysis"
    first = analyze(references, destination)
    first_manifest_path = destination / first["run"] / "manifest.json"
    original_manifest = first_manifest_path.read_bytes()
    notes = destination / first["run"] / "visual-observations.md"
    notes.write_text("Artist-reviewed shape notes", encoding="utf-8")
    same = analyze(references, destination)
    assert same["run"] == first["run"]
    assert first_manifest_path.read_bytes() == original_manifest
    Image.new("RGBA", (4, 4), (60, 110, 65, 255)).save(image_path)
    second = analyze(references, destination)
    assert second["run"] != first["run"]
    assert first_manifest_path.read_bytes() == original_manifest
    assert notes.read_text(encoding="utf-8") == "Artist-reviewed shape notes"
    assert json.loads((destination / "latest.json").read_text())["run"] == second["run"]
    old_entries = {item["path"]: item for item in first["files"]}
    new_entries = {item["path"]: item for item in second["files"]}
    assert old_entries["bush.png"]["sha256"] != new_entries["bush.png"]["sha256"]
    assert old_entries["map.tbin"]["sha256"] == new_entries["map.tbin"]["sha256"]
    assert new_entries["map.tbin"]["kind"] == "binary_map"
    assert "no TBIN decoder" in new_entries["map.tbin"]["interpretation"]
    assert new_entries["bush.png"]["visual_review"].startswith("pending")


def test_exact_upscale_evidence_uses_pixels_not_dimensions():
    native = Image.new("RGBA", (3, 2), (0, 0, 0, 0))
    native.putpixel((0, 0), (120, 90, 50, 255))
    native.putpixel((1, 1), (40, 70, 90, 255))
    enlarged = native.resize((12, 8), Image.Resampling.NEAREST)
    assert exact_upscale_factor(enlarged) == 4
    enlarged.putpixel((1, 1), (130, 90, 50, 255))
    assert exact_upscale_factor(enlarged) == 1
    assert exact_upscale_factor(Image.new("RGBA", (16, 16), (0, 0, 0, 0))) == 1
