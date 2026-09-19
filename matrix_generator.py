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
            tasks.append(task)

    return tasks, task_name


def write_tasks(cfg, out_dir=None):
    """展开配置并落盘任务清单，返回 (out_path, tasks)。

    CLI 与 UI 共用这一份落盘逻辑 —— 文件名/时间戳规则只有一处，
    否则 task_runner 的「取 json/ 下最新一份」启发式会失准。
    """
    tasks, task_name = generate_tasks(cfg)
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
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