# -*- coding: utf-8 -*-
"""ComfyUI 路径解析 —— 唯一入口，取代分散在各处的路径推导。

## 为什么单独抽出来

原来 `matrix_viewer/loras.py` 为了拿一个 `COMFYUI_DIR` 常量 import 了
一个外部模块 —— 只为一行字符串，却把 485MB 的模型权重拖进了依赖链。
本工具不发布那一块，所以在这里自解析。

## 优先级（发布给谁都能跑）

  1. 环境变量 `COMFYUI_DIR`              —— CI / 临时切换
  2. `config.json` 的 `comfyui_dir`  —— 别人拿到后改这里
  3. 包内常量 `COMFYUI_OUTPUT` 的父目录   —— 作者本机兜底

第 3 条让本机**完全不用改任何东西**就能继续跑。
"""
# ── 扁平目录自举 ───────────────────────────────────────────────────────
# ComfyUI 便携版的 python_embeded 带 python313._pth，那条 ._pth 把 sys.path
# 写死成「便携版的 ComfyUI/ + zip + .」——**不含脚本所在目录**。所以直接
# `python task_runner.py` 会 ModuleNotFoundError: png_meta（本工具所有模块都
# 同目录，靠这一句自举）。用系统 Python 跑同样的问题不会出现，只有便携版会。
import os as _os
import sys as _sys

_HERE_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _HERE_DIR not in _sys.path:
    _sys.path.insert(0, _HERE_DIR)
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "config.json")

# 工具根目录 —— 本文件所在目录。
# 源码布局是 ，扁平发布包里就是那个唯一的文件夹，两种情况都对，
# 所以「工具自己的配置文件放哪」一律由这里推导，别的模块不用各自猜路径。
TOOL_DIR = _HERE


def _from_env():
    v = (os.environ.get("COMFYUI_DIR") or "").strip()
    return v.replace("/", os.sep) if v else ""


def _from_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(cfg, dict):
        return ""
    v = str(cfg.get("comfyui_dir") or "").strip()
    return v.replace("/", os.sep) if v else ""


# 兜底路径常量 —— 发布版留空，请用 COMFYUI_DIR 或 config.json 指定。
# ⚠️ 必须放在 paths 自己这里，不能回头 import paths.py
# （那个文件会 `from . import paths`，反过来就循环了）。
LEGACY_OUTPUT = ""    # 发布版留空：没配 COMFYUI_DIR / config.json 时由界面提示


def _fallback():
    """兜底：从 LEGACY_OUTPUT 反推 ComfyUI 根目录（发布版为空 → 返回空串）。"""
    if not LEGACY_OUTPUT:
        return ""
    return os.path.dirname(os.path.abspath(LEGACY_OUTPUT.replace("/", os.sep)))


def comfyui_dir():
    """ComfyUI 根目录；解析不出来返回 ''（调用方据此给提示，别默默用相对路径）。"""
    return _from_env() or _from_config() or _fallback()


def output_dir():
    """ComfyUI 的 output 目录。"""
    d = comfyui_dir()
    return os.path.join(d, "output") if d else ""


def source():
    """当前用的是哪一档来源 —— 排查「路径不对」时有用。"""
    if _from_env():
        return "环境变量 COMFYUI_DIR"
    if _from_config():
        return "config.json"
    if _fallback():
        return "包内常量兜底（作者本机）"
    return "解析失败"


def report():
    """给启动日志用的一行诊断。"""
    d = comfyui_dir()
    return "ComfyUI 目录: %s  (来源: %s)" % (d or "(未解析到)", source())


__all__ = ["comfyui_dir", "output_dir", "source", "report", "CONFIG_PATH"]

if __name__ == "__main__":
    print(report())
    print("  LoRA 目录:", os.path.join(comfyui_dir(), "models", "loras"))
    print("  配置文件  :", CONFIG_PATH, "(存在)" if os.path.isfile(CONFIG_PATH) else "(不存在，用兜底)")


# 扁平版：原来由包的 __init__.py 提供，现在归到这里
COMFYUI_OUTPUT = output_dir()
