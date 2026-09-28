"""Constellium Extrusions Děčín (korábban Alcan / Alusuisse / Aluminium Děčín) – alumínium profilok a gyártó
szkennelt profilrajzaiból (data/forras/constellium/constellium_transport2024*.pdf – a Quadris-nak küldött rajzok).

A két PDF-ben oldalanként (néhol kettő) egy-egy „PROFIL LISOVANÝ Č. <szám>” rajz van szövegréteg nélkül.
A profilszámokat tesseract OCR-rel és szemrevételezéssel azonosítottuk (az oldal -> profilszám index a
.cache/constellium/index.json fájlban); a Quadris beszállítói kódja (supplierCode) pontosan a profilszám.

Minden rajzból egy tisztított kép készül: csak a profil keresztmetszete és a fő befoglaló méretek (teljes
magasság, szélesség, falvastagság, ha egyértelműen jelölve van) maradnak meg; a szövegmező, keret, rádiuszok,
tűrések, részméretek, részletnézetek, szimmetriavonalak kimaradnak. A szkennelt kép fekete-fehérre van
küszöbölve; a profil körvonalát egy-egy kezdőpontból kiinduló összefüggő tartomány-kitöltéssel választjuk ki
(„seeds”), a megtartott méretek téglalapjait („keep”) hozzáadjuk, a körvonalhoz tapadó mutatóvonalakat és
tűréseket előtte kifehérítjük („blank”). Az adatok (kerület, anyag, folyóméter-tömeg, keresztmetszet,
profiltípus) a rajz szövegmezőjéből valók, kézzel ellenőrizve.

Kód nélküli Quadris-termékek (NO_CODE): a „Dobozos keret elox 134/80” a 11543-as (134 mm magas, a peremtől 80 mm),
a „Hűtős keretprofil nyitott elox” a 7971-es (OTEVŘENÝ = nyitott keretprofil) rajz – mindkettőnél a slug számrésze
is a profilszám vége (231543, 237971), ahogy a többi Constellium-terméknél.
Az Alu-SV-nél felvett 226915 „30 mm U szegő profil” a 6915-ös rajz (EXTRA_SLUGS).
Nem található a két PDF-ben: 8755 (talpas hossztartó 140/6) és 14230 (köztes 250 mm profil, natúr és elox).

Használat: python3 scripts/termekadatok/constellium.py [--debug KÓD KIMENET.png]
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Constellium rajz"
URL = "https://www.constellium.com"
SRC = ROOT / "data/forras/constellium"
PDFS = {"A": ("constellium_transport2024.pdf", "Transport2024"), "B": ("constellium_transport2024b.pdf", "Transport2024B")}
ZOOM = 250 / 72

# profilszám -> rajz: pdf (A/B), oldal, kivágás [pt], seeds = a profil körvonalának pontjai [pt],
# region = a körvonal ebből a területből marad meg, keep = megtartott méretek téglalapjai [pt], blank = előre kifehérítendő téglalapok / sokszögek [pt],
# draw = elhalványult méretvonalak pótlása; open / bridge / threshold / bold = a vonalszűrés beállításai
DRAWINGS = {
 "12386": dict(pdf="A", page=52, bold=3, crop=(100, 430, 740, 760), seeds=[(145, 600)], region=[(140, 452, 605, 650)],
   blank=[(555, 579, 579.5, 586)],
   keep=[(140, 705, 606, 730), (141, 648, 149, 730), (597, 648, 605, 730),  # 130
         (604, 452, 720, 460), (695, 452, 720, 650), (604, 641, 720, 650),  # 60
         (452, 588, 467, 611), (472, 588, 479, 665)]),  # 4,5
 "12387": dict(pdf="A", page=53, crop=(270, 330, 750, 840), seeds=[(380, 364), (400, 780), (527, 520), (549, 520)], region=None,
  blank=[(440, 715, 447, 732.5), (596, 720, 611, 732.8), (598, 748, 610.8, 758), (600, 779.5, 623, 795), (459, 770, 475, 782),
         [(641, 731), (655, 718), (662, 724), (646, 738)], (655, 709, 678.5, 714), (684, 709, 696, 714), (700.5, 709, 735, 714), (480, 809, 492, 819)],
  keep=[(365, 460, 716, 481), (365, 428, 371, 481), (709, 398, 715, 481),  # 50
        (378, 812, 704, 834), (379, 776, 385, 834), (696, 776, 702, 834),  # 46
        (281, 560.6, 296, 578.8), (296, 360, 301, 779), (296, 360, 372, 366), (296, 773, 385, 780)]),  # 70
 "10902": dict(pdf="A", page=49, crop=(130, 320, 545, 780), seeds=[(300, 400)], region=None, open=7,
  blank=[(160, 648, 175.5, 660), (163, 655, 176.3, 664.5), (451, 660, 458, 683), (451, 686, 458, 700), (480.5, 660, 487.5, 683), (480.5, 686, 487.5, 700), (508.5, 660, 515.5, 683)],
  keep=[(300, 321, 340, 339), (175, 333, 478, 339.5), (175, 333, 180, 660), (472, 333, 477.5, 400),  # 85
        (514, 528, 529, 560), (528, 398, 534, 687), (472, 398, 535, 403), (428, 682, 535, 687),  # 90
        (240, 499, 310, 518)]),  # 3
 "8652": dict(pdf="A", page=44, crop=(495, 185, 715, 500), seeds=[(555, 350)], open=3,
  region=[(549, 224, 672.5, 290), (549, 290, 604.3, 420), (552.8, 420, 604.3, 460)],
  blank=[(551.2, 344.5, 554.5, 349.5), (549, 351.5, 552.9, 355.5), (583.5, 434.8, 587.5, 438.6), (578, 395, 606, 431.8), (558, 440.9, 566, 446), (589, 442.3, 595, 450), (604.5, 441, 610, 448),
         (568.8, 452, 585, 466), (577, 441.5, 581, 460), (598, 268.2, 618.3, 291), (622.3, 268.2, 632, 291),
         (519, 229.2, 524, 240), (529, 229.2, 536, 240), (540, 229.2, 545, 240), (531, 449, 537, 456.8)],
  keep=[(498, 319, 506.3, 342), (506, 224, 509.5, 460), (505, 224, 552, 229), (505, 456.5, 560, 460),  # 126,5
        (548, 194, 622, 205.5), (548, 203, 552, 227), (618, 203, 622.5, 227),  # 40
        (618, 283, 672, 294.5), (668.5, 262, 672, 294.5), (618.5, 265, 622, 294.5)]),  # 28
 "12388": dict(pdf="A", page=54, crop=(70, 75, 520, 486), seeds=[(159.6, 133.2), (139.8, 363), (400, 204.6), (320, 133), (255, 181.2), (255, 193.4), (153.2, 190), (175, 461.8)], open=1, bold=3,
  region=[(138, 132, 347, 195.5), (328, 132, 347, 219.8), (326, 203.5, 476, 219.8), (138, 132, 155, 220), (138, 345, 282.5, 478)],
  blank=[(132, 273, 139, 289), (141.3, 273, 147.5, 289), (232, 175, 245, 179.8), (232, 182.8, 245, 188.5),
         (106, 135.3, 111, 145), (124, 135.3, 129, 145), (111, 455, 118, 478.2),
         (130, 125, 139.2, 132.3), (155, 144.5, 165, 160), (176, 149.5, 191.3, 158), (208.5, 120, 230, 137), (270.3, 120, 274.3, 153),
         (207.5, 147, 225, 152), (216, 156, 232, 172), (247, 156, 262, 172), (188, 187, 195.5, 196), (279, 189, 292, 199),
         (320, 202.8, 327.8, 206.5), (330, 202.8, 340.5, 206.5), (330.2, 205.8, 340.6, 208.3), (434.5, 205.8, 438.5, 217.2), (316, 216, 327.5, 224),
         (154.5, 378, 162, 384.3), (194, 386.6, 205, 397.4), (255, 386.6, 262, 397.4), (240, 355, 285, 384.2), (235, 401, 256, 420),
         (160, 401, 185, 425), (198.8, 180.4, 217.5, 182.8), (297, 146, 326, 158), (324, 134.5, 329, 142.5), (359.5, 206, 363, 217),
         (344, 206.2, 347, 217.2), [(125, 448), (149.6, 448), (151.5, 452), (125, 458)], (168.2, 430, 190, 445.6),
         [(155, 447.5), (163.8, 443.1), (163.8, 445.9), (155, 450.3)], (187.5, 470, 195, 476)],
  keep=[(228, 80, 250, 89.5), (138, 89.5, 346, 93.3), (138.5, 89.5, 141.5, 131), (343.5, 89.5, 347, 131),  # 40
        (80, 270, 88.3, 291), (86, 131, 89.5, 478), (86, 131.5, 141, 135), (86, 475, 185, 482)]),  # 109
 "12579": dict(pdf="A", page=33, crop=(85, 75, 285, 455), seeds=[(177, 250), (220, 250), (200, 400), (200, 276)], region=[(170, 89, 230, 444.6)], open=1, bold=3,
  blank=[(180, 272.5, 185, 276.6), (180, 281.8, 184.5, 286), (213.5, 272, 217.8, 276.3), (213.5, 281.8, 217.8, 285.5), (180.8, 158.5, 217.2, 167), (165, 149, 175.5, 163), (220.2, 155, 222.4, 162),
         (224.2, 140, 236, 163), (170, 404, 175.8, 407), (224.3, 398, 231, 447), (223.5, 97, 231, 112), (158, 84, 171, 91), (158, 93.2, 171, 99), (180.8, 386, 217, 402.5), (180.5, 327.5, 216.5, 332), (170, 318, 175.8, 332), (180.5, 336.5, 217, 341), (224, 336.5, 231, 341), (184.5, 440, 226, 447),
         (170, 393, 175.8, 444)],
  keep=[(95, 243, 102.5, 273), (100, 89, 104, 190), (100, 89, 190, 94)],
  draw=[("line", [(101.7, 92), (103, 442.9)]), ("line", [(99, 443), (176, 443)]), ("poly", [(101.6, 436.5), (104.2, 436.5), (103, 442.9)]),
        ("poly", [(100.5, 98.5), (103.1, 98.5), (101.7, 92)])]),
 "12225": dict(pdf="B", page=46, bold=3, crop=(55, 75, 580, 485), seeds=[(200, 268.6), (250, 434), (250, 288.9)], open=3,
  region=[(103.6, 104, 470.5, 436.5), (460, 265, 576, 281)],
  blank=[(120.8, 148.5, 124.2, 153.5), (120.8, 179, 124.2, 184.5), (292, 258, 312, 267.5), (298.5, 270.2, 302, 287.8),
         (371.5, 270.2, 375.5, 287.8), (371.5, 289.8, 375.5, 298), (427, 306, 436.6, 311), (445, 322.5, 452.6, 327),
         (447.5, 390, 451, 393.6), (205.5, 422, 209, 432.3), (125, 419, 138.8, 425.5), (125, 431, 138, 438),
         (110, 384, 145, 391.5), (110, 391.5, 118, 403), (106, 107.5, 110.5, 113),
         (85, 425, 89.5, 433.2), (97.5, 425, 102, 433.2), (113.5, 425, 118, 433.2)],
  keep=[(285, 471.6, 312, 480.5), (102, 479.8, 576, 483.5), (102.5, 438, 106.5, 483.5), (571.5, 281.5, 575.5, 483.5),  # 90
        (63, 257, 71, 277), (70.8, 103, 73.8, 437), (70.5, 103, 104, 107.5), (70.5, 434.8, 141, 437.5)]),  # 70
 "12226": dict(pdf="B", page=46, bold=3, crop=(55, 690, 590, 940), seeds=[(300, 758.2), (102, 766.8), (191, 774.8), (336.6, 774.8), (472.6, 766.8), (343, 868.6)],
  region=[(64.5, 756.5, 102, 768), (100, 756.5, 513.5, 870)], open=3,
  blank=[(104, 784, 134.5, 787.5), (136.8, 784, 145.4, 787.4), (148, 770.8, 174.6, 812), (194.5, 849, 200, 854.5), (190.5, 859, 196, 864.5),
         (83, 760.8, 86.5, 764.6), (296.5, 760.3, 300.5, 772.8), (296.5, 776, 300.5, 796), (395.5, 760.4, 400.5, 772),
         (474.5, 773.5, 488.5, 793), (501, 782.8, 509.8, 786.2), (472, 769.5, 476, 774), (495, 768.5, 499.5, 772.5), (504, 759.8, 508.5, 765),
         (498.5, 800.5, 502, 808), (461.5, 811, 469.3, 815), (471.8, 811, 492, 815), (455, 853, 459.5, 858), (432, 847, 436, 856.8),
         (432, 859.6, 436, 866.5), (395.5, 859.6, 400.5, 866.8), (296, 856.5, 323.8, 861)],
  keep=[(274, 705, 296, 714), (64, 712.5, 515, 716.3), (64, 712.5, 68, 757), (510.8, 712.5, 514.5, 757),  # 128
        (567.5, 803, 577, 823), (576.5, 757, 580.5, 869), (513, 756.5, 580, 760), (513, 865.8, 580, 869.4)]),  # 35
 "6941": dict(pdf="B", page=54, crop=(440, 330, 700, 770), seeds=[(466, 600)], region=[(463, 432, 572.5, 748)], open=3,
  blank=[(644.8, 438.2, 649, 452), (616, 438.2, 620.5, 466), (616, 420, 620.5, 433.8),
         (484, 451, 488, 480), (549.5, 451, 553.3, 480), (484, 474.5, 553.3, 479), (474.8, 539.8, 558.8, 544.3), (561.5, 539.8, 565, 544.3),
         (545, 508.5, 558.5, 513), (512, 559.5, 550, 564), (512, 618, 550, 622.5), (544.5, 559.5, 549, 622.5), (483, 589.3, 500.5, 593),
         (500.8, 624, 505, 660), (467, 654.8, 470.8, 659.3), (474.5, 654.8, 505, 659.3)],
  keep=[(668, 571, 683, 609), (683.5, 433, 688, 748), (571, 434, 689, 438), (571, 744, 689, 748),  # 100
        (476, 342, 515.5, 357), (464, 360.5, 573, 365), (464.5, 360.5, 468, 433), (569.3, 360.5, 573, 433)]),  # 30,3
 "8477": dict(pdf="B", page=44, crop=(375, 470, 545, 822), seeds=[(391, 650), (398, 650)], region=[(388, 505, 493, 812)], open=3,
  blank=[(439, 503, 442.7, 515.2), (439, 525.8, 442.7, 531), (399.2, 768, 426, 801.8), (386, 661, 426.5, 664.5), (433.3, 661, 477.8, 664.5), (486.6, 661, 493, 664.5), (480.8, 661, 482.9, 664.5), (428.6, 661, 430.2, 664.5)],
  keep=[(515.5, 648, 527.5, 671), (526.5, 515, 530.5, 812), (500, 515, 531, 519.5), (490, 806.5, 531, 811.5),  # 100
        (409, 478, 438.8, 491.5), (391, 490.3, 491, 494.5), (487, 490.3, 491, 515), (390.5, 490.3, 395, 515)],  # 30,2
  draw=[("line", [(528.3, 517.2), (528.3, 546)]), ("line", [(491, 517.2), (503.5, 517.2)])]),
 "7543": dict(pdf="B", page=50, bold=3, crop=(115, 212, 560, 345), seeds=[(300, 280.5), (148, 300)], region=[(127, 272, 508, 325)], open=3,
  blank=[(230.7, 281.8, 236.2, 287.3), (243.8, 281.8, 249.3, 287.3), (322.4, 281.8, 327.9, 287.3), (335.5, 281.8, 341.0, 287.3),
         (412.7, 281.8, 418.2, 287.3), (425.8, 281.8, 431.3, 287.3), (232.0, 309.3, 236.2, 316.1), (243.8, 309.3, 249.3, 316.1),
         (322.4, 309.3, 326.6, 316.1), (335.5, 309.3, 341.0, 316.1), (224.2, 311.9, 229.7, 317.4), (224.2, 321.1, 229.7, 326.6),
         (249.1, 311.9, 254.6, 317.4), (249.1, 321.1, 254.6, 326.6), (315.8, 313.2, 321.3, 318.7), (315.8, 321.1, 321.3, 326.6),
         (340.7, 313.2, 346.2, 318.7), (340.7, 321.1, 346.2, 326.6),
         (127, 300.5, 145.8, 307), (151, 300.5, 236.3, 307), (243.8, 300.5, 326.5, 307), (334.1, 300.5, 418.2, 307), (425.8, 300.5, 495.3, 307),
         (218, 294, 236.3, 297.5), (243.8, 294, 254, 297.5), (308, 294, 326.5, 297.5), (334.1, 294, 345, 297.5), (219, 287, 233, 294),
         (310, 287, 325, 294), (196.3, 281, 200.3, 292), (448, 290, 475, 307), (127, 297, 145.8, 303.3), (495, 287.2, 498.3, 310)],
  keep=[(298, 214, 318, 228.5), (147, 227.5, 502, 231.8), (147, 227.5, 151, 272), (494.8, 227.5, 499, 272),  # 200
        (531.5, 292, 541.5, 305), (538.5, 273, 542.5, 324), (506.5, 272.8, 543, 276.8), (441, 320, 543, 324)],  # 30
  draw=[("line", [(496.8, 231), (496.8, 272.5)]), ("line", [(149.1, 231), (149.1, 272.5)])]),
 "7846": dict(pdf="A", page=75, crop=(200, 320, 740, 900), seeds=[(421.5, 550)], region=[(420, 383, 580, 651)], open=3,
  blank=[(412, 375, 419.5, 382.5), (470, 488, 477, 496.5), (580, 488, 588, 496.5), (464, 381, 470, 387), (577, 571, 584, 578),
         (414, 649, 421, 657), (540, 357, 544.5, 497.5), (540, 514.5, 544.5, 555), (540, 500.2, 544.5, 511.8), (468.5, 414.6, 544, 418),
         (468.5, 467.5, 544, 471), (466.5, 382.5, 544, 386),
         (421.8, 433.3, 432, 436.3), (434.8, 433.3, 462, 436.3), (427, 451.2, 432, 454.2), (434.8, 451.2, 513, 454.2),
         (431.8, 385.8, 434.6, 400.8), (455, 385.8, 457.4, 401), (455, 418.5, 457.4, 468.3), (465.4, 418.5, 467.8, 468.3),
         (431.5, 630.8, 567, 634.2), (422.6, 630.8, 429, 634.2), (570.6, 630.8, 575.8, 634.2), (567.5, 573.5, 570.6, 640)],
  draw=[("poly", [(535, 511.1), (548, 511.1), (548, 514.3), (535, 514.3)])],
  keep=[(258, 492, 275, 518), (274.5, 383, 278.5, 651), (274, 382.5, 300, 386.5), (303, 382.5, 420, 386.5), (274, 647.5, 420, 651.5),  # 65
        (470, 663, 537.5, 684), (420, 683.5, 580, 687.5), (419.5, 650, 423, 688), (576.3, 572, 580, 688)]),  # 34,35
 "7847": dict(pdf="A", page=76, crop=(250, 280, 720, 960), seeds=[(399.5, 450)], region=[(397, 352, 562, 750)], open=3,
  blank=[(557, 409.5, 562, 471.3), (474.8, 410.5, 557, 416.5), (405.5, 589, 411, 640), (561.2, 471.3, 563, 475.5), (561.2, 484, 563, 488),
         (411.5, 632.5, 547, 636.3), (549.8, 632.5, 557.3, 636.3), (561.2, 632.5, 563, 636.3),
         (391, 348, 397.5, 355), (474, 348, 481, 354.8), (464, 480, 471.5, 488), (540, 488.5, 548, 495), (393, 586.5, 398, 594),
         (561.2, 746.5, 568, 753), (413.5, 371.5, 421, 379), (451, 371.5, 458.5, 379), (478, 460, 490, 470)],
  keep=[(638, 525, 657, 562), (655.5, 355, 659.5, 749), (474, 353.5, 660, 358), (561, 744.5, 660, 748.5),  # 93
        (450, 745, 521, 764), (398, 763.5, 560, 767.5), (397, 586.6, 401, 769), (557, 749, 561, 769)]),  # 34,25
 "11543": dict(pdf="B", page=38, crop=(80, 300, 400, 800), seeds=[(199, 600), (300, 522)], region=[(165, 360, 378, 784)], open=5, bridge=7,
  blank=[(184.2, 360, 240, 434.5), (174.9, 430.5, 179.8, 434.5), (165, 393, 169.2, 471.5), (163, 424, 171.5, 441),
         (174.9, 423.5, 180.4, 430.5), (174.9, 434.5, 180.4, 441), (174.9, 394, 180.4, 402), (170, 491, 178.5, 494.5),
         (185, 491, 200, 494.5), (190, 478, 199, 491), (209.5, 516, 214, 521.8), (209.5, 525.2, 214, 530.5), (209.5, 534, 214, 538),
         (305, 512, 309, 521.8), (305, 525.2, 309, 530.5), (305, 534, 309, 560),
         (165, 537, 174, 548), (165, 545, 182.8, 632), (163, 632, 182.8, 665), (165, 665, 182.8, 758), (169, 758, 173.5, 782),
         (188.3, 583, 196.8, 588), (200.4, 583, 216, 588), (188.3, 548, 196.7, 636), (188.3, 660, 196.7, 757),
         (200.6, 548, 206, 757)], keep=[(81, 555, 95, 591), (96, 361, 99.5, 783), (96, 361, 168, 364.5), (96, 780, 175, 783.5),  # 134
                  (257, 308, 292, 323), (166, 322.5, 377, 326), (165.5, 322, 169, 362), (374.5, 322, 378, 523)]),  # 60
 "7971": dict(pdf="B", page=24, crop=(360, 225, 720, 860), seeds=[(448.3, 400)], region=[(447, 269, 575, 820), (447, 470, 687, 489.5)], open=3, threshold=185, bold=3,
  blank=[(462, 268.5, 575, 272.5), (449.9, 327, 459, 330.5), (462, 327, 500, 330.5), (449.9, 348, 459, 351.8), (462, 348, 490, 351.8),
         (449.9, 410, 459, 450), (462, 410, 470, 450), (462, 428, 505, 433), (468.5, 461, 474.5, 468.5), (463.5, 520.5, 470, 528.5),
         (466, 778, 473, 786), (447, 534, 473.8, 548), (476.8, 526, 485.2, 540),
         (488.3, 490, 575, 545), (488.3, 703, 575, 707.5), (447, 680, 473.6, 730), (476.8, 680, 485.2, 730), (488.3, 680, 505, 730),
         (447, 732, 473.6, 736), (476.8, 732, 485.2, 736), (488.3, 732, 575, 736), (488.3, 767.5, 575, 772), (568, 765, 575, 799.5),
         (525.5, 778, 529, 802.2), (525.5, 805.4, 529, 810.3), (525.5, 813.6, 529, 830), (476.5, 792, 482, 799), (560, 555, 576, 561), (446.5, 490, 450.2, 548), (447, 795, 470, 799.5), (447, 780, 469, 795)],
  keep=[(382, 510, 392, 554), (392.5, 269, 395.5, 819.5), (392, 268.5, 448, 272.3), (392, 816.5, 472, 820),  # 187,5
        (545, 238, 576, 253), (449, 252, 686.5, 255.8), (448.5, 247, 451.5, 270), (684, 252, 687.5, 486)]),  # 73,8
 "6915": dict(pdf="A", page=67, crop=(360, 360, 750, 770), seeds=[(404.5, 600)], region=[(403.5, 461.5, 653, 714.8)], open=3, bold=3,
  blank=[(409.5, 462, 412.2, 524), (423.5, 555, 440, 559.5), (412, 555, 421.3, 559.5), (619, 555, 633.3, 559.5), (636.6, 555, 646.2, 559.5),
         (652.3, 555, 672, 559.5), (526, 462, 529.8, 640), (526, 655, 529.8, 692.6), (526, 696, 529.8, 710.5), (526, 714, 529.8, 716),
         (514, 680, 542, 692.6), (514, 695.8, 542, 711), (514, 714, 542, 716), (536, 664, 570, 692.6), (441, 640, 445.5, 692.6),
         (610.8, 640, 614.5, 692.6), (445, 641, 470, 645), (580, 641, 612, 645), (636.2, 466, 641, 471), (652.3, 524, 700, 528.5),
         (652.3, 586, 700, 591), (614, 689.5, 620, 692.6), (421.5, 696, 424, 711), (631.7, 696, 634.2, 711)],
  keep=[(512, 368, 546, 381), (405, 382.5, 653, 386.5), (404, 380, 407.5, 472), (650.5, 382, 654, 465),  # 35,5
        (724, 575, 734, 596), (733.5, 462, 737, 715.5), (651, 462, 738, 466), (651, 711.5, 737, 715.5)],  # 40
  draw=[("line", [(406, 384.4), (460, 384.4)])]),
}

# a rajzok szövegmezőjéből (kézzel ellenőrizve) és a megtartott fő méretekből
AL = "AlMgSi0,5 (≈ EN AW-6060)"
SPECS = {
    "12386": {"Ötvözet": "EN AW-6005", "Tömeg": "3,205 kg/fm", "Kerület": "484 mm", "Keresztmetszet": "1 188 mm²", "Profil típusa": "nyitott",
              "Szélesség": "130 mm", "Magasság": "60 mm", "Falvastagság": "4,5 mm"},
    "12387": {"Ötvözet": "EN AW-6005", "Tömeg": "1,733 kg/fm", "Kerület": "393 mm", "Keresztmetszet": "642 mm²", "Profil típusa": "nyitott",
              "Magasság": "70 mm", "Szélesség": "50 mm (felső öv), 46 mm (alsó öv)"},
    "10902": {"Ötvözet": "EN AW-6060", "Tömeg": "2,428 kg/fm", "Kerület": "511 mm", "Keresztmetszet": "899 mm²", "Profil típusa": "nyitott",
              "Szélesség": "85 mm", "Magasság": "90 mm", "Falvastagság": "3 mm"},
    "8652": {"Ötvözet": AL + " F25", "Tömeg": "2,26 kg/fm", "Kerület": "522 mm", "Keresztmetszet": "834 mm²", "Profil típusa": "nyitott",
             "Magasság": "126,5 mm", "Szélesség": "40 mm (felső rész), 28 mm (alsó perem)"},
    "12388": {"Ötvözet": "EN AW-6005", "Tömeg": "1,638 kg/fm", "Kerület": "458 mm", "Keresztmetszet": "607 mm²", "Profil típusa": "nyitott",
              "Magasság": "109 mm", "Szélesség": "40 mm (felső rész)"},
    "12579": {"Ötvözet": "EN AW-6060", "Tömeg": "1,903 kg/fm", "Kerület": "618 mm", "Keresztmetszet": "704 mm²", "Profil típusa": "zárt (üreges)",
              "Magasság": "222 mm (teljes), 200 mm beépítési magasság"},
    "12225": {"Ötvözet": "EN AW-6005", "Tömeg": "2,585 kg/fm", "Kerület": "421 mm", "Keresztmetszet": "958 mm²", "Profil típusa": "zárt (üreges)",
              "Szélesség": "90 mm", "Magasság": "70 mm"},
    "12226": {"Ötvözet": "EN AW-6005", "Tömeg": "3,181 kg/fm", "Kerület": "538 mm", "Keresztmetszet": "1 171 mm²", "Profil típusa": "zárt (üreges)",
              "Szélesség": "128 mm", "Magasság": "35 mm"},
    "6941": {"Ötvözet": "EN AW-6060", "Tömeg": "1,483 kg/fm", "Kerület": "305 mm", "Keresztmetszet": "549 mm²", "Profil típusa": "zárt (üreges)",
             "Magasság": "100 mm", "Szélesség": "30,3 mm"},
    "8477": {"Ötvözet": AL, "Tömeg": "1,125 kg/fm", "Kerület": "301 mm", "Keresztmetszet": "415 mm²", "Profil típusa": "zárt (üreges)",
             "Magasság": "100 mm", "Szélesség": "30,2 mm"},
    "7543": {"Ötvözet": "EN AW-6005", "Tömeg": "3,032 kg/fm", "Kerület": "732 mm", "Keresztmetszet": "1 123 mm²", "Profil típusa": "nyitott",
             "Szélesség": "200 mm", "Magasság": "30 mm"},
    "7846": {"Ötvözet": AL, "Tömeg": "0,935 kg/fm", "Kerület": "254 mm", "Keresztmetszet": "345 mm²", "Profil típusa": "nyitott",
             "Magasság": "65 mm", "Szélesség": "34,35 mm"},
    "7847": {"Ötvözet": AL, "Tömeg": "1,014 kg/fm", "Kerület": "346 mm", "Keresztmetszet": "374 mm²", "Profil típusa": "nyitott",
             "Magasság": "93 mm", "Szélesség": "34,25 mm"},
    "11543": {"Ötvözet": "EN AW-6060 T6", "Tömeg": "1,743 kg/fm", "Kerület": "389 mm", "Keresztmetszet": "646 mm²", "Profil típusa": "nyitott",
              "Magasság": "134 mm", "Szélesség": "60 mm"},
    "7971": {"Ötvözet": AL + " F22", "Tömeg": "2,981 kg/fm", "Kerület": "568 mm", "Keresztmetszet": "1 100 mm²", "Profil típusa": "nyitott",
             "Magasság": "187,5 mm", "Szélesség": "73,8 mm"},
    "6915": {"Ötvözet": AL + " F25", "Tömeg": "0,743 kg/fm", "Keresztmetszet": "274 mm²", "Profil típusa": "nyitott",
             "Szélesség": "35,5 mm", "Magasság": "40 mm", "Falvastagság": "3 mm"},
}
# más beszállítónál (Alu-SV) felvett, de Constellium-profilszámú termékek – kifejezett slug-lista
EXTRA_SLUGS = {"226915-n-30-mm-u-szego-profil": "6915"}  # 30 mm U szegő profil (rajz: Transport2024, 67. oldal)
# kód nélküli Quadris-termékek: a slug számrésze a profilszám utolsó 4 számjegye (mint pl. 202386 = 12386, 237846 = 7846),
# és a rajz méretei is egyeznek a megnevezéssel
NO_CODE = {"231543-dobozos-keret-elox-134-80": "11543",  # 134 mm magas, 80 mm a peremtől lefelé
           "237971-hutos-keretprofil-nyitott-elox": "7971"}  # OTEVŘENÝ (nyitott) keretprofil


def _poly(b):
    return [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])] if isinstance(b[0], (int, float)) else b


def area(boxes, size, px, default=False):
    """Téglalapok / sokszögek uniójának maszkja (None -> az egész kép, ha default igaz)."""
    if boxes is None:
        return np.full((size[1], size[0]), default)
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    for b in boxes:
        d.polygon([px(*p) for p in _poly(b)], fill=255)
    return np.asarray(im) > 0


def render(code, trim=True):
    cfg = DRAWINGS[code]
    doc = pymupdf.open(SRC / PDFS[cfg["pdf"]][0])
    page = doc[cfg["page"] - 1]
    x0, y0, x1, y1 = cfg["crop"]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=pymupdf.Rect(x0, y0, x1, y1), colorspace=pymupdf.csGRAY, alpha=False)
    gray = Image.frombytes("L", (pix.width, pix.height), pix.samples)

    def px(x, y):
        return ((x - x0) * ZOOM, (y - y0) * ZOOM)

    draw = ImageDraw.Draw(gray)
    for b in cfg.get("blank", []):
        draw.polygon([px(*p) for p in _poly(b)], fill=255)
    gray = gray.filter(ImageFilter.GaussianBlur(0.8))
    ink = np.asarray(gray) < cfg.get("threshold", 150)
    # a körvonal vastag, a méret- és mutatóvonalak vékonyak: nyitással (erózió + dilatáció) csak a vastag vonalak maradnak
    inkim = Image.fromarray((ink * 255).astype(np.uint8))
    k = cfg.get("open", 5)
    thick = inkim.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k)) if k > 1 else inkim
    # a körvonal kiválasztása: kitöltés a kezdőpontokból a vastag vonalak képén
    dil = thick.filter(ImageFilter.MaxFilter(cfg.get("bridge", 3)))  # a vastag vonalak kis hézagainak áthidalása
    ys, xs = np.nonzero(np.asarray(dil))
    for sx, sy in cfg["seeds"]:
        cx, cy = px(sx, sy)
        i = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
        if (xs[i] - cx) ** 2 + (ys[i] - cy) ** 2 > (6 * ZOOM) ** 2:
            raise ValueError(f"{code}: a kezdőpont ({sx}, {sy}) nincs vonal közelében")
        if dil.getpixel((int(xs[i]), int(ys[i]))) == 255:
            ImageDraw.floodfill(dil, (int(xs[i]), int(ys[i])), 128)
    comp = Image.fromarray(((np.asarray(dil) == 128) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    mask = (np.asarray(comp) > 0) & ink & area(cfg.get("region"), gray.size, px, True)
    mask |= area(cfg.get("keep"), gray.size, px) & ink
    img = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8))
    # a szkennelésen elhalványult méretvonalak pótlása (vonal / nyílhegy)
    d = ImageDraw.Draw(img)
    for kind, pts in cfg.get("draw", []):
        if kind == "line":
            d.line([px(*p) for p in pts], fill=0, width=3)
        else:
            d.polygon([px(*p) for p in pts], fill=0)
        mask |= np.asarray(img) == 0
    if cfg.get("bold", 1) > 1:  # vékony vonalú rajzoknál vastagítás, hogy kicsinyítve is jól látsszon
        img = img.filter(ImageFilter.MinFilter(cfg["bold"]))
    if not trim:
        return img
    ys, xs = np.nonzero(mask)
    m = 30
    return img.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, img.width), min(ys.max() + m, img.height)))


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--debug":
        render(sys.argv[2]).save(sys.argv[3])
        return
    existing = load_enrichment()
    enrichment, skipped = {}, []
    products = load_products("Constellium Decin") + [p for p in load_products() if p["slug"] in EXTRA_SLUGS]
    for p in products:
        code = EXTRA_SLUGS.get(p["slug"]) or (p["supplierCode"] or "").strip() or NO_CODE.get(p["slug"], "")
        cfg = DRAWINGS.get(code)
        other = existing.get(p["slug"], {})
        if not cfg:
            continue
        if other.get("images") and other.get("source") != SOURCE:
            skipped.append((p, other.get("source")))
            continue
        title = PDFS[cfg["pdf"]][1]
        specs = {"Profilszám (gyártói)": code, **SPECS[code], "Felület": "eloxált" if "elox" in p["name"].lower() else "natúr"}
        clear_images(p["slug"])
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": URL, "sourceTitle": f"Constellium Děčín profilrajz {code} ({title}, {cfg['page']}. oldal)",
                                 "matchedCode": code, "specs": specs, "images": [save_image(render(code), p["slug"], 1)]}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")
    for p, src in skipped:
        print(f"  kihagyva (már van képe: {src}): {p['slug']}")


if __name__ == "__main__":
    main()
