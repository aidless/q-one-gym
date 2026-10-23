"""Append-only hash-chained event ledger (q-one-core event shape)."""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path

def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.events = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.events.append(json.loads(line))

    def append(self, type_, payload):
        prev = self.events[-1]['hash'] if self.events else '0' * 64
        base = {'seq': len(self.events) + 1,
                'ts': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'type': type_, 'payload': payload, 'prev_hash': prev}
        base['hash'] = hashlib.sha256(_canon(base).encode()).hexdigest()
        with self.path.open('a') as f:
            f.write(_canon(base) + '\n')
        self.events.append(base)
        return base

    def verify(self):
        prev = '0' * 64
        for i, e in enumerate(self.events, 1):
            body = {k: v for k, v in e.items() if k != 'hash'}
            if e['seq'] != i or e['prev_hash'] != prev:
                return False, f'seq/prev_hash break at {i}'
            if hashlib.sha256(_canon(body).encode()).hexdigest() != e['hash']:
                return False, f'hash mismatch at {i}'
            prev = e['hash']
        return True, f'{len(self.events)} events OK'
