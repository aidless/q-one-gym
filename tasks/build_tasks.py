#!/usr/bin/env python3
"""Freeze the v1 task set from data/games.csv (seed 20261023). Appends nothing later."""
import csv, json, random, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path('/home/liuzewen/文档/求职demo/agent-databench/data/games.csv')
OUT = ROOT / 'tasks' / 'tasks_v1.json'
SEED = 20261023
MONEY_HI = 110000.0

def main():
    rows = list(csv.DictReader(SRC.open()))
    tasks = []
    for r in rows:
        feats = {
            'seed_mod': int(r['seed']) % 1000,
            'pass_a': int(r['pass_turns_a']), 'pass_b': int(r['pass_turns_b']),
            'act_a': int(r['act_turns_a']), 'act_b': int(r['act_turns_b']),
        }
        tasks.append({'task_id': f"win_a::{r['episode_id'][:8]}", 'type': 'win_a',
                      'features': feats, 'question': 'P(winner = side a)?',
                      'y': 1 if r['winner'] == 'a' else 0})
        y_money = 1 if float(r['money_a'] if r['winner'] == 'a' else r['money_b']) > MONEY_HI else 0
        tasks.append({'task_id': f"money_hi::{r['episode_id'][:8]}", 'type': 'money_hi',
                      'features': {k: v for k, v in feats.items()},
                      'question': f'P(winner final money > {MONEY_HI:.0f})?', 'y': y_money})
    rng = random.Random(SEED)
    by_type = {}
    for t in tasks:
        by_type.setdefault(t['type'], []).append(t)
    train, held = [], []
    for typ, ts in sorted(by_type.items()):
        rng.shuffle(ts)
        k = round(len(ts) * 0.7)
        train += ts[:k]
        held += ts[k:]          # frozen for the life of v1
    blob = json.dumps({'seed': SEED, 'n_train': len(train), 'n_held': len(held),
                       'train': train, 'held_out': held}, sort_keys=True, ensure_ascii=False)
    OUT.write_text(blob)
    print(f"frozen: train={len(train)} held_out={len(held)} sha256={hashlib.sha256(blob.encode()).hexdigest()[:16]}")

if __name__ == '__main__':
    main()
