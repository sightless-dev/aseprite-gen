"""Current original-art gallery; reference comparisons always remain private."""
import argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
KINDS=("bush","tree","barrel")


def font(size):
    for name in ["C:/Windows/Fonts/segoeui.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(name).is_file():return ImageFont.truetype(name,size)
    return ImageFont.load_default(size=size)


def paste(canvas,image,center_x,y,height,scale=4):
    image=image.convert("RGBA")
    image=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    canvas.paste(image,(center_x-image.width//2,y+(height-image.height)//2),image)


def comparison(output,atlas=None):
    private=atlas is not None
    canvas=Image.new("RGB",(1180 if private else 810,1160),"#d2ccc0")
    draw=ImageDraw.Draw(canvas)
    columns=[205,590,975] if private else [205,605]
    titles=["SUMMER REFERENCE","REJECTED VERSION","REBUILT VERSION"] if private else ["REJECTED VERSION","REBUILT VERSION"]
    for x,title in zip(columns,titles):draw.text((x-170,20),title,font=font(20),fill="#252b26")
    draw.text((30,55),"Same 4x pixel scale; object sizes are not normalized.",font=font(16),fill="#53594e")
    boxes=[(208,0,256,48),(0,0,48,96),(320,944,352,976)]
    for kind,box,y,h in zip(KINDS,boxes,[100,385,850],[270,450,245]):
        draw.rectangle((15,y,canvas.width-15,y+h),fill="#f0ece2")
        draw.text((32,y+10),kind.upper(),font=font(16),fill="#53594e")
        images=[]
        if private:
            crop=atlas.crop(box)
            if kind=="tree":
                # Exclude neighboring fruit/log objects only from this comparison crop.
                for neighbor in [(35,75,48,96),(0,60,19,80)]:crop.paste((0,0,0,0),neighbor)
            images.append(crop)
        images += [Image.open(ROOT/f"examples/{kind}.png"),Image.open(output/f"{kind}.png")]
        for x,im in zip(columns,images):paste(canvas,im,x,y+40,h-50)
    draw.text((30,1120),"Private reference comparison — do not publish." if private else "Original art only. Technical tests are not artistic approval.",font=font(16),fill="#53594e")
    return canvas


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--reference-atlas",type=Path);args=parser.parse_args()
    out=ROOT/"examples/summer-v2"
    comparison(out).save(out/"comparison.png")
    hero=Image.new("RGB",(900,560),"#eee8d8");draw=ImageDraw.Draw(hero)
    draw.text((30,20),"SUMMER STUDIES / REBUILT",font=font(28),fill="#253c2e")
    draw.text((30,60),"Original native-grid sprites rendered through Aseprite MCP",font=font(16),fill="#536550")
    for kind,x,title in zip(KINDS,[150,450,750],["BUSH · 48 x 48","TREE · 64 x 96","BARREL · 32 x 32"]):
        with Image.open(out/f"{kind}.png") as im:
            large=im.convert("RGBA").resize((im.width*4,im.height*4),Image.Resampling.NEAREST)
            hero.paste(large,(x-large.width//2,470-large.height),large)
        draw.text((x-100,500),title,font=font(16),fill="#253c2e")
    hero.save(out/"gallery.png")
    cards="".join(f'<article><h2>{kind.title()}</h2><img class="sprite" src="{kind}.png" alt="Rebuilt {kind}"><p><a href="{kind}.aseprite">Aseprite source</a> · <a href="{kind}.scene.json">Scene</a> · <a href="{kind}.review.json">Review</a></p></article>' for kind in KINDS)
    (out/"index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Summer pixel studies</title><style>body{max-width:1050px;margin:3rem auto;padding:0 1rem;background:#eee8d8;color:#253c2e;font:17px system-ui}main{display:flex;flex-wrap:wrap;gap:24px}article{background:#f8f4e8;padding:20px;border-radius:12px}.sprite{image-rendering:pixelated;max-width:100%}article:nth-child(1) .sprite{width:192px}article:nth-child(2) .sprite{width:256px}article:nth-child(3) .sprite{width:128px}a{color:#315c3e}.comparison{width:100%;image-rendering:pixelated}</style><h1>Summer studies — revision 2</h1><p>Rebuilt leaf structure, warm bark and convex staves. Earlier examples were rejected for style mismatch and remain available for comparison.</p><main>'+cards+'</main><img class="comparison" src="comparison.png" alt="Rejected and rebuilt original sprites at the same scale"><p>Remaining differences include a more regular canopy and simpler bark/grain. No claim of artist-level equivalence or human approval.</p></html>',encoding="utf-8")
    if args.reference_atlas:
        target=ROOT/".local/review/summer-comparison";target.mkdir(parents=True,exist_ok=True)
        with Image.open(args.reference_atlas) as atlas:comparison(out,atlas.convert("RGBA")).save(target/"revision-2-comparison.png")
    print(out/"gallery.png")


if __name__=="__main__":main()
