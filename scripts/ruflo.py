"""Call the pinned Ruflo MCP server; no simulated agents or provider claims."""
import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

VERSION = "3.72.1"


async def run(requests):
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command=shutil.which("npx.cmd" if os.name == "nt" else "npx"),
        args=["-y", f"ruflo@{VERSION}", "mcp", "start"], cwd=str(root),
        env={**os.environ, "NO_COLOR": "1"},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            info = await session.initialize()
            result = {"server": info.serverInfo.model_dump(), "calls": []}
            if not requests:
                result["tools"] = [t.model_dump() for t in (await session.list_tools()).tools]
            for request in requests:
                reply = await session.call_tool(request["name"], request.get("arguments", {}))
                result["calls"].append({**request, "response": reply.model_dump()})
                if reply.isError:
                    raise RuntimeError(result["calls"][-1])
            return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, help="JSON array of tool name/arguments")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run(json.loads(args.requests.read_text()) if args.requests else []))
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)
