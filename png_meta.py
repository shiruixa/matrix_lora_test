"""
PNG 元数据补写 —— 项目侧给生成图内嵌 Model（不动 ComfyUI 任何文件）
====================================================================
背景：Save Image (LoraManager) 写元数据依赖 LoRA Manager 的 metadata_collector，
它不认识本项目 workflow 用的 comfyui-image-saver 加载器类（UNETLoaderWithName /
CheckpointLoaderWithName），导致 PNG 元数据缺 "Model:" 行（Steps/CFG/Seed/LoRA 正常）。

本项目脚本在出图后直接改写 PNG 的 "parameters" 元数据块，把 ", Model: xxx" 追加到
参数行末尾。纯标准库实现（struct + zlib），不依赖任何第三方、不改 ComfyUI。

⚠️ chunk 类型：实测本机 Save Image (LoraManager) 写入的是 **iTXt**（非 tEXt），
两者都支持（2026-08-05 修复）。

模型名从 adapter 取：UNET 适配层读 `unet_name`，Checkpoint 读 `ckpt_name`，
写法与 image-saver 一致（去扩展名，如 `Model: anima_baseV10`）。

用法：
    import png_meta
    n = png_meta.embed_model_from_history(history, model_name, output_root)

批量回补旧图（递归目录下所有 PNG）：
    python png_meta.py <目录> <模型名>
"""
import os
import struct
import sys
import zlib

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_KEY = b"parameters"


def clean_model_name(name):
    """去路径去扩展名，对齐 image-saver 的写法（Model: anima_baseV10）。"""
    return os.path.splitext(os.path.basename(name))[0]


def _find_text_start(cdata, kw_end):
    """定位 iTXt 文本起点：keyword\0 + flag(1) + method(1) + lang\0 + translated\0"""
    pos = kw_end + 3  # 跳过 \0、flag、method
    # 跳过 language tag（NULL-terminated）
    lang_end = cdata.index(b"\x00", pos)
    pos = lang_end + 1
    # 跳过 translated keyword（NULL-terminated）
    trans_end = cdata.index(b"\x00", pos)
    return trans_end + 1


def _iter_chunks(raw):
    pos = 8
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + length]
        yield ctype, cdata
        pos += 12 + length
        if ctype == b"IEND":
            return


def append_model_to_png(png_path, model_name):
    """在 PNG 的 parameters 元数据末尾补 `, Model: <name>`（支持 tEXt + iTXt）。已含则跳过。返回是否改动。"""
    if not model_name:
        return False
    try:
        with open(png_path, "rb") as f:
            raw = f.read()
    except OSError:
        return False
    if raw[:8] != _PNG_SIG:
        return False

    # 解析 chunk 列表
    pos, chunks = 8, []
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + length]
        chunks.append([ctype, cdata])
        pos += 12 + length
        if ctype == b"IEND":
            break

    marker = f", Model: {clean_model_name(model_name)}"
    changed = False
    for i, (ctype, cdata) in enumerate(chunks):
        if ctype == b"tEXt" and cdata.startswith(_KEY + b"\x00"):
            old = cdata[len(_KEY) + 1:].decode("utf-8", "replace").rstrip()
            if ", Model: " in old:
                return False  # 已有模型信息，保持原样
            chunks[i] = (ctype, _KEY + b"\x00" + (old + marker).encode("utf-8"))
            changed = True
            break
        if ctype == b"iTXt" and cdata.startswith(_KEY + b"\x00"):
            kw_end = cdata.index(b"\x00")
            flag = cdata[kw_end + 1]
            if flag & 1:
                continue  # 压缩 iTXt，跳过
            text_start = _find_text_start(cdata, kw_end)
            old = cdata[text_start:].decode("utf-8", "replace").rstrip()
            if ", Model: " in old:
                return False
            chunks[i] = (ctype, cdata[:text_start] + (old + marker).encode("utf-8"))
            changed = True
            break

    if not changed:
        return False

    # 重建 PNG（所有 chunk 重算 CRC）
    out = bytearray(_PNG_SIG)
    for ctype, cdata in chunks:
        out += struct.pack(">I", len(cdata))
        out += ctype
        out += cdata
        out += struct.pack(">I", zlib.crc32(ctype + cdata) & 0xFFFFFFFF)
    with open(png_path, "wb") as f:
        f.write(out)
    return True


def write_parameters_chunk(png_path, meta):
    """为 SaveImage 生成的 PNG（无 parameters chunk）写入完整的 iTXt parameters 元数据块。

    meta dict 支持字段：
        positive, negative, steps, cfg, seed, model, size, sampler, scheduler, loras
    """
    lines = []
    # positive prompt：后面拼接 <lora:> 标签
    pos_text = meta.get("positive", "")
    lora_tags = meta.get("loras", [])
    if lora_tags:
        lora_line = " ".join(lora_tags)
        # 如果 prompt 末尾有逗号，直接接；否则加逗号
        if pos_text.rstrip().endswith(","):
            pos_text = pos_text.rstrip() + " " + lora_line
        else:
            pos_text = pos_text.rstrip() + ", " + lora_line
    lines.append(pos_text)
    if meta.get("negative"):
        lines.append(f"Negative prompt: {meta['negative']}")
    params = []
    if meta.get("steps"):
        params.append(f"Steps: {meta['steps']}")
    if meta.get("sampler"):
        s = meta["sampler"]
        if meta.get("scheduler"):
            s += f"_{meta['scheduler']}"
        params.append(f"Sampler: {s}")
    if meta.get("cfg"):
        params.append(f"CFG: {meta['cfg']}")
    if meta.get("seed") is not None:
        params.append(f"Seed: {meta['seed']}")
    if meta.get("size"):
        params.append(f"Size: {meta['size']}")
    if meta.get("model"):
        params.append(f"Model: {clean_model_name(meta['model'])}")
    lines.append(", ".join(params))
    text = "\n".join(lines)

    try:
        with open(png_path, "rb") as f:
            raw = f.read()
    except OSError:
        return False
    if raw[:8] != _PNG_SIG:
        return False

    # iTXt: keyword\0 + flag(0) + method(0) + lang\0 + translated\0 + text
    ctype = b"iTXt"
    cdata = _KEY + b"\x00" + bytes([0, 0]) + b"\x00" + b"\x00" + text.encode("utf-8")

    chunks = []
    pos = 8
    inserted = False
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype_existing = raw[pos + 4:pos + 8]
        cdata_existing = raw[pos + 8:pos + 8 + length]
        # 跳过已有的 parameters chunk（否则重复）
        if ctype_existing in (b"tEXt", b"iTXt") and cdata_existing.startswith(_KEY + b"\x00"):
            pass
        elif not inserted and ctype_existing == b"IEND":
            chunks.append([ctype, cdata])
            inserted = True
            chunks.append([ctype_existing, cdata_existing])
        else:
            chunks.append([ctype_existing, cdata_existing])
        pos += 12 + length
        if ctype_existing == b"IEND":
            break
    if not inserted:
        return False

    out = bytearray(_PNG_SIG)
    for ct, cd in chunks:
        out += struct.pack(">I", len(cd))
        out += ct
        out += cd
        out += struct.pack(">I", zlib.crc32(ct + cd) & 0xFFFFFFFF)
    with open(png_path, "wb") as f:
        f.write(out)
    return True


def copy_text_chunks(src_png, dst_png):
    """把 src 的 tEXt/iTXt 文本 chunk 复制到 dst（保留提示词/参数等元数据）。

    后处理产物由 PIL 保存，PIL 不写任何文本 chunk → 查看器读不到提示词。
    本函数把原图的元数据搬过去（同名 keyword 覆盖，其余保留）。
    返回是否改动。
    """
    if not os.path.isfile(src_png) or not os.path.isfile(dst_png):
        return False
    try:
        with open(src_png, "rb") as f:
            raw_src = f.read()
        with open(dst_png, "rb") as f:
            raw_dst = f.read()
    except OSError:
        return False
    if raw_src[:8] != _PNG_SIG or raw_dst[:8] != _PNG_SIG:
        return False

    src_chunks = [(ct, cd) for ct, cd in _iter_chunks(raw_src)
                  if ct in (b"tEXt", b"iTXt")]
    if not src_chunks:
        return False

    # 源里出现的 keyword —— 目标的同名 chunk 要删掉，避免重复
    kws = set()
    for _ct, cd in src_chunks:
        try:
            kws.add(cd[:cd.index(b"\x00")])
        except ValueError:
            pass

    out_chunks = []
    for ct, cd in _iter_chunks(raw_dst):
        if ct in (b"tEXt", b"iTXt"):
            try:
                k = cd[:cd.index(b"\x00")]
            except ValueError:
                k = None
            if k in kws:
                continue
        if ct == b"IEND":
            out_chunks.extend(src_chunks)   # 在 IEND 前插入源的文本 chunk
        out_chunks.append((ct, cd))

    out = bytearray(_PNG_SIG)
    for ct, cd in out_chunks:
        out += struct.pack(">I", len(cd)) + ct + cd
        out += struct.pack(">I", zlib.crc32(ct + cd) & 0xFFFFFFFF)
    try:
        with open(dst_png, "wb") as f:
            f.write(out)
    except OSError:
        return False
    return True


def embed_model_from_history(history, model_name, output_root):
    """从 ComfyUI history 的 outputs 找图片文件，逐个补写 Model。返回成功改写张数。"""
    if not history or not model_name:
        return 0
    done = 0
    for node_out in (history.get("outputs") or {}).values():
        for img in (node_out.get("images") or []):
            fn = img.get("filename", "")
            if not fn:
                continue
            sub = img.get("subfolder", "") or ""
            path = os.path.join(output_root, sub, fn) if sub else os.path.join(output_root, fn)
            if append_model_to_png(path, model_name):
                done += 1
    return done


def batch_backfill(root, model_name):
    """递归补写目录下所有 PNG，返回成功张数。"""
    done = 0
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            if not fn.lower().endswith(".png"):
                continue
            p = os.path.join(dirpath, fn)
            if append_model_to_png(p, model_name):
                done += 1
    return done


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("用法: python png_meta.py <目录> <模型名>")
    n = batch_backfill(sys.argv[1], sys.argv[2])
    print(f"补写完成: {n} 张")

