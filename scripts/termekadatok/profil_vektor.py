"""Profil-keresztmetszetek pontos, vektoros újrarajzolása a gyártói méretezett rajz méretei alapján.

A szkennelt (recés, törésvonallal rövidített) rajzok helyett a profil falát a középvonal és a falvastagság
alapján szerkesztjük meg: a középvonal egyenes szakaszokból és a rajzon megadott lekerekítési sugarú ívekből
áll, a falat a középvonal ± fél falvastagságú eltolása adja (shapely). Az eredmény precíz egyenes élekből és
szabályos ívekből áll. Mértékegység: mm, az origó a profil bal felső külső sarka, az y lefelé nő.
"""

import math

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union


def fillet(points, radius):
    """Töröttvonal belső töréspontjainak lekerekítése (radius: szám vagy töréspontonkénti lista, 0 = éles)."""
    pts = [np.array(p, float) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * (len(pts) - 2)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        r = radii[i - 1]
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u, v = (a - b) / np.linalg.norm(a - b), (c - b) / np.linalg.norm(c - b)
        ang = math.acos(max(-1.0, min(1.0, float(u @ v))))
        if r <= 0 or ang > math.pi - 1e-6:
            out.append(b)
            continue
        t = r / math.tan(ang / 2)  # az érintési pontok távolsága a töréspontól
        p1, p2 = b + u * t, b + v * t
        bis = (u + v) / np.linalg.norm(u + v)
        center = b + bis * (r / math.sin(ang / 2))
        a1, a2 = math.atan2(*(p1 - center)[::-1]), math.atan2(*(p2 - center)[::-1])
        d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(17):
            ak = a1 + d * k / 16
            out.append(center + r * np.array([math.cos(ak), math.sin(ak)]))
    out.append(pts[-1])
    return [tuple(p) for p in out]


def arc(cx, cy, r, a0, a1, n=24):
    """Ív pontjai (fokban megadott kezdő- és végszöggel)."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def wall(points, t):
    """Fal: a középvonal ± t/2 eltolása, lekerekített végekkel és csatlakozásokkal."""
    return LineString(points).buffer(t / 2, cap_style="round", join_style="round", quad_segs=16)


def profile_202388():
    """Constellium 12388 (Quadris 202388, 15/70 keretprofil) – Transport2024, 54. oldal méretei:
    befoglaló 40 (felső rész) × 109, általános falvastagság 2,5; felső horony [13] / 12,8 / 6,4, 20°-os ferde fal,
    R4,5/R5 ívek; jobb oldali fal 4°-os dőléssel [15,5] mélyen, rajta 25 mm-es, 3 mm-es vízszintes szár;
    alul [27,5] hosszú, 3 mm-es szár 4,8-as gömbvéggel, alatta R25-ös ívelt horog, a horog alja 109-nél."""
    t = 2.5
    h = t / 2
    top = fillet([
        (h, 90.5),                 # a bal fal alja (az alsó szárnál)
        (h, h),                    # bal felső sarok
        (14.25, h),                # a horony bal fala
        (14.25, 9.25),             # horony alja
        (26.6, 9.25),
        (29.55, h),                # 20°-os ferde fal
        (38.75, h),                # jobb felső sarok
        (37.7, 17.0),              # 4°-os dőlésű jobb fal
        (64.0, 17.0),              # jobb oldali vízszintes szár (vége lent külön)
    ], [2.25, 3.0, 5.75, 5.75, 3.0, 2.25, 1.0])
    parts = [wall(top[:-1], t), LineString(top[-2:]).buffer(1.5, cap_style="flat", join_style="round")]  # a szár 3 mm
    parts.append(Point(64.0 - 0.5, 17.0).buffer(1.5))  # a szár lekerekített vége
    # alsó szár (3 mm) gömbvéggel
    parts.append(LineString([(h, 90.5), (25.1, 90.5)]).buffer(1.5, cap_style="flat"))
    parts.append(Point(25.1, 90.5).buffer(2.4))
    # a bal fal lefelé folytatódik, majd R25-ös ívben (a középvonal sugara 26,25) jobbra hajló horog
    hook = [(h, 90.5)] + arc(h + 25 + h, 92.0, 25 + h, 180, 142.5)
    parts.append(wall(hook, t))
    return unary_union(parts)


def profile_226915n():
    """226915/n (30 mm-es U szegő, natúr) – a szkennelt Constellium-rajz méretei: külső szélesség 35,5, magasság 40,
    falvastagság a rajzon mérve kb. 2,5 mm, a külső alsó sarkok lekerekítettek."""
    t = 2.5
    h = t / 2
    line = fillet([(h, 0), (h, 40 - h), (35.5 - h, 40 - h), (35.5 - h, 0)], 2.0)
    return LineString(line).buffer(h, cap_style="flat", join_style="round", quad_segs=16)


VECTOR = {"202388-15-70-mm-keretprofil-elox-cd": profile_202388, "226915-n-30-mm-u-szego-profil": profile_226915n}


def rasterize(geom, ppm, pad):
    """A geometria bináris maszkja (ppm képpont/mm, pad mm margó) és a befoglaló (px) a maszkon."""
    import cv2
    x0, y0, x1, y1 = geom.bounds
    w, h = int((x1 - x0 + 2 * pad) * ppm), int((y1 - y0 + 2 * pad) * ppm)
    mask = np.zeros((h, w), np.uint8)
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        ext = np.array([((x - x0 + pad) * ppm, (y - y0 + pad) * ppm) for x, y in poly.exterior.coords], np.int32)
        cv2.fillPoly(mask, [ext], 255, lineType=cv2.LINE_8)
        for ring in poly.interiors:
            hole = np.array([((x - x0 + pad) * ppm, (y - y0 + pad) * ppm) for x, y in ring.coords], np.int32)
            cv2.fillPoly(mask, [hole], 0)
    box = (int(pad * ppm), int(pad * ppm), int((x1 - x0 + pad) * ppm), int((y1 - y0 + pad) * ppm))
    return mask > 0, box
