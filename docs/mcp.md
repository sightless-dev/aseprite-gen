# Aseprite MCP

This project supplies a local **stdio Model Context Protocol server**, using the
official Python MCP SDK. The generator CLI uses an MCP client to call this server;
the server starts the real Aseprite executable in batch mode and runs a fixed Lua
renderer. Aseprite creates the layers, rasterizes the drawing operations, saves the
editable source, and exports the PNG. Python only validates requests, manages files,
and scales review previews with nearest-neighbor.

## Connect a client

Install the project in its virtual environment and build or install Aseprite first.
The process command is:

```powershell
$env:ASEPRITE_PATH = 'D:\AsepriteGen\.local\aseprite\build\bin\aseprite.exe'
$env:ASEPRITE_OUTPUT_DIR = 'D:\AsepriteGen\output'
& 'D:\AsepriteGen\.venv\Scripts\python.exe' -m aseprite_gen.mcp_server
```

The server waits for MCP JSON-RPC on stdin; ordinary stdout must remain reserved
for the protocol. An MCP client starts and owns this process. Do not pipe arbitrary
console commands into it.

A project-local Codex configuration can use this section in `.codex/config.toml`:

```toml
[mcp_servers.aseprite]
command = "D:\\AsepriteGen\\.venv\\Scripts\\python.exe"
args = ["-m", "aseprite_gen.mcp_server"]

[mcp_servers.aseprite.env]
ASEPRITE_PATH = "D:\\AsepriteGen\\.local\\aseprite\\build\\bin\\aseprite.exe"
ASEPRITE_OUTPUT_DIR = "D:\\AsepriteGen\\output"
```

Adjust all paths for the target machine. Keep this machine-specific file local.
Restart/reconnect the client to discover tools added after a chat started. The CLI
client can invoke and test MCP immediately without relying on a refreshed chat tool
inventory. Setting `ASEPRITE_OUTPUT_DIR` in a Python `call_tool(..., output_dir=...)`
call confines that server invocation to the specified directory.

## Tools and scene format

| Tool | Behavior |
| --- | --- |
| `editor_status()` | Resolves the executable and output directory; rendering is the actual runtime health check. |
| `render_scene(scene, output_name)` | Creates a source document, ordered layers, explicit palette and PNG. |
| `inspect_sprite(path, scale=1)` | Reopens the source in Aseprite and returns metadata plus actual PNG image content. |
| `refine_sprite(path, layer, operations, output_name)` | Changes a selected layer or adds it on top; saves a new revision. |
| `export_sprite(path, output_name)` | Reopens and exports a source copy and native PNG. |

Example scene:

```json
{
  "width": 16,
  "height": 16,
  "palette": ["#5f3456", "#e2b868"],
  "layers": [
    {
      "name": "body",
      "operations": [
        {"op": "rect", "x": 3, "y": 4, "w": 10, "h": 9, "color": "#5f3456"}
      ]
    },
    {
      "name": "light",
      "operations": [
        {"op": "line", "x": 4, "y": 5, "x2": 10, "y2": 5, "color": "#e2b868"}
      ]
    }
  ]
}
```

Layers are ordered bottom to top. The supported operations are:

- `pixel`: `x`, `y`, `color`.
- `line`: `x`, `y`, `x2`, `y2`, `color`; Bresenham line, one pixel wide.
- `rect`: `x`, `y`, `w`, `h`, `color`; filled rectangle.
- `ellipse`: `x`, `y`, `w`, `h`, `color`; filled, tested at pixel centers.
- `polygon`: `points` as integer `[x,y]` pairs and `color`; even-odd scanline fill
  with an included one-pixel Bresenham boundary.

Coordinates must fit inside the canvas; widths/heights are positive pixel counts.
There is no implicit clipping or interpolation. Use exact integers. Colors use
`#RRGGBB` or `#RRGGBBAA`, with alpha only `00` or `FF`; opaque colors must appear in
the palette. An alpha-zero operation erases the selected layer's pixels, revealing
lower layers. All supported source documents are single-frame RGB sprites.

Limits: 512 pixels per dimension, 64 requested palette colors, 32 uniquely named
layers, 20,000 operations per scene/request, 256 vertices per polygon, and a
120-second Aseprite subprocess timeout. Layer names may contain Unicode. Output
basenames use ASCII letters, digits, `_`, `-`, with no extension or path separators.
The Aseprite palette includes a transparent entry in addition to requested colors.

## Preservation and scope

Outputs are `.aseprite` and `.png`. Each result reports actual dimensions, layer
names, frames, palette, editor version, paths, and the PNG SHA-256. Existing output
names are refused, so use `tree-v1`, `tree-v2`, etc. Refinement does not overwrite
its source. Source reads and output writes are confined to `ASEPRITE_OUTPUT_DIR`,
including checks after path resolution. Drawing requests cannot supply Lua code,
shell arguments, arbitrary filesystem paths or external commands.

`inspect_sprite` produces a fresh render of the actual source. At `scale=1` it
returns native pixels; `scale=2..16` is an integer nearest-neighbor review preview.
The helper `protocol.call_tool` returns metadata only; `call_tool_raw` exposes the
SDK `CallToolResult` including `ImageContent` for visual inspection.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_aseprite.py tests/test_mcp.py -q
```

The tests include a real MCP handshake, tool/schema discovery, error responses,
and (when Aseprite is available) actual render → source review → layer refinement
→ re-export. Pixel checks verify transparency, colors, layers and that targeted
refinement changes the intended pixel while preserving the original document.
Tests marked `integration` explicitly skip if no editor executable is available;
such skips are not evidence of a working editor integration.

The drawing implementation uses the official Aseprite [Sprite API](https://www.aseprite.org/api/sprite/),
[Image API](https://www.aseprite.org/api/image/), and
[Palette API](https://www.aseprite.org/api/palette/).
