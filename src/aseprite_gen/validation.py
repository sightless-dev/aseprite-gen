"""Technical pixel invariants and descriptive metrics, never an art-quality score."""
from collections import Counter, deque
from pathlib import Path

from PIL import Image


def review_png(path, *, expected_size=None, palette=None, max_colors=24):
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
    pixels = list(image.getdata())
    colors = Counter(p for p in pixels if p[3])
    errors, warnings = [], []
    if expected_size and tuple(expected_size) != image.size:
        errors.append("Unexpected canvas dimensions")
    if any(p[3] not in (0, 255) for p in pixels):
        errors.append("Partial alpha pixels found")
    if not colors:
        errors.append("Empty sprite")
    if len(colors) > max_colors:
        errors.append(f"Color budget exceeded: {len(colors)} > {max_colors}")
    if not any(p[3] == 0 for p in pixels):
        errors.append("No transparent background")
    if palette:
        allowed = {tuple(bytes.fromhex(c.lstrip('#')[:6])) for c in palette}
        if any(c[:3] not in allowed for c in colors):
            errors.append("Pixels outside the selected palette")
    visible = {i for i,p in enumerate(pixels) if p[3]}
    def neighbors(i):
        x,y=i%width,i//width
        return [ny*width+nx for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]
                if 0<=nx<width and 0<=ny<height]
    pending=set(visible); component_sizes=[]
    while pending:
        start=pending.pop(); queue=deque([start]); count=0
        while queue:
            current=queue.popleft();count+=1
            for nxt in neighbors(current):
                if nxt in pending:
                    pending.remove(nxt);queue.append(nxt)
        component_sizes.append(count)
    isolated_color=sum(not any(pixels[j] == pixels[i] for j in neighbors(i)) for i in visible)
    if len(component_sizes)>1:
        warnings.append("Disconnected silhouette components: inspect intentional gaps versus stray pixels")
    if isolated_color/max(1,len(visible))>.08:
        warnings.append("Many single-color pixels: inspect highlights and potential noise")
    if any(pixels[y*width+x][3] for x,y in
           [(x,0) for x in range(width)]+[(x,height-1) for x in range(width)]+
           [(0,y) for y in range(height)]+[(width-1,y) for y in range(height)]):
        warnings.append("Silhouette touches canvas edge")
    return {"path":str(Path(path).resolve()),"width":width,"height":height,"colors":len(colors),
            "visible_pixels":len(visible),"transparent_pixels":len(pixels)-len(visible),
            "silhouette_component_sizes":sorted(component_sizes,reverse=True),
            "singleton_color_pixels":isolated_color,"singleton_color_fraction":round(isolated_color/max(1,len(visible)),4),
            "errors":errors,"warnings":warnings,"technical_pass":not errors,
            "artistic_verdict":"unreviewed: view native and nearest-neighbor previews; metrics cannot approve art"}


def preview(path, output, scale=6):
    if not isinstance(scale,int) or not 1<=scale<=16:
        raise ValueError("Preview scale must be an integer from 1 to 16")
    with Image.open(path) as image:
        image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST).save(output)
    return str(Path(output).resolve())
