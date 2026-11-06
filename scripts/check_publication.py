"""Check the tracked publication boundary without reading credentials or references."""
import subprocess
from pathlib import PurePosixPath

files=subprocess.check_output(["git","ls-files","-z"],text=True).split("\0")
denied={"reference",".local",".venv","node_modules",".codex",".claude-flow",".swarm",".ruflo"}
bad=[name for name in files if name and (any(part.casefold() in denied for part in PurePosixPath(name).parts) or PurePosixPath(name).name in {".env",".mcp.json"})]
if bad:raise SystemExit("Private paths tracked: "+", ".join(bad))
print("Publication boundary passed: no private source/build/config paths tracked.")
