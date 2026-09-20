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

/* 相似度散点 */
.sim-wrap{position:relative;padding:18px}
#simCanvas{background:var(--panel);border:1px solid var(--line);border-radius:12px;display:block}
.sim-tip{position:absolute;background:rgba(13,16,32,.96);border:1px solid var(--line-2);
  border-radius:10px;padding:8px;pointer-events:none;z-index:50;box-shadow:0 8px 28px #0009}
.sim-tip img{width:180px;display:block;border-radius:6px;background:#0a0c1a}
.sim-tip div{font-size:11px;color:var(--dim);margin-top:6px;max-width:180px;word-break:break-all;
  font-family:SF Mono,Consolas,monospace}

/* 相似度的数值化表格 */
#tab-sim{overflow-y:auto;max-height:calc(100vh - 58px)}
.mono{font-family:SF Mono,Cascadia Code,Consolas,monospace}
.statcard{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 15px;margin-top:14px}
.statcard h4{margin:0 0 9px;font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.7px;font-weight:700}
.statnote{font-size:11px;color:var(--dim-2);line-height:1.6;margin:7px 0 0}
.statrow{display:flex;justify-content:space-between;gap:12px;font-size:12px;padding:4px 0;
  border-bottom:1px solid rgba(255,255,255,.04)}
.statrow:last-of-type{border-bottom:none}
.statrow span{color:var(--dim)}
.statrow b{color:var(--txt);font-family:SF Mono,Consolas,monospace;font-weight:600}
.stattable{width:100%;border-collapse:collapse;font-size:11px}
.stattable th{text-align:left;color:var(--dim-2);font-weight:600;padding:3px 6px;
  border-bottom:1px solid var(--line-2);font-size:10px;text-transform:uppercase;letter-spacing:.5px}
.stattable td{padding:5px 6px;border-bottom:1px solid rgba(255,255,255,.04);color:var(--txt);vertical-align:middle}
.stattable tr:last-child td{border-bottom:none}
.bar{height:9px;border-radius:5px;background:#1a1e38;overflow:hidden;min-width:70px}
.bar > i{display:block;height:100%;border-radius:5px;
  background:linear-gradient(90deg,var(--accent),var(--hot))}
.statcols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.statcols{grid-template-columns:1fr}}

/* 诊断报告 */
.diagsum{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--dim)}
.diagsum b{color:var(--txt);font-family:SF Mono,Consolas,monospace}
td.ok,.ok{color:var(--ok)}
td.warn,.warn{color:#ffc46b}
.diaglist{display:flex;flex-direction:column;gap:9px}
.diagitem{display:flex;gap:11px;align-items:center}
.diagitem img{width:66px;height:66px;object-fit:cover;border-radius:7px;flex:none;background:#0a0c1a}
.diagitem b{font-size:11px;word-break:break-all}
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
.grid-wrap{padding:0;overflow:hidden;max-height:var(--grid-h,calc(100vh - 175px));display:flex;flex-direction:column}
/* 可缩放画布：滚轮缩放、空白处拖拽平移（像 CAD / 白板） */
/* ⚠️ min-height 必须是 0 —— 早先写死 520px，矮窗口下画布被撑到 520 而父容器只给
   两百多，clientHeight 谎报 520 → fitView() 按 520 缩放居中，多出来的部分被
   .grid-wrap 的 overflow:hidden 裁掉，**底排图片看不见**。0 才能如实收缩。 */
#canvasWrap{position:relative;flex:1;min-height:0;overflow:hidden;cursor:grab;background:#0a0c1a;
  background-image:radial-gradient(circle at 1px 1px, rgba(255,255,255,.05) 1px, transparent 0);
  background-size:22px 22px}
#canvasWrap.dragging{cursor:grabbing}
/* 内容超出画布时的提示角标。
   为什么需要它：画面是 transform 缩放的，**溢出内容不会产生滚动条**，
   overflow:hidden 一裁就没了。用户滚轮放大后底部看不见，又不知道该按什么
   —— 这个角标就是告诉他出口在哪。内容放得下时自动隐藏。 */
.fit-hint{position:absolute;right:12px;bottom:12px;z-index:16;
  background:rgba(13,16,32,.94);border:1px solid var(--line-2);border-radius:9px;
  padding:7px 12px;font-size:11.5px;color:var(--dim);pointer-events:none;
  box-shadow:0 6px 20px #0007}
.fit-hint b{color:#ffd166;font-weight:600}
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
</style>
</head><body>

<div class="topbar">
  <span class="brand"><span class="dot"></span>LoRA 矩阵</span>
  <button class="tabbtn active" id="tabbtn-view" onclick="switchTab('view')">网格查看</button>
  <button class="tabbtn" id="tabbtn-sim" onclick="switchTab('sim')">融合诊断</button>
  <button class="tabbtn" id="tabbtn-gen" onclick="switchTab('gen')">新建矩阵</button>
  <button class="tabbtn" id="tabbtn-queue" onclick="switchTab('queue')">任务队列</button>
  <span id="viewTools" style="display:flex;gap:10px;align-items:center;flex:1;min-width:0">
    <input type="text" id="pathInput" placeholder="矩阵目录（默认 ComfyUI 的 output/matrix）" />
    <button class="btn ghost" onclick="pickFolder()">📂 浏览</button>
    <button class="btn" onclick="loadTasks()">⟳ 加载</button>
    <span id="taskInfo" style="font-size:11px;color:var(--dim);white-space:nowrap"></span>
  </span>
</div>

<div id="tab-view">
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
      <div class="hint">选一个矩阵目录，或点 <b>📂 浏览</b><br>默认目录 = ComfyUI 的 <b>output/matrix</b></div>
    </div>
    <div id="fitHint" class="fit-hint hidden">内容超出画布 · <b>⌖ 适应</b> 缩到一屏，或滚轮缩小、<b>中键拖动</b>平移</div>
  </div>
</div>
</div><!-- /tab-view -->

<div id="tab-sim" class="hidden">
  <div class="toolbar">
    <span style="font-size:12px;color:var(--dim)">散点图只作<b>全局概览</b>（效果接近的会自动聚在一起）—— 结论看下方诊断报告</span>
    <button class="btn ghost" onclick="simLoad()">⟳ 重算</button>
    <span id="simInfo" style="font-size:11px;color:var(--dim);margin-left:auto;white-space:nowrap"></span>
  </div>
  <div class="sim-wrap">
    <canvas id="simCanvas"></canvas>
    <div id="simTip" class="sim-tip hidden"></div>
  </div>
  <div id="simStats" style="padding:0 18px 22px"></div>
</div>

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
// ── 标签切换 ──
function switchTab(name){
  var isView = (name === 'view');
  var isGen  = (name === 'gen');
  var isSim  = (name === 'sim');
  var isQ    = (name === 'queue');
  document.getElementById('tab-view').classList.toggle('hidden', !isView);
  document.getElementById('tab-gen').classList.toggle('hidden', !isGen);
  document.getElementById('tab-sim').classList.toggle('hidden', !isSim);
  document.getElementById('tab-queue').classList.toggle('hidden', !isQ);
  document.getElementById('tabbtn-view').classList.toggle('active', isView);
  document.getElementById('tabbtn-gen').classList.toggle('active', isGen);
  document.getElementById('tabbtn-sim').classList.toggle('active', isSim);
  document.getElementById('tabbtn-queue').classList.toggle('active', isQ);
  document.getElementById('viewTools').style.display = isView ? 'flex' : 'none';
  if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
  if (isGen && window.genInit) window.genInit();   // 首次切过去时才初始化
  if (isSim) simLoad();
  if (isQ && typeof qInit === 'function') qInit();
  // 切回网格页：离开期间画布是 display:none，量出来的高度是 0，必须重新量一遍
  if (isView) { layoutGrid(); if (!viewTouched) fitView(); }
}
window.addEventListener('DOMContentLoaded', function(){
  var h = (location.hash || '').replace('#', '');
  if (h === 'view' || h === 'gen' || h === 'sim' || h === 'queue') switchTab(h);
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

// ── Load ──
function loadTasks() {
  var folder = document.getElementById("pathInput").value.trim();
  if (!folder) return;
  var sp = document.getElementById("spinner");
  var grid = document.getElementById("grid");
  sp.classList.remove("hidden");
  grid.innerHTML = "";
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
      // 用户若直接落在「相似度」标签，目录加载完再算（DOMContentLoaded 那会儿
      // pathInput 还是空的 —— config 是异步取的）
      if (typeof simLoad === "function" &&
          !document.getElementById("tab-sim").classList.contains("hidden")) simLoad();
    })
    .catch(function(err) {
      sp.classList.add("hidden");
      grid.innerHTML = '<div class="hint" style="color:var(--hot)">加载失败：' + escHtml(err.message) + '</div>';
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
  // 相似度视图开着的话同步刷新
  var sim = document.getElementById("tab-sim");
  if (sim && !sim.classList.contains("hidden") && typeof renderScatter === "function") renderScatter();
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

// ── 相似度散点 ──
var simPoints = [], simExplained = [0, 0], simLoadedFor = "";
var simImgCache = {};   // 避免每次重绘都重新解码 PNG

function simGetImg(url, cb) {
  if (simImgCache[url]) { cb(simImgCache[url]); return }
  var im = new Image();
  im.onload = function(){ simImgCache[url] = im; cb(im) };
  im.onerror = function(){ cb(null) };
  im.src = url;
}

// 把提示画在画布上 —— 多行等宽，方便直接复制里面的命令
function simShowMsg(msg) {
  var info = document.getElementById("simInfo");
  if (info) info.textContent = "无法计算";
  var st = document.getElementById("simStats");
  if (st) st.innerHTML = "";      // 出错时别留着上一次的表格
  var cv = document.getElementById("simCanvas");
  if (!cv) return;
  var wrap = cv.parentElement;
  var W = Math.max(420, wrap.clientWidth - 36);
  var H = Math.round(Math.max(240, Math.min(660, window.innerHeight * 0.52)));
  cv.width = W; cv.height = H;
  cv.style.width = W + "px"; cv.style.height = H + "px";
  var ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, W, H);
  ctx.font = "12px SF Mono, Consolas, monospace";
  var y = 44;
  String(msg).split("\n").forEach(function(ln, i){
    ctx.fillStyle = i === 0 ? "#ff8fa3" : "#8a93bb";
    ctx.fillText(ln, 26, y);
    y += 20;
  });
}

function simLoad() {
  var folder = document.getElementById("pathInput").value.trim();
  var info = document.getElementById("simInfo");
  if (!folder) { simShowMsg("先在「网格查看」标签里选好矩阵目录"); return }
  if (simLoadedFor === folder && simPoints.length) { simDraw(); return }
  info.textContent = "计算中…";
  api('GET', '/api/similarity?folder=' + encodeURIComponent(folder)).then(function(d){
    if (!d || !d.ok) { simShowMsg((d && d.error) || "计算失败"); return }
    if (d.error) { simShowMsg(d.error); return }   // 缺依赖之类：给提示而不是崩
    simPoints = d.points || [];
    simExplained = d.explained || [0, 0];
    simLoadedFor = folder;
    info.textContent = simPoints.length + " 张 · 前两主成分解释 "
      + (simExplained[0] * 100).toFixed(0) + "% + " + (simExplained[1] * 100).toFixed(0) + "%";
    simDraw();
    simRenderReport(d.diagnose);
  });
}

// ── 诊断报告 ──
// 从诊断里挑出组合 → 切到「新建矩阵」把组合选择里的勾选换成这些
function simSelectOnly(keys){
  switchTab('gen');
  setTimeout(function(){
    if (typeof genCombos === "undefined" || !genCombos.length) {
      genMsg("请先在「新建矩阵」里配好并生成一次任务清单", "err");
      return;
    }
    var want = {};
    keys.forEach(function(k){ want[k] = 1 });
    genCombos.forEach(function(c){ c.sel = !!want[c.key] });
    genOpenCombos();
    genMsg("已只选 " + keys.length + " 个组合（去复核）", "ok");
  }, 260);
}

// ── 诊断报告渲染 ──────────────────────────────────────────────────────────
// 每个区块一个函数，simRenderReport() 只负责拼。改某一块不用读整段 110 行。
// 后端 diagnose.py 的 ANALYSES 清单决定返回哪些键；这里要把新块接上才能显示
// （后端加一项诊断 = 加一个函数 + 在下面拼一行）。

function simBlockSummary(d){
  var eff   = d.effective || [];
  var outs  = d.outliers || [];
  var inter = d.interference || [];
  var weak  = eff.filter(function(e){ return e.verdict === "无效" }).length;
  var bad   = inter.filter(function(x){ return x.verdict === "可能互相干扰" }).length;
  return '<div class="statcard"><h4>诊断总结</h4><div class="diagsum">'
     + '<span><b>' + d.n + '</b> 个组合</span>'
     + '<span class="' + (weak ? 'warn' : 'ok') + '"><b>' + eff.length + '</b> 个 LoRA，'
     + (weak ? weak + ' 个疑似无效' : '全部有效') + '</span>'
     + '<span class="' + (outs.length ? 'warn' : 'ok') + '"><b>' + outs.length + '</b> 个可疑组合</span>'
     + '<span class="' + (bad ? 'warn' : 'ok') + '"><b>' + bad + '</b> 对可能干扰</span>'
     + '</div></div>';
}

// ① 有效性
function simBlockEffective(eff){
  var h = '<div class="statcard"><h4>① LoRA 有效性</h4>'
     + '<div class="statnote" style="margin:0 0 9px">与 baseline（不加任何 LoRA）的画面距离 —— '
     + '太小说明加了等于没加</div>';
  if (eff.length) {
    h += '<table class="stattable"><thead><tr><th>LoRA</th><th>距离</th><th>相对</th>'
       + '<th>判定</th></tr></thead><tbody>';
    eff.forEach(function(e){
      h += '<tr><td class="mono">' + esc(e.dim) + '</td>'
         + '<td class="mono">' + e.dist + '</td>'
         + '<td class="mono" style="color:var(--dim-2)">x' + e.ratio + '</td>'
         + '<td class="' + (e.verdict === "无效" ? "warn" : "ok") + '">' + e.verdict + '</td></tr>';
    });
    h += '</tbody></table>';
  } else {
    h += '<div class="statnote" style="margin:0">没有找到 baseline 组合，无法比较</div>';
  }
  return h + '</div>';
}

// ② 可疑组合
function simBlockOutliers(outs){
  var h = '<div class="statcard"><h4>② 可疑组合（画面明显偏离大部队）';
  if (outs.length) {
    var keys = outs.map(function(o){ return o.key });
    h += '<button class="btn ghost" style="float:right;padding:2px 10px;font-size:11px" '
       + 'onclick="simSelectOnly(' + escAttr(JSON.stringify(keys)) + ')">只跑这些去复核</button>';
  }
  h += '</h4>';
  if (outs.length) {
    h += '<div class="diaglist">';
    outs.forEach(function(o){
      h += '<div class="diagitem">'
         + (o.img ? '<img src="' + escAttr(o.img) + '" loading="lazy" />' : '')
         + '<div><b class="mono">' + esc(o.name) + '</b>'
         + '<div class="statnote" style="margin:2px 0 0">偏离 <span class="warn">' + o.sigma
         + 'σ</span>（到其他组合的平均差异 ' + o.score + '）</div></div></div>';
    });
    h += '</div>';
  } else {
    h += '<div class="statnote" style="margin:0">没有明显离群的组合 —— 没有哪组崩得特别厉害</div>';
  }
  return h + '</div>';
}

// ③ 饱和点
function simBlockSaturation(sats){
  var h = '<div class="statcard"><h4>③ 强度饱和点</h4>'
     + '<div class="statnote" style="margin:0 0 9px">同一 LoRA 相邻强度档之间的画面变化量 —— '
     + '越往右越短说明再加强度收益递减</div>'
     + '<table class="stattable"><thead><tr><th>LoRA</th><th>档位</th>'
     + '<th style="width:38%">相邻档变化量</th><th>结论</th></tr></thead><tbody>';
  sats.forEach(function(s){
    var mx = Math.max.apply(null, s.deltas) || 1;
    var bars = s.deltas.map(function(dd){
      var w = Math.max(6, Math.round(dd / mx * 46));
      return '<div class="bar" style="display:inline-block;width:' + w
           + 'px;margin-right:3px;vertical-align:middle"><i style="width:100%"></i></div>';
    }).join('');
    h += '<tr><td class="mono">' + esc(s.dim) + '</td>'
       + '<td class="mono" style="color:var(--dim-2);white-space:nowrap">' + s.levels.join('→') + '</td>'
       + '<td>' + bars + '</td>'
       + '<td class="' + (s.enough ? '' : 'warn') + '">' + esc(s.note) + '</td></tr>';
  });
  return h + '</tbody></table></div>';
}

// ④ 干扰
function simBlockInterference(inter){
  var h = '<div class="statcard"><h4>④ LoRA 互相干扰</h4>'
     + '<div class="statnote" style="margin:0 0 9px">理想融合应落在「单用 A」和「单用 B」之间；'
     + '跑到两者之外（比值 &gt;1）说明叠加产生了第三种东西，往往是崩坏</div>';
  if (inter.length) {
    h += '<table class="stattable"><thead><tr><th>组合</th><th>比值</th>'
       + '<th>样本</th><th>判定</th></tr></thead><tbody>';
    inter.forEach(function(x){
      h += '<tr><td class="mono">' + esc(x.a) + ' <span style="color:var(--dim-2)">×</span> '
         + esc(x.b) + '</td><td class="mono">' + x.ratio + '</td>'
         + '<td class="mono" style="color:var(--dim-2)">' + x.samples + '</td>'
         + '<td class="' + (x.verdict === "可能互相干扰" ? "warn" : "ok") + '">'
         + x.verdict + '</td></tr>';
    });
    h += '</tbody></table>';
  } else {
    h += '<div class="statnote" style="margin:0">需要「单用 A」「单用 B」「一起用」三类组合都存在才能判断</div>';
  }
  return h + '</div>';
}

function simRenderReport(d){
  var box = document.getElementById("simStats");
  if (!box) return;
  if (!d) { box.innerHTML = ""; return }
  if (d.error) {
    box.innerHTML = '<div class="statcard"><h4>诊断失败</h4>'
      + '<div class="statnote" style="margin:0">' + esc(d.error) + '</div></div>';
    return;
  }
  box.innerHTML = simBlockSummary(d)
    + simBlockEffective(d.effective || [])
    + simBlockOutliers(d.outliers || [])
    + simBlockSaturation(d.saturation || [])
    + simBlockInterference(d.interference || []);
}

function simDraw() {
  var cv = document.getElementById("simCanvas");
  if (!cv) return;
  var wrap = cv.parentElement;
  var W = Math.max(420, wrap.clientWidth - 36);
  // 别占满视口 —— 下面还有数值表格要看。整页交给 #tab-sim 滚动
  var H = Math.round(Math.max(360, Math.min(660, window.innerHeight * 0.52)));
  cv.width = W; cv.height = H;
  cv.style.width = W + "px"; cv.style.height = H + "px";
  var ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, W, H);
  if (simPoints.length < 2) {
    ctx.fillStyle = "#8a93bb"; ctx.font = "13px sans-serif";
    ctx.fillText("至少需要 2 张有图的组合", 24, 44);
    return;
  }
  var xs = simPoints.map(function(p){return p.x}), ys = simPoints.map(function(p){return p.y});
  var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
  var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
  var pad = 70, TS = 58;
  simPoints.forEach(function(p){
    p._sx = pad + (p.x - x0) / Math.max(1e-6, x1 - x0) * (W - pad * 2);
    p._sy = H - pad - (p.y - y0) / Math.max(1e-6, y1 - y0) * (H - pad * 2);
  });
  // 散开挤在一起的缩略图 —— PCA 只保留两维，投影重叠很常见，不散开看不清有几张。
  // 用网格分桶（精确坐标匹配不够，相邻但不相等的点照样会叠），
  // 桶内再按黄金角螺旋铺开，分布最均匀
  var BUCKET = TS + 6, seen = {};   // 桶要 ≥ 缩略图尺寸，否则相邻桶的图仍然叠
  simPoints.forEach(function(p){
    var k = Math.round(p._sx / BUCKET) + "|" + Math.round(p._sy / BUCKET);
    var n = (seen[k] = (seen[k] || 0) + 1);
    if (n > 1) {
      var ang = n * 2.399963229728653;
      var rad = TS * 0.62 * Math.sqrt(n - 1);
      p._sx += Math.cos(ang) * rad;
      p._sy += Math.sin(ang) * rad;
    }
  });
  var pending = simPoints.length;
  simPoints.forEach(function(p){
    simGetImg(p.img, function(im){
      if (im) ctx.drawImage(im, p._sx - TS / 2, p._sy - TS / 2, TS, TS);
      else { ctx.fillStyle = "#28304f"; ctx.fillRect(p._sx - TS / 2, p._sy - TS / 2, TS, TS) }
      var mk = marks[p.key];
      ctx.strokeStyle = mk ? "#ffd166" : "rgba(255,255,255,.18)";
      ctx.lineWidth = mk ? 2.5 : 1;
      ctx.strokeRect(p._sx - TS / 2, p._sy - TS / 2, TS, TS);
      if (mk) {
        ctx.fillStyle = "#ffd166"; ctx.font = "13px sans-serif";
        ctx.fillText("★", p._sx + TS / 2 - 14, p._sy - TS / 2 + 14);
      }
      if (--pending === 0) simBind(cv);
    });
  });
}

function simHit(cv, e) {
  var r = cv.getBoundingClientRect();
  var mx = e.clientX - r.left, my = e.clientY - r.top;
  for (var i = 0; i < simPoints.length; i++) {
    var p = simPoints[i];
    if (Math.abs(mx - p._sx) <= 32 && Math.abs(my - p._sy) <= 32) return p;
  }
  return null;
}

function simBind(cv) {
  cv.onmousemove = function(e){
    var hit = simHit(cv, e);
    var tip = document.getElementById("simTip");
    if (hit) {
      tip.innerHTML = '<img src="' + escAttr(hit.img) + '" /><div>' + escHtml(hit.key) + '</div>';
      tip.style.left = Math.min(hit._sx + 36, Math.max(0, cv.width - 200)) + 'px';
      tip.style.top = Math.max(0, hit._sy - 40) + 'px';
      tip.classList.remove("hidden");
      cv.style.cursor = "pointer";
    } else {
      tip.classList.add("hidden");
      cv.style.cursor = "default";
    }
  };
  cv.onmouseleave = function(){ document.getElementById("simTip").classList.add("hidden") };
  cv.onclick = function(e){
    var hit = simHit(cv, e);
    if (!hit) return;
    switchTab('view');
    setTimeout(function(){ openTask(hit.key) }, 60);   // 等网格渲染完再开弹窗
  };
}

window.addEventListener('resize', function(){
  // 网格页：先按新窗口高度重新量画布，用户没手动调过视角就顺带重新适应
  layoutFacet();     // 分面模式下列数会随可用宽度变
  layoutGrid();
  var gridTab = document.getElementById('tab-view');
  if (gridTab && !gridTab.classList.contains('hidden') && !viewTouched) fitView();
  var tab = document.getElementById('tab-sim');
  if (tab && !tab.classList.contains('hidden') && simPoints.length) simDraw();
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
  wrap.style.maxHeight = Math.max(180, window.innerHeight - top - 12) + 'px';
}

function fitView(){
  var g = document.getElementById("grid"), wrap = document.getElementById("canvasWrap");
  if (!g || !wrap) return;
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
</script>
</body></html>
"""
