SPDX-License-Identifier: MIT

# brisk tiny chess

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/Fanc1er/tiny-brisk-01/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/Fanc1er/tiny-brisk-01/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

A chess engine in under 4 KB of Python for [make.fun](https://make.fun/bounty/tiny-chess-01)'s "Build the strongest chess engine in 4 KB of Python" bounty.

`main.py` is self-contained: a mailbox-120 board, iterative-deepening
alpha-beta with a transposition table, quiescence search over captures and
promotions plus every reply to a check, and check extension. Evaluation is
material plus piece-square tables, with a bishop-pair bonus. The search adds
null-move pruning and killer-move ordering; every move is derived from the
position and history alone (a fixed node cap per move, no clock, no
randomness), so trials replay byte for byte.

Licensed under the MIT license.
