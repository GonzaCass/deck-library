#!/usr/bin/env python3
"""Draw Deck Library's icon and the Steam artwork (flat shapes, no gradients) and render them with rsvg-convert."""
import pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent.parent
BG='#161616';SHELF='#393939';BLUE='#78a9ff';WHITE='#f4f4f4';EMBER='#ff8a3d'

def cards(x,y,scale=1.0,play=BG):
    """Three upright game cases on a shelf; the tallest carries a play triangle."""
    def s(v):return round(v*scale,2)
    return (f'<g transform="translate({x} {y})">'
     f'<rect x="{s(0)}" y="{s(56)}" width="{s(88)}" height="{s(216)}" rx="{s(14)}" fill="{BLUE}"/>'
     f'<rect x="{s(104)}" y="{s(0)}" width="{s(112)}" height="{s(272)}" rx="{s(16)}" fill="{WHITE}"/>'
     f'<path d="M{s(138)} {s(102)}L{s(138)} {s(170)}L{s(192)} {s(136)}Z" fill="{play}"/>'
     f'<rect x="{s(232)}" y="{s(80)}" width="{s(100)}" height="{s(192)}" rx="{s(14)}" fill="{EMBER}"/>'
     f'<rect x="{s(-20)}" y="{s(272)}" width="{s(372)}" height="{s(16)}" rx="{s(8)}" fill="{SHELF}"/></g>')

def svg(width,height,body):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{body}</svg>'

def text(x,y,size,anchor='start',spacing=0):
    return (f'<text x="{x}" y="{y}" font-family="Noto Sans" font-weight="700" font-size="{size}" letter-spacing="{spacing}" text-anchor="{anchor}">'
            f'<tspan fill="{WHITE}">Deck </tspan><tspan fill="{BLUE}">Library</tspan></text>')

def stacked(x,y,size,anchor='middle'):
    return (f'<text x="{x}" y="{y}" font-family="Noto Sans" font-weight="800" font-size="{size}" letter-spacing="6" text-anchor="{anchor}" fill="{WHITE}">DECK</text>'
            f'<text x="{x}" y="{y+size*1.05}" font-family="Noto Sans" font-weight="800" font-size="{size}" letter-spacing="6" text-anchor="{anchor}" fill="{BLUE}">LIBRARY</text>')

ART={
 'icon':svg(512,512,f'<rect width="512" height="512" rx="112" fill="{BG}"/>'+cards(88,112,1.0)),
 'portrait':svg(600,900,f'<rect width="600" height="900" fill="{BG}"/>'+cards(76,170,1.35)+stacked(300,690,104)),
 'banner':svg(920,430,f'<rect width="920" height="430" fill="{BG}"/>'+cards(70,60,1.0)+stacked(450,185,84,'start')),
 'hero':svg(3840,1240,f'<rect width="3840" height="1240" fill="{BG}"/><rect y="1000" width="3840" height="20" fill="{SHELF}"/>'
            +''.join(f'<rect x="{x}" y="{1000-h}" width="{w}" height="{h}" rx="22" fill="{c}" opacity="0.10"/>' for x,w,h,c in ((200,150,380,BLUE),(380,190,470,WHITE),(600,170,330,EMBER),(1000,160,420,WHITE),(1190,210,520,BLUE),(1430,150,360,EMBER),(1700,170,400,BLUE),(1900,200,500,WHITE),(2130,160,350,EMBER)))
            +cards(2640,374,2.3)),
 'logo':svg(1280,360,cards(20,40,1.0)+stacked(430,170,120,'start')),
}

def render():
    steam=ROOT/'assets/steam';steam.mkdir(parents=True,exist_ok=True)
    targets={'icon':[(ROOT/'assets/icon.svg',None),(ROOT/'assets/icon.png',512),(steam/'icon.png',256)],'portrait':[(steam/'portrait.png',None)],'banner':[(steam/'banner.png',None)],'hero':[(steam/'hero.png',None)],'logo':[(steam/'logo.png',None)]}
    for name,outputs in targets.items():
        source=steam/(name+'.svg') if name!='icon' else ROOT/'assets/icon.svg'
        source.write_text(ART[name])
        for path,size in outputs:
            if path.suffix=='.svg':continue
            command=['rsvg-convert','-o',str(path),str(source)]
            if size:command[1:1]=['-w',str(size),'-h',str(size)]
            subprocess.run(command,check=True)
    for name in ('portrait','banner','hero','logo'):(steam/(name+'.svg')).unlink()
if __name__=='__main__':render()
