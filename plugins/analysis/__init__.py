# -*- coding: utf-8 -*-
"""融合诊断 —— 矩阵工具的第一个插件。

原先是内联在 gui.py 里的「相似度散点 + 诊断报告」，加上 server.py 的
`/api/similarity` 路由，以及 diagnose.py / similarity.py 两个算法模块。
现在整块搬到这里，内核不再认识它们。
详见 plugins/README.md（插件开发规范）。

契约（plugin_loader 认这几个顶层名字）：
    BODY   页签内容 HTML       → 注入外壳的 @PLUGIN_BODY@
    CSS    该页签样式          → @PLUGIN_CSS@
    JS     该页签脚本          → @PLUGIN_JS@（包在 IIFE 里，只经 window.MLX 与内核通信）
    routes() → {路径: handler}  插件自己的 HTTP 路由

⚠️ BODY 只写**内容**，不要自己套 `<div id="tab-xxx">` 外壳 ——
   外壳由 plugin_loader 按 `plugin.json` 的 `tab.id` 生成。
   两边都套 = 重复 id，`getElementById('tab-sim')` 会拿到错误的那一层。

⚠️ CSS 只放**这个页签独有**的规则。跨页签共享的基础类（`.mono` / `.ok` /
   `.warn` / `.bar`）在内核样式表里 —— 放这儿的话一卸载就弄坏别的页签。
   判断归属：看这条规则在几个页签里出现，≥2 个就是内核的。

handler 签名 `(handler, params)`，拿到的是内核的 Handler 实例。
**内核给插件的后端接口**（见 server.py 的 Handler 类头）：
    handler._json(data)            回一个 JSON
    handler.resolve_folder(f)      父目录 → 真正含 task.json 的任务目录
    handler.scan_tasks(f)          扫出 {tasks, dimensions}
插件不该自己重写目录扫描，也不该 `import server`（那会循环导入）。

卸载 = 删掉本目录。
"""
import os

# 本模块自包含：similarity.py / diagnose.py 就在同目录。
# plugin_loader 会把本目录加进 sys.path，所以 similarity.py 里的
# `import diagnose` 原样可用，那两个文件一个字都不用改。
BODY = r"""
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
"""

CSS = r"""
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
.statcols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.statcols{grid-template-columns:1fr}}

/* 诊断报告 */
.diagsum{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--dim)}
.diagsum b{color:var(--txt);font-family:SF Mono,Consolas,monospace}
.diaglist{display:flex;flex-direction:column;gap:9px}
.diagitem{display:flex;gap:11px;align-items:center}
.diagitem img{width:66px;height:66px;object-fit:cover;border-radius:7px;flex:none;background:#0a0c1a}
.diagitem b{font-size:11px;word-break:break-all}
"""

JS = r"""
(function(){
"use strict";
// 内核函数取本地别名 —— 下面是与搬家前逐行相同的实现，靠这几个别名跟内核说话
var MLX = window.MLX;
var api = MLX.api, switchTab = MLX.switchTab, openTask = MLX.openTask,
    escAttr = MLX.escAttr, escHtml = MLX.escHtml;

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
  var folder = MLX.getFolder();
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
      var mk = MLX.getMarks()[p.key];
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

// ── 与内核的接线（全部走 MLX，不碰内核内部标识符）──

// ① 内联 onclick 用得到的那两个必须挂到全局
MLX.expose({ simLoad: simLoad, simSelectOnly: simSelectOnly });

// ② 页签自注册：切过去时跑 simLoad
MLX.registerTab({ id: "sim", label: "融合诊断", onShow: simLoad });

// ③ 目录加载完 —— 用户直接落在本页签时补算一次
//    （DOMContentLoaded 那会儿 pathInput 还是空的，config 是异步取的）
MLX.on("folder-loaded", function(){
  if (!document.getElementById("tab-sim").classList.contains("hidden")) simLoad();
});

// ④ 星标变了 —— 本视图开着就重绘
//    ⚠️ 这里原来在 gui.py 里写的是 `typeof renderScatter === "function"`，
//    而 renderScatter **全文只出现在那一行** —— 函数早改名成 simDraw 了，
//    所以那个钩子从来没生效过（点星标时散点不刷新）。搬家时一并修掉。
MLX.on("marks-changed", function(){
  var t = document.getElementById("tab-sim");
  if (t && !t.classList.contains("hidden") && simPoints.length) simDraw();
});

// ⑤ 窗口尺寸变了 —— 本视图开着就按新尺寸重画
MLX.on("resize", function(){
  var t = document.getElementById("tab-sim");
  if (t && !t.classList.contains("hidden") && simPoints.length) simDraw();
});
})();

"""


def handle_similarity(handler, params):
    """图片视觉相似度散点数据（颜色/纹理特征 → PCA 2D）。

    每次请求现算 —— 百来张图不到一秒，不值得加缓存（还会带来失效问题）。
    函数体从 server.py 的 `_handle_similarity` 原样搬来。
    """
    folder = params.get("folder", [""])[0]
    if not folder or not os.path.isdir(folder):
        handler._json({"ok": False, "error": "invalid folder"})
        return
    resolved = handler.resolve_folder(folder)
    tasks, _dims = handler.scan_tasks(resolved)
    try:
        import similarity
        r = similarity.similarity_map(tasks)
    except Exception as exc:
        handler._json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})
        return
    handler._json({"ok": True, **r})


def routes():
    """插件注册的 HTTP 路由。内核在分发时查这张表。"""
    return {"/api/similarity": handle_similarity}
