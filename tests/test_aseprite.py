import copy
from pathlib import Path

from PIL import Image
import pytest

from aseprite_gen.aseprite import AsepriteBackend, find_aseprite, normalize_color, validate_scene


@pytest.fixture
def scene():
    return {
        "width": 16, "height": 16, "palette": ["#5f3456", "#e2b868"],
        "layers": [
            {"name": "body", "operations": [{"op": "rect", "x": 2, "y": 3, "w": 8, "h": 9, "color": "#5f3456"}]},
            {"name": "light", "operations": [{"op": "line", "x": 3, "y": 4, "x2": 8, "y2": 4, "color": "#e2b868"}]},
        ],
    }


def executable_or_skip():
    try:
        return find_aseprite()
    except FileNotFoundError:
        pytest.skip("Actual Aseprite executable unavailable; set ASEPRITE_PATH")


def test_scene_is_normalized_without_mutating_request(scene):
    original = copy.deepcopy(scene)
    normalized = validate_scene(scene)
    assert scene == original
    assert normalized["palette"] == ["#5f3456ff", "#e2b868ff"]
    assert normalized["layers"][0]["operations"][0]["color"] == "#5f3456ff"


@pytest.mark.parametrize("color", ["red", "#abcd", "#11111180", "#abcd00();os.exit()", None])
def test_invalid_color_rejected(color):
    with pytest.raises(ValueError):
        normalize_color(color)


@pytest.mark.parametrize("operation", [
    {"op": "pixel", "x": -1, "y": 0, "color": "#5f3456"},
    {"op": "pixel", "x": True, "y": 0, "color": "#5f3456"},
    {"op": "pixel", "x": 0, "y": 0, "color": "#ffffff"},
    {"op": "pixel", "x": 0, "y": 0, "color": "#5f3456", "lua": "os.exit()"},
    {"op": "rect", "x": 15, "y": 0, "w": 2, "h": 1, "color": "#5f3456"},
    {"op": "polygon", "points": [[0,0], [1,1], [16,0]], "color": "#5f3456"},
])
def test_invalid_operations_rejected(scene, operation):
    scene["layers"][0]["operations"] = [operation]
    with pytest.raises(ValueError):
        validate_scene(scene)


def test_layer_names_and_bounds_are_checked(scene):
    scene["layers"][1]["name"] = "body"
    with pytest.raises(ValueError, match="unique"):
        validate_scene(scene)
    scene["width"] = 513
    with pytest.raises(ValueError, match="width"):
        validate_scene(scene)


def test_alpha_zero_can_erase_without_palette_entry(scene):
    scene["layers"][0]["operations"] = [{"op": "pixel", "x": 0, "y": 0, "color": "#00000000"}]
    assert validate_scene(scene)["layers"][0]["operations"][0]["color"] == "#00000000"


def test_backend_blocks_outside_sources_and_unsafe_output_names(tmp_path, scene):
    backend = AsepriteBackend(tmp_path / "output")
    outside = tmp_path / "outside.aseprite"
    outside.write_bytes(b"private")
    for path in [outside, "../outside.aseprite", "not-a-source.png"]:
        with pytest.raises(ValueError):
            backend.source_path(path)
    for name in ["../outside", "a/b", "C:\\escape", "x.lua", "CON", "NUL", ""]:
        with pytest.raises(ValueError):
            backend.render_scene(scene, name)


def test_existing_output_is_not_overwritten(tmp_path, scene):
    sentinel = tmp_path / "keep.png"
    sentinel.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        AsepriteBackend(tmp_path).render_scene(scene, "keep")
    assert sentinel.read_bytes() == b"keep"
    assert not (tmp_path / ".keep.lock").exists()


@pytest.mark.integration
def test_native_layers_pixels_roundtrip_and_targeted_refinement(tmp_path, scene):
    executable_or_skip()
    backend = AsepriteBackend(tmp_path)
    created = backend.render_scene(scene, "original")
    assert created["layer_names"] == ["body", "light"]
    assert created["frames"] == 1
    before = Path(created["aseprite_path"]).read_bytes()
    with Image.open(created["png_path"]) as image:
        rgba = image.convert("RGBA")
        assert rgba.size == (16, 16)
        assert rgba.getpixel((0, 0)) == (0, 0, 0, 0)
        assert rgba.getpixel((2, 3)) == (95, 52, 86, 255)
        assert rgba.getpixel((3, 4)) == (226, 184, 104, 255)
        pixels = list(rgba.getdata())
    revised = backend.refine_sprite(created["aseprite_path"], "light", [
        {"op": "pixel", "x": 3, "y": 4, "color": "#00000000"},
    ], "revised")
    assert Path(created["aseprite_path"]).read_bytes() == before
    assert revised["layer_names"] == ["body", "light"]
    with Image.open(revised["png_path"]) as image:
        rgba = image.convert("RGBA")
        assert rgba.getpixel((3, 4)) == (95, 52, 86, 255)
        changed = [i for i, (a, b) in enumerate(zip(pixels, rgba.getdata())) if a != b]
        assert changed == [4 * 16 + 3]
    exported = backend.export_sprite(revised["aseprite_path"], "exported")
    assert exported["sha256"] == revised["sha256"]


@pytest.mark.integration
def test_polygon_ellipse_and_pixel_are_aseprite_rendered(tmp_path, scene):
    executable_or_skip()
    scene["layers"] = [{"name": "geometry", "operations": [
        {"op": "polygon", "points": [[1, 1], [6, 1], [1, 6]], "color": "#5f3456"},
        {"op": "ellipse", "x": 8, "y": 8, "w": 5, "h": 5, "color": "#e2b868"},
        {"op": "pixel", "x": 15, "y": 15, "color": "#e2b868"},
    ]}]
    created = AsepriteBackend(tmp_path).render_scene(scene, "shapes")
    with Image.open(created["png_path"]) as image:
        rgba = image.convert("RGBA")
        assert rgba.getpixel((1,1))[3] == 255
        assert rgba.getpixel((3,3))[3] == 255
        assert rgba.getpixel((6,6))[3] == 0
        assert rgba.getpixel((10,10)) == (226,184,104,255)
        assert rgba.getpixel((8,8))[3] == 0
        assert rgba.getpixel((15,15)) == (226,184,104,255)
        assert {pixel[3] for pixel in rgba.getdata()} == {0, 255}
