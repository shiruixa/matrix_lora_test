# -*- coding: utf-8 -*-
"""「新建矩阵」标签页的 UI 片段。

gui.py 是页面外壳（含唯一的 <style>），这里只提供两段：
  CSS  —— 追加进外壳的样式表（填 @GEN_CSS@）
  BODY —— 标签页内容 + 自带 <script>（填 @GEN_BODY@）

共享工具（esc / api / switchTab）来自外壳的 <script>，本模块不重复定义。
"""

CSS = r"""
/* ── 生成页签 ──
   所有选择器都挂在 .gen-wrap 下：外壳（gui.py）已有 .row/.hint/.empty/.warn
   等同名 class，不加命名空间会互相污染（.hint 的 padding:70px 曾把卡片撑出大块空白）。*/
.gen-wrap{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px;padding:18px;align-items:start}
@media(max-width:1150px){.gen-wrap{grid-template-columns:1fr}}
.gen-wrap .gen-col{display:flex;flex-direction:column;gap:14px;min-width:0}
.gen-wrap .card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
.gen-wrap .card > h3{margin:0 0 6px;font-size:11px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:var(--dim)}
.gen-wrap .card .sub{font-size:11px;color:var(--dim);line-height:1.6;margin-bottom:10px}
.gen-wrap .row{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.gen-wrap .row:last-child{margin-bottom:0}
.gen-wrap .row > label{color:var(--dim);min-width:54px}
.gen-wrap .row > .tag{font-size:11px;color:var(--dim-2)}
.gen-wrap input[type=text],.gen-wrap input[type=number],.gen-wrap textarea{
  padding:7px 10px;border:1px solid var(--line-2);border-radius:7px;
  background:#0d1022;color:var(--txt);font-size:12px;font-family:inherit;
  transition:border-color .15s;
}
.gen-wrap input[type=text]:focus,.gen-wrap input[type=number]:focus,.gen-wrap textarea:focus{
  outline:none;border-color:var(--accent);
}
.gen-wrap textarea{width:100%;resize:vertical;font-family:SF Mono,Cascadia Code,Consolas,monospace;line-height:1.55}
.gen-wrap .col{flex-direction:column;align-items:stretch}
.gen-wrap .col > label{font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.gen-wrap .grow{flex:1;min-width:110px}
.gen-wrap .w80{width:82px}
.gen-wrap .w64{width:64px}
.gen-wrap .hint{font-size:11px;color:var(--dim-2);line-height:1.6;padding:0;text-align:left}
.gen-wrap .hint.warn{color:#ffc46b}

/* 强度模式分段控件 */
.gen-wrap .seg{display:inline-flex;border:1px solid var(--line-2);border-radius:8px;overflow:hidden}
.gen-wrap .seg button{padding:5px 11px;border:none;border-right:1px solid var(--line-2);background:none;
  color:var(--dim);cursor:pointer;font-size:11px;font-family:inherit;transition:background .12s}
.gen-wrap .seg button:last-child{border-right:none}
.gen-wrap .seg button:hover{background:rgba(255,255,255,.05);color:var(--txt)}
.gen-wrap .seg button.on{background:var(--accent);color:#fff;font-weight:600}

/* LoRA 行 */
.gen-wrap .lrow{display:flex;gap:8px;align-items:center;padding:9px;margin-bottom:8px;
  border:1px solid var(--line-2);border-radius:9px;background:rgba(255,255,255,.014);flex-wrap:wrap}
.gen-wrap .lrow.axis{border-color:#7c5cff66;background:#7c5cff10}
.gen-wrap .lbtn{flex:1;min-width:170px;text-align:left;padding:7px 11px;border:1px solid var(--line-2);
  border-radius:7px;background:#0d1022;color:var(--txt);cursor:pointer;font-size:12px;
  font-family:SF Mono,Cascadia Code,Consolas,monospace;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;transition:border-color .15s}
.gen-wrap .lbtn:hover{border-color:var(--accent)}
.gen-wrap .lbtn.empty{color:var(--dim-2)}
.gen-wrap .del{padding:6px 10px;border:1px solid var(--line-2);border-radius:7px;background:none;
  color:var(--dim);cursor:pointer;font-family:inherit;font-size:12px;transition:all .15s}
.gen-wrap .del:hover{color:#ff7a90;border-color:#ff7a9066}
.gen-wrap .chips{display:flex;gap:5px;flex-wrap:wrap;width:100%;margin-top:7px;padding-left:2px}
.gen-wrap .chip{padding:2px 9px;border-radius:20px;background:#7c5cff22;border:1px solid #7c5cff44;
  color:#b9a6ff;font-size:11px;font-family:SF Mono,Consolas,monospace}
.gen-wrap .chip.off{background:#3ddc9722;border-color:#3ddc9744;color:#7ff0c0}
.gen-wrap .role{font-size:10px;font-weight:700;letter-spacing:.5px;padding:3px 8px;border-radius:5px;
  background:var(--panel-2);color:var(--dim);white-space:nowrap}

/* 右栏 */
.gen-wrap .big{font-size:36px;font-weight:800;line-height:1.05;
  background:linear-gradient(135deg,var(--accent),var(--hot));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.gen-wrap .big small{font-size:14px;font-weight:600;-webkit-text-fill-color:var(--dim)}
.gen-wrap .axisline{font-size:11px;line-height:1.9;color:var(--dim)}
.gen-wrap .axisline b{color:#b9a6ff;font-weight:600}
.gen-wrap .axisline i{color:#7ff0c0;font-style:normal}
.gen-wrap .pbar{height:8px;border-radius:5px;background:#1a1e38;overflow:hidden;margin:12px 0 8px}
.gen-wrap .pbar > i{display:block;height:100%;width:0;
  background:linear-gradient(90deg,var(--accent),var(--hot));transition:width .35s}
.gen-wrap .log{max-height:180px;overflow:auto;font-size:11px;line-height:1.7;
  font-family:SF Mono,Consolas,monospace;color:var(--dim);
  background:#0a0c1a;border-radius:7px;padding:8px 10px;margin-top:9px}
.gen-wrap .msg{font-size:11px;line-height:1.6;margin-top:10px;color:var(--dim)}
.gen-wrap .msg.err{color:#ff8fa3}
.gen-wrap .msg.ok{color:var(--ok)}

/* 组合勾选列表 */
.gen-wrap .combolist{max-height:250px;overflow-y:auto;display:flex;flex-direction:column;gap:2px;
  border:1px solid var(--line-2);border-radius:8px;padding:5px;background:#0a0c1a}
.gen-wrap .comboitem{display:flex;gap:8px;align-items:center;padding:4px 7px;border-radius:6px;
  cursor:pointer;font-size:11px;font-family:SF Mono,Cascadia Code,Consolas,monospace}
.gen-wrap .comboitem:hover{background:rgba(255,255,255,.05)}
.gen-wrap .comboitem input{flex:none;margin:0;cursor:pointer}
.gen-wrap .comboitem .cname{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt)}
.gen-wrap .comboitem.done .cname{color:var(--dim)}

/* LoRA 选择弹窗 */
#gp-ol{position:fixed;inset:0;z-index:400;display:none;align-items:center;justify-content:center;
  background:rgba(5,6,15,.72);backdrop-filter:blur(3px)}
#gp-ol.show{display:flex}
#gp-box{width:920px;max-width:94vw;background:var(--panel);border:1px solid var(--line-2);
  border-radius:14px;padding:16px}
#gp-box h2{margin:0 0 12px;font-size:14px}
#gp-search{width:100%;padding:10px 14px;border:1px solid var(--line-2);border-radius:10px;
  background:#0d1022;color:var(--txt);font-size:13px;font-family:SF Mono,Consolas,monospace}
#gp-search:focus{outline:none;border-color:var(--accent)}
.gp-tops{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
#gp-list{max-height:46vh;overflow-y:auto;display:flex;flex-direction:column;gap:2px;margin-top:6px}
.gp-item{display:flex;gap:10px;align-items:center;padding:7px 11px;border-radius:7px;cursor:pointer;
  font-size:12px;font-family:SF Mono,Cascadia Code,Consolas,monospace;transition:background .12s}
.gp-item:hover{background:rgba(255,255,255,.05)}
.gp-path{flex:1;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gp-val{color:var(--ok);font-weight:600}
.gp-item img{width:34px;height:34px;object-fit:cover;border-radius:5px;background:#0d1022;flex:none}
"""

BODY = r"""
<div class="gen-wrap">
  <div class="gen-col">

    <div class="card">
      <h3>任务基础</h3>
      <div class="row">
        <label>任务名</label>
        <input type="text" id="g-name" class="grow" placeholder="LoRA矩阵_日期_时间" />
      </div>
      <div class="row">
        <label>模型</label>
        <select id="g-model" class="grow"></select>
        <button class="btn ghost" onclick="genLoadModels()">⟳</button>
      </div>
      <div class="row">
        <label>CLIP</label>
        <select id="g-clip" class="grow"></select>
        <button class="btn ghost" onclick="genLoadModels()">⟳</button>
      </div>
      <div class="row">
        <label>VAE</label>
        <select id="g-vae" class="grow"></select>
        <button class="btn ghost" onclick="genLoadModels()">⟳</button>
      </div>
      <div class="msg" id="g-srcmsg" style="margin:2px 0 0"></div>
      <div class="row">
        <label>尺寸</label>
        <input type="number" id="g-w" class="w80" step="8" />
        <span class="tag">×</span>
        <input type="number" id="g-h" class="w80" step="8" />
        <button class="btn ghost" onclick="genSize(832,1216)">832×1216</button>
        <button class="btn ghost" onclick="genSize(896,1152)">896×1152</button>
        <button class="btn ghost" onclick="genSize(1024,1024)">1024²</button>
      </div>
      <div class="row">
        <label>采样</label>
        <span class="tag">steps</span><input type="number" id="g-steps" class="w64" />
        <span class="tag">cfg</span><input type="number" id="g-cfg" class="w64" step="0.1" />
        <span class="tag">batch</span><input type="number" id="g-batch" class="w64" />
      </div>
      <div class="row">
        <label>种子</label>
        <input type="number" id="g-seed" class="grow" />
        <button class="btn ghost" onclick="genRollSeed()">🎲 换一个</button>
      </div>
      <div class="hint">固定种子才能保证「预估 = 实际」，也方便重跑复现。</div>
    </div>

    <div class="card">
      <h3>提示词</h3>
      <div class="row col">
        <label>通用提示词</label>
        <textarea id="g-pos" rows="3"></textarea>
      </div>
      <div class="row col">
        <label>负面提示词</label>
        <textarea id="g-neg" rows="4"></textarea>
      </div>
      <div class="row col">
        <label>场景（一行一个）</label>
        <textarea id="g-scenes" rows="4"></textarea>
        <div class="hint" id="g-scene-count"></div>
      </div>
    </div>

    <div class="card">
      <h3>常驻 LoRA</h3>
      <div class="sub">所有组合都会加载（例如 turbo 加速器）。强度设 0 = 不加载、也不加触发词。</div>
      <div id="g-fixed"></div>
      <button class="btn ghost" onclick="genAddFixed()">+ 添加常驻 LoRA</button>
    </div>

    <div class="card">
      <h3>矩阵 LoRA · 被测维度</h3>
      <div class="sub">强度模式决定它是否撑大组合数：<b>固定</b>不进网格（用来控制出图量），<b>范围/列表</b>才成为轴。</div>
      <div id="g-matrix"></div>
      <button class="btn ghost" onclick="genAddMatrix()">+ 添加矩阵 LoRA</button>
      <div class="row" style="margin-top:12px">
        <label style="min-width:auto">
          <input type="checkbox" id="g-baseline" checked onchange="genEstimate()" />
          包含全零基线
        </label>
        <span class="hint">生成「所有被测 LoRA 都不加」的对照组（查看器里绿框标出）</span>
      </div>
    </div>

  </div>

  <div class="gen-col">

    <div class="card">
      <h3>预估</h3>
      <div class="big" id="g-total">–</div>
      <div class="hint" id="g-detail" style="margin-top:6px">…</div>
      <div class="axisline" id="g-axes" style="margin-top:10px"></div>
    </div>

    <div class="card">
      <h3>组合选择</h3>
      <button class="btn ghost" style="width:100%;text-align:left" onclick="genOpenCombos()">
        🎯 选择要跑的组合 <span id="g-selstat" style="color:var(--dim-2)"></span>
      </button>
      <div class="hint" style="margin-top:9px">默认全选。取消勾选的不会跑；标 ✅ 的已跑完，执行时会自动跳过。</div>
    </div>

    <div class="card">
      <h3>配置预设</h3>
      <button class="btn ghost" style="width:100%;text-align:left" onclick="genOpenPresets()">
        📁 浏览 / 保存预设 <span id="g-preset-cur" style="color:var(--dim-2)"></span>
      </button>
      <div class="hint" style="margin-top:9px">预设是一份标准的生成器配置，可直接喂给 matrix_generator.py 的 CLI。</div>
    </div>

    <div class="card">
      <h3>执行</h3>
      <button class="btn" id="g-run" style="width:100%" onclick="genRun()">▶ 生成并执行</button>
      <label class="row" style="margin:9px 0 0;min-width:auto;gap:7px">
        <input type="checkbox" id="g-skipdone" checked />
        <span class="hint" style="margin:0">跳过已完成的（断点续跑）</span>
      </label>
      <button class="btn ghost" id="g-only" style="width:100%;margin-top:8px" onclick="genOnly()">仅生成任务清单</button>
      <div id="g-progress" class="hidden" style="margin-top:12px">
        <div class="pbar"><i id="g-bar"></i></div>
        <div class="hint" id="g-pinfo"></div>
        <button class="btn ghost" style="width:100%;margin-top:8px" onclick="genStop()">⏸ 暂停（已完成的不丢）</button>
        <div class="log" id="g-log"></div>
      </div>
      <div class="msg" id="g-runmsg"></div>
      <div class="msg" id="g-depmsg" style="white-space:pre-line"></div>
    </div>

  </div>
</div>

<div id="gp-ol" onclick="if(event.target===this)genClosePicker()">
  <div id="gp-box">
    <h2>选择 LoRA</h2>
    <input id="gp-search" placeholder="搜索 —— 文件名或路径，空格分词（例：artist howan）" oninput="genFilterLoras()" />
    <div class="gp-tops" id="gp-tops"></div>
    <div id="gp-list"></div>
    <div style="text-align:right;margin-top:12px">
      <button class="btn ghost" onclick="genClosePicker()">取消</button>
    </div>
  </div>
</div>

<div id="gpr-ol" style="position:fixed;inset:0;z-index:400;display:none;align-items:center;
     justify-content:center;background:rgba(5,6,15,.74);backdrop-filter:blur(3px)"
     onclick="if(event.target===this)genClosePresets()">
  <div style="width:880px;max-width:94vw;max-height:88vh;display:flex;flex-direction:column;
       background:var(--panel);border:1px solid var(--line-2);border-radius:14px;padding:16px">
    <h2 style="margin:0 0 12px;font-size:14px">配置预设</h2>
    <input id="gpr-search" placeholder="搜索预设名 / 任务名 / 模型 / LoRA 名…（空格分词）"
           style="width:100%;padding:10px 14px;border:1px solid var(--line-2);border-radius:10px;
                  background:#0d1022;color:var(--txt);font-size:13px;font-family:inherit"
           oninput="genRenderPresets()" />
    <div id="gpr-list" style="flex:1;overflow-y:auto;margin-top:12px;display:flex;flex-direction:column;gap:8px"></div>
    <div style="display:flex;gap:8px;align-items:center;margin-top:14px;padding-top:12px;
         border-top:1px solid var(--line)">
      <input id="gpr-name" placeholder="新预设名称（留空则用任务名）"
             style="flex:1;padding:9px 12px;border:1px solid var(--line-2);border-radius:9px;
                    background:#0d1022;color:var(--txt);font-size:12px;font-family:inherit" />
      <button class="btn" onclick="genSavePreset()">💾 保存当前配置</button>
      <button class="btn ghost" onclick="genClosePresets()">关闭</button>
    </div>
  </div>
</div>

<div id="gcb-ol" style="position:fixed;inset:0;z-index:410;display:none;align-items:center;
     justify-content:center;background:rgba(5,6,15,.74);backdrop-filter:blur(3px)"
     onclick="if(event.target===this)genCloseCombos()">
  <div style="width:900px;max-width:95vw;height:86vh;display:flex;flex-direction:column;
       background:var(--panel);border:1px solid var(--line-2);border-radius:14px;padding:16px">

    <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:11px">
      <h2 style="margin:0;font-size:14px">选择要跑的组合</h2>
      <span id="gcb-stat" style="margin-left:auto;font-size:11px;color:var(--dim)"></span>
    </div>

    <!-- 只留一行常驻控件：搜索 + 筛选开关 + 全选/全不选 -->
    <div style="display:flex;gap:7px">
      <input id="gcb-search" placeholder="搜索组合名 / 维度 / 数值…（空格分词，如 howan 0.5）"
             style="flex:1;padding:9px 13px;border:1px solid var(--line-2);border-radius:9px;
                    background:#0d1022;color:var(--txt);font-size:13px;font-family:inherit"
             oninput="genRenderCombos()" />
      <button class="btn ghost" id="gcb-filter-btn" onclick="genToggleFilters()">筛选 ▾</button>
      <button class="btn ghost" onclick="genSelectAll(true)">全选</button>
      <button class="btn ghost" onclick="genSelectAll(false)">全不选</button>
    </div>

    <!-- 筛选区：默认收起，展开后每维一行、值可多选叠加 -->
    <div id="gcb-dims" style="display:none;margin-top:10px;padding:10px 12px;border:1px solid var(--line-2);
         border-radius:9px;background:rgba(255,255,255,.02);max-height:30vh;overflow-y:auto"></div>

    <div id="g-combos" style="flex:1;overflow-y:auto;margin-top:10px;display:flex;
         flex-direction:column;gap:2px;border:1px solid var(--line-2);border-radius:9px;
         padding:6px;background:#0a0c1a;user-select:none"></div>

    <div style="display:flex;align-items:center;gap:7px;margin-top:12px;padding-top:12px;
         border-top:1px solid var(--line)">
      <select id="gcb-selset" style="padding:6px 10px;border:1px solid var(--line-2);border-radius:8px;
              background:#0d1022;color:var(--txt);font-size:12px;font-family:inherit;min-width:150px">
        <option value="">选择集…</option>
      </select>
      <button class="btn ghost" onclick="genApplySelSet()">载入</button>
      <button class="btn ghost" onclick="genSaveSelSet()">存为选择集</button>
      <button class="btn ghost" onclick="genDeleteSelSet()">删除</button>
      <span style="flex:1"></span>
      <button class="btn" onclick="genCloseCombos()">完成</button>
    </div>
  </div>
</div>

<script>
// ══ 生成页签状态 ══
var genFixed  = [];   // {lora, strength, trigger}
var genMatrix = [];   // {lora, trigger, mode:'fixed'|'range'|'list', p1,p2,p3}
var genAllLoras = [], genAllModels = [], genTopFilter = '', genReady = false;
var genPickerTarget = null, genTimer = null, genPollTimer = null;

function gv(id){var e=document.getElementById(id);return e?e.value:''}
function gi(id,d){var n=parseInt(gv(id));return isNaN(n)?d:n}
function gf(id,d){var n=parseFloat(gv(id));return isNaN(n)?d:n}
function gstamp(){ return fmtTime(null, 'compact') }   // 见 gui.py 的 fmtTime
function gRoll(){return Math.floor(Math.random()*2147483646)+1}

// ══ 初始化（外壳的 switchTab 首次切到本页时调用）══
window.genInit = function(){
  if(genReady) return;
  genReady = true;
  document.getElementById('g-name').value = 'LoRA矩阵_' + gstamp();
  document.getElementById('g-w').value = 896;
  document.getElementById('g-h').value = 1152;
  document.getElementById('g-steps').value = 10;
  document.getElementById('g-cfg').value = 1;
  document.getElementById('g-batch').value = 1;
  document.getElementById('g-seed').value = gRoll();
  document.getElementById('g-pos').value =
    'masterpiece, best quality, amazing quality, absurdres, highres, newest, score_9, score_8, score_7, year2025';
  // 默认模板：读 example_config.json，让用户一进来就有内容可改
  api('GET','/api/example-config').then(function(d){
    if(d && d.ok && d.config) genApplyConfig(d.config, true);
    else { genAddFixed(); genAddMatrix(); }
    genLoadModels(); genLoadPresets(); genCheckNodes(); genEstimate();
  });
  ['g-name','g-w','g-h','g-steps','g-cfg','g-batch','g-seed','g-pos','g-neg','g-scenes']
    .forEach(function(id){document.getElementById(id).addEventListener('input', genEstimate)});
};

// ══ 尺寸 / 种子 ══
function genSize(w,h){document.getElementById('g-w').value=w;document.getElementById('g-h').value=h;genEstimate()}
function genRollSeed(){document.getElementById('g-seed').value=gRoll()}
// 种子框为空时摇**一次**并写回输入框。
// 不这么做的话 genEstimate 每 300ms 读一次配置就换一个种子 →
// 「预估」和「实际跑」用的不是同一个 seed，断点续跑的比对也就永远对不上。
function genEnsureSeed(){
  var el = document.getElementById('g-seed');
  var v = parseInt(el.value);
  if (isNaN(v) || v <= 0) { v = gRoll(); el.value = v }
  return v;
}

// ══ 依赖自检 ══
// workflow.json 用了 5 个非内置节点，分别来自 4 个插件。
// 缺任何一个都会在跑到一半时失败 —— 不如一进页面就说清楚。
function genCheckNodes(){
  var el = document.getElementById("g-depmsg");
  if (!el) return;
  api('GET', '/api/check-nodes').then(function(d){
    if (!d || !d.ok) { el.className = "msg"; el.textContent = ""; return }
    // 路径先报 —— 没配好时 LoRA 列表是空的，比缺插件更早卡住，且症状更费解
    if (d.path && d.path.fallback) {
      el.className = "msg err";
      el.textContent = "⚠ ComfyUI 路径用了包内兜底常量（作者本机路径），在你机器上不存在，"
        + "LoRA 列表会是空的。\n"
        + "　当前解析： " + (d.path.dir || "(无)") + "\n"
        + "　改法：设环境变量 COMFYUI_DIR，或写 config.json";
      return;
    }
    if (!d.online) {
      el.className = "msg";
      el.textContent = "ComfyUI 没在运行（启动后会自检必需插件）";
      return;
    }
    if (!d.missing || !d.missing.length) {
      el.className = "msg ok";
      el.textContent = "✓ 必需插件齐全（" + d.checked + " 个节点）";
      return;
    }
    el.className = "msg err";
    el.textContent = "⚠ 缺少 " + d.missing.length + " 个节点，生图会失败：\n"
      + d.missing.map(function(m){ return "　" + m.node + "　← 装 " + m.plugin }).join("\n");
  });
}

// ══ 模型下拉 ══
// 用一个模型列表填某个下拉（按 group 分 optgroup）。
// 底模 / CLIP / VAE 三处共用同一套填法，只是数据源不同。
function genFillSelect(id, list){
  var sel = document.getElementById(id);
  if (!sel) return;
  var keep = sel.value;                 // 重新加载时尽量保住当前选择
  sel.innerHTML = '';
  var groups = {};
  (list || []).forEach(function(m){ (groups[m.group] = groups[m.group] || []).push(m.name) });
  Object.keys(groups).forEach(function(g){
    var og = document.createElement('optgroup'); og.label = g;
    groups[g].forEach(function(n){
      var o = document.createElement('option'); o.value = n; o.textContent = n; og.appendChild(o);
    });
    sel.appendChild(og);
  });
  if (keep) genSelectValue(id, keep);
}

// 选中某个值；下拉里没有就补一个「(配置里指定)」选项 ——
// 否则载入一份指定了别处模型的预设时，用户会以为自己的配置丢了。
function genSelectValue(id, value){
  if (!value) return;
  var sel = document.getElementById(id);
  if (!sel) return;
  var found = Array.prototype.some.call(sel.options, function(o){ return o.value === value });
  if (!found) {
    var o = document.createElement('option');
    o.value = value;
    o.textContent = value + '  (配置里指定)';
    sel.appendChild(o);
  }
  sel.value = value;
}

// 清单是哪来的 —— 用户看到空列表时能立刻知道为什么
function genModelSource(src){
  var el = document.getElementById('g-srcmsg');
  if (!el) return;
  var txt = {
    comfyui: '模型清单来自运行中的 ComfyUI',
    disk:    '模型清单来自磁盘扫描（ComfyUI 未运行）',
    none:    '拿不到模型清单 —— ComfyUI 没运行，磁盘路径也没配'
  }[src];
  if (!txt) { el.className = 'msg'; el.textContent = ''; return }
  el.className = 'msg ' + (src === 'comfyui' ? 'ok' : (src === 'disk' ? '' : 'err'));
  el.textContent = txt;
}

function genLoadModels(){
  api('GET','/api/models').then(function(d){
    genAllModels = (d && d.files) || [];
    genFillSelect('g-model', d && d.files);   // 底模 / UNet / checkpoint
    genFillSelect('g-clip',  d && d.clips);   // 文本编码器
    genFillSelect('g-vae',   d && d.vaes);    // VAE
    genModelSource(d && d.source);
    if(d && d.comfyui_online === false) genMsg('ComfyUI 没在运行，执行前请先启动它', 'err');
  });
}

// ══ 常驻 LoRA ══
function genAddFixed(){ genFixed.push({lora:'',strength:1,trigger:''}); genRenderFixed(); genEstimate() }
function genRenderFixed(){
  var c = document.getElementById('g-fixed'); c.innerHTML = '';
  if(!genFixed.length){ c.innerHTML = '<div class="hint" style="margin-bottom:8px">（无）</div>'; return }
  genFixed.forEach(function(r,i){
    var d = document.createElement('div'); d.className = 'lrow';
    d.innerHTML =
      '<span class="role">常驻</span>' +
      '<button class="lbtn'+(r.lora?'':' empty')+'">'+esc(r.lora||'点击选择 LoRA…')+'</button>' +
      '<span class="tag">强度</span>' +
      '<input type="number" class="w64" step="0.01" min="0" max="2" value="'+r.strength+'" />' +
      '<input type="text" class="grow" placeholder="触发词（可选）" value="'+esc(r.trigger||'')+'" />' +
      '<button class="del">✕</button>';
    var inp = d.querySelectorAll('input');
    var btn = d.querySelector('.lbtn');
    if(btn) btn.onclick = function(){ genOpenPicker({kind:'fixed', idx:i}) };
    inp[0].onchange = function(){ r.strength = parseFloat(this.value)||0; genEstimate() };
    inp[1].oninput  = function(){ r.trigger = this.value; genEstimate() };
    d.querySelector('.del').onclick = function(){ genFixed.splice(i,1); genRenderFixed(); genEstimate() };
    c.appendChild(d);
  });
}

// ══ 矩阵 LoRA ══
function genAddMatrix(){ genMatrix.push({lora:'',trigger:'',mode:'range',p1:'0',p2:'1',p3:'3'}); genRenderMatrix(); genEstimate() }
function genRenderMatrix(){
  var c = document.getElementById('g-matrix'); c.innerHTML = '';
  if(!genMatrix.length){ c.innerHTML = '<div class="hint" style="margin-bottom:8px">（无 —— 全部为固定值时只出 1 张对照图）</div>'; return }
  genMatrix.forEach(function(r,i){
    var d = document.createElement('div');
    d.className = 'lrow' + (genStrengthCount(r) > 1 ? ' axis' : '');
    var isFixed = (r.mode === 'fixed');
    var params = '';
    if(r.mode === 'fixed'){
      params = '<span class="tag">值</span><input type="number" class="w64" step="0.01" value="'+r.p1+'" data-p="1" />';
    } else if(r.mode === 'range'){
      params = '<span class="tag">最小</span><input type="number" class="w64" step="0.01" value="'+r.p1+'" data-p="1" />' +
               '<span class="tag">最大</span><input type="number" class="w64" step="0.01" value="'+r.p2+'" data-p="2" />' +
               '<span class="tag">段数</span><input type="number" class="w64" min="1" value="'+r.p3+'" data-p="3" />';
    } else {
      params = '<span class="tag">列表</span><input type="text" class="grow" value="'+esc(r.p1)+'" data-p="1" placeholder="0, 0.5, 1" />';
    }
    d.innerHTML =
      '<span class="role" style="background:'+(isFixed?'var(--panel-2)':'#7c5cff33')+';color:'+(isFixed?'var(--dim)':'#b9a6ff')+'">'+(isFixed?'固定':'轴')+'</span>' +
      '<button class="lbtn'+(r.lora?'':' empty')+'">'+esc(r.lora||'点击选择 LoRA…')+'</button>' +
      '<input type="text" class="grow" placeholder="触发词" value="'+esc(r.trigger||'')+'" data-t="1" />' +
      '<button class="del">✕</button>' +
      '<div class="chips" style="width:100%"></div>' +
      '<div style="display:flex;gap:8px;align-items:center;width:100%;margin-top:7px">' +
        '<span class="seg">' +
          '<button data-m="fixed"'+(r.mode==='fixed'?' class="on"':'')+'>固定</button>' +
          '<button data-m="range"'+(r.mode==='range'?' class="on"':'')+'>范围</button>' +
          '<button data-m="list"' +(r.mode==='list' ?' class="on"':'')+'>列表</button>' +
        '</span>' + params +
      '</div>';

    var btn = d.querySelector('.lbtn');
    if(btn) btn.onclick = function(){ genOpenPicker({kind:'matrix', idx:i}) };
    var trg = d.querySelector('input[data-t]');
    if(trg) trg.oninput = function(){ r.trigger = this.value; genEstimate() };
    d.querySelectorAll('.seg button').forEach(function(b){
      b.onclick = function(){ r.mode = b.getAttribute('data-m'); genRenderMatrix(); genEstimate() };
    });
    d.querySelectorAll('input[data-p]').forEach(function(inp){
      inp.oninput = function(){ r['p'+inp.getAttribute('data-p')] = this.value; genChips(d, r); genEstimate() };
    });
    d.querySelector('.del').onclick = function(){ genMatrix.splice(i,1); genRenderMatrix(); genEstimate() };
    genChips(d, r);
    c.appendChild(d);
  });
}

// 把强度配置展开成 chips —— 让「会不会进网格」一眼可见
function genStrengthList(r){
  if(r.mode === 'fixed'){ var v = parseFloat(r.p1); return isNaN(v) ? [] : [v] }
  if(r.mode === 'range'){
    var mn = parseFloat(r.p1), mx = parseFloat(r.p2), n = Math.max(1, parseInt(r.p3)||1);
    if(isNaN(mn)||isNaN(mx)) return [];
    if(n <= 1 || mn === mx) return [isNaN(mn)?mx:mn];
    var st = (mx-mn)/(n-1), out = [];
    for(var i=0;i<n;i++) out.push(Math.round((mn+i*st)*10000)/10000);
    return out;
  }
  return String(r.p1||'').split(/[,，\s]+/).map(Number).filter(function(x){return !isNaN(x)});
}
function genStrengthCount(r){ return genStrengthList(r).length }
function genChips(host, r){
  var box = host.querySelector('.chips'); if(!box) return;
  var vals = genStrengthList(r);
  box.innerHTML = '';
  if(!vals.length){ box.innerHTML = '<span class="hint warn">强度为空，这一维会被忽略</span>'; return }
  if(r.mode === 'range' && parseInt(r.p3) === 1)
    box.innerHTML = '<span class="hint warn">段数 1 不会形成轴（等价于固定值）</span>';
  var multi = vals.length > 1;
  vals.forEach(function(v){
    var s = document.createElement('span'); s.className = 'chip' + (multi ? '' : ' off');
    s.textContent = v; box.appendChild(s);
  });
  if(!multi){
    var t = document.createElement('span'); t.className = 'hint'; t.style.alignSelf = 'center';
    t.textContent = '不进网格'; box.appendChild(t);
  }
}

// ══ 读 / 写配置 ══
function genReadConfig(){
  var scenes = gv('g-scenes').split('\n').map(function(s){return s.trim()}).filter(Boolean);
  return {
    '任务名': gv('g-name') || ('LoRA矩阵_' + gstamp()),
    '通用提示词': gv('g-pos'),
    '负面提示词': gv('g-neg'),
    '场景': scenes.length ? scenes : [''],
    '尺寸': {'宽': gi('g-w',896), '高': gi('g-h',1152)},
    'base_model': gv('g-model'),
    'clip_name': gv('g-clip'),
    'vae_name': gv('g-vae'),
    'steps': gi('g-steps',10),
    'cfg': gf('g-cfg',1),
    'batch': Math.max(1, gi('g-batch',1)),
    'seed': genEnsureSeed(),
    '包含全零基线': document.getElementById('g-baseline').checked,
    '常驻lora': genFixed.filter(function(r){return r.lora}).map(function(r){
      return {'lora': r.lora, '强度': parseFloat(r.strength)||0, '触发词': r.trigger||''};
    }),
    'lora矩阵': genMatrix.filter(function(r){return r.lora}).map(function(r){
      var st;
      if(r.mode === 'fixed')      st = parseFloat(r.p1) || 0;
      else if(r.mode === 'range') st = {'最小':parseFloat(r.p1)||0, '最大':parseFloat(r.p2)||0,
                                        '段数':Math.max(1, parseInt(r.p3)||1)};
      else                        st = genStrengthList(r);
      return {'lora': r.lora, '触发词': r.trigger||'', '强度': st};
    })
  };
}
function genApplyConfig(cfg, keepName){
  if(!cfg) return;
  if(!keepName && cfg['任务名']) document.getElementById('g-name').value = cfg['任务名'];
  document.getElementById('g-pos').value = cfg['通用提示词'] || '';
  document.getElementById('g-neg').value = cfg['负面提示词'] || '';
  document.getElementById('g-scenes').value = (cfg['场景'] || []).join('\n');
  var sz = cfg['尺寸'] || {};
  document.getElementById('g-w').value = sz['宽'] || 896;
  document.getElementById('g-h').value = sz['高'] || 1152;
  genSelectValue('g-model', cfg['base_model']);
  genSelectValue('g-clip',  cfg['clip_name']);
  genSelectValue('g-vae',   cfg['vae_name']);
  document.getElementById('g-steps').value = cfg['steps'] !== undefined ? cfg['steps'] : 10;
  document.getElementById('g-cfg').value   = cfg['cfg']   !== undefined ? cfg['cfg']   : 1;
  document.getElementById('g-batch').value = cfg['batch'] !== undefined ? cfg['batch'] : 1;
  document.getElementById('g-seed').value  = cfg['seed']  !== undefined ? cfg['seed']  : gRoll();
  document.getElementById('g-baseline').checked = cfg['包含全零基线'] !== false;

  genFixed = (cfg['常驻lora'] || []).map(function(r){
    return {lora:r['lora']||'', strength:(r['强度']!==undefined?r['强度']:1), trigger:r['触发词']||''};
  });
  genMatrix = (cfg['lora矩阵'] || cfg['loras'] || []).map(function(r){
    var st = r['强度'], mode = 'fixed', p1 = '1', p2 = '1', p3 = '3';
    if(typeof st === 'number'){ mode = 'fixed'; p1 = String(st) }
    else if(Array.isArray(st)){ mode = 'list'; p1 = st.join(', ') }
    else if(st && typeof st === 'object'){
      mode = 'range'; p1 = String(st['最小']!==undefined?st['最小']:0);
      p2 = String(st['最大']!==undefined?st['最大']:1); p3 = String(st['段数']||3);
    }
    return {lora:r['lora']||'', trigger:r['触发词']||'', mode:mode, p1:p1, p2:p2, p3:p3};
  });
  genRenderFixed(); genRenderMatrix(); genEstimate();
}

// ══ 组合勾选 ══
var genCombos = [];        // [{key, combo, scene, done, sel}]
var genComboInit = false;  // 首次拿到列表时默认全选，之后保留用户勾选

// ── 组合选择弹窗 ──
var genDimFilter = {};   // {维度名: {值: 1}} —— 多维多值叠加（AND）
var genLastIdx = -1;     // Shift 连选锚点
var genDrag = null;      // {val: bool} 拖拽刷选中
var genSelSets = {};     // {名称: [key,...]} 存 localStorage

function genOpenCombos(){
  document.getElementById("gcb-ol").style.display = "flex";
  document.getElementById("gcb-search").value = "";
  genDimFilter = {}; genLastIdx = -1; genDrag = null;
  genLoadSelSets();
  genRenderCombos();
}
function genCloseCombos(){
  document.getElementById("gcb-ol").style.display = "none";
  genSelStat();
}
function genToggleFilters(){
  var el = document.getElementById("gcb-dims");
  var open = el.style.display !== "none";
  el.style.display = open ? "none" : "block";
  document.getElementById("gcb-filter-btn").textContent = open ? "筛选 ▾" : "筛选 ▴";
}
function genDimActive(n){ return genDimFilter[n] ? Object.keys(genDimFilter[n]).length : 0 }

// 搜索 + 维度筛选 共同决定的可见集合
function genVisibleCombos(){
  var q = document.getElementById("gcb-search").value.toLowerCase().trim();
  var terms = q ? q.split(/\s+/) : [];
  return genCombos.filter(function(c){
    for (var n in genDimFilter) {                 // 多维度 AND
      var want = Object.keys(genDimFilter[n]);
      if (!want.length) continue;
      var v = (c.coords || {})[n];
      if (v === undefined) return false;
      if (!want.some(function(w){ return valEq(parseFloat(w), v) })) return false;
    }
    if (!terms.length) return true;
    var hay = (c.combo + " " + Object.keys(c.coords || {}).join(" ") + " "
               + Object.values(c.coords || {}).join(" ")).toLowerCase();
    return terms.every(function(t){ return hay.indexOf(t) >= 0 });
  });
}

// 数据改了之后同步 DOM 上的勾选框（拖拽/连选改的是数据）
function genSyncChecks(box, shown){
  var items = box.querySelectorAll('input[type=checkbox]');
  for (var i = 0; i < items.length && i < shown.length; i++) items[i].checked = shown[i].sel;
}

function genRenderCombos(){
  var box = document.getElementById("g-combos");
  if (!box) return;
  genRenderDimFilters();
  if (!genCombos.length) {
    box.innerHTML = '<div class="hint" style="padding:12px">（还没有组合 —— 先配置 LoRA 与强度）</div>';
    genSelStat(); return;
  }
  var shown = genVisibleCombos();
  box.innerHTML = "";
  if (!shown.length) {
    box.innerHTML = '<div class="hint" style="padding:12px">没有匹配的组合</div>';
    genSelStat(); return;
  }
  shown.forEach(function(c, i){
    var d = document.createElement("div");     // 用 div 不用 label —— 交互自己接管
    d.style.cssText = "display:flex;gap:9px;align-items:center;padding:5px 9px;border-radius:6px;"
      + "cursor:pointer;font-size:11px;font-family:SF Mono,Cascadia Code,Consolas,monospace";
    d.onmouseenter = function(){
      this.style.background = "rgba(255,255,255,.05)";
      if (genDrag) { c.sel = genDrag.val; genSyncChecks(box, shown); genSelStat() }
    };
    d.onmouseleave = function(){ this.style.background = "" };
    var cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = c.sel;
    cb.style.cssText = "pointer-events:none;flex:none";
    var nm = document.createElement("span");
    nm.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:"
      + (c.done ? "var(--dim)" : "var(--txt)");
    nm.textContent = c.combo + (c.scene ? "  [场景" + c.scene + "]" : "");
    d.appendChild(cb); d.appendChild(nm);
    if (c.done) { var b = document.createElement("span"); b.textContent = "✅"; d.appendChild(b) }
    if (marks[c.key]) {
      var s = document.createElement("span"); s.textContent = "★"; s.style.color = "#ffd166";
      d.appendChild(s);
    }
    // 多选：Shift 连选 / 按住拖拽刷选
    d.onmousedown = function(ev){
      ev.preventDefault();                       // 别触发文本选择
      if (ev.shiftKey && genLastIdx >= 0 && genLastIdx < shown.length) {
        var a = Math.min(genLastIdx, i), b2 = Math.max(genLastIdx, i);
        for (var k = a; k <= b2; k++) shown[k].sel = c.sel;
      } else {
        c.sel = !c.sel;
        genLastIdx = i;
        genDrag = {val: c.sel};
      }
      genSyncChecks(box, shown);
      genSelStat();
    };
    box.appendChild(d);
  });
  genSelStat();
}
document.addEventListener("mouseup", function(){ genDrag = null });

// 维度筛选：点值多选，多维叠加
function genRenderDimFilters(){
  var box = document.getElementById("gcb-dims");
  if (!box) return;
  var dims = {};
  genCombos.forEach(function(c){
    for (var k in (c.coords || {})) (dims[k] = dims[k] || {})[c.coords[k]] = 1;
  });
  var names = Object.keys(dims);
  if (!names.length) { box.innerHTML = '<div class="hint">还没有维度</div>'; return }
  var anyAct = names.some(function(n){ return genDimActive(n) });
  var h = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:9px">'
        + '<span style="font-size:11px;color:var(--dim)">点值多选，多个维度可叠加</span>'
        + (anyAct ? '<button class="btn ghost" style="padding:2px 9px;font-size:11px;margin-left:auto" '
            + 'onclick="genClearDimFilter()">清空筛选</button>' : '')
        + '</div>';
  names.forEach(function(n){
    var act = genDimActive(n);
    h += '<div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin-bottom:7px">';
    h += '<span style="font-size:11px;min-width:135px;overflow:hidden;text-overflow:ellipsis;'
       + 'white-space:nowrap;color:' + (act ? '#ffd166' : 'var(--dim)') + '">'
       + esc(n) + (act ? ' (' + act + ')' : '') + '</span>';
    Object.keys(dims[n]).map(parseFloat).sort(function(a, b){ return a - b }).forEach(function(v){
      var on = genDimFilter[n] && genDimFilter[n][String(v)];
      h += '<button class="btn ghost" style="padding:3px 11px;font-size:11px'
         + (on ? ';border-color:#ffd166;color:#ffd166' : '') + '" '
         + 'onclick="genToggleDimVal(\'' + escAttr(n) + '\',' + v + ')">'
         + formatStrength(v) + '</button>';
    });
    h += '</div>';
  });
  box.innerHTML = h;
}

function genToggleDimVal(dim, val){
  var set = genDimFilter[dim] = genDimFilter[dim] || {};
  var k = String(val);
  if (set[k]) delete set[k]; else set[k] = 1;
  if (!Object.keys(set).length) delete genDimFilter[dim];
  genRenderCombos();
}
function genClearDimFilter(){ genDimFilter = {}; genLastIdx = -1; genRenderCombos() }

function genSelStat(){
  var sel = genCombos.filter(function(c){ return c.sel }).length;
  var done = genCombos.filter(function(c){ return c.done }).length;
  var n = genCombos.length;
  var a = document.getElementById("g-selstat");
  if (a) a.textContent = n ? ('（已选 ' + sel + '/' + n + '）') : '';
  var b = document.getElementById("gcb-stat");
  if (b) b.textContent = n
    ? ('已选 ' + sel + ' / ' + n + ' 个组合' + (done ? ' · 其中 ' + done + ' 个已完成' : ''))
    : '还没有组合';
}

// 只作用于「当前可见」的（搜索 + 维度筛选之后）
function genSelectAll(on){
  genVisibleCombos().forEach(function(c){ c.sel = on });
  genRenderCombos();
}

// ── 选择集（存 localStorage）──
function genLoadSelSets(){
  try { genSelSets = JSON.parse(localStorage.getItem("mx_selsets") || "{}") || {} }
  catch (e) { genSelSets = {} }
  var sel = document.getElementById("gcb-selset");
  sel.innerHTML = '<option value="">选择集…</option>';
  Object.keys(genSelSets).sort().forEach(function(n){
    var o = document.createElement("option");
    o.value = n; o.textContent = n + "  (" + genSelSets[n].length + ")";
    sel.appendChild(o);
  });
}
function genSaveSelSet(){
  var keys = genCombos.filter(function(c){ return c.sel }).map(function(c){ return c.key });
  if (!keys.length) { genMsg("当前没勾选任何组合", "err"); return }
  var n = prompt("选择集名称：", "选择集 " + keys.length + " 个");
  if (!n) return;
  genSelSets[n] = keys;
  try { localStorage.setItem("mx_selsets", JSON.stringify(genSelSets)) } catch (e) {}
  genLoadSelSets();
  document.getElementById("gcb-selset").value = n;
  genMsg("已存选择集「" + n + "」（" + keys.length + " 个）", "ok");
}
function genApplySelSet(){
  var n = document.getElementById("gcb-selset").value;
  if (!n) { genMsg("先在下拉里选一个选择集", "err"); return }
  var want = {};
  (genSelSets[n] || []).forEach(function(k){ want[k] = 1 });
  genCombos.forEach(function(c){ c.sel = !!want[c.key] });
  genRenderCombos();
  genMsg("已载入选择集「" + n + "」", "ok");
}
function genDeleteSelSet(){
  var n = document.getElementById("gcb-selset").value;
  if (!n) { genMsg("先在下拉里选一个选择集", "err"); return }
  if (!confirm("删除选择集「" + n + "」？")) return;
  delete genSelSets[n];
  try { localStorage.setItem("mx_selsets", JSON.stringify(genSelSets)) } catch (e) {}
  genLoadSelSets();
  genMsg("已删除选择集「" + n + "」", "ok");
}

// ══ 预估（debounce → 后端试算）══
var genEstTimer = null;
function genEstimate(){
  var n = gv('g-scenes').split('\n').filter(function(s){return s.trim()}).length;
  document.getElementById('g-scene-count').textContent = n + ' 个场景';
  clearTimeout(genEstTimer);
  genEstTimer = setTimeout(function(){
    api('POST','/api/generate-preview',{config: genReadConfig()}).then(function(d){
      if(!d || !d.ok){ document.getElementById('g-total').textContent = '–';
        document.getElementById('g-detail').textContent = (d && d.error) || '配置有误'; return }
      document.getElementById('g-total').innerHTML = d.total + '<small> 张</small>';
      document.getElementById('g-detail').textContent =
        d.axes && Object.keys(d.axes).length
          ? (Object.keys(d.axes).length + ' 个轴 × ' +
             Object.keys(d.axes).map(function(k){return d.axes[k].length}).join('×') +
             ' = ' + d.combos + ' 组合 × ' + d.scenes + ' 场景 × batch ' + d.batch)
          : '无轴（只有固定值）→ 每个场景 1 张';
      var ax = document.getElementById('g-axes'), h = '';
      var ks = Object.keys(d.axes || {});
      if(ks.length){
        h += '<div>查看器里可作轴：</div>';
        ks.forEach(function(k, i){
          h += '<div><b>' + (i===0?'X':i===1?'Y':'·') + ' ' + esc(k) + '</b> &nbsp;' +
               d.axes[k].map(function(v){return '<i>'+v+'</i>'}).join(' ') + '</div>';
        });
      }
      if(d.fixed_dims && d.fixed_dims.length)
        h += '<div style="margin-top:6px">固定值（不进网格）：' + d.fixed_dims.map(esc).join('、') + '</div>';
      if(d.warn) h += '<div class="hint warn" style="margin-top:6px">⚠ ' + esc(d.warn) + '</div>';
      ax.innerHTML = h;

      // 组合清单：首次默认全选，之后保留用户的勾选状态
      if(d.combo_list){
        var prev = {};
        genCombos.forEach(function(c){ prev[c.key] = c.sel });
        genCombos = d.combo_list.map(function(c){
          return {key:c.key, combo:c.combo, scene:c.scene, done:!!c.done,
                  coords:c.coords || {},   // ← 必须带上：维度筛选、搜索都靠它
                  sel: genComboInit ? (prev[c.key] !== false) : true};
        });
        genComboInit = true;
        genRenderCombos();
      }
    });
  }, 300);
}

// ══ LoRA 选择器 ══
function genOpenPicker(target){
  genPickerTarget = target;
  document.getElementById('gp-ol').classList.add('show');
  document.getElementById('gp-search').value = '';
  genTopFilter = '';
  var load = function(){
    document.getElementById('gp-list').innerHTML = '<div class="hint" style="padding:10px">载入中…</div>';
    api('GET','/api/loras').then(function(d){
      genAllLoras = (d && d.files) || [];
      var tops = {}, seen = [];
      genAllLoras.forEach(function(f){ if(f.top && !tops[f.top]){ tops[f.top]=1; seen.push(f.top) } });
      seen.sort();
      var tc = document.getElementById('gp-tops'); tc.innerHTML = '';
      seen.forEach(function(t){
        var b = document.createElement('button');
        b.className = 'btn ghost'; b.textContent = t;
        b.onclick = function(){
          genTopFilter = (genTopFilter === t) ? '' : t;
          tc.querySelectorAll('button').forEach(function(x){ x.style.borderColor=''; x.style.color='' });
          if(genTopFilter){ b.style.borderColor='var(--accent)'; b.style.color='var(--txt)' }
          genFilterLoras();
        };
        tc.appendChild(b);
      });
      genFilterLoras();
    });
  };
  load();
}
function genClosePicker(){ document.getElementById('gp-ol').classList.remove('show'); genPickerTarget = null }
function genFilterLoras(){
  var q = document.getElementById('gp-search').value.toLowerCase().trim();
  var terms = q ? q.split(/\s+/) : [];
  var files = genAllLoras.filter(function(f){
    if(genTopFilter && f.top !== genTopFilter) return false;
    if(!terms.length) return true;
    var hay = (f.relpath + ' ' + f.name + ' ' + f.noext).toLowerCase();
    return terms.every(function(t){ return hay.indexOf(t) >= 0 });
  });
  var c = document.getElementById('gp-list'); c.innerHTML = '';
  if(!files.length){ c.innerHTML = '<div class="hint" style="padding:10px">没有匹配的 LoRA</div>'; return }
  files.slice(0, 400).forEach(function(f){
    var it = document.createElement('div'); it.className = 'gp-item';
    var img = f.has_preview
      ? '<img src="/api/lora-preview?name=' + encodeURIComponent(f.name) + '" loading="lazy" alt="" />'
      : '<span style="width:34px"></span>';
    it.innerHTML = img +
      '<span class="gp-path">' + esc(f.relpath) + '</span>' +
      '<span class="gp-val">' + esc(f.noext) + '</span>';
    it.onclick = function(){ genPickLora(f) };
    c.appendChild(it);
  });
  if(files.length > 400){
    var m = document.createElement('div'); m.className = 'hint';
    m.style.padding = '8px 10px';
    m.textContent = '还有 ' + (files.length - 400) + ' 个，继续输入以缩小范围';
    c.appendChild(m);
  }
}
// 关键：存进去的是纯文件名（noext），不是完整路径
function genPickLora(f){
  var val = f.noext || f.name;
  var t = genPickerTarget;
  if(t){
    if(t.kind === 'fixed')  genFixed[t.idx].lora  = val;
    if(t.kind === 'matrix') genMatrix[t.idx].lora = val;
  }
  genRenderFixed(); genRenderMatrix(); genClosePicker(); genEstimate();
}

// ══ 配置预设（弹窗）══
var genPresets = [];

function genOpenPresets(){
  document.getElementById("gpr-ol").style.display = "flex";
  document.getElementById("gpr-search").value = "";
  document.getElementById("gpr-name").value = "";
  genLoadPresets();
}
function genClosePresets(){
  document.getElementById("gpr-ol").style.display = "none";
}

function genLoadPresets(){
  var box = document.getElementById("gpr-list");
  box.innerHTML = '<div class="hint" style="padding:12px">载入中…</div>';
  api('GET','/api/presets').then(function(d){
    genPresets = (d && d.files) || [];
    genRenderPresets();
  });
}

// 实现已收敛到内核的 fmtTime（gui.py）—— 三份副本合一。
// 空值仍返回空串（原来就是），别改成返回当前时间。
function genFmtTime(ts){ return ts ? fmtTime(ts, 'ymdhm') : "" }

function genRenderPresets(){
  var box = document.getElementById("gpr-list");
  var q = document.getElementById("gpr-search").value.toLowerCase().trim();
  var terms = q ? q.split(/\s+/) : [];
  var files = genPresets.filter(function(p){
    if(!terms.length) return true;
    var hay = (p.name + ' ' + (p.task||'') + ' ' + (p.model||'') + ' '
               + (p.loras||[]).join(' ')).toLowerCase();
    return terms.every(function(t){ return hay.indexOf(t) >= 0 });
  });
  box.innerHTML = "";
  if(!files.length){
    box.innerHTML = '<div class="hint" style="padding:16px">' +
      (genPresets.length ? '没有匹配的预设' : '还没有预设 —— 在下面输入名字，点「保存当前配置」') + '</div>';
    return;
  }
  files.forEach(function(p){
    var d = document.createElement("div");
    d.style.cssText = "border:1px solid var(--line-2);border-radius:10px;padding:11px 13px;"
      + "cursor:pointer;transition:border-color .15s;background:rgba(255,255,255,.014)";
    var names = (p.loras || []).filter(Boolean);
    var extra = (p.matrix || 0) - names.length;
    var h = '<div style="display:flex;align-items:baseline;gap:9px">'
          +   '<b style="font-size:13px;color:var(--txt);flex:1;overflow:hidden;'
          +   'text-overflow:ellipsis;white-space:nowrap">' + esc(p.name) + '</b>'
          +   '<span style="font-size:11px;color:var(--dim-2);white-space:nowrap">'
          +   genFmtTime(p.mtime) + '</span>'
          + '</div>'
          + '<div style="font-size:11px;color:var(--dim);margin-top:6px;line-height:1.7">'
          +   '<span style="color:#b9a6ff">矩阵 ' + (p.matrix||0) + '</span>'
          +   ' · 常驻 ' + (p.fixed||0)
          +   ' · 场景 ' + (p.scenes||0)
          +   ' · ' + esc(p.size||'')
          +   ' · steps ' + esc(String(p.steps||'-'))
          + ' cfg ' + esc(String(p.cfg||'-'))
          + ' batch ' + (p.batch||1)
          + '</div>';
    if(p.model){
      h += '<div style="font-size:11px;color:var(--dim-2);margin-top:3px;'
         + 'font-family:SF Mono,Consolas,monospace">' + esc(p.model) + '</div>';
    }
    if(names.length){
      h += '<div style="font-size:11px;color:var(--dim-2);margin-top:5px;'
         + 'font-family:SF Mono,Consolas,monospace">'
         + esc(names.join(' · ')) + (extra > 0 ? ' …+' + extra : '') + '</div>';
    }
    d.innerHTML = h;

    var ops = document.createElement("div");
    ops.style.cssText = "display:flex;gap:6px;margin-top:9px";
    var bLoad = document.createElement("button");
    bLoad.className = "btn ghost"; bLoad.textContent = "载入";
    bLoad.onclick = function(ev){ ev.stopPropagation(); genLoadPresetByName(p.name) };
    var bDel = document.createElement("button");
    bDel.className = "del"; bDel.textContent = "删除";
    bDel.onclick = function(ev){ ev.stopPropagation(); genDeletePresetByName(p.name) };
    ops.appendChild(bLoad); ops.appendChild(bDel);
    d.appendChild(ops);

    d.onclick = function(){ genLoadPresetByName(p.name) };   // 整卡可点
    d.onmouseenter = function(){ this.style.borderColor = "var(--accent)" };
    d.onmouseleave = function(){ this.style.borderColor = "" };
    box.appendChild(d);
  });
}

function genLoadPresetByName(n){
  api('GET','/api/presets/load?name=' + encodeURIComponent(n)).then(function(d){
    if(d && d.ok){
      genApplyConfig(d.config);
      genClosePresets();
      genMsg('已载入预设：' + n, 'ok');
      var cur = document.getElementById("g-preset-cur");
      if(cur) cur.textContent = '（' + n + '）';
    } else { genMsg((d && d.error) || '载入失败', 'err') }
  });
}

function genDeletePresetByName(n){
  if(!confirm('删除预设「' + n + '」？')) return;
  api('POST','/api/presets/delete',{name:n}).then(function(d){
    if(d && d.ok){ genLoadPresets(); genMsg('已删除：' + n, 'ok') }
    else genMsg('删除失败', 'err');
  });
}

function genSavePreset(){
  var el = document.getElementById("gpr-name");
  var n = (el.value || "").trim() || gv("g-name");
  if(!n){ genMsg('请填预设名称', 'err'); return }
  api('POST','/api/presets/save',{name:n, config: genReadConfig()}).then(function(d){
    if(d && d.ok){
      el.value = "";
      genLoadPresets();
      genMsg('已保存预设：' + n, 'ok');
      var cur = document.getElementById("g-preset-cur");
      if(cur) cur.textContent = '（' + n + '）';
    } else genMsg((d && d.error) || '保存失败', 'err');
  });
}

// ══ 生成 / 执行 ══
function genMsg(m, kind){
  var e = document.getElementById('g-runmsg');
  e.className = 'msg' + (kind ? ' ' + kind : '');
  e.textContent = m || '';
}
function genBusy(on){
  document.getElementById('g-run').disabled = on;
  document.getElementById('g-only').disabled = on;
}
function genOnly(){
  genMsg('生成中…');
  api('POST','/api/generate-tasks',{config: genReadConfig()}).then(function(d){
    if(d && d.ok) genMsg('已生成 ' + d.total + ' 个任务 →\n' + d.path, 'ok');
    else genMsg((d && d.error) || '生成失败', 'err');
  });
}
function genRun(){
  var cfg = genReadConfig();
  if(!cfg['lora矩阵'].length && !cfg['常驻lora'].length){
    if(!confirm('没有任何 LoRA，只会生成对照组。继续？')) return;
  }
  var sel = genCombos.filter(function(c){ return c.sel });
  // 全勾选时传 null（= 全跑），只勾了部分才传白名单
  var only = (genCombos.length && sel.length < genCombos.length)
             ? sel.map(function(c){ return c.key }) : null;
  if(genCombos.length && !sel.length){ genMsg('一个组合都没勾选 —— 至少选一个', 'err'); return }
  var skipDone = document.getElementById('g-skipdone').checked;

  genBusy(true); genMsg('提交中…');
  api('POST','/api/run',{config: cfg, only: only, skip_done: skipDone}).then(function(d){
    if(!d || !d.ok){ genBusy(false); genMsg((d && d.error) || '启动失败', 'err'); return }
    genMsg('正在跑 ' + (d.total || '?') + ' 个任务'
           + (only ? '（只跑勾选的 ' + only.length + ' 个）' : '')
           + (skipDone ? '，自动跳过已完成的' : '') + '…');
    document.getElementById('g-progress').classList.remove('hidden');
    if(genPollTimer) clearInterval(genPollTimer);
    genPollTimer = setInterval(genPoll, 1000);
    genPoll();
  });
}
function genStop(){ api('POST','/api/run/stop',{}).then(function(){ genMsg('已请求停止（跑完当前组合后停）') }) }
function genPoll(){
  api('GET','/api/run/status').then(function(d){
    if(!d || !d.ok) return;
    var pct = d.total ? Math.round(d.index / d.total * 100) : 0;
    document.getElementById('g-bar').style.width = pct + '%';
    document.getElementById('g-pinfo').textContent =
      d.index + '/' + d.total + ' · ' + (d.combo || '') +
      ' · 成功 ' + (d.ok_images || 0) + ' 张' +
      (d.skipped ? ' · 跳过 ' + d.skipped : '') +
      (d.fail ? ' · 失败 ' + d.fail : '') +
      (d.elapsed ? ' · 用时 ' + Math.round(d.elapsed) + 's' : '');
    var lg = document.getElementById('g-log');
    if(d.log && d.log.length){
      lg.textContent = d.log.join('\n');
      lg.scrollTop = lg.scrollHeight;
    }
    if(d.state && d.state !== 'running'){
      clearInterval(genPollTimer); genPollTimer = null; genBusy(false);
      var tail = (d.log && d.log.length) ? d.log[d.log.length-1] : '';
      if(d.state === 'done')    genMsg('完成：成功 ' + (d.ok_images||0) + ' 张' + (tail ? ' · ' + tail : ''), 'ok');
      else if(d.state === 'stopped') genMsg('已停止：成功 ' + (d.ok_images||0) + ' 张');
      else genMsg('出错：' + (d.error || '未知'), 'err');
    }
  });
}
</script>
"""
