# -*- coding: utf-8 -*-
"""后台执行任务清单 —— 单独线程 + 全局进度状态，供前端轮询。

刻意复用 task_runner._run_task()（不复制它的逻辑），让 CLI 与 UI
走同一条代码路径，行为不会漂移。
"""
import json
import os
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))

import paths, task_runner  # noqa: E402

_LOCK = threading.Lock()
_JOB = {"state": "idle"}
LOG_MAX = 200

# ComfyUI 地址不写死 —— 统一由 paths.comfyui_url() 解析
# （环境变量 COMFYUI_URL → config.json 的 comfyui_url → 默认 127.0.0.1:8188）。
# 每次调用现取，这样用户在 config.json 里改了地址不用重启查看器。


def _load_tasks(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("顶层不是 list，这不是任务清单")
    return data


def task_key(task):
    """勾选用的唯一键。

    `组合文件夹` 不含场景序号 —— 配置里「场景」写多行时，同一组合会产出多个
    task 且该字段逐字相同，必须带上 `场景序号` 才唯一。
    """
    return "%s#%s" % (task.get("组合文件夹", task.get("组合标识", "?")),
                      task.get("场景序号", 0))


def _log(line):
    with _LOCK:
        _JOB["log"] = (_JOB.get("log", []) + [line])[-LOG_MAX:]


def _worker(paths, skip_done=False, only=None):
    try:
        for fi, jp in enumerate(paths, 1):
            tasks = _load_tasks(jp)
            with _LOCK:
                _JOB["total"] = len(tasks)
                _JOB["file"] = os.path.basename(jp)
                _JOB["file_index"] = fi            # 第几份（多份队列时才看得出）
            for idx, task in enumerate(tasks, 1):
                combo = task.get("组合文件夹", task.get("组合标识", "?"))
                with _LOCK:
                    if _JOB.get("stop"):          # 唯一的协作式中断检查点
                        _JOB["state"] = "stopped"
                        return
                    _JOB["index"] = idx
                    _JOB["combo"] = combo

                if only is not None and task_key(task) not in only:
                    continue                      # 没勾选，跳过
                if skip_done and task_runner.is_combo_done(task):
                    with _LOCK:
                        _JOB["skipped"] = _JOB.get("skipped", 0) + 1
                        _JOB["grand_done"] = _JOB.get("grand_done", 0) + 1
                    _log("[%d/%d] %s ⏭ 已完成，跳过" % (idx, len(tasks), combo))
                    continue

                try:
                    ok = task_runner._run_task(task)   # ← 零改动复用
                    err = ""
                except Exception as exc:
                    # 异常隔离：单条坏 task（缺键 / 路径超长）不该让整个 job 终止，
                    # 但也不能静默吞掉 —— 打出类型和消息，用户才知道哪条坏了
                    ok, err = 0, "%s: %s" % (type(exc).__name__, exc)
                with _LOCK:
                    _JOB["ok_images"] = _JOB.get("ok_images", 0) + ok
                    _JOB["grand_done"] = _JOB.get("grand_done", 0) + 1
                    if not ok:
                        _JOB["fail"] = _JOB.get("fail", 0) + 1
                _log("[%d/%d] %s 异常: %s" % (idx, len(tasks), combo, err) if err
                     else "[%d/%d] %s -> %d 张" % (idx, len(tasks), combo, ok))
        with _LOCK:
            _JOB["state"] = "done"
    except Exception as exc:                          # 后台线程的异常必须落到状态里
        with _LOCK:
            _JOB["state"] = "error"
            _JOB["error"] = str(exc)


def start(paths, out_dir="", skip_done=True, only=None):
    """启动后台执行。返回 (ok: bool, error: str)。

    paths     —— 一份或多份任务清单，**按给定顺序**依次跑
    skip_done —— 跳过磁盘上已跑完的组合（断点续跑，默认开）
    only      —— 只跑这些组合（键由 task_key() 生成）；None = 全跑
    """
    paths = list(paths)
    # 队列级进度：每份多少组合，先数好 —— 清单不大，读一遍 len 而已。
    # 主进度条用 grand_done/grand_total，多份时才看得出「整体还剩多少」；
    # index/total 仍表示**当前这一份**内的进度，两者互补。
    queue, grand = [], 0
    for jp in paths:
        try:
            n = len(_load_tasks(jp))
        except Exception:
            n = 0
        queue.append({"name": os.path.basename(jp), "total": n})
        grand += n

    with _LOCK:
        if _JOB.get("state") == "running":
            return False, "已有任务在运行"
        _JOB.clear()
        _JOB.update(state="running", stop=False, index=0, total=0, combo="",
                    ok_images=0, fail=0, skipped=0, log=[], started=time.time(),
                    out_dir=out_dir, error="", file="",
                    queue=queue, file_index=0, file_total=len(paths),
                    grand_done=0, grand_total=grand,
                    skip_done=bool(skip_done), only_count=(len(only) if only else 0))
    threading.Thread(target=_worker,
                     args=(paths, bool(skip_done), only),
                     daemon=True).start()
    return True, ""


def status():
    """返回状态快照（拷贝，避免调用方持有内部字典）。"""
    with _LOCK:
        snap = dict(_JOB)
        snap["log"] = list(_JOB.get("log", []))
    started = snap.get("started")
    snap["elapsed"] = round(time.time() - started, 1) if started else 0.0
    return snap


def request_stop():
    """协作式停止：跑完当前组合后退出（无法中断正在等待的 ComfyUI 出图）。"""
    with _LOCK:
        if _JOB.get("state") != "running":
            return False
        _JOB["stop"] = True
    return True


def comfyui_online(timeout=2):
    """检测 ComfyUI 是否在线，供 UI 在执行前提示。"""
    import urllib.request
    try:
        with urllib.request.urlopen(paths.comfyui_url() + "/system_stats",
                                    timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False
