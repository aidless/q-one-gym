import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gym.scoring import brier, murphy, interval_score, sign_test_p, paired_vs_base  # noqa: E402
from gym.ledger import Ledger  # noqa: E402
from gym.baselines import FORECASTERS  # noqa: E402


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


def test_ledger_chain(tmp_path):
    p = tmp_path / 'ledger.jsonl'
    led = Ledger(p)
    led.append('task_set_frozen', {'a': 1})
    led.append('run_recorded', {'b': 2})
    ok, msg = led.verify()
    assert ok, msg
    lines = p.read_text().splitlines()
    ev = json.loads(lines[0])
    ev['payload']['a'] = 999
    lines[0] = json.dumps(ev, sort_keys=True, separators=(',', ':'))
    p.write_text('\n'.join(lines) + '\n')
    ok2, message = Ledger(p).verify()
    assert not ok2
    assert 'hash mismatch' in message


def test_verify_cli_rejects_tamper(tmp_path):
    import subprocess
    p = tmp_path / 'ledger.jsonl'
    led = Ledger(p)
    led.append('task_set_frozen', {'a': 1})
    lines = p.read_text().splitlines()
    ev = json.loads(lines[0])
    ev['hash'] = '0' * 64
    lines[0] = json.dumps(ev)
    p.write_text('\n'.join(lines) + '\n')
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(root / 'run.py'), '--verify', '--ledger', str(p)],
        cwd=root, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert 'False' in result.stdout


def test_bootstrap_constant_and_repeatable():
    from gym.scoring import bootstrap_brier_ci
    ci = bootstrap_brier_ci([0.5, 0.5], [1, 0], n_boot=32, seed=1)
    assert ci['lo'] == ci['hi'] == ci['point'] == 0.25
    again = bootstrap_brier_ci([0.2, 0.8, 0.4], [0, 1, 1], n_boot=50, seed=7)
    assert again == bootstrap_brier_ci([0.2, 0.8, 0.4], [0, 1, 1], n_boot=50, seed=7)
    assert again['lo'] <= again['point'] <= again['hi']


def test_gate_cannot_promote_below_30_or_without_checks():
    from gym.scoring import promotion_gate
    blocked = promotion_gate(-0.05, 0.0, 24, canary_passed=True, iteration_clean=True)
    assert blocked['verdict'] == 'HOLD'
    assert 'n_below_30_murphy_display_only' in blocked['reasons']
    missing = promotion_gate(-0.05, 0.0, 40, canary_passed=None, iteration_clean=None)
    assert missing['verdict'] == 'HOLD'
    assert 'canary_check_not_run' in missing['reasons']
    assert 'held_out_iteration_log_not_audited' in missing['reasons']
    ready = promotion_gate(-0.05, 0.0, 40, canary_passed=True, iteration_clean=True)
    assert ready['verdict'] == 'PROMOTE'
    assert ready['reasons'] == []


def test_forecasters_do_not_read_scored_outcome():
    class Guard(dict):
        def __getitem__(self, key):
            if key == 'y':
                raise AssertionError('forecaster read the scored outcome')
            return dict.__getitem__(self, key)

    train = [
        {'type': 'win_a', 'y': 1, 'features': {'act_a': 1, 'act_b': 2}},
        {'type': 'win_a', 'y': 0, 'features': {'act_a': 3, 'act_b': 1}},
        {'type': 'money_hi', 'y': 1, 'features': {}},
        {'type': 'money_hi', 'y': 0, 'features': {}},
    ]
    tasks = [
        Guard(task_id='w', type='win_a', features={'act_a': 5, 'act_b': 1}, question='q', y=1),
        Guard(task_id='m', type='money_hi', features={'act_a': 1, 'act_b': 1}, question='q', y=0),
    ]
    for fn in FORECASTERS.values():
        for task in tasks:
            p = fn(train, task)
            assert isinstance(p, float)


def _frozen_tasks():
    import os
    import runpy
    os.environ.pop('GAMES_CSV', None)
    root = Path(__file__).resolve().parent.parent
    runpy.run_path(str(root / 'tasks' / 'build_tasks.py'), run_name='__main__')
    return json.loads((root / 'tasks' / 'tasks_v1.json').read_text())


def test_held_out_labels_do_not_change_forecasts_and_train_labels_do():
    from gym.baselines import base_rate
    from run import build_report, without_outcome
    from gym.headline import assert_v1_numbers
    ts = _frozen_tasks()
    train_ids = {t['task_id'] for t in ts['train']}
    held_ids = {t['task_id'] for t in ts['held_out']}
    assert train_ids.isdisjoint(held_ids)
    assert len(train_ids) == 56 and len(held_ids) == 24
    flipped = []
    for task in ts['held_out']:
        copy = dict(task)
        copy['y'] = 1 - task['y']
        flipped.append(copy)
    for fn in FORECASTERS.values():
        original = [fn(ts['train'], without_outcome(task)) for task in ts['held_out']]
        relabeled = [fn(ts['train'], without_outcome(task)) for task in flipped]
        assert original == relabeled
    flipped_train = []
    for task in ts['train']:
        copy = dict(task)
        copy['y'] = 1 - task['y']
        flipped_train.append(copy)
    assert any(
        base_rate(ts['train'], without_outcome(task)) != base_rate(flipped_train, without_outcome(task))
        for task in ts['held_out']
    )
    visible = without_outcome(ts['held_out'][0])
    assert 'y' not in visible
    assert_v1_numbers(build_report(ts['train'], ts['held_out'], FORECASTERS))


def test_labels_resolve_from_csv_columns():
    import csv
    ts = _frozen_tasks()
    by_id = {t['task_id']: t for t in ts['train'] + ts['held_out']}
    root = Path(__file__).resolve().parent.parent
    with (root / 'data' / 'games.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 40
    allowed = {'seed_mod', 'pass_a', 'pass_b', 'act_a', 'act_b'}
    for row in rows:
        prefix = row['episode_id'][:8]
        win = by_id[f'win_a::{prefix}']
        money = by_id[f'money_hi::{prefix}']
        assert win['y'] == (1 if row['winner'] == 'a' else 0)
        winner_money = float(row['money_a'] if row['winner'] == 'a' else row['money_b'])
        assert money['y'] == (1 if winner_money > 110000 else 0)
        assert set(win['features']) == allowed
        assert 'y' not in win['features']


def test_readme_headline_extractor_rejects_a_different_block():
    from gym.headline import extract_headline
    text = "<!-- HEADLINE:START -->\nalpha\n<!-- HEADLINE:END -->"
    assert extract_headline(text) == "alpha"
    assert extract_headline(text.replace("alpha", "beta")) != "alpha"
