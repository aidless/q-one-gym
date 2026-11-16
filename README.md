# Q-One Gym

[![CI](https://github.com/aidless/q-one-gym/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-gym/actions/workflows/checks.yml)

Offline Brier scores for three heuristics on 80 tasks from 40 game episodes.
Held-out n=24 is below this project's n<30 display cutoff, so the gate stays HOLD.
No LLM results.

STATUS: WORK-IN-PROGRESS — not A yet. The GitHub About description is still the old five-feature sentence. Replace it with the three sentences above. This change cannot edit that setting.

## Headline

`make check` rebuilds this block from `data/games.csv`. A mismatch fails the check.

<!-- HEADLINE:START -->
task_sha256_16=add2402464df8e75 train=56 held_out=24
base_rate brier=0.2498 ci95=[0.1906, 0.3093] rel=0.0171 res=0.0017 unc=0.2344 display_only=true
uniform brier=0.2500 ci95=[0.2500, 0.2500] rel=0.0156 res=0.0000 unc=0.2344 display_only=true sign_wins=9 sign_losses=15 sign_ties=0 sign_p=0.3075 delta=+0.0002 rel_gap=-0.0015 gate=HOLD reasons=n_below_30_murphy_display_only,delta_brier_not_le_-0.02,canary_check_not_run,held_out_iteration_log_not_audited
act_majority brier=0.2268 ci95=[0.1646, 0.2914] rel=0.0375 res=0.0451 unc=0.2344 display_only=true sign_wins=10 sign_losses=2 sign_ties=12 sign_p=0.0386 delta=-0.0230 rel_gap=+0.0204 gate=HOLD reasons=n_below_30_murphy_display_only,reliability_regression_gt_0.02_display_only,canary_check_not_run,held_out_iteration_log_not_audited
llm_results=none
<!-- HEADLINE:END -->

`ci95` is a percentile bootstrap interval (2000 resamples, nearest rank, seed 20261023). It describes the pooled Brier. It does not promote a forecaster. `display_only=true` means the Murphy reliability, resolution, and uncertainty terms are shown and are not a diagnosis. `uniform`'s interval is a point because a forecast of 0.5 has squared error 0.25 on every binary outcome. `act_majority`'s interval contains the base-rate point estimate. Both gates are HOLD: n=24 is below the cutoff, the canary check and the held-out iteration audit are not run, and `act_majority`'s reliability gap is recorded but not used as a diagnosis. The sign counts are an exact binomial sign test on per-task Brier wins and losses.

## Reproduce

```bash
python3 -m pip install pytest   # the only third-party package
make check                      # offline: rebuild tasks, rescore, diff this file, run tests
```

`make check` does not use the network and ignores `GAMES_CSV`. It expects a fresh ledger of 6 events. `python3 run.py --offline` appends to `results/ledger.jsonl` if that file already exists; `python3 run.py --verify` replays the hash chain and exits non-zero if an event was altered.

An OpenAI-compatible forecaster is optional and is not part of the check:

```bash
LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_MODEL=qwen2.5:7b python3 run.py --llm
```

No such run is recorded in `results/`.

## What was scored

| Name | Probability | On this held-out split |
|---|---|---|
| `base_rate` | Training-split outcome frequency for that task type | Reference value. Not a promotion candidate. |
| `uniform` | 0.5 | HOLD |
| `act_majority` | 0.6 if `act_a > act_b`, else 0.4, on `win_a` only; otherwise `base_rate` | HOLD |

Tasks are built from the vendored 40-row table (`data/PROVENANCE.md`) by `tasks/build_tasks.py` with seed 20261023. `win_a` asks whether side a won. `money_hi` asks whether the winner's final money exceeded 110000. The split is 70/30 by type.

## Related work

ForecastBench scores forecasts of future events that have no known answer at submission time (Karger, Bastani, Yueh-Han, Jacobs, Halawi, Zhang, and Tetlock, ICLR 2025, [arXiv:2409.19839](https://arxiv.org/abs/2409.19839)). This repository does not use ForecastBench questions, code, or leaderboard. The labels here are already columns in a 40-row table.

Reference class forecasting, as defined by Flyvbjerg (2006, *Project Management Journal* 37(3), 5–15, [doi:10.1177/875697280603700302](https://doi.org/10.1177/875697280603700302)), places a project in the outcome distribution of comparable past projects. `base_rate` is the training-split mean of a binary label. It is not that procedure.

The reliability − resolution + uncertainty split of the Brier score is the Murphy decomposition (Murphy, 1973, *Journal of Applied Meteorology* 12(4), 595–600, [doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2)). Binned components need extra within-bin terms when a bin contains more than one probability (Stephenson, Coelho, and Jolliffe, 2008, *Weather and Forecasting* 23(4), 752–757, [doi:10.1175/2007WAF2006116.1](https://doi.org/10.1175/2007WAF2006116.1)). The identity checked in `gym/scoring.py` is reliability − resolution + uncertainty against the Brier score of the bin-mean probabilities. The n<30 display cutoff is this project's rule (`PREREG.md`), not a threshold stated in that 2008 paper.

## Limits

Read [FAILURE_MODES.md](FAILURE_MODES.md) before treating the point estimates as a finding. The frozen promotion rule and the 2026-11-16 amendment are in [PREREG.md](PREREG.md). There is no self-improvement loop. Nothing here is a claim that some combination of ledger, decomposition, and gate is missing from other open systems.

*Author: Zewen Liu (Independent Researcher) · [github.com/aidless](https://github.com/aidless)*
