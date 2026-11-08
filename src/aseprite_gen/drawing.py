"""Native-grid construction: overlapping leaves, bark ribbons and curved staves.

These are original shapes. Reference pixels are never read by this renderer.
"""
import math


def _leaf(s, x, y, width, length, angle, ramp, value):
    """Hand-constructed native-pixel leaf planes, with no hollow highlight loops."""
    patterns = [
        ("..b..", ".bhb.", "bhmmb", "bhmmd", ".mmdd", ".mbd.", "..d.."),
        ("..bb..", ".bhmb.", "bhmmmb", "bhmmmd", ".bmmdd", "..mbd.", "...d.."),
        ("..b..", ".bhb.", "bhmmb", "bmmmd", "bmmdd", ".mbd.", ".bd..", "..d.."),
    ]
    pattern=patterns[2 if length>=8 else (int(x)+int(y)+width)%2]
    colors={"d":ramp[max(0,value-4)],"b":ramp[max(1,value-2)],
            "m":ramp[max(2,value-1)],"h":ramp[min(len(ramp)-1,value+1)]}
    flip=angle<0
    for row,text in enumerate(pattern):
        if flip:text=text[::-1]
        shear=round((row-(len(pattern)-1)/2)*math.sin(angle)*.65)
        col=0
        while col<len(text):
            token=text[col];end=col+1
            while end<len(text) and text[end]==token:end+=1
            if token!=".":s.rect(round(x)-len(text)//2+col+shear,round(y)-len(pattern)//2+row,end-col,1,colors[token])
            col=end


def _canopy(s, center, radius, ramp, rng, settings, detail, branch=None, shape_power=2):
    cx,cy = center
    rx,ry = radius
    phase = rng.uniform(-.8,.8)
    def edge(theta):
        return 1+.045*math.sin(5*theta+phase)+.028*math.sin(9*theta-1.1)
    def contour(theta):
        a,b=math.cos(theta),math.sin(theta)
        return (math.copysign(abs(a)**(2/shape_power),a),
                math.copysign(abs(b)**(2/shape_power),b))
    s.layer("canopy depth")
    outline=[]
    for i in range(52):
        angle=i*math.tau/52
        a,b=contour(angle)
        outline.append((cx+rx*a*edge(angle),cy+ry*b*edge(angle)))
    s.poly(outline,ramp[0])
    s.poly([(cx+(x-cx)*.95-1,cy+(y-cy)*.94-1) for x,y in outline],ramp[1])
    s.poly([(cx+(x-cx)*.83-2,cy+(y-cy)*.8-3) for x,y in outline],ramp[2])
    s.layer("leaf shadow clusters")
    # Quiet overlapping leaves keep gaps between the lit sprays from reading flat.
    understory=[]
    for _ in range(round(rx*ry*5)):
        x,y=rng.uniform(-.96,.96),rng.uniform(-.96,.96)
        if abs(x)**shape_power+abs(y)**shape_power>.94:continue
        px,py=cx+x*rx,cy+y*ry
        if any((px-a)**2+(py-b)**2<12 for a,b in understory):continue
        understory.append((px,py))
    for x,y in sorted(understory,key=lambda p:p[1]):
        _leaf(s,x,y,5,7,(x-cx)/rx*.5,ramp,3)
    # Individual edge leaves break the smooth ellipse into a foliage silhouette.
    for i in range(round((rx+ry)*.72)):
        theta=i*math.tau/round((rx+ry)*.72)
        a,b=contour(theta)
        x=cx+rx*a*edge(theta)*.97
        y=cy+ry*b*edge(theta)*.97
        value=5 if math.sin(theta)<-.25 else 3
        _leaf(s,x,y,5,7,math.cos(theta)*.7,ramp,value)
    if branch:
        s.layer("inner branches")
        branch()
    s.layer("overlapping leaves")
    # Rejection-sampled centres avoid the old repeated rows and diagonal bands.
    spacing=settings["spacing"]*2.05
    count=round(math.pi*rx*ry/(spacing*spacing)*(.84 if detail else .4))
    centers=[]
    for _ in range(count*90):
        x,y=rng.uniform(-.96,.96),rng.uniform(-.96,.96)
        if abs(x)**shape_power+abs(y)**shape_power>.94**2:
            continue
        px,py=cx+x*rx,cy+y*ry
        if any((px-a)**2+(py-b)**2<spacing**2 for a,b in centers):
            continue
        centers.append((px,py))
        if len(centers)>=count:
            break
    centers.sort(key=lambda p:p[1])
    leaves=[]
    for gx,gy in centers:
        tilt=(gx-cx)/rx
        spray=[(-2,-2),(2,0),(-1,4)]
        if gy<cy and rng.random()<.5:spray.append((3,-5))
        for dx,dy in spray:
            x,y=gx+dx+tilt*dy*.3,gy+dy
            if abs((x-cx)/rx)**shape_power+abs((y-cy)/ry)**shape_power>1.02:continue
            leaves.append((x,y))
    for x,y in sorted(leaves,key=lambda p:p[1]):
        nx,ny=(x-cx)/rx,(y-cy)/ry
        volume=math.sqrt(max(0,1-nx*nx-ny*ny))
        fold=.28*math.sin(nx*8+ny*3)+.22*math.cos(ny*10-nx*2)
        lit=3.2+1.7*volume-1.15*ny-.6*nx+fold
        value=max(3,min(len(ramp)-2,round(lit)))
        width=rng.randint(*settings["width"])
        length=rng.randint(*settings["length"])
        angle=nx*.5+rng.uniform(-.3,.3)
        _leaf(s,x,y,width,length,angle,ramp,value)


def bush(s,p,rng,spec,detail):
    f=p["palette"]["autumn" if spec["autumn"] else "foliage"]
    wood=p["palette"]["wood"]
    cfg=p["geometry"]["bush"]
    cx,cy,rx,ry=cfg["crown"]
    cx+=rng.choice([-1,0,1])
    s.layer("woody stems")
    s.poly([(cx-4,42),(cx-2,33),(cx+2,31),(cx+5,42),(cx+2,44),(cx,38),(cx-2,44)],wood[0])
    s.line(cx-1,40,cx,34,wood[3])
    def branches():
        s.line(cx,38,cx-5,24,wood[1]);s.line(cx-3,30,cx-9,26,wood[2])
        s.line(cx,34,cx+7,23,wood[1])
    _canopy(s,(cx,cy),(rx,ry),f,rng,p["leaf_clusters"],detail,branches,cfg.get("shape_power",2.6))
    if spec["berries"]:
        s.layer("berry accents")
        b=p["palette"]["berries"]
        for x,y in [(cx-10,cy),(cx+6,cy-7),(cx+9,cy+7)]:
            s.ellipse(x,y,3,3,b[0]);s.rect(x,y,2,2,b[1]);s.rect(x,y,1,1,b[2])


def tree(s,p,rng,spec,detail):
    wood=p["palette"]["wood"]
    f=p["palette"]["autumn" if spec["autumn"] else "tree_foliage"]
    cx,cy,rx,ry=p["geometry"]["tree"]["crown"]
    lean=rng.choice([-2,-1,1,2])
    if spec["young"]:rx*=.78;ry*=.83;cy+=6
    s.layer("trunk and roots")
    # Slender taper, unequal roots and branching shoulders avoid the old stump shape.
    s.poly([(28,48),(36,47),(37,64),(35,74),(37,84),(44,90),(43,93),
            (37,91),(33,86),(30,89),(28,94),(25,94),(27,87),(21,92),(18,91),
            (24,85),(27,77),(28,65)],wood[0])
    s.poly([(30,51),(34,49),(34,67),(32,78),(35,86),(40,90),(36,89),
            (31,84),(28,91),(29,83),(24,89),(28,77)],wood[2])
    s.poly([(30,55),(32,53),(31,69),(30,78),(32,84),(30,87),(28,83),(29,72)],wood[4])
    s.poly([(30,58),(31,58),(30,71),(30,78),(29,80),(29,74)],wood[6])
    s.poly([(30,82),(32,85),(31,90),(28,94),(28,91),(29,87)],wood[3])
    s.line(30,86,29,91,wood[5])
    s.line(33,68,32,72,wood[2]);s.line(34,74,34,78,wood[3])
    s.line(30,74,31,77,wood[5]);s.line(30,80,31,83,wood[4])
    # Bark follows several interrupted, crooked longitudinal ribbons.
    for pts,color in [([(34,57),(33,65),(34,68),(32,73)],wood[1]),
                      ([(28,63),(29,66),(28,70)],wood[3]),
                      ([(32,76),(33,81),(32,84)],wood[1]),
                      ([(28,82),(26,87),(23,89)],wood[4]),
                      ([(34,84),(36,88),(40,91)],wood[4])]:
        for (x,y),(x2,y2) in zip(pts,pts[1:]):s.line(x,y,x2,y2,color)
    if detail:
        for y in range(55,84,4):
            x=29+rng.randrange(4)
            s.line(x,y,x+1,y+1,wood[3 if x>30 else 5])
    def branches():
        s.poly([(30,65),(23,54),(18,43),(20,43),(26,52),(32,58),(37,51),
                (44,36),(46,36),(41,52),(35,63)],wood[1])
        s.line(23,49,29,57,wood[3]);s.line(36,56,41,46,wood[2])
        s.line(31,56,30,36,wood[1])
    _canopy(s,(cx+lean,cy),(rx,ry),f,rng,p["leaf_clusters"],detail,branches)


def barrel(s,p,rng,spec,detail):
    w=p["palette"]["barrel_wood"]
    m=p["palette"]["metal"]
    s.layer("stave body")
    s.poly([(8,5),(22,5),(26,9),(28,16),(28,21),(26,27),(22,30),
            (10,30),(5,27),(3,22),(3,16),(5,9)],w[0])
    s.poly([(7,8),(24,8),(26,15),(26,23),(23,28),(19,29),(10,28),(6,25),(5,18)],w[2])
    # Projected stave boundaries are narrower at the sides of the cylinder.
    edges=[0,.1,.25,.43,.62,.8,.93,1]
    shades=[2,3,4,4,3,3,2]
    def point(u,y):
        bulge=1-((y-18)/14)**2
        left=5-1.5*bulge
        right=26+1*bulge
        return left+u*(right-left),y
    for i,(a,b) in enumerate(zip(edges,edges[1:])):
        shade=shades[i]
        poly=[point(a,10),point(b,10),point(b,18),point(b,24),point(b-.01,27),
              point(a+.01,27),point(a,24),point(a,18)]
        s.poly(poly,w[shade])
        if i:
            for ya,yb in [(13,19),(20,25)]:
                x,y=point(a,ya);x2,y2=point(a,yb);s.line(x,y,x2,y2,w[max(1,shade-2)])
        mid=a+(b-a)*.43
        s.poly([point(a+.025,14),point(mid,13),point(mid+.015,18),
                point(mid,23),point(a+.045,25),point(a+.03,20)],w[min(7,shade+1)])
        if detail and i in (1,2,4,5):
            y=17+rng.randrange(4);x,_=point(mid,y)
            s.line(x,y,x,y+2,w[max(1,shade-1)])
    s.layer("dark forged hoops")
    for y in (9,23):
        s.poly([(4,y),(7,y+2),(13,y+3),(20,y+3),(26,y+1),(27,y),
                (27,y+3),(23,y+5),(16,y+6),(8,y+5),(4,y+3)],m[0])
        s.poly([(5,y+1),(9,y+3),(16,y+4),(23,y+3),(26,y+1),
                (26,y+3),(22,y+4),(16,y+5),(9,y+4),(5,y+2)],m[1])
        s.line(7,y+2,11,y+3,m[2]);s.line(12,y+4,18,y+4,m[2])
        s.line(7,y+2,9,y+2,m[3])
    s.layer("wooden rim and lid")
    s.ellipse(5,2,22,11,w[0]);s.ellipse(5,2,21,9,w[4])
    s.ellipse(6,2,19,8,w[6]);s.ellipse(8,3,16,6,w[2]);s.ellipse(9,4,14,5,w[4])
    s.line(9,5,20,5,w[3]);s.line(10,7,22,7,w[2]);s.line(13,9,19,9,w[3])
    s.line(10,3,19,3,w[7]);s.line(7,5,7,7,w[7]);s.line(9,9,12,10,w[5])
    bung=16+rng.randrange(4)
    s.rect(bung,6,3,2,w[2]);s.rect(bung,6,2,1,w[5])
