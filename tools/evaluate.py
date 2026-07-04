"""Grade every transcript→rewrite pair with the Ollama model itself.

Grades real usage pairs (from logs) plus seed transcripts rewritten fresh
with the current system prompt. Writes eval/report.md and eval/results.jsonl.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import ROOT, load_config, load_system_prompt
from evaluator import CRITERIA, grade, letter, load_seed_transcripts, load_usage_pairs
from rewriter import Rewriter, ensure_server


def main():
    cfg = load_config()
    o = cfg["ollama"]
    url, model = o["url"], o["model"]
    if not ensure_server(url):
        sys.exit(f"Ollama is not reachable at {url}")

    pairs = load_usage_pairs()
    print(f"Loaded {len(pairs)} pair(s) from real usage.")

    seeds = load_seed_transcripts()
    if seeds:
        print(f"Rewriting {len(seeds)} seed transcript(s) with the current prompt...")
        rw = Rewriter(url, model, load_system_prompt(), temperature=o.get("temperature", 0.3))
        seen = {p["transcript"] for p in pairs}
        for s in seeds:
            if s not in seen:
                pairs.append({"transcript": s, "rewrite": rw.rewrite(s), "source": "seed"})

    if not pairs:
        sys.exit("Nothing to evaluate: no usage history and no seed transcripts.")

    print(f"Grading {len(pairs)} pair(s) with {model}...\n")
    results = []
    for i, p in enumerate(pairs, 1):
        g = grade(url, model, p["transcript"], p["rewrite"])
        results.append({**p, **g, "grade": letter(g["pct"])})
        print(f"  [{i}/{len(pairs)}] {results[-1]['grade']} "
              f"({g['pct'] * 100:.0f}%) [{p['source']}] {p['transcript'][:60]}...")

    avg = sum(r["pct"] for r in results) / len(results)
    print(f"\nAverage: {avg * 100:.0f}% ({letter(avg)})")

    eval_dir = ROOT / "eval"
    eval_dir.mkdir(exist_ok=True)
    with open(eval_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lines = [
        "# Prompt Wizard — Evaluation Report",
        "",
        f"- Date: {time.strftime('%Y-%m-%d %H:%M')}",
        f"- Grader model: `{model}` (self-grading — same model that writes the rewrites)",
        f"- Pairs: {len(results)} ({sum(r['source'] == 'usage' for r in results)} usage, "
        f"{sum(r['source'] == 'seed' for r in results)} seed)",
        f"- **Average: {avg * 100:.0f}% ({letter(avg)})**",
        "",
    ]
    for i, r in enumerate(sorted(results, key=lambda r: r["pct"]), 1):
        scores = ", ".join(f"{c}={r['scores'][c]}" for c in CRITERIA)
        lines += [
            f"## {i}. Grade {r['grade']} ({r['pct'] * 100:.0f}%) — {r['source']}",
            "",
            f"Scores: {scores}",
            "",
            f"**Issues:** {r['issues'] or 'none'}",
            "",
            f"**Spoken:** {r['transcript']}",
            "",
            "**Rewrite:**",
            "",
            "```",
            r["rewrite"],
            "```",
            "",
        ]
    (eval_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {eval_dir / 'report.md'}")


if __name__ == "__main__":
    main()
