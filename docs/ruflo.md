# Verified Ruflo integration

The official [Ruflo documentation](https://github.com/ruvnet/ruflo) describes a stdio MCP server usable from Codex. This project uses `npx -y ruflo@3.72.1 mcp start`; `scripts/ruflo.py` connects through the Python MCP SDK, performs `initialize` and `tools/list`, and then calls discovered tools. It does not synthesize MCP results.

```powershell
.\.venv\Scripts\python.exe scripts/ruflo.py --output .local/ruflo-tools.json
.\.venv\Scripts\python.exe scripts/ruflo.py --requests requests.json --output .local/ruflo-result.json
```

`requests.json` is an array of `{ "name": "memory_retrieve", "arguments": { "namespace": "aseprite-gen", "key": "render-contract" } }` objects. Inspect current tool schemas before changing requests. First use requires network access and may install the pinned package in the npm cache. No daemon, global hooks or unrelated Codex configuration is modified.

During implementation, Ruflo 3.72.1 actually provided:

- `swarm_init`: persisted a hierarchical coordination group.
- `agent_spawn`: registered builder, analyst, integrator and artist roles.
- `task_create` / `task_update` / `task_list`: persisted assignments, progress and evidence across sessions.
- `memory_store` / `memory_retrieve`: shared rendering/privacy decisions and review lessons, including a real cross-session read.

**Execution boundary:** Ruflo's `agent_spawn` response explicitly says “registered.” It did not launch an LLM worker. Actual work ran in Codex's native collaboration workers and the main Codex session, coordinated through those persisted Ruflo tasks and shared decisions. No Anthropic API key or independent Ruflo `agent_execute` invocation was used. Default model labels in registration metadata are not evidence of those models executing. Two workers stopped after a service quota error; the main session completed their remaining analysis/build verification.

On this Windows machine, memory reported the `sql.js + HNSW` backend with 384-dimensional embeddings, with the native bridge disabled by Ruflo's own Windows compatibility default. We do not claim model training, consensus execution or autonomous LLM scheduling was tested. Local task and memory databases are ignored by Git; no private source-derived content is sent to external models by these calls.

The CLI pins the Ruflo package, but upstream may resolve transitive packages dynamically. The authoritative tested version is the MCP server's initialization response, recorded as 3.72.1; inspect it again after installation changes. This integration is useful persistent coordination, not a replacement for Codex execution or image review.
