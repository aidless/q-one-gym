# Q-One Gym pre-registration — frozen v1.0 (2026-10-23)

Frozen **before** any forecaster (baseline or LLM) is scored. Amendments must be appended with dates; in-place edits are prohibited.

## Task set

- Source: `data/games.csv`, 40 episodes (CC0 Kaggle dump, unchanged).
- Types: `win_a` (P(winner=a) | seed, pass/act turns), `money_hi` (P(winner money > 110000)).
- 80 tasks total (one per episode per type). Split **70/30 train/held-out**, stratified by type, `random.Random(20261023)`.
- The held-out set is **frozen for the life of v1**: no prompt, model, or heuristic may be iterated against it. Task set SHA-256 recorded in the ledger at freeze time.

## Forecasters

- `base_rate`: constant p = train-population outcome rate, per task type. **This is the reference class — the bar.**
- `uniform`: p = 0.5.
- `act_majority`: heuristic p = 0.6 for the side with more act turns (`win_a` only; `money_hi` falls back to base rate).
- `llm:*`: any OpenAI-compatible endpoint; prompt fixed below; temperature 0.

LLM prompt (fixed): "You are a calibrated forecaster. Given the features, output ONLY a JSON object {\"p\": <probability side a wins / event occurs, 0..1>, \"lo\": <0..1>, \"hi\": <0..1>} where [lo,hi] is your 80% interval."

## Scoring (frozen)

- Primary: **Brier score on held-out**, per forecaster, per type, and pooled.
- Murphy decomposition (10 equal bins): BS = reliability − resolution + uncertainty. With n<30 per cell: display-only, no diagnosis (Stephenson 2008).
- Interval score at α=0.2: IS = (hi−lo) + (2/α)(lo−y)·1[y<lo] + (2/α)(y−hi)·1[y>hi], averaged; reported separately, never pooled into Brier.
- Paired comparison vs `base_rate`: win/loss/tie counts per task (strictly lower Brier wins); exact binomial p on wins-vs-losses (sign-test flavor). No other inferential claims at v0 sample sizes.

## Promotion rule (the gate)

A candidate forecaster (or prompt/model variant) is **promoted** only if, on the frozen held-out set:

1. pooled ΔBrier vs current best ≤ **−0.02**, AND
2. no Murphy reliability regression > **0.02**, AND
3. canary consistency passes: on duplicated identical tasks, |Δp| ≤ 0.30 for ≥ 90% of pairs, AND
4. it was not iterated against the held-out set (iteration log lives in the ledger; any held-out-informed change disqualifies the candidate permanently).

Otherwise the outcome is **HOLD** — recorded, not retried silently. Gate decisions are ledger events.

## Non-goals / non-claims

No causal claims; no leaderboard generalization beyond this frozen set; v0 backtests outcomes already fixed at generation time; LLM forecasts are advice evidence, never auto-executed objectives.
