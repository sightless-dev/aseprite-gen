"""Replay archived revision-1 correction arrays, independently of the current style."""
import json
from pathlib import Path
from aseprite_gen.protocol import call_tool
from aseprite_gen.validation import preview, review_png

root=Path(__file__).resolve().parents[1]
output=root/"examples"
for kind,prompt in [("bush","berry bush"),("tree","old oak tree"),("barrel","weathered wooden barrel")]:
    scene=json.loads((output/f"{kind}-detailed.scene.json").read_text())
    correction={"name":"art direction","operations":json.loads((output/f"{kind}.corrections.json").read_text())}
    source=output/f"{kind}-detailed.aseprite"
    result=call_tool("refine_sprite",{"path":str(source),"layer":correction["name"],"operations":correction["operations"],"output_name":kind},output)
    # Preserve the exact earlier scene plus the applied patch for reproducibility.
    actual=json.loads((output/f"{kind}-detailed.scene.json").read_text())
    actual["layers"].append(correction)
    (output/f"{kind}.scene.json").write_text(json.dumps(actual,indent=2))
    (output/f"{kind}.corrections.json").write_text(json.dumps(correction["operations"],indent=2))
    metrics=review_png(result["png_path"],expected_size=(scene["width"],scene["height"]),palette=scene["palette"])
    metrics["path"]=Path(metrics["path"]).name
    (output/f"{kind}.review.json").write_text(json.dumps(metrics,indent=2))
    preview(result["png_path"],output/f"{kind}.preview.png")
    print(kind,metrics["technical_pass"],result["layer_names"])
