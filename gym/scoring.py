"""Scoring: Brier, Murphy decomposition (10 bins), interval score, sign-test p. Pure stdlib."""
import math

def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)

def murphy(ps, ys, k=10):
    """REL - RES + UNC == bs_recal (Stephenson 2008: identity holds for the
    bin-recalibrated forecast, not for raw BS; we report both)."""
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
