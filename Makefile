.PHONY: check

# Offline from a fresh clone after `python3 -m pip install pytest`.
# Rebuilds tasks from data/games.csv, rescores, and fails on README drift.
check:
	python3 check.py
