"""Stdio MCP server; no drawing operation accepts executable code or outside paths."""

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ImageContent, TextContent
import base64

from .aseprite import AsepriteBackend, find_aseprite


mcp = FastMCP("aseprite-gen", instructions="Create and review single-frame pixel art through Aseprite. Layers are ordered bottom to top. All paths are confined to ASEPRITE_OUTPUT_DIR; choose a new output_name for every revision.", log_level="WARNING")


@mcp.tool()
def editor_status() -> dict:
    """Resolve the installed Aseprite executable and the confined output directory."""
    backend = AsepriteBackend()
    return {"executable": str(find_aseprite()), "output_dir": str(backend.output_dir), "transport": "stdio"}


@mcp.tool()
def render_scene(scene: dict, output_name: str) -> dict:
    """Draw a validated scene in Aseprite, save editable layers and export PNG.

    Scene: {width:1..512,height:1..512,palette:[#RRGGBB],layers:[{name,operations}]}.
    Operations: {op:'pixel',x,y,color}; {op:'line',x,y,x2,y2,color};
    {op:'rect'|'ellipse',x,y,w,h,color}; {op:'polygon',points:[[x,y],...],color}.
    Coordinates are integer canvas pixels. Shapes are filled; lines one pixel wide.
    Colors must be in palette, except alpha 00 erases. Alpha is either 00 or FF.
    output_name is an ASCII basename without extension. Existing results are preserved.
    """
    return AsepriteBackend().render_scene(scene, output_name)


@mcp.tool()
def inspect_sprite(path: str, scale: int = 1) -> CallToolResult:
    """Open the actual .aseprite source and return metadata plus a rendered PNG image.

    path must be inside ASEPRITE_OUTPUT_DIR. scale is an integer from 1 to 16;
    preview scaling is nearest-neighbor and never changes the source.
    """
    metadata, png = AsepriteBackend().inspect_sprite(path, scale)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(metadata)),
                 ImageContent(type="image", data=base64.b64encode(png).decode("ascii"), mimeType="image/png")],
        structuredContent=metadata,
    )


@mcp.tool()
def refine_sprite(path: str, layer: str, operations: list[dict], output_name: str) -> dict:
    """Apply validated operations to a named layer and save a NEW source + PNG revision.

    Reuses render_scene operation schema and the source palette. A missing layer is
    added on top. Other layers and the original file are preserved. Alpha 00 erases
    pixels on the selected layer. Only single-frame RGB source files are supported.
    """
    return AsepriteBackend().refine_sprite(path, layer, operations, output_name)


@mcp.tool()
def export_sprite(path: str, output_name: str) -> dict:
    """Reopen an actual source and export native PNG plus a saved .aseprite copy."""
    return AsepriteBackend().export_sprite(path, output_name)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
