# Failure modes

What this result can be mistaken for, and why that reading is wrong.

## Tiny n

Held-out n=24. The frozen rule in `PREREG.md` says Murphy components are display-only when n<30. Ten bins on 24 forecasts leave many bins empty, so reliability and resolution are unstable. The gate therefore returns HOLD and does not promote. The percentile bootstrap intervals are wide (base rate about 0.19 to 0.31; act-majority about 0.16 to 0.29) and overlap. They are descriptive. They are not a test, and they are not a promotion rule.

The exact sign test for act-majority is 10 wins and 2 losses, p≈0.039, with 12 ties. Those 12 comparisons are not evidence that a forecaster should be promoted. v1.0 already refuses extra inferential claims at this sample size.

## Single dataset

This is a single dataset: one table of 40 episodes from one game, flattened once. Both task types (`win_a`, `money_hi`) are labels on those same episodes. Nothing here is evidence about another game, another CSV, or forecasting questions that have not resolved yet.

## Clairvoyance test limits

Recomputing `y` from `winner` and the money columns shows that every task is resolvable by a person who has the CSV. That clairvoyance check is only resolvability. It is not a prospective forecast.

The features are same-episode aggregates (seed modulus, pass counts, act counts). They exclude the winner and the money columns, and the runner does not pass `y` into a forecaster. The tests lock those two facts. They do not show that the act counts were known before the episode ended, and they do not audit a future training loop that opens `held_out` and reads labels. The task JSON stores `y` beside the features. A later change that stops using `without_outcome` would see the answer.

ForecastBench (Karger et al., ICLR 2025) asks about events that are unresolved at submission time. This repository does not.

## Majority baseline strength

`act_majority` is a fixed rule: probability 0.6 if `act_a > act_b`, otherwise 0.4, and only on `win_a`. Ties in the act counts fall through to 0.4. On `money_hi` the rule copies `base_rate`, which is why the paired comparison has 12 ties — every held-out money task. The entire win/loss record is 12 `win_a` tasks. The 0.6 and 0.4 values are not fit on the training split. A hardcoded tilt on 12 items can move pooled Brier by a few hundredths without being a strong forecaster. `uniform` is the constant 0.5. For a binary outcome that constant has squared error 0.25 on every row, so its bootstrap interval is a point. That is an identity, not precision.

## Gate checks that this runner does not do

PREREG rules 3 and 4 (canary consistency, and an audit that the candidate was not iterated on the held-out set) are not executed. The report records them as not run. Either one is enough to HOLD, including if a later split has n≥30. There is no self-improvement loop in this repository.

The offline baselines do not emit intervals, so the preregistered interval score is not part of this result. `gym/scoring.py` still has the function, and the unit test only checks the formula.

## Ledger

`run.py --verify` checks the hash chain and fails if a payload and its stored hash disagree. One `--offline` run appends 6 events. A second run appends 6 more; verify will still pass on the longer chain. `make check` uses a fresh ledger and expects 6. Event hashes include a timestamp, so they are not a golden file.
