"""
HTTP server for Matrix Viewer — scans task.json, serves images, folder picker.
"""
import http.server
import json
import os
import re
import sys
import threading
import urllib.parse

# tkinter 只在「浏览文件夹」那一处用，而 **ComfyUI 便携版的 python_embeded 不含 tkinter**
# （官方为瘦身去掉了）。硬 import 会让整个 matrix_viewer 起不来 —— 所以设为可选，
# 缺了就把「浏览」按钮降级成「手填路径」。
try:
    import tkinter as tk
    import tkinter.filedialog
    _HAS_TK = True
except ImportError:
    tk = None
    _HAS_TK = False

_HERE = os.path.dirname(os.path.abspath(__file__))

import png_meta_read as _pngmeta
import matrix_generator, paths, task_runner
import config, gen_tab, gui, jobs, loras, queue_tab
import plugin_loader

# ── 插件 ────────────────────────────────────────────────────────────────
# 启动时扫一次 plugins/。**内核不 import 插件里的任何模块** —— 插件目录
# 整个删掉也不影响这里，只是页签少几个、路由少几条。
#
# 未启用的插件（缺依赖 / 导入失败）也会出现在 PLUGINS 里，但 enabled=False、
# 没有路由，BODY 是「未启用」提示 —— 页签照常显示，用户能看懂少了什么。
PLUGINS = plugin_loader.discover()
PLUGIN_ROUTES = plugin_loader.collect_routes(PLUGINS)

# 原来由包 __init__.py 提供，扁平版统一从 paths 拿
COMFYUI_OUTPUT = paths.COMFYUI_OUTPUT

# ── 退出钩子 ────────────────────────────────────────────────────────────
# 打成 exe 后是 `--windowed`（没有控制台窗口），于是**用户没有任何办法关掉它**：
# 浏览器标签一关，进程还在后台占着端口；再双击一次就变成两个实例（端口顺延）。
# 网页上那个「退出」按钮走这里。
#
# 用回调而不是在这里直接退出：本模块不该知道服务是怎么起的（可能在测试里、
# 也可能是别的宿主）。matrix_viewer 启动时把自己那套关停逻辑挂进来。
_shutdown_hook = None


def set_shutdown_hook(fn):
    """由入口（matrix_viewer）注册「怎么关掉自己」。"""
    global _shutdown_hook
    _shutdown_hook = fn


def _refresh_comfyui_paths():
    """切换 ComfyUI 之后，把散落各处的 COMFYUI_OUTPUT **副本**一起更新。

    ⚠️ 为什么必须做：`from paths import COMFYUI_OUTPUT` 拷的是**值**不是引用
    （config.py / task_runner.py / 本模块各存了一份）。不刷新它们的话，
    界面上切了实例、实际落盘还写在老地方的 output 里 —— 一个「点了没反应」
    的假切换。**刷新点就这一处，别在别的地方再判断。**

    返回新的 output 目录（可能为空 = 新实例没自报路径）。
    """
    global COMFYUI_OUTPUT
    new = paths.output_dir()
    paths.COMFYUI_OUTPUT = new
    COMFYUI_OUTPUT = new
    try:
        task_runner.COMFYUI_OUTPUT = new
    except Exception:
        pass
    try:
        config.DEFAULT_FOLDER = (os.path.join(new.replace("/", os.sep), "matrix")
                                 if new else "")
    except Exception:
        pass
    return new


def _log(msg):
    print(f"[matrix_viewer] {msg}", flush=True)


# workflow.json 里用到的非内置节点 —— 缺任何一个都跑不了。
# 清单来自 workflow.json 实际用到的 class_type，改动那个模板时要同步这里。
REQUIRED_NODES = [
    ("Power Lora Loader (rgthree)", "rgthree-comfy"),
    ("Seed (rgthree)", "rgthree-comfy"),
    ("ImpactWildcardProcessor", "ComfyUI-Impact-Pack"),
    ("Save Image (LoraManager)", "comfyui-lora-manager"),
    ("UNet loader with Name (Image Saver)", "comfyui-image-saver"),
]


def check_nodes(timeout=6):
    """问 ComfyUI 的 /object_info 要全部节点定义，对照必需清单。

    比让用户跑到一半才发现「节点不存在」友好得多。
    """
    import urllib.request

    # 顺带把 ComfyUI 路径的解析结果报出去。
    # 为什么必须报：没配 COMFYUI_DIR / config.json 时会退回包内的作者本机常量，
    # 在别人机器上那个目录不存在 → LoRA 列表静默为空、什么提示都没有。
    d = paths.comfyui_dir()
    path_info = {
        "dir": d,
        "source": paths.source(),
        "exists": bool(d) and os.path.isdir(d),
        # 是否靠包内常量兜底 —— 那常量是作者本机的，在别人机器上必然不存在。
        # 给前端一个布尔量，省得它去匹配中文来源串。
        "fallback": paths.source().startswith("包内常量兜底"),
    }

    url = paths.comfyui_url() + "/object_info"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"online": False, "error": "%s: %s" % (type(exc).__name__, exc),
                "missing": [], "path": path_info}
    missing = [{"node": n, "plugin": p} for n, p in REQUIRED_NODES if n not in info]
    return {"online": True, "missing": missing, "checked": len(REQUIRED_NODES),
            "path": path_info}


# 清单列表的短缓存 —— is_combo_done 每条要 batch 次 stat，上千组合就是上千次。
# 这个接口只在打开「任务队列」页签 / 点刷新时调，不进 1 秒轮询；
# 再加几秒缓存，重复请求就不会反复 stat。
_LIST_CACHE = {"t": 0.0, "data": []}
LIST_CACHE_TTL = 5.0


def _bust_list_cache():
    """删清单、跑完一轮之后要让缓存失效，否则用户会看到过期的完成度。"""
    _LIST_CACHE["t"] = 0.0


def _matrix_folders():
    """快速选择用的候选目录：ComfyUI 的 `output/matrix` 根 + 它下面的任务目录。

    为什么不用通用文件夹对话框：**ComfyUI 便携版的 python_embeded 不含 tkinter**，
    弹不出来；而这个工具要看的目录几乎总在 `output/matrix` 底下，工具自己就知道
    那个路径。与其让用户手粘路径，不如把候选直接列出来 —— 点一下即加载，
    而且完全不依赖 tkinter。
    """
    root = (os.path.join(COMFYUI_OUTPUT.replace("/", os.sep), "matrix")
            if COMFYUI_OUTPUT else "")
    out = {"root": root, "exists": bool(root) and os.path.isdir(root), "dirs": [],
           "has_tk": _HAS_TK}
    if not out["exists"]:
        return out
    try:
        names = os.listdir(root)
    except OSError:
        return out
    for name in names:
        p = os.path.join(root, name)
        if not os.path.isdir(p):
            continue
        try:
            mtime = os.path.getmtime(p)
            # 是不是任务目录 —— _resolve_folder 认的就是「含 *.task.json」
            has_tasks = any(f.endswith(".task.json") for f in os.listdir(p))
        except OSError:
            continue
        out["dirs"].append({"path": p, "name": name, "mtime": mtime,
                            "has_tasks": has_tasks})
    # 新的在前（刚跑完的那批通常就是你要看的）
    out["dirs"].sort(key=lambda d: d["mtime"], reverse=True)
    return out


def _delete_tasklist(path_or_name):
    """删一份任务清单。返回 (ok, error)。

    ⚠️ 只认 `json/` 目录下的 .json —— 先取 basename 再拼回 json/，这样
    `../../x.json`、`D:/x.json`、带分隔符的名字全都被 basename 剥掉，
    再校验最终路径确实落在 json/ 里（双保险，照 config._safe_preset_name 的思路）。

    **只删清单本身，不动产物** —— 已生成的图在 ComfyUI 的 output 里，那是另一回事。
    """
    json_dir = os.path.join(_HERE, "json")
    base = os.path.basename(str(path_or_name or "").replace("\\", "/").strip())
    if not base or not base.endswith(".json"):
        return False, "只能删 json/ 下的 .json 清单"
    target = os.path.abspath(os.path.join(json_dir, base))
    if os.path.dirname(target) != os.path.abspath(json_dir):
        return False, "路径不合法"
    if not os.path.isfile(target):
        return False, "清单不存在"
    try:
        os.remove(target)
    except OSError as exc:
        return False, str(exc)
    _bust_list_cache()
    return True, ""


def _list_tasklists(max_age=LIST_CACHE_TTL):
    """列出 json/ 下的任务清单，附**从磁盘推导**的完成度（新的在前）。

    完成度是数出来的，不是记出来的：`task_runner.is_combo_done()` 去看输出目录里
    存不存在 seed 匹配的 PNG。所以**不需要任何状态文件**，也不会出现
    「记录说跑完了、其实产物没了」这种脱节。
    """
    import time
    now = time.time()
    if max_age > 0 and now - _LIST_CACHE["t"] < max_age:
        return _LIST_CACHE["data"]

    d = os.path.join(_HERE, "json")
    out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json") or f.startswith("example"):
                continue
            p = os.path.join(d, f)
            try:
                with open(p, encoding="utf-8") as fh:
                    data = json.load(fh)
                if not isinstance(data, list):
                    continue      # 不是任务清单（比如误放进来的预设），跳过
                mtime = os.path.getmtime(p)
            except (json.JSONDecodeError, OSError):
                continue
            total = len(data)
            try:
                done = sum(1 for t in data if task_runner.is_combo_done(t))
            except Exception:
                done = 0          # 清单格式老旧/缺字段时不至于让整个列表 500
            # 辨认信息：都从 tasks[0] 现成字段里取，不额外解析
            first = data[0] if data else {}
            loras = list((first.get("坐标") or {}).keys())
            scenes = len({t.get("场景") for t in data})
            out.append({
                "file": p, "name": f, "task_name": first.get("任务名") or f,
                "total": total, "done": done, "mtime": mtime,
                "state": ("done" if total and done >= total
                          else "partial" if done else "fresh"),
                "loras": loras, "scenes": scenes, "seed": first.get("seed"),
            })
    out.sort(key=lambda x: x["mtime"], reverse=True)
    _LIST_CACHE.update(t=now, data=out)
    return out


_PICK_LOCK = threading.Lock()


def _pick_folder():
    """tkinter 文件夹选择对话框。

    加锁：server 改用 ThreadingHTTPServer 后，连点两次会并发创建两个 Tk root
    并各自进入 mainloop → 崩溃。

    无 tkinter 时返回空串，前端应提示用户手填路径。
    """
    if not _HAS_TK:
        return ""
    with _PICK_LOCK:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            path = tkinter.filedialog.askdirectory(title="选择矩阵输出目录")
        except Exception:
            return ""
        finally:
            root.destroy()
        return path or ""


def _resolve_folder(folder):
    """把「父目录」解析成真正含 task.json 的任务目录。

    用户可能填 output/matrix（父目录，下面按任务名分子目录），
    这时自动选**最新的**一个任务目录。已经是任务目录则原样返回。
    """
    try:
        entries = os.listdir(folder)
    except OSError:
        return folder
    if any(e.endswith(".task.json") for e in entries):
        return folder
    # 找一层子目录里含 task.json 的，取最新修改的
    subs = []
    for e in entries:
        p = os.path.join(folder, e)
        if not os.path.isdir(p):
            continue
        if any(x.endswith(".task.json") for x in os.listdir(p)):
            subs.append(p)
    if not subs:
        return folder
    return max(subs, key=lambda p: os.path.getmtime(p))


def _scan_tasks(folder):
    """扫描目录下所有 task.json（支持新旧格式），返回 {tasks, dimensions}

    传进来的 folder 应已由 _resolve_folder 解析成任务目录。
    """
    tasks = []
    dims = {}

    # 新格式（扁平）：{combo}.task.json + {combo}_{seed}.png 并列在 folder 下
    # PNG 前缀取 task.json 的**文件名**（权威），不用里面的 组合文件夹 字段——
    # 字段可能是旧的带空格写法，跟实际 PNG 名对不上。
    # 用精确正则匹配，避免 combo 是另一个 combo 的前缀时串图
    # （例：HowanJoe1 会误匹配 HowanJoe1_bantan0.5_42.png）
    all_pngs = [p for p in os.listdir(folder) if p.lower().endswith(".png")]
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".task.json"):
            continue
        combo_key = fname[: -len(".task.json")]     # 文件名去掉后缀 = 安全组合名
        task_path = os.path.join(folder, fname)
        with open(task_path, encoding="utf-8") as f:
            task = json.load(f)
        pat = re.compile(r"^" + re.escape(combo_key) + r"_\d+\.png$", re.IGNORECASE)
        pngs = sorted(p for p in all_pngs if pat.match(p))
        task["_images"] = [
            f"/image?path={urllib.parse.quote(os.path.join(folder, p))}"
            for p in pngs
        ]
        task["_combo_dir"] = combo_key
        task["组合文件夹"] = combo_key     # 统一成安全名，供前端显示
        tasks.append(task)
        _collect_dims(task, dims)

    if tasks:
        return tasks, _sort_dims(dims)

    # 旧格式（嵌套子目录）：combo_dir/task.json 或 combo_dir/sceneN/task.json
    for combo_dir in sorted(os.listdir(folder)):
        combo_path = os.path.join(folder, combo_dir)
        if not os.path.isdir(combo_path):
            continue

        task_json = os.path.join(combo_path, "task.json")
        if os.path.isfile(task_json):
            scene_path = combo_path
        else:
            for scene_dir in sorted(os.listdir(combo_path)):
                scene_path = os.path.join(combo_path, scene_dir)
                task_json = os.path.join(scene_path, "task.json")
                if os.path.isfile(task_json):
                    break
            else:
                continue

        with open(task_json, encoding="utf-8") as f:
            task = json.load(f)

        pngs = sorted(
            p for p in os.listdir(scene_path)
            if p.lower().endswith(".png")
        )
        task["_images"] = [
            f"/image?path={urllib.parse.quote(os.path.join(scene_path, p))}"
            for p in pngs
        ]
        task["_combo_dir"] = combo_dir
        tasks.append(task)
        _collect_dims(task, dims)

    return tasks, _sort_dims(dims)


def _collect_dims(task, dims):
    coords = task.get("坐标", {})
    for lora_name, val in coords.items():
        if lora_name not in dims:
            dims[lora_name] = set()
        dims[lora_name].add(val)


def _sort_dims(dims):
    for name in dims:
        dims[name] = sorted(dims[name])
    return dims

    return tasks, dims


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    # ── 给插件的后端接口 ──────────────────────────────────────────────────
    # 插件不该 `import server`（循环导入：server → plugin_loader → 插件），
    # 也不该自己重写一套目录扫描。这两个是模块级函数的直通，
    # 让插件的路由 handler 能直接拿到任务清单 —— 见 plugins/analysis/__init__.py。
    resolve_folder = staticmethod(_resolve_folder)
    scan_tasks = staticmethod(_scan_tasks)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        _log(f"GET {path}")

        # 插件路由优先查表。插件被卸载 / 未启用时这里自然查不到，
        # 请求会落到下面的 else —— 也就是「这个接口没了」。
        _plugin_fn = PLUGIN_ROUTES.get(path)
        if _plugin_fn is not None:
            try:
                _plugin_fn(self, params)
            except Exception as exc:
                _log(f"plugin route {path} 出错: {type(exc).__name__}: {exc}")
                self._json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})
            return

        if path == "/api/tasks":
            self._handle_tasks(params)
        elif path == "/image":
            self._serve_file(params)
        elif path == "/api/pick-folder":
            self._json({"path": _pick_folder(), "has_tk": _HAS_TK})
        elif path == "/api/matrix-folders":
            self._json(_matrix_folders())
        elif path == "/api/config":
            self._json(config.load())
        elif path == "/api/metadata":
            self._handle_metadata(params)
        elif path == "/api/loras":
            items, src = loras.list_loras()
            self._json({"ok": True, "root": loras.LORAS_ROOT,
                        "files": items, "source": src})
        elif path == "/api/lora-preview":
            self._serve_preview(params)
        elif path == "/api/models":
            # 底模 / CLIP / VAE 三组都给 —— 界面上是三个独立下拉，不预设任何模型。
            # 清单优先向运行中的 ComfyUI 要（见 loras.list_*），离线才退回扫盘；
            # source 一并回给前端，好让用户知道这份清单是哪来的。
            models, ms = loras.list_models()
            clips, cs = loras.list_clips()
            vaes, vs = loras.list_vaes()
            srcs = (ms, cs, vs)
            source = ("comfyui" if all(s == "comfyui" for s in srcs)
                      else "disk" if "disk" in srcs else "none")
            self._json({"ok": True, "files": models, "clips": clips, "vaes": vaes,
                        "source": source,
                        # 用 loras 那份**带缓存**的在线判定（同一个 /system_stats）。
                        # 上面 list_* 刚探过、缓存已填，这里读缓存 = 不再付探测代价
                        "comfyui_online": loras.comfyui_ready()})
        elif path == "/api/check-nodes":
            self._json({"ok": True, **check_nodes()})
        elif path == "/api/tasklists":
            self._json({"ok": True, "files": _list_tasklists()})
        elif path == "/api/run/status":
            self._json({"ok": True, **jobs.status()})
        elif path == "/api/presets":
            self._json({"ok": True, "files": config.list_presets()})
        elif path == "/api/presets/load":
            self._json(config.load_preset(params.get("name", [""])[0]))
        elif path == "/api/comfyui":
            self._handle_comfyui(params)
        elif path == "/api/example-config":
            self._handle_example_config()
        else:
            # 未命中的 /api/* 返回 404，而不是把首页 HTML 塞回去 ——
            # 插件卸载后前端调 /api/similarity 能立刻看出「这个接口没了」，
            # 而不是拿到一坨 HTML 去 JSON.parse（报错信息会难看懂得多）。
            if path.startswith("/api/"):
                self._json({"ok": False, "error": "no such endpoint: " + path}, 404)
            else:
                self._serve_html()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        _log(f"POST {path}")

        if path == "/api/quit":
            self._handle_quit(data)
        elif path == "/api/comfyui":
            self._handle_comfyui_switch(data)
        elif path == "/api/save-config":
            config.save(data)
            self._json({"ok": True})
        elif path == "/api/generate-preview":
            self._handle_generate(data, write=False)
        elif path == "/api/generate-tasks":
            self._handle_generate(data, write=True)
        elif path == "/api/run":
            self._handle_run(data)
        elif path == "/api/run/stop":
            self._json({"ok": jobs.request_stop()})
        elif path == "/api/tasklists/delete":
            ok, err = _delete_tasklist(data.get("file") or data.get("name") or "")
            self._json({"ok": ok, "error": err})
        elif path == "/api/presets/save":
            ok, err = config.save_preset(data.get("name", ""), data.get("config") or {})
            self._json({"ok": ok, "error": err})
        elif path == "/api/presets/delete":
            self._json({"ok": config.delete_preset(data.get("name", ""))})
        else:
            self._json({"error": "not found"})

    def _handle_quit(self, data):
        """网页上的「退出」按钮 —— 关掉工具本身。

        ⚠️ **必须先回响应再关停**：`shutdown()` 会让 `serve_forever()` 返回、
        进程随即退出；如果先关停，这个响应还没写出去连接就断了，浏览器会显示
        「连接被重置」，用户以为点坏了。

        关停放在**另一个线程**里：本函数就跑在 server 的线程池里，
        在它自己身上调 shutdown() 会死等（shutdown 等的是「所有 handler 返回」）。
        """
        import threading
        if _shutdown_hook is None:
            self._json({"ok": False, "error": "当前不是由 matrix_viewer 启动的，没有退出钩子"})
            return
        self._json({"ok": True})
        threading.Thread(target=_shutdown_hook, daemon=True).start()

    def _handle_comfyui(self, params):
        """当前连的 ComfyUI + 扫到的全部实例。

        多便携版并存时，「连的是哪一台」必须让用户看得见、能换 ——
        否则他只会看到「LoRA 列表怎么不对」而不知道连错了实例。
        """
        cur = paths.comfyui_url()
        found = paths.discover_comfyui(timeout=0.25)
        # 把「当前这台」补进列表（万一它不在扫描范围内，比如手动填了别的端口）
        if not any(f["url"] == cur for f in found):
            p = paths.probe_comfyui(cur, timeout=0.6)
            if p:
                found = [p] + found
        self._json({
            "ok": True,
            "current": cur,
            "source": paths.url_source(),
            "dir": paths.comfyui_dir(),
            # 环境变量在的话，界面上的切换是不生效的（优先级比 config 高）
            "locked_by_env": bool(os.environ.get("COMFYUI_URL")),
            "instances": found,
        })

    def _handle_comfyui_switch(self, data):
        """切换要连的 ComfyUI。写 config.json + 刷新全进程的路径副本。"""
        url = str(data.get("url") or "").strip()
        ok, msg = paths.set_comfyui_url(url)
        if not ok:
            self._json({"ok": False, "error": msg})
            return
        new_out = _refresh_comfyui_paths()
        paths.publish_url()          # comfy_api 读的是环境变量，也要跟着走
        self._json({
            "ok": True,
            "current": paths.comfyui_url(),
            "dir": paths.comfyui_dir(),
            "output": new_out,
            "warn": "" if new_out else "这台没自报路径，输出目录暂时未知",
        })

    def _handle_example_config(self):
        """返回 example_config.json，供生成页签当默认模板。"""
        p = os.path.join(_HERE, "example_config.json")
        try:
            with open(p, encoding="utf-8") as f:
                self._json({"ok": True, "config": json.load(f)})
        except (json.JSONDecodeError, OSError) as exc:
            self._json({"ok": False, "error": str(exc)})

    def _serve_html(self):
        # 外壳（gui.HTML，持有唯一的 <style>）+ 各页签片段。
        #
        # 两类页签：
        #   · 内核自带的 gen_tab / queue_tab —— 硬编码在这里的 4 行 replace
        #   · 插件页签 —— 由 plugin_loader 汇总后填进 @PLUGIN_*@ 四个占位符，
        #     加/删插件不需要动这个函数
        html = (gui.HTML
                .replace("@GEN_CSS@", gen_tab.CSS)
                .replace("@GEN_BODY@", gen_tab.BODY)
                .replace("@QUEUE_CSS@", queue_tab.CSS)
                .replace("@QUEUE_BODY@", queue_tab.BODY)
                .replace("@PLUGIN_CSS@", plugin_loader.tab_css(PLUGINS))
                .replace("@PLUGIN_TABS@", plugin_loader.tab_buttons(PLUGINS))
                .replace("@PLUGIN_BODY@", plugin_loader.tab_containers(PLUGINS))
                .replace("@PLUGIN_JS@", plugin_loader.tab_js(PLUGINS))
                # 页签元数据给前端 —— MLX.tabs 要先塞进插件页签，switchTab 才认它们。
                # ⚠️ 这段 JSON 进的是 <script> 内部，label 来自 plugin.json（半受信）：
                #    json.dumps 挡得住引号，挡不住 `</script>` 提前闭合脚本标签。
                #    把 `</` 转成 `<\/`（JSON 里等价、HTML 里不再是闭合标签）。
                .replace("@PLUGIN_TABMETA@",
                         json.dumps(plugin_loader.tab_meta(PLUGINS),
                                    ensure_ascii=False).replace("</", "<\\/")))
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        # 不缓存 HTML：改了 gui.py / gen_tab.py 后刷新即可生效，不必硬刷新
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_tasks(self, params):
        folder = params.get("folder", [""])[0]
        if not folder or not os.path.isdir(folder):
            self._json({"tasks": [], "dimensions": {}, "error": "invalid folder"})
            return
        resolved = _resolve_folder(folder)        # 父目录 → 最新任务目录
        tasks, dims = _scan_tasks(resolved)
        self._json({"tasks": tasks, "dimensions": dims, "folder": resolved})

    def _handle_metadata(self, params):
        path = params.get("path", [""])[0]
        if not path or not os.path.isfile(path):
            self._json({"error": "not found"})
            return
        meta = {"file": path}
        if path.lower().endswith(".png"):
            try:
                png = _pngmeta.read(path)
                meta["png"] = png
            except Exception:
                pass
        self._json(meta)

    def _serve_preview(self, params):
        """LoRA 的 sidecar 预览图。

        只接受纯文件名，经 loras.find_lora_preview 查表解析 ——
        绝不拼接用户传入的路径（防目录穿越）。
        """
        p = loras.find_lora_preview(params.get("name", [""])[0])
        if not p:
            self.send_response(404)
            self.end_headers()
            return
        self._send_image(p)

    def _handle_generate(self, data, write):
        """试算（write=False）或落盘（write=True）任务清单。

        维度统计直接取自 generate_tasks() 的结果 —— 不在前端复刻
        _parse_strength：浮点等分 round(mn+i*step,4) 与 JS 有差异，
        会让「预计 N 张」和实际不符，而这个数字用户是拿来决策的。
        """
        cfg = data.get("config") or {}
        try:
            tasks, name = matrix_generator.generate_tasks(cfg)
        except Exception as exc:
            self._json({"ok": False, "error": "配置有误: %s" % exc})
            return

        dims = {}
        for t in tasks:
            for k, v in (t.get("坐标") or {}).items():
                dims.setdefault(k, set()).add(v)
        axes = {k: sorted(v) for k, v in dims.items() if len(v) > 1}
        fixed = sorted(k for k, v in dims.items() if len(v) <= 1)

        resp = {
            "ok": True,
            "name": name,
            "total": len(tasks),
            "combos": len(set(t["组合标识"] for t in tasks)),
            "scenes": len(cfg.get("场景") or [""]),
            "batch": int(cfg.get("batch", 1) or 1),
            "axes": axes,
            "fixed_dims": fixed,
            "warn": ("组合数 %d，可能耗时很久" % len(tasks)) if len(tasks) > 2000 else "",
        }
        # 组合清单（供前端勾选 / 标已完成）—— key 必须带场景序号，见 jobs.task_key
        combo_map = {}
        for t in tasks:
            k = jobs.task_key(t)
            if k in combo_map:
                continue
            combo_map[k] = {
                "key": k,
                "combo": t.get("组合文件夹", "?"),
                "scene": t.get("场景序号", 0),
                "loras": [l.get("name") for l in (t.get("loras") or [])],
                "coords": t.get("坐标") or {},      # 供弹窗按维度值批量筛选
                "done": task_runner.is_combo_done(t),
            }
        resp["combo_list"] = list(combo_map.values())

        if write:
            try:
                out_path, tasks2 = matrix_generator.write_tasks(cfg)
            except Exception as exc:
                self._json({"ok": False, "error": "落盘失败: %s" % exc})
                return
            resp["path"] = out_path
            resp["total"] = len(tasks2)
        self._json(resp)

    def _handle_run(self, data):
        """启动后台生图。

        body {"config": {...}}   —— 先落盘再跑（生成并执行）
        body {"file": "..."}     —— 直接跑已有清单（单份）
        body {"files": [...]}    —— 跑多份，按给定顺序（「任务队列」页签用）
        """
        if not jobs.comfyui_online():
            self._json({"ok": False,
                        "error": "ComfyUI 没在运行（%s 无响应），先启动它"
                                 % paths.comfyui_url()})
            return

        only = data.get("only")
        only_set = set(only) if only else None      # None = 全跑
        skip_done = data.get("skip_done", True)     # 默认跳过已完成的（断点续跑）

        cfg = data.get("config")
        if cfg:
            try:
                out_path, tasks = matrix_generator.write_tasks(cfg)
            except Exception as exc:
                self._json({"ok": False, "error": "生成失败: %s" % exc})
                return
            task_name = str(cfg.get("任务名") or "matrix")
            out_dir = os.path.join(COMFYUI_OUTPUT.replace("/", os.sep), "matrix",
                                   task_runner._make_safe(task_name, maxlen=50) or "matrix")
            total = len(tasks)
            paths = [out_path]
        else:
            # 多份（任务队列页签）与单份走同一条路 —— jobs.start 本来就吃列表
            raw = data.get("files")
            if raw is None:
                raw = [data.get("file") or ""]
            wanted = [str(f) for f in raw if str(f).strip()]
            paths = [f for f in wanted if os.path.isfile(f)]
            if not paths:
                self._json({"ok": False, "error": "没有可跑的任务清单（文件不存在？）"})
                return
            if len(paths) != len(wanted):
                self._json({"ok": False,
                            "error": "%d 份清单里有 %d 份找不到" % (len(wanted),
                                                                  len(wanted) - len(paths))})
                return
            out_dir, total = "", 0

        ok, err = jobs.start(paths, out_dir=out_dir,
                             skip_done=skip_done, only=only_set)
        if not ok:
            self._json({"ok": False, "error": err})
            return
        _bust_list_cache()          # 跑起来的清单完成度会变，别让列表显示旧值
        self._json({"ok": True, "total": total, "out_dir": out_dir, "file": paths[0],
                    "files": paths,
                    "only_count": len(only_set) if only_set else 0,
                    "skip_done": bool(skip_done)})

    def _serve_file(self, params):
        self._send_image(params.get("path", [""])[0])

    def _send_image(self, path):
        if not path or not os.path.isfile(path):
            self.send_response(404)
            self.end_headers()
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = {
            ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".webp": "image/webp",
        }.get(ext, "application/octet-stream")
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self.send_response(404)
            self.end_headers()

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # 不缓存：否则浏览器会留住旧的 API 响应（例如端点还不存在时的 404），
        # 表现为「重启了 server 但页面拿到的还是旧数据」
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)