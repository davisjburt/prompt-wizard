"""Grade transcript→rewrite pairs using the same Ollama model that produced them."""
import json
import re

import requests

from config import ROOT

LOG_FILE = ROOT / "logs" / "prompt-wizard.log"
HISTORY_FILE = ROOT / "logs" / "history.jsonl"
SEEDS_FILE = ROOT / "eval" / "seed_transcripts.txt"

CRITERIA = ("intent", "no_invention", "clarity", "structure", "concise")

GRADER_SYSTEM = """You grade the output of a "prompt rewriter" tool. The tool listens to \
spoken, rambling dictation and rewrites it into a clear, effective prompt for an LLM.

Given the SPOKEN TRANSCRIPT and the REWRITTEN PROMPT, score the rewrite on each \
criterion from 1 (bad) to 5 (excellent):
- intent: every requirement and detail from the speech is preserved
- no_invention: nothing was added that the speaker did not say or clearly imply
- clarity: unambiguous, well-worded, keeps the speaker's first-person voice
- structure: sensibly organized (numbered steps or bullets when multi-part, plain \
prose when simple)
- concise: filler and repetition removed, no bloat added

Also write "issues": a short list of concrete problems, or an empty string if none.

Respond with ONLY a JSON object:
{"intent": n, "no_invention": n, "clarity": n, "structure": n, "concise": n, "issues": "..."}"""


def ollama_chat(url, model, system, user, temperature=0.0, fmt=None, timeout=180):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if fmt:
        body["format"] = fmt
    r = requests.post(f"{url.rstrip('/')}/api/chat", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def parse_log() -> list[dict]:
    """Extract transcript/rewrite pairs from the plain-text usage log."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    stamped = re.compile(r"^\[\d\d:\d\d:\d\d\] ")
    heard = re.compile(r"^\[\d\d:\d\d:\d\d\]\s+Heard\s+\([\d.]+s\): (.*)")
    rewrote = re.compile(r"^\[\d\d:\d\d:\d\d\]\s+Rewrote \([\d.]+s\): (.*)")
    pairs = []
    i = 0
    while i < len(lines):
        m = heard.match(lines[i])
        if m and i + 1 < len(lines):
            m2 = rewrote.match(lines[i + 1])
            if m2:
                parts = [m2.group(1)]
                k = i + 2
                while k < len(lines) and not stamped.match(lines[k]):
                    parts.append(lines[k])
                    k += 1
                pairs.append({
                    "transcript": m.group(1).strip(),
                    "rewrite": "\n".join(parts).strip(),
                    "source": "usage",
                })
                i = k
                continue
        i += 1
    return pairs


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    pairs = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            pairs.append({
                "transcript": d["transcript"],
                "rewrite": d["rewrite"],
                "source": "usage",
            })
    return pairs


def load_usage_pairs() -> list[dict]:
    seen = set()
    out = []
    for p in load_history() + parse_log():
        key = (p["transcript"], p["rewrite"])
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def load_seed_transcripts() -> list[str]:
    if not SEEDS_FILE.exists():
        return []
    return [
        line.strip()
        for line in SEEDS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def grade(url: str, model: str, transcript: str, rewrite: str) -> dict:
    """Score one pair. Returns {"scores": {...}, "pct": float, "issues": str}."""
    user = f"SPOKEN TRANSCRIPT:\n{transcript}\n\nREWRITTEN PROMPT:\n{rewrite}"
    last_err = None
    for _attempt in range(3):
        text = ollama_chat(url, model, GRADER_SYSTEM, user, temperature=0.0, fmt="json")
        try:
            d = json.loads(text)
            scores = {c: max(1, min(5, int(d[c]))) for c in CRITERIA}
            return {
                "scores": scores,
                "pct": sum(scores.values()) / (5 * len(CRITERIA)),
                "issues": str(d.get("issues", "")).strip(),
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            last_err = e
    raise RuntimeError(f"Grader returned unparseable output: {last_err}")


def letter(pct: float) -> str:
    for threshold, grade_ in ((0.9, "A"), (0.8, "B"), (0.7, "C"), (0.6, "D")):
        if pct >= threshold:
            return grade_
    return "F"
