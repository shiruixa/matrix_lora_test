# -*- coding: utf-8 -*-
"""LoRA / 模型扫描 —— 路径从 COMFYUI_DIR 推导，不硬编码盘符。

COMFYUI_DIR 是项目里唯一的 ComfyUI 路径源（定义在
paths.py）。
历史坑：早期硬编码盘符 → 换机后 LoRA 列表永远是空的。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _comfyui_dir():
    # 走 paths 统一解析（环境变量 → config.json → 包内兜底）。
    # 早期这里为了拿一个路径常量而 import 了外部模块，把 485MB 权重拖进了
    # 依赖链 —— 那块不随本工具发布，所以改成自解析。
    try:
        import paths
        return paths.comfyui_dir()
    except Exception:
        return ""


COMFYUI_DIR = _comfyui_dir()
LORAS_ROOT = os.path.join(COMFYUI_DIR, "models", "loras") if COMFYUI_DIR else ""

# base_model 候选目录 —— 实测 anima_baseV10 在 diffusion_models、
# terraRising 在 checkpoints，两个都得扫，缺一个用户就选不到模型
MODEL_DIRS = ("diffusion_models", "unet", "checkpoints")
# CLIP / VAE 也各有自己的目录，命名习惯因模型栈而异，所以都扫上。
# 底模/CLIP/VAE 三项全部由用户在「新建矩阵」页里选，工具不预设任何模型。
CLIP_DIRS = ("clip", "text_encoders")
VAE_DIRS = ("vae",)

LORA_EXTS = (".safetensors", ".ckpt", ".pt")
PREVIEW_EXTS = (".jpeg", ".jpg", ".webp", ".png")


def _preview_for(dirpath, stem):
    for ext in PREVIEW_EXTS:
        p = os.path.join(dirpath, stem + ext)
        if os.path.isfile(p):
            return p
    return ""


def scan_loras():
    """扫描 LoRA 库。

    返回 [{'name','noext','relpath','dir','top','ext','size','mtime','has_preview'}]
      name / noext —— 带 / 不带扩展名的纯文件名
      relpath      —— 相对 LORAS_ROOT 的路径，仅供用户辨认（列表左侧显示）
      top          —— relpath 第一段，用作类别筛选（Style / Slider / Pose ...）
    """
    out = []
    if not LORAS_ROOT or not os.path.isdir(LORAS_ROOT):
        return out
    for root, dirs, fnames in os.walk(LORAS_ROOT):
        dirs[:] = [d for d in dirs if d != "recipes"]
        for f in sorted(fnames):
            if not f.lower().endswith(LORA_EXTS):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, LORAS_ROOT)
            stem, ext = os.path.splitext(f)
            parts = rel.replace(os.sep, "/").split("/")
            try:
                st = os.stat(fp)
                size, mtime = st.st_size, st.st_mtime
            except OSError:
                size, mtime = 0, 0
            out.append({
                "name": f,
                "noext": stem,
                "relpath": rel,
                "dir": "/".join(parts[:-1]),
                "top": parts[0] if len(parts) > 1 else "",
                "ext": ext.lower(),
                "size": size,
                "mtime": mtime,
                "has_preview": bool(_preview_for(root, stem)),
            })
    out.sort(key=lambda x: x["relpath"].lower())
    return out


def find_lora_preview(name):
    """按纯文件名（带不带扩展名都行）找 sidecar 预览图，返回绝对路径或 ''。

    只取 basename：先用扫描结果查表，绝不拼接用户传入的路径（防目录穿越）。
    """
    base = os.path.basename(str(name or "").replace("\\", "/"))
    if not base:
        return ""
    if not base.lower().endswith(LORA_EXTS):
        base += ".safetensors"
    stem = os.path.splitext(base)[0]
    for item in scan_loras():
        if item["name"].lower() == base.lower():
            d = os.path.join(LORAS_ROOT, item["dir"].replace("/", os.sep))
            return _preview_for(d, stem)
    return ""


def _scan_dirs(dirs):
    """扫 models/ 下若干子目录里的模型文件。返回 [{'name','group'}]，group = 目录名。"""
    out = []
    if not COMFYUI_DIR:
        return out
    for grp in dirs:
        d = os.path.join(COMFYUI_DIR, "models", grp)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".safetensors", ".ckpt", ".pt")):
                out.append({"name": f, "group": grp})
    return out


def scan_models():
    """扫描可作 base_model 的模型（底模 / UNet / checkpoint）。"""
    return _scan_dirs(MODEL_DIRS)


def scan_clips():
    """扫描可作文本编码器的 CLIP。"""
    return _scan_dirs(CLIP_DIRS)


def scan_vaes():
    """扫描可作 VAE 的模型。"""
    return _scan_dirs(VAE_DIRS)


# ── 清单来源：优先问运行中的 ComfyUI，离线才退回磁盘扫描 ──────────────────
#
# ComfyUI 的每个加载节点都在 /object_info 里暴露「可选模型」的枚举，这才是最准的清单：
#   - 不用先配 ComfyUI 路径（配错也不会静默给空列表）
#   - **尊重 ComfyUI 自己的 extra_model_paths.yaml** —— 模型放在外挂目录也能看到，
#     而硬扫 models/ 是看不到的
#   - 列出来的东西保证是 ComfyUI 真能加载的
#
# 离线时退回扫盘，这样不启动 ComfyUI 也能先配矩阵、看图、跑诊断。
# ⚠️ Power Lora Loader (rgthree) 不暴露枚举（它吃动态字符串），
#    但标准 LoraLoader 给的是同一份清单，所以照样拿得到 LoRA。
API_SOURCES = {
    "models": [("UNETLoader", "unet_name"), ("CheckpointLoaderSimple", "ckpt_name")],
    "clips": [("CLIPLoader", "clip_name")],
    "vaes": [("VAELoader", "vae_name")],
    "loras": [("LoraLoader", "lora_name")],
}
API_TIMEOUT = 6

# 在线状态探测 + 缓存。
#
# ⚠️ 为什么必须有这层：实测本机（装了网络过滤驱动的环境）**连不通的端口要 ~2 秒
# 才返回拒绝**，而不是瞬间 ECONNREFUSED。不缓存的话「底模+CLIP+VAE+LoRA」五处各探
# 一次 = 10 秒白等（下拉框十秒不出东西）。缓存后：ComfyUI 关着时整个 TTL 窗口内
# 只付一次 2 秒。
_API_STATE = {"t": 0.0, "ok": False}
API_PROBE_TTL = 5.0     # 秒 —— 够短，用户启动 ComfyUI 后很快能反映出来


def comfyui_ready(max_age=API_PROBE_TTL):
    """ComfyUI 在线吗？结果缓存 max_age 秒，避免每次都付端口探测的代价。"""
    import time
    now = time.time()
    if now - _API_STATE["t"] < max_age:
        return _API_STATE["ok"]
    p = _paths_module()
    ok = False
    if p:
        import urllib.request
        try:
            with urllib.request.urlopen(p.comfyui_url() + "/system_stats", timeout=2) as r:
                ok = r.status == 200
        except Exception:
            ok = False
    _API_STATE.update(t=now, ok=ok)
    return ok


def _paths_module():
    """取 paths 模块（两种布局都能拿到）；拿不到返回 None。"""
    try:
        import paths
        return paths
    except Exception:
        return None


def _enum_from_api(node, field, timeout=API_TIMEOUT):
    """向 ComfyUI 要某个节点的枚举清单。

    返回 None = **没问到**（连不上/节点不存在）；返回 [] = 问到了但清单是空的。
    这个区别很重要 —— 前者要退回扫盘，后者说明「ComfyUI 确实没有模型」。
    """
    import json
    import urllib.parse
    import urllib.request

    p = _paths_module()
    if not p:
        return None
    try:
        url = "%s/object_info/%s" % (p.comfyui_url(), urllib.parse.quote(node))
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not data:
        return None                      # 节点不存在
    node_def = next(iter(data.values()))
    for sect in ("required", "optional"):
        spec = ((node_def.get("input") or {}).get(sect) or {}).get(field)
        if isinstance(spec, list) and spec and isinstance(spec[0], list):
            return [str(x) for x in spec[0]]
    return []                            # 节点在，但没有这个字段


def _collect_from_api(kind):
    """按 API_SOURCES 收集某一类的名字（去重）。全问不到返回 None。"""
    # 先看一次在线状态（有缓存）—— 离线就直接回 None 走扫盘，
    # 不然后面每个节点都要各等一次连接失败
    if not comfyui_ready():
        return None
    got_any, names = False, []
    for node, field in API_SOURCES[kind]:
        got = _enum_from_api(node, field)
        if got is None:
            continue
        got_any = True
        names.extend(got)
    if not got_any:
        return None
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _model_items(names):
    """API 来的名字没有目录概念，group 统一给 'ComfyUI'（前端靠它做 optgroup）。"""
    return [{"name": n, "group": "ComfyUI"} for n in sorted(names)]


def _lora_items(names):
    """把 ComfyUI 给的相对路径（如 Style/Artist/x.safetensors）拼成与扫盘一致的字段。

    size/mtime 没有就置 0；has_preview 只在磁盘路径能解析出来时才去查 ——
    预览是增强不是依赖，没配路径就是纯文字列表，前端本来就能处理。
    """
    out = []
    for n in names:
        rel = str(n).replace("\\", "/")
        parts = rel.split("/")
        fname = parts[-1]
        stem, ext = os.path.splitext(fname)
        item = {
            "name": fname,
            "noext": stem,
            "relpath": rel,
            "dir": "/".join(parts[:-1]),
            "top": parts[0] if len(parts) > 1 else "",
            "ext": ext.lower(),
            "size": 0,
            "mtime": 0,
            "has_preview": False,
        }
        if LORAS_ROOT:
            fp = os.path.join(LORAS_ROOT, rel.replace("/", os.sep))
            if os.path.isfile(fp):
                try:
                    st = os.stat(fp)
                    item["size"], item["mtime"] = st.st_size, st.st_mtime
                except OSError:
                    pass
                item["has_preview"] = bool(_preview_for(os.path.dirname(fp), stem))
        out.append(item)
    out.sort(key=lambda x: x["relpath"].lower())
    return out


def list_models():
    """底模清单。返回 (items, source)，source ∈ {'comfyui','disk','none'}"""
    names = _collect_from_api("models")
    if names is not None:
        return _model_items(names), "comfyui"
    items = scan_models()
    return items, ("disk" if items else "none")


def list_clips():
    """CLIP 清单。返回 (items, source)"""
    names = _collect_from_api("clips")
    if names is not None:
        return _model_items(names), "comfyui"
    items = scan_clips()
    return items, ("disk" if items else "none")


def list_vaes():
    """VAE 清单。返回 (items, source)"""
    names = _collect_from_api("vaes")
    if names is not None:
        return _model_items(names), "comfyui"
    items = scan_vaes()
    return items, ("disk" if items else "none")


def list_loras():
    """LoRA 清单。返回 (items, source)"""
    names = _collect_from_api("loras")
    if names is not None:
        return _lora_items(names), "comfyui"
    items = scan_loras()
    return items, ("disk" if items else "none")
