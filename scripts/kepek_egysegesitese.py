# Rajz jellegű első termékképek egységesítése: tartalomra vágás + egyenletes margó, hajszálvonalas rajzok vastagítása.
# kepek_egysegesitese.py <kimeneti mappa> <felmérés.json>   (az eredetikhez nem nyúl; a kimenetet kell a public/termekkepek alá másolni)
import json,sys,os
import numpy as np, cv2
from PIL import Image
out=sys.argv[1]; os.makedirs(out,exist_ok=True)
rows=json.load(open(sys.argv[2]))  # képfelmérés: [csoport, típus, _, _, slug]
d={p['slug']:p for p in json.load(open('dist/kereso-index.json'))['products']}
PROFILE_GROUPS={'aluminium-alvaz-profilok','aluminium-padlo-profilok','ponyvas-oldalfal-profilok-es-szegok','zart-dobozos-es-hutos-profilok','acel-profilok','acel-es-alu-rakoncak-es-szegok'}
done=set(); n=thick=0
for g,kind,_,_,slug in rows:
    if kind!='drawing': continue
    im=d[slug]['image']
    if im in done or not im.startswith('/termekkepek/') or '/3d/' in im: continue
    done.add(im)
    rgb=np.asarray(Image.open('public'+im).convert('RGB'))
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    ys,xs=np.where(gray<235)
    if len(xs)<50: continue
    x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max(); side=max(x1-x0,y1-y0)+1
    dark=(gray<160).astype(np.uint8)
    dist=cv2.distanceTransform(dark,cv2.DIST_L2,3)
    w=2*np.percentile(dist[dark>0],90) if dark.any() else 0   # jellemző vonalvastagság (képpont)
    target=side*0.011
    work=rgb
    if w<target*0.75 and g in PROFILE_GROUPS:
        k=int(round((target-w)/2)); k=max(1,min(k,4))
        ker=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*k+1,2*k+1))
        g2=cv2.erode(gray,ker)
        g2=np.clip((g2.astype(float)-30)*255/(200-30),0,255).astype(np.uint8)  # szürke vonalak feketítése
        work=cv2.cvtColor(g2,cv2.COLOR_GRAY2RGB); thick+=1; open(out+"/_thick.txt","a").write(os.path.basename(im)+"\n")
        x0,y0=max(0,x0-k),max(0,y0-k); x1,y1=min(gray.shape[1]-1,x1+k),min(gray.shape[0]-1,y1+k)
    crop=work[y0:y1+1,x0:x1+1]; m=int(round(max(crop.shape[:2])*0.035))
    canvas=np.full((crop.shape[0]+2*m,crop.shape[1]+2*m,3),255,np.uint8); canvas[m:m+crop.shape[0],m:m+crop.shape[1]]=crop
    Image.fromarray(canvas).save(os.path.join(out,os.path.basename(im)),quality=90,method=6); n+=1
print('feldolgozva',n,'vastagítva',thick)
