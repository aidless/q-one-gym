#!/usr/bin/env python3
"""Q-One Gym runner. --offline (baselines) | --llm (OpenAI-compatible endpoint) | --verify."""
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gym.baselines import FORECASTERS, base_rate          # noqa: E402
from gym.ledger import Ledger                              # noqa: E402
from gym.scoring import brier, murphy, paired_vs_base      # noqa: E402

PROMPT = ('You are a calibrated forecaster. Given the features, output ONLY a JSON object '
          '{"p": <probability the event occurs, 0..1>, "lo": <0..1>, "hi": <0..1>} '
          'where [lo,hi] is your 80% interval.')


def load_tasks():
    f = ROOT / 'tasks' / 'tasks_v1.json'
    if not f.exists():
        sys.exit('run tasks/build_tasks.py first')
    return json.loads(f.read_text())


def llm_forecast(task, base, model):
    import urllib.request
    body = json.dumps({'model': model, 'temperature': 0, 'messages': [
        {'role': 'system', 'content': PROMPT},
        {'role': 'user', 'content': json.dumps({'question': task['question'], 'features': task['features']})}]}).encode()
    req = urllib.request.Request(os.environ['LLM_BASE_URL'].rstrip('/') + '/chat/completions',
                                 data=body, headers={'Content-Type': 'application/json',
                                                     'Authorization': 'Bearer ' + os.environ.get('LLM_API_KEY', 'x')})
    with urllib.request.urlopen(req, timeout=300) as r:
        txt = json.loads(r.read())['choices'][0]['message']['content']
    obj = json.loads(txt[txt.find('{'):txt.rfind('}') + 1])
    return float(obj['p'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--llm', action='store_true')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    led_path = ROOT / 'results' / 'ledger.jsonl'
    (ROOT / 'results').mkdir(exist_ok=True)
    led = Ledger(led_path)

    if args.verify:
        print(led.verify())
        return

    ts = load_tasks()
    train, held = ts['train'], ts['held_out']
    led.append('task_set_frozen', {'n_train': ts['n_train'], 'n_held': ts['n_held'],
                                   'sha16': __import__('hashlib').sha256(
                                       (ROOT / 'tasks' / 'tasks_v1.json').read_bytes()).hexdigest()[:16]})

    forecasters = dict(FORECASTERS)
    if args.llm:
        model = os.environ.get('LLM_MODEL', 'qwen2.5:7b')
        forecasters['llm:' + model] = lambda tr, t: llm_forecast(t, None, model)

    report = {}
    base_ps = None
    ys = [t['y'] for t in held]
    for name, fn in forecasters.items():
        ps = [fn(train, t) for t in held]
        led.append('run_recorded', {'forecaster': name, 'pooled_brier': brier(ps, ys)})
        entry = {'pooled_brier': brier(ps, ys),
                 'murphy': murphy(ps, ys),
                 'by_type': {ty: brier([p for p, t in zip(ps, held) if t['type'] == ty],
                                       [t['y'] for t in held if t['type'] == ty])
                             for ty in {t['type'] for t in held}}}
        if name == 'base_rate':
            base_ps = ps
        if base_ps is not None and name != 'base_rate':
            entry['vs_base_rate'] = paired_vs_base(ps, base_ps, ys)
        report[name] = entry

    # frozen promotion gate vs base_rate (PREREG rule 1+2)
    for name, e in report.items():
        if name == 'base_rate' or 'vs_base_rate' not in e:
            continue
        d = e['pooled_brier'] - report['base_rate']['pooled_brier']
        rel_reg = e['murphy']['reliability'] - report['base_rate']['murphy']['reliability']
        verdict = 'PROMOTE' if (d <= -0.02 and rel_reg <= 0.02) else 'HOLD'
        e['gate'] = {'delta_brier': round(d, 4), 'rel_regression': round(rel_reg, 4), 'verdict': verdict}
        led.append('gate_decision', {'candidate': name, **e['gate']})

    out = ROOT / 'results' / 'report_v1.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: {'pooled_brier': round(v['pooled_brier'], 4),
                          **({'gate': v['gate']['verdict']} if 'gate' in v else {})}
                      for k, v in report.items()}, indent=2))
    print('ledger:', led.verify()[1])


if __name__ == '__main__':
    main()
