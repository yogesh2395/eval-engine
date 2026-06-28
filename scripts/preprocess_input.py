#!/usr/bin/env python3
"""
Preprocessor — deterministic, no LLM, target <500ms.
Converts any supported input_type to normalized plaintext.

Supported: pdf, md, txt, json
Usage:
    python3 preprocess_input.py <file_path> [output_path]
    → if output_path omitted, writes to /tmp/eval_preprocessed_<hash>.txt
    → prints JSON: {"output_path": "...", "input_type": "...", "char_count": int, "notes": [...]}
"""

import sys, json, os, re, zlib, hashlib


def _extract_pdf(data: bytes) -> str:
    def clean_tj(block):
        out = []
        for arr in re.findall(rb'\[(.*?)\]\s*TJ', block, re.DOTALL):
            for p in re.findall(rb'\(([^)]*)\)', arr):
                try:
                    out.append(p.decode('latin-1'))
                except Exception:
                    pass
        for p in re.findall(rb'\(([^)]*)\)\s*Tj', block):
            try:
                out.append(p.decode('latin-1'))
            except Exception:
                pass
        return ''.join(out)

    pattern = re.compile(rb'stream\r?\n(.*?)\r?\nendstream', re.DOTALL)
    sections = []
    for m in pattern.findall(data):
        try:
            dec = zlib.decompress(m)
            blocks = re.findall(rb'BT(.*?)ET', dec, re.DOTALL)
            if blocks:
                pt = ' '.join(clean_tj(b) for b in blocks).strip()
                if len(pt) > 80:
                    sections.append(pt)
        except Exception:
            pass
    return '\n\n'.join(sections)


def _strip_md_chrome(text: str) -> str:
    # Remove page/section headers that are navigation noise, not content
    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        # Skip pure navigation headers (short standalone lines)
        if re.match(r'^#{1,4}\s+(Metadata|Source|Split|Category|Difficulty|Sector)\b', stripped, re.IGNORECASE):
            continue
        # Strip bullet metadata lines (- **Key:** value)
        if re.match(r'^-\s+\*\*\w[\w\s]+:\*\*', stripped):
            continue
        lines.append(line)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines))
    # Remove markdown formatting marks but keep text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def _flatten_json(data, depth=0) -> str:
    if depth > 4:
        return str(data)
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return '\n'.join(_flatten_json(v, depth + 1) for v in data)
    if isinstance(data, dict):
        parts = []
        for k, v in data.items():
            val = _flatten_json(v, depth + 1)
            if val.strip():
                parts.append(f"{k}: {val}")
        return '\n'.join(parts)
    return str(data)


def preprocess(path: str, output_path: str = None) -> dict:
    ext = os.path.splitext(path)[1].lower()
    notes = []

    try:
        if ext == '.pdf':
            with open(path, 'rb') as f:
                raw = f.read()
            text = _extract_pdf(raw)
            notes.append(f"pdf: extracted via zlib FlateDecode, {len(text)} chars")
        elif ext in ('.md', '.txt', ''):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()
            text = _strip_md_chrome(raw_text) if ext == '.md' else raw_text
            notes.append(f"{ext or 'txt'}: read directly, {len(text)} chars")
        elif ext == '.json':
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()
            try:
                data = json.loads(raw_text)
                text = _flatten_json(data)
                notes.append(f"json: flattened to plaintext, {len(text)} chars")
            except json.JSONDecodeError:
                text = raw_text
                notes.append("json: invalid JSON, treating as plaintext")
        else:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            notes.append(f"unknown extension {ext}: read as plaintext")
    except Exception as e:
        return {"error": str(e), "path": path}

    if output_path is None:
        h = hashlib.md5(path.encode()).hexdigest()[:8]
        job_tmp = os.environ.get("CLAUDE_JOB_DIR", "")
        if job_tmp:
            output_path = os.path.join(job_tmp, "tmp", f"eval_preprocessed_{h}.txt")
        else:
            output_path = os.path.join(os.path.dirname(path), f".eval_preprocessed_{h}.txt")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return {
        "output_path": output_path,
        "input_type": ext.lstrip('.') or "txt",
        "char_count": len(text),
        "notes": notes
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: preprocess_input.py <file_path> [output_path]"}))
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(preprocess(sys.argv[1], out), indent=2))
