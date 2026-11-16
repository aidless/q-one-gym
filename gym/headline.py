"""README headline rendered from a scored report. `make check` diffs this text."""

ABOUT_LINES = (
    "Offline Brier scores for three heuristics on 80 tasks from 40 game episodes.",
    "Held-out n=24 is below this project's n<30 display cutoff, so the gate stays HOLD.",
    "No LLM results.",
)
ABOUT = " ".join(ABOUT_LINES)

HEADLINE_START = "<!-- HEADLINE:START -->"
HEADLINE_END = "<!-- HEADLINE:END -->"

# Removed from the README on purpose. `make check` fails if one is restored.
FORBIDDEN_README_PHRASES = (
    "no open system combines them",
    "What Q-One Gym adds",
    "externally-gated self-improvement",
    "McNemar",
)

GAMES_SHA256 = "37a08ff1151631277124fb4d786328d97f68b6090a99af5b202e95146c93567b"
TASK_SHA16 = "add2402464df8e75"
N_TRAIN = 56
N_HELD = 24


def format_headline(task_sha16, n_train, n_held, report):
    lines = [f"task_sha256_16={task_sha16} train={n_train} held_out={n_held}"]
    for name in ("base_rate", "uniform", "act_majority"):
        entry = report[name]
        ci = entry["brier_bootstrap95"]
        murphy = entry["murphy"]
        bits = [
            f"{name} brier={entry['pooled_brier']:.4f}",
            f"ci95=[{ci['lo']:.4f}, {ci['hi']:.4f}]",
            f"rel={murphy['reliability']:.4f}",
            f"res={murphy['resolution']:.4f}",
            f"unc={murphy['uncertainty']:.4f}",
            f"display_only={str(entry['murphy_display_only']).lower()}",
        ]
        versus = entry.get("vs_base_rate")
        if versus:
            bits.append(
                f"sign_wins={versus['wins']} sign_losses={versus['losses']} "
                f"sign_ties={versus['ties']} sign_p={versus['p']:.4f}"
            )
        gate = entry.get("gate")
        if gate:
            bits.append(f"delta={gate['delta_brier']:+.4f}")
            bits.append(f"rel_gap={gate['rel_regression']:+.4f}")
            bits.append(f"gate={gate['verdict']}")
            bits.append("reasons=" + ",".join(gate["reasons"]))
        lines.append(" ".join(bits))
    lines.append("llm_results=none")
    return "\n".join(lines)


def extract_headline(text):
    start = text.find(HEADLINE_START)
    end = text.find(HEADLINE_END)
    if start < 0 or end < 0 or end < start:
        raise AssertionError("README missing HEADLINE markers")
    inner = text[start + len(HEADLINE_START):end]
    if inner.startswith("\n"):
        inner = inner[1:]
    if inner.endswith("\n"):
        inner = inner[:-1]
    return inner


def assert_v1_numbers(report):
    """Locks the recomputed v1 offline result. Raises AssertionError on drift."""
    assert round(report["base_rate"]["pooled_brier"], 4) == 0.2498
    assert round(report["uniform"]["pooled_brier"], 4) == 0.2500
    assert round(report["act_majority"]["pooled_brier"], 4) == 0.2268
    assert "gate" not in report["base_rate"]
    uniform = report["uniform"]["gate"]
    majority = report["act_majority"]["gate"]
    for gate in (uniform, majority):
        assert gate["verdict"] == "HOLD"
        assert gate["n_held"] == N_HELD
        assert gate["murphy_display_only"] is True
        assert "n_below_30_murphy_display_only" in gate["reasons"]
        assert "canary_check_not_run" in gate["reasons"]
        assert "held_out_iteration_log_not_audited" in gate["reasons"]
    assert "delta_brier_not_le_-0.02" in uniform["reasons"]
    assert "delta_brier_not_le_-0.02" not in majority["reasons"]
    assert "reliability_regression_gt_0.02_display_only" in majority["reasons"]
    assert majority["delta_brier"] == -0.023
    assert majority["rel_regression"] == 0.0204
    paired = report["act_majority"]["vs_base_rate"]
    assert (paired["wins"], paired["losses"], paired["ties"]) == (10, 2, 12)
    assert round(paired["p"], 4) == 0.0386
    uniform_paired = report["uniform"]["vs_base_rate"]
    assert (uniform_paired["wins"], uniform_paired["losses"], uniform_paired["ties"]) == (9, 15, 0)
    for name in ("base_rate", "uniform", "act_majority"):
        assert report[name]["murphy_display_only"] is True
        ci = report[name]["brier_bootstrap95"]
        assert ci["n"] == N_HELD and ci["n_boot"] == 2000 and ci["seed"] == 20261023
        assert ci["lo"] <= report[name]["pooled_brier"] <= ci["hi"]
