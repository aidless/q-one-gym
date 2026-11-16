"""Scoring: Brier, Murphy decomposition (10 bins), interval score, sign-test p. Pure stdlib."""
import math
import random

def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)

def murphy(ps, ys, k=10):
    """Binned reliability, resolution, and uncertainty.

    reliability - resolution + uncertainty equals `bs_recal`, the Brier score
    after each probability is replaced by its bin mean. That quantity need not
    equal the raw Brier score when a bin contains more than one distinct
    probability (Stephenson, Coelho, and Jolliffe 2008). This function does
    not apply the project's n<30 display-only rule; the gate does.
    """
    o = sum(ys) / len(ys)
    rel = res = 0.0
    n = len(ps)
    recal = []
    for b in range(k):
        lo, hi = b / k, (b + 1) / k
        idx = [i for i, p in enumerate(ps) if (lo <= p < hi) or (b == k - 1 and p == hi)]
        if not idx:
            continue
        nb = len(idx)
        pbar = sum(ps[i] for i in idx) / nb
        obar = sum(ys[i] for i in idx) / nb
        rel += (nb / n) * (pbar - obar) ** 2
        res += (nb / n) * (obar - o) ** 2
        recal += [(pbar, ys[i]) for i in idx]
    bs_recal = sum((p - y) ** 2 for p, y in recal) / n
    return {'reliability': rel, 'resolution': res, 'uncertainty': o * (1 - o), 'bs_recal': bs_recal}

def interval_score(los, his, ys, alpha=0.2):
    out = []
    for lo, hi, y in zip(los, his, ys):
        s = hi - lo
        if y < lo:
            s += (2 / alpha) * (lo - y)
        if y > hi:
            s += (2 / alpha) * (y - hi)
        out.append(s)
    return sum(out) / len(out)

def sign_test_p(wins, losses):
    """Exact two-sided binomial p for paired win/loss counts."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)

def paired_vs_base(ps_c, ps_b, ys):
    """Per-task strict-Brier comparison: candidate vs baseline."""
    w = l = t = 0
    for pc, pb, y in zip(ps_c, ps_b, ys):
        bc, bb = (pc - y) ** 2, (pb - y) ** 2
        if bc < bb:
            w += 1
        elif bc > bb:
            l += 1
        else:
            t += 1
    return {'wins': w, 'losses': l, 'ties': t, 'p': sign_test_p(w, l)}


BOOT_N = 2000
BOOT_SEED = 20261023


def bootstrap_mean_ci(values, n_boot=BOOT_N, seed=BOOT_SEED, alpha=0.05):
    """Percentile interval for a mean, by nearest rank.

    Resamples are drawn with replacement using random.Random(seed). After the
    bootstrap means are sorted ascending, the lower endpoint is the order
    statistic at 1-based rank ceil(alpha/2 * n_boot), and the upper endpoint
    is the order statistic at 1-based rank ceil((1-alpha/2) * n_boot).
    """
    if n_boot < 1:
        raise ValueError('n_boot')
    if not values:
        raise ValueError('empty')
    rng = random.Random(seed)
    n = len(values)
    stats = []
    for _ in range(n_boot):
        total = 0.0
        for _i in range(n):
            total += values[rng.randrange(n)]
        stats.append(total / n)
    stats.sort()
    lo_i = min(max(math.ceil((alpha / 2) * n_boot) - 1, 0), n_boot - 1)
    hi_i = min(max(math.ceil((1 - alpha / 2) * n_boot) - 1, 0), n_boot - 1)
    return {
        'method': 'percentile_nearest_rank',
        'n': n,
        'n_boot': n_boot,
        'seed': seed,
        'alpha': alpha,
        'lo': stats[lo_i],
        'hi': stats[hi_i],
    }


def bootstrap_brier_ci(ps, ys, n_boot=BOOT_N, seed=BOOT_SEED, alpha=0.05):
    """Descriptive percentile interval for the mean squared error."""
    errs = [(p - y) ** 2 for p, y in zip(ps, ys)]
    out = bootstrap_mean_ci(errs, n_boot=n_boot, seed=seed, alpha=alpha)
    out['point'] = brier(ps, ys)
    return out


def promotion_gate(delta_brier, rel_regression, n_held, canary_passed=None, iteration_clean=None):
    """PREREG v1.0 rules 1–4, plus the n<30 display-only block.

    Comparisons use the unrounded scores. `canary_passed` and `iteration_clean`
    are None when that check was not executed. None blocks PROMOTE. A verdict
    of PROMOTE requires n_held >= 30 and every rule checked and passed.
    """
    reasons = []
    if n_held < 30:
        reasons.append('n_below_30_murphy_display_only')
    if not (delta_brier <= -0.02):
        reasons.append('delta_brier_not_le_-0.02')
    if rel_regression > 0.02:
        reasons.append(
            'reliability_regression_gt_0.02_display_only' if n_held < 30
            else 'reliability_regression_gt_0.02'
        )
    if canary_passed is None:
        reasons.append('canary_check_not_run')
    elif canary_passed is not True:
        reasons.append('canary_failed')
    if iteration_clean is None:
        reasons.append('held_out_iteration_log_not_audited')
    elif iteration_clean is not True:
        reasons.append('iterated_against_held_out')
    return {
        'delta_brier': round(delta_brier, 4),
        'rel_regression': round(rel_regression, 4),
        'n_held': n_held,
        'murphy_display_only': n_held < 30,
        'verdict': 'HOLD' if reasons else 'PROMOTE',
        'reasons': reasons,
    }
