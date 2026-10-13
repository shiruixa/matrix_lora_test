"""
Matrix viewer config — 持久化上次打开的目录（.matrix_viewer_config.json）
"""
import json
import os
import sys
from pathlib import Path

# ⚠️ 数据目录一律走 paths.data_dir()，**不要**用 Path(__file__).parent ——
#    冻结成 exe 之后 __file__ 指向 _internal/，用户的配置/预设会被写进去，
#    既找不到、又会在换 exe 时被覆盖。见 paths.data_dir() 的说明。
_HERE_DIR = os.path.dirname(os.path.abspath(__file__))
if _HERE_DIR not in sys.path:
    sys.path.insert(0, _HERE_DIR)
import paths as _paths          # noqa: E402  （paths 不 import 本模块，无循环）

# 默认目录 = ComfyUI 的 output/matrix（生图与 task.json 都写在那里）
try:
    from paths import COMFYUI_OUTPUT
    DEFAULT_FOLDER = os.path.join(COMFYUI_OUTPUT.replace("/", os.sep), "matrix")
except Exception:
    DEFAULT_FOLDER = ""

CONFIG_FILE = Path(_paths.data_dir()) / ".matrix_viewer_config.json"


def load():
    defaults = {"last_folder": DEFAULT_FOLDER}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            cfg.setdefault("last_folder", DEFAULT_FOLDER)
            return cfg
        except (json.JSONDecodeError, OSError):
            return dict(defaults)
    return dict(defaults)


def save(cfg):
    merged = load()
    merged.update(cfg)
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=2)
    except OSError:
        pass


# ── 矩阵配置预设 ──────────────────────────────────────────────────────
# 预设就是一份合法的 matrix_generator 配置（中文键名），可以直接
#   python matrix_generator.py <预设>.json
# ⚠️ 绝不能存进 json/ —— task_runner.main() 会把那里
#    最新的文件当任务清单，遇到 dict 会迭代出字符串键然后崩溃。

PRESET_DIR = Path(_paths.data_dir()) / "matrix_configs"


def _safe_preset_name(name):
    """只允许常规字符，防路径穿越。返回 '' 表示非法。"""
    import re
    n = str(name or "").strip()
    if not n or len(n) > 80:
        return ""
    if not re.match(r"^[\w一-鿿 .\-()（）]+$", n):
        return ""
    return n


def list_presets():
    """列出预设，附摘要 —— 弹窗里要能一眼看出「这份配置是干嘛的」。

    只读顶层几个键，不把整份配置塞进列表响应。
    """
    if not PRESET_DIR.is_dir():
        return []
    out = []
    for f in sorted(PRESET_DIR.glob("*.json")):
        try:
            mtime = f.stat().st_mtime
            cfg = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(cfg, dict):
            continue
        sz = cfg.get("尺寸") or {}
        scenes = [s for s in (cfg.get("场景") or []) if str(s).strip()]
        out.append({
            "name": f.stem,
            "mtime": mtime,
            "task": str(cfg.get("任务名") or ""),
            "model": str(cfg.get("base_model") or ""),
            "fixed": len(cfg.get("常驻lora") or []),
            "matrix": len(cfg.get("lora矩阵") or cfg.get("loras") or []),
            "scenes": len(scenes),
            "steps": cfg.get("steps", ""),
            "cfg": cfg.get("cfg", ""),
            "batch": cfg.get("batch", 1),
            "size": "%s×%s" % (sz.get("宽", "?"), sz.get("高", "?")),
            "loras": [l.get("lora", "") for l in (cfg.get("lora矩阵") or cfg.get("loras") or [])][:6],
        })
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


def load_preset(name):
    n = _safe_preset_name(name)
    if not n:
        return {"ok": False, "error": "非法的配置名"}
    p = PRESET_DIR / f"{n}.json"
    if not p.is_file():
        return {"ok": False, "error": "配置不存在"}
    try:
        with open(p, encoding="utf-8") as f:
            return {"ok": True, "name": n, "config": json.load(f)}
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def save_preset(name, cfg):
    """整份写入（不是合并）—— 否则 UI 里删掉一行 LoRA 永远删不掉。"""
    n = _safe_preset_name(name)
    if not n:
        return False, "非法的配置名"
    if not isinstance(cfg, dict) or not cfg:
        return False, "配置为空"
    try:
        PRESET_DIR.mkdir(parents=True, exist_ok=True)
        with open(PRESET_DIR / f"{n}.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        return False, str(exc)
    return True, ""


def delete_preset(name):
    n = _safe_preset_name(name)
    if not n:
        return False
    p = PRESET_DIR / f"{n}.json"
    try:
        if p.is_file():
            p.unlink()
            return True
    except OSError:
        pass
    return False
