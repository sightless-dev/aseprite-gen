---
name: aseprite-pixel-artist
description: "Analyze local pixel-art references and create, visually review, refine, vary, or export original layered Aseprite sprites. Use for pixel-grid game assets, not general image generation or copying existing sprites."
---

# Aseprite Pixel Artist

Work from the project containing this skill (`../../..` from this folder). Run its `.venv/Scripts/python.exe` on Windows, or `.venv/bin/python` elsewhere. Read `profiles/cozy-rpg.json` before creating art; it persists the chosen material ramps, visual grammar and known contradictions. Read `docs/style-guide.md` when making artistic decisions. This is knowledge and tooling, not trained model weights.

## Choose the workflow

- **ANALYZE:** Run `python -m aseprite_gen.cli analyze Reference`. Results and source-derived contact sheets belong in `.local/analysis`. Open every relevant sheet and native detail crop with an image viewer. The manifest's measurements do not establish visual review. Keep observations, hypotheses and contradictory groups distinct. Never use recolor masks, UI or effects as the default prop style. Existing hash-versioned analyses and authored observations must survive an update. Propose a new profile revision from actual observations; do not overwrite unrelated rules from palette statistics.
- **GENERATE:** Decompose the request into silhouette, material planes, overlapping clusters and focal details. For the supported bush/tree/barrel grammar use `python -m aseprite_gen.cli generate "berry bush" --seed 7 --name bush-v1`. It renders through real MCP. Supported prompt modifiers are autumn, berries, young and weathered (including Russian equivalents); unsupported prose is not a general semantic model. For a different construction, use `plan` as a starting point or author a scene JSON following [scene-and-review.md](references/scene-and-review.md), then `render` it through MCP. Do not call a PNG-writing script a tested Aseprite integration.
- **REVIEW:** Run `review output/bush-v1.aseprite --output output`, then actually open the returned native PNG and nearest-neighbor preview. Read the silhouette at 1x before evaluating enlarged clusters. Technical validation cannot approve artwork. Record concrete locations and intended fixes; avoid numerical art scores. If no image viewer is available, explicitly leave artistic review pending.
- **REFINE:** Apply narrowly scoped operations on a named layer with `refine`; choose a new output name. Read the actual source palette; refinement cannot silently add colors. Preserve the earlier source and strong regions, reopen the new source, and compare both. See [scene-and-review.md](references/scene-and-review.md).
- **VARIATIONS:** Use `variations "autumn tree" --count 3 --seed 4 --name autumn`. Inspect differences; seeds change cluster placement or bung position, not every semantic aspect. For stronger silhouette variation modify lobe geometry in scene JSON.
- **EXPORT:** Use `export output/bush-v2.aseprite --output output --name bush-release` to reopen and export editable source plus native PNG. Deliver the `.aseprite`, PNG, scene/generation metadata, and optional nearest-neighbor preview. Retain explicit caveats from review.

The examples under `examples/` show real earlier and refined outputs. `docs/visual-review.md` explains their strengths and limitations. Use them as evidence of decisions, not templates to copy indiscriminately.

## Invariants

Use integer coordinates, opaque palette colors and transparent empty pixels; no anti-aliasing, blur, uncontrolled dithering, or random pixel noise. Use named semantic layers, connected forms, selective one-pixel contours and upper-left lighting. Aseprite is the renderer/source of truth. An installed MCP server can expose the tools directly; otherwise the CLI's real stdio client is the supported transport. Run `doctor` to verify availability before claiming it works.

Keep `Reference`, local configs, source-derived sheets, crops, filenames and paths private. Only original outputs and generalized style rules belong in a public repository. Generation with `--references` writes private selection metadata: do not publish it. A later skill invocation does not itself authorize publishing or messaging anyone.

For persistent orchestration use the project's pinned Ruflo MCP bridge (`scripts/ruflo.py`), discover its tools first and record actual results. Ruflo stores coordination and memory; registered agents alone are not running LLM workers. See `docs/ruflo.md` for the verified execution boundary.
