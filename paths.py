# -*- coding: utf-8 -*-
"""ComfyUI 路径解析 —— 唯一入口，取代分散在各处的路径推导。

## 为什么单独抽出来

原来 `matrix_viewer/loras.py` 为了拿一个 `COMFYUI_DIR` 常量 import 了
一个外部模块 —— 只为一行字符串，却把 485MB 的模型权重拖进了依赖链。
本工具不发布那一块，所以在这里自解析。

## 优先级

  1. **运行中的 ComfyUI 自己报的路径**  —— `GET {COMFYUI_URL}/internal/folder_paths`
  2. 环境变量 `COMFYUI_DIR`              —— CI / 临时切换
  3. `config.json` 的 `comfyui_dir`  —— 别人拿到后改这里
  4. 包内常量 `COMFYUI_OUTPUT` 的父目录   —— 作者本机兜底（需目录存在）

第 1 条是最权威的一档：**多个便携版并存时，端口决定一切** —— 连哪个端口就
拿到哪台的路径；模型目录被 `extra_model_paths.yaml` 重定向；ComfyUI 装在移动
硬盘上盘符变了 —— 服务端自己都知道，不用我们猜。旧版 ComfyUI 没这个端点，
请求失败就退回第 2 档，行为与以前一致。

第 4 条让本机**完全不用改任何东西**就能继续跑。
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


def data_dir():
    """运行时数据放哪 —— **exe 旁边**（源码树里就是本文件所在目录）。

    ⚠️ 冻结成 exe 之后 `__file__` 指向 PyInstaller 解出来的 `_internal/`，
    那是**代码目录**，不是放数据的地方：

      · 用户找不到它（不在 exe 旁边，得钻进去）
      · 换一个 exe 就把整个 `_internal/` 覆盖掉 → `config.json`、
        `plugins/`、任务清单**全没**

    所以凡是「要写、要用户看见、要能改」的文件，一律走这里；
    只有只读资源（screenshots 之类）才可以留在 `_internal`。

    开发时行为和以前**完全一样**（还是本文件所在目录），不改变现状。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return _HERE


# 工具根目录 —— 名字保留（6 个模块在用），值改走 data_dir()。
# 源码布局是 ，扁平发布包 / exe 旁边，三种情况都对，
# 所以「工具自己的文件放哪」一律由这里推导，别的模块不用各自猜路径。
TOOL_DIR = data_dir()
CONFIG_PATH = os.path.join(TOOL_DIR, "config.json")


def _from_env():
    v = (os.environ.get("COMFYUI_DIR") or "").strip()
    return v.replace("/", os.sep) if v else ""


def _cfg_get(key):
    """从 config.json 读一个字符串字段；读不到返回 ''。"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(cfg, dict):
        return ""
    return str(cfg.get(key) or "").strip()


def _from_config():
    v = _cfg_get("comfyui_dir")
    return v.replace("/", os.sep) if v else ""


# 兜底路径常量 —— 发布版留空，请用 COMFYUI_DIR 或 config.json 指定。
# ⚠️ 必须放在 paths 自己这里，不能回头 import paths.py
# （那个文件会 `from . import paths`，反过来就循环了）。
LEGACY_OUTPUT = r""   # 发布版不带作者本机路径，请配 COMFYUI_DIR 或 config.json


# ── ComfyUI 服务地址 ──────────────────────────────────────────────────────
# 同一个「ComfyUI 在哪」的问题，只是问的是「服务在哪」而不是「文件在哪」。
# 以前这个地址写死在 5 个文件里，想连别的端口/别的机器就得改代码。
DEFAULT_URL = "http://127.0.0.1:8188"


def _url_from_env():
    return (os.environ.get("COMFYUI_URL") or "").strip()


def comfyui_url():
    """ComfyUI 服务地址。优先级：环境变量 COMFYUI_URL → config.json 的 comfyui_url → 默认。"""
    return (_url_from_env() or _cfg_get("comfyui_url") or DEFAULT_URL).rstrip("/")


def url_source():
    """地址用的是哪一档来源 —— 和 source() 一样，排查「连不上」时有用。"""
    if _url_from_env():
        return "环境变量 COMFYUI_URL"
    if _cfg_get("comfyui_url"):
        return "config.json"
    return "默认值"


def _cfg_set(key, value):
    """往 config.json 写一个字段（保留其它字段）。失败返回 False。"""
    d = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cur = json.load(f)
        if isinstance(cur, dict):
            d = cur
    except (OSError, ValueError):
        pass
    d[key] = value
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def set_comfyui_url(url):
    """切换到另一台 ComfyUI：写进 config.json + 清缓存。返回 (ok, msg)。

    ⚠️ **光写文件不够 —— 调用方还必须刷新各模块里那份 COMFYUI_OUTPUT 拷贝。**
    有 4 个文件在 import 时用 `from paths import COMFYUI_OUTPUT` 或
    `paths.COMFYUI_OUTPUT` 把值拷走了；不刷新它们的话，界面切了实例、
    实际落盘还写在老地方的 output 里 —— 一个「点了没反应」的假切换。

    刷新那一步放在 server.py 做（那里能 import 到全部模块）；本模块
    import server 会循环，所以只能把话说在这里。
    """
    url = (str(url or "")).strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        return False, "地址要以 http:// 或 https:// 开头"
    if _url_from_env():
        return False, ("环境变量 COMFYUI_URL 正覆盖着配置（%s）——"
                       "先清掉那个环境变量才能在这里切" % _url_from_env())
    if not _cfg_set("comfyui_url", url):
        return False, "写 config.json 失败"
    _invalidate()
    return True, url


def _invalidate():
    """丢掉缓存过的服务端信息 —— 换了地址之后必须重问。"""
    global _SERVER_PATHS
    _SERVER_PATHS = None


def publish_url():
    """把解析出来的地址发布到环境变量 COMFYUI_URL。

    为什么要这样：`comfy_api.py`（提交 prompt 用）是独立模块，刻意不反向 import
    本模块。两边靠这个环境变量对齐 —— 工具启动时发布一次，comfy_api 每次请求现读，
    于是「查看器连哪，提交就连哪」。

    已经被显式设过 COMFYUI_URL 就不覆盖（那个优先级更高）。
    """
    if not _url_from_env():
        os.environ["COMFYUI_URL"] = comfyui_url()
    return os.environ["COMFYUI_URL"]


def report():
    """给启动日志用的一行诊断。"""
    d = comfyui_dir()
    return "ComfyUI 目录: %s  (来源: %s)  |  服务: %s (%s)" % (
        d or "(未解析到)", source(), comfyui_url(), url_source())


# ── 问运行中的服务端（最权威的一档）─────────────────────────────────────
# 本工具本来就通过 HTTP 跟 ComfyUI 说话，那就顺便问它一句「你在哪」。
# `GET /internal/folder_paths` 返回各文件夹类型的**绝对路径**，而且那是
# 服务端**自己算出来的** —— 比我们从配置文件猜准得多：
#
#   · **多个便携版并存时，端口决定一切**：连 8188 就拿到 8188 那台的路径，
#     连 8189 就拿到 8189 那台。不用（也不可能）靠配置文件分辨。
#   · 模型目录被 `extra_model_paths.yaml` 重定向到别的盘 —— 服务端报的就是
#     重定向后的真路径，我们反推根目录反而会错。
#   · ComfyUI 装在**移动硬盘**上、盘符从 G: 变成 H: —— 服务端自己知道，
#     我们不用猜。
#
# 所以它在优先级里排在环境变量/config.json **之前**：文件必须落在「正在
# 收我们 prompt 的那台服务」能读到的地方，服务端才是权威。
#
# 降级：旧版 ComfyUI 没有这个端点（本项目的开发机就有一个）→ 请求失败 →
# 静默退回下面几档，行为与以前完全一致。
#
# 拿不到 output（ComfyUI 没暴露它）→ 从模型目录反推，见 `_from_server`。

_SERVER_PATHS = None      # None = 还没问过；{} = 问过但没拿到


def folder_paths_of(url, timeout=1.5):
    """问**指定**的 ComfyUI 实例要它的文件夹路径；失败返回 {}。

    和 `_server_folder_paths()` 的区别：这个不认「当前配置的地址」，问谁由调用方定
    —— 端口发现时要挨个问，不能都用全局地址。
    """
    try:
        import urllib.request
        req = urllib.request.Request(str(url).rstrip("/") + "/internal/folder_paths")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}     # 旧版没这端点 / 服务没起 / 超时


def root_from_folder_paths(fp):
    """从一份 folder_paths 响应反推 ComfyUI 根目录；认不出返回 ''。

    规则：找形如 `<root>/models/<子目录>` 的路径，取 `<root>`，
    **且要求 `<root>/output` 真的存在**才认。那一条同时验证了
    「它确实是 ComfyUI 的根」和「输出目录就在它下面」。

    ⚠️ 不能只看 `loras[0]`：它可能被 extra_model_paths 指到别的盘，
    那样切出来的「根」是假的。所以遍历多个键，谁先通过验证用谁。
    """
    if not isinstance(fp, dict):
        return ""
    for key in ("loras", "checkpoints", "vae", "diffusion_models",
                "text_encoders", "embeddings", "upscale_models", "controlnet"):
        for p in (fp.get(key) or []):
            d = str(p).replace("\\", "/")
            if "/models/" not in d:
                continue
            root = d.split("/models/")[0]
            if root and os.path.isdir(os.path.join(root, "output")):
                return os.path.normpath(root)
    return ""


def _server_folder_paths():
    """当前配置那个地址的 folder_paths。每个进程只问一次。"""
    global _SERVER_PATHS
    if _SERVER_PATHS is None:
        _SERVER_PATHS = folder_paths_of(comfyui_url())
    return _SERVER_PATHS


def _from_server():
    """从服务端报的模型目录反推 ComfyUI 根目录；认不出返回 ''。"""
    return root_from_folder_paths(_server_folder_paths())


def _fallback_path():
    """兜底那一档**不管存不存在**推导出的路径（空串 = 常量没配）。"""
    if not LEGACY_OUTPUT:
        return ""
    return os.path.dirname(os.path.abspath(LEGACY_OUTPUT.replace("/", os.sep)))


def _fallback():
    """作者本机兜底：从 LEGACY_OUTPUT 反推 ComfyUI 根目录，**且目录必须存在**。

    ⚠️ 为什么要校验存在性：不校验的话这一档就是「永远返回一个非空但不存在路径」——
    别人拿到这份工具、什么都不配就跑，会拿到作者本机那个路径，
    然后在下游表现为「LoRA 列表是空的」「落盘失败」这类**和根因无关**的报错，
    而不是「你没配 ComfyUI 路径」。返回 '' 才能让上层给出那句人话提示。
    """
    d = _fallback_path()
    return d if d and os.path.isdir(d) else ""


def fallback_missing():
    """兜底常量配着、但那个目录不在 —— 多半是**移动硬盘没插**。

    之所以要单独区分：作者本机的 ComfyUI 装在**移动硬盘**上，盘符会变、盘会拔。
    这时报「解析失败」会把人引去翻 config.json，而真正该做的是把盘插上、
    或者去 config.json 里改成当前的实际盘符。一句话的差别，排查方向完全不同。
    """
    d = _fallback_path()
    return bool(d) and not os.path.isdir(d)


def comfyui_dir():
    """ComfyUI 根目录；解析不出来返回 ''（调用方据此给提示，别默默用相对路径）。

    顺序 = 服务端 → 环境变量 → config.json → 兜底。
    服务端排第一的理由见上面 `_from_server` 那段注释。
    """
    return _from_server() or _from_env() or _from_config() or _fallback()


def output_dir():
    """ComfyUI 的 output 目录。"""
    d = comfyui_dir()
    return os.path.join(d, "output") if d else ""


# 生图端与查看器共用的输出根目录。
# 以前这个常量住在包的 __init__.py 里；扁平化后没有包了，归到「路径」这个模块最自然。
COMFYUI_OUTPUT = output_dir()


def source():
    """当前用的是哪一档来源 —— 排查「路径不对」时有用。"""
    if _from_server():
        return "运行中的 ComfyUI（%s 的 /internal/folder_paths）" % comfyui_url()
    if _from_env():
        return "环境变量 COMFYUI_DIR"
    if _from_config():
        return "config.json"
    if _fallback():
        return "包内常量兜底（作者本机）"
    if fallback_missing():
        # 和「完全没配」区别开：这条是「配了，但盘不在」——多半是移动硬盘没插
        return "解析失败：兜底路径 %s 不存在（移动硬盘没插？或盘符变了，去 config.json 改成实际路径）" \
               % _fallback_path()
    return "解析失败：没配 ComfyUI 路径（设环境变量 COMFYUI_DIR 或写 config.json）"


# ── 发现本地在跑的 ComfyUI ────────────────────────────────────────────────
# 多个便携版并存时，**端口是唯一的区分依据** —— 配置文件里只能写一个地址，
# 而用户可能同时开着两台（各自的盘、各自的模型/输出目录）。
#
# 判据用 `/system_stats` 的**返回结构**，不是「端口通不通」：后者会把任何
# HTTP 服务都算成 ComfyUI。返回里必须有 `system` 键。
#
# 并行探测：12 个端口 × 0.4s 超时，串行最坏 5 秒，并行只花最慢那个（约 0.4s）。

SCAN_PORTS = tuple(range(8188, 8200))     # ComfyUI 默认 8188，往后顺延常见


def probe_comfyui(url, timeout=0.4):
    """这个地址上跑的是不是 ComfyUI。是就返回 {url, dir, version}，否则 None。"""
    try:
        import urllib.request
        with urllib.request.urlopen(str(url).rstrip("/") + "/system_stats",
                                   timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    if not (isinstance(d, dict) and "system" in d):
        return None
    sysinfo = d.get("system") or {}
    return {
        "url": str(url).rstrip("/"),
        # 顺手问一句「你在哪」——选择器里要显示成
        # `127.0.0.1:8188  G:\...\Anima\ComfyUI`，用户才知道哪个是哪个
        "dir": root_from_folder_paths(folder_paths_of(url, timeout=1.0)),
        "version": str(sysinfo.get("comfyui_version") or ""),
    }


def discover_comfyui(ports=None, timeout=0.4):
    """扫本地常见端口，返回正在跑的 ComfyUI 列表（按端口排序）。"""
    import threading
    ports = list(ports or SCAN_PORTS)
    found, lock = [], threading.Lock()

    def _one(p):
        r = probe_comfyui("http://127.0.0.1:%d" % p, timeout=timeout)
        if r:
            r["port"] = p
            with lock:
                found.append(r)

    ts = [threading.Thread(target=_one, args=(p,), daemon=True) for p in ports]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout + 1.5)      # 单个线程卡死也不拖住整体
    return sorted(found, key=lambda x: x["port"])


__all__ = ["comfyui_dir", "output_dir", "COMFYUI_OUTPUT", "source", "report", "CONFIG_PATH",
           "comfyui_url", "url_source", "publish_url", "DEFAULT_URL", "TOOL_DIR",
           "fallback_missing", "data_dir", "discover_comfyui", "probe_comfyui",
           "folder_paths_of", "root_from_folder_paths"]

if __name__ == "__main__":
    print(report())
    print("  LoRA 目录:", os.path.join(comfyui_dir(), "models", "loras"))
    print("  配置文件  :", CONFIG_PATH, "(存在)" if os.path.isfile(CONFIG_PATH) else "(不存在，用兜底)")