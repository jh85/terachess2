# Terachess II playing agent

C++20 engine, executable Lean 4 rules, and a PyTorch Transformer with native Monte Carlo tree search for **Default-Alternate with Trolls**. The profile is `terachess-ii/default-alternate@2`. See the [rules and FEN reference](RULES.md), [proof scope](RULES_PROFILE.md), and [experiment report](experiments/REPORT.md).

## Build and verify

Use a C++20 compiler, GNU Make, and Python 3.10 or newer. The shared-library build targets Linux. Install Lean with the version in [lean-toolchain](lean-toolchain) or pass its executable as `LEAN=/path/to/lean`.

```sh
make -j
make test
TERA_SLOW=1 make test       # Also run the independent depth-3 oracle and C++ depth 4
make lean                   # Kernel-check the rules and proofs
make lean-test              # Compare executable Lean, C++, and the supplied opening FEN
python3 tests/check_experiment.py
```

## Generate moves and replay a game

```sh
build/tera moves "$(cat terachess_ii_initial.fen)"
build/tera apply start a4-a6 b13-b11
build/tera status start a4-a6 b13-b11
build/tera perft 4 start
build/tera divide 3 start
build/tera material 1 start
```

`moves` prints a JSON array of coordinate strings such as `"a4-a6"`. A source and destination uniquely identify a move in a given position, including en passant and compulsory promotion. `apply` and `fen` print canonical FEN. `status` prints JSON with the ending, check flag, and current repetition count. `divide` prints the perft subtree count for every legal root move. `batch` reads one FEN per line and prints one JSON array or `null` per line. Single-input commands return exit code 2 and a diagnostic on invalid input.

Give the game’s starting FEN followed by its move log to reconstruct repetition history. A lone FEN starts with one occurrence of that position. The engine keeps exact repetition keys and retains an en passant target in the key only when an en passant capture is legal. Position queries such as `moves` and `perft` use immediate board legality. `apply`, baseline search, and MCTS enforce full game adjudication with history.

The native integration surface is [cpp/api.h](cpp/api.h), with a Python binding in [python/native.py](python/native.py). The C ABI policy code is `256 * source + destination`, with `a1 = 0`, `b1 = 1`, `a2 = 16`, and `p16 = 255`. The inference callback receives 256 piece IDs in that order (empty 0, White A–Z 1–26, Black a–z 27–52) followed by turn, jump-right bitmask, en passant index plus one, halfmove clock capped at 200, and the current repetition count capped at 3. The neural input summarizes repetition with that count, while native search uses the complete history. It returns one logit per supplied legal move and a value from the side-to-move perspective.

## Train, resume, and play

Use Python 3.12 or newer for the pinned training environment. Install the CPU dependencies in a virtual environment. Use the Python executable from that environment for the commands below.

```sh
python3 -m venv .venv
.venv/bin/pip install -r python/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu 'torch==2.15.0+cpu'
```

```sh
.venv/bin/python python/agent.py train \
  --output runs/model.pt --games-log runs/selfplay.jsonl \
  --games 48 --workers 16 --threads 2 --max-plies 144 \
  --sims 24 --steps 160 --batch 48 --curriculum .333333 --iterations 2

.venv/bin/python python/agent.py train \
  --resume runs/model.pt --output runs/model.pt \
  --games-log runs/selfplay.jsonl --iterations 1

.venv/bin/python python/agent.py evaluate runs/model.pt \
  --seed 84511 --pairs 8 --opening-plies 4 --workers 16 --threads 2 \
  --max-plies 128 --sims 24 --material-depth 1 --output runs/evaluation.json

.venv/bin/python python/agent.py play runs/model.pt \
  --sims 64 --moves a4-a6 b13-b11
```

`play` defaults to the preset start and accepts `--fen "$FEN"` as a replay origin. It emits the selected move, root value, and visit counts as JSON. `evaluate` plays paired opening lines, switching the checkpoint’s side for the second game of each pair. Opponents are uniform random, native material minimax, and an independently initialized Transformer with the same MCTS budget. Use `--baselines` to select opponents. `--device cuda` is available with a matching PyTorch build.

The 108,000-parameter network uses sixteen spatial patch tokens, a game-state token, and two self-attention layers. A policy head scores legal source–destination pairs, and the value head predicts the outcome for the player to move. C++ performs PUCT selection, expansion, and sign-correct backup. Python batches leaf evaluation across games. Self-play uses root Dirichlet noise and samples from visits in the first 24 plies by default. Training uses normalized visits for policy and rule outcomes for value. Capped games contribute policy targets only. Resuming restores the optimizer, replay buffer, iteration, and self-play seed. The current command’s training settings apply to each added iteration.

The archived [initial experiment](experiments/REPORT.md) used profile `@1` with a 100-halfmove threshold. Its checkpoint and results retain that profile tag. The agent requires a checkpoint from the active profile for resume, evaluation, or play.
