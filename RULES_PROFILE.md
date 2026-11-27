# Rules verification

The adopted rules and FEN reference is [RULES.md](RULES.md).

## Lean proof scope

[Rules.lean](Rules.lean) models bounded board coordinates, explicit piece geometry and occupancy conditions, a proposition `Legal`, an exhaustive executable generator, deterministic transitions, and history-aware play. The proofs use Lean 4.19.0 and Std. The initial safety checks use kernel-checked `decide`.

- `generator_sound` and `generator_complete` identify enumeration membership with `Legal`. The generator enumerates finite source–destination pairs and checks the stated predicates. The movement table and attack geometry are the formal specification used by both.
- `step_exists_iff` and `step_unique` establish that the model returns exactly one successor for every legal coordinate move. Ordinary, en passant, and jump components are pairwise disjoint for a legal move. `ep_clears_victim` verifies removal on the victim square, and `ep_preserved` verifies that any new target has the correct empty origin and crossed square and correctly typed opposing victim.
- `initial_valid` and `valid_step` establish and preserve one King per side with correct cached coordinates, promotion-rank validity, jump-right consistency, en passant metadata, mover safety, and a positive fullmove number. `rights_monotone` and `king_consumes_right` establish that used rights stay spent. `reachable_pawn_bounds` and `no_promoted_ep_victim` establish the rank argument for promoted en passant. The formal reachability relation follows board-legal transitions, which also covers actual plays that stop at adjudication.
- `play_iff` and `play_history` tie successful game moves to legality, ongoing game status, and exact history updates. `move_count_iff` gives the 200-halfmove threshold when higher-priority endings are absent. Separate precedence theorems cover mate and stalemate.

The C++ implementation uses directional generation and a separate capture-geometry attack routine. It is checked by differential tests against the Lean executable and a Python oracle. There is no machine-checked equivalence theorem for C++ and Lean, no formal FEN codec, and no claim that the specification completely captures the author’s intent in ambiguous cases. The Lean bridge consumes a simple expanded board wire format so FEN parsing tests remain independent.
