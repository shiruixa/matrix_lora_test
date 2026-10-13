"""
矩阵生成器 — 展开 LoRA 强度矩阵 → 生成任务清单 JSON
=====================================================

用法：
    python matrix_generator.py <config.json>

配置示例见 example_config.json
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
import argparse
import itertools
import json
import os
import random
from datetime import datetime

# 只为 data_dir()（任务清单默认落点）—— paths 不 import 任何本地模块，无循环。
# 本模块原本「零兄弟依赖」，为这一处破例：自己复刻一遍 sys.frozen 判断
# 迟早和 paths 里的那份漂移。
import paths


def _parse_strength(val):
    """强度配置：数字、数组或 {最小,最大,段数} → 列表"""
    if isinstance(val, (int, float)):
        return [float(val)]
    if isinstance(val, list):
        return [float(v) for v in val]
    if isinstance(val, dict):
        mn = float(val.get("最小", 0))
        mx = float(val.get("最大", 1))
        n = int(val.get("段数", 4))
        if n <= 1:
            return [mn]
        step = (mx - mn) / (n - 1)
        return [round(mn + i * step, 4) for i in range(n)]
    return [0.0]


def _list_loras(cfg):
    """返回（常驻 LoRA, 矩阵 LoRA）"""
    fixed = cfg.get("常驻lora", [])
    matrix = cfg.get("lora矩阵", [])
    # 兼容旧字段名
    if not matrix and "loras" in cfg:
        matrix = cfg["loras"]
    return fixed, matrix


def generate_tasks(cfg):
    """读配置 → 展开任务清单"""
    # 基础参数
    task_name = cfg.get("任务名", f"matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    common_prompt = cfg.get("通用提示词", "").strip()
    neg_prompt = cfg.get("负面提示词", "").strip()
    scenes = cfg.get("场景", [""])
    batch = cfg.get("batch", 2)
    size = cfg.get("尺寸", {"宽": 832, "高": 1216})
    model_name = cfg.get("base_model", "")
    # CLIP / VAE 也由配置指定 —— 不同人用的底模栈不一样（Anima 是 UNet+CLIPLoader，
    # SDXL/Pony 是 CheckpointLoader），不能预设作者的模型文件名。留空则沿用
    # workflow.json 模板里的值（模板本身是用户可编辑的）。
    clip_name = cfg.get("clip_name", "")
    vae_name = cfg.get("vae_name", "")
    steps = cfg.get("steps", 10)
    cfg_val = cfg.get("cfg", 1)
    # 整批共用种子：没配就随机一个；配置了就用指定的（方便重跑复现）
    if "seed" in cfg:
        batch_seed = cfg["seed"]
    else:
        batch_seed = random.randint(1, 2**31 - 1)
    # 是否生成「全零对照」组合（所有被测 LoRA 都不加，只剩常驻 LoRA）。
    # 它在网格里就是 (0,0) 那个角落格子，用来对照「不加这些 LoRA 长什么样」
    include_baseline = cfg.get("包含全零基线", True)

    fixed_loras, matrix_loras = _list_loras(cfg)

    # 展开每个矩阵 LoRA 的强度列表
    lora_dimensions = []
    lora_names = []
    lora_triggers = []
    for l in matrix_loras:
        strengths = _parse_strength(l.get("强度", [0, 1]))
        lora_dimensions.append(strengths)
        lora_names.append(l.get("lora", "?"))
        lora_triggers.append(l.get("触发词", ""))

    # 笛卡尔积
    tasks = []
    for combo in itertools.product(*lora_dimensions):
        # 全零组合 = 对照基线（不加任何被测 LoRA），默认保留
        if all(v == 0 for v in combo) and not include_baseline:
            continue

        # 触发词拼接（常驻 LoRA 的触发词排在最前；强度 0 不加，与下面的 lora_list 同规则）
        trigger_parts = []
        for fl in fixed_loras:
            if float(fl.get("强度", 1) or 0) != 0 and fl.get("触发词"):
                trigger_parts.append(fl["触发词"])
        for i, strength in enumerate(combo):
            if strength > 0 and lora_triggers[i]:
                trigger_parts.append(lora_triggers[i])

        # LoRA 列表（常驻 + 矩阵）—— 强度 0 一律不加载
        lora_list = []
        for fl in fixed_loras:
            st = fl.get("强度", 1)
            if float(st or 0) == 0:
                continue
            lora_list.append({"name": fl["lora"], "strength": st})
        for i, strength in enumerate(combo):
            if strength > 0:
                lora_list.append({"name": lora_names[i], "strength": strength})

        # 组合标识（完整，供元数据/查看器用）
        combo_label = "_".join(f"{lora_names[i]}={combo[i]}" for i in range(len(combo)))

        # 简短的文件夹名（只含非零 LoRA，如 BunnySlop0.33_HowanJoe1）
        active = [(lora_names[i], combo[i]) for i in range(len(combo)) if combo[i] > 0]
        if active:
            parts = []
            for name, s in active:
                s_str = f"{s:.3g}" if s != int(s) else str(int(s))
                parts.append(f"{name}{s_str}")
            folder_name = "_".join(parts)
        else:
            folder_name = "baseline"   # 全零 = 不加任何被测 LoRA 的对照图

        for scene_idx, scene_text in enumerate(scenes):
            # 拼接正面提示词
            trigger_text = ", ".join(filter(None, trigger_parts))
            parts = [common_prompt, trigger_text, scene_text]
            final_prompt = ", ".join(p for p in parts if p)

            # 多场景时给文件夹名加场景后缀 —— 否则同一组合的不同场景会写向同一个
            # `{组合}.task.json` / `{组合}_{seed}.png` 互相覆盖（task_runner 的文件名
            # 只由「组合文件夹」决定）。单场景配置不受影响。
            scene_folder = (folder_name if len(scenes) <= 1
                            else "%s_s%d" % (folder_name, scene_idx))

            task = {
                "任务名": task_name,
                "场景序号": scene_idx,
                "场景": scene_text,
                "正面": final_prompt,
                "负面": neg_prompt,
                "base_model": model_name,
                "steps": steps,
                "cfg": cfg_val,
                "batch": batch,
                "尺寸": size,
                "loras": lora_list,
                "组合标识": combo_label,
                "组合文件夹": scene_folder,
                # 全体组合共用同一个 latent 种子，保证对比只看 LoRA 差异
                "seed": batch_seed,
                # 维度坐标（供查看器使用）
                "坐标": {lora_names[i]: combo[i] for i in range(len(combo))},
            }
            # 配置里给了才写 —— 保持旧配置生成的 task 结构完全不变（向后兼容）
            if clip_name:
                task["clip_name"] = clip_name
            if vae_name:
                task["vae_name"] = vae_name
            tasks.append(task)

    _disambiguate_folders(tasks)
    return tasks, task_name


def _disambiguate_folders(tasks):
    """把**真撞了**的「组合文件夹」名加短哈希区分开。

    为什么会撞：文件夹名用 `%.3g` 压缩强度（`0.3333` 与 `0.3334` 都成 `0.333`，
    `1.0001` 也成 `1`），而 task_runner 的 `_make_safe` 又把 `A B` / `A_B` / `A+B`
    统一映射成 `A_B`。两条**不同**组合拿到同一个名字 → `{组合}.task.json` 与
    `{组合}_{种子}.png` 写到同一路径 → **后跑的静默覆盖先跑的，不报任何错**，
    查看器看到的图比配置的少。

    ⚠️ **只在真碰撞时才改名**：常规配置的文件夹名一个字不变，已有图片的断点续跑
    照常工作。改命名规则会让旧图全部不被识别（`is_combo_done` 按文件夹名匹配），
    那种代价不该由没撞的人承担。

    哈希基于「组合标识」（完整、含全部维度），所以同一份配置每次生成的名字一致。
    """
    import hashlib
    by_folder = {}
    for t in tasks:
        by_folder.setdefault(t["组合文件夹"], set()).add(t["组合标识"])
    clash = {f for f, labels in by_folder.items() if len(labels) > 1}
    if not clash:
        return
    for t in tasks:
        if t["组合文件夹"] in clash:
            h = hashlib.md5(t["组合标识"].encode("utf-8")).hexdigest()[:6]
            t["组合文件夹"] = "%s_%s" % (t["组合文件夹"], h)


def write_tasks(cfg, out_dir=None):
    """展开配置并落盘任务清单，返回 (out_path, tasks)。

    CLI 与 UI 共用这一份落盘逻辑 —— 文件名/时间戳规则只有一处，
    否则 task_runner 的「取 json/ 下最新一份」启发式会失准。
    """
    tasks, task_name = generate_tasks(cfg)
    out_dir = out_dir or os.path.join(paths.data_dir(), "json")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"{task_name}_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    return out_path, tasks


def main():
    parser = argparse.ArgumentParser(description="矩阵测试 — 生成任务清单")
    parser.add_argument("config", help="配置文件路径")
    parser.add_argument("--output", "-o", default="", help="输出目录（默认 json/）")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    out_path, tasks = write_tasks(cfg, args.output or None)

    print(f"生成 {len(tasks)} 个任务")
    print(f"输出: {out_path}")
    print(f"组合数: {len(set(t['组合标识'] for t in tasks))}")
    print(f"场景数: {len(cfg.get('场景', ['']))}")
    print(f"每批: {cfg.get('batch', 2)} 张")


if __name__ == "__main__":
    main()