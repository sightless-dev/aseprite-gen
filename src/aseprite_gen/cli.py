"""Command-line workflows; generation and editing always cross actual MCP stdio."""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import sys

from .analysis import analyze, select_references
from .generation import plan
from .protocol import call_tool, call_tool_raw, list_tools
from .validation import preview, review_png


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")


def generate(args, seed=None, name=None):
    scene, metadata=plan(args.prompt,kind=args.kind,width=args.size[0] if args.size else None,
                         height=args.size[1] if args.size else None,seed=args.seed if seed is None else seed,
                         profile=args.profile,detail=not args.draft)
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    name=name or args.name
    result=call_tool("render_scene",{"scene":scene,"output_name":name},output)
    metadata.update({"render":result,"review":review_png(result["png_path"],expected_size=(scene["width"],scene["height"]),palette=scene["palette"])})
    if args.references:
        manifest=analyze(args.references,Path(".local/analysis"))
        metadata["private_reference_selection"]=[{"path":e["path"],"sha256":e["sha256"]} for e in select_references(manifest,args.prompt)]
        metadata["privacy"]="Contains private reference paths; do not publish this metadata"
    write_json(output/f"{name}.scene.json",scene)
    portable=json.loads(json.dumps(metadata))
    for key in ("aseprite_path","png_path"):
        portable["render"][key]=Path(portable["render"][key]).name
    portable["review"]["path"]=Path(portable["review"]["path"]).name
    write_json(output/f"{name}.generation.json",portable)
    preview(result["png_path"],output/f"{name}.preview.png")
    return metadata


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("analyze");p.add_argument("references",type=Path);p.add_argument("--output",default=".local/analysis")
    for command in ("generate","variations","plan"):
        p=sub.add_parser(command);p.add_argument("prompt");p.add_argument("--kind",choices=["bush","tree","barrel"])
        p.add_argument("--size",nargs=2,type=int,metavar=("WIDTH","HEIGHT"));p.add_argument("--seed",type=int,default=0)
        p.add_argument("--profile",type=Path);p.add_argument("--output",default="output");p.add_argument("--name",default="sprite")
        p.add_argument("--draft",action="store_true",help="Sparse cluster pass for an actual before/after workflow")
        p.add_argument("--references",type=Path,help="Optional PRIVATE local reference selection metadata")
        if command=="variations":p.add_argument("--count",type=int,default=3)
    p=sub.add_parser("render");p.add_argument("scene",type=Path);p.add_argument("--output",default="output");p.add_argument("--name",required=True)
    p=sub.add_parser("review");p.add_argument("path",type=Path);p.add_argument("--output",default="output");p.add_argument("--scale",type=int,default=6)
    p=sub.add_parser("refine");p.add_argument("path",type=Path);p.add_argument("operations",type=Path);p.add_argument("--layer",required=True);p.add_argument("--name",required=True);p.add_argument("--output",default="output")
    p=sub.add_parser("export");p.add_argument("path",type=Path);p.add_argument("--name",required=True);p.add_argument("--output",default="output")
    sub.add_parser("doctor")
    args=parser.parse_args(argv)
    try:
        if args.command=="analyze":
            manifest=analyze(args.references,args.output); result={"run":manifest["run"],"counts":manifest["counts"],"output":str(Path(args.output).resolve())}
        elif args.command=="plan":
            scene,metadata=plan(args.prompt,kind=args.kind,width=args.size[0] if args.size else None,height=args.size[1] if args.size else None,seed=args.seed,profile=args.profile,detail=not args.draft)
            directory=Path(args.output);directory.mkdir(parents=True,exist_ok=True)
            target=directory/f"{args.name}.scene.json"
            if target.exists():raise FileExistsError(target)
            write_json(target,scene);result={"scene":str(target),"metadata":metadata,"rendered":False}
        elif args.command=="generate":result=generate(args)
        elif args.command=="variations":
            if not 1<=args.count<=12:raise ValueError("Variation count must be 1..12")
            result=[generate(args,seed=args.seed+i,name=f"{args.name}-{i+1:02}") for i in range(args.count)]
        elif args.command=="render":result=call_tool("render_scene",{"scene":json.loads(args.scene.read_text()),"output_name":args.name},args.output)
        elif args.command=="doctor":result={"editor":call_tool("editor_status",{}),"tools":[t["name"] for t in list_tools()]}
        elif args.command=="review":
            reply=asyncio.run(call_tool_raw("inspect_sprite",{"path":str(args.path.resolve()),"scale":1},args.output))
            result=reply.structuredContent
            native=Path(args.output)/(args.path.stem+".review-native.png")
            native.write_bytes(base64.b64decode(next(c.data for c in reply.content if c.type=="image")))
            result["technical_review"]=review_png(native)
            result["preview"]=preview(native,Path(args.output)/(args.path.stem+".preview.png"),args.scale)
        elif args.command=="refine":
            result=call_tool("refine_sprite",{"path":str(args.path.resolve()),"layer":args.layer,
                          "operations":json.loads(args.operations.read_text()),"output_name":args.name},args.output)
        else:result=call_tool("export_sprite",{"path":str(args.path.resolve()),"output_name":args.name},args.output)
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (ValueError,RuntimeError,OSError) as error:
        print(f"aseprite-gen: {error}",file=sys.stderr);return 1


if __name__=="__main__":
    raise SystemExit(main())
