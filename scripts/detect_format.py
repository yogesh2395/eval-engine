#!/usr/bin/env python3
"""
Format Detector — deterministic, no LLM, target <100ms.
Classifies input into Format A (transcript), Format B (structured response),
hybrid, or unknown. Also detects input_type for the preprocessor.

Usage:
    python3 detect_format.py <file_path>
    → prints JSON: {"format": "A"|"B"|"hybrid"|"unknown", "input_type": "pdf"|"md"|"json"|"txt"|"unknown", "confidence": 0.0-1.0, "signals": [...]}
"""

import sys, json, os, re


def detect(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()

    input_type_map = {".pdf": "pdf", ".md": "md", ".json": "json", ".txt": "txt"}
    input_type = input_type_map.get(ext, "unknown")

    if input_type == "pdf":
        return {"format": "unknown", "input_type": "pdf", "confidence": 0.0,
                "signals": ["pdf requires preprocessor before format detection"]}

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        return {"format": "unknown", "input_type": input_type, "confidence": 0.0,
                "signals": [f"read error: {e}"]}

    if input_type == "json":
        try:
            data = json.loads(text)
            if isinstance(data, dict) and any(k in data for k in ("transcript", "dialogue", "conversation")):
                return {"format": "A", "input_type": "json", "confidence": 0.9,
                        "signals": ["json with transcript/dialogue key"]}
            return {"format": "B", "input_type": "json", "confidence": 0.7,
                    "signals": ["json without transcript key — treating as structured"]}
        except Exception:
            pass  # fall through to text analysis

    signals_A = []
    signals_B = []

    # Format A signals — conversational transcript
    if re.search(r"interview transcript", text, re.IGNORECASE):
        signals_A.append("contains 'Interview Transcript' header")
    q_count = len(re.findall(r"\?\s", text))
    if q_count >= 5:
        signals_A.append(f"high question density: {q_count} questions")
    if re.search(r"(can you tell me|i would like to (ask|understand|know)|could you (please |)elaborate|"
                 r"is the (decline|problem|issue)|does our client|what (is|are) (our|the) (revenue|cost|client))",
                 text, re.IGNORECASE):
        signals_A.append("clarifying question patterns detected")
    if re.search(r"(that is correct|go ahead|yes,? (that'?s?|it) (correct|right)|"
                 r"fair enough|good question|yes,? please|correct\.)",
                 text, re.IGNORECASE):
        signals_A.append("interviewer confirmation patterns detected")
    candidate_pivots = re.findall(
        r"(i would like to (structure|break|split|analyse|analyze|begin|start)|"
        r"my (hypothesis|recommendation|approach|analysis|understanding) is|"
        r"to summarize|in conclusion|based on (my|the) analysis)",
        text, re.IGNORECASE)
    if candidate_pivots:
        signals_A.append(f"candidate pivot language detected: {len(candidate_pivots)} instances")

    # Format B signals — polished structured response
    b_headers = re.findall(r"^#{1,3}\s+(Executive Summary|Key Findings|Recommendations|"
                           r"Problem Statement|Analysis|Root Cause|Conclusion|Approach|Framework)",
                           text, re.IGNORECASE | re.MULTILINE)
    if b_headers:
        signals_B.append(f"structured headers: {b_headers[:3]}")
    if re.search(r"(in summary|our recommendation(s)? (is|are)|the root cause (is|appears)|"
                 r"we recommend|the primary driver)", text, re.IGNORECASE):
        signals_B.append("executive summary language detected")
    if re.search(r"\|\s*\w+\s*\|", text):  # markdown table
        signals_B.append("markdown table detected")

    score_A = len(signals_A)
    score_B = len(signals_B)

    if score_A == 0 and score_B == 0:
        fmt, conf = "unknown", 0.3
    elif score_A >= 3 and score_B == 0:
        fmt, conf = "A", 0.95
    elif score_A >= 2 and score_B <= 1:
        fmt, conf = "A", 0.80
    elif score_B >= 2 and score_A == 0:
        fmt, conf = "B", 0.90
    elif score_B >= 2 and score_A <= 1:
        fmt, conf = "B", 0.75
    elif score_A > 0 and score_B > 0:
        fmt, conf = "hybrid", 0.60
    else:
        fmt, conf = "A" if score_A > score_B else "B", 0.55

    return {
        "format": fmt,
        "input_type": input_type,
        "confidence": conf,
        "signals": signals_A + signals_B
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: detect_format.py <file_path>"}))
        sys.exit(1)
    print(json.dumps(detect(sys.argv[1]), indent=2))
