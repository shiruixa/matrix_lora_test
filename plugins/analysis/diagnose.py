# -*- coding: utf-8 -*-
"""LoRA 融合质量诊断 —— 从生成结果反推「哪组参数能一起用」。

和 similarity.py 共用同一批颜色/纹理特征，但**不问「哪两张像」**（那个问题对
「挑最佳融合」没有指导意义），而是回答四个有决策价值的问题：

  ① 这个 LoRA 到底有没有效果？      —— 与 baseline 的距离
  ② 哪些组合崩了？                  —— 离群检测
  ③ 强度加到多少就饱和了？          —— 相邻档位的距离增量
  ④ 这两个 LoRA 一起用会打架吗？    —— 三角关系（单用A / 单用B / 一起用）

## 为什么不用学术界那套

文献里的评价手段（CLIPScore / DINO / DreamSim / ArcFace / HPSv3 / MLLM）
都要额外模型，本机 models/clip_vision/ 是空的。而且 CLIPScore 已被证明
与人类判断相关性接近零（-0.006 / 0.083）。

这里只用已有的颜色/纹理特征——虽然粗糙，但**全部可解释、可复现、
零依赖**，且这四项诊断本来就不需要语义理解。

## 结构调整（2026-09-19）：拆耦合，没改算法

原来四项诊断是 `diagnose()` 里 150 行顺序代码，共享一堆局部变量；阈值是模块级
常量，改一个数要动代码。现在：

  - **阈值** → `DEFAULTS` + `load_params()` 读 `analysis.json`（缺失键补默认）
  - **四项分析** → 各自一个 `_xxx(ctx)` 函数，签名统一，共享状态装在 `ctx` 里
  - **清单** → `ANALYSES`，加一项 / 删一项就是动一行

`diagnose()` 的**返回键名与结构完全没变**，前端不用改。算法本身一行没动。

以后要换算法、加第五项诊断、接 CLIP/DINO，都只动对应那一个函数或往 ANALYSES
加一行即可 —— 不用先拆骨架。
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
# 正常情况靠 paths.TOOL_DIR 定位（它就是本文件所在目录）；这只是拿不到 paths 时的兜底
_TOOL_ROOT_GUESS = _HERE


# ── 可调阈值 ──────────────────────────────────────────────────────────────
# 这些数是拍脑袋定的经验值，方向明确但具体取值可以调。改 analysis.json 即可，
# 不用动代码 —— 以前它们是模块级常量，调一个数就得改源文件。
DEFAULTS = {
    "outlier_sigma":   2.0,   # 离群：到其他点的平均距离 > μ + 2σ
    "effect_weak":     0.35,  # 有效性：与 baseline 距离 / 全局平均距离 低于此 = 几乎没影响
    "effect_strong":   0.8,   # 有效性：高于此 = 效果显著
    "saturation_drop": 0.45,  # 饱和：相邻档增量跌到峰值增量的这个比例以下
    "interfere_ratio": 1.0,   # 干扰：偏离中间态 / (A与B距离的一半)，>1 即跑到两者之外
}

# 参数自描述 —— 将来前端要自动生成调节控件，靠这张表（照项目里参数注册表的一贯做法：
# 每个参数自带 type/default/min/max/label/help）。
PARAM_SPEC = {
    "outlier_sigma":   {"type": "number", "min": 1.0, "max": 5.0, "step": 0.1,
                        "label": "离群阈值(σ)", "help": "越大越宽松，越不容易判成可疑组合"},
    "effect_weak":     {"type": "number", "min": 0.0, "max": 1.0, "step": 0.05,
                        "label": "无效下限", "help": "与 baseline 的相对距离低于此 → 判「无效」"},
    "effect_strong":   {"type": "number", "min": 0.0, "max": 3.0, "step": 0.05,
                        "label": "显著下限", "help": "高于此 → 判「显著」"},
    "saturation_drop": {"type": "number", "min": 0.1, "max": 0.9, "step": 0.05,
                        "label": "饱和判定比例", "help": "相邻档增量跌到峰值的这个比例以下即视为饱和"},
    "interfere_ratio": {"type": "number", "min": 0.5, "max": 2.0, "step": 0.05,
                        "label": "干扰判定比值", "help": ">1 说明融合结果跑到「单用A」和「单用B」之外"},
}


def config_path():
    """`analysis.json` 的位置。两种布局都把工具根当成它的家。"""
    try:
        # paths 是工具自己的路径解析模块。这一行由打包器负责在两种布局间改写
        # （注释必须单独占行 —— 行尾注释会让改写正则匹配不上）。
        import paths
        if getattr(paths, "TOOL_DIR", ""):
            return os.path.join(paths.TOOL_DIR, "analysis.json")
    except Exception:
        pass
    return os.path.join(_TOOL_ROOT_GUESS, "analysis.json")


def load_params():
    """读 analysis.json；缺失键用 DEFAULTS 补齐，读不到就全是默认值。

    照抄项目里「配置 + 默认值合并」的一贯写法（见 matrix_viewer/config.py）。
    坏文件不抛异常 —— 分析照跑，只是用默认阈值。
    """
    p = config_path()
    raw = {}
    try:
        with open(p, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            raw = loaded
    except (OSError, ValueError):
        pass
    out = dict(DEFAULTS)
    for k in DEFAULTS:
        if k in raw:
            try:
                out[k] = float(raw[k])
            except (TypeError, ValueError):
                pass                        # 手填错了就退回默认值，别让整页崩掉
    return out


def describe_params():
    """参数清单（含中文说明），给未来的配置界面 / 文档用。"""
    cur = load_params()
    out = []
    for k, spec in PARAM_SPEC.items():
        out.append({"key": k, "value": cur.get(k), "default": DEFAULTS[k], **spec})
    return out


# ── 基础工具 ──────────────────────────────────────────────────────────────

def _dist(a, b):
    return float(np.linalg.norm(a - b))


def _groups(keep, dim):
    """按某个维度的取值分组，返回 {值: [索引...]}"""
    g = {}
    for i, (t, _p) in enumerate(keep):
        v = (t.get("坐标") or {}).get(dim)
        if v is None:
            continue
        g.setdefault(v, []).append(i)
    return g


def _centroid(Xn, idxs):
    return Xn[idxs].mean(axis=0)


def _key(task):
    """显示用的名字（组合文件夹，不带场景序号）"""
    return task.get("_combo_dir") or task.get("组合文件夹") or ""


def _sel_key(task):
    """和「组合选择」弹窗对齐的键 —— 那边是 `组合文件夹#场景序号`。

    下面对得上，诊断结论里的「只跑这些」按钮才能真的勾中。
    """
    return "%s#%s" % (_key(task), task.get("场景序号", 0))


# ── 共享上下文 ────────────────────────────────────────────────────────────
# 四项分析都要用到「全局尺度」和「baseline」，以前是 diagnose() 里的局部变量。
# 抽成 ctx 之后每项分析只吃 ctx，互相之间不直接耦合。

def _make_ctx(Xn, keep, dim_names, params):
    n = Xn.shape[0]

    # 全局平均距离，用作各处的参照尺度
    all_d = [_dist(Xn[i], Xn[j]) for i in range(n) for j in range(i + 1, n)]
    scale = float(np.mean(all_d)) if all_d else 1.0
    if scale <= 1e-9:
        scale = 1.0

    # baseline：所有被测维度都为 0（或缺失）的组合
    base_idx = []
    for i, (t, _p) in enumerate(keep):
        co = t.get("坐标") or {}
        if not co or all(abs(float(v)) < 1e-9 for v in co.values()):
            base_idx.append(i)
    base_c = _centroid(Xn, base_idx) if base_idx else None

    return {
        "Xn": Xn, "keep": keep, "dim_names": dim_names, "n": n,
        "params": params, "scale": scale,
        "base_idx": base_idx, "base_c": base_c,
    }


# ── ① 有效 / 无效 ─────────────────────────────────────────────────────────

def _effectiveness(ctx):
    Xn, keep, dim_names = ctx["Xn"], ctx["keep"], ctx["dim_names"]
    scale, base_c = ctx["scale"], ctx["base_c"]
    weak, strong = ctx["params"]["effect_weak"], ctx["params"]["effect_strong"]

    effective = []
    if base_c is not None:
        for dim in dim_names:
            g = _groups(keep, dim)
            isolated = None
            for v, idxs in g.items():
                if abs(float(v)) < 1e-9:
                    continue
                # 优先用「只有这一维非零」的组合，避免别的 LoRA 混进来
                pure = [i for i in idxs
                        if all(abs(float(x)) < 1e-9
                               for k, x in (keep[i][0].get("坐标") or {}).items() if k != dim)]
                if pure:
                    isolated = pure
                    break
                if isolated is None:
                    isolated = [i for i in idxs if abs(float(v)) > 1e-9]
            if not isolated:
                continue
            d = _dist(_centroid(Xn, isolated), base_c)
            rel = d / scale
            verdict = ("无效" if rel < weak else "显著" if rel >= strong else "有效")
            effective.append({
                "dim": dim,
                "dist": round(d, 3),
                "ratio": round(rel, 2),
                "verdict": verdict,
                "samples": len(isolated),
            })
    # 先按距离排，再按判定排 —— 两次排序都要保留，第二次是稳定排序，
    # 少了第一次，同判定内部的顺序会跟以前不一样
    verdict_rank = {"无效": 0, "有效": 1, "显著": 2}
    effective.sort(key=lambda x: -x["dist"])
    effective.sort(key=lambda x: (verdict_rank.get(x["verdict"], 1), -x["dist"]))
    return effective


# ── ② 离群 / 崩坏 ─────────────────────────────────────────────────────────

def _outliers(ctx):
    Xn, keep, n = ctx["Xn"], ctx["keep"], ctx["n"]
    sigma = ctx["params"]["outlier_sigma"]

    self_avg = []
    for i in range(n):
        ds = [_dist(Xn[i], Xn[j]) for j in range(n) if j != i]
        self_avg.append(float(np.mean(ds)) if ds else 0.0)
    mu = float(np.mean(self_avg))
    sd = float(np.std(self_avg))
    thr = mu + sigma * sd

    outliers = []
    for i, v in enumerate(self_avg):
        if v > thr and sd > 1e-9:
            # baseline 天然离群（它不加任何 LoRA），不算「可疑」——
            # 混进去会把真正崩掉的组合挤下去
            if i in ctx["base_idx"]:
                continue
            outliers.append({
                "key": _sel_key(keep[i][0]),
                "name": _key(keep[i][0]),
                "score": round(v, 3),
                "sigma": round((v - mu) / sd, 2),
                "img": (keep[i][0].get("_images") or [""])[0],
                "coords": keep[i][0].get("坐标") or {},
            })
    outliers.sort(key=lambda x: -x["sigma"])
    return outliers


# ── ③ 强度饱和点 ──────────────────────────────────────────────────────────

def _saturation(ctx):
    Xn, keep, dim_names = ctx["Xn"], ctx["keep"], ctx["dim_names"]
    drop = ctx["params"]["saturation_drop"]

    saturation = []
    for dim in dim_names:
        g = _groups(keep, dim)
        vals = sorted(float(v) for v in g.keys())
        if len(vals) < 3:
            continue
        cents = [_centroid(Xn, g[v]) for v in vals]
        deltas = [_dist(cents[i], cents[i + 1]) for i in range(len(cents) - 1)]
        if not deltas or max(deltas) <= 1e-9:
            continue
        mx = max(deltas)
        # 第一个「增量跌到峰值以下」的位置 —— 之后再加强度收益递减
        point = None
        for i, d in enumerate(deltas):
            if d < mx * drop:
                point = vals[i]        # 从这一档起
                break
        if len(deltas) < 3:
            note = "只有 %d 档，判断不了饱和（至少 4 档）" % len(vals)
        elif point is None:
            note = "全程都有明显变化，没看到饱和"
        else:
            note = "%s 之后变化趋缓，再往上加收益递减" % round(point, 3)
        saturation.append({
            "dim": dim,
            "levels": [round(v, 3) for v in vals],
            "deltas": [round(d, 3) for d in deltas],
            "peak": round(mx, 3),
            "point": (round(point, 3) if point is not None else None),
            "enough": len(deltas) >= 3,
            "note": note,
        })
    return saturation


# ── ④ 互相干扰 ────────────────────────────────────────────────────────────

def _interference(ctx):
    Xn, keep, dim_names = ctx["Xn"], ctx["keep"], ctx["dim_names"]
    limit = ctx["params"]["interfere_ratio"]

    interference = []
    for a in range(len(dim_names)):
        for b in range(a + 1, len(dim_names)):
            da, db = dim_names[a], dim_names[b]
            only_a, only_b, both = [], [], []
            for i, (t, _p) in enumerate(keep):
                co = t.get("坐标") or {}
                va, vb = co.get(da), co.get(db)
                if va is None or vb is None:
                    continue
                pa, pb = abs(float(va)) > 1e-9, abs(float(vb)) > 1e-9
                if pa and not pb:
                    only_a.append(i)
                elif pb and not pa:
                    only_b.append(i)
                elif pa and pb:
                    both.append(i)
            if not only_a or not only_b or not both:
                continue
            ca, cb, cab = (_centroid(Xn, only_a), _centroid(Xn, only_b),
                           _centroid(Xn, both))
            d_ab = _dist(ca, cb)
            if d_ab <= 1e-9:
                continue
            # 理想融合落在 ca/cb 之间 → min(偏离) ≤ d_ab/2。比值 >1 就是跑到外面了
            ratio = min(_dist(cab, ca), _dist(cab, cb)) / (d_ab / 2.0)
            interference.append({
                "a": da, "b": db,
                "ratio": round(ratio, 2),
                "d_ab": round(d_ab, 3),
                "samples": len(both),
                "verdict": ("可能互相干扰" if ratio > limit
                            else "融合正常" if ratio > 0.6 else "高度融合"),
            })
    interference.sort(key=lambda x: -x["ratio"])
    return interference


# ── 分析清单：加一项诊断 = 加一行 ─────────────────────────────────────────
# (返回键名, 显示标题, 函数)。键名必须和前端 simRenderReport() 里读的一致。
ANALYSES = [
    ("effective",    "① LoRA 有效性",   _effectiveness),
    ("outliers",     "② 可疑组合",      _outliers),
    ("saturation",   "③ 强度饱和点",    _saturation),
    ("interference", "④ LoRA 互相干扰", _interference),
]


def diagnose(Xn, keep, dim_names, params=None):
    """四项诊断。Xn 是标准化后的高维特征 (n,d)，keep 是 [(task, path)]。

    params 不传就读 analysis.json（缺失键补 DEFAULTS）。
    """
    n = Xn.shape[0]
    if n < 3:
        return None

    if params is None:
        params = load_params()
    ctx = _make_ctx(Xn, keep, dim_names, params)

    out = {
        "n": n,
        "scale": round(ctx["scale"], 3),
        "baseline": _key(keep[ctx["base_idx"][0]][0]) if ctx["base_idx"] else "",
        "thresholds": dict(params),
    }

    # 逐项独立跑：一项炸了不影响其余（原来一项出问题会整块失败）
    for key, _title, fn in ANALYSES:
        try:
            out[key] = fn(ctx)
        except Exception as exc:
            out[key] = []
            out.setdefault("_errors", {})[key] = "%s: %s" % (type(exc).__name__, exc)

    return out


def available_analyses():
    """给前端/文档用的清单（将来做配置界面时按这个列条目）。"""
    return [{"key": k, "title": t} for k, t, _fn in ANALYSES]
