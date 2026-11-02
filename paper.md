# Q-One Gym：可复现的校准决策健身房——带哈希链预测账本与外部门控自改进

## 摘要（Abstract）

**背景**：LLM 预测器常被直接用作「自动优化目标」，但判断与自动执行之间的红线常被忽略。一个校准好的决策系统需要：任务可自动解析、基线（reference class）是必须击败的对手、所有预测/结果/门控决策可复算、Brier 分解而非单指标、以及自改进被外部冻结规则门控。

**方法**：Q-One Gym 把这五件事组合成一个约 600 行、一个下午可审计完的开放系统。任务从一份冻结的数据集（40 个游戏 episode，CC0）生成 80 个 backtest 任务（56 train + 24 held-out，seed 20261023），outcome 在生成时冻结、可由计算机械解析（clairvoyance 检查：有 CSV 无上下文的人可机械解析每个任务）。三个基线（reference-class base rate / uniform / act-majority heuristic）用 Brier + Murphy 分解 + McNemar 计数评分；每个预测/结果/门控决策追加进哈希链账本，`verify` 重放整条链。自改进被冻结的推广规则门控（PREREG.md）：候选只在冻结 held-out 集上满足「ΔBrier ≤ −0.02 ∧ 无可靠性回归 > 0.02 ∧ canary 一致 ∧ 未对 held-out 迭代」时才推广，否则 HOLD。

**结果**（真实复算，2026-11-02 实测）：3 个基线端到端跑通。`base_rate` pooled Brier 0.2498、`uniform` 0.25、`act_majority` 0.2268。`act_majority` 对 base_rate 的 McNemar p=0.0386（10 wins / 2 losses / 12 ties），但**门 `gate.verdict = HOLD`**（`rel_regression=0.0204 > 0`，校准回归不合格）——**不因单指标显著而提升**。哈希链账本重放一致（`run.py --verify` 返回 `(True, 'N events OK')`），6 个单元测试通过（scoring + ledger）。

**边界**：v0 是 80 任务的**单数据集 backtest**，刻意小规模——目的是**协议**（账本 + 分解 + 外部门），**不是 leaderboard 数字**。无 LLM 运行（`--llm` 路径需外部端点，本仓未声明 LLM 表现）。无自动执行（协议红线：LLM 判断是建议证据，永不自动执行任何事）。Brier 在 n<30 的 cell 上为 display-only（Murphy 分解标注）。

**关键词**：校准决策；Brier 分解；reference class；哈希链账本；门控自改进；预注册
