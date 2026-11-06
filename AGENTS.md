# Aseprite Gen

Keep work scoped to the requested behavior and run focused checks. Source lives in `src/aseprite_gen`; art rules in `profiles/cozy-rpg.json`; the reusable Codex skill in `.agents/skills/aseprite-pixel-artist`.

- `Reference/` is private. Never commit it, derived sheets/crops, local metadata containing its filenames, credentials, local MCP config, or `.local/` build products. Public examples must be original artwork.
- Aseprite is the renderer/source of truth. Use real MCP stdio calls for generation/refinement. Never claim a PNG-only renderer is an Aseprite integration.
- Inspect actual images at native and nearest-neighbor scale. Technical checks do not certify artistic quality. Preserve before/after files and honest limitations.
- Follow the saved profile; separate confirmed evidence, inferences and contradictions. Never treat RGB recolor masks or UI as the prop style.
- Preserve existing output names and layers. Validate scene shapes, limits and colors before Lua execution; do not accept executable Lua from callers.
- Tests: `.venv/Scripts/python.exe -m pytest tests/test_<affected>.py -q`. Integration tests require a built Aseprite; report skips honestly. CI unit checks deliberately exclude native editor tests.
- Use `scripts/build-aseprite.ps1` for a pinned Windows build; keep upstream source/binaries local. Do not redistribute Aseprite or impose a project license without the owner's decision.
- Read `docs/ruflo.md` before orchestration. Registered roles are not autonomous model execution; discover schemas and record real responses.
