#!/usr/bin/env python3
"""Q-One Gym benchmark — re-run the frozen offline evaluation and record results.

This is a real benchmark: it executes the same offline baseline evaluation that
run.py --offline runs (base_rate / uniform / act-majority on the frozen 80-task
held-out set), then replays the hash-chained ledger (run.py --verify), and writes
a timestamped benchmark record under results/benchmarks/ so the numbers are
traceable to a real run rather than to memory.

Usage:
    python3 benchmark.py            # run + record
    python3 benchmark.py --json     # print the benchmark record as JSON

Nothing here fabricates a number: every figure is produced by executing the
repo's own evaluation code (gym/scoring.py, gym/baselines.py, run.py).
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = __file__.rsplit("/", 1)[0]


def run(cmd):
    """Run a command in the repo root, return (exit_code, stdout)."""
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="print record as JSON")
    args = ap.parse_args()

    # 1) unit tests (scoring + ledger)
    code_t, out_t = run([sys.executable, "-m", "pytest", "tests/", "-q"])
    import re
    m = re.search(r"(\d+) passed", out_t)
    passed = m.group(1) if m else ("failed" if code_t else "?")
    # 2) offline evaluation (real Brier + gates)
    code_o, out_o = run([sys.executable, "run.py", "--offline"])
    # run.py --offline prints a JSON blob followed by "ledger: N events OK".
    scores = None
    try:
        start = out_o.index("{")
        # find the matching close of the top-level object (last '}' before "ledger")
        end = out_o.index("ledger:")
        # walk back from the last '}' before 'ledger:' to get the JSON object
        json_txt = out_o[start:out_o.rindex("}", 0, end) + 1]
        scores = json.loads(json_txt)
    except Exception:
        scores = {"_error": out_o.strip()[:400]}
    ledger_line = out_o.strip().splitlines()[-1] if out_o.strip() else ""
    # 3) replay the hash chain
    code_v, out_v = run([sys.executable, "run.py", "--verify"])
    verify_ok = "OK" in out_v

    record = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "unit_tests": {"exit": code_t, "passed": passed},
        "offline": {
            "exit": code_o,
            "scores": scores,
            "ledger_line": out_o.strip().splitlines()[-1] if out_o.strip() else "",
        },
        "verify": {"exit": code_v, "ok": verify_ok, "output": out_v.strip()[:200]},
    }

    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    # Write timestamped record under results/benchmarks/
    import os
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bench_dir = os.path.join(REPO_ROOT, "results", "benchmarks")
    os.makedirs(bench_dir, exist_ok=True)
    path = os.path.join(bench_dir, f"benchmark_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"benchmark recorded: {path}")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
