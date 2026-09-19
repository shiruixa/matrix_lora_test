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
