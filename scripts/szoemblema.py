# QUADRIS szóembléma: vastag, szögletes, dőlt betűk körvonalként (Kanit Black Italic, OFL licenc) + a jobb végén felkanyarodó aláhúzás
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
f=TTFont('font/kanit-900i.ttf'); inst=f
gs=inst.getGlyphSet(); cmap=inst.getBestCmap(); H=inst['OS/2'].sCapHeight
extra=math.tan(math.radians(14))-math.tan(math.radians(abs(inst['post'].italicAngle)))   # a betűk kb. 14°-ban dőlnek
x=0; d=[]; track=6
for ch in 'QUADRIS':
    g=cmap[ord(ch)]; pen=SVGPathPen(gs,ntos=lambda v:f'{v:.0f}'); tp=TransformPen(pen,(1,0,-extra,-1,x+extra*H,H)); gs[g].draw(tp); d.append(pen.getCommands()); x+=gs[g].width+track
W=x-track+extra*H
sl=math.tan(math.radians(22)); gap=0.14*H; th=0.19*H; y0=H+gap; y1=y0+th; up=H-0.30*H
xl=0.21*W; xr=W+0.005*W; xin=xr-th*1.08
X=lambda xb,y: xb+sl*(y1-y)
poly=[(X(xl,y0),y0),(X(xin,y0),y0),(X(xin,up),up),(X(xr,up),up),(xr,y1),(xl,y1)]
line='M'+' L'.join(f'{a:.0f} {b:.0f}' for a,b in poly)+'Z'
pad=6; vbw=X(xr,up)+2*pad; vbh=y1+2*pad
letters=" ".join(d)
print(f'{vbw:.0f} {vbh:.0f}')
svg=f'<svg class="wordmark" xmlns="http://www.w3.org/2000/svg" viewBox="-{pad} -{pad} {vbw:.0f} {vbh:.0f}" aria-hidden="true" focusable="false"><path fill="currentColor" d="{letters}"/><path class="wm-line" d="{line}"/></svg>'
open('quadris-wordmark.svg','w').write(svg)
open('preview.html','w').write(f'<style>.wm-line{{fill:#f2462e}}</style><body style="margin:0"><div style="background:#f6f3ec;color:#0e4f55;padding:30px;width:700px">{svg}</div><div style="background:#0e4f55;color:#fff;padding:30px;width:700px">{svg}</div><div style="background:#f6f3ec;color:#0e4f55;padding:20px"><div style="width:170px">{svg}</div></div></body>')
