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

## 测试与复算（2026-11-01 实测）

```bash
python3 -m pytest tests/ -q        # 6 passed（scoring + ledger 单元测试）
python3 run.py --offline           # 基线端到端：base_rate Brier 0.2498 / uniform 0.25 /
                                   #   act_majority 0.2268；ledger 14 events OK
python3 run.py --verify            # (True, '14 events OK') —— 重放哈希链全部一致
```

报告头部（`results/report_v1.json`）关键数字与上面 `--offline` 输出一致：
base_rate pooled Brier `0.2497874`、uniform `0.25`、act_majority `0.2267687`。
act_majority 对 base_rate 的 McNemar `p=0.0386`（10 wins / 2 losses / 12 ties），
但**门 `gate.verdict = HOLD`**（`rel_regression=0.0204 > 0`，校准回归不合格，
不提升）。

## Fail-closed 声明

本健身房**默认 fail-closed**（对「假装提升」零容忍）：

- **推广门全拒绝**：候选只被推广当**全部**冻结判据满足（`ΔBrier ≤ −0.02` ∧ 无可靠性回归 > 0.02 ∧ canary 一致 ∧ 未对 held-out 迭代）。否则**唯一合法结局是 HOLD**——记录进账本，**不静默重试**，**不因单指标显著而提升**（`act_majority` 虽 McNemar p=0.0386 显著，但因 `rel_regression=0.0204 > 0` 门 HOLD）。
- **账本 append-only + 哈希链**：每个预测/结果/门控决策是哈希链事件；`run.py --verify` 重放整条链，任何不一致即失败。
- **LLM 判断是建议证据，永不自动执行任何事**（协议红线）。
- **held-out 集冻结**：任何 prompt/模型/heuristic 不得对 held-out 迭代；违反即候选永久取消资格。

> 立场：宁可不推广、宁可 HOLD，也不在未满足全部判据时放行。fail-closed 意味着「不满足冻结规则就不提升」，而不是「看着像赢了就提升」。

## 证明什么 / 不证明什么

**证明什么**：
- 协议正确性：80 个冻结任务（56 train + 24 held-out，seed 20261023）上，
  参考类（base rate）/uniform/act-majority 三个基线可端到端跑通，产出 Brier +
  Murphy 分解 + McNemar 计数 + 哈希链账本（14 events）且 `--verify` 重放一致。
- 外部门禁存在并生效：`act_majority` 虽在 McNemar 上显著（p=0.0386），但校准
  回归不合格（`rel_regression=0.0204`），门 `HOLD`——**不因单指标显著而提升**。

**不证明什么**：
- v0 是 **80 任务的单数据集 backtest**，刻意小规模——目的是**协议**（账本 +
  分解 + 外部门），**不是 leaderboard 数字**。README 已注明 "small on purpose"。
- **无 LLM 运行**：`results/ledger.jsonl` 与 `report_v1.json` 只含三个基线
  （base_rate / uniform / act_majority），**不含任何 LLM forecaster 结果**；
  `--llm` 路径需要外部端点（如 Ollama），且 CPU 慢——**本仓未声明 LLM 表现**。
- **无自动执行**：任何 forecast 不自动执行任何事（协议红线，见顶部）。
- 任务集从 `agent-databench/data/games.csv` 生成（`tasks/build_tasks.py` 中
  `SRC` 为硬编码绝对路径 `/home/liuzewen/文档/求职demo/agent-databench/data/games.csv`，
  本机之外需改路径重跑 `python3 tasks/build_tasks.py` 才能复算任务集）。
- Brier 在 n<30 的 cell 上为**display-only**（Murphy 分解标注），不构成统计结论。

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
