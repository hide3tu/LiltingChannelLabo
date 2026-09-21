"""Measure the shift and changed-pixel ratio between a source image and an edited output.

Same method as the July 2026 Qwen-Image-Edit 2511 article: phase correlation on edge maps (global + 3x3 blocks)
and the ratio of pixels whose mean abs RGB difference exceeds 20/255, inside / outside the face boxes.

usage: python measure_edit.py source.png output1.png [output2.png ...]
"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
FACE_BOXES = [(140, 90, 330, 260), (490, 120, 680, 290)]  # face boxes for the 832x1216 two-girl source image; edit for your image

def edge_map(img):
    g = np.asarray(img.convert("L"), dtype=np.float64)
    gy, gx = np.gradient(g)
    e = np.hypot(gx, gy)
    e -= e.mean()
    return e

def phase_shift(a, b):
    wy = np.hanning(a.shape[0])[:, None]; wx = np.hanning(a.shape[1])[None, :]
    fa = np.fft.fft2(a * wy * wx); fb = np.fft.fft2(b * wy * wx)
    r = fa * np.conj(fb); r /= np.abs(r) + 1e-9
    c = np.fft.ifft2(r).real
    py, px = np.unravel_index(np.argmax(c), c.shape)
    def sub(idx, n, cm1, c0, cp1):
        den = cm1 - 2 * c0 + cp1
        d = 0.0 if abs(den) < 1e-12 else 0.5 * (cm1 - cp1) / den
        v = idx + d
        return v - n if v > n / 2 else v
    dy = sub(py, a.shape[0], c[(py - 1) % a.shape[0], px], c[py, px], c[(py + 1) % a.shape[0], px])
    dx = sub(px, a.shape[1], c[py, (px - 1) % a.shape[1]], c[py, px], c[py, (px + 1) % a.shape[1]])
    return -dy, -dx

def measure(src, out, tag):
    res = {"tag": tag}
    a, b = edge_map(src), edge_map(out)
    dy, dx = phase_shift(a, b)
    res["global"] = [round(dx, 2), round(dy, 2)]
    H, W = a.shape; blocks = []
    for by in range(3):
        row = []
        for bx in range(3):
            sa = a[by*H//3:(by+1)*H//3, bx*W//3:(bx+1)*W//3]; sb = b[by*H//3:(by+1)*H//3, bx*W//3:(bx+1)*W//3]
            bdy, bdx = phase_shift(sa, sb); row.append([round(bdx, 2), round(bdy, 2)])
        blocks.append(row)
    res["blocks_dx_dy"] = blocks
    d = np.abs(np.asarray(src.convert("RGB"), dtype=np.float64) - np.asarray(out.convert("RGB"), dtype=np.float64)).mean(axis=2)
    face = np.zeros(d.shape, dtype=bool)
    for x0, y0, x1, y1 in FACE_BOXES: face[y0:y1, x0:x1] = True
    ch = d > 20
    res.update(mean_diff=round(float(d.mean()), 2), changed_all=round(float(ch.mean()*100), 2), changed_face=round(float(ch[face].mean()*100), 2),
               changed_outside=round(float(ch[~face].mean()*100), 2), changed_left=round(float(ch[:, :W//2].mean()*100), 2), changed_right=round(float(ch[:, W//2:].mean()*100), 2))
    # diff heatmap and edge overlay (red = source edges, cyan = output edges)
    (ROOT/"edit").mkdir(exist_ok=True)
    heat = np.zeros((H, W, 3), dtype=np.uint8); g = np.asarray(src.convert("L"), dtype=np.float64) * 0.35
    heat[:, :, 0] = np.clip(g + d * 4, 0, 255); heat[:, :, 1] = np.clip(g, 0, 255); heat[:, :, 2] = np.clip(g, 0, 255)
    Image.fromarray(heat).save(ROOT/"edit"/f"diff_{tag}.png")
    an = np.zeros((H, W, 3), dtype=np.uint8)
    ea = np.clip(np.abs(a) / (np.abs(a).max() + 1e-9) * 4 * 255, 0, 255); eb = np.clip(np.abs(b) / (np.abs(b).max() + 1e-9) * 4 * 255, 0, 255)
    an[:, :, 0] = ea; an[:, :, 1] = eb; an[:, :, 2] = eb
    Image.fromarray(an).save(ROOT/"edit"/f"overlay_{tag}.png")
    return res

if __name__ == "__main__":
    src = Image.open(sys.argv[1]).convert("RGB")
    for path in sys.argv[2:]:
        out = Image.open(path).convert("RGB")
        if out.size != src.size:
            print(path, "size differs", out.size)
            continue
        print(json.dumps(measure(src, out, Path(path).stem), ensure_ascii=False))
