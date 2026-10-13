# -*- coding: utf-8 -*-
"""「任务队列」标签页的 UI 片段。

gui.py 是页面外壳（含唯一的 <style>），这里只提供两段：
  CSS  —— 追加进外壳的样式表（填 @QUEUE_CSS@）
  BODY —— 标签页内容 + 自带 <script>（填 @QUEUE_BODY@）

共享工具（esc / api / switchTab）来自外壳的 <script>，本模块不重复定义。

## 这个页签解决什么

`json/` 下会攒下**多份**任务清单（不同配置生成的）。以前界面上看不到它们，
要跑只能「跑刚生成的那一份」；CLI 侧 `task_runner` 也只默认跑最新的一份。

这里把它们列出来，带**从磁盘推导的完成度**（数输出目录里 seed 匹配的 PNG，
见 server._list_tasklists），可以勾选多份按顺序跑。

## 两个刻意的取舍

- **不持久化**：完成度是从产物数出来的，不是记出来的。重启后重新勾一下即可，
  而且有「跳过已完成」，重跑是安全的。
- **执行顺序 = 表格顺序**（创建时间倒序）。想指定别的顺序就单独跑一份。
"""

CSS = r"""
/* ── 任务队列页签 ──
   ⚠️ 全部挂在 .q-wrap 下 —— 外壳已有 .row/.hint/.empty 等同名 class，
   不隔离会互相污染（gen_tab 的 .hint padding:70px 曾经把卡片撑出大块空白）。 */
.q-wrap{padding:18px}
.q-tools{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.q-wrap .grow{flex:1}
.q-sel{font-size:12px;color:var(--dim)}
.q-sel b{color:var(--txt)}

.q-list{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel)}
.q-head,.q-row{display:grid;
  grid-template-columns:36px 1fr 76px 96px 92px 118px 44px;align-items:center}
.q-head{background:var(--panel-2);border-bottom:1px solid var(--line-2);
  font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px}
.q-head > div{padding:9px 10px}
.q-row{border-bottom:1px solid rgba(255,255,255,.04);font-size:12.5px}
.q-row:last-child{border-bottom:none}
.q-row:hover{background:rgba(255,255,255,.02)}
.q-row > div{padding:9px 10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.q-row .q-name{font-weight:600}
.q-row .q-sub{font-size:11px;color:var(--dim-2);margin-top:2px;
  overflow:hidden;text-overflow:ellipsis}
.q-row .mono{font-family:SF Mono,Consolas,monospace;font-variant-numeric:tabular-nums}
.q-row.done .q-name{color:#7ff0c0}
.q-row.partial .q-name{color:#ffd166}
.q-row.fresh .q-name{color:var(--dim)}
.q-wrap .q-del{border:none;background:none;color:var(--dim-2);cursor:pointer;
  font-size:14px;padding:2px 6px;border-radius:6px}
.q-wrap .q-del:hover{background:#ff5c5c22;color:#ff8a8a}
.q-empty{padding:26px 20px;text-align:center;color:var(--dim);font-size:13px;line-height:1.9}
.q-empty b{color:var(--txt)}

.q-progress{margin-top:14px}
.q-bar{height:9px;border-radius:5px;background:#1a1e38;overflow:hidden}
.q-bar > i{display:block;height:100%;width:0;background:linear-gradient(90deg,#7c5cff,#b06cff);
  transition:width .25s}
.q-pinfo{font-size:11.5px;color:var(--dim);margin-top:8px;
  font-family:SF Mono,Consolas,monospace;font-variant-numeric:tabular-nums}
.q-log{margin-top:8px;max-height:210px;overflow-y:auto;background:#0b0e1e;
  border:1px solid var(--line);border-radius:8px;padding:10px;
  font-size:11px;line-height:1.65;color:#c3c9e6;white-space:pre-wrap;word-break:break-word}
"""

BODY = r"""
<div class="q-wrap">
  <div class="q-tools">
    <button class="btn ghost" onclick="qLoad()">⟳ 刷新</button>
    <button class="btn ghost" onclick="qAll(true)">全选</button>
    <button class="btn ghost" onclick="qAll(false)">全不选</button>
    <span class="q-sel" id="q-sel"></span>
    <span class="grow"></span>
    <button class="btn" id="q-run" onclick="qRun()">▶ 运行选中</button>
    <button class="btn ghost" id="q-stop" onclick="qStop()" disabled>⏹ 停止</button>
  </div>

  <div class="q-list" id="q-list">
    <div class="q-empty">加载中…</div>
  </div>

  <div class="q-progress hidden" id="q-progress">
    <div class="q-bar"><i id="q-bar"></i></div>
    <div class="q-pinfo" id="q-pinfo"></div>
    <pre class="q-log" id="q-log"></pre>
  </div>

  <div class="msg" id="q-msg"></div>
</div>

<script>
var qItems = [];                 // 清单列表（来自 /api/tasklists）
var qSel = {};                   // 勾选状态：file → true
var qTimer = null;               // 进度轮询
var qRunning = false;

function qMsg(m, kind){
  var e = document.getElementById('q-msg');
  if (!e) return;
  e.className = 'msg' + (kind ? ' ' + kind : '');
  e.textContent = m || '';
}

// 实现已收敛到内核的 fmtTime（gui.py）。队列清单都是当天的，所以不带年份。
function qFmtTime(ts){ return fmtTime(ts, 'mdhm') }

var Q_STATE = {
  done:    { cls: 'done',    txt: '✓ 已完成' },
  partial: { cls: 'partial', txt: '↻ 部分完成' },
  fresh:   { cls: 'fresh',   txt: '· 未开始' }
};

function qRender(){
  var box = document.getElementById('q-list');
  if (!qItems.length){
    box.innerHTML = '<div class="q-empty">还没有任务清单。<br>'
      + '去 <b>新建矩阵</b> 页签配置并点「仅生成任务清单」，或直接点「生成并执行」。</div>';
    qRefreshSel();
    return;
  }
  var h = '<div class="q-head"><div></div><div>任务</div><div>组合</div>'
        + '<div>完成</div><div>状态</div><div>创建时间</div><div></div></div>';
  qItems.forEach(function(it){
    var st = Q_STATE[it.state] || Q_STATE.fresh;
    // 勾选状态按 file 存；刷新后仍保留（同一份清单路径不变）
    var on = qSel[it.file] ? ' checked' : '';
    var sub = (it.loras && it.loras.length)
      ? ('LoRA: ' + it.loras.join(' / '))
      : '';
    if (it.scenes > 1) sub += (sub ? ' · ' : '') + it.scenes + ' 个场景';
    h += '<div class="q-row ' + st.cls + '">'
       +   '<div><input type="checkbox" data-file="' + escAttr(it.file) + '"'
       +        on + ' onchange="qToggle(this)"></div>'
       +   '<div><div class="q-name">' + esc(it.task_name) + '</div>'
       +        (sub ? '<div class="q-sub">' + esc(sub) + '</div>' : '')
       +        '<div class="q-sub">' + esc(it.name) + '</div></div>'
       +   '<div class="mono">' + it.total + '</div>'
       +   '<div class="mono">' + it.done + '/' + it.total + '</div>'
       +   '<div class="' + (it.state === 'done' ? 'ok' : it.state === 'partial' ? 'warn' : '') + '">'
       +      esc(st.txt) + '</div>'
       +   '<div class="mono" style="color:var(--dim-2)">' + qFmtTime(it.mtime) + '</div>'
       +   '<div><button class="q-del" title="只删清单，不动已生成的图" '
       +        'data-file="' + escAttr(it.file) + '" '
       +        'onclick="qDelete(this.dataset.file)">🗑</button></div>'
       + '</div>';
  });
  box.innerHTML = h;
  qRefreshSel();
}

function qToggle(el){
  if (qRunning){ el.checked = false; qMsg('正在运行，先停止再改选择', 'err'); return }
  if (el.checked) qSel[el.dataset.file] = true;
  else delete qSel[el.dataset.file];
  qRefreshSel();
}

function qAll(on){
  if (qRunning){ qMsg('正在运行，先停止再改选择', 'err'); return }
  qSel = {};
  if (on) qItems.forEach(function(it){ qSel[it.file] = true });
  qRender();
}

function qSelected(){
  // 按**表格顺序**返回，这就是执行顺序
  return qItems.filter(function(it){ return qSel[it.file] });
}

function qRefreshSel(){
  var sel = qSelected();
  var combos = sel.reduce(function(a, it){ return a + (it.total - it.done) }, 0);
  var el = document.getElementById('q-sel');
  if (el){
    el.innerHTML = sel.length
      ? ('已选 <b>' + sel.length + '</b> 份 · 还需跑 <b>' + combos + '</b> 个组合')
      : '未选任何清单';
  }
  var run = document.getElementById('q-run');
  if (run) run.disabled = qRunning || !sel.length;
}

function qLoad(){
  api('GET','/api/tasklists').then(function(d){
    qItems = (d && d.files) || [];
    // 清掉已不存在的清单的勾选
    var alive = {};
    qItems.forEach(function(it){ alive[it.file] = 1 });
    Object.keys(qSel).forEach(function(f){ if (!alive[f]) delete qSel[f] });
    qRender();
  }).catch(function(){ qMsg('读取清单失败', 'err') });
}

function qDelete(file){
  if (!confirm('删除这份任务清单？\n\n只删 json/ 里的清单文件，'
             + '已经生成的图不受影响。')) return;
  api('POST','/api/tasklists/delete',{file:file}).then(function(d){
    if (!d || !d.ok){ qMsg((d && d.error) || '删除失败', 'err'); return }
    delete qSel[file];
    qLoad();
  });
}

function qRun(){
  var sel = qSelected();
  if (!sel.length){ qMsg('先勾选要跑的清单', 'err'); return }
  var files = sel.map(function(it){ return it.file });
  qMsg('提交中…');
  api('POST','/api/run',{files: files, skip_done: true}).then(function(d){
    if (!d || !d.ok){ qMsg((d && d.error) || '启动失败', 'err'); return }
    qMsg('开始跑 ' + files.length + ' 份…');
    qRunning = true;
    document.getElementById('q-progress').classList.remove('hidden');
    qRefreshSel();
    document.getElementById('q-stop').disabled = false;
    if (qTimer) clearInterval(qTimer);
    qTimer = setInterval(qPoll, 1000);
    qPoll();
  });
}

function qStop(){
  api('POST','/api/run/stop',{}).then(function(){
    qMsg('已请求停止 —— 跑完当前组合后退出');
  });
}

function qPoll(){
  api('GET','/api/run/status').then(function(d){
    if (!d || !d.ok) return;
    // 主进度条用「全部份」的口径 —— 多份时才看得出整体还剩多少
    var g = d.grand_total || d.total || 0;
    var gd = d.grand_done || 0;
    document.getElementById('q-bar').style.width =
      (g ? Math.round(gd / g * 100) : 0) + '%';
    var parts = [];
    if (d.file_total > 1) parts.push('第 ' + (d.file_index || 0) + '/' + d.file_total + ' 份');
    parts.push('当前份 ' + (d.index || 0) + '/' + (d.total || 0));
    if (g) parts.push('共 ' + gd + '/' + g);
    parts.push('成功 ' + (d.ok_images || 0) + ' 张');
    if (d.skipped) parts.push('跳过 ' + d.skipped);
    if (d.fail) parts.push('失败 ' + d.fail);
    if (d.elapsed) parts.push('用时 ' + Math.round(d.elapsed) + 's');
    document.getElementById('q-pinfo').textContent = parts.join(' · ');
    var lg = document.getElementById('q-log');
    if (d.log && d.log.length){
      lg.textContent = d.log.join('\n');
      lg.scrollTop = lg.scrollHeight;
    }
    if (d.state && d.state !== 'running'){
      clearInterval(qTimer); qTimer = null; qRunning = false;
      document.getElementById('q-stop').disabled = true;
      var tail = (d.log && d.log.length) ? d.log[d.log.length - 1] : '';
      if (d.state === 'done')
        qMsg('完成：成功 ' + (d.ok_images || 0) + ' 张' + (tail ? ' · ' + tail : ''), 'ok');
      else if (d.state === 'stopped')
        qMsg('已停止：成功 ' + (d.ok_images || 0) + ' 张');
      else
        qMsg('出错：' + (d.error || '未知'), 'err');
      qLoad();          // 完成度会变，刷一遍列表
    }
  });
}

// 切到这个页签时自动拉一次（switchTab 里调用；首次进入才需要）
function qInit(){
  if (!qItems.length) qLoad();
  else qRefreshSel();
  // 页面刷新时如果后台还在跑，恢复进度显示
  api('GET','/api/run/status').then(function(d){
    if (d && d.ok && d.state === 'running'){
      qRunning = true;
      document.getElementById('q-progress').classList.remove('hidden');
      document.getElementById('q-stop').disabled = false;
      qRefreshSel();
      if (qTimer) clearInterval(qTimer);
      qTimer = setInterval(qPoll, 1000);
      qPoll();
    }
  });
}
</script>
"""
