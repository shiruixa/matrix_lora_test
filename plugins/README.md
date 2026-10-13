# 插件开发规范

一个插件 = `plugins/` 下的**一个目录**。加插件不用动内核，删目录即卸载。

> ⚠️ **插件就是任意 Python 代码。** 内核会 `exec` 你的 `__init__.py`，
> 所以「安装一个插件」等价于「信任并运行它」。别装来源不明的插件。

---

## 1. 目录结构

```
plugins/<id>/                 ← <id> 必须与 plugin.json 里的 id 一致
    plugin.json               ← 必需。清单
    __init__.py               ← 可选。契约实现（没有它就只是个声明式登记）
    ...                       ← 你自己的模块 / 数据 / 模板，随便放
```

目录名以 `.` 或 `_` 开头的会被跳过（放临时/禁用插件用）。

**加载顺序** = 目录名的字典序。插件之间的可见性不做保证，别互相依赖。

---

## 2. `plugin.json`

```jsonc
{
  "id":     "analysis",              // 必需。插件唯一标识，也是目录名
  "name":   "融合诊断",               // 显示名（页签文字默认取这个）
  "desc":   "一句话说明",             // 可选，给人和未来的插件列表用
  "tab":    { "id": "sim", "label": "融合诊断" },   // 可选。要挂页签才写
  "requires": ["numpy", "PIL"]       // 可选。需要能 import 的模块名
}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | ✅ | 唯一标识。缺了这份清单会被跳过并打日志 |
| `name` | | 显示名 |
| `tab.id` | | 页签 DOM id 的后半段（生成 `#tab-<id>` / `#tabbtn-<id>`）。**同时决定 hash 路由**（`#sim`） |
| `tab.label` | | 页签按钮文字，缺省用 `name` |
| `requires` | | 逐个 `import`，任一失败 → **整个插件不启用**（见 §6） |

> ⚠️ `plugin.json` 是**唯一必需**的文件，且**必须能被 `json.load` 解析**。
> 写坏了不会让内核起不来，但插件会静默消失（控制台有日志）。

---

## 3. Python 契约（`__init__.py`）

四个顶层名字，**全部可选**：

| 名字 | 类型 | 用途 |
|---|---|---|
| `BODY` | `str` | 页签**内容** HTML → `@PLUGIN_BODY@` |
| `CSS` | `str` | 样式 → `@PLUGIN_CSS@` |
| `JS` | `str` | 脚本 → `@PLUGIN_JS@`（内核包一层 IIFE，见 §5） |
| `routes()` | `callable` | 返回 `{路径: handler}` |

### `BODY` 只写内容，不要自己套外壳

```python
# ✅ 对
BODY = r"""
  <div class="toolbar">…</div>
  <div id="myCanvas"></div>
"""

# ❌ 错 —— 外壳由加载器按 plugin.json 的 tab.id 生成，两边都套 = 重复 id
BODY = r"""<div id="tab-sim" class="hidden">…</div>"""
```

加载器会生成 `<div id="tab-<tab.id>">…</div>` 把 `BODY` 包起来。
**只想要一个静态说明页的话，写 `BODY` 就够了**，不需要 `JS`。

### `routes()` —— 后端路由

```python
def routes():
    return {"/api/my-thing": handle_my_thing}

def handle_my_thing(handler, params):
    """handler = 内核的 HTTP Handler 实例；params = parse_qs 的结果（值都是 list）。"""
    folder = params.get("folder", [""])[0]
    resolved = handler.resolve_folder(folder)   # 父目录 → 真正含 task.json 的目录
    tasks, dims = handler.scan_tasks(resolved)  # → ({...}, {...})
    handler._json({"ok": True, "n": len(tasks)})
```

**内核给插件的后端接口**（就这三个，别指望更多）：

| 接口 | 作用 |
|---|---|
| `handler._json(data, code=200)` | 回 JSON |
| `handler.resolve_folder(folder)` | 把「父目录」解析成真正含 `task.json` 的任务目录 |
| `handler.scan_tasks(folder)` | 扫出 `{tasks, dimensions}` |

> ⚠️ **不要 `import server`** —— 那会循环导入（server → plugin_loader → 你）。
> 需要什么跟内核要，别去抓内部符号。

**路由冲突**：两个插件注册同一路径时**先到先得**，后者被忽略并打警告。

---

## 4. 你在 `__init__.py` 里的同级模块

插件目录会被加到 `sys.path` **末尾**，所以：

```python
# plugins/analysis/__init__.py
import similarity      # → plugins/analysis/similarity.py ✅
import config          # → 内核的 config.py（内核路径在前，同名时内核优先）
```

- **追加**而非插前 → 插件放一个 `config.py` **不会**顶掉内核的
- **一直留着** → 你可以把 `import` 写在函数体里（延迟导入），请求时也能找到

⚠️ 反过来说：你的模块名如果和内核同名，**你被内核遮住**。取个独特的名字。

---

## 5. JS 契约 —— `window.MLX`

你的 `JS` 会被内核包进一个 IIFE，**唯一**与内核通信的入口是 `window.MLX`。
**不要**去 `document.getElementById` 内核的元素、也不要调内核的全局函数
（那些名字内核随时可以改）。

### 可直接调用的

| 成员 | 签名 | 说明 |
|---|---|---|
| `MLX.api` | `api(method, path, body?) → Promise` | 封装好的 fetch，失败返回 `{ok:false, error}` 而不是抛异常 |
| `MLX.getFolder()` | `→ string` | 当前选中的矩阵目录 |
| `MLX.getMarks()` | `→ object` | 星标表 `{key: true}`。**必须用这个函数**，别缓存返回值 |
| `MLX.switchTab(id)` | | 切到某个页签 |
| `MLX.openTask(key)` | | 打开网格里某张图的大图弹窗 |
| `MLX.escAttr(s)` / `MLX.escHtml(s)` | `→ string` | 转义（生成 HTML 字符串时用） |
| `MLX.tabs` | `→ array` | 全部页签 `[{id, label, onShow?}]`（只读，别直接改；加页签用 `registerTab`） |
| `MLX.emit(事件, …)` | | 主动触发一个事件（给别的插件听；内核自己也在用） |

> `_` 开头的成员（`MLX._hooks` 等）是内部实现，**不要碰**。契约只覆盖上面这张表 ——
> 表里没有的，内核改版时不会知会你。

> ⚠️ **`getMarks()` 是函数不是属性，这是有意的**：内核在切换目录时会
> `marks = JSON.parse(localStorage…)` **整体重新赋值**。你若在初始化时
> `var m = MLX.getMarks()` 存下来，之后拿到的就是**过期对象** —— 星标状态会一直不对。

### 注册

| 调用 | 说明 |
|---|---|
| `MLX.registerTab({id, label, onShow})` | 登记页签。`onShow()` 在每次切到该页签时调用。**同一 id 重复注册 = 覆盖**（用于补上 `onShow`） |
| `MLX.on(事件, fn)` | 订阅内核事件 |
| `MLX.expose({name: fn, …})` | 把函数挂到 `window` —— 供**内联 `onclick="fn()"`** 用 |

> 因为你的脚本跑在 IIFE 里，函数**默认不全局**。`BODY` 里写了
> `<button onclick="myReload()">` 的话，必须 `MLX.expose({myReload: myReload})`。
> 更干净的做法：别用内联 `onclick`，在 `onShow` 里 `addEventListener`。

### 可订阅的事件

| 事件 | 何时触发 |
|---|---|
| `folder-loaded` | 目录里的任务加载完成（用户换了目录，或首次加载） |
| `marks-changed` | 星标被改动 |
| `resize` | 窗口尺寸变化 |

```js
MLX.on("folder-loaded", function(){
  // 本页签可见时才重算 —— 用户可能正停在别的页签
  if (!document.getElementById("tab-" + "sim").classList.contains("hidden")) myLoad();
});
```

---

## 6. 依赖与降级

`requires` 里任一模块 import 失败 → **插件整体不启用**，但：

| 现象 | 表现 |
|---|---|
| 控制台 | `[plugin] <id> 未启用：缺少 xxx` + `pip install xxx` 提示 |
| 页签 | **照常出现**，内容换成加载器生成的内置提示（含缺失模块名和安装命令） |
| `CSS` / `JS` | 不注入 |
| 路由 | 不注册 → 访问返回 404 |

**这是有意设计的**：静默消失会让你去猜「为什么少了个页签」，而明确提示
「装好 numpy 刷新即可」是能直接照做的。

> 如果你的插件**只在某个函数里**才用到重依赖（像 `from PIL import Image` 写在
> 函数体内），把它写进 `requires` 能让失败**提前到启动时**并给出人话提示；
> 不写则要等到用户点下去才炸。

---

## 7. 卸载

删掉 `plugins/<id>/` 目录，重启。内核**不会** import 插件里的任何模块，
所以没有残留 import 会炸。`plugins/` 整个目录不存在也正常。

插件自己的数据（配置、缓存）**放在自己的目录里** —— 那样卸载才彻底。

---

## 8. 完整示例

见 `plugins/analysis/` —— 它有页签、有 CSS/JS、有后端路由、有同级算法模块、
有依赖声明，是一个把这套契约全部用上的实例。

---

## 9. 已知限制

| 限制 | 说明 |
|---|---|
| **只能注册 GET 路由** | `routes()` 目前只被 `do_GET` 查表。需要 POST 的话得先改内核（`server.py` 的 `do_POST`） |
| **CSS 是全局的** | `CSS` 会被拼进页面唯一的 `<style>`，**没有作用域**。类名请自带前缀，否则会和内核/其它插件打架 |
| **没有版本协商** | `plugin.json` 不声明兼容的内核版本。内核契约变了，老插件会静默失效 |
| **没有生命周期钩子** | 只有 `onShow` 和三个事件，没有 `on_unload` / `on_install` |
| **不能加热重载** | 改完插件要重启查看器 |
| **不能加工具栏按钮** | 只能挂页签，或往自己的 `BODY` 里放控件 |
