import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gym.scoring import brier, murphy, interval_score, sign_test_p, paired_vs_base  # noqa: E402
from gym.ledger import Ledger  # noqa: E402


def test_brier_perfect():
    assert abs(brier([1.0, 0.0], [1, 0])) < 1e-12
    assert abs(brier([0.5, 0.5], [1, 0]) - 0.25) < 1e-12


def test_murphy_identity():
    ps, ys = [0.2, 0.4, 0.6, 0.8, 0.3, 0.7, 0.9, 0.1, 0.5, 0.65], [0, 1, 1, 1, 0, 1, 1, 0, 0, 1]
    m = murphy(ps, ys)
    assert abs(m['reliability'] - m['resolution'] + m['uncertainty'] - m['bs_recal']) < 1e-9


def test_interval_score_covers():
    assert abs(interval_score([0.3], [0.7], [0.5]) - 0.4) < 1e-12      # covered: width only
    assert interval_score([0.3], [0.7], [0.9]) > 0.4                    # miss penalized


def test_sign_test():
    assert sign_test_p(0, 10) < 0.01
    assert sign_test_p(5, 5) > 0.5


def test_paired():
    r = paired_vs_base([0.9, 0.1], [0.5, 0.5], [1, 0])
    assert r['wins'] == 2 and r['ties'] == 0


def test_ledger_chain(tmp_path=None):
    p = Path('/tmp/_qone_gym_ledger_test.jsonl')
    p.unlink(missing_ok=True)
    led = Ledger(p)
    led.append('task_set_frozen', {'a': 1})
    led.append('run_recorded', {'b': 2})
    ok, msg = led.verify()
    assert ok, msg
    # tamper detection
    lines = p.read_text().splitlines()
    ev = json.loads(lines[0]); ev['payload']['a'] = 999
    lines[0] = json.dumps(ev, sort_keys=True, separators=(',', ':'))
    p.write_text('\n'.join(lines) + '\n')
    ok2, _ = Ledger(p).verify()
    assert not ok2
    p.unlink()
