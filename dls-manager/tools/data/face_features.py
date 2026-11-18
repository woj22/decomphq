#!/usr/bin/env python3
"""Measure each player's look in his photo: skin tone, hair colour, hair length / volume, beard.

Uses Google's MediaPipe models (downloaded once, paths given on the command line):
  * face_landmarker.task: 478 face points (cheeks, chin, upper lip, forehead, jaw);
  * selfie_multiclass_256x256.tflite: per-pixel classes (0 background, 1 hair, 2 body skin,
    3 face skin, 4 clothes, 5 other).
For every photo (assets/headshots/_src/<player id>[_wd].jpg, the full-size source):
  skin    median Lab of face-skin pixels in the cheek band, plus ITA (individual typology
          angle, atan((L-50)/b)), after a grey-world white balance of the face crop;
  hair    hair pixels' median Lab, how far the hair reaches (above the forehead, beside the
          face, below the chin) relative to the face size;
  beard   how much of the chin / jaw / upper-lip area is hair (by class) or clearly darker
          than the cheeks.
Writes JSON {player id: features}. Thresholds turning these into DLS codes live in
set_heads.py (calibrated on players whose DLS look is known).

Usage: python3 -I face_features.py --data menu/data.json --photos assets/headshots/_src
           --landmarker face_landmarker.task --segmenter selfie_multiclass_256x256.tflite --out features.json
"""
import argparse
import json
import math
import os

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

CHEEK_L = [50, 101, 118, 117, 123, 187, 205, 36]
CHEEK_R = [280, 330, 347, 346, 352, 411, 425, 266]
CHIN = [152, 148, 176, 149, 150, 136, 172, 58, 132, 377, 400, 378, 379, 365, 397, 288, 361, 18, 200, 199, 175, 171, 396]
LIP_UP = [0, 37, 39, 40, 185, 267, 269, 270, 409, 164, 165, 391, 92, 322]


def poly_mask(shape, pts):
    m = np.zeros(shape[:2], np.uint8)
    hull = cv2.convexHull(np.array(pts, np.int32))
    cv2.fillConvexPoly(m, hull, 1)
    return m.astype(bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--photos", required=True)
    ap.add_argument("--landmarker", required=True)
    ap.add_argument("--segmenter", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=a.landmarker), num_faces=3))
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=a.segmenter), output_category_mask=True))
    data = json.load(open(a.data, encoding="utf-8"))
    out = {}
    for p in data["players"]:
        src = None
        for f in (f"{p['id']}_wd.jpg", f"{p['id']}.jpg", f"{p['id']}.png", f"{p['id']}.jpeg"):
            if os.path.exists(os.path.join(a.photos, f)):
                src = os.path.join(a.photos, f)
                break
        if not src:
            continue
        img = cv2.imread(src)
        if img is None:
            continue
        H, W = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        if not res.face_landmarks:
            continue
        # the biggest face is the player
        faces = [[(q.x * W, q.y * H) for q in f] for f in res.face_landmarks]
        pts = max(faces, key=lambda f: (max(x for x, _ in f) - min(x for x, _ in f)) * (max(y for _, y in f) - min(y for _, y in f)))
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        fw, fh = max(xs) - min(xs), max(ys) - min(ys)
        if fw < 40:
            continue
        # crop around the head: 1.2 face heights above, 0.9 below, 0.9 widths each side
        x0, x1 = int(max(0, min(xs) - 0.9 * fw)), int(min(W, max(xs) + 0.9 * fw))
        y0, y1 = int(max(0, min(ys) - 1.2 * fh)), int(min(H, max(ys) + 0.9 * fh))
        crop = img[y0:y1, x0:x1].copy()
        cp = [(x - x0, y - y0) for x, y in pts]
        ch, cw = crop.shape[:2]
        # grey-world white balance on the crop (photos come in all lights)
        f32 = crop.astype(np.float32)
        means = f32.reshape(-1, 3).mean(axis=0)
        f32 *= means.mean() / np.maximum(means, 1)
        bal = np.clip(f32, 0, 255).astype(np.uint8)
        lab = cv2.cvtColor(bal, cv2.COLOR_BGR2LAB).astype(np.float32)
        lab[..., 0] *= 100 / 255.0
        lab[..., 1] -= 128
        lab[..., 2] -= 128
        sres = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))))
        cls = sres.category_mask.numpy_view().copy()
        if cls.shape != (ch, cw):
            cls = cv2.resize(cls, (cw, ch), interpolation=cv2.INTER_NEAREST)
        cheeks = (poly_mask(crop.shape, [cp[i] for i in CHEEK_L]) | poly_mask(crop.shape, [cp[i] for i in CHEEK_R])) & (cls == 3)
        if cheeks.sum() < 20:
            cheeks = poly_mask(crop.shape, [cp[i] for i in CHEEK_L]) | poly_mask(crop.shape, [cp[i] for i in CHEEK_R])
        sk = np.median(lab[cheeks], axis=0)
        # alternatives for calibration: no white balance, and grey-world over the whole photo
        def lab_of(bgr):
            q = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
            return q[..., 0] * 100 / 255.0, q[..., 2] - 128
        L0, B0 = lab_of(crop)
        g = img.astype(np.float32)
        gm = g.reshape(-1, 3).mean(axis=0)
        gcrop = np.clip(crop.astype(np.float32) * (gm.mean() / np.maximum(gm, 1)), 0, 255).astype(np.uint8)
        LG, BG = lab_of(gcrop)
        ita0 = math.degrees(math.atan2(float(np.median(L0[cheeks])) - 50, max(float(np.median(B0[cheeks])), 0.5)))
        itaG = math.degrees(math.atan2(float(np.median(LG[cheeks])) - 50, max(float(np.median(BG[cheeks])), 0.5)))
        ita = math.degrees(math.atan2(sk[0] - 50, max(sk[2], 0.5)))
        hair = cls == 1
        fore_y = cp[10][1]
        chin_y = cp[152][1]
        face_h = max(1.0, chin_y - fore_y)
        left_x = min(x for x, _ in cp)
        right_x = max(x for x, _ in cp)
        face_w = max(1.0, right_x - left_x)
        feat = {"L": round(float(sk[0]), 1), "a": round(float(sk[1]), 1), "b": round(float(sk[2]), 1), "ita": round(ita, 1), "ita0": round(ita0, 1), "itaG": round(itaG, 1), "L0": round(float(np.median(L0[cheeks])), 1),
                "hairArea": round(float(hair.sum()) / (face_w * face_h), 3)}
        if hair.sum() > 30:
            hl = np.median(lab[hair], axis=0)
            hy, hx = np.nonzero(hair)
            feat.update({"hairL": round(float(hl[0]), 1), "hairA": round(float(hl[1]), 1), "hairB": round(float(hl[2]), 1),
                         "hairTop": round(float(fore_y - hy.min()) / face_h, 2),          # height above the forehead
                         "hairLow": round(float(hy.max() - chin_y) / face_h, 2),          # how far below the chin
                         "hairSide": round(float((((hx < left_x - 0.08 * face_w) | (hx > right_x + 0.08 * face_w)) & (hy > fore_y + 0.35 * face_h)).sum()) / (face_w * face_h), 3)})
        chin = poly_mask(crop.shape, [cp[i] for i in CHIN])
        lipm = poly_mask(crop.shape, [cp[i] for i in LIP_UP])
        def beardiness(m):
            if m.sum() < 10:
                return 0.0
            darker = lab[m][:, 0] < sk[0] - 12
            return float(((cls[m] == 1) | darker).mean())
        feat["beardChin"] = round(beardiness(chin), 2)
        feat["beardLip"] = round(beardiness(lipm), 2)
        # sharper beard measures: hair-class share, and how much darker than the cheeks
        for nm, m in (("Chin", chin), ("Lip", lipm)):
            if m.sum() >= 10:
                feat["hair" + nm] = round(float((cls[m] == 1).mean()), 2)
                feat["dark" + nm] = round(float(sk[0] - np.median(lab[m][:, 0])), 1)
        out[p["id"]] = feat
    json.dump(out, open(a.out, "w"), indent=0)
    print(len(out), "players measured")


if __name__ == "__main__":
    main()
