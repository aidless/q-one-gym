#!/usr/bin/env python3
"""Offline acceptance check. No network and no GAMES_CSV override.

Rebuilds the task set from data/games.csv, rescores the three heuristics,
checks the committed report and the README headline, and shows that a tampered
ledger event fails verification.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gym.headline import (  # noqa: E402
    ABOUT,
    ABOUT_LINES,
    FORBIDDEN_README_PHRASES,
    GAMES_SHA256,
    N_HELD,
    N_TRAIN,
    TASK_SHA16,
    extract_headline,
    format_headline,
)


def fail(message):
    print(message, file=sys.stderr)
    return 1


def run(cmd, env, check=True):
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if check and result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def main():
    env = os.environ.copy()
    env.pop("GAMES_CSV", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    games = ROOT / "data" / "games.csv"
    if not games.is_file():
        return fail("data/games.csv is missing; the clone is not self-contained")
    games_sha = hashlib.sha256(games.read_bytes()).hexdigest()
    if games_sha != GAMES_SHA256:
        return fail(f"games.csv sha256 {games_sha} != {GAMES_SHA256}")
    provenance = (ROOT / "data" / "PROVENANCE.md").read_text()
    if GAMES_SHA256 not in provenance or TASK_SHA16 not in provenance:
        return fail("data/PROVENANCE.md does not record the pinned hashes")

    tasks_path = ROOT / "tasks" / "tasks_v1.json"
    if tasks_path.exists():
        tasks_path.unlink()
    built = run([sys.executable, "tasks/build_tasks.py"], env)
    if f"train={N_TRAIN} held_out={N_HELD} sha256={TASK_SHA16}" not in built.stdout:
        return fail(f"task build did not reproduce the frozen line:\n{built.stdout}")
    task_sha = hashlib.sha256(tasks_path.read_bytes()).hexdigest()[:16]
    if task_sha != TASK_SHA16:
        return fail(f"task sha16 {task_sha} != {TASK_SHA16}")

    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "ledger.jsonl"
        report_path = Path(tmp) / "report.json"
        run([
            sys.executable, "run.py", "--offline",
            "--ledger", str(ledger),
            "--report", str(report_path),
        ], env)
        verified = run([sys.executable, "run.py", "--verify", "--ledger", str(ledger)], env)
        if verified.stdout.strip() != "(True, '6 events OK')":
            return fail(f"unexpected verify output: {verified.stdout!r}")
        n_events = sum(1 for line in ledger.read_text().splitlines() if line.strip())
        if n_events != 6:
            return fail(f"expected 6 ledger events from one offline run, got {n_events}")

        lines = ledger.read_text().splitlines()
        event = json.loads(lines[0])
        event["payload"]["sha16"] = "tampered"
        lines[0] = json.dumps(event)
        tampered = Path(tmp) / "tampered.jsonl"
        tampered.write_text("\n".join(lines) + "\n")
        bad = run(
            [sys.executable, "run.py", "--verify", "--ledger", str(tampered)],
            env,
            check=False,
        )
        if bad.returncode == 0:
            return fail("tampered ledger verified; verify must fail")
        if "False" not in bad.stdout:
            return fail(f"tamper did not report failure: {bad.stdout!r} {bad.stderr!r}")

        report = json.loads(report_path.read_text())

    committed_path = ROOT / "results" / "report_v1.json"
    committed = json.loads(committed_path.read_text())
    if report != committed:
        print("committed results/report_v1.json does not match a fresh offline run", file=sys.stderr)
        fresh = json.dumps(report, sort_keys=True, indent=2)
        old = json.dumps(committed, sort_keys=True, indent=2)
        for left, right in zip(fresh.splitlines(), old.splitlines()):
            if left != right:
                print(f"- {right}", file=sys.stderr)
                print(f"+ {left}", file=sys.stderr)
                break
        return 1

    headline = format_headline(TASK_SHA16, N_TRAIN, N_HELD, report)
    readme = (ROOT / "README.md").read_text()
    try:
        found = extract_headline(readme)
    except AssertionError as exc:
        return fail(str(exc))
    if found != headline:
        print("README headline drift. Expected:", file=sys.stderr)
        print(headline, file=sys.stderr)
        print("Found:", file=sys.stderr)
        print(found, file=sys.stderr)
        return 1
    for line in ABOUT_LINES:
        if line not in readme:
            return fail(f"README is missing the problem line: {line}")
    opening = [line for line in readme.splitlines() if line in ABOUT_LINES]
    if opening != list(ABOUT_LINES):
        return fail("README problem statement is not the three About lines, in order")
    for phrase in FORBIDDEN_README_PHRASES:
        if phrase in readme:
            return fail(f"README contains a removed claim: {phrase}")

    pyproject = (ROOT / "pyproject.toml").read_text()
    if ABOUT not in pyproject:
        return fail("pyproject description does not match the About sentence")

    modes = (ROOT / "FAILURE_MODES.md").read_text()
    for token in ("n=24", "n<30", "single dataset", "clairvoyance", "0.6"):
        if token not in modes:
            return fail(f"FAILURE_MODES.md is missing {token!r}")

    prereg = (ROOT / "PREREG.md").read_text()
    if "Amendment 2026-11-16" not in prereg:
        return fail("PREREG.md is missing the 2026-11-16 amendment")
    if "in-place edits are prohibited" not in prereg:
        return fail("PREREG.md lost the frozen-text rule")

    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text()
    if "make check" not in workflow:
        return fail("CI checks.yml does not run make check")

    tested = run([sys.executable, "-m", "pytest", "tests", "-q"], env)
    sys.stdout.write(tested.stdout)
    print("check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
