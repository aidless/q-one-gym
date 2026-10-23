"""Reference-class and heuristic forecasters. All deterministic given the frozen task set."""
from statistics import mean

def base_rate(train, task):
    same = [t['y'] for t in train if t['type'] == task['type']]
    return mean(same) if same else 0.5

def uniform(train, task):
    return 0.5

def act_majority(train, task):
    if task['type'] != 'win_a':
        return base_rate(train, task)
    f = task['features']
    return 0.6 if f['act_a'] > f['act_b'] else 0.4

FORECASTERS = {'base_rate': base_rate, 'uniform': uniform, 'act_majority': act_majority}
