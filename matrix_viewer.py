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

# ⚠️ 日志必须在 **import server 之前**接好。
#    打成 exe（--noconsole）后 `sys.stdout` 是 None，而 `import server` 时
#    插件加载器就会 print（`[plugin] xxx 已启用`）—— 那一下直接 AttributeError，
#    整个程序启动不了。而且无控制台时这些诊断信息本来也无处可看。
#    放在这里而不是 main() 里，就是因为 import 阶段就在打日志。
import paths as _paths


def _safe_console():
    """让 print 永远不会因为字符编不出来而崩。

    ⚠️ 踩过：往启动提示里放了个 `⏻`（U+23FB），GBK 控制台直接
    `UnicodeEncodeError` —— **整个程序起不来**，而且报错指向一句无关紧要的提示语。
    这类字符（emoji、特殊符号）在 Windows 控制台上随时会炸，
    统一降级成 `?` 比每次记得「别用这些字符」可靠。

    （冻结成 exe 时走的是文件重定向，UTF-8 没问题；这条是给源码用户的。）
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _setup_logging():
    """冻结运行时把 stdout/stderr 接到 exe 旁边的日志文件。

    顺带解决两件事：① 无控制台时 print 有地方去；② 用户遇到「双击没反应」
    时有个文件可以翻（也让别人能远程帮他看）。
    """
    if not getattr(sys, "frozen", False):
        return None
    try:
        log = os.path.join(_paths.data_dir(), "启动日志.txt")
        f = open(log, "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = f
        return log
    except OSError:
        return None


_safe_console()
_LOG_FILE = _setup_logging()

import config          # noqa: E402
import server          # noqa: E402

HOST = "127.0.0.1"
PORT = 18890


def pick_port(host, preferred=PORT, span=20):
    """从 preferred 起找一个**真能独占**的端口。返回 0 = 全占，交给 OS 随便给。

    为什么要探测：18890 被占（不小心开了两个查看器）时，以前是直接抛
    `OSError: [WinError 10048]` 起不来，用户只看到一个没有解释的报错。

    ⚠️ 探测时**不能**设 SO_REUSEADDR —— Windows 上它允许**抢占**已被绑定的
    端口，探到「成功」但实际会和旧进程双绑，请求被随机分发，表现为
    「改了代码有时生效有时不生效」（这个坑本项目踩过，见 memory）。
    探测必须严格，才能真的发现冲突。
    """
    import socket
    for p in range(preferred, preferred + span):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return 0


def _startup_report():
    """启动自检 —— 路径不对是最高频的「跑不起来」原因，先打出来。"""
    try:
        import paths as _paths
        # 先打诊断再发布地址 —— 反过来的话 report() 会把「默认值」误报成
        # 「环境变量 COMFYUI_URL」（发布动作自己设了这个变量）
        print(f"[matrix_viewer] {_paths.report()}")
        # 再把自己配置里的地址发布到环境变量，好让 comfy_api（提交 prompt 用）
        # 跟查看器连同一个实例 —— 它在另一个包里，刻意不反向 import 这里
        _paths.publish_url()
        if not _paths.comfyui_dir():
            # source() 已经区分了「没配」和「配了但盘不在」—— 直接用它，别再写一遍
            print("[matrix_viewer] ⚠ %s" % _paths.source())
        # 顺便报一下扫到几个 ComfyUI 实例（多便携版并存时用户要心里有数）
        try:
            found = _paths.discover_comfyui(timeout=0.3)
            if len(found) > 1:
                print("[matrix_viewer] 发现 %d 个 ComfyUI 在跑，可在页面工具栏切换："
                      % len(found))
                for f in found:
                    print("    %-22s %s" % (f["url"], f["dir"] or "(未自报路径)"))
        except Exception:
            pass
    except Exception as _e:
        print(f"[matrix_viewer] 路径自检跳过: {_e}")


def main():
    _startup_report()

    port = pick_port(HOST)
    if port == 0:
        print("[matrix_viewer] ⚠ %d-%d 全被占了，改用系统分配的端口"
              % (PORT, PORT + 19))
    # ThreadingHTTPServer：后台跑生图时仍能响应前端的进度轮询。
    # daemon_threads 必须在**构造前**赋值 —— 它在 TCPServer.__init__ ->
    # server_bind() 阶段就被消费掉了，之后赋值无效。
    #
    # ⚠️ **必须显式设成 False** —— CPython 的 `http.server.HTTPServer` 自己
    # 把这个值默认为 **1**（源码注释："Seems to make sense in testing
    # environment"）。所以「不设」等于开着，原代码那句 `= True` 其实是空操作。
    #
    # 为什么必须关：Windows 上 SO_REUSEADDR 允许**抢占**已被绑定的端口
    # （与 Unix 语义不同，不是只复用 TIME_WAIT）。一旦双绑，两个查看器同时
    # 监听同一端口、请求被随机分发，表现为「改了代码有时生效有时不生效」——
    # 本项目踩过这个坑且复发过（见 memory：两个 PID 同时 LISTENING）。
    # 而且它会让上面的 pick_port 完全失效：探到占用也没用，真 bind 时照样成功。
    http.server.ThreadingHTTPServer.allow_reuse_address = False
    http.server.ThreadingHTTPServer.daemon_threads = True
    srv = http.server.ThreadingHTTPServer((HOST, port), server.Handler)

    # 网页上那个「退出」按钮走这里。
    # exe 是 --windowed（没有控制台窗口），不给这条路的话**用户没有任何办法关掉工具** ——
    # 浏览器标签一关，进程还在后台占着端口；再双击一次就变成两个实例。
    # serve_forever() 一返回，main() 就结束，进程随之退出。
    server.set_shutdown_hook(srv.shutdown)

    actual = srv.server_address[1]          # port=0 时由 OS 决定，以实际为准
    print(f"[matrix_viewer] http://{HOST}:{actual}")
    if actual != PORT:
        print(f"[matrix_viewer] （{PORT} 被占用，已自动改用 {actual}）")
    if _LOG_FILE:
        print(f"[matrix_viewer] 日志: {_LOG_FILE}（关掉本工具：网页右上角「退出」按钮）")
    else:
        print("[matrix_viewer] 关掉本工具：Ctrl+C，或网页右上角「退出」按钮")
    webbrowser.open(f"http://{HOST}:{actual}")   # bind 之后才开：端口占用时不再弹无效页面
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[matrix_viewer] 退出")
    finally:
        srv.server_close()
        print("[matrix_viewer] 已停止，窗口可以关了")


if __name__ == "__main__":
    main()