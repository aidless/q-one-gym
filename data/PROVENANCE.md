# data/games.csv provenance

Vendored so `make check` can rebuild `tasks/tasks_v1.json` without a second repository.

| Field | Value |
|---|---|
| File | `data/games.csv` |
| Rows | 40 episodes, plus a header (41 lines) |
| Byte sha256 | `37a08ff1151631277124fb4d786328d97f68b6090a99af5b202e95146c93567b` |
| Git blob | `60ac6f8fa1e7412e183fe75048ec96184ed526cf` |
| Task-set sha256 prefix | `add2402464df8e75` (from `tasks/build_tasks.py`, train 56, held-out 24) |
| Bytes | 4303, CRLF line endings |
| Copied from | [aidless/agent-databench `data/games.csv`](https://github.com/aidless/agent-databench/blob/e94048d5ae23fe4212d45a885ce999065ec24640/data/games.csv) at commit `e94048d5ae23fe4212d45a885ce999065ec24640` |
| Introduced | commit `17b7c2c259f4b9c453f83301302e5d3d0a180a10` (`real data: flatten 40 official CC0 episodes...`, 2026-09-21). The raw file at that commit and at the commit above are the same bytes. |

## License

`agent-databench` is MIT licensed, Copyright (c) 2026 Liu Zewen. See that repository's `LICENSE`. This copy does not change the MIT license of q-one-gym.

That repository's README and `tasks/build_games_from_episodes.py` describe the rows as a local flatten of a Kaggle episode dump, called CC0 there, with a claimed public release date of 2026-09-19. The rebuild script reads `~/下载/kagg_decode/external/eps_top10`, which is not in either repository. This gym did not re-download a Kaggle archive. The CC0 claim and the release date are inherited from that README and were not re-verified here. Do not describe this file as an independently confirmed CC0 dump.

## What the columns are

`tasks/build_games_from_episodes.py` in agent-databench sums pass and act counts over every step of the episode and takes winner and money from the last step. The pass/act columns are full-episode aggregates, not measurements taken before the winner was known. q-one-gym's task generator then keeps `seed % 1000` and those four counts as features, and builds labels from `winner` and the winner's money. See the 2026-11-16 amendment in `PREREG.md`.
