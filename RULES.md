# Terachess II rules and FEN

This is the project reference for **Terachess II, Default-Alternate with Trolls**, profile `terachess-ii/default-alternate@2`. Version 2 adopts the 200-halfmove threshold. The preset fixes the initial arrangement and piece alphabet. The designer’s Terachess II and Metamachy rules inform movement. This document defines the project’s operational rules for jump transit, promoted en passant, and adjudication. The original research records source discrepancies and retrieval details. [Game Courier preset mirror](http://ftp.chessvariants.com/play/pbm/play.php?game=Terachess+II&settings=Default-Alternate) · [Designer’s Terachess II rules](http://ftp.chessvariants.com/rules/terachess-ii) · [Designer’s Metamachy rules](http://history.chess.free.fr/metamachy.htm) · [Source research](terachess_ii_rules_and_fen.md)

## 1. Board and turns

The board has 16 files `a` through `p` from White’s left to right, and 16 ranks `1` through `16` from White’s home edge toward Black’s. A square is a lowercase file followed by its decimal rank, such as `a1`, `h2`, or `p16`. The square `a1` is dark. White moves first and advances toward higher ranks. Black advances toward lower ranks. Each turn consists of one move. There is no passing, castling, or dropping.

Orthogonal means along a rank or file. Diagonal means equal absolute file and rank displacement. A King step moves to one of the eight adjacent squares. A `(u,v)` leap includes both coordinate orders and all sign choices. Chebyshev distance is the larger of the absolute file and rank displacements. Every destination and required path square must lie on the board.

A leap ignores intervening occupancy. An ordinary slide requires every square strictly before the destination on its path to be empty. A move may land on an empty square or capture an opposing piece where its movement component permits. A friendly piece cannot be the destination. Ordinary captures remove the piece at the destination. En passant removes its victim on a separate square. Each move relocates one piece and captures at most one piece. Only the King is royal.

## 2. Pieces and movement

Uppercase FEN letters designate White pieces and lowercase letters designate Black pieces. Archer is also called Crocodile or Vao. Marshall is also spelled Marshal, and Machine is also called War Machine.

| FEN | Piece | Movement and capture pattern | Mandatory promotion |
|---|---|---|---|
| A | Amazon | Queen or Knight. | None |
| B | Bishop | Diagonal slide. | None |
| C | Cannon | Quiet orthogonal slide; orthogonal capture across exactly one screen. | None |
| D | Duchess | Orthogonal or diagonal displacement of exactly 1, 2, or 3 squares; ignores intervening occupancy. | None |
| E | Elephant | Diagonal displacement of 1 or 2 squares; the two-square move leaps. | Lion |
| F | Buffalo | Any Knight, Camel, or Giraffe leap: (2,1), (3,1), or (3,2). | None |
| G | Eagle | One diagonal step, optionally followed by an outward orthogonal slide. | None |
| H | Marshall | Rook or Knight. | None |
| I | Prince | Nonroyal King step; also a quiet, unobstructed two-square forward advance. | Amazon |
| J | Centaur | Nonroyal King step or Knight leap. | Lion |
| K | King | King step, subject to royal safety; initial jump in section 3. | None |
| L | Lion | Any nonzero displacement with `max(abs(dx), abs(dy)) ≤ 2`; ignores intervening occupancy. | None |
| M | Camel | (3,1) leap. | Buffalo |
| N | Knight | (2,1) leap. | Buffalo |
| O | Sorceress | Quiet Queen slide; capture on a Queen line across exactly one screen. | None |
| P | Pawn | Quiet forward 1 or 2; capture diagonally forward 1; en passant as specified in section 4.2. | Queen |
| Q | Queen | Orthogonal or diagonal slide. | None |
| R | Rook | Orthogonal slide. | None |
| S | Admiral | Rook or one-square diagonal step. | None |
| T | Troll | Orthogonal/diagonal leap of exactly 3; also quiet forward 1 or capture diagonally forward 1. | Queen, only after its one-step Pawn component |
| U | Rhinoceros | One orthogonal step, optionally followed by an outward diagonal slide. | None |
| V | Archer | Quiet diagonal slide; diagonal capture across exactly one screen. | None |
| W | Machine | Orthogonal displacement of 1 or 2 squares; the two-square move leaps. | Lion |
| X | Cardinal | Bishop or Knight. | None |
| Y | Missionary | Bishop or one-square orthogonal step. | None |
| Z | Giraffe | (3,2) leap. | Buffalo |

### 2.1 Cannon-family pieces

Cannon uses orthogonal rays, Archer uses diagonal rays, and Sorceress uses both. Quiet moves land on an empty destination with zero intervening pieces. Captures land on an enemy with exactly one occupied square strictly between the attacker and the destination. The intervening piece, called the screen, may be of either color and remains on its square. A capture cannot take the first piece on the ray or cross a second screen. Empty squares beyond a screen are unavailable for quiet moves.

### 2.2 Eagle

Choose a diagonal first step `(a,b)` with `a,b ∈ {−1,+1}`. The Eagle may stop at that square, including to capture. If the first square is empty, it may continue by one or more squares in either of the outward orthogonal directions `(a,0)` or `(0,b)`. The continuation is an ordinary slide and may capture the first enemy on its path. Occupancy at the bend ends or blocks the move.

### 2.3 Rhinoceros

Choose an orthogonal first step. The Rhinoceros may stop there, including to capture. If the first square is empty, it may continue with an ordinary outward diagonal slide by one or more squares. After `(a,0)`, the allowed directions are `(a,+1)` and `(a,−1)`. After `(0,b)`, the allowed directions are `(+1,b)` and `(−1,b)`. Occupancy at the bend ends or blocks the move.

### 2.4 Pawn, Prince, and Troll

- **Pawn.** Move one square straight forward into an empty square, or two squares straight forward if both crossed and destination squares are empty. The double advance is available from any rank where it fits. Capture one square diagonally forward, including by the en passant rule below.
- **Prince.** Move or capture with a King step, in any direction. It can also advance two squares straight forward through two empty squares from any rank where the move fits. The Prince is nonroyal and can be an en passant victim. Only Pawns can make en passant captures.
- **Troll.** Move or capture by leaping exactly three squares orthogonally or diagonally. It can also move one square straight forward quietly or capture one square diagonally forward. Its Pawn component has no double advance or en passant capture.

## 3. Check, legality, and the King’s initial jump

An attack is determined by an opposing piece’s capture geometry and the required path occupancy, treating the queried square as a hypothetical enemy capture target. This applies to empty squares and occupied squares alike and includes protection of a friendly piece on the queried square. A pinned piece still attacks by this definition. Pawn pushes, Prince double advances, en passant, and the King’s initial jump do not count as attacks. For Cannon-family attacks, exactly one occupied square must lie strictly between attacker and queried square. The occupancy of the queried square itself does not count as a screen.

A King is in check when the opponent attacks its square. A legal board move follows its piece’s movement, occupancy, and promotion rules and leaves the moving side’s King unattacked on the actual resulting board. Evaluate that board after all changes, including capture, en passant victim removal, and promotion. A move may give check. Capturing a King is forbidden.

On its first move the King may make a quiet jump to an empty square at Chebyshev distance exactly two. It may jump orthogonally, diagonally, or with a Knight-shaped displacement. The following conditions apply.

1. The side still has its initial jump right and its King is not currently in check.
2. For an orthogonal or diagonal jump, the unique halfway square must be unattacked.
3. For a displacement `(2a,b)`, at least one of the squares at `(a,0)` or `(a,b)` relative to the origin must be unattacked. For `(a,2b)`, at least one of `(0,b)` or `(a,b)` must be unattacked. Here `a,b ∈ {−1,+1}`. For example, `h2-j3` requires a safe `i2` or `i3`.
4. Test intermediate attacks on the board **immediately before the jump**, with the King still on its original square and all other pieces in their original positions. The capture geometry above applies, including Cannon-family screen counts on this original board. An intermediate square may be occupied.
5. Test destination safety on the **actual resulting board**, after removing the King from its origin and placing it at the destination.

Every King move consumes its side’s jump right permanently. Being in check on an earlier turn does not consume it. For example, a Black Cannon on `a2` can use the White King on `h2` as its only screen when attacking `i2`. In that case `h2-j2` fails the transit test even if removing the King from `h2` would leave `i2` unattacked.

## 4. Promotion and en passant

### 4.1 Compulsory promotion

White promotes on rank 16 and Black on rank 1. Promotion happens immediately on arrival and has the fixed result in the piece table. Any legal move by a listed piece to its promotion rank promotes it, subject to the Troll exception. A Troll promotes only on a one-square forward move or diagonal forward capture. A Troll arriving by a three-square leap remains a Troll and may later leap away. The piece’s current type is sufficient to record promotion in FEN.

### 4.2 En passant

After every legal two-square advance by a Pawn or Prince, the square it crossed is the en passant target for the opponent’s immediately following move. An opposing Pawn that could capture one square diagonally forward onto the crossed square may capture en passant. It moves to the crossed square and removes the advancing piece from its landing square. The target and victim are on the same file. The opportunity expires after that reply and is replaced only if the reply creates a new one. The capture must leave the capturing side’s King safe.

For example, after Black’s Prince goes from `b11` to `b9`, a White Pawn on `a9` may play `a9-b10`, removing the Prince from `b9`.

Promotion on a double advance leaves the en passant opportunity in force. An opposing Pawn may remove the newly promoted Queen or Amazon from its landing square under the same conditions. A valid right must arise from the preceding Pawn or Prince double advance. Other Queens and Amazons are ineligible.

This capture of a newly promoted piece is possible in valid constructed FENs. From the preset, a Black Pawn starts on rank 13 and can never reach rank 16, which it would need to occupy to capture a White double advance ending there. A White Pawn starts on rank 4 and can never reach rank 1 for the corresponding capture. A double advance can still promote and record a crossed square in a preset game.

## 5. Game endings and history

### 5.1 Checkmate and stalemate

A side to move with no legal board move is checkmated if its King is in check. The opponent wins. If its King is safe, the position is stalemate and the game is drawn. Checkmate takes precedence over automatic draws, including when the mating move advances the halfmove clock to 200.

### 5.2 Threefold repetition

The game automatically draws on the **third occurrence** of a position. No claim is required. Occurrences need not be consecutive, and the initial position counts.

For repetition, compare piece types, colors, and occupied squares, the side to move, the remaining King-jump rights, and **effective en passant**. Keep an en passant target in the repetition key only if a Pawn of the side to move can legally capture en passant in that position, including the test for its own King’s safety. Disregard the halfmove and fullmove counters for repetition comparison.

Store repetition history outside FEN. Exact adjudication after a restart requires replay from a known starting FEN or equivalent history of repetition keys. A standalone FEN loaded without history starts with one occurrence of its position.

### 5.3 200-halfmove rule

The game automatically draws when the halfmove clock reaches or exceeds **200**. It counts individual turns since the last resetting move. Reset it to zero after any capture, including en passant, or any move by a piece whose type before the move was Pawn. Increment it by one after every other move. Quiet Prince or Troll moves and quiet non-Pawn promotions increment the clock.

### 5.4 Bare Kings and precedence

A board containing only the two Kings is automatically drawn. Bare Kings is the sole dead-position test in this profile. Other positions continue until another ending rule applies, regardless of whether some of them also rule out checkmate.

For a single reported status, resolve checkmate or stalemate first, followed by bare Kings, threefold repetition, and the 200-halfmove rule. After adjudication the game has ended. Position-only move lists and perft may still describe immediate board legality. Training ply caps are recorded as truncations outside the game rules.

## 6. Default-Alternate starting position

The rows below run from file `a` through `p` for both colors. White occupies the four listed ranks. Black occupies ranks 16, 15, 14, and 13, respectively, with the corresponding lowercase letters in the same file order. Ranks 5 through 12 are empty.

| White rank | File order from a to p |
| --- | --- |
| 1 | `S J Y H X F D O O D F X H Y J S` |
| 2 | `C M Z T U V L K A L V U T Z M C` |
| 3 | `E R N B W I G Q Q G I W B N R E` |
| 4 | `P P P P P P P P P P P P P P P P` |

Each side has one King, one Amazon, sixteen Pawns, and two of each of the remaining 23 types. The Kings start on `h2` and `h15` and the Amazons on `i2` and `i15`. White moves first. Both sides have their jump right, there is no en passant target, the halfmove clock is zero, and the fullmove number is one.

## 7. FEN specification

This profile uses the six-field FEN-TSF layout with the canonical conventions below. Keep the rules profile identifier alongside FENs when recording games or datasets. [FEN-TSF source specification](https://github.com/Belzedar94/Terachess-Stockfish/blob/7031715a8f9e9cd9e7596ff53bba88135262df7e/TERACHESS_SPEC.md)

```text
<placement> <side> <king-jump-rights> <ep-square> <halfmove-clock> <fullmove-number>
```

| Field | Syntax and meaning |
| --- | --- |
| Placement | Sixteen slash-separated ranks from 16 down to 1. Each rank runs file `a` through `p` and expands to exactly 16 squares. A piece letter occupies one square. A maximal sequence of decimal digits is one empty run of length 1–16, with no leading zero. |
| Side | `w` or `b`. |
| King-jump rights | `Kk`, `K`, `k`, or `-`, for both sides, White only, Black only, or neither. |
| En passant square | The lowercase coordinate of the crossed square from the last legal Pawn or Prince double advance, or `-` otherwise. Store a literal target even if no legal en passant capture is available. |
| Halfmove clock | Nonnegative decimal integer. Use the reset and increment convention in section 5.3. |
| Fullmove number | Positive decimal integer that starts at 1 and increments after Black moves. |

For example, `16` is an entirely empty rank, `8K7` has a White King on file `i`, and `10p5` has a Black Pawn on file `k`. `88` is invalid because the maximal digit sequence represents 88. Whitespace separates fields and is forbidden inside placement. The canonical writer uses one maximal number for each empty run, a single ASCII space between fields, and decimal counters without leading zeros. The importer accepts counters with leading zeros and normalizes them. Counters support arbitrary precision.

### 7.1 En passant validation

Let `f` be the forward direction of the side to move, `+1` for White or `−1` for Black. For a target `(x,y)`, the last mover landed on `(x,y−f)` from `(x,y+f)`. Both squares must be on the board. Its origin and the crossed square must be empty. If the landing square is the opponent’s promotion rank, it must contain an opponent Queen or Amazon representing the immediate promotion of the preceding double advance. On any other rank, it must contain an opponent Pawn or Prince. The en passant target alone does not imply that a capture is currently legal.

### 7.2 Local validation and constructed positions

Require exactly one King of each color and an unattacked nonmoving King. The side to move may be in check. Enforce jump-right and en passant metadata consistency, including the board conditions above. In the default import mode a King with a retained jump right must be on its home square, `h2` for White and `h15` for Black. The engine’s explicit `--composition` mode also accepts off-home Kings with retained rights. Pieces subject to mandatory promotion must be absent in their unpromoted form from their own promotion rank, except for Trolls.

Local validation permits constructed positions, including positions with promoted en passant captures. It checks counter syntax and range without reconstructing their provenance. Reachability from the preset is a separate property and must be established by legal play. FEN parsing and local validation failures yield an error in single-position queries.

### 7.3 Canonical initial FEN

```text
sjyhxfdoodfxhyjs/cmztuvlkalvutzmc/ernbwigqqgiwbnre/pppppppppppppppp/16/16/16/16/16/16/16/16/PPPPPPPPPPPPPPPP/ERNBWIGQQGIWBNRE/CMZTUVLKALVUTZMC/SJYHXFDOODFXHYJS w Kk - 0 1
```

The same line is available as [terachess_ii_initial.fen](terachess_ii_initial.fen).

### 7.4 State represented by FEN

For immediate board legality the relevant fields are piece placement, turn, jump rights, and en passant target. Literal targets with no legal capture can produce distinct FENs with the same move options and repetition identity. The halfmove clock affects move-count adjudication. The fullmove number records game progress. Exact history-aware game state also requires repetition history. A state-space estimate should specify whether it counts serialized FENs, reachable board positions with move rights, or history-aware game states, and whether reachability stops at automatic endings.

## 8. Opening move fixture

The published preset shows 54 distinct legal board moves. The following transcription excludes its interface-only `skip` entry. [Game Courier preset mirror](http://ftp.chessvariants.com/play/pbm/play.php?game=Terachess+II&settings=Default-Alternate)

| Type | Moves |
| --- | --- |
| Pawn | For every file `x` from `a` through `p`, `x4-x5` and `x4-x6` |
| Elephant | `a3-c5`, `p3-n5` |
| Machine | `e3-e5`, `l3-l5` |
| Knight | `c3-b5`, `c3-d5`, `n3-m5`, `n3-o5` |
| Camel | `b2-a5`, `b2-c5`, `o2-n5`, `o2-p5` |
| Giraffe | `c2-a5`, `c2-e5`, `n2-l5`, `n2-p5` |
| Troll | `d2-a5`, `d2-d5`, `d2-g5`, `m2-j5`, `m2-m5`, `m2-p5` |

See the [Lean model and verification scope](RULES_PROFILE.md) for the proofs and their relationship to the C++ implementation.
