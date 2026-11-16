#!/usr/bin/env python3
"""Q-One Gym runner. --offline (baselines) | --llm (OpenAI-compatible endpoint) | --verify.

--offline is the default scoring path. It does not call a model. --llm adds one
OpenAI-compatible forecaster and is not part of `make check`. No LLM result is
committed.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gym.baselines import FORECASTERS  # noqa: E402
from gym.ledger import Ledger  # noqa: E402
from gym.scoring import (  # noqa: E402
    brier,
    bootstrap_brier_ci,
    murphy,
    paired_vs_base,
    promotion_gate,
)

PROMPT = (
    'You are a calibrated forecaster. Given the features, output ONLY a JSON object '
    '{"p": <probability the event occurs, 0..1>, "lo": <0..1>, "hi": <0..1>} '
    'where [lo,hi] is your 80% interval.'
)


def without_outcome(task):
    """Fields a forecaster may see. The outcome `y` is not among them."""
    return {k: task[k] for k in ('task_id', 'type', 'features', 'question')}


def load_tasks(path=None):
    f = Path(path) if path else ROOT / 'tasks' / 'tasks_v1.json'
    if not f.exists():
        sys.exit('run tasks/build_tasks.py first')
    return json.loads(f.read_text())


def llm_forecast(task, model):
    import urllib.request
    body = json.dumps({
        'model': model,
        'temperature': 0,
        'messages': [
            {'role': 'system', 'content': PROMPT},
            {'role': 'user', 'content': json.dumps({
                'question': task['question'],
                'features': task['features'],
            })},
        ],
    }).encode()
    req = urllib.request.Request(
        os.environ['LLM_BASE_URL'].rstrip('/') + '/chat/completions',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.environ.get('LLM_API_KEY', 'x'),
        },
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        txt = json.loads(response.read())['choices'][0]['message']['content']
    obj = json.loads(txt[txt.find('{'):txt.rfind('}') + 1])
    return float(obj['p'])


def build_report(train, held, forecasters):
    """Score forecasters on held-out tasks. Outcomes are not passed to them.

    Canary consistency and the held-out iteration audit are not executed.
    promotion_gate records those checks as not run, which blocks PROMOTE.
    """
    report = {}
    base_ps = None
    ys = [t['y'] for t in held]
    visible = [without_outcome(t) for t in held]
    n_held = len(held)
    for name, fn in forecasters.items():
        ps = [fn(train, task) for task in visible]
        entry = {
            'pooled_brier': brier(ps, ys),
            'brier_bootstrap95': bootstrap_brier_ci(ps, ys),
            'murphy': murphy(ps, ys),
            'murphy_display_only': n_held < 30,
            'by_type': {
                ty: brier(
                    [p for p, task in zip(ps, held) if task['type'] == ty],
                    [task['y'] for task in held if task['type'] == ty],
                )
                for ty in sorted({task['type'] for task in held})
            },
        }
        if name == 'base_rate':
            base_ps = ps
        if base_ps is not None and name != 'base_rate':
            entry['vs_base_rate'] = paired_vs_base(ps, base_ps, ys)
        report[name] = entry

    for name, entry in report.items():
        if name == 'base_rate' or 'vs_base_rate' not in entry:
            continue
        delta = entry['pooled_brier'] - report['base_rate']['pooled_brier']
        rel_gap = entry['murphy']['reliability'] - report['base_rate']['murphy']['reliability']
        entry['gate'] = promotion_gate(
            delta, rel_gap, n_held, canary_passed=None, iteration_clean=None,
        )
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--llm', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--ledger', default=None)
    ap.add_argument('--report', default=None)
    ap.add_argument('--tasks', default=None)
    args = ap.parse_args(argv)

    led_path = Path(args.ledger) if args.ledger else ROOT / 'results' / 'ledger.jsonl'
    report_path = Path(args.report) if args.report else ROOT / 'results' / 'report_v1.json'
    led_path.parent.mkdir(parents=True, exist_ok=True)
    led = Ledger(led_path)

    if args.verify:
        ok, msg = led.verify()
        print((ok, msg))
        return 0 if ok else 1

    ts = load_tasks(args.tasks)
    train, held = ts['train'], ts['held_out']
    task_path = Path(args.tasks) if args.tasks else ROOT / 'tasks' / 'tasks_v1.json'
    led.append('task_set_frozen', {
        'n_train': ts['n_train'],
        'n_held': ts['n_held'],
        'sha16': hashlib.sha256(task_path.read_bytes()).hexdigest()[:16],
    })

    forecasters = dict(FORECASTERS)
    if args.llm:
        model = os.environ.get('LLM_MODEL', 'qwen2.5:7b')
        forecasters['llm:' + model] = lambda train, task, model=model: llm_forecast(task, model)

    report = build_report(train, held, forecasters)
    for name, entry in report.items():
        led.append('run_recorded', {'forecaster': name, 'pooled_brier': entry['pooled_brier']})
    for name, entry in report.items():
        if 'gate' not in entry:
            continue
        led.append('gate_decision', {
            'candidate': name,
            'verdict': entry['gate']['verdict'],
            'reasons': entry['gate']['reasons'],
        })

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({
        k: {
            'pooled_brier': round(v['pooled_brier'], 4),
            **({'gate': v['gate']['verdict']} if 'gate' in v else {}),
        }
        for k, v in report.items()
    }, indent=2))
    print('ledger:', led.verify()[1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
