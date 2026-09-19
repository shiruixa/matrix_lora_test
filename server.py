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
import config, gen_tab, gui, jobs, loras

# 原来由包 __init__.py 提供，扁平版统一从 paths 拿
COMFYUI_OUTPUT = paths.COMFYUI_OUTPUT


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

    url = "http://127.0.0.1:8188/object_info"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"online": False, "error": "%s: %s" % (type(exc).__name__, exc),
                "missing": [], "path": path_info}
    missing = [{"node": n, "plugin": p} for n, p in REQUIRED_NODES if n not in info]
    return {"online": True, "missing": missing, "checked": len(REQUIRED_NODES),
            "path": path_info}


def _list_tasklists():
    """列出 json/ 下的任务清单，供 UI 选择要跑哪一份（新的在前）。"""
    d = os.path.join(_HERE, "json")
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json") or f.startswith("example"):
            continue
        p = os.path.join(d, f)
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                continue          # 不是任务清单（比如误放进来的预设），跳过
            mtime = os.path.getmtime(p)
        except (json.JSONDecodeError, OSError):
            continue
        out.append({"file": p, "name": f, "total": len(data), "mtime": mtime})
    out.sort(key=lambda x: x["mtime"], reverse=True)
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

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        _log(f"GET {path}")

        if path == "/api/tasks":
            self._handle_tasks(params)
        elif path == "/image":
            self._serve_file(params)
        elif path == "/api/pick-folder":
            self._json({"path": _pick_folder(), "has_tk": _HAS_TK})
        elif path == "/api/config":
            self._json(config.load())
        elif path == "/api/metadata":
            self._handle_metadata(params)
        elif path == "/api/loras":
            self._json({"ok": True, "root": loras.LORAS_ROOT,
                        "files": loras.scan_loras()})
        elif path == "/api/lora-preview":
            self._serve_preview(params)
        elif path == "/api/models":
            # 底模 / CLIP / VAE 三组都给 —— 界面上是三个独立下拉，不预设任何模型
            self._json({"ok": True, "files": loras.scan_models(),
                        "clips": loras.scan_clips(), "vaes": loras.scan_vaes(),
                        "comfyui_online": jobs.comfyui_online()})
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
        elif path == "/api/example-config":
            self._handle_example_config()
        elif path == "/api/similarity":
            self._handle_similarity(params)
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

        if path == "/api/save-config":
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
        elif path == "/api/presets/save":
            ok, err = config.save_preset(data.get("name", ""), data.get("config") or {})
            self._json({"ok": ok, "error": err})
        elif path == "/api/presets/delete":
            self._json({"ok": config.delete_preset(data.get("name", ""))})
        else:
            self._json({"error": "not found"})

    def _handle_similarity(self, params):
        """图片视觉相似度散点数据（颜色/纹理特征 → PCA 2D）。

        每次请求现算 —— 百来张图不到一秒，不值得加缓存（还会带来失效问题）。
        """
        folder = params.get("folder", [""])[0]
        if not folder or not os.path.isdir(folder):
            self._json({"ok": False, "error": "invalid folder"})
            return
        resolved = _resolve_folder(folder)
        tasks, _dims = _scan_tasks(resolved)
        try:
            import similarity
            r = similarity.similarity_map(tasks)
        except Exception as exc:
            self._json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})
            return
        self._json({"ok": True, **r})

    def _handle_example_config(self):
        """返回 example_config.json，供生成页签当默认模板。"""
        p = os.path.join(_HERE, "example_config.json")
        try:
            with open(p, encoding="utf-8") as f:
                self._json({"ok": True, "config": json.load(f)})
        except (json.JSONDecodeError, OSError) as exc:
            self._json({"ok": False, "error": str(exc)})

    def _serve_html(self):
        # 外壳（gui.HTML，持有唯一的 <style>）+ 生成页签片段
        html = (gui.HTML
                .replace("@GEN_CSS@", gen_tab.CSS)
                .replace("@GEN_BODY@", gen_tab.BODY))
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

        body {"config": {...}} —— 先落盘再跑（生成并执行）
        body {"file": "..."}   —— 直接跑已有清单
        """
        if not jobs.comfyui_online():
            self._json({"ok": False,
                        "error": "ComfyUI 没在运行（127.0.0.1:8188 无响应），先启动它"})
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
            f = str(data.get("file") or "")
            if not f or not os.path.isfile(f):
                self._json({"ok": False, "error": "任务清单不存在"})
                return
            paths, out_dir, total = [f], "", 0

        ok, err = jobs.start(paths, out_dir=out_dir,
                             skip_done=skip_done, only=only_set)
        if not ok:
            self._json({"ok": False, "error": err})
            return
        self._json({"ok": True, "total": total, "out_dir": out_dir, "file": paths[0],
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

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # 不缓存：否则浏览器会留住旧的 API 响应（例如端点还不存在时的 404），
        # 表现为「重启了 server 但页面拿到的还是旧数据」
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)