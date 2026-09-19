"""
ComfyUI API 客户端 —— 提交 prompt、轮询结果。
"""
import json
import os
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8188"
POLL_FIRST_DELAY = 3   # 提交后首次查队列延迟（秒）——太慢则空等，太快则早查一次
POLL_INTERVAL = 5      # 未完成时的重复查询间隔（秒）——本地 API 查询很轻，5s 一次无压力


def base_url():
    """ComfyUI 服务地址。

    读环境变量 `COMFYUI_URL`，没有则用默认。**刻意不反向 import 上层工具的配置模块**
    —— 本模块是通用客户端，不该依赖某个具体工具。上层工具启动时会把自己配置里的
    地址发布进环境变量（`paths.publish_url()`），两边就一致了。
    每次调用现取，改配置不用重启。
    """
    return (os.environ.get("COMFYUI_URL") or "").strip().rstrip("/") or DEFAULT_BASE


def _url(endpoint):
    """拼接 ComfyUI API 完整 URL"""
    return base_url() + endpoint


def get(endpoint):
    """GET 请求 ComfyUI API，失败返回 None"""
    try:
        req = urllib.request.Request(_url(endpoint))
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def post(endpoint, data, log_fn=None):
    """POST JSON 到 ComfyUI API，失败时通过 log_fn 输出错误原因"""
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(_url(endpoint), data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        msg = f"[API] POST {endpoint} 失败: {e}"
        if log_fn:
            log_fn(msg)
        else:
            print(msg, flush=True)
        return None


def wait(prompt_id, timeout=600, poll_interval=None, first_delay=None):
    """提交后等待生成完成。先用短延迟让 ComfyUI 开始处理，再按间隔轮询。"""
    if poll_interval is None:
        poll_interval = POLL_INTERVAL
    if first_delay is None:
        first_delay = POLL_FIRST_DELAY
    time.sleep(first_delay)

    start = time.time()
    while time.time() - start < timeout:
        data = get("/queue")
        if data is None:
            time.sleep(5)
            continue

        running = any(
            item[1] == prompt_id for item in data.get("queue_running", [])
        )
        pending = any(
            item[1] == prompt_id for item in data.get("queue_pending", [])
        )

        # 不在运行队列也不在等待队列中 = 已完成
        if not running and not pending:
            time.sleep(2)  # 给 ComfyUI 一点时间写入历史
            history = get(f"/history/{prompt_id}")
            if history and prompt_id in history:
                return history[prompt_id]
            time.sleep(3)
            history = get(f"/history/{prompt_id}")
            if history and prompt_id in history:
                return history[prompt_id]
            return None

        time.sleep(poll_interval)

    return None
