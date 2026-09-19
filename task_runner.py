"""
任务执行器 — 读 json/*.json 任务清单 → 逐个提交 ComfyUI API 生图
=================================================================

直接基于 workflow/nodes/ 下的 workflow JSON（不走 adapter），
node_id 硬编码，清楚直接。

用法：
    python task_runner.py
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
import copy
import hashlib
import json
import os
import random
import sys
import urllib.request
from urllib.error import HTTPError


import comfy_api as _api
import png_meta
from paths import COMFYUI_OUTPUT
import paths

# ── 配置 ──
JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")

# 基于 通用测试.json 的 node_id，硬编码
NODE_KSAMPLER = "7"          # KSamplerAdvanced
NODE_LATENT = "4"            # EmptyLatentImage
NODE_SAVE = "5"              # Save Image (LoraManager)
NODE_SEED = "6"              # Seed (rgthree)
NODE_POS = "8"               # ImpactWildcardProcessor (正)
NODE_NEG = "9"               # ImpactWildcardProcessor (负)
NODE_UNET = "12"             # UNet loader with Name (Image Saver)
NODE_LORA = "13"             # Power Lora Loader (rgthree)
NODE_VAE = "1"               # VAELoader
NODE_CLIP = "3"              # CLIPLoader

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflow.json")


def _make_safe(name, maxlen=90):
    """文件名安全化：空格 + Windows 非法字符 → 下划线，并限制长度。

    ⚠️ 注意：这里用 str.isalnum()，它对 CJK 也返回 True，所以**中文会保留**。
    实测 ComfyUI 处理中文路径没问题，真正会出问题的是空格
    （SaveImage 会把空格路径里的片段拼成带 _00001_ 的怪名字），
    所以这里只需要把空格和非法字符换掉。

    **长度上限**：Windows 路径上限 260 字符，而输出根目录已占 47
    。调用方按层级分配预算：
    任务名（目录名）maxlen=50，组合名（文件名）maxlen=90 —— 实测最坏情况总长
    203、余量 57。

    超长时截断并追加基于**原始 name**的哈希（不是截断后的），这样同一个 task
    每次生成的文件名稳定不变 —— 否则「跳过已完成」永远匹配不上。
    """
    s = "".join(
        ch if (ch.isalnum() or ch in "._-") else "_"
        for ch in name
    ).strip("_")
    if len(s) > maxlen:
        h = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
        s = s[: maxlen - 9] + "_" + h
    return s


def _combo_target(task):
    """返回 (out_dir, combo_safe, seed, batch)。

    `_run_task` 与 `is_combo_done` 共用同一套命名规则 —— 两处各写一份迟早漂移，
    而「跳过已完成」正是靠这个规则去磁盘上找回产物的。
    """
    combo = task.get("组合文件夹", task.get("组合标识", "unknown"))
    task_name = task.get("任务名", "matrix")
    out_dir = os.path.join(COMFYUI_OUTPUT, "matrix",
                           _make_safe(task_name, maxlen=50) or "matrix")
    return (out_dir, _make_safe(combo), task.get("seed", 0),
            int(task.get("batch", 1) or 1))


def is_combo_done(task):
    """这个组合是否已经跑完。

    判据是 **seed 匹配的 PNG 数量 >= batch**，而不是 task.json 是否存在 ——
    task.json 在生图**之前**就写盘了，它只证明「尝试过」。

    seed 必须参与判断：换了种子重新生成清单后，旧 PNG 还躺在目录里，但那是
    另一个种子的图，应当重跑（新旧并存，查看器会显示 +N 角标）。
    """
    out_dir, combo_safe, seed, batch = _combo_target(task)
    if not seed:
        return False                      # task 没带 seed，无从比对
    for i in range(batch):
        if not os.path.isfile(os.path.join(out_dir, "%s_%d.png" % (combo_safe, seed + i))):
            return False
    return True


def _submit(prompt_data, timeout=180):
    body = json.dumps(prompt_data).encode("utf-8")
    req = urllib.request.Request(
        paths.comfyui_url() + "/prompt", data=body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("prompt_id")
    except HTTPError as e:
        detail = e.read().decode()[:400]
        print(f"  400: {detail}", flush=True)
        return None
    except Exception as e:
        print(f"  提交异常: {e}", flush=True)
        return None


def _run_task(task):
    """执行一个任务，返回成功张数"""
    seed = task.get("seed", 0) or random.randint(1, 2 ** 31 - 1)
    task_name_raw = task.get("任务名", "matrix")
    # 命名规则与 is_combo_done 共用（含长度保护）—— 不要在这里另写一份
    out_dir, combo_safe, _, _ = _combo_target(task)
    os.makedirs(out_dir, exist_ok=True)

    # task.json 与图片放同一目录，查看器只读这一个目录
    tp = os.path.join(out_dir, f"{combo_safe}.task.json")
    task_saved = dict(task)
    task_saved["_task_name_display"] = task_name_raw
    task_saved["组合文件夹"] = combo_safe
    with open(tp, "w", encoding="utf-8") as f:
        json.dump(task_saved, f, ensure_ascii=False, indent=2)

    # 加载 workflow
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        wf = json.load(f)
    wf_copy = copy.deepcopy(wf)

    # ── 注入参数 ──

    # Prompt（直接设 wildcard_text + mode=fixed，避免 Impact Pack 服务端重处理）
    wf_copy[NODE_POS]["inputs"]["wildcard_text"] = task["正面"]
    wf_copy[NODE_POS]["inputs"]["populated_text"] = task["正面"]
    wf_copy[NODE_POS]["inputs"]["mode"] = "fixed"
    wf_copy[NODE_POS]["inputs"]["seed"] = seed

    wf_copy[NODE_NEG]["inputs"]["wildcard_text"] = task["负面"]
    wf_copy[NODE_NEG]["inputs"]["populated_text"] = task["负面"]
    wf_copy[NODE_NEG]["inputs"]["mode"] = "fixed"
    wf_copy[NODE_NEG]["inputs"]["seed"] = seed

    # Seed
    wf_copy[NODE_SEED]["inputs"]["seed"] = seed

    # LoRA — 清掉旧的，按 task 重建
    li = wf_copy[NODE_LORA]["inputs"]
    for k in list(li.keys()):
        if k.startswith("lora_") and k[5:].isdigit():
            del li[k]
    for si, slot in enumerate(task.get("loras", []), 1):
        li[f"lora_{si}"] = {"on": True, "lora": slot["name"], "strength": slot["strength"]}

    # KSampler
    wf_copy[NODE_KSAMPLER]["inputs"]["noise_seed"] = seed
    wf_copy[NODE_KSAMPLER]["inputs"]["steps"] = task.get("steps", 10)
    wf_copy[NODE_KSAMPLER]["inputs"]["cfg"] = task.get("cfg", 1)

    # Latent
    sz = task.get("尺寸", {"宽": 896, "高": 1152})
    wf_copy[NODE_LATENT]["inputs"]["width"] = sz["宽"]
    wf_copy[NODE_LATENT]["inputs"]["height"] = sz["高"]

    # Model — 支持 UNET 或 Checkpoint
    model_name = task.get("base_model", "")
    if model_name:
        if "unet" in wf_copy[NODE_UNET]["class_type"].lower():
            wf_copy[NODE_UNET]["inputs"]["unet_name"] = model_name
            # UNET 模型需要 clip 和 vae。
            # ⚠️ 这里**不设默认值** —— 原先写的是 task.get("clip_name", "qwen_3_06b_base.safetensors")，
            # 等于强制所有人用作者的 CLIP/VAE；而 matrix_generator 以前又不写这两个字段，
            # 于是那个兜底永远生效。现在只在配置确实指定时才覆盖，否则保留 workflow.json
            # 模板里的值（模板是用户可编辑的）。
            if task.get("clip_name") and "clip_name" in wf_copy[NODE_CLIP]["inputs"]:
                wf_copy[NODE_CLIP]["inputs"]["clip_name"] = task["clip_name"]
            if task.get("vae_name") and "vae_name" in wf_copy[NODE_VAE]["inputs"]:
                wf_copy[NODE_VAE]["inputs"]["vae_name"] = task["vae_name"]
        else:
            wf_copy[NODE_UNET]["inputs"]["ckpt_name"] = model_name

    # ── 提交 ──
    # 元数据（含 <lora:name:strength>）由 ComfyUI 的 Save 节点自己写全，不再二次改写
    wf_copy[NODE_SAVE]["inputs"]["add_loras_to_prompt"] = True
    wf_copy[NODE_SAVE]["inputs"]["add_counter_to_filename"] = False

    ok = 0
    for i in range(task.get("batch", 1)):
        # 文件名 {组合}_{种子}.png —— 每张种子不同，prefix 带上种子避免互相覆盖
        wf_copy[NODE_KSAMPLER]["inputs"]["noise_seed"] = seed + i
        wf_copy[NODE_SAVE]["inputs"]["filename_prefix"] = f"{out_dir}/{combo_safe}_{seed + i}"

        pid = _submit({"prompt": wf_copy})
        if not pid:
            continue

        history = _api.wait(pid, timeout=300)
        if not history:
            print(f"    超时", flush=True)
            continue

        status_str = history.get("status_str", "")
        if not (status_str == "success" or history.get("completed") or history.get("outputs")):
            print(f"    执行失败", flush=True)
            continue

        ok += 1
        # 补 Model 元数据（LoraManager 不认识 comfyui-image-saver 的 UNET 加载器）
        if model_name:
            png_meta.embed_model_from_history(history, model_name, COMFYUI_OUTPUT)

        for node_out in (history.get("outputs") or {}).values():
            for img_info in node_out.get("images", []):
                sub = img_info.get("subfolder", "")
                fn = img_info["filename"]
                p = os.path.join(COMFYUI_OUTPUT, sub, fn) if sub else os.path.join(COMFYUI_OUTPUT, fn)
                print(f"    -> {p}", flush=True)

    return ok


def main():
    """跑任务清单。

    默认只跑 json/ 下**最新的一个**（生成器每次产出一个带时间戳的新文件，
    全跑会把历史批次重复生成一遍）。
    指定具体文件：python task_runner.py <任务清单.json>
    """
    # 同 matrix_viewer：把配置里的地址发布给 comfy_api（命令行单独跑时也要一致）
    paths.publish_url()
    jdir = JSON_DIR
    skip_done = "--no-skip" not in sys.argv          # 加了 --no-skip 就重跑全部
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        paths = [args[0]]
    else:
        # json/ 是运行时产物，全新克隆里还不存在 —— 直接 listdir 会 FileNotFoundError
        names = os.listdir(jdir) if os.path.isdir(jdir) else []
        candidates = sorted(
            (os.path.join(jdir, f) for f in names
             if f.endswith(".json") and not f.startswith("example")),
            key=os.path.getmtime,
        )
        if not candidates:
            print(f"没有任务清单 (json 目录: {jdir})")
            print("先用生成器产出一份：python matrix_generator.py example_config.json")
            return
        paths = [candidates[-1]]   # 只跑最新那份
        if len(candidates) > 1:
            print(f"json/ 下有 {len(candidates)} 份任务清单，只跑最新的：{os.path.basename(paths[0])}")
            print(f"（要跑别的：python task_runner.py <文件路径>）")

    total_ok = 0
    skipped = 0
    for jp in paths:
        print(f"\n=== {os.path.basename(jp)} ===")
        with open(jp, encoding="utf-8") as f:
            tasks = json.load(f)
        # 守卫：json/ 下若混入非任务清单（例如矩阵预设是 dict），
        # 直接迭代 dict 会得到字符串键，后面 task.get 立刻 AttributeError
        if not isinstance(tasks, list):
            print(f"  跳过：顶层不是 list，这不是任务清单")
            continue
        print(f"任务数: {len(tasks)}")
        for idx, task in enumerate(tasks, 1):
            combo = task.get("组合文件夹", task.get("组合标识", "?"))
            if skip_done and is_combo_done(task):
                skipped += 1
                print(f"[{idx}/{len(tasks)}] {combo}  ⏭ 已完成，跳过", flush=True)
                continue
            print(f"\n[{idx}/{len(tasks)}] {combo}")
            try:
                ok = _run_task(task)
            except Exception as exc:
                # 异常隔离：单条坏 task 不该炸掉整轮；但也不能静默吞掉，要打出来
                print(f"    异常: {type(exc).__name__}: {exc}", flush=True)
                ok = 0
            if ok:
                total_ok += ok
                print(f"    生成 {ok} 张", flush=True)
            else:
                print(f"    失败", flush=True)

    tail = f"，跳过 {skipped} 个已完成" if skipped else ""
    print(f"\n=== 完成: 成功 {total_ok} 张{tail} ===")


if __name__ == "__main__":
    main()