# Scene editing and image review

A scene is JSON: `width`, `height`, `palette` (`#RRGGBB` strings), and bottom-to-top `layers`. Each layer has a unique `name` and `operations`. Geometry is filled, integer and inclusive. Operations:

```json
{"op":"polygon","points":[[4,5],[14,5],[12,12],[6,12]],"color":"#397047"}
```

Other operations: `rect` / `ellipse` use `x,y,w,h`; `line` uses `x,y,x2,y2`; `pixel` uses `x,y`. All points must fit the canvas. `#00000000` erases the target layer only. See `docs/mcp.md` for limits. Never interpolate user prompts into Lua.

Refinement example: save an array of operations to a JSON file, then:

```powershell
python -m aseprite_gen.cli refine output/bush-v1.aseprite corrections.json --layer "art direction" --name bush-v2 --output output
python -m aseprite_gen.cli review output/bush-v2.aseprite --output output
```

View the returned image, rather than trusting the file's existence. Check:

1. Native scale: does the object read immediately, and is its baseline stable?
2. Silhouette: uneven but purposeful proportions, clean steps, no accidental disconnected pixels.
3. Masses: a clear light side, continuous shadow side, depth at overlaps; avoid concentric pillow shading.
4. Material: tapered leaf groups, interrupted wood grain, curved and narrow metal highlights.
5. Color: limited ramp per material; high contrast concentrated at important edges.
6. Comparison: describe the actual improvement and any remaining mismatch to the selected style group.

Use `review_png` warnings as prompts for inspection, not mandatory cleanup: a single-pixel eye, rivet or berry glint can be intentional. Preserve before/after images and a short reason for each revision. Iterate when a specific defect remains; do not claim human artistic approval from model self-review.
