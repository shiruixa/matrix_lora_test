"""
矩阵查看器 — LoRA 强度组合网格浏览
===================================
扫描 output/matrix/ 下的 task.json，以 N 维网格展示不同 LoRA 强度组合的效果。

用法：
    python matrix_viewer.py

端口：18890
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
import http.server
import os
import sys
import webbrowser

import config
import server

HOST = "127.0.0.1"
PORT = 18890


def main():
    print(f"[matrix_viewer] http://{HOST}:{PORT}")
    # 路径解析结果打在启动日志里 —— 路径不对是最高频的「跑不起来」原因
    try:
        import paths as _paths
        # 先打诊断再发布地址 —— 反过来的话 report() 会把「默认值」误报成
        # 「环境变量 COMFYUI_URL」（发布动作自己设了这个变量）
        print(f"[matrix_viewer] {_paths.report()}")
        # 再把自己配置里的地址发布到环境变量，好让 comfy_api（提交 prompt 用）
        # 跟查看器连同一个实例 —— 它在另一个包里，刻意不反向 import 这里
        _paths.publish_url()
        if not _paths.comfyui_dir():
            print("[matrix_viewer] ⚠ 没解析到 ComfyUI 目录，请设环境变量 COMFYUI_DIR "
                  "或 config.json")
    except Exception as _e:
        print(f"[matrix_viewer] 路径自检跳过: {_e}")
    # ThreadingHTTPServer：后台跑生图时仍能响应前端的进度轮询。
    # allow_reuse_address / daemon_threads 必须在**构造前**赋值 —— 它们在
    # TCPServer.__init__ -> server_bind() 阶段就被消费掉了，之后赋值无效。
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    http.server.ThreadingHTTPServer.daemon_threads = True
    srv = http.server.ThreadingHTTPServer((HOST, PORT), server.Handler)
    webbrowser.open(f"http://{HOST}:{PORT}")   # 移到 bind 之后：端口占用时不再弹无效页面
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[matrix_viewer] 退出")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()