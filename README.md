# Q-One Gym

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

*Author: Zewen Liu (Independent Researcher) · [github.com/aidless](https://github.com/aidless)*
