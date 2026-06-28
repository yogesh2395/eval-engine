#!/usr/bin/env python3
"""
parse_transcript.py — Haiku transcript parser via direct Anthropic API.
No agent wrapper overhead. Target: <10s per document.

Requires ANTHROPIC_API_KEY in the shell environment.
Credential source options (in order of preference):
  1. macOS Keychain (production): security find-generic-password -s eval-engine -a anthropic -w
  2. Shell session export (development): export ANTHROPIC_API_KEY=sk-ant-...
  3. Credential manager (prod deployment): inject via AWS Secrets Manager / Vault at runtime
Never store the key in a file on disk.

Usage:
    PYTHONPATH=.pip_deps python3 scripts/parse_transcript.py <file_path>
    → prints JSON extraction result to stdout
    → stderr: latency_ms and token usage
"""

import sys, json, os, time

SYSTEM_PROMPT = """\
You are a transcript parser. Read one case interview file and extract structured artifacts. \
Do NOT evaluate, score, or summarize. Extract verbatim text and structure it.

Return ONLY this JSON object — no preamble, no markdown wrapper, nothing else:
{
  "case_title": "string",
  "case_category": "Profitability|Market Entry|Pricing|Operations|M&A|Unconventional|Public Policy|Unknown",
  "difficulty": "Easy|Moderate|Challenging|Unknown",
  "sector": "string",
  "problem_statement": "string",
  "initial_framing": "string",
  "final_recommendation": "string",
  "full_transcript": "string",
  "approach_framework_present": true or false,
  "approach_framework_text": "string or empty string",
  "turn_count": {"interviewer": integer, "candidate": integer},
  "extraction_notes": ["string"]
}

EXTRACTION RULES:

problem_statement: The interviewer's opening case setup BEFORE the candidate speaks.
Start at "Your client is..." / "You have been hired..." / "A company is facing..." or equivalent.
End before the candidate's first question. If transcript starts mid-dialogue, write \
"[Problem statement not found at transcript start — see full_transcript]" and note it.

initial_framing: Candidate's FIRST 3-5 turns only, concatenated verbatim.
Include: clarifying questions, initial hypothesis, first structural breakdown.
Exclude: interviewer responses in this window.
Stop when candidate moves from clarifying to requesting numbers or diving into sub-branches.

final_recommendation: Candidate's LAST 2-4 turns, verbatim.
Include: root cause synthesis, recommendations, prioritisation.
Exclude: interviewer closing remarks.
If recommendations scattered (no distinct closing block), extract last 400 words of candidate speech and note it.
Do NOT pull from approach_framework_text — only candidate dialogue.

full_transcript: Complete transcript text, lightly cleaned.
Remove page headers (IIM Ahmedabad, 2024-2025, Page N, Consult Club, Click here for...).
Normalize spacing. Preserve interleaved dialogue exactly as-is.

approach_framework_present / approach_framework_text: If file contains "Approach / Framework" \
or "Approach/ Framework" section after transcript, set true and include verbatim. Keep OUT of final_recommendation.

turn_count: Count distinct speaker turns (continuous block from one party before other responds).

Speaker attribution (when not labelled): Interviewer = provides data, confirms/denies, prompts. \
Candidate = asks questions, builds frameworks, delivers recommendations.

extraction_notes: Document EVERY uncertainty. Examples:
"Speaker attribution inferred — no I:/C: labels"
"Initial framing only 2 candidate turns — transcript may be abbreviated"
"Final recommendation not a distinct closing block — extracted last 400 words"

CONSTRAINTS:
- Return ONLY the JSON. No explanation before or after.
- No paraphrase. All extracted fields = verbatim text from file.
- If file unreadable: return {"error": "File not readable", "path": "<path>"}
"""


def parse(file_path: str) -> dict:
    t0 = time.time()

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e), "path": file_path}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "error": "ANTHROPIC_API_KEY not set.",
            "fix": "export ANTHROPIC_API_KEY=$(security find-generic-password -s eval-engine -a anthropic -w) "
                   "or export ANTHROPIC_API_KEY=sk-ant-... for a shell session (never write to disk)"
        }

    # Add .pip_deps to sys.path for local anthropic install
    pip_deps = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".pip_deps")
    if pip_deps not in sys.path:
        sys.path.insert(0, pip_deps)

    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not found. Run: python3 -m pip install anthropic --target=.pip_deps"}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Parse this case interview file.\n\nFile: {file_path}\n\n{content}"
            }]
        )
    except Exception as e:
        return {"error": f"API call failed: {e}"}

    t1 = time.time()
    latency_ms = int((t1 - t0) * 1000)

    raw = response.content[0].text.strip()
    # Strip any accidental markdown wrapper
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse failed: {e}", "raw_response": raw[:500], "latency_ms": latency_ms}

    result["_parser_meta"] = {
        "latency_ms": latency_ms,
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "file": file_path
    }
    print(f"[parse_transcript] {latency_ms}ms | in={response.usage.input_tokens} out={response.usage.output_tokens}", file=sys.stderr)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_transcript.py <file_path>"}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(parse(sys.argv[1]), indent=2))
