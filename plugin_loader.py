# -*- coding: utf-8 -*-
"""插件加载器 —— 扫描 plugins/，把插件挂到内核上。

## 一个插件长什么样

    plugins/<id>/
        plugin.json      清单：id / name / tab / requires
        __init__.py      契约：BODY / CSS / JS / routes()

`plugin.json` 是**唯一必需的**。`__init__.py` 里那几个名字都可选
（只想要一个纯后端路由的插件，不写 BODY 也行）。

## 契约

| 名字 | 类型 | 用途 |
|---|---|---|
| `BODY` | str | 页签 HTML 片段，注入外壳的 `@PLUGIN_BODY@` |
| `CSS`  | str | 该页签样式，注入 `@PLUGIN_CSS@` |
| `JS`   | str | 该页签脚本，注入 `@PLUGIN_JS@` |
| `routes()` | callable | 返回 `{路径: handler}`；handler 签名 `(handler_instance, params)` |

JS 跑在 IIFE 里，**只能通过 `window.MLX` 与内核通信**（见 gui.py 的 MLX 定义）。
这样插件不会去抓内核的内部标识符 —— 那些名字内核随时可以改。

## 依赖缺失

`requires` 里任何一个 import 不进来 → 整个插件不启用：
- 控制台打一行警告（含 pip 安装提示）
- **页签照常出现**，内容换成「未启用」提示 —— 用户能看懂少了什么，
  而不是发现页签凭空消失、去猜为什么
- 路由不注册（访问返回 404）

## 卸载

删掉 `plugins/<id>/` 目录即可。内核**不 import** 插件里的任何模块，
所以不会有残留 import 炸掉。`plugins/` 整个目录不在也没关系。
"""
import html as _html       # 清单字段要拼进 HTML，必须转义
import importlib
import importlib.util      # 显式导入：`import importlib` 不保证 util 子模块可用
import json
import os
import re
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))


def _esc(s):
    """把清单里的字符串安全地放进 HTML。

    `plugin.json` 是半受信输入（用户从别处拿来的插件就可能是别人的）。
    `tab.label` 里一个引号就能破掉属性、一个 `<script>` 就能改页面 ——
    转义成本为零，没有理由不做。
    """
    return _html.escape(str(s), quote=True)


# 页签 id 的合法形状：字母开头，只含字母数字 _ -
_TAB_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _valid_tab_id(v):
    return isinstance(v, str) and bool(_TAB_ID_RE.match(v.strip()))
def _data_dir():
    """插件目录跟着**数据目录**走（exe 旁边），不是代码目录（_internal/）。

    冻结成 exe 后如果这里用 __file__，用户把插件丢到 exe 旁边的 plugins/
    会**完全不被发现** —— 因为代码在看 _internal/plugins/。
    延迟 import paths：本模块要在 plugins/ 不存在时也能被 import。
    """
    try:
        import paths
        return paths.data_dir()
    except Exception:
        return HERE


PLUGIN_DIR = os.path.join(_data_dir(), "plugins")

MANIFEST = "plugin.json"
ENTRY = "__init__.py"


class Plugin(object):
    """一个已发现（可能未启用）的插件。

    ⚠️ **清单是用户手写的 JSON，字段类型一律不可信。** 构造函数必须把每个字段
    归一化 —— 见下面 `__init__` 的注释。`discover()` 承诺「插件坏了不拖垮内核」，
    而它在 `import server` 期间跑，所以这里抛异常 = 整个查看器起不来。
    """

    def __init__(self, pid, path, manifest):
        self.id = pid
        self.path = path
        self.manifest = manifest

        name = manifest.get("name")
        self.name = name.strip() if isinstance(name, str) and name.strip() else pid

        # requires 必须是「一串模块名」。写成 5 / true / 一个字符串 都不能炸 ——
        # 以前直接 `list(manifest.get("requires") or [])`，`"requires": 5`
        # 就是 TypeError: 'int' object is not iterable，而它发生在 import server
        # 期间 → 整个工具起不来。2026-10-13 审查发现。
        req = manifest.get("requires")
        self.requires = []
        if req:
            if isinstance(req, str):
                req = [req]                       # 写成单个字符串 → 当一项，别按字符拆
            if isinstance(req, (list, tuple)):
                self.requires = [m.strip() for m in req
                                 if isinstance(m, str) and m.strip()]
            else:
                self.requires = []
                self.warn = "requires 不是列表，已忽略"

        # tab 要么是一个**带合法 id 的** dict，要么当作没有。
        # 下游（tab_buttons / tab_containers / tab_meta）一律 `p.tab["id"]`，
        # 所以这里必须保证「p.tab 为真 ⇒ 一定有 id」——
        # 以前渲染处用下标、把关处用 .get，"tab": {"label": "X"} 就是首页 500。
        #
        # ⚠️ id 必须**在源头校验成标识符**，不能靠转义：同一个 id 会同时出现在
        #    ① HTML 属性 ② 内联 onclick 的 JS 字符串 ③ 给前端的 JSON 里。
        #    转义只在 ① 正确，②③ 会拿到被转义的串，三处对不上 = 页签点不动。
        #    校验成 [A-Za-z][A-Za-z0-9_-]* 三个上下文都安全。
        # label 是显示文字，保留原文（HTML 输出时才转义）。
        self.tab = None
        tab = manifest.get("tab")
        if tab:
            if not isinstance(tab, dict):
                self.warn = "tab 不是对象，已忽略"
            elif not _valid_tab_id(tab.get("id")):
                self.warn = ("tab.id 缺失或非法（只能用字母数字_-，且以字母开头），"
                             "已忽略 —— 页签不会出现")
            else:
                self.tab = {
                    "id": tab["id"].strip(),
                    "label": str(tab.get("label") or self.name),
                }

        self.enabled = True
        self.error = ""            # 非空 = 未启用的原因（人话，直接给用户看）
        self.warn = getattr(self, "warn", "")   # 非致命问题（清单字段写错之类）
        self.missing = []          # 缺的模块名

        self.BODY = ""
        self.CSS = ""
        self.JS = ""
        self.routes = {}

    # ── 未启用时页签里显示什么 ──
    def disabled_body(self):
        # 模块名来自清单，也要转义 —— 它会进 <code> 和 <b>
        req = _esc("、".join(self.missing)) or "依赖"
        # 建议随模式变：exe 里没有 pip，打出来是骗人（见 _missing_hint）
        hint = _missing_hint(self.missing)
        code = ("<code style=\"display:inline-block;margin-top:8px;padding:7px 12px;"
                "background:#0a0c1a;border:1px solid var(--line-2);border-radius:7px;"
                "font-family:SF Mono,Consolas,monospace;color:var(--txt)\">%s</code>"
                % _esc(hint))
        return (
            '<div style="padding:34px 22px;max-width:660px">'
            '<div style="font-size:15px;font-weight:600;color:#ffc46b;margin-bottom:10px">'
            '⚠ 「%s」插件未启用</div>'
            '<div style="font-size:12.5px;color:var(--dim);line-height:1.9">'
            '缺少依赖：<b style="color:var(--txt)">%s</b><br>'
            '其余页签不受影响，照常可用。<br>%s'
            '</div></div>' % (_esc(self.name), req, code)
        )


def _missing_hint(missing):
    """缺依赖时给什么建议。

    ⚠️ **冻结成 exe 之后不存在 pip** —— 再打 `pip install numpy` 就是骗人：
    用户照着敲只会得到一个 "不是内部或外部命令"。发布版里缺库的唯一
    可能是打包时漏了，那就该说「联系发布者」。
    """
    if getattr(sys, "frozen", False):
        return "本发布版没有打包这些库（%s）—— 请联系发布者" % "、".join(missing)
    return "pip install " + " ".join(missing)


def _nested_hint(path):
    """plugins/<X>/ 里没有 plugin.json，但**子目录**里有 —— 多半是解压多套了一层。

    这是新手装插件最常见的错：解压出 `analysis-main/`，他把整个目录拷进
    plugins/，真正的插件就落在了 `plugins/analysis-main/analysis/`。
    没有这句提示，用户只会看到「插件没生效」，完全不知道错在哪。

    返回 (子目录名, 子目录清单里声明的 id)。**id 有用**：加载器拿**目录名**
    当插件 id，所以建议的目录名应该是那个 id，而不是外层的 `analysis-main`。
    """
    try:
        for name in sorted(os.listdir(path)):
            sub = os.path.join(path, name)
            man = os.path.join(sub, MANIFEST)
            if os.path.isdir(sub) and os.path.isfile(man):
                inner_id = ""
                try:
                    with open(man, encoding="utf-8") as f:
                        d = json.load(f)
                    if isinstance(d, dict):
                        inner_id = str(d.get("id") or "")
                except Exception:
                    pass
                return name, inner_id
    except OSError:
        pass
    return "", ""


def _read_manifest(path):
    p = os.path.join(path, MANIFEST)
    if not os.path.isfile(p):
        return None, "没有 %s" % MANIFEST
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as exc:
        return None, "%s 读不了（%s）" % (MANIFEST, exc)
    if not isinstance(d, dict) or not d.get("id"):
        return None, "%s 里没有 id" % MANIFEST
    return d, ""


def _check_requires(names):
    """返回 import 不进来的模块名列表。"""
    missing = []
    for m in names:
        try:
            importlib.import_module(m)
        except Exception:
            missing.append(m)
    return missing


def _load_module(path, pid):
    """按**文件路径**导入插件的 __init__.py。

    刻意不用 `import plugins.<id>` —— 那样插件就成了内核的包，得处理
    包名冲突，而且插件目录还得有 __init__.py 才认。按路径加载更独立。

    插件目录会加进 sys.path（**追加，不是插到最前**），且**一直留着**：
    - 追加而非插前 → 同名时内核的模块优先。插件里放个 `config.py` 不会
      把内核的 config 顶掉，但插件自己的 `similarity.py` 能被找到。
    - 一直留着 → 插件里的 `import similarity` 可能发生在**请求时**
      （函数体内延迟导入），加载完就摘掉的话那时会 ModuleNotFoundError。
      这个坑踩过一次：路由能注册、页面能开，一请求就 500。
    """
    entry = os.path.join(path, ENTRY)
    if not os.path.isfile(entry):
        return None
    if path not in sys.path:
        sys.path.append(path)
    spec = importlib.util.spec_from_file_location("mtxplug_%s" % pid, entry)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover(verbose=True):
    """扫描 plugins/ 并加载。返回 [Plugin]。

    永不抛异常 —— 插件坏了不该拖垮内核启动。坏的那个跳过并说明原因。
    """
    out = []
    if not os.path.isdir(PLUGIN_DIR):
        return out

    # listdir 也可能抛（权限、IO 错误）—— 它曾经在 try 外面
    try:
        names = sorted(n for n in os.listdir(PLUGIN_DIR)
                       if os.path.isdir(os.path.join(PLUGIN_DIR, n))
                       and not n.startswith((".", "_")))
    except OSError as exc:
        if verbose:
            print("[plugin] plugins/ 读不了，本次不加载任何插件：%s" % exc)
        return out

    for pid in names:
        # ★ 整个插件处理包一层：**任何**意外都只跳过这一个插件。
        #   本函数在 `import server` 期间被调用，抛出去 = 整个查看器起不来 ——
        #   那正是这个插件系统存在的意义要避免的事。宁可少一个插件，不能少一个软件。
        try:
            _load_one(pid, out, verbose)
        except Exception as exc:
            if verbose:
                print("[plugin] 跳过 %s：%s: %s" % (pid, type(exc).__name__, exc))
                for ln in traceback.format_exc().splitlines()[-3:]:
                    print("[plugin]   " + ln)
    return out


def _load_one(pid, out, verbose):
    """处理一个插件，把结果 append 进 out。异常由 discover 兜住。"""
    path = os.path.join(PLUGIN_DIR, pid)
    manifest, err = _read_manifest(path)
    if manifest is None:
        if verbose:
            print("[plugin] 跳过 %s：%s" % (pid, err))
            sub, inner_id = _nested_hint(path)
            if sub:
                want = inner_id or sub          # 加载器拿目录名当 id，所以建议用清单里的 id
                print("[plugin]   ↑ 但子目录 %s/ 里有 %s —— 多半是解压多套了一层。"
                      % (sub, MANIFEST))
                print("[plugin]     修法：把 plugins/%s/%s/ 里的文件移到 plugins/%s/ 下面"
                      % (pid, sub, want))
                print("[plugin]     （目录名就是插件的名字，用 %s）" % want)
        return

    p = Plugin(pid, path, manifest)
    if p.warn and verbose:
        print("[plugin] %s 清单有问题：%s" % (pid, p.warn))

    # ① 依赖检查 —— 缺了就整块不启用，但页签留着（见 disabled_body）
    missing = _check_requires(p.requires)
    if missing:
        p.enabled = False
        p.missing = missing
        p.error = "缺少 %s" % "、".join(missing)
        if p.tab:
            p.BODY = p.disabled_body()
        if verbose:
            print("[plugin] %s 未启用：缺少 %s" % (p.id, "、".join(missing)))
            print("[plugin]          → %s" % _missing_hint(missing))
        out.append(p)
        return

    # ② 加载模块
    try:
        mod = _load_module(path, pid)
    except Exception as exc:
        p.enabled = False
        p.error = "导入失败：%s: %s" % (type(exc).__name__, exc)
        if p.tab:
            p.BODY = ('<div style="padding:34px 22px;color:#ffc46b;font-size:13px">'
                      '⚠ 「%s」插件导入失败：%s</div>' % (_esc(p.name), _esc(p.error)))
        if verbose:
            print("[plugin] %s 导入失败：%s" % (pid, p.error))
            for ln in traceback.format_exc().splitlines()[-4:]:
                print("[plugin]   " + ln)
        out.append(p)
        return

    if mod is None:
        # 有清单没入口 —— 纯声明式插件（比如只想挂个页签的静态说明页）
        if verbose:
            print("[plugin] %s 已登记（无 %s，仅清单）" % (pid, ENTRY))
        out.append(p)
        return

    p.BODY = getattr(mod, "BODY", "") or ""
    p.CSS = getattr(mod, "CSS", "") or ""
    p.JS = getattr(mod, "JS", "") or ""
    try:
        r = getattr(mod, "routes", None)
        p.routes = dict(r() or {}) if callable(r) else {}
    except Exception as exc:
        p.enabled = False
        p.error = "routes() 抛异常：%s: %s" % (type(exc).__name__, exc)
        if verbose:
            print("[plugin] %s 的 routes() 失败：%s" % (pid, p.error))

    if verbose:
        bits = []
        if p.tab:
            bits.append("页签 %s" % p.tab["id"])
        if p.routes:
            bits.append("%d 条路由" % len(p.routes))
        print("[plugin] %s「%s」已启用%s"
              % (p.id, p.name, ("（" + "，".join(bits) + "）") if bits else ""))
    out.append(p)


# 内核自己占用的路径 —— 插件**不许**注册。
# 插件路由在分发时优先于内核的 if/elif 链，不挡的话，一个插件注册 `/api/run`
# 就能静默顶掉「跑任务」的入口（不是提权，但会让内核行为变得无法解释）。
# 这份清单要和 server.py 的 do_GET/do_POST 手工对齐 —— 内核加了新端点记得同步。
RESERVED_ROUTES = {
    "/image",
    "/api/comfyui", "/api/quit",
    "/api/tasks", "/api/config", "/api/metadata", "/api/loras", "/api/lora-preview",
    "/api/models", "/api/check-nodes", "/api/tasklists", "/api/tasklists/delete",
    "/api/run", "/api/run/status", "/api/run/stop",
    "/api/presets", "/api/presets/load", "/api/presets/save", "/api/presets/delete",
    "/api/save-config", "/api/generate-preview", "/api/generate-tasks",
    "/api/pick-folder", "/api/matrix-folders", "/api/example-config",
}


def collect_routes(plugins):
    """把各插件的路由汇总成 {路径: handler}。

    撞车时**先到先得** + 打警告。两条规矩：
      · 插件之间撞 → 后来的忽略
      · 撞内核保留路径（RESERVED_ROUTES）→ 一律拒绝
    """
    table = {}
    for p in plugins:
        for path, fn in (p.routes or {}).items():
            if path in RESERVED_ROUTES:
                print("[plugin] %s 想注册内核保留路径 %s —— 已拒绝" % (p.id, path))
                continue
            if not (isinstance(path, str) and path.startswith("/")):
                print("[plugin] %s 的路由路径非法（必须是 / 开头）：%r" % (p.id, path))
                continue
            if path in table:
                print("[plugin] 路由冲突：%s 已被占用，%s 的注册被忽略" % (path, p.id))
                continue
            table[path] = fn
    return table


def tab_buttons(plugins):
    """页签按钮 HTML（注入 @PLUGIN_TABS@）。

    ⚠️ label 来自 plugin.json（半受信），**必须转义** —— 一个 `"><img onerror=>`
    就能改页面。id 不用转义：它在 Plugin.__init__ 里已被校验成
    `[A-Za-z][A-Za-z0-9_-]*`，三个上下文（HTML 属性 / JS 字符串 / JSON）都安全。
    """
    return "".join(
        '<button class="tabbtn" id="tabbtn-%s" onclick="switchTab(\'%s\')">%s</button>'
        % (p.tab["id"], p.tab["id"], _esc(p.tab["label"]))
        for p in plugins if p.tab)


def tab_containers(plugins):
    """页签容器 HTML（注入 @PLUGIN_BODY@），含 `<div id="tab-<id>">` 外壳。

    ⚠️ **不要**对 p.BODY 转义 —— 那是插件自己写的 HTML，是它要渲染的内容。
    只转义「清单来的、被当作纯文本的」东西（label / name / 模块名）。
    """
    return "".join(
        '<div id="tab-%s" class="hidden">%s</div>' % (p.tab["id"], p.BODY)
        for p in plugins if p.tab)


def tab_css(plugins):
    return "\n".join("/* ── 插件 %s ── */\n%s" % (p.id, p.CSS)
                     for p in plugins if p.CSS)


def tab_js(plugins):
    return "\n".join("/* ── 插件 %s ── */\n%s" % (p.id, p.JS)
                     for p in plugins if p.JS)


def tab_meta(plugins):
    """给前端 JS 的页签元数据（内核靠它做 switchTab / hash 路由）。

    未启用的插件也在里面 —— 页签要照常显示。
    """
    return [{"id": p.tab["id"], "label": p.tab.get("label") or p.name,
             "enabled": bool(p.enabled)}
            for p in plugins if p.tab]
