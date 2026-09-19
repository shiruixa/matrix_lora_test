"""
Metadata parsers for AI-generated PNG images.

Format A — 本工具的 PNG 输出 (SaveImage LoraManager node):
  PNG tEXt chunk "parameters" = plain text with prompt, negative prompt, steps line, lora hashes.
  No workflow JSON embedded.

Format B — ComfyUI native save / manual generation:
  PNG tEXt chunks = "parameters" (prompt text) + "workflow" (JSON).
  Parameters block may also have "Steps:...", "Model:...", "Civitai resources:...".

Extension: to add a new format, register a parser function that takes
(bytes) from a tEXt chunk keyword and a metadata dict to fill.
"""

import json
import os
import re
import struct


# ── Public API ──────────────────────────────────────────
def read(filepath):
    """Read PNG metadata from filepath. Returns dict with all extracted fields."""
    img_w, img_h = _read_ihdr(filepath)
    result = _empty_result(filepath, img_w, img_h)
    chunks = _read_text_chunks(filepath)

    # Phase 1: parse parameters text (Format A + Format B both have this)
    if 'parameters' in chunks:
        _parse_parameters(chunks['parameters'], result)

    # Phase 2: parse workflow JSON (Format B only — fills gaps)
    if 'workflow' in chunks:
        result["workflow_raw"] = _parse_workflow_json(chunks['workflow'], result)

    # Phase 3: fallbacks
    _apply_fallbacks(result)
    return result


# ── PNG chunk reader ─────────────────────────────────────
def _read_ihdr(filepath):
    """Read IHDR chunk to get image dimensions."""
    try:
        with open(filepath, 'rb') as f:
            f.read(8)
            cl = struct.unpack('>I', f.read(4))[0]
            ct = f.read(4)
            if ct == b'IHDR':
                w = struct.unpack('>I', f.read(4))[0]
                h = struct.unpack('>I', f.read(4))[0]
                return w, h
    except Exception:
        pass
    return 0, 0

def _read_text_chunks(filepath):
    """Read all tEXt and iTXt chunks from PNG, return {keyword: text_value}."""
    chunks = {}
    try:
        with open(filepath, 'rb') as f:
            f.read(8)
            # Skip IHDR
            cl = struct.unpack('>I', f.read(4))[0]
            ct = f.read(4)
            f.read(cl + 4)
            while True:
                cl = struct.unpack('>I', f.read(4))[0]
                ct = f.read(4)
                data = f.read(cl)
                f.read(4)
                if ct == b'tEXt':
                    kw_end = data.index(b'\x00')
                    kw = data[:kw_end].decode('latin-1', 'ignore')
                    chunks[kw] = data[kw_end + 1:].decode('utf-8', 'ignore')
                elif ct == b'iTXt':
                    # iTXt: keyword\0 flag(1) method(1) language\0 trans_keyword\0 text
                    kw_end = data.index(b'\x00')
                    kw = data[:kw_end].decode('latin-1', 'ignore')
                    # skip flag + method
                    pos = kw_end + 3
                    # skip language tag
                    lang_end = data.index(b'\x00', pos)
                    pos = lang_end + 1
                    # skip translated keyword
                    trans_end = data.index(b'\x00', pos)
                    pos = trans_end + 1
                    chunks[kw] = data[pos:].decode('utf-8', 'ignore')
                if ct == b'IEND':
                    break
    except Exception:
        pass
    return chunks


def _empty_result(filepath, img_w=0, img_h=0):
    return {
        "filename": os.path.basename(filepath), "filepath": filepath,
        "file_size": os.path.getsize(filepath), "file_mtime": os.path.getmtime(filepath),
        "image_width": img_w, "image_height": img_h,
        "positive_prompt": "", "negative_prompt": "",
        "model": "", "loras": [], "lora_hashes": "",
        "seed": None, "steps": None, "cfg": None,
        "sampler": "", "scheduler": "", "width": None, "height": None,
        "civitai_resources": [], "workflow_raw": None,
    }


# ── Parameters text parser (Format A + B) ───────────────
def _parse_parameters(text, result):
    lines = text.split('\n')
    neg_line_idx = steps_line_idx = None
    for i, l in enumerate(lines):
        lo = l.lower()
        if 'negative prompt:' in lo: neg_line_idx = i
        if l.startswith('Steps:') or l.startswith('steps:'): steps_line_idx = i

    # Positive prompt: everything before Negative prompt or Steps line
    if neg_line_idx is not None:
        pos_lines = lines[:neg_line_idx]
    elif steps_line_idx is not None:
        pos_lines = lines[:steps_line_idx]
    else:
        pos_lines = lines

    clean_pos = []
    for l in pos_lines:
        s = l.strip()
        if not s:
            continue
        # Extract <lora:Name:Strength> triggers
        if s.startswith('<lora:') and '>' in s:
            for m in re.finditer(r'<lora:([^:>]+):([\d.]+)>', s):
                name = m.group(1).strip()
                strength = float(m.group(2))
                if not any(lo["name"] == name for lo in result["loras"]):
                    result["loras"].append({"name": name, "strength": strength})
            continue
        if s.startswith('pos:') and len(s) > 80:
            s = s[4:].strip()
        clean_pos.append(s)
    result["positive_prompt"] = '\n'.join(clean_pos).strip()

    # Negative prompt (may span multiple continuation lines)
    if neg_line_idx is not None:
        neg_lines = [lines[neg_line_idx]]
        for j in range(neg_line_idx + 1, len(lines)):
            l = lines[j]
            if l.startswith('Steps:') or l.startswith('steps:'):
                steps_line_idx = j
                break
            if 'negative prompt:' in l.lower():
                # Another negative marker — shouldn't happen in practice, but be safe
                break
            neg_lines.append(l)
        neg_text = '\n'.join(neg_lines)
        neg_text = re.sub(r'^[Nn]egative prompt:\s*', '', neg_text)
        m = re.search(r',?\s*Steps:\s*\d+', neg_text)
        if m:
            neg_text = neg_text[:m.start()].strip()
        result["negative_prompt"] = neg_text

    # Steps line
    if steps_line_idx is not None:
        _parse_steps_line(lines[steps_line_idx], result)
    else:
        for l in lines:
            if re.search(r'Steps:\s*\d+', l):
                parts = l.split('Steps:', 1)
                if parts[0].strip() and not result["negative_prompt"]:
                    result["negative_prompt"] = re.sub(
                        r'^[Nn]egative prompt:\s*', '', parts[0]).strip()
                _parse_steps_line('Steps:' + parts[1], result)
                break


def _parse_steps_line(text, result):
    for pat, key in [(r'Steps:\s*(\d+)', 'steps'),
                     (r'CFG scale:\s*([\d.]+)', 'cfg'),
                     (r'Seed:\s*(\d+)', 'seed')]:
        m = re.search(pat, text, re.IGNORECASE)
        if m and result[key] is None:
            result[key] = int(m.group(1)) if '.' not in m.group(1) else float(m.group(1))

    # Sampler (formats: "Euler simple", "er_sde_simple", "er_sde", "dpmpp_2m karras")
    m = re.search(r'Sampler:\s*([^,]+?)(?:,\s*CFG|$)', text, re.IGNORECASE)
    if m:
        s = m.group(1).strip()
        known_schedulers = {'karras', 'simple', 'normal', 'ddim_uniform', 'sgm_uniform', 'exponential', 'beta'}

        # Step 1: try space split first (most common: "Euler simple", "er_sde simple", "dpmpp_2m karras")
        parts = s.split()
        if len(parts) >= 2:
            # last token might be a scheduler
            candidate = parts[-1]
            if candidate in known_schedulers:
                result["sampler"] = ' '.join(parts[:-1])
                result["scheduler"] = candidate
                # 不直接 return——继续执行 model/LoRA/Size 解析
            # Check if last token is a number-like thing (e.g. "Euler a" → leave as-is)

        # Step 2: try underscore split ("er_sde_simple", "dpmpp_2m_karras")
        if '_' in s:
            parts = s.rsplit('_', 1)
            if len(parts) == 2 and parts[1] in known_schedulers:
                result["sampler"] = parts[0]
                result["scheduler"] = parts[1]
                # 不直接 return——继续执行 model/LoRA/Size 解析

        # Fallback: raw sampler value
        result["sampler"] = s

    # Size
    m = re.search(r'Size:\s*(\d+)\s*x\s*(\d+)', text, re.IGNORECASE)
    if m:
        if not result["width"]:  result["width"] = int(m.group(1))
        if not result["height"]: result["height"] = int(m.group(2))

    # Model (Format B)
    m = re.search(r'Model:\s*([^,]+?)(?:,\s*(?:Version|Hashes)|$)', text, re.IGNORECASE)
    if m and not result["model"]:
        result["model"] = m.group(1).strip()

    # Lora hashes (Format A)
    m = re.search(r'Lora hashes:\s*"([^"]*)"', text, re.IGNORECASE)
    if m:
        result["lora_hashes"] = m.group(1)
        if not result["loras"]:
            for item in result["lora_hashes"].split(','):
                parts = item.strip().split(':')
                if len(parts) >= 1:
                    result["loras"].append({"name": parts[0].strip(), "strength": 0})

    # Hashes JSON (Format B: Hashes: {"model":"...","LORA:xxx":"..."})
    m = re.search(r'Hashes:\s*(\{[^}]+\})', text, re.IGNORECASE)
    if m:
        try:
            hashes = json.loads(m.group(1))
            for k, v in hashes.items():
                if k.startswith("LORA:") or k.startswith("lora:"):
                    name = k.split(":", 1)[1].strip()
                    if name and not any(l["name"] == name for l in result["loras"]):
                        result["loras"].append({"name": name, "strength": 0})
        except Exception:
            pass

    # Civitai resources (Format B)
    m = re.search(r'Civitai resources:\s*(\[.+\])', text, re.IGNORECASE)
    if m:
        try:
            result["civitai_resources"] = json.loads(m.group(1))
            # Civitai resources 里的 LoRA 版本名（如 "Anima v5.56"）跟 Hashes 里的
            # 文件名（如 "BunnySlop_Ani_v5.56"）不一致，会导致 LoRA 列表重复。
            # 改用 <lora:> 标签或 Hashes（优先 <lora:> 标签，有正确文件名和 strength）。
            # 所以这里不再从 Civitai resources 添加 LoRA。
            # 只利用 Civitai resources 补全 model 名（如果没有从 Hashes 拿到的话）
            if not result["model"]:
                for rsrc in result["civitai_resources"]:
                    if "checkpoint" in str(rsrc.get("air", "")):
                        result["model"] = rsrc.get("modelName", "")
                        break
        except Exception:
            pass


# ── Workflow JSON parser (Format B) ─────────────────────
def _parse_workflow_json(wf_text, result):
    """Parse ComfyUI workflow JSON. Returns workflow dict and fills gaps in result."""
    try:
        wf = json.loads(wf_text)
    except Exception:
        return None

    nodes = wf.get('nodes', []) if isinstance(wf, dict) else (
        wf if isinstance(wf, list) else [])
    if not nodes and isinstance(wf, dict):
        nodes = [dict(n, _id=k) for k, n in wf.items()
                 if isinstance(n, dict) and ('class_type' in n or 'type' in n)]

    for node in nodes:
        if not isinstance(node, dict):
            continue
        ct = node.get('class_type') or node.get('type', '')
        inp = node.get('widgets_values', [])
        oi = node.get('inputs', {})

        if 'KSampler' in ct or 'Sampler' in ct:
            if isinstance(inp, list):
                # KSamplerAdvanced has variable widget order.
                # Scan by type: seed=big int, steps=small int, cfg=float/small, sampler/scheduler=lowercase strings
                ints = [v for v in inp if isinstance(v, (int, float)) and not isinstance(v, bool)]
                strs = [v for v in inp if isinstance(v, str)]
                # seed: very large int (>10000)
                big_ints = [v for v in ints if isinstance(v, int) and v > 10000]
                small_ints = [v for v in ints if isinstance(v, int) and v <= 10000]
                floats = [v for v in ints if isinstance(v, float) or (isinstance(v, int) and 1 < v < 20)]
                # sampler/scheduler: lowercase strings, not 'enable'/'disable'/'randomize'
                param_strs = [v for v in strs if v not in ('enable', 'disable', 'randomize') and v[0].islower()]

                if big_ints and result["seed"] is None:
                    result["seed"] = big_ints[0]
                if small_ints and result["steps"] is None:
                    result["steps"] = small_ints[0]
                if floats and result["cfg"] is None:
                    result["cfg"] = floats[0]
                if len(param_strs) >= 1 and not result["sampler"]:
                    result["sampler"] = param_strs[0]
                if len(param_strs) >= 2 and not result["scheduler"]:
                    result["scheduler"] = param_strs[1]
            elif oi:
                for k, fk in [('seed', 'seed'), ('steps', 'steps'), ('cfg', 'cfg'),
                              ('sampler', 'sampler_name'), ('scheduler', 'scheduler')]:
                    v = oi.get(fk) or oi.get('noise_seed')
                    if v is not None and (result[k] is None or (isinstance(result[k], str) and not result[k])):
                        result[k] = v

        if 'Checkpoint' in ct and not result["model"]:
            if isinstance(inp, list) and len(inp) >= 1:
                result["model"] = inp[0]
            elif oi:
                result["model"] = oi.get('ckpt_name', '')

        if ('EmptyLatent' in ct or 'Latent' in ct) and result["width"] is None:
            if isinstance(inp, list) and len(inp) >= 2:
                result["width"] = inp[0]
                result["height"] = inp[1]
            elif oi:
                result["width"] = oi.get('width')
                result["height"] = oi.get('height')

    return wf


def _apply_fallbacks(result):
    if result["width"] is None:
        result["width"] = result["image_width"]
    if result["height"] is None:
        result["height"] = result["image_height"]

    # 注意：不在 result["model"] 为空时做任何兜底猜测。
    # 旧 Format A PNG（png_meta.py 接入前）物理上没有模型名，就是没有——显示 "?"。
    # 新 PNG 由 png_meta.py 补写 Model 行，直接读真值。

