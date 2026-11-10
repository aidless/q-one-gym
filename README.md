# Q-One Gym

[![CI](https://github.com/aidless/q-one-gym/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-gym/actions/workflows/checks.yml)

**A reproducible gym for calibrated decision-making under uncertainty — with a hash-chained forecast ledger and externally-gated self-improvement.**

The frontier claim (honest): the five components below each exist in prior work, but **no open system combines them**. Q-One Gym is that combination, in ~600 lines you can audit in an afternoon.

| Component | Closest prior art | What Q-One Gym adds |
|---|---|---|
| Auto-resolvable forecast tasks | ForecastBench | tasks are *decisions* with clairvoyance-tested resolution (Metaculus-style), resolvable by computation over a frozen dataset — zero API cost, zero contamination |
| Reference-class baseline | Flyvbjerg RCF | the base rate is a first-class forecaster every candidate must beat |
| Append-only forecast ledger | q-one-core protocol | every forecast/outcome/gate decision is hash-chained; `verify` replays the chain |
| Calibration reporting | Murphy decomposition | Brier is reported as reliability − resolution + uncertainty; n<30 ⇒ display-only |
| Gated self-improvement | RLVR / RaR | frozen held-out set never touched by iteration; canary consistency checks; promotion rule frozen in [PREREG.md](PREREG.md) |

Protocol red line (from [SYNTHESIS](https://github.com/aidless/q-one-core/blob/main/docs/SYNTHESIS.md)): **LLM judgments are advice evidence, never automatic optimization targets.** No forecast ever auto-executes anything.

## Quickstart

```bash
python3 tasks/build_tasks.py          # freeze task set + SHA-256 (seed 20261023)
python3 run.py --offline              # baselines end-to-end: ledger, scores, report
python3 run.py --verify               # replay the hash chain
python3 -m pytest tests/ -q           # unit tests (scoring + ledger)
# optional LLM forecaster (any OpenAI-compatible endpoint; slow on CPU):
LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_MODEL=qwen2.5:7b python3 run.py --llm
```

Outputs land in `results/` (JSONL ledger + report). The report's headline table: **did any forecaster beat the reference class on the frozen held-out set?**

### Captured output (2026-11-10 re-run, fresh clone state)

```text
$ GAMES_CSV=../agent-databench/data/games.csv python3 tasks/build_tasks.py
frozen: train=56 held_out=24 sha256=add2402464df8e75

$ python3 run.py --offline          (tail)
  "act_majority": {
    "pooled_brier": 0.2268,
    "gate": "HOLD"
  }
}
ledger: 6 events OK                 # one --offline run appends 6 events

$ python3 run.py --verify
(True, '6 events OK')

$ python3 -m pytest tests/ -q
6 passed in 0.02s
```

## Results (committed `results/report_v1.json`)

| Forecaster | pooled Brier (24 held-out) | Δ vs base rate | McNemar vs base rate | Gate |
|---|---|---|---|---|
| base_rate (reference class) | 0.2498 | — | — | — |
| uniform | 0.2500 | +0.0002 | wins 9 / losses 15 / ties 0, p = 0.3075 | **HOLD** |
| act_majority | **0.2268** | −0.0230 | wins 10 / losses 2 / ties 12, **p = 0.0386** | **HOLD** |

Reading: `act_majority` beats the reference class with McNemar p = 0.0386 (< 0.05)
and ΔBrier = −0.023, but the frozen promotion rule still says **HOLD** — n = 24
held-out tasks is below the preregistered evidence bar ([PREREG.md](PREREG.md);
Murphy decomposition and n<30 display-only rule in `gym/scoring.py`). Nothing is
promoted; the ledger records the HOLD decision.

## Task types (v0, frozen)

Generated from `data/games.csv` (40 game episodes, CC0; copy from agent-databench):

- **`win_a`** — given pre-outcome stats (seed, pass turns, act turns for both sides), forecast P(winner = side a). Outcome resolved by the `winner` column.
- **`money_hi`** — forecast P(winning side's final money > 110,000). Resolved by computation.

Both are backtest tasks: outcomes were frozen at generation time; models cannot "know" them except through the features. Clairvoyance check: a person with the CSV and no context can resolve every task mechanically.

## Repository layout

```
PREREG.md            frozen pre-registration (design, split, promotion rule) — v1.0
tasks/build_tasks.py task generator + SHA-256 freeze
gym/scoring.py       Brier, Murphy decomposition, interval score, McNemar counts
gym/ledger.py        append-only hash-chained event ledger (q-one-core shape)
gym/baselines.py     reference-class (base rate), uniform, act-majority heuristic
run.py               offline / llm / verify entrypoints
tests/               unit tests
```

## Scope (non-claims)

v0 is a backtest gym on 80 tasks from one dataset — small on purpose: the point is the *protocol* (ledger + decomposition + external gates), not a leaderboard number. The path to M2 (break the plateau) is: candidates (prompts/models/routing) are promoted only by the frozen rule on the frozen set. Everything else stays HOLD.

### Limits

- One dataset (40 CC0 game episodes → 80 tasks), one offline run: no cross-domain
  evidence, no LLM-forecaster numbers committed (`--llm` path exists but no run
  with a real endpoint is recorded in `results/`).
- Held-out set is 24 tasks — below the n ≥ 30 bar, so all gates correctly return
  HOLD even where McNemar p < 0.05.
- Baselines are heuristics (uniform / act-majority), not model forecasts.

*Author: Zewen Liu (Independent Researcher) · [github.com/aidless](https://github.com/aidless)*
