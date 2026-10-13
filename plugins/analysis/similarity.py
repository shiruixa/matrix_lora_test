# -*- coding: utf-8 -*-
"""图片视觉相似度 —— 特征提取 + 降维，供「相似度」标签页的散点图用。

## 为什么不用 CLIP

CLIP 是在**图文对**上训练的，编码的是语义（"图里有什么"），对**画风/质感不敏感** ——
同一个角色用两种画风渲染，在 CLIP 空间里几乎重合，而画风恰恰是矩阵测试最主要的场景。

所以这里用颜色/纹理特征，它们在「厚涂 vs 平涂 vs 线稿」上的差异是数量级的。
要补语义维度的话得往 ComfyUI 的 models/clip_vision/ 放模型（现在那个目录是空的），
那是另一条路，不是这里的替代品。

## 特征构成

- HSV 直方图 8×8×8 = 512 维 —— 色调/饱和/明度分布
- 边缘密度梯度直方图 16 维 —— 线条多寡
- 色彩统计 11 维 —— 均值/方差/饱和度/高梯度像素占比

合计 **539 维**（旧注释写「色彩统计 12 维 / 合计 540」是数错了，实测 11/539）。

只依赖 PIL + numpy（装 ComfyUI 时通常已带）。
"""
import os
import sys
from urllib.parse import unquote

# PIL 只在真正算特征时才需要 —— 模块级不硬 import，
# 这样缺 Pillow 时前端能拿到一条说人话的提示，而不是裸的 ModuleNotFoundError。
# （本机有多个 Python，launcher.py 用 sys.executable 传递解释器，
#   从没装 Pillow 的那个启动就会走到这里）
try:
    from PIL import Image
    import numpy as np
    _HAS_DEPS = True
    _MISSING = ""
except ImportError as _e:
    Image = None
    np = None
    _HAS_DEPS = False
    _MISSING = str(_e)


def _missing_hint():
    return ("相似度需要 Pillow + numpy，当前解释器缺少：%s\n"
            "当前 Python：%s\n"
            "请改用装了它们的解释器启动，例如：\n"
            r"  <装了 Pillow + numpy 的解释器> "
            r"matrix_viewer.py") % (_MISSING, sys.executable)

FEAT_SIZE = 128          # 缩放到这个边长再算特征，够用且快
DEFAULT_LIMIT = 400      # 最多处理多少张（几百张几秒钟）


# ── 特征块 ────────────────────────────────────────────────────────────────
# 每种特征一个独立函数，签名统一（a = RGB float 数组，im = 缩放后的 PIL 图），
# 各自算各自的，互不依赖。加一种特征 = 往 FEATURES 加一行，不用碰这个函数体。
#
# ⚠️ FEATURES 的顺序 = 特征向量的拼接顺序 = 距离空间的坐标含义。
#    改顺序或删块会让「和历史结果对比」失效（维度都变了），加块则向后兼容。

def _gray_mag(a):
    """灰度梯度幅值（边缘块和统计块都要用，抽出来共用）"""
    g = a.mean(axis=2)
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    return np.sqrt(gx * gx + gy * gy)


def _f_hsv(a, im):
    """① HSV 直方图 8×8×8 = 512 维 —— 色调/饱和/明度分布"""
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32)
    h = np.clip((hsv[:, :, 0] / 256.0 * 8).astype(np.int32), 0, 7)
    s = np.clip((hsv[:, :, 1] / 256.0 * 8).astype(np.int32), 0, 7)
    v = np.clip((hsv[:, :, 2] / 256.0 * 8).astype(np.int32), 0, 7)
    hist = np.bincount((h * 64 + s * 8 + v).ravel(), minlength=512).astype(np.float32)
    hist /= max(1.0, float(hist.sum()))
    return hist


def _f_edge(a, im):
    """② 边缘密度梯度直方图 16 维 —— 线条多寡"""
    mag = _gray_mag(a).ravel()
    ed, _ = np.histogram(mag, bins=16, range=(0.0, 0.5))
    return ed.astype(np.float32) / max(1.0, float(ed.sum()))


def _f_stats(a, im):
    """③ 色彩统计 11 维 —— 均值/方差/饱和度/高梯度像素占比"""
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32)
    flat = a.reshape(-1, 3)
    sat = hsv[:, :, 1] / 255.0
    val = hsv[:, :, 2] / 255.0
    mag = _gray_mag(a).ravel()
    return np.array([
        *flat.mean(axis=0), *flat.std(axis=0),
        float(sat.mean()), float(sat.std()),
        float(val.mean()), float(val.std()),
        float((mag > 0.15).mean()),
    ], dtype=np.float32)


FEATURES = [
    ("hsv",   _f_hsv),
    ("edge",  _f_edge),
    ("stats", _f_stats),
]


def _features(path):
    """单张图的特征向量（各块按 FEATURES 顺序拼起来）；读不了返回 None。"""
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    im = im.resize((FEAT_SIZE, FEAT_SIZE), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32) / 255.0
    return np.concatenate([fn(a, im) for _name, fn in FEATURES]).astype(np.float32)


def pca_2d(X):
    """标准化后 PCA 降到 2 维。返回 (coords, 各主成分解释方差比)。"""
    if X.shape[0] < 2:
        return np.zeros((X.shape[0], 2), dtype=np.float32), [0.0, 0.0]
    X = X - X.mean(axis=0, keepdims=True)
    sd = X.std(axis=0, keepdims=True)
    sd[sd < 1e-8] = 1.0                 # 常量维度别把标准差搞成 0
    Z = X / sd
    # 用 SVD 而不是协方差特征分解 —— 数值上稳得多
    U, S, _ = np.linalg.svd(Z, full_matrices=False)
    coords = (U[:, :2] * S[:2]).astype(np.float32)
    var = S ** 2
    tot = float(var.sum())
    ratio = (var[:2] / tot).tolist() if tot > 0 else [0.0, 0.0]
    return coords, ratio


def _real_path(image_url):
    """`/image?path=<quote(...)>` → 真实文件路径"""
    if "path=" in image_url:
        return unquote(image_url.split("path=", 1)[1])
    return image_url


def _stats(Xn, keep, ratio, top=5):
    """数值化统计 —— 供前端表格展示。

    距离一律用**标准化后的高维特征**算，不用 PCA 的 2D 投影：
    前两主成分只解释了约三分之一方差，投影距离会失真。
    """
    from itertools import combinations
    n = Xn.shape[0]
    if n < 2:
        return None

    # ① 两两距离
    pairs = []
    for i, j in combinations(range(n), 2):
        d = float(np.linalg.norm(Xn[i] - Xn[j]))
        pairs.append((d, i, j))
    pairs.sort()
    dists = [p[0] for p in pairs]
    mean_d = float(np.mean(dists))

    def _pair(rec):
        d, i, j = rec
        return {
            "dist": round(d, 3),
            "a": keep[i][0].get("_combo_dir") or keep[i][0].get("组合文件夹") or "",
            "b": keep[j][0].get("_combo_dir") or keep[j][0].get("组合文件夹") or "",
            "a_img": (keep[i][0].get("_images") or [""])[0],
            "b_img": (keep[j][0].get("_images") or [""])[0],
        }

    # ② 各维度影响力：该维度不同取值之间的**平均跨组距离**。
    #    越大 = 这个 LoRA 对画面的影响越大
    dim_names = []
    for t, _p in keep:
        for k in (t.get("坐标") or {}):
            if k not in dim_names:
                dim_names.append(k)
    influence = []
    for dim in dim_names:
        groups = {}
        for idx, (t, _p) in enumerate(keep):
            v = (t.get("坐标") or {}).get(dim)
            if v is None:
                continue
            groups.setdefault(v, []).append(idx)
        if len(groups) < 2:
            continue                     # 只有一个取值 → 不构成维度
        vals = list(groups.values())
        ds = []
        for a in range(len(vals)):
            for b in range(a + 1, len(vals)):
                for i in vals[a]:
                    for j in vals[b]:
                        ds.append(float(np.linalg.norm(Xn[i] - Xn[j])))
        influence.append({
            "dim": dim,
            "spread": round(float(np.mean(ds)), 3) if ds else 0.0,
            "levels": len(groups),
            "ratio": round((float(np.mean(ds)) / mean_d), 2) if ds and mean_d > 0 else 0.0,
        })
    influence.sort(key=lambda x: -x["spread"])

    return {
        "n": n,
        "pairs": len(pairs),
        "pca": [round(ratio[0], 4), round(ratio[1], 4)],
        "dist": {"mean": round(mean_d, 3), "min": round(dists[0], 3), "max": round(dists[-1], 3)},
        "influence": influence,
        "closest": [_pair(p) for p in pairs[:top]],
        "farthest": [_pair(p) for p in pairs[-top:][::-1]],
    }


def similarity_map(tasks, limit=DEFAULT_LIMIT):
    """给每个 task 取第一张图算特征 → 降到 2D 散点。

    返回 {"points": [...], "explained": [r1, r2], "count": n, "skipped": m}
    缺依赖时返回同构结果 + "error" 字段 —— 让前端显示提示，而不是当成崩溃
    """
    if not _HAS_DEPS:
        return {"points": [], "explained": [0.0, 0.0], "count": 0, "skipped": 0,
                "error": _missing_hint()}

    pairs = []
    skipped = 0
    for t in tasks:
        imgs = t.get("_images") or []
        if not imgs:
            continue
        p = _real_path(imgs[0])
        if not os.path.isfile(p):
            skipped += 1
            continue
        pairs.append((t, p))
        if len(pairs) >= limit:
            break

    feats, keep = [], []
    for t, p in pairs:
        f = _features(p)
        if f is None:
            skipped += 1
            continue
        feats.append(f)
        keep.append((t, p))

    if len(feats) < 2:
        return {"points": [], "explained": [0.0, 0.0], "count": len(feats), "skipped": skipped}

    X = np.vstack(feats)
    coords, ratio = pca_2d(X)
    # 标准化后的高维特征 —— 统计用它算距离（PCA 2D 投影只保留约 1/3 方差，会失真）
    sd = X.std(axis=0, keepdims=True)
    sd[sd < 1e-8] = 1.0
    Xn = (X - X.mean(axis=0, keepdims=True)) / sd

    points = []
    for i, (t, _p) in enumerate(keep):
        imgs = t.get("_images") or []
        points.append({
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "key": t.get("_combo_dir") or t.get("组合文件夹") or "",
            "coords": t.get("坐标") or {},
            "img": imgs[0] if imgs else "",
        })
    dim_names = []
    for t, _p in keep:
        for k in (t.get("坐标") or {}):
            if k not in dim_names:
                dim_names.append(k)

    return {"points": points, "explained": ratio, "count": len(points),
            "skipped": skipped, "stats": _stats(Xn, keep, ratio),
            "diagnose": _diagnose(Xn, keep, dim_names)}


def _diagnose(Xn, keep, dim_names):
    """四项融合诊断 —— 单独 try，免得它出问题把整个相似度接口带崩。"""
    try:
        import diagnose as _d
        return _d.diagnose(Xn, keep, dim_names)
    except Exception as exc:
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
