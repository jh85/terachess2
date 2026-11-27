# Initial CPU experiment

This archived run used profile `terachess-ii/default-alternate@1`, with a 100-halfmove draw threshold. Its checkpoint is tied to that profile. The current [rules reference](../RULES.md) specifies profile `@2`.

The run used PyTorch 2.15.0+cpu on an AMD Ryzen 9 9955HX with 16 physical cores. One Transformer with 108,000 parameters trained for two iterations from seed 4102. Each iteration ran 48 games with 24 MCTS simulations per move, 16 parallel games, two PyTorch CPU threads, a 144-ply cap, and 160 AdamW steps at learning rate 0.001. The batch size was 48. Each iteration began 32 games from Default-Alternate and 16 from sparse King-and-rider-versus-King positions to produce rule outcomes early.

| Iteration | Self-play plies | Checkmates | Rule draws | Truncated | Policy loss | Value loss | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5,356 | 8 | 8 | 32 | 4.4393 | 0.0384 | 31.01 s |
| 2 | 5,230 | 9 | 8 | 31 | 4.4552 | 0.0812 | 27.37 s |

There were 10,586 replay positions and 263,710 network inferences. Of the 64 full-start games, one ended in checkmate and 63 reached the ply cap. The 32 sparse games produced 16 checkmates, 13 move-count draws, and 3 bare-Kings draws. Rule outcomes supplied value labels for 1,514 replay positions. Truncations supplied policy targets. The losses are training-batch averages measured on expanding replay data.

## Paired opening evaluation

Each opponent played eight distinct four-ply random opening lines from seed 84511, with both color assignments for each line. Evaluation used 24 search simulations per move for both neural agents and a 128-ply cap after the opening. Mean material uses the engine’s piece weights and is reported from the checkpoint’s perspective.

| Opponent | Wins | Losses | Rule draws | Truncated | Mean final material |
| --- | ---: | ---: | ---: | ---: | ---: |
| Uniform random | 0 | 0 | 0 | 16 | +4.75 |
| One-ply material minimax | 0 | 1 | 1 | 14 | −94.31 |
| Untrained Transformer with MCTS | 0 | 0 | 1 | 15 | +0.81 |

The engine and training pipeline completed self-play, optimization, checkpoint resume, and evaluation. The trained checkpoint lost a completed game to the material baseline and had less final material in 15 of the 16 games against that opponent. The small material margins against random and untrained MCTS, with 45 of 48 evaluation games capped, do not establish a playing-strength improvement. The full-board value data are especially sparse, with most value labels coming from the curriculum.

## Artifacts and checks

- The local iteration-2 checkpoint (`experiments/initial.pt`) includes weights, optimizer, and replay buffer. Its SHA-256 is `6d5ec336797803772e9cc7d92fd8ca12ef718956b4dd135f70b2994200bc6a5a`.
- [Training metrics](train.jsonl), [self-play logs](selfplay.jsonl), [evaluation metrics](evaluation.jsonl), and [evaluation game logs](evaluation_games.json) record the run. All 144 game logs were replayed to check their endpoints and material.
- A [resume check](resume_check.jsonl) restored iteration 2, generated four more games, and completed four optimizer steps in iteration 3. [A play check](play_check.jsonl) used the resumed checkpoint and returned the legal Troll move `d15-d12` after `a4-a6`. The primary checkpoint remains iteration 2.

## Engine verification

The source opening list matched exactly. The independent Python oracle and C++ agreed on starting perft counts of 54, 2,916, and 175,508 at depths 1–3. C++ depth 4 produced 10,562,564 in 2.18 seconds on the same CPU. The two special-position depth-3 divides were also checked against the Python oracle. Lean and C++ agreed on 358 move lists and 200 state transitions. The native and Python engine tests passed with undefined-behavior sanitization enabled.
