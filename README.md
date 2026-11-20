SPDX-License-Identifier: MIT

# brisk tiny chess

A chess engine in under 4 KB of Python for the tiny-chess-01 competition.

`main.py` is self-contained: a mailbox-120 board, iterative-deepening
alpha-beta with a transposition table, quiescence search over captures and
promotions plus every reply to a check, and check extension. Evaluation is
material plus piece-square tables. Every move is derived from the position
and history alone (a fixed node cap per move, no clock, no randomness), so
trials replay byte for byte.

Licensed under the MIT license.
