"""Iteratively improve the rewrite system prompt using evaluation results.

Loop: rewrite all transcripts with the current prompt → grade each with the
same Ollama model → feed the worst examples back to the model to propose an
improved prompt → keep the candidate only if the measured average improves.

The winning prompt is written to prompts/rewrite_system.md (the previous
version is backed up to prompts/archive/). Report: eval/optimize_report.md.

Usage: optimize.py [--iterations N]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import ROOT, load_config, load_system_prompt
from evaluator import (
    grade,
    letter,
    load_seed_transcripts,
    load_usage_pairs,
    ollama_chat,
)
from rewriter import Rewriter, ensure_server

OPTIMIZER_SYSTEM = """You improve system prompts for a speech-to-prompt rewriter tool. \
The tool listens to spoken, rambling dictation and rewrites it as a clear, effective \
prompt for an LLM.

You will receive the current system prompt and graded examples of its output, worst \
first, with the issues a reviewer found. Write an improved system prompt that fixes \
the observed issues while keeping what already works.

Hard requirements the prompt must always keep:
- Preserve ALL intent and details from the speech; never invent requirements.
- Keep the speaker's first-person voice.
- The tool must output ONLY the rewritten prompt, with no preamble or explanation.

Keep the prompt under 250 words. Output ONLY the new system prompt text — no \
commentary, no markdown fences."""

PROMPT_FILE = ROOT / "prompts" / "rewrite_system.md"
ARCHIVE_DIR = ROOT / "prompts" / "archive"


def score_prompt(url, model, temperature, system_prompt, transcripts):
    """Rewrite every transcript with system_prompt and grade each result."""
    rw = Rewriter(url, model, system_prompt, temperature=temperature)
    details = []
    for i, t in enumerate(transcripts, 1):
        rewrite = rw.rewrite(t)
        g = grade(url, model, t, rewrite)
        details.append({"transcript": t, "rewrite": rewrite, **g})
        print(f"    [{i}/{len(transcripts)}] {letter(g['pct'])} ({g['pct'] * 100:.0f}%)")
    avg = sum(d["pct"] for d in details) / len(details)
    return avg, details


def improvement_request(current_prompt, details):
    worst = sorted(details, key=lambda d: d["pct"])[:5]
    examples = []
    for d in worst:
        examples.append(
            f"--- example (scored {d['pct'] * 100:.0f}%) ---\n"
            f"SPOKEN: {d['transcript']}\n"
            f"REWRITE: {d['rewrite']}\n"
            f"ISSUES: {d['issues'] or 'none noted'}"
        )
    return (
        f"CURRENT SYSTEM PROMPT:\n{current_prompt}\n\n"
        f"GRADED EXAMPLES (worst first):\n" + "\n".join(examples)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=3)
    args = ap.parse_args()

    cfg = load_config()
    o = cfg["ollama"]
    url, model = o["url"], o["model"]
    temperature = o.get("temperature", 0.3)
    if not ensure_server(url):
        sys.exit(f"Ollama is not reachable at {url}")

    transcripts = [p["transcript"] for p in load_usage_pairs()]
    for s in load_seed_transcripts():
        if s not in transcripts:
            transcripts.append(s)
    if not transcripts:
        sys.exit("No transcripts to optimize against.")
    print(f"Optimizing against {len(transcripts)} transcript(s), "
          f"{args.iterations} iteration(s), model {model}.\n")

    original = load_system_prompt()
    print("Baseline (current prompt):")
    best_avg, best_details = score_prompt(url, model, temperature, original, transcripts)
    best_prompt = original
    print(f"  Baseline average: {best_avg * 100:.0f}% ({letter(best_avg)})\n")

    log_lines = [f"Baseline: {best_avg * 100:.0f}% ({letter(best_avg)})"]
    for it in range(1, args.iterations + 1):
        print(f"Iteration {it}: proposing improved prompt...")
        candidate = ollama_chat(
            url, model, OPTIMIZER_SYSTEM,
            improvement_request(best_prompt, best_details),
            temperature=0.6,
        ).strip().strip("`").strip()
        if len(candidate) < 50:
            print("  Candidate too short, skipping.")
            continue
        print("  Scoring candidate:")
        avg, details = score_prompt(url, model, temperature, candidate, transcripts)
        verdict = "ADOPTED" if avg > best_avg else "rejected"
        print(f"  Candidate average: {avg * 100:.0f}% ({letter(avg)}) — {verdict}\n")
        log_lines.append(f"Iteration {it}: {avg * 100:.0f}% ({letter(avg)}) — {verdict}")
        if avg > best_avg:
            best_avg, best_details, best_prompt = avg, details, candidate

    eval_dir = ROOT / "eval"
    eval_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    report = [
        "# Prompt Wizard — Optimization Report",
        "",
        f"- Date: {stamp}",
        f"- Model: `{model}` (rewriter, grader, and optimizer)",
        f"- Transcripts: {len(transcripts)}",
        "",
        "## Runs",
        "",
        *[f"- {line}" for line in log_lines],
        "",
        "## Final prompt",
        "",
        "```",
        best_prompt,
        "```",
        "",
    ]
    (eval_dir / "optimize_report.md").write_text("\n".join(report), encoding="utf-8")

    if best_prompt != original:
        ARCHIVE_DIR.mkdir(exist_ok=True)
        backup = ARCHIVE_DIR / f"rewrite_system_{time.strftime('%Y%m%d_%H%M%S')}.md"
        backup.write_text(original, encoding="utf-8")
        PROMPT_FILE.write_text(best_prompt + "\n", encoding="utf-8")
        print(f"Improved prompt saved to {PROMPT_FILE} "
              f"({best_avg * 100:.0f}%). Old prompt backed up to {backup}.")
        print("Restart Prompt Wizard to pick it up.")
    else:
        print(f"No candidate beat the baseline ({best_avg * 100:.0f}%). Prompt unchanged.")
    print(f"Report: {eval_dir / 'optimize_report.md'}")


if __name__ == "__main__":
    main()
