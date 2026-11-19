# QUADRIS szóembléma: vastag, szögletes, dőlt betűk körvonalként (Kanit Black Italic, OFL licenc) + a jobb végén
# felkanyarodó aláhúzás. A betűk szélessége, dőlése és a vonal arányai egy mintáról mért értékek (H = nagybetű-magasság).
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
f=TTFont('font/kanit-900i.ttf'); gs=f.getGlyphSet(); cmap=f.getBestCmap(); H=f['OS/2'].sCapHeight
KX=0.86                                                                  # vízszintes arány
SH=math.tan(math.radians(16))-math.tan(math.radians(abs(f['post'].italicAngle)))  # a betűk 16°-ban dőlnek
x=0; d=[]; track=0
for ch in 'QUADRIS':
    g=cmap[ord(ch)]; pen=SVGPathPen(gs,ntos=lambda v:f'{v:.0f}'); gs[g].draw(TransformPen(pen,(KX,0,SH,-1,x,H))); d.append(pen.getCommands()); x+=gs[g].width*KX+track
# a szó tényleges bal és jobb széle (körvonalból)
import re
xs=[float(a) for seg in d for a in re.findall(r'(-?\d+) -?\d+',seg)]
xL,xR=min(xs),max(xs); W=xR-xL
gap=0.165*H; th=0.162*H; up=0.275*H; k=0.577; kl=0.70; uw=0.22*H
y0=H+gap; y1=y0+th; yu=H-up
xb=xL+0.2325*W                       # a vonal bal alsó sarka
xo=xR-0.069*H                        # a felszár külső élének alja
X=lambda xbase,y: xbase+k*(y1-y)
poly=[(xb+kl*th,y0),(X(xo-uw,y0),y0),(X(xo-uw,yu),yu),(X(xo,yu),yu),(xo,y1),(xb,y1)]
line='M'+' L'.join(f'{a:.0f} {b:.0f}' for a,b in poly)+'Z'
pad=8; vx=xL-pad; vw=X(xo,yu)-xL+2*pad; vh=y1+2*pad
svg=f'<svg class="wordmark" xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.0f} -{pad} {vw:.0f} {vh:.0f}" aria-hidden="true" focusable="false"><path fill="currentColor" d="{" ".join(d)}"/><path class="wm-line" d="{line}"/></svg>'
open('quadris-wordmark.svg','w').write(svg); print(f'{vw:.0f}x{vh:.0f}', len(svg))
