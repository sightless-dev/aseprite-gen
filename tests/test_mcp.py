import asyncio
import base64
import io
from pathlib import Path

from PIL import Image
import pytest

from aseprite_gen.aseprite import find_aseprite
from aseprite_gen.protocol import call_tool, call_tool_raw, list_tools


def test_real_stdio_tool_discovery_has_callable_schemas(tmp_path):
    tools = {tool["name"]: tool for tool in list_tools(tmp_path)}
    assert set(tools) == {"editor_status", "render_scene", "inspect_sprite", "refine_sprite", "export_sprite"}
    assert tools["render_scene"]["inputSchema"]["properties"]["scene"]["type"] == "object"
    assert set(tools["refine_sprite"]["inputSchema"]["required"]) == {"path", "layer", "operations", "output_name"}


def test_real_stdio_invalid_scene_returns_actionable_error(tmp_path):
    with pytest.raises(RuntimeError, match="width must be an integer"):
        call_tool("render_scene", {"scene": {}, "output_name": "invalid"}, tmp_path)
    assert not list(tmp_path.glob("*.aseprite"))


@pytest.mark.integration
def test_actual_mcp_render_review_refine_export(tmp_path):
    try:
        find_aseprite()
    except FileNotFoundError:
        pytest.skip("Actual Aseprite executable unavailable; set ASEPRITE_PATH")
    scene = {"width": 8, "height": 8, "palette": ["#8d6651", "#d8b777"], "layers": [
        {"name": "wood", "operations": [{"op": "rect", "x": 2, "y": 2, "w": 4, "h": 4, "color": "#8d6651"}]},
    ]}
    created = call_tool("render_scene", {"scene": scene, "output_name": "mcp-original"}, tmp_path)
    assert Path(created["aseprite_path"]).is_file()
    inspected = asyncio.run(call_tool_raw("inspect_sprite", {"path": created["aseprite_path"], "scale": 4}, tmp_path))
    images = [item for item in inspected.content if item.type == "image"]
    assert len(images) == 1
    with Image.open(io.BytesIO(base64.b64decode(images[0].data))) as preview:
        assert preview.size == (32,32)
        assert preview.getpixel((8,8)) == (141,102,81,255)
        assert preview.getpixel((11,11)) == preview.getpixel((8,8))
    assert inspected.structuredContent["layer_names"] == ["wood"]
    revised = call_tool("refine_sprite", {"path": created["aseprite_path"], "layer": "highlights", "operations": [
        {"op": "pixel", "x": 2, "y": 2, "color": "#d8b777"},
    ], "output_name": "mcp-revised"}, tmp_path)
    assert revised["layer_names"] == ["wood", "highlights"]
    assert revised["sha256"] != created["sha256"]
    exported = call_tool("export_sprite", {"path": revised["aseprite_path"], "output_name": "mcp-export"}, tmp_path)
    assert exported["sha256"] == revised["sha256"]
