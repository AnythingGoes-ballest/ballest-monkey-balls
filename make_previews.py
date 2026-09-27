"""Draws a model file (the plugin manager's cosmetics model format) without the game: the parts are ray marched as
signed distances, posed at one moment of the tempo. Makes the tile pictures, and previews for checking a model.
  python make_previews.py tile models/aiai.txt aiai_preview.png        a tile: the monkey in a glassy ball
  python make_previews.py models/aiai.txt out.png [yaw] [beat] [m/s]  a check: seen from yaw degrees, with the ball's
                                                                       outline (glass isn't drawn)
Needs Python with NumPy and Pillow."""
import math
import sys

import numpy as np
from PIL import Image


def rot_matrix(pitch, yaw, roll):
    p, y, r = (math.radians(a) for a in (pitch, yaw, roll))
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    x_axis = [cp * cy, cp * sy, sp]
    y_axis = [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp]
    z_axis = [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]
    return np.array([x_axis, y_axis, z_axis]).T      # columns: local axes in parent space


def nums(s):
    return [float(v) for v in s.split(",")]


def parse(text):
    mats, groups, tempo = {}, [], dict(rate=1, run=0, max=1e9, calm=1, full=1)
    groups.append(dict(name="main", parent=-1, pivot=[0, 0, 0], swing=-1, angle=0, phase=0, bob=0, travel=False, parts=[]))
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "# " in s:
            s = s[: s.index("# ")]
        w = s.split()
        kv = {x.split("=")[0]: x.split("=", 1)[1] for x in w if "=" in x}
        if w[0] == "material":
            if w[2] == "glass":
                h = w[3][1:] if len(w) > 3 and w[3].startswith("#") else "ffffff"
                mats[w[1]] = ("glass", ([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], float(kv.get("opacity", 0.2))))
            else:
                h = w[3][1:]
                mats[w[1]] = (w[2], [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])
        elif w[0] == "tempo":
            for k in tempo:
                if k in kv:
                    tempo[k] = float(kv[k])
        elif w[0] == "group":
            if len(groups) == 1 and not groups[0]["parts"]:
                groups.clear()
            g = dict(name=w[1], parent=-1, pivot=[0, 0, 0], swing=-1, angle=float(kv.get("angle", 0)),
                     phase=float(kv.get("phase", 0)), bob=float(kv.get("bob", 0)), travel="travel" in w, parts=[])
            if "on" in kv:
                g["parent"] = [x["name"] for x in groups].index(kv["on"])
            if "pivot" in kv:
                g["pivot"] = nums(kv["pivot"])
            if "swing" in kv:
                g["swing"] = "xyz".index(kv["swing"])
            groups.append(g)
        else:
            part = dict(shape=w[0], mat=w[1], at=nums(kv.get("at", "0,0,0")), rot=nums(kv.get("rot", "0,0,0")),
                        scale=nums(kv.get("scale", "1,1,1")))
            for k in ("r", "h", "top", "thick", "len", "hole", "wall", "degrees", "inner", "turns"):
                if k in kv:
                    part[k] = float(kv[k])
            if "size" in kv:
                part["size"] = nums(kv["size"])
            groups[-1]["parts"].append(part)
    return mats, groups, tempo


def group_world(groups, tempo, beat, speed):
    """World matrix (3x3, translation) of each group at this beat."""
    reach = tempo["calm"] + (1 - tempo["calm"]) * min(1, speed / tempo["full"])
    turn = 2 * math.pi * beat
    out = []
    for g in groups:
        ang = [0, 0, 0]
        ph = math.radians(g["phase"])
        if g["swing"] >= 0:
            ang[g["swing"]] += g["angle"] * reach * math.sin(turn + ph)
        R = rot_matrix(ang[1], ang[2], ang[0])
        if g["parent"] >= 0:
            base = groups[g["parent"]]["pivot"]
            at = np.array(g["pivot"]) - np.array(base)
        else:
            at = np.array(g["pivot"], float)
        at = at + np.array([0, 0, g["bob"] * reach * (0.5 - 0.5 * math.cos(2 * turn + ph))])
        if g["parent"] >= 0:
            PR, PT = out[g["parent"]]
            out.append((PR @ R, PT + PR @ at))
        else:
            out.append((R, at))
    return out


def sdf(shape, q, part):
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    if shape == "sphere":
        return np.linalg.norm(q, axis=-1) - part["r"]
    if shape == "box":
        d = np.abs(q) - np.array(part["size"]) / 2
        return np.linalg.norm(np.maximum(d, 0), axis=-1) + np.minimum(d.max(-1), 0)
    if shape in ("cylinder", "cone"):
        h = part["h"]
        r0 = part["r"]
        r1 = part.get("top", r0) if shape == "cone" else r0
        t = np.clip(z / h, 0, 1)
        rad = r0 + (r1 - r0) * t
        dr = np.hypot(x, y) - rad
        dz = np.maximum(-z, z - h)
        return np.maximum(dr * 0.9, dz)
    if shape == "capsule":
        r, ln = part["r"], part.get("len", 0)
        zc = np.clip(z, r, r + ln)
        return np.sqrt(x * x + y * y + (z - zc) ** 2) - r
    if shape == "disc":
        rr = np.hypot(x, y)
        d = np.maximum(rr - part["r"], part.get("hole", 0) - rr)
        return np.maximum(d, np.abs(z) - 0.3)
    if shape == "ring":
        a = np.degrees(np.arctan2(y, x)) % 360
        deg = part.get("degrees", 360)
        d = np.sqrt((np.hypot(x, y) - part["r"]) ** 2 + z * z) - part["thick"] / 2
        if deg < 360:
            d = np.where(a <= deg, d, 1e3)
        return d
    if shape == "bowl":
        r, wall = part["r"], part["wall"]
        return np.maximum(np.abs(np.linalg.norm(q, axis=-1) - (r - wall / 2)) - wall / 2, z)
    if shape == "spiral":
        n = max(8, int(part["turns"] * 28))
        t = np.linspace(0, 1, n + 1)
        a = 2 * np.pi * part["turns"] * t
        rad = part["r"] + (part["inner"] - part["r"]) * t
        pts = np.stack([rad * np.cos(a), rad * np.sin(a), np.zeros_like(a)], -1)
        best = np.full(q.shape[:-1], 1e9)
        for i in range(n):
            p0, p1 = pts[i], pts[i + 1]
            d = p1 - p0
            h = np.clip(((q - p0) @ d) / (d @ d), 0, 1)
            best = np.minimum(best, np.linalg.norm(q - p0 - h[..., None] * d, axis=-1))
        return best - part["thick"] / 2
    if shape == "cup":
        rr = np.hypot(x, y)
        h = part["h"]
        top = part.get("top", part["r"])
        rad = part["r"] + (top - part["r"]) * np.clip(z / h, 0, 1)
        outer = np.maximum(rr - rad, np.maximum(-z, z - h))
        inner = np.maximum(rr - (rad - part["wall"]), np.maximum(part["wall"] - z, z - h - 1))
        return np.maximum(outer, -inner)
    raise ValueError(shape)


def render(path, out, yaw=20.0, beat=0.25, speed=0.0, size=420, pitch=12.0, tile=False):
    mats, groups, tempo = parse(open(path, encoding="utf-8").read())
    worlds = group_world(groups, tempo, beat, speed)
    prims = []
    for g, (GR, GT) in zip(groups, worlds):
        for p in g["parts"]:
            kind, col = mats[p["mat"]]
            if kind == "glass" or (tile and g["name"] == "shell"):
                continue
            R = GR @ rot_matrix(*p["rot"])
            T = GT + GR @ (np.array(p["at"]) - np.array(g["pivot"]))
            prims.append((p, R, T, np.array(p["scale"]), kind, col))
    # camera looks toward -dir from dir*distance
    cy, cp = math.radians(yaw), math.radians(pitch)
    fwd = -np.array([math.cos(cp) * math.cos(cy), math.cos(cp) * math.sin(cy), math.sin(cp)])
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    half = 51.0 if tile else 58.0
    u = np.linspace(-half, half, size)
    U, V = np.meshgrid(u, -u)
    origin = (-fwd * 200)[None, None, :] + U[..., None] * right + V[..., None] * up
    t = np.zeros(U.shape)
    hit = np.zeros(U.shape, bool)
    idx = np.full(U.shape, -1)

    def scene(pts):
        best = np.full(pts.shape[:-1], 1e9)
        which = np.full(pts.shape[:-1], -1)
        for i, (p, R, T, S, kind, col) in enumerate(prims):
            q = (pts - T) @ R / S
            d = sdf(p["shape"], q, p) * S.min()
            m = d < best
            best = np.where(m, d, best)
            which = np.where(m, i, which)
        return best, which

    for _ in range(90):
        pts = origin + fwd * t[..., None]
        d, w = scene(pts)
        newly = (d < 0.05) & ~hit
        idx = np.where(newly, w, idx)
        hit |= newly
        t = np.where(hit, t, t + np.maximum(d, 0.05))
        if (t > 400).all():
            break
    pts = origin + fwd * t[..., None]
    e = 0.05
    n = np.stack([scene(pts + np.array(v))[0] - scene(pts - np.array(v))[0] for v in ([e, 0, 0], [0, e, 0], [0, 0, e])], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    light = np.array([0.5, 0.3, 0.8]); light /= np.linalg.norm(light)
    diff = np.clip((n * light).sum(-1), 0, 1)
    img = np.zeros(U.shape + (3,)) + np.array([0.11, 0.12, 0.15])
    for i, (p, R, T, S, kind, col) in enumerate(prims):
        m = hit & (idx == i)
        c = np.array(col)
        shade = 1.0 if kind == "glow" else (0.35 + 0.65 * diff[m])[..., None]
        img[m] = c * shade
    rr = np.hypot(U, V)
    if not tile:
        img[np.abs(rr - 50) < 0.35] = [0.8, 0.85, 0.9]      # the ball's outline (radius 50)
        Image.fromarray((np.clip(img, 0, 1) ** (1 / 1.4) * 255).astype(np.uint8)).save(out)
        return
    # a tile picture: the monkey in a glassy ball on nothing, the lower half of the ball tinted by the shell's bowl
    rgb = np.clip(img, 0, 1) ** (1 / 1.4)
    inside = rr < 50
    tint = None
    for g in groups:
        if g["name"] == "shell":
            for part in g["parts"]:
                kind, value = mats[part["mat"]]
                if part["shape"] == "bowl" and kind == "glass":
                    tint = value
    if tint is not None:
        # where each pixel's ray meets the ball, front and back: each crossing below the middle tints what is behind
        b = (origin * fwd).sum(-1)
        c = (origin * origin).sum(-1) - 50 ** 2
        root = np.sqrt(np.maximum(b * b - c, 0))
        zf = (origin + fwd * (-b - root)[..., None])[..., 2]
        zb = (origin + fwd * (-b + root)[..., None])[..., 2]
        colour, opacity = np.array(tint[0]), min(1.0, tint[1] * 1.6)
        front = (inside & (zf < 0)).astype(float)
        back = (inside & (zb < 0) & ~hit).astype(float)
        layers = front + back
        rgb = rgb * (1 - opacity * front[..., None]) + colour * opacity * front[..., None]
    else:
        layers = np.zeros(U.shape)
    glass = np.clip((rr / 50) ** 6, 0, 1) * inside                  # brighter toward the rim
    shine = np.exp(-(((U + 22) ** 2 + (V - 24) ** 2) / 120)) * inside
    alpha = np.where(hit & inside, 1.0, np.clip(0.18 + 0.6 * glass + 0.7 * shine + 0.3 * layers, 0, 1)) * inside
    empty = np.array([0.85, 0.93, 1.0]) if tint is None else None
    if tint is None:
        col = np.where((hit & inside)[..., None], rgb, empty)
    else:
        glassy = np.where((layers > 0)[..., None], np.array(tint[0]) * 0.85 + 0.15, np.array([0.85, 0.93, 1.0]))
        col = np.where((hit & inside)[..., None], rgb, glassy)
    col = col + (1 - col) * (0.8 * shine)[..., None] * (hit & inside)[..., None]
    rgba = np.dstack([col, alpha])
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    im.resize((256, 256), Image.LANCZOS).save(out)


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "tile":
        render(a[2], a[3], 25, 0.25, 0, size=512, tile=True)
    else:
        render(a[1], a[2], float(a[3]) if len(a) > 3 else 20, float(a[4]) if len(a) > 4 else 0.25, float(a[5]) if len(a) > 5 else 0)
