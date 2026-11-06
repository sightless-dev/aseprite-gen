"""Small real MCP client shared by the CLI and integration tests."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


def _parameters(output_dir: str | Path | None = None) -> StdioServerParameters:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if output_dir is not None:
        env["ASEPRITE_OUTPUT_DIR"] = str(Path(output_dir).resolve())
    return StdioServerParameters(command=sys.executable, args=["-m", "aseprite_gen.mcp_server"], env=env)


async def call_tool_raw(name: str, arguments: dict, output_dir: str | Path | None = None) -> CallToolResult:
    async with stdio_client(_parameters(output_dir)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=180)) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
    if result.isError:
        message = "\n".join(item.text for item in result.content if item.type == "text")
        raise RuntimeError(message)
    return result


def call_tool(name: str, arguments: dict, output_dir: str | Path | None = None) -> dict:
    """Invoke a new stdio MCP session and return metadata (images stay in raw API)."""
    result = asyncio.run(call_tool_raw(name, arguments, output_dir))
    if result.structuredContent is not None:
        return result.structuredContent
    for item in result.content:
        if item.type == "text":
            return json.loads(item.text)
    raise RuntimeError("MCP tool returned no metadata")


async def _list_tools(output_dir: str | Path | None) -> list[dict]:
    async with stdio_client(_parameters(output_dir)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool.model_dump() for tool in result.tools]


def list_tools(output_dir: str | Path | None = None) -> list[dict]:
    return asyncio.run(_list_tools(output_dir))
