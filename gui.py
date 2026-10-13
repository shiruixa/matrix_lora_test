"""
Matrix Viewer GUI — HTML + CSS + JS for N-dimensional LoRA strength grid.
All in one Python string for self-contained serving.
"""
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>LoRA 矩阵查看器</title>
<style>
:root{
  --bg:#0b0d1a; --bg-2:#111428; --panel:#161a30; --panel-2:#1c2140;
  --line:#28304f; --line-2:#333c63;
  --txt:#e9ecf8; --dim:#8a93bb; --dim-2:#5d6689;
  --accent:#7c5cff; --accent-d:#5f45d8; --hot:#ff4d7a; --ok:#3ddc97;
  --thumb:150px;
  --radius:10px;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{
  font:13px/1.55 ui-sans-serif,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
  color:var(--txt);
  background:
    radial-gradient(1100px 600px at 12% -10%, #241c4d55, transparent 60%),
    radial-gradient(900px 500px at 105% 0%, #3a164055, transparent 55%),
    var(--bg);
  background-attachment:fixed;
  min-height:100vh;
}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:6px;border:2px solid var(--bg)}
::-webkit-scrollbar-thumb:hover{background:var(--accent-d)}

/* ── 顶栏 ── */
.topbar{
  position:sticky;top:0;z-index:300;
  display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  padding:12px 18px;
  background:rgba(13,16,32,.82);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line);
}
.brand{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14px;letter-spacing:.3px;white-space:nowrap}
.brand .dot{width:9px;height:9px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--hot));box-shadow:0 0 12px var(--accent)}
.topbar input[type=text]{
  flex:1;min-width:200px;padding:8px 12px;
  border:1px solid var(--line);border-radius:8px;
  background:#0d1022;color:var(--txt);font-size:12px;
  transition:border-color .15s, box-shadow .15s;
}
.topbar input[type=text]:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px #7c5cff22}
.btn{
  padding:8px 14px;border:1px solid transparent;border-radius:8px;
  background:linear-gradient(180deg,var(--accent),var(--accent-d));
  color:#fff;cursor:pointer;font-size:12px;font-weight:500;white-space:nowrap;
  transition:filter .15s, transform .1s;
}
.btn:hover{filter:brightness(1.15)}
.btn:active{transform:translateY(1px)}
.btn.ghost{background:var(--panel-2);border-color:var(--line-2);color:var(--dim)}
.btn.ghost:hover{color:var(--txt);border-color:var(--accent)}

/* ── 工具栏 ── */
.toolbar{
  position:sticky;top:57px;z-index:290;
  display:flex;gap:22px;align-items:center;flex-wrap:wrap;
  padding:11px 18px;
  background:rgba(17,20,40,.86);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line);
}
.ctrl{display:flex;align-items:center;gap:8px}
.ctrl > label{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.6px;white-space:nowrap}
select{
  padding:6px 10px;border:1px solid var(--line-2);border-radius:7px;
  background:#0d1022;color:var(--txt);font-size:12px;cursor:pointer;
  transition:border-color .15s;
}
select:focus{outline:none;border-color:var(--accent)}
.ctrl select{font-weight:600;color:#fff}
/* ComfyUI 实例选择器 —— 多便携版并存时，「连的是哪台」必须一眼看得见 */
#cuiSel{max-width:360px;font-family:SF Mono,Consolas,monospace;font-size:11px}
#cuiSel.off{border-color:#7a3a3a;color:#ffb4b4}
#cuiSel.busy{opacity:.6}
.axis-tag{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:5px;font-size:10px;font-weight:700}
.axis-tag.x{background:#7c5cff33;color:#b9a6ff;border:1px solid #7c5cff55}
.axis-tag.y{background:#3ddc9733;color:#7ff0c0;border:1px solid #3ddc9755}
.axis-tag.z{background:#ffb24733;color:#ffd166;border:1px solid #ffb24755}
/* 分面平铺：用 Grid 而不是 flex-wrap —— 每行列数一致，位置可预期。
   分面值已按升序排（_sort_dims），所以从左到右、从上到下就是值的递增顺序 */
.facet-grid{display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, max-content));
  gap:18px;align-items:start;justify-content:start}
.facet-cell{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 10px 10px}
.facet-cell > .facet-title{font-size:11px;color:#ffd166;font-weight:700;margin-bottom:7px;
  font-family:SF Mono,Consolas,monospace;white-space:nowrap}

input[type=range]{
  -webkit-appearance:none;appearance:none;width:120px;height:4px;border-radius:2px;
  background:var(--line-2);outline:none;cursor:pointer;
}
input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none;width:15px;height:15px;border-radius:50%;
  background:var(--accent);border:2px solid #fff2;box-shadow:0 2px 6px #0008;cursor:pointer;
}
input[type=range]::-moz-range-thumb{width:15px;height:15px;border-radius:50%;background:var(--accent);border:none;cursor:pointer}

/* ── 过滤条 ── */
.filters{
  display:flex;gap:18px;flex-wrap:wrap;align-items:center;
  padding:11px 18px;border-bottom:1px solid var(--line);
  background:#0e1124aa;
}
.fgroup{display:flex;align-items:center;gap:7px}
.fgroup .flabel{color:var(--dim);font-size:11px;white-space:nowrap;max-width:190px;overflow:hidden;text-overflow:ellipsis}
.fbtn{
  padding:4px 11px;border:1px solid var(--line-2);border-radius:20px;
  background:transparent;color:var(--dim);cursor:pointer;font-size:11px;
  transition:all .14s;
}
.fbtn:hover{border-color:var(--accent);color:var(--txt)}
.fbtn.active{
  background:linear-gradient(180deg,var(--accent),var(--accent-d));
  border-color:transparent;color:#fff;font-weight:600;
  box-shadow:0 2px 10px #7c5cff55;
}

/* ── 网格 ── */
/* ⚠️⚠️ 这里必须是 height，**不能改回 max-height** —— 这个坑复发过两次。
   max-height 会让容器**按内容收缩**：空目录下画布只剩一行提示那么高（~300px），
   下面露出整片页面底色（--bg #0b0d1a），用户看到的就是「画布没铺下去 / 像被盖住了」。
   配合 #canvasWrap{min-height:0}，height 让画布拿到**真实**高度，
   fitView() 量到的 clientHeight 也就准 —— 不会重演「按 520 缩放、底部被裁」。
   改完请跑 `node agent_tool/layout_check.mjs` 自查。 */
.grid-wrap{padding:0;overflow:hidden;height:var(--grid-h,calc(100vh - 175px));display:flex;flex-direction:column}
/* 可缩放画布：滚轮缩放、空白处拖拽平移（像 CAD / 白板） */
/* ⚠️ min-height 必须是 0 —— 早先写死 520px，矮窗口下画布被撑到 520 而父容器只给
   两百多，clientHeight 谎报 520 → fitView() 按 520 缩放居中，多出来的部分被
   .grid-wrap 的 overflow:hidden 裁掉，**底排图片看不见**。0 才能如实收缩。 */
#canvasWrap{position:relative;flex:1;min-height:0;overflow:hidden;cursor:grab;background:#0a0c1a;
  background-image:radial-gradient(circle at 1px 1px, rgba(255,255,255,.05) 1px, transparent 0);
  background-size:22px 22px}
#canvasWrap.dragging{cursor:grabbing}
/* 空状态（没找到 task.json / 加载失败）：提示居中显示。
   画布现在铺满整屏，不居中的话那行字会孤零零挂在顶上。 */
#canvasWrap.empty{display:flex;align-items:center;justify-content:center}
#canvasWrap.empty #grid{transform:none !important}
/* 内容超出画布时的提示角标。
   为什么需要它：画面是 transform 缩放的，**溢出内容不会产生滚动条**，
   overflow:hidden 一裁就没了。用户滚轮放大后底部看不见，又不知道该按什么
   —— 这个角标就是告诉他出口在哪。内容放得下时自动隐藏。 */
.fit-hint{position:absolute;right:12px;bottom:12px;z-index:16;
  background:rgba(13,16,32,.94);border:1px solid var(--line-2);border-radius:9px;
  padding:7px 12px;font-size:11.5px;color:var(--dim);pointer-events:none;
  box-shadow:0 6px 20px #0007}
.fit-hint b{color:#ffd166;font-weight:600}

/* 快捷目录 —— 工具要看的目录几乎总在 ComfyUI 的 output/matrix 底下，
   直接列出来点选：比文件夹对话框少好几步，而且**不依赖 tkinter**
   （便携版的 python_embeded 没有它，弹不出对话框）。
   :empty 隐藏，免得没内容时留一条空隙。 */
.quickdirs{display:flex;gap:6px;flex-wrap:wrap;align-items:center;
  padding:10px 18px 0;font-size:11.5px}
.quickdirs:empty{display:none;padding:0}
.qd-label{color:var(--dim-2);margin-right:2px}
.qd-chip{background:var(--panel);border:1px solid var(--line);border-radius:20px;
  padding:3px 11px;color:var(--dim);cursor:pointer;transition:background .14s,border-color .14s;
  white-space:nowrap;max-width:280px;overflow:hidden;text-overflow:ellipsis}
.qd-chip:hover{background:var(--panel-2);border-color:var(--line-2);color:var(--txt)}
.qd-chip.on{background:#7c5cff22;border-color:#7c5cff66;color:#c3b6ff}
.qd-chip.dim{opacity:.45}
#grid{transform-origin:0 0;will-change:transform;display:inline-block;padding:20px}
.grid-table{border-collapse:separate;border-spacing:0;margin:0 auto}
.grid-table th{
  position:sticky;top:0;z-index:20;
  padding:8px 12px;font-size:11px;font-weight:600;color:var(--dim);
  background:var(--panel-2);border-bottom:1px solid var(--line-2);
  border-right:1px solid var(--line);white-space:nowrap;
}
.grid-table thead th:first-child{left:0;z-index:30}
.grid-table tbody th{
  position:sticky;left:0;z-index:21;
  background:var(--panel-2);border-right:1px solid var(--line-2);
  border-bottom:1px solid var(--line);
  padding:8px 14px;white-space:nowrap;text-align:center;
  font-variant-numeric:tabular-nums;color:#c3c9e6;
}
.grid-table th.corner{padding:8px 11px;color:var(--dim-2);font-weight:700;cursor:default}
.grid-table td{
  padding:6px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);
  text-align:center;vertical-align:middle;background:var(--panel);
  transition:background .14s;
}
.grid-table td.empty{background:#0d1022}
.grid-table td.empty .ph{color:var(--dim-2);font-size:11px;padding:26px 0;display:block}
.cellbox{position:relative;display:inline-block;border-radius:8px;overflow:hidden;cursor:pointer}
.cellbox img{
  display:block;width:var(--thumb);height:auto;border-radius:8px;
  transition:transform .18s ease, filter .18s;
  background:#0a0c18;
}
.cellbox:hover img{transform:scale(1.03);filter:brightness(1.08)}
.cellbox .badge{
  position:absolute;top:6px;right:6px;padding:1px 6px;border-radius:20px;
  font-size:9px;font-weight:700;background:rgba(0,0,0,.62);color:#cfd6f5;
  backdrop-filter:blur(4px);
}
.cellbox.base{border:2px solid var(--ok);box-shadow:0 0 0 1px #0008, 0 0 16px #3ddc9733}
.cellbox.base .badge{background:var(--ok);color:#06231a}
/* 十字准星：同列 / 同行高亮 */
.grid-table td.cross{background:#7c5cff14}
.grid-table tbody th.cross{color:var(--txt);background:#7c5cff2e}
.grid-table thead th.cross{color:var(--txt);background:#7c5cff2e}

.spinner{width:30px;height:30px;border:3px solid var(--line-2);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;margin:60px auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.hint{text-align:center;color:var(--dim);padding:70px 20px;font-size:13px;line-height:2}
.hint b{color:var(--txt)}

/* ── 弹窗 ── */
.overlay{position:fixed;inset:0;background:rgba(4,6,16,.9);backdrop-filter:blur(6px);z-index:999;display:flex;align-items:center;justify-content:center;padding:22px}
.modal{
  display:flex;max-width:min(1600px,96vw);max-height:92vh;overflow:hidden;
  background:var(--panel);border:1px solid var(--line-2);border-radius:16px;
  box-shadow:0 30px 90px #000c;
}
.modal-left{position:relative;flex:1;min-width:0;display:flex;align-items:center;justify-content:center;background:#05060f}
.modal-left img{max-width:100%;max-height:92vh;object-fit:contain;display:block}
.modal-right{width:390px;min-width:300px;overflow-y:auto;padding:20px 22px;border-left:1px solid var(--line)}
.modal-right h3{
  font-size:11px;text-transform:uppercase;letter-spacing:.9px;color:var(--dim);
  margin:18px 0 8px;padding-top:14px;border-top:1px solid var(--line);
}
.modal-right h3:first-child{margin-top:0;padding-top:0;border-top:none}
.row{display:flex;gap:10px;margin-bottom:5px;font-size:12px}
.row .lbl{color:var(--dim);min-width:74px;flex-shrink:0}
.row .val{color:var(--txt);word-break:break-all}
.prompt{font-size:11px;color:#c3c9e6;line-height:1.6;max-height:170px;overflow-y:auto;background:#0b0e1e;border:1px solid var(--line);border-radius:8px;padding:10px;white-space:pre-wrap;word-break:break-word}
.prompt.neg{color:#e39aa8}
.lora-tag{display:inline-block;background:#7c5cff1f;border:1px solid #7c5cff44;border-radius:20px;padding:3px 10px;margin:3px 4px 3px 0;font-size:10.5px;color:#c0b0ff}
.lora-tag b{color:#fff;font-weight:600}
.nav-btn{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:68px;border:none;background:rgba(255,255,255,.06);color:#fff;font-size:26px;cursor:pointer;border-radius:10px;z-index:3;display:flex;align-items:center;justify-content:center;transition:background .15s}
.nav-btn:hover{background:rgba(255,255,255,.18)}
.nav-btn.prev{left:10px}.nav-btn.next{right:10px}
.hidden{display:none !important}
/* ── 标签栏 ── */
.tabbtn{background:none;border:1px solid transparent;color:var(--dim);padding:5px 13px;
  border-radius:8px;cursor:pointer;font-size:12px;font-weight:600;font-family:inherit;
  white-space:nowrap;transition:all .15s}
.tabbtn:hover{color:var(--txt);background:rgba(255,255,255,.05)}
.tabbtn.active{color:#fff;background:var(--accent);border-color:var(--accent);box-shadow:0 0 14px #7c5cff55}

/* ── 星标（网格与相似度视图共用同一份 marks）── */
.cellbox.marked{outline:2px solid #ffd166;outline-offset:-2px}
.cellbox .mk{position:absolute;top:3px;right:3px;z-index:6;border:none;
  background:rgba(0,0,0,.6);color:#ffd166;font-size:13px;line-height:1;
  padding:3px 6px;border-radius:6px;cursor:pointer;opacity:0;transition:opacity .15s}
.cellbox:hover .mk{opacity:1}
.cellbox.marked .mk{opacity:1}
.cellbox .mk:hover{background:rgba(0,0,0,.85)}
.fbtn.fall{font-weight:700;opacity:.7;letter-spacing:normal}
.fbtn.fall.active{opacity:1;background:#3ddc9733;border-color:#3ddc9755;color:#7ff0c0}
@GEN_CSS@
@QUEUE_CSS@
/* ── 跨页签共享的基础类 ──────────────────────────────────────────────
   ⚠️ 这几个**必须留在内核**：任务队列页签（queue_tab.py）也在用
   （`.mono` 的数字、`.ok/.warn` 的状态色、`.bar` 的进度条）。
   2026-10-13 插件化时它们一度被搬进 plugins/analysis 的 CSS，
   结果**卸载插件就把队列页签的样式弄坏了** —— 正是「可卸载」要避免的。
   判断某条 CSS 属于谁：看它在**几个页签**里出现。≥2 个 → 内核。
   （内联 `class="..."` 之外还要查 JS 拼串设类名的写法，那次就是漏了这种。） */
.mono{font-family:SF Mono,Cascadia Code,Consolas,monospace}
.bar{height:9px;border-radius:5px;background:#1a1e38;overflow:hidden;min-width:70px}
.bar > i{display:block;height:100%;border-radius:5px;
  background:linear-gradient(90deg,var(--accent),var(--hot))}
td.ok,.ok{color:var(--ok)}
td.warn,.warn{color:#ffc46b}

@PLUGIN_CSS@
</style>
</head><body>

<div class="topbar">
  <span class="brand"><span class="dot"></span>LoRA 矩阵</span>
  <button class="tabbtn active" id="tabbtn-view" onclick="switchTab('view')">网格查看</button>
@PLUGIN_TABS@
  <button class="tabbtn" id="tabbtn-gen" onclick="switchTab('gen')">新建矩阵</button>
  <button class="tabbtn" id="tabbtn-queue" onclick="switchTab('queue')">任务队列</button>
  <span id="viewTools" style="display:flex;gap:10px;align-items:center;flex:1;min-width:0">
    <input type="text" id="pathInput" placeholder="矩阵目录（默认 ComfyUI 的 output/matrix）" />
    <button class="btn ghost" id="browseBtn" onclick="pickFolder()">📂 浏览</button>
    <button class="btn" onclick="loadTasks()">⟳ 加载</button>
    <select id="cuiSel" title="连的是哪台 ComfyUI（多开时在这里换）" onchange="cuiSwitch(this.value)"></select>
    <button class="btn ghost" id="quitBtn" onclick="quitApp()"
            title="关闭本工具本身。注意：关掉浏览器标签**不会**关掉它">⏻ 退出</button>
    <span id="taskInfo" style="font-size:11px;color:var(--dim);white-space:nowrap"></span>
  </span>
</div>

<div id="tab-view">
<div id="quickFolders" class="quickdirs"></div>
<div id="controlsArea" class="toolbar hidden">
  <div class="ctrl">
    <label>横轴</label><span class="axis-tag x">X</span>
    <select id="xSelect" onchange="onAxisChange()"></select>
  </div>
  <div class="ctrl">
    <label>纵轴</label><span class="axis-tag y">Y</span>
    <select id="ySelect" onchange="onAxisChange()"></select>
  </div>
  <div class="ctrl" id="facetCtrl" style="display:none">
    <label>分面</label><span class="axis-tag z">Z</span>
    <select id="facetSelect" onchange="onFacetChange()"></select>
  </div>
  <div class="ctrl">
    <label>布局</label>
    <button class="btn ghost" id="layoutBtn" onclick="toggleLayout()">切平铺</button>
  </div>
  <div class="ctrl">
    <label style="cursor:pointer;text-transform:none;display:flex;align-items:center;gap:6px">
      <input type="checkbox" id="onlyMarkedChk" onchange="setOnlyMarked(this.checked)" />
      只看标记
    </label>
    <span id="markCount" style="color:#ffd166;font-size:11px;white-space:nowrap"></span>
  </div>
  <div class="ctrl" style="margin-left:auto">
    <label>缩略图</label>
    <input type="range" id="thumbRange" min="24" max="420" step="4" value="150" oninput="setThumb(this.value)" />
  </div>
  <div class="ctrl">
    <label>缩放</label>
    <span id="zoomLabel" style="font-size:11px;color:var(--dim);min-width:42px;text-align:right">100%</span>
    <button class="btn ghost" onclick="fitView()" title="缩放到刚好放下整个矩阵">⌖ 适应</button>
    <button class="btn ghost" onclick="resetView()" title="回到 100% 并归位">1:1</button>
  </div>
</div>

<div id="filtersArea" class="filters hidden"></div>

<div class="grid-wrap">
  <div id="spinner" class="spinner hidden"></div>
  <div id="canvasWrap">
    <div id="grid">
      <div class="hint">选一个矩阵目录 —— 点上方<b>快捷目录</b>里的 <b>📁 output/matrix</b> 即可<br>默认目录 = ComfyUI 的 <b>output/matrix</b>，也可以直接把路径粘到输入框里回车</div>
    </div>
    <div id="fitHint" class="fit-hint hidden">内容超出画布 · <b>⌖ 适应</b> 缩到一屏，或滚轮缩小、<b>中键拖动</b>平移</div>
  </div>
</div>
</div><!-- /tab-view -->

@PLUGIN_BODY@
<div id="tab-gen" class="hidden">@GEN_BODY@</div>

<div id="tab-queue" class="hidden">@QUEUE_BODY@</div>

<div id="modal" class="overlay hidden" onclick="closeModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-left">
      <img id="modalImg" src="" />
      <button class="nav-btn prev hidden" id="modalPrev" onclick="navModal(-1)">‹</button>
      <button class="nav-btn next hidden" id="modalNext" onclick="navModal(1)">›</button>
    </div>
    <div class="modal-right" id="modalRight"></div>
  </div>
</div>

<script>
// ── 插件宿主接口 ───────────────────────────────────────────────────────
// 插件跑在自己的 IIFE 里，只能通过这个对象跟内核说话 ——
// 不去抓内核内部标识符（那些名字内核随时可以改）。
//
// ⚠️ marks 用 getter 不能用引用：内核在 loadMarks() 里会**整体重新赋值**
//    `marks = JSON.parse(localStorage...)`，插件手里攥着旧对象就会读到过期星标。
window.MLX = {
  api: api,
  escAttr: escAttr,
  escHtml: escHtml,
  openTask: openTask,
  switchTab: switchTab,
  getMarks: function(){ return marks },
  getFolder: function(){ return (document.getElementById('pathInput').value || '').trim() },

  tabs: [],                       // 内核 + 插件的全部页签，switchTab 遍历它
  _hooks: {},                     // {事件名: [回调]}

  // 插件页签元数据（server 按 plugin.json 注入）。
  // 用途：插件**因缺依赖没启用**时它的脚本不会注入，registerTab 也就跑不到，
  // 光靠自注册页签会凭空消失。先用这份元数据把页签立起来，内容是「未启用」提示。
  pluginMeta: @PLUGIN_TABMETA@,

  // 同一个 id 再注册一次 → 覆盖（插件脚本随后补上 onShow）
  registerTab: function(t){
    for (var i = 0; i < this.tabs.length; i++) {
      if (this.tabs[i].id === t.id) { this.tabs[i] = t; return }
    }
    this.tabs.push(t);
  },
  on: function(evt, fn){ (this._hooks[evt] = this._hooks[evt] || []).push(fn) },
  emit: function(evt){
    var a = this._hooks[evt] || [];
    for (var i = 0; i < a.length; i++) {
      try { a[i]() } catch (e) { console.error('[plugin] 钩子 ' + evt + ' 出错:', e) }
    }
  },
  // 插件把内联 onclick 要用的函数挂到全局
  expose: function(obj){ for (var k in obj) window[k] = obj[k] },
};

// ── 标签切换 ──
function switchTab(name){
  // 页签表由内核注册（view/gen/queue）+ 插件自注册（MLX.registerTab）拼成，
  // 这里不再硬编码 —— 加一个插件页签不需要动内核。
  MLX.tabs.forEach(function(t){
    var el = document.getElementById('tab-' + t.id);
    if (el) el.classList.toggle('hidden', t.id !== name);
    var btn = document.getElementById('tabbtn-' + t.id);
    if (btn) btn.classList.toggle('active', t.id === name);
    if (t.id === name && t.onShow) t.onShow();
  });
  document.getElementById('viewTools').style.display = (name === 'view') ? 'flex' : 'none';
  if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
  // ⚠️ 这里**不要**再调 genInit()/qInit() —— 上面 forEach 已经通过 onShow 调过了。
  //    早先两处都写，gen 因为有 genReady 守卫没露馅，queue 的 qInit 没有守卫，
  //    结果是每次切到队列页都发两遍 /api/run/status、还 clearInterval 重设一次轮询。
  // 切回网格页：离开期间画布是 display:none，量出来的高度是 0，必须重新量一遍
  if (name === 'view') { layoutGrid(); if (!viewTouched) fitView(); }
}
// 内核自带的三个页签。插件的由 plugin_loader 注入的脚本调 MLX.registerTab 追加。
MLX.tabs = [
  { id: 'view',  label: '网格查看' },
  { id: 'gen',   label: '新建矩阵', onShow: function(){ if (window.genInit) window.genInit() } },
  { id: 'queue', label: '任务队列', onShow: function(){ if (typeof qInit === 'function') qInit() } },
];
// 插件页签先按元数据登记（必须在本行之后 —— 上面那行会把 tabs 整个换掉）。
// 启用的插件稍后由自己的脚本 registerTab 覆盖补上 onShow；
// 没启用的就保持这样，页签在、内容是未启用提示。
MLX.pluginMeta.forEach(function(t){ MLX.registerTab(t) });
window.addEventListener('DOMContentLoaded', function(){
  var h = (location.hash || '').replace('#', '');
  // 白名单改成查页签表 —— 插件页签也能直接被 #sim 这种 hash 打开
  for (var i = 0; i < MLX.tabs.length; i++) {
    if (MLX.tabs[i].id === h) { switchTab(h); break }
  }
});

// ── State ──
var allTasks = [];
var allDims = {};      // {loraName: [strength values]}
var dimNames = [];     // ordered list of lora names
var currentData = null;
var filterState = {};  // {loraName: [选中的值]} —— 多选；非 X/Y 维度的过滤条件
var marks = {};        // {comboKey: true} —— 星标，存 localStorage，网格与相似度视图共享
var onlyMarked = false;// 只显示星标
var layoutMode = "grid";  // "grid" = X/Y 二维网格；"facet" = 再切一个维度做分面
var facetDim = null;      // facet 模式下当分面的维度名

// ── Init ──
document.addEventListener("DOMContentLoaded", function() {
  loadQuickFolders();      // 顶部那排快捷目录（并据 has_tk 决定藏不藏「浏览」按钮）
  cuiLoad();               // ComfyUI 实例选择器（多便携版并存时用）
  fetch("/api/config").then(r => r.json()).then(cfg => {
    if (cfg.last_folder) {
      document.getElementById("pathInput").value = cfg.last_folder;
      loadTasks();
    }
    if (cfg.thumb) {
      var r = document.getElementById("thumbRange");
      r.value = cfg.thumb;
      setThumb(cfg.thumb);
    }
  }).catch(function() {});
  document.getElementById("pathInput").addEventListener("keydown", function(e) {
    if (e.key === "Enter") loadTasks();
  });
  bindCanvas();
  observeGrid();    // 图片异步撑开布局时自动重新适应
  layoutGrid();     // 首屏就先把画布高度按实际窗口量好，避免第一次渲染就裁底
});

function setThumb(v) {
  document.documentElement.style.setProperty("--thumb", v + "px");
  saveConfig({thumb: parseInt(v, 10)});
  // 缩略图尺寸变了 = 整个布局都变了，之前手动调过的视角已经没有参照意义
  // → 清掉「用户动过」标记，重新适应。否则拖大滑块后内容溢出，底部一直是被裁的。
  viewTouched = false;
  fitWhenSettled();
}

function saveConfig(partial) {
  fetch("/api/save-config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(partial)
  }).catch(function() {});
}

// ── Folder picker ──
// ── 快捷目录 ────────────────────────────────────────────────────────────
// 工具要看的目录几乎总在 ComfyUI 的 output/matrix 下，直接列出来点选。
//
// 为什么不用文件夹对话框：**ComfyUI 便携版的 python_embeded 不含 tkinter**，
// 弹不出来；那个「📂 浏览」按钮在便携版下点了只会弹一句「请手填路径」——
// 对给别人用的工具来说不合格。所以没有 tkinter 时干脆把按钮藏掉（不留死按钮），
// 靠这里的候选目录覆盖绝大多数场景；路径还是可以手粘。
function loadQuickFolders(){
  api('GET','/api/matrix-folders').then(function(d){
    var box = document.getElementById('quickFolders');
    if (!box) return;
    var bb = document.getElementById('browseBtn');
    if (bb) bb.style.display = (d && d.has_tk) ? '' : 'none';

    var cur = document.getElementById('pathInput').value;
    var h = '';
    if (d && d.exists) {
      h += '<span class="qd-label">快捷目录</span>';
      h += qdChip(d.root, '📁 output/matrix', false, cur);
      (d.dirs || []).forEach(function(x){
        h += qdChip(x.path, x.name, !x.has_tasks, cur);
      });
    } else if (d && d.root) {
      h += '<span class="qd-label">找不到 ' + esc(d.root)
         + ' —— 先在 config.json 里配好 ComfyUI 路径</span>';
    }
    box.innerHTML = h;
  }).catch(function(){});   // 拿不到就不显示，不打扰
}

function qdChip(path, label, dim, cur){
  var on = (path === cur) ? ' on' : '';
  return '<span class="qd-chip' + (dim ? ' dim' : '') + on + '"'
       + ' title="' + escAttr(path) + '"'
       + ' onclick="pickQuick(' + escAttr(JSON.stringify(path)) + ')">'
       + esc(label) + '</span>';
}

function pickQuick(p){
  document.getElementById('pathInput').value = p;
  loadTasks();
}

function pickFolder() {
  fetch("/api/pick-folder").then(r => r.json()).then(function(data) {
    if (data.path) {
      document.getElementById("pathInput").value = data.path;
      loadTasks();
    } else if (data.has_tk === false) {
      // ComfyUI 便携版的 python_embeded 不含 tkinter —— 弹不出对话框
      alert("这个 Python 环境没装 tkinter，无法弹出文件夹选择框。\n\n"
          + "请直接把路径粘贴到输入框里，然后回车。");
      document.getElementById("pathInput").focus();
    }
  }).catch(function(err) {
    console.warn("pick-folder 失败，请在输入框内直接粘贴路径", err);
    document.getElementById("pathInput").focus();
  });
}

// ── 退出工具 ──────────────────────────────────────────────────────────
// exe 是 --windowed（没有黑框框），所以「关掉浏览器标签」**不会**关掉工具 ——
// 进程还在后台占着端口，再双击一次就变成两个实例。这里给一条明确的路。
function quitApp(){
  if (!confirm('关闭「LoRA 矩阵测试台」？\n\n'
             + '注意：关掉浏览器标签不会关掉它，得点这里。')) return;
  var btn = document.getElementById('quitBtn');
  if (btn){ btn.disabled = true; btn.textContent = '正在关闭…'; }
  api('POST', '/api/quit', {}).then(function(d){
    if (!d || !d.ok){
      // 唯一的正常失败是「不是由 matrix_viewer 启动的」（开发时直接跑 server）
      if (btn){ btn.disabled = false; btn.textContent = '⏻ 退出'; }
      alert('退出失败：' + ((d && d.error) || '未知错误')
          + '\n\n也可以在任务管理器里结束 MatrixLoRATest.exe');
      return;
    }
    // 已回响应、后端正在关停 —— 这页不会再连上，直接换成告别文案
    document.body.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;'
      + 'height:100vh;flex-direction:column;gap:16px;color:var(--dim);font-size:15px">'
      + '<div style="font-size:36px">👋</div>'
      + '<div>工具已关闭，这个标签页可以关掉了</div></div>';
  });
}

// ── ComfyUI 实例选择器 ────────────────────────────────────────────────
// 多便携版并存时，端口是唯一的区分依据。这里把扫到的都列出来，
// 每项带上**那台自报的路径** —— 否则两个 `127.0.0.1:81xx` 用户分不清谁是谁。
var CUI = { cur: '', list: [] };

function cuiLoad(){
  var sel = document.getElementById('cuiSel');
  if (!sel) return;
  api('GET', '/api/comfyui').then(function(d){
    if (!d || !d.ok) return;
    CUI.cur = d.current || '';
    CUI.list = d.instances || [];
    var MANUAL = '<option value="__manual__">＋ 手动填地址…</option>';
    if (!CUI.list.length){
      // 扫不到不等于没有 —— ComfyUI 可能跑在 `--port 9000` 这种非默认端口上
      sel.innerHTML = '<option value="">未找到 ComfyUI</option>' +
                      '<option value="__manual__">＋ 手动填地址…</option>';
      sel.className = 'off';
      sel.title = '默认端口（8188-8199）上没扫到 ComfyUI。\n'
                + '先确认它在跑；如果它用了别的端口，选「手动填地址」。';
      return;
    }
    sel.innerHTML = CUI.list.map(function(it){
      var label = String(it.url).replace(/^https?:\/\//, '') +
                  (it.dir ? '   ' + it.dir : '   （未自报路径）');
      return '<option value="' + escAttr(it.url) + '"' +
             (it.url === CUI.cur ? ' selected' : '') + '>' + esc(label) + '</option>';
    }).join('') + MANUAL;
    sel.className = '';
    sel.title = '连的是哪台 ComfyUI。多开时在这里换（换完会自动重新加载）。'
              + (d.locked_by_env ? '\n⚠ 环境变量 COMFYUI_URL 正覆盖着配置，这里的切换不会生效。' : '');
  });
}

function cuiSwitch(url){
  if (url === '__manual__'){
    // 扫描只覆盖默认端口段；跑在别的端口就手填
    var v = prompt('ComfyUI 地址（形如 http://127.0.0.1:9000）：',
                   CUI.cur || 'http://127.0.0.1:8188');
    if (!v){ cuiLoad(); return }
    url = v.trim();
  }
  if (!url || url === CUI.cur){ cuiLoad(); return }
  var sel = document.getElementById('cuiSel');
  if (sel) sel.className = 'busy';
  api('POST', '/api/comfyui', { url: url }).then(function(d){
    if (sel) sel.className = '';
    if (!d || !d.ok){ alert('切换失败：' + ((d && d.error) || '未知错误')); cuiLoad(); return; }
    CUI.cur = d.current;
    toast('已切到 ' + d.current + (d.warn ? '（' + d.warn + '）' : ''));
    loadTasks();      // 换实例 = 换 output 目录 → 重新加载
    cuiLoad();
  });
}

// ── Load ──
function loadTasks() {
  var folder = document.getElementById("pathInput").value.trim();
  if (!folder) return;
  var sp = document.getElementById("spinner");
  var grid = document.getElementById("grid");
  sp.classList.remove("hidden");
  grid.innerHTML = "";
  resetView();     // 清空网格时把视图也归零 —— 否则 #grid 会带着上一次的
                   // transform（平移/缩放）渲染新内容，文字被画布裁掉
  document.getElementById("taskInfo").textContent = "加载中…";
  saveConfig({last_folder: folder});

  fetch("/api/tasks?folder=" + encodeURIComponent(folder))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      sp.classList.add("hidden");
      allTasks = data.tasks || [];
      allDims = data.dimensions || {};
      dimNames = Object.keys(allDims);
      filterState = {};
      facetDim = null;             // 换目录后分面维度要重选
      loadMarks();                 // 星标跨目录持久（存 localStorage）
      currentData = {tasks: allTasks, dims: allDims, dimNames: dimNames};

      var shown = data.folder || folder;
      if (data.folder && data.folder !== folder) {
        document.getElementById("pathInput").value = data.folder;
      }
      var withImg = allTasks.filter(function(t) { return (t._images || []).length; }).length;
      document.getElementById("taskInfo").textContent =
        dimNames.length + " 维 · " + withImg + "/" + allTasks.length + " 张 · " +
        shown.replace(/\\/g, "/").split("/").slice(-2).join("/");

      if (!dimNames.length) {
        document.getElementById("controlsArea").classList.add("hidden");
        document.getElementById("filtersArea").classList.add("hidden");
        grid.innerHTML = '<div class="hint">这个目录里没有找到 task.json<br><span style="color:var(--dim-2)">' + escHtml(shown) + '</span></div>';
        // 这条路径**不走 applyView**，所以必须显式归零视图：
        // 否则 #grid 保留着上一次看有内容矩阵时的 translate/scale，
        // 提示文字会带着旧变换渲染，被画布从中间裁掉（用户截图反馈过）。
        resetView();
        return;
      }
      initControls();
      renderFilters();
      renderGrid();
      layoutGrid();
      applyView();
      // 等图片撑开布局后：先按实际高度重设画布，再适应 —— 243 张也能一屏看全。
      // 顺序不能反：fitView 读的 clientHeight 由 layoutGrid 决定。
      setTimeout(function(){ layoutGrid(); fitView(); }, 70);
      // 目录加载完 —— 插件页签自己决定要不要补算
      MLX.emit('folder-loaded');
    })
    .catch(function(err) {
      sp.classList.add("hidden");
      // 浏览器的原始文案是英文 "Failed to fetch"，而且不说该怎么办 ——
      // 这通常意味着查看器服务被重启/关掉了（改了代码重启、或手动关的），
      // 页面还是旧的那一份，所以请求全失败。给一句能照做的中文。
      var raw = (err && err.message) || String(err);
      var down = /Failed to fetch|NetworkError|load failed/i.test(raw);
      // 两种原因要分开说 —— 之前只写「刷新即可」，可服务真被关掉时刷新多少次都一样，
      // 用户会卡在一个没有出口的循环里（实测撞到过）。
      grid.innerHTML = '<div class="hint" style="color:var(--hot)">'
        + (down
           ? '连不上查看器服务<br><span style="color:var(--dim)">'
             + '① 它刚被重启 → 按 <b>Ctrl+R</b> 刷新即可<br>'
             + '② 它已经被关掉 → 刷新也没用，得重新运行 <b>matrix_viewer.py</b></span>'
           : '加载失败：' + escHtml(raw))
        + '</div>';
      resetView();
    });
}

// ── Controls ──
function initControls() {
  document.getElementById("controlsArea").classList.remove("hidden");
  var xSel = document.getElementById("xSelect");
  var ySel = document.getElementById("ySelect");
  xSel.innerHTML = "";
  ySel.innerHTML = "";
  dimNames.forEach(function(name, i) {
    xSel.innerHTML += '<option value="' + escAttr(name) + '"' + (i === 0 ? ' selected' : '') + '>' + escHtml(name) + '</option>';
    var yDef = (dimNames.length > 1 ? i === 1 : i === 0);
    ySel.innerHTML += '<option value="' + escAttr(name) + '"' + (yDef ? ' selected' : '') + '>' + escHtml(name) + '</option>';
  });
  fixAxisConflict();
}

function fixAxisConflict() {
  var xSel = document.getElementById("xSelect");
  var ySel = document.getElementById("ySelect");
  if (xSel.value === ySel.value && dimNames.length > 1) {
    var idx = dimNames.indexOf(ySel.value);
    ySel.value = dimNames[(idx + 1) % dimNames.length];
  }
}

function onAxisChange() {
  fixAxisConflict();
  initFacetSelect();
  renderFilters();
  renderGrid();
}

// ── 布局：网格 / 平铺（facet = 再切一个维度铺开）──
function toggleLayout() {
  layoutMode = (layoutMode === "grid") ? "facet" : "grid";
  if (layoutMode === "facet" && !facetDim) {
    var x = document.getElementById("xSelect").value;
    var y = document.getElementById("ySelect").value;
    for (var i = 0; i < dimNames.length; i++) {
      if (dimNames[i] !== x && dimNames[i] !== y) { facetDim = dimNames[i]; break }
    }
    if (!facetDim) { layoutMode = "grid"; alert("至少要有 3 个维度才能平铺"); return }
  }
  document.getElementById("facetCtrl").style.display = (layoutMode === "facet") ? "flex" : "none";
  document.getElementById("layoutBtn").textContent = (layoutMode === "facet") ? "切网格" : "切平铺";
  initFacetSelect();
  renderFilters();
  renderGrid();
}

function initFacetSelect() {
  var sel = document.getElementById("facetSelect");
  if (!sel) return;
  var x = document.getElementById("xSelect").value;
  var y = document.getElementById("ySelect").value;
  var opts = dimNames.filter(function(n) { return n !== x && n !== y });
  if (opts.indexOf(facetDim) < 0) facetDim = opts[0] || null;
  sel.innerHTML = "";
  opts.forEach(function(n) {
    sel.innerHTML += '<option value="' + escAttr(n) + '"' +
      (n === facetDim ? ' selected' : '') + '>' + escHtml(n) + '</option>';
  });
  if (facetDim) sel.value = facetDim;
}

function onFacetChange() {
  facetDim = document.getElementById("facetSelect").value;
  renderFilters();
  renderGrid();
}

// ── Filters（状态存 filterState，不读 DOM）──
// ── 标记（星标）── 存 localStorage，网格与相似度视图共享同一份
function markKey(t) { return (t && (t._combo_dir || t.组合文件夹)) || "" }

function loadMarks() {
  try { marks = JSON.parse(localStorage.getItem("mx_marks") || "{}") || {} }
  catch (e) { marks = {} }
}
function saveMarks() {
  try { localStorage.setItem("mx_marks", JSON.stringify(marks)) } catch (e) {}
}
function toggleMark(ev, key) {
  if (ev) { ev.stopPropagation(); ev.preventDefault() }   // 别触发格子的 openCell
  if (!key) return;
  if (marks[key]) delete marks[key]; else marks[key] = true;
  saveMarks();
  renderGrid();
  // 星标变了 —— 插件页签自己监听（原先是内核替 sim 操心）
  MLX.emit('marks-changed');
}
function setOnlyMarked(on) {
  onlyMarked = !!on;
  renderGrid();
}

// 浮点相等 —— 强度值可能是 0.3333 这种，不能直接 ===
function valEq(a, b) { return Math.abs(a - b) < 0.0001 }
function valIn(v, arr) {
  for (var i = 0; i < arr.length; i++) if (valEq(arr[i], v)) return true;
  return false;
}

function renderFilters() {
  var area = document.getElementById("filtersArea");
  var xLora = document.getElementById("xSelect").value;
  var yLora = document.getElementById("ySelect").value;
  // facet 模式下分面维度也退出过滤条 —— 它已经用另一种方式展示了
  var skip = {};
  skip[xLora] = 1; skip[yLora] = 1;
  if (layoutMode === "facet" && facetDim) skip[facetDim] = 1;

  var html = "";
  dimNames.forEach(function(name) {
    if (skip[name]) return;
    var vals = allDims[name] || [];
    if (!vals.length) return;
    // 首次遇到：默认只选第一个值，保持原有「锁定一个切片」的行为
    if (!Array.isArray(filterState[name]) || !filterState[name].length) {
      filterState[name] = [vals[0]];
    }
    var cur = filterState[name];
    var allOn = cur.length === vals.length;
    html += '<div class="fgroup" data-lora="' + escAttr(name) + '">';
    html += '<span class="flabel" title="' + escAttr(name) + '">' + escHtml(name) + '</span>';
    vals.forEach(function(v) {
      html += '<button class="fbtn' + (valIn(v, cur) ? ' active' : '') + '" onclick="toggleFilter(\'' +
              escAttr(name) + '\',' + v + ')">' + formatStrength(v) + '</button>';
    });
    html += '<button class="fbtn fall' + (allOn ? ' active' : '') + '" title="这一维不过滤（显示全部）" ' +
            'onclick="filterAll(\'' + escAttr(name) + '\')">全</button>';
    html += '</div>';
  });
  area.innerHTML = html;
  area.classList.toggle("hidden", html === "");
}

function toggleFilter(name, value) {
  var cur = filterState[name] || [];
  var idx = -1;
  for (var i = 0; i < cur.length; i++) if (valEq(cur[i], value)) { idx = i; break }
  if (idx >= 0) {
    if (cur.length === 1) return;   // 至少留一个 —— 整维消失会让用户困惑
    cur.splice(idx, 1);
  } else {
    cur.push(value);
  }
  filterState[name] = cur;
  renderFilters();
  renderGrid();
}

function filterAll(name) {
  filterState[name] = (allDims[name] || []).slice();   // 全选 = 这一维不过滤
  renderFilters();
  renderGrid();
}

function currentFilters() {
  var xLora = document.getElementById("xSelect").value;
  var yLora = document.getElementById("ySelect").value;
  var skip = {};
  skip[xLora] = 1; skip[yLora] = 1;
  if (layoutMode === "facet" && facetDim) skip[facetDim] = 1;
  var f = {};
  dimNames.forEach(function(name) {
    if (skip[name]) return;
    var cur = filterState[name];
    // 全选等价于不过滤 —— 跳过能让 lookup 更快，也让「+N」不误报
    if (Array.isArray(cur) && cur.length && cur.length < (allDims[name] || []).length) {
      f[name] = cur;
    }
  });
  return f;
}

// 按当前 X/Y + 过滤条件构建 "x|y" -> [task,...] 索引（多值过滤后同一格可能落多个 task）
function buildLookup(xLora, yLora) {
  var filters = currentFilters();
  var lookup = {};
  allTasks.forEach(function(t) {
    var coords = t.坐标 || {};
    for (var k in filters) {
      if (coords[k] === undefined) return;
      if (!valIn(coords[k], filters[k])) return;
    }
    if (onlyMarked && !marks[markKey(t)]) return;
    var xv = coords[xLora], yv = coords[yLora];
    if (xv === undefined || yv === undefined) return;
    var kk = xv + "|" + yv;
    (lookup[kk] = lookup[kk] || []).push(t);
  });
  return lookup;
}

// 单个格子的内容 —— 网格与平铺共用
function cellHtml(group, xv, yv) {
  var t = group[0];
  var imgs = (t && t._images) || [];
  if (!imgs.length) return '<span class="ph">—</span>';
  var key = markKey(t);
  var isBase = /^baseline$/i.test(t._combo_dir || "");
  var extra = (group.length - 1) + (imgs.length - 1);   // 重叠组合数 + 同组合多图
  var h = '<div class="cellbox' + (isBase ? ' base' : '') + (marks[key] ? ' marked' : '') + '" ' +
          'data-key="' + escAttr(key) + '" data-col="' + escAttr(String(xv)) + '" ' +
          'data-row="' + escAttr(String(yv)) + '" onclick="openTask(\'' + escAttr(key) + '\')">';
  h += '<img src="' + escAttr(imgs[0]) + '" loading="lazy" />';
  if (extra > 0) h += '<span class="badge">+' + extra + '</span>';
  else if (isBase) h += '<span class="badge">基线</span>';
  h += '<button class="mk" title="标记 / 取消标记" onclick="toggleMark(event,\'' +
       escAttr(key) + '\')">' + (marks[key] ? '★' : '☆') + '</button>';
  h += '</div>';
  return h;
}

function updateMarkCount() {
  var n = 0;
  for (var k in marks) if (marks[k]) n++;
  var el = document.getElementById("markCount");
  if (el) el.textContent = n ? ('★ ' + n) : '';
}


window.addEventListener('resize', function(){
  // 网格页：先按新窗口高度重新量画布，用户没手动调过视角就顺带重新适应
  layoutFacet();     // 分面模式下列数会随可用宽度变
  layoutGrid();
  var gridTab = document.getElementById('tab-view');
  if (gridTab && !gridTab.classList.contains('hidden') && !viewTouched) fitView();
  // 插件页签自己决定要不要按新尺寸重画（原先这里直接 simDraw()，是内核替插件操心）
  MLX.emit('resize');
});

// 画一个二维网格表（供 renderGrid 与 renderFacet 复用）
function gridTableHtml(lookup, xVals, yVals, xLora, yLora) {
  var html = '<table class="grid-table"><thead><tr>';
  // 角落格用紧凑符号，轴名在工具栏已有 —— 长标题会把第一列撑很宽
  html += '<th class="corner" style="left:0" title="' + escAttr(yLora + ' ↓  /  ' + xLora + ' →') + '">↘</th>';
  xVals.forEach(function(xv) {
    html += '<th data-col="' + escAttr(String(xv)) + '">' + formatStrength(xv) + '</th>';
  });
  html += '</tr></thead><tbody>';
  for (var yi = yVals.length - 1; yi >= 0; yi--) {
    var yv = yVals[yi];
    html += '<tr><th data-row="' + escAttr(String(yv)) + '">' + formatStrength(yv) + '</th>';
    xVals.forEach(function(xv) {
      var group = lookup[xv + "|" + yv] || [];
      html += '<td data-col="' + escAttr(String(xv)) + '" data-row="' + escAttr(String(yv)) + '">';
      html += cellHtml(group, xv, yv);
      html += '</td>';
    });
    html += '</tr>';
  }
  return html + '</tbody></table>';
}

function bindCrosshair(root) {
  root.querySelectorAll('td[data-col]').forEach(function(td) {
    td.addEventListener("mouseenter", function() {
      var c = td.getAttribute("data-col"), r = td.getAttribute("data-row");
      root.querySelectorAll('[data-col="' + CSS.escape(c) + '"]').forEach(function(e) { e.classList.add("cross"); });
      root.querySelectorAll('[data-row="' + CSS.escape(r) + '"]').forEach(function(e) { e.classList.add("cross"); });
    });
    td.addEventListener("mouseleave", function() {
      root.querySelectorAll(".cross").forEach(function(e) { e.classList.remove("cross"); });
    });
  });
}

// ── 画布视图：滚轮缩放 + 拖拽平移（像 CAD / 白板）──
var view = {k: 1, x: 0, y: 0};
// 用户是否手动动过视图（缩放/平移）。动过之后窗口 resize 就不再强制重新适应，
// 免得把刚对准的视角冲掉。
var viewTouched = false;
var panning = null;

function applyView(){
  var g = document.getElementById("grid");
  if (!g) return;
  g.style.transform = "translate(" + view.x + "px," + view.y + "px) scale(" + view.k + ")";
  var el = document.getElementById("zoomLabel");
  if (el) el.textContent = Math.round(view.k * 100) + "%";
  updateFitHint();
}

// 内容超出画布 → 亮角标告诉用户出口。transform 缩放不产生滚动条，
// 溢出部分被 overflow:hidden 直接裁掉，不给提示用户只会觉得「下面被遮挡了」。
function updateFitHint(){
  var g = document.getElementById("grid"), wrap = document.getElementById("canvasWrap");
  var h = document.getElementById("fitHint");
  if (!g || !wrap || !h || !wrap.clientWidth || !wrap.clientHeight) return;
  // 没有格子就没有「超出画布」可言。空状态（没找到 task.json / 加载失败）时角标必须消失 ——
  // 这条路径**不会**调 applyView，没人去关它，就会把上一次的状态残留下来压在空画布上。
  var empty = !g.querySelector(".cellbox");
  wrap.classList.toggle("empty", empty);   // 空状态让提示居中（见 CSS）
  if (empty) { h.classList.add("hidden"); return }
  var over = g.scrollWidth * view.k > wrap.clientWidth + 1 ||
             g.scrollHeight * view.k > wrap.clientHeight + 1;
  h.classList.toggle("hidden", !over);
}

function zoomAt(cx, cy, factor){
  var k2 = Math.min(6, Math.max(0.03, view.k * factor));
  if (k2 === view.k) return;
  viewTouched = true;
  // 让鼠标指的那个点在缩放前后停在原地（CAD 手感的关键）
  view.x = cx - (cx - view.x) * (k2 / view.k);
  view.y = cy - (cy - view.y) * (k2 / view.k);
  view.k = k2;
  applyView();
}

function resetView(){ view = {k: 1, x: 0, y: 0}; viewTouched = true; applyView() }

// 画布可用高度 = 窗口高度 − 画布容器距顶部的位置 − 一点底边留白。
// 原来 CSS 里直接写 calc(100vh - 175px)：175 是估的，矮窗口下白剩几十像素，
// 而且一旦估少了就会把底部内容裁掉（.grid-wrap 是 overflow:hidden，没有滚动条）。
// 改成量出来的实际位置，多高用多高。必须在 fitView() 之前调 —— fitView 读的
// clientHeight 就是这里定下来的。
function layoutGrid(){
  var wrap = document.querySelector('.grid-wrap');
  if (!wrap) return;
  var top = wrap.getBoundingClientRect().top + window.pageYOffset;
  // ⚠️ 设 height，**不是 maxHeight** —— 见 .grid-wrap 那条注释，改错会让画布缩成一小块
  wrap.style.height = Math.max(180, window.innerHeight - top - 12) + 'px';
}

function fitView(){
  var g = document.getElementById("grid"), wrap = document.getElementById("canvasWrap");
  if (!g || !wrap) return;
  // 空状态（没有格子）**不缩放** —— 那时 grid 里只有一行提示文字，
  // 「把它缩放到刚好放下」算出来的倍率可能很大（画布相对提示很高时，
  // k 能顶到 6 的上限），文字被放大到超出画布反被裁掉。原始尺寸最合适。
  if (!g.querySelector(".cellbox")) { resetView(); return }
  var w = wrap.clientWidth, h = wrap.clientHeight;
  var gw = g.scrollWidth, gh = g.scrollHeight;
  if (!gw || !gh || !w || !h) return;
  view.k = Math.max(0.03, Math.min(6, Math.min((w - 26) / gw, (h - 26) / gh)));
  view.x = (w - gw * view.k) / 2;
  view.y = (h - gh * view.k) / 2;
  viewTouched = false;      // 适应之后又回到「自动」状态
  applyView();
}

// 图片是**异步**撑开布局的：renderGrid() 那一刻 <img> 还没有尺寸，表格量出来偏小，
// 此时 fitView() 算出的缩放不对（极端情况 g.scrollHeight 为 0 会直接 return），
// 等图片陆续加载完，网格就撑出画布 —— 底排看不见。
// 所以盯住网格的**真实尺寸变化**，一变就重新量画布并适应（防抖 60ms）。
// ResizeObserver 看的是布局尺寸，fitView 改的是 transform（不影响布局）→ 不会自激。
var _fitTimer = null;

function fitWhenSettled(){
  if (viewTouched) return;          // 用户手动缩放过就别打扰
  var vt = document.getElementById("tab-view");
  if (vt && vt.classList.contains("hidden")) return;   // 不在网格页，量出来是 0
  clearTimeout(_fitTimer);
  // layoutFacet 也放这儿：缩略图尺寸一变，分面轨道的宽度要跟着重量（它本身幂等，
  // 量出来一样就设一样的值，不会自激）
  _fitTimer = setTimeout(function(){ layoutFacet(); layoutGrid(); fitView(); }, 60);
}

function observeGrid(){
  var g = document.getElementById("grid");
  if (!g || g._ro || typeof ResizeObserver === "undefined") return;
  g._ro = new ResizeObserver(fitWhenSettled);
  g._ro.observe(g);
}

function bindCanvas(){
  var wrap = document.getElementById("canvasWrap");
  if (!wrap || wrap._bound) return;
  wrap._bound = true;

  wrap.addEventListener("wheel", function(e){
    e.preventDefault();
    var r = wrap.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.14 : 1 / 1.14);
  }, {passive: false});

  // 中键拖动平移（CAD/Blender 的习惯）—— 左键留给「点击开弹窗」，两者不打架
  wrap.addEventListener("mousedown", function(e){
    if (e.button !== 1) return;      // 1 = 中键
    e.preventDefault();              // 同时挡掉中键的自动滚动
    var origin = {x: e.clientX - view.x, y: e.clientY - view.y};
    panning = true;
    wrap.classList.add("dragging");

    function onMove(ev){
      view.x = ev.clientX - origin.x;
      view.y = ev.clientY - origin.y;
      applyView();
    }
    function onUp(){
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      panning = null;
      wrap.classList.remove("dragging");
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
  // 有些浏览器中键抬起还会派发 auxclick / 触发自动滚动，一并拦掉
  wrap.addEventListener("auxclick", function(e){ if (e.button === 1) e.preventDefault() });
  // 键盘：0 = 适应屏幕，1 = 回到 1:1
  document.addEventListener("keydown", function(e){
    var t = e.target.tagName;
    if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
    if (e.key === "0") fitView();
    else if (e.key === "1") resetView();
  });
}

// ── Grid ──
function renderGrid() {
  updateMarkCount();
  if (layoutMode === "facet" && facetDim) return renderFacet();

  var grid = document.getElementById("grid");
  var xLora = document.getElementById("xSelect").value;
  var yLora = document.getElementById("ySelect").value;
  var xVals = allDims[xLora] || [];
  var yVals = allDims[yLora] || [];
  grid.innerHTML = gridTableHtml(buildLookup(xLora, yLora), xVals, yVals, xLora, yLora);
  bindCrosshair(grid);
}

// ── Facet 平铺：把分面维度铺成一排小网格 ──
function renderFacet() {
  var grid = document.getElementById("grid");
  var xLora = document.getElementById("xSelect").value;
  var yLora = document.getElementById("ySelect").value;
  var xVals = allDims[xLora] || [];
  var yVals = allDims[yLora] || [];
  var fVals = allDims[facetDim] || [];
  if (!fVals.length || !xVals.length || !yVals.length) {
    grid.innerHTML = '<div class="hint">这个组合没法平铺（缺少维度值）</div>';
    return;
  }
  var lookup = buildLookup(xLora, yLora);

  var html = '<div class="facet-grid">';
  fVals.forEach(function(fv) {
    html += '<div class="facet-cell">';
    html += '<div class="facet-title">' + escHtml(facetDim) + ' = ' + formatStrength(fv) + '</div>';
    // 只保留分面维度 = fv 的格子
    var sub = {};
    for (var k in lookup) {
      var keep = lookup[k].filter(function(t) {
        var v = (t.坐标 || {})[facetDim];
        return v !== undefined && valEq(v, fv);
      });
      if (keep.length) sub[k] = keep;
    }
    html += gridTableHtml(sub, xVals, yVals, xLora, yLora);
    html += '</div>';
  });
  html += '</div>';
  grid.innerHTML = html;
  bindCrosshair(grid);
  layoutFacet();
}

// 分面格子的轨道宽度必须**按内容真实宽度钉死**。
//
// 原来 CSS 是 `repeat(auto-fit, minmax(320px, max-content))`：轨道宽度被 320px 那个
// 下限主导，实测每个格子只分到 447px，而格子里那张 3 列缩略图要 891px —— 内容溢出
// 格子，相邻分面直接叠在一起。`--thumb` 越大越明显（作者配置里是 268px，必现）。
// auto-fit / max-content / width:max-content / flex-wrap 各种写法都在真机上量过，
// 要么照旧溢出，要么每行只放得下 1 个、缩到 12% 看不清楚。所以改成量出来再定。
//
// 列数按「适应后缩放最大」挑：一行铺开几乎总是赢（正是「一次看 N 个维度」的意图），
// 分面很多时会自动退化成多行，不至于缩到肉眼不可见。
var FACET_GAP = 18;

function layoutFacet(){
  var fg = document.querySelector('.facet-grid');
  var wrap = document.getElementById('canvasWrap');
  if (!fg || !wrap) return;
  var cells = fg.querySelectorAll('.facet-cell');
  var n = cells.length;
  if (!n) return;

  // 内容真实尺寸：表格宽 + 格子左右内边距；高度 = 标题 + 表格 + 上下内边距
  var cw = 0, ch = 0;
  cells.forEach(function(c){
    var t = c.querySelector('table.grid-table');
    if (!t) return;
    var cs = getComputedStyle(c);
    var pl = parseFloat(cs.paddingLeft) || 0, pr = parseFloat(cs.paddingRight) || 0;
    var pt = parseFloat(cs.paddingTop) || 0, pb = parseFloat(cs.paddingBottom) || 0;
    var title = c.querySelector('.facet-title');
    cw = Math.max(cw, t.offsetWidth + pl + pr);
    ch = Math.max(ch, t.offsetHeight + (title ? title.offsetHeight + 7 : 0) + pt + pb);
  });
  if (cw <= 0 || ch <= 0) return;

  // 挑列数：让 fitView 之后的缩放最大。#grid 有 20px padding，算进去。
  var PAD = 40;
  var availW = wrap.clientWidth, availH = wrap.clientHeight;
  var best = 1, bestScore = -1;
  for (var cols = 1; cols <= n; cols++) {
    var rows = Math.ceil(n / cols);
    var W = cols * cw + (cols - 1) * FACET_GAP + PAD;
    var H = rows * ch + (rows - 1) * FACET_GAP + PAD;
    var score = Math.min(availW / W, availH / H);
    if (score > bestScore + 1e-9) { bestScore = score; best = cols }
  }
  fg.style.gridTemplateColumns = 'repeat(' + best + ', ' + Math.ceil(cw) + 'px)';
}

// ── Modal ──
var modalTasks = [];
var modalIdx = 0;

// 按组合键直接打开 —— 比原来的「按坐标反搜」更准更快，
// 也顺带修了 filters 改多选后 Math.abs(coords[k] - [数组]) 变 NaN 的问题
function openTask(key) {
  var task = null;
  for (var i = 0; i < allTasks.length; i++) {
    if (markKey(allTasks[i]) === key) { task = allTasks[i]; break }
  }
  if (!task || !(task._images || []).length) return;
  modalTasks = task._images;
  modalIdx = 0;
  showModal(0, task);
  document.getElementById("modal").classList.remove("hidden");
}

function showModal(idx, task) {
  var total = modalTasks.length;
  var imgPath = modalTasks[idx];
  var actualPath = decodeURIComponent(imgPath.split("?path=")[1] || "");
  document.getElementById("modalImg").src = imgPath;
  document.getElementById("modalPrev").classList.toggle("hidden", idx <= 0 || total <= 1);
  document.getElementById("modalNext").classList.toggle("hidden", idx >= total - 1 || total <= 1);

  if (!task) {
    allTasks.forEach(function(t) { if ((t._images || []).indexOf(imgPath) >= 0) task = t; });
  }

  var right = document.getElementById("modalRight");
  var h = '';
  h += '<div style="font-size:11px;color:var(--dim);margin-bottom:12px">第 ' + (idx + 1) + ' / ' + total + ' 张</div>';

  if (task) {
    var isBase = /^baseline$/i.test(task._combo_dir || "");
    if (isBase) h += '<div style="display:inline-block;background:#3ddc9722;border:1px solid #3ddc9755;color:#7ff0c0;border-radius:20px;padding:3px 11px;font-size:10.5px;margin-bottom:12px">对照基线（不含被测 LoRA）</div>';

    h += '<h3>各 LoRA 强度</h3>';
    var coords = task.坐标 || {};
    Object.keys(coords).forEach(function(k) {
      var v = coords[k];
      var on = Math.abs(v) > 0.0001;
      h += '<div class="row"><span class="lbl">' + escHtml(k) + '</span><span class="val" style="' +
           (on ? 'color:#c0b0ff;font-weight:600' : 'color:var(--dim-2)') + '">' +
           formatStrength(v) + (on ? '' : '  <span style="font-weight:400;color:var(--dim-2)">(未启用)</span>') +
           '</span></div>';
    });

    h += '<h3>模型参数</h3>';
    h += '<div class="row"><span class="lbl">Steps</span><span class="val">' + (task.steps != null ? task.steps : '?') + '</span></div>';
    h += '<div class="row"><span class="lbl">CFG</span><span class="val">' + (task.cfg != null ? task.cfg : '?') + '</span></div>';
    h += '<div class="row"><span class="lbl">Seed</span><span class="val">' + (task.seed != null ? task.seed : extractSeed(actualPath)) + '</span></div>';
    var sz = task.尺寸 || {};
    h += '<div class="row"><span class="lbl">尺寸</span><span class="val">' + (sz.宽 || '?') + ' × ' + (sz.高 || '?') + '</span></div>';

    var loras = task.loras || [];
    if (loras.length) {
      h += '<h3>实际加载</h3>';
      h += loras.map(function(l) {
        return '<span class="lora-tag">' + escHtml(l.name) + ' <b>' + l.strength + '</b></span>';
      }).join('');
    }

    h += '<h3>正面提示词</h3><div class="prompt">' + escHtml(task.正面 || "") + '</div>';
    h += '<h3>负面提示词</h3><div class="prompt neg">' + escHtml(task.负面 || "") + '</div>';
  }
  right.innerHTML = h;

  // PNG 内嵌元数据（交叉验证）
  fetch("/api/metadata?path=" + encodeURIComponent(actualPath))
    .then(function(r) { return r.json(); })
    .then(function(meta) {
      var png = meta.png;
      if (!png) return;
      var extra = '';
      if (png.loras && png.loras.length) {
        extra += '<h3>PNG 内嵌 LoRA</h3>';
        extra += png.loras.map(function(l) {
          return '<span class="lora-tag">' + escHtml(l.name) + ' <b>' + l.strength + '</b></span>';
        }).join('');
      }
      if (png.model) extra += '<div class="row" style="margin-top:8px"><span class="lbl">Model</span><span class="val">' + escHtml(png.model) + '</span></div>';
      if (png.sampler) extra += '<div class="row"><span class="lbl">Sampler</span><span class="val">' + escHtml(png.sampler) + (png.scheduler ? ' / ' + escHtml(png.scheduler) : '') + '</span></div>';
      right.innerHTML += extra;
    })
    .catch(function() {});
}

function navModal(delta) {
  var n = modalIdx + delta;
  if (n < 0 || n >= modalTasks.length) return;
  modalIdx = n;
  showModal(n);
}

function closeModal(e) {
  if (e.target === document.getElementById("modal")) {
    document.getElementById("modal").classList.add("hidden");
  }
}
document.addEventListener("keydown", function(e) {
  if (!document.getElementById("modal").classList.contains("hidden")) {
    if (e.key === "Escape") document.getElementById("modal").classList.add("hidden");
    if (e.key === "ArrowLeft") navModal(-1);
    if (e.key === "ArrowRight") navModal(1);
  }
});

// ── Helpers ──
function formatStrength(v) {
  if (v === 0 || v === 0.0) return "0";
  if (v === 1 || v === 1.0) return "1";
  var s = Number(v).toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  return s;
}
function extractSeed(path) {
  var m = String(path).match(/(\d+)\.png$/);
  return m ? m[1] : "?";
}
function escHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
// 生成页签用更短的名字，两个名字指向同一实现
var esc = escHtml;

// ── 时间格式化（跨页签共享）──────────────────────────────────────────
// 以前有三个各写各的副本：gen 的 genFmtTime（带年份）、queue 的 qFmtTime
// （不带年份）、生成的 gstamp（紧凑文件名用），补零还一个用
// ('0'+n).slice(-2)、一个用 (n<10?'0':'')+n。显示格式不同是有意的
// （生成页看历史要年份、队列页看当天不需要），所以保留三种**输出**，
// 只把 Date 构造和补零收敛到这里。
//   'ymdhm'   → 2026-10-13 14:30   （生成页：预设的历史时间）
//   'mdhm'    → 10-13 14:30        （队列页：当天的清单）
//   'compact' → 20261013_1430      （文件名用，无分隔符）
function fmtTime(ts, style){
  var d = (ts === undefined || ts === null) ? new Date() : new Date(ts * 1000);
  var p = function(n){ return (n < 10 ? '0' : '') + n };
  var md = p(d.getMonth() + 1) + '-' + p(d.getDate());
  var hm = p(d.getHours()) + ':' + p(d.getMinutes());
  if (style === 'mdhm')    return md + ' ' + hm;
  if (style === 'compact') return '' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate())
                                  + '_' + p(d.getHours()) + p(d.getMinutes());
  return d.getFullYear() + '-' + md + ' ' + hm;
}

// 统一的 JSON 请求封装：失败一律归一到 {ok:false,error}，调用方不必 try/catch
function api(method, path, body) {
  var opt = { method: method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined && body !== null) opt.body = JSON.stringify(body);
  return fetch(path, opt)
    .then(function(r){ return r.json() })
    .catch(function(e){ return { ok: false, error: String(e) } });
}
function escAttr(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

@PLUGIN_JS@
</script>
</body></html>
"""
