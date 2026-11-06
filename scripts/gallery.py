"""Compose original examples; optional reference comparison stays under .local."""
import argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]


def font(size):
    for name in ["C:/Windows/Fonts/segoeui.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(name).is_file():return ImageFont.truetype(name,size)
    return ImageFont.load_default(size=size)


def paste(canvas,path,box,scale):
    with Image.open(path) as source:
        im=source.convert("RGBA");im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
        x,y,w,h=box
        canvas.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2),im)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--reference-atlas",type=Path,help="Optional private atlas, never copied to public output");args=parser.parse_args()
    out=ROOT/"examples";bg="#ece8dc";ink="#223c36"
    canvas=Image.new("RGB",(1120,1010),bg);d=ImageDraw.Draw(canvas)
    d.text((35,23),"ASEPRITE GEN / ORIGINAL STUDIES",font=font(28),fill=ink)
    d.text((35,64),"Native resolution     /     Sparse first pass     /     Reviewed layer refinements",font=font(18),fill="#637369")
    descriptions=["Grouped foliage and an irregular crown edge","Denser light clusters and directional bark","Interrupted rim highlights and stave grain"]
    for row,kind in enumerate(["bush","tree","barrel"]):
        y=110+row*285;d.rounded_rectangle((25,y,1095,y+270),radius=14,fill="#faf7ee")
        d.text((45,y+12),kind.upper(),font=font(18),fill=ink)
        d.text((330,y+12),"BEFORE",font=font(14),fill="#7a766c");d.text((740,y+12),"REFINED",font=font(14),fill="#406847")
        scale=3 if kind=="tree" else 6
        paste(canvas,out/f"{kind}.png",(40,y+50,180,170),1)
        paste(canvas,out/f"{kind}-before.png",(280,y+35,330,235),scale)
        paste(canvas,out/f"{kind}.png",(690,y+35,330,235),scale)
        d.text((45,y+230),"1x / transparent PNG",font=font(12),fill="#7a766c")
    d.text((35,980),"Model visual review is subjective. Earlier versions and editable sources are preserved.",font=font(15),fill="#637369")
    canvas.save(out/"comparison.png")
    hero=Image.new("RGB",(1000,540),ink);d=ImageDraw.Draw(hero)
    d.text((35,25),"THE ORCHARD SET",font=font(30),fill="#f1ddae")
    d.text((36,70),"Original pixel studies / editable Aseprite layers",font=font(17),fill="#a9b9a5")
    for kind,box,scale,label in [("bush",(40,150,260,280),5,"BERRY BUSH  /  48 x 32"),("tree",(350,115,310,340),4,"OLD OAK  /  64 x 80"),("barrel",(710,150,250,280),6,"WOODEN CASK  /  32 x 40")]:
        paste(hero,out/f"{kind}.png",box,scale)
        d.text((box[0],470),label,font=font(15),fill="#f1ddae")
    hero.save(out/"gallery.png")
    cards="".join(f'<article><h2>{k.title()}</h2><img class="large" src="{k}.png" alt="Original {k} pixel sprite"><p>{desc}</p><img src="{k}.png" alt="Native size"><p><a href="{k}.aseprite">Editable source</a> · <a href="{k}.scene.json">Scene</a> · <a href="{k}.review.json">Review</a></p></article>' for k,desc in zip(["bush","tree","barrel"],descriptions))
    (out/"index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aseprite Gen — original studies</title><style>body{margin:3rem auto;max-width:1100px;padding:0 1rem;background:#ece8dc;color:#223c36;font:17px system-ui}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}article{background:#faf7ee;border-radius:16px;padding:24px}img{image-rendering:pixelated}.large{width:auto;height:240px;max-width:100%;object-fit:contain}a{color:#325d48}.comparison{width:100%;margin-top:2rem}</style><h1>The Orchard Set</h1><p>Original sprites generated and refined through Aseprite MCP. Native images, editable sources and honest review evidence.</p><main>'+cards+'</main><img class="comparison" src="comparison.png" alt="Native, initial and refined sprites"><p>Technical checks do not establish artistic approval. Outputs remain simpler and darker than the private reference group. No private reference images are included here.</p></html>',encoding="utf-8")
    if args.reference_atlas:
        private=ROOT/".local/review";private.mkdir(parents=True,exist_ok=True)
        comp=Image.new("RGB",(1120,1560),bg);comp.paste(canvas,(0,550));d=ImageDraw.Draw(comp)
        d.text((35,20),"PRIVATE REFERENCE COMPARISON / DO NOT PUBLISH",font=font(23),fill=ink)
        atlas=Image.open(args.reference_atlas).convert("RGBA")
        for crop,pos,scale in [((0,0,256,112),(30,75),3),((304,928,368,976),(815,130),4)]:
            im=atlas.crop(crop);im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST);comp.paste(im,pos,im)
        d.text((35,450),"Reference: finer, brighter leaf structure. Outputs: broader and more muted clusters.",font=font(20),fill=ink)
        comp.save(private/"reference-comparison.png")
    print(out/"gallery.png")


if __name__=="__main__":main()
