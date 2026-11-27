# Terachess II: rules and FEN specification

**Target:** the ChessVariants Game Courier preset `Terachess II / Default-Alternate`, using Trolls.  
**Document version:** 0.1, prepared 26 November 2026 (America/New_York).  
**Scope:** source research, rules documentation, initial position, and position serialization. A legal move generator, Lean proofs, and an AlphaZero agent are later work.

## 1. Status and source policy

The exact requested preset has been retrieved through ChessVariants' public HTTP mirror. Its displayed board was decoded square by square. The FEN in this document matches all 256 cells, including 64 pieces of each color. Its piece alphabet is already used by that preset and by an existing third-party Terachess II engine; a new alphabet is unnecessary. [S1, S5]

This is a source-backed implementation specification with an explicit interpretation register, not a claim that the natural-language rules have already been formally proved complete. Three categories are distinguished:

- **Published rule:** stated by the designer or the requested preset.
- **Representation convention:** a choice about how to serialize or validate those rules, without asserting that it is an official universal standard.
- **Open interpretation:** a boundary case for which the sources do not provide an unambiguous operational definition.

For the initial arrangement, the exact requested preset controls. For movement, its published explanation and the designer's ChessVariants article are the principal sources, corroborated by his own site and the Metamachy rules that he explicitly incorporates. The third-party engine establishes the existence of a FEN convention; its additional assumptions are not automatically game rules.

### 1.1 Sources

| ID | Source and role |
|---|---|
| S1 | [Requested Game Courier preset](https://www.chessvariants.com/play/pbm/play.php?game=Terachess+II&settings=Default-Alternate), retrieved at its [public mirror](http://ftp.chessvariants.com/play/pbm/play.php?game=Terachess+II&settings=Default-Alternate). Exact displayed setup, piece IDs, published rules, and initial move-list fixture. Credits Jean-Louis Cazaux. No reliable preset revision date was exposed. |
| S2 | [Terachess II rules by Jean-Louis Cazaux](https://www.chessvariants.com/rules/terachess-ii), retrieved at its [public mirror](http://ftp.chessvariants.com/rules/terachess-ii). Page identifies creation as 20 December 2020 and last update as 18 April 2023. Includes H. G. Muller's Interactive Diagram configuration. |
| S3 | [Cazaux's Terachess page](http://history.chess.free.fr/terachess.htm), section “TERACHESS II (2020)”; page footer 18 July 2024. Also contains a clearly separated Terachess I archive, which must not be mixed into II. |
| S4 | [Cazaux's Metamachy rules](http://history.chess.free.fr/metamachy.htm). Referenced by the Terachess rules for the King, Pawn, Prince, and other shared pieces. |
| S5 | [Terachess-Stockfish specification](https://github.com/Belzedar94/Terachess-Stockfish/blob/7031715a8f9e9cd9e7596ff53bba88135262df7e/TERACHESS_SPEC.md), at commit `7031715a8f9e9cd9e7596ff53bba88135262df7e`; specification identifies itself as v1.0, 18 July 2026. Defines the implementation-specific name **FEN-TSF**. This is not evidence of official standardization. |
| S6 | [Cazaux's Zanzibar rules](http://history.chess.free.fr/zanzibarxxl.html). Supporting definitions for shared pieces and the Prince's unobstructed two-square advance. |

All sources were inspected for this document. The source site’s server-side rule program has not been audited; the rendered preset, its embedded board data, and its published explanation have been inspected. A beta-version message remains in the preset, so its output is evidence to compare against, not a proof of correctness.

### 1.2 Version identity and naming

Use the external ruleset identifier `terachess-ii/default-alternate` with this document's version in future datasets and engine configurations. The FEN line alone does not identify its ruleset.

This preset uses **Troll**, not the experimental Squirrel. Terachess I's Corporal, Ship, and Gazelle are not pieces in this game. The current Archer is also called Crocodile or Vao in related sources. Marshal and Marshall denote the same piece; this document uses **Marshall** to match the ChessVariants article. Machine is also called War Machine. These aliases do not create additional types. [S1–S3]

## 2. Board, sides, and coordinates

The board has 16 files and 16 ranks. Files run `a` through `p` from White's left to right. Ranks run `1` through `16` from White's home edge toward Black's. Thus White advances toward increasing ranks; Black advances toward decreasing ranks. `a1` is dark and `p1` is light. White moves first. Each turn consists of one move. [S1–S3]

Write a square as a lowercase file letter followed by its decimal rank, for example `a1`, `h2`, or `p16`. In formulas, let a square be `(x,y)` with `x ∈ {0,…,15}` and `y ∈ {1,…,16}`. Let forward be `f = +1` for White and `f = −1` for Black. All destinations and all required path squares must be on the board; there is no wrapping.

### 2.1 Ordinary movement conventions

The following are operational restatements of the source movement rules:

- A **step** goes to the indicated adjacent square.
- A **leap** ignores intervening pieces, but cannot land on a friendly piece.
- A **slide** requires every square before the destination on its path to be empty. It may stop on an empty square or capture the first enemy piece encountered; it cannot continue through that capture.
- Unless a component is expressly restricted to quiet movement or capture, it can do either. A normal capture removes the enemy piece on the destination. Cannon-family screens are not captured.
- Except for en passant, the pieces here do not capture on a square other than their destination. No piece makes a two-capture move. There are no drops or castling moves. [S1–S4]

For the compact movement table below:

- **Orthogonal** means along a file or rank.
- **Diagonal** means along a line with equal absolute file and rank displacement.
- A **(u,v) leap** includes both coordinate orders and all sign choices. For example, a (2,1) leap has eight possible destinations on an otherwise empty, sufficiently large board.
- **King step** means a single step in any of the eight directions. For a nonroyal piece, it does not impose the King's own destination-safety restriction; the mover must still keep its actual King safe.

## 3. Piece alphabet and movement

The requested preset already uses all 26 letters. Uppercase represents White; lowercase represents Black. Keep the same alphabet for FEN. In particular, `C` is Cannon, `M` is Camel, `I` is Prince, and `W` is Machine. Symbols in this table are position labels, not Betza movement notation. [S1, S2, S5]

The table expresses the published movement facts in compact operational terms. Special rules and path details follow in Sections 4–7. [S1–S4, S6]

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
| K | King | King step, subject to royal safety; special initial jump in Section 6. | None |
| L | Lion | Any nonzero displacement with `max(abs(dx), abs(dy)) ≤ 2`; ignores intervening occupancy. | None |
| M | Camel | (3,1) leap. | Buffalo |
| N | Knight | (2,1) leap. | Buffalo |
| O | Sorceress | Quiet Queen slide; capture on a Queen line across exactly one screen. | None |
| P | Pawn | Quiet forward 1 or 2; capture diagonally forward 1; en passant as specified below. | Queen |
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

Only `K/k` is royal. Prince, Centaur, Admiral, and Missionary do not inherit the King's initial jump. A piece having a King-step component does not become a second royal.

### 3.1 Important distinctions

The Lion has 24 possible geometric destinations on an empty board away from edges, but makes just one relocation and at most one capture. It has no Chu Shogi Lion double move, return capture, or Lion-protection rule. [S2, S3]

The Duchess also has 24 geometric destinations away from edges, but they are the 1-, 2-, and 3-square orthogonal/diagonal destinations. It does not cover every square within distance three and has no Knight-shaped component. The Troll has eight three-square leap destinations plus its separate one-step Pawn components. [S1–S3]

## 4. Path-sensitive pieces

### 4.1 Cannon, Archer, and Sorceress

For a permitted ray, quiet movement requires zero occupied squares between origin and destination, and an empty destination.

For a capture, the destination must hold an enemy piece and exactly one occupied square must lie strictly between origin and destination. That intervening piece is the **screen**; either color is allowed. It remains on its square. A capture cannot take the first piece in the ray, jump two screens, or capture beyond an additional intervening piece. [S1–S3]

The permitted rays are orthogonal for Cannon, diagonal for Archer, and both for Sorceress. An empty square beyond a screen is not a quiet destination.

**Consequence for check detection:** quiet movement and attack are different relations for these pieces. A clear line to a King with no screen is not a capture attack; a line with exactly one screen can be. Always evaluate the resulting board after a move, because moving or capturing a screen can change check.

### 4.2 Eagle

From origin `s`, choose signs `a,b ∈ {−1,+1}` and let the bend square be `e = s + (a,b)`.

- The Eagle can stop on `e`, moving quietly if empty or capturing if it contains an enemy.
- If `e` is empty, it may instead continue from `e` along either `(a,0)` or `(0,b)`, for one or more squares, following ordinary slide rules.
- If `e` contains any piece, the Eagle cannot continue through it. Capturing an enemy on `e` ends the move.

Only the two **outward** directions are allowed. Thus the full offsets are `(a,b)`, `(a(1+n),b)`, and `(a,b(1+n))`, with `n ≥ 1` for the continuations, subject to the actual two-segment path being clear. [S1–S3, S4]

### 4.3 Rhinoceros

Choose an orthogonal first step. It may stop there under the same occupancy rules as the Eagle's bend square. If that square is empty, it may continue diagonally outward:

- After `(a,0)`, continue along `(a,+1)` or `(a,−1)`.
- After `(0,b)`, continue along `(+1,b)` or `(−1,b)`.

The first step and the whole following diagonal path are real, nonjumping parts of the move. Capture at the bend ends the move. [S1–S3, S6]

This is the Terachess II Rhinoceros. Do not substitute the older Terachess I movement that begins with a Knight leap. [S3]

## 5. Pawn, Prince, Troll, and en passant

### 5.1 Pawn

From `(x,y)`, a Pawn may move quietly to `(x,y+f)` if empty. It may move quietly to `(x,y+2f)` if both `(x,y+f)` and `(x,y+2f)` are empty. The double advance is available from any rank where the move fits; it is not limited to the Pawn's first move or starting rank.

Ordinary captures go to `(x−1,y+f)` or `(x+1,y+f)` when occupied by an enemy. A Pawn cannot capture straight ahead or move diagonally to an empty square except by en passant. [S1–S4]

### 5.2 Prince

The Prince's normal move is any King step, including backward or sideways captures. In addition, it has the same quiet two-square forward advance and path-clearance requirement as the Pawn. It can be captured en passant after such an advance, but cannot itself capture en passant. It is nonroyal. [S1, S2, S4, S6]

### 5.3 Troll

The Troll's long move is a leap of exactly three squares in an orthogonal or diagonal direction; it can move or capture at that destination. Separately, it can move one square straight forward quietly or capture one square diagonally forward. It has no two-square advance and no en passant capture. [S1–S3]

### 5.4 En passant

A Pawn or Prince that has just advanced two squares creates an en passant opportunity for the immediately responding opponent. An opposing Pawn whose one-step diagonal capture reaches the crossed square may move there and remove the advancing piece from its landing square. Only a Pawn can make this capture. The opportunity expires after that one reply. There is no restriction to the ranks used for en passant in orthodox chess. [S1, S2, S4]

Example: Black plays `i b11-b9`, crossing `b10`. A White Pawn on `a9` may answer `P a9-b10`, removing the Black Prince on `b9`, provided White's King is safe afterward. A White Prince or Troll on `a9` cannot use that en passant right.

Both the capturing Pawn's origin and the victim's square become empty. King safety must be checked after both changes, not only after moving the Pawn.

The unusual interaction between a double advance, promotion, and an artificial imported position is documented in Section 11.3.

## 6. The King's initial jump

There is no castling. On its first move, the King may instead jump to an empty square at **Chebyshev distance exactly two**: orthogonal distance two, diagonal distance two, or a Knight-shaped displacement. The full geometric perimeter has 16 squares before board-edge restrictions. [S1, S2, S4]

The conditions are:

1. The King has never moved.
2. It is not currently in check.
3. The destination is empty.
4. The destination is safe after the jump.
5. The required intermediate-square safety condition below holds.

The jump may cross occupied squares. This permission does not remove the threat restriction. Any King move, ordinary or special, permanently consumes the initial-jump right. Having previously been in check does not by itself consume that right; the jump is unavailable while the King is currently in check.

For displacement `(±2,0)`, `(0,±2)`, or `(±2,±2)`, the unique halfway square must be safe.

For displacement `(2a,b)` with signs `a,b ∈ {−1,+1}`, the possible intermediate squares are `s+(a,0)` and `s+(a,b)`. For displacement `(a,2b)`, they are `s+(0,b)` and `s+(a,b)`. At least one of the two must be safe. For example, `h2→j3` requires `i2` or `i3` to be safe.

From the actual starting square `h2`, the on-board geometric jump destinations are:

```text
f1 f2 f3 f4 g4 h4 i4 j1 j2 j3 j4
```

These are geometric possibilities, not legal moves in the initial occupied position.

**Open interpretation:** the prose does not fully specify which board to use for the intermediate-square attack test when occupancy changes would alter Cannon-family attacks. Section 11.2 preserves this issue rather than silently selecting the third-party engine's interpretation.

## 7. Promotion

White's promotion rank is 16; Black's is 1. Promotion happens immediately on reaching that rank, is compulsory, and has one fixed result. The published mappings are: [S1–S3]

| Before | After |
|---|---|
| Pawn `P` | Queen `Q` |
| Prince `I` | Amazon `A` |
| Knight `N`, Camel `M`, Giraffe `Z` | Buffalo `F` |
| Elephant `E`, Machine `W`, Centaur `J` | Lion `L` |
| Troll `T`, arriving by its one-step Pawn move or capture | Queen `Q` |

Use corresponding lowercase codes for Black. No other type promotes.

A Troll landing on the promotion rank by a three-square jump remains a Troll. It can later jump away; a subsequent qualifying one-step arrival promotes it. The promotion decision therefore depends on the move just made, but no persistent “previously jumped onto the back rank” flag is needed.

Examples for White, assuming path, occupancy, and King safety permit the move:

- `g15→g16` by a Troll's quiet Pawn step produces a Queen.
- `g15→h16` by its one-step capture produces a Queen.
- `g13→g16` by its three-square leap leaves a Troll.
- `e14→e16` by a Machine leap produces a Lion.
- `f14→f16` by a Prince's double advance produces an Amazon.

The resulting piece type is what goes on the board and into FEN. There is no separate promoted-piece marker because these resulting types have no further promotion rule and the sources give them no origin-dependent abilities.

## 8. Check, legality, and game ending

A normal legal move obeys its piece's movement, path, occupancy, capture, and promotion rules, and leaves its own King unattacked. For en passant, evaluate the board after removing the victim. For promotion, evaluate the board with the resulting type. King captures are not played as terminal moves: checkmate ends the game. [S1, S2]

The attack relation must use capture geometry, not simply the set of quiet destinations or the opponent's legal moves. In particular, Pawn forward advances, Prince double advances, and the King's special quiet jump are not attacks. A Cannon-family attack needs a screen. Orthodox treatment of pinned attackers should be made explicit in the formal model; it must not be implemented by recursively calling the opposing legal-move generator.

The published rules establish checkmate as a win and refer other endings to ordinary chess. Stalemate is consequently a draw. [S2, S3]

They do not provide an explicit variant-specific operational policy for repetition claims, automatic repetition draws, move-count claims, automatic move-count draws, or an implementable dead-position test. Those questions are material for self-play labels and remain in the decision register. A training maximum-ply cutoff is a training policy, not automatically a draw under the game rules.

No published rule in the inspected sources grants a pass. A literal `skip` in the preset's interface data is not being treated as a game move.

## 9. Exact initial position

There are 64 pieces per side: 16 Pawns, one King, one Amazon, and two of each of the remaining 23 types. The exact requested preset and the ChessVariants Interactive Diagram agree on this arrangement. [S1, S2]

### 9.1 White's four occupied ranks

Files within every row below run **a→p**, regardless of the side whose pieces are shown.

| White rank | Piece codes, a→p |
|---|---|
| 1 | `S J Y H X F D O O D F X H Y J S` |
| 2 | `C M Z T U V L K A L V U T Z M C` |
| 3 | `E R N B W I G Q Q G I W B N R E` |
| 4 | `P P P P P P P P P P P P P P P P` |

Black's ranks 16, 15, 14, and 13 use the corresponding lowercase rows in the **same file order**. This is reflection across the middle ranks, not a 180-degree rotation. Ranks 5 through 12 are empty.

Consequently:

- White King: `h2`; Black King: `h15`.
- White Amazon: `i2`; Black Amazon: `i15`.
- Both initial-jump rights are available; White is to move; there is no en passant opportunity.

### 9.2 Conflicting source details resolved for this target

The ChessVariants article contains a sentence placing the King on the third row. Its own inventory, jump example, Interactive Diagram, and the exact preset instead put it on the second row. This document uses `h2/h15`. [S1, S2]

There is also a genuine difference between the requested preset and the static setup artwork on the designer's personal site. Comparing the named piece icons gives:

| White squares | Requested preset / Interactive Diagram | Personal-site static artwork |
|---|---|---|
| `b1`, `o1` | Centaur | Marshall |
| `d1`, `m1` | Marshall | Cardinal |
| `e1`, `l1` | Cardinal | Centaur |

The corresponding Black back-rank pairs differ in the same way. The present FEN deliberately follows **the requested preset**. The difference is recorded rather than combined into a hybrid setup. See [the artwork](http://history.chess.free.fr/images/variantes/terachess-II.jpg) and the author's named [Centaur](http://history.chess.free.fr/images/pieces2/w-centaur.jpg), [Cardinal](http://history.chess.free.fr/images/pieces2/w-cardinal.jpg), and [Marshall movement illustration](http://history.chess.free.fr/images/moves/move-marshall.jpeg).

## 10. FEN format

### 10.1 Reuse an existing convention

The third-party engine in S5 calls its six-field format **FEN-TSF**. It uses the requested preset's existing alphabet and starting arrangement. This document adopts that layout and defines strict, interoperable serialization conventions below. It does not claim that FEN-TSF is an official standard or that all chess software supports it.

```text
<placement> <side> <king-jump-rights> <ep-square> <halfmove-clock> <fullmove-number>
```

| Field | Meaning |
|---|---|
| placement | Sixteen ranks from 16 down to 1, separated by `/`; each rank runs file a to p. |
| side | `w` or `b`, the side to move. |
| king-jump-rights | `Kk`, `K`, `k`, or `-`: White, Black, or both Kings retain their initial-jump privilege. These are **not castling rights**. |
| ep-square | A lowercase coordinate such as `b10`, or `-`; the square crossed by the immediately preceding Pawn or Prince double advance. |
| halfmove-clock | Nonnegative decimal counter, under the explicit counter convention in Section 10.5. |
| fullmove-number | Positive decimal number starting at 1; increment after Black's move. |

### 10.2 Placement grammar and canonical form

Read each maximal consecutive digit sequence as a **decimal integer**, not a sequence of one-digit FEN counts. It must be in `1…16`, with no leading zero. A letter occupies one square. Every rank must expand to exactly 16 squares, and there must be exactly 16 ranks.

Examples:

| Rank text | Meaning |
|---|---|
| `16` | Entire rank empty. |
| `8K7` | Eight empty squares, a White King, seven empty squares. |
| `10p5` | Ten empty squares, a Black Pawn, five empty squares. |
| `88` | Invalid: decimal 88 is not a valid rank run. |
| `8 8` | Invalid inside placement: whitespace separates FEN fields. |

A canonical writer emits one maximal number for each empty run and exactly one ASCII space between the six fields. Do not import the existing specification's suggestion that `8 8` can represent an empty rank; it is incompatible with this whitespace-delimited grammar. [S5, corrected representation convention]

### 10.3 Exact initial FEN

The following is a single line:

```text
sjyhxfdoodfxhyjs/cmztuvlkalvutzmc/ernbwigqqgiwbnre/pppppppppppppppp/16/16/16/16/16/16/16/16/PPPPPPPPPPPPPPPP/ERNBWIGQQGIWBNRE/CMZTUVLKALVUTZMC/SJYHXFDOODFXHYJS w Kk - 0 1
```

It is also provided separately as `terachess_ii_initial.fen`.

The placement was independently decoded from the preset's 256 board image elements and compared with its embedded position data. Validation checks rank widths, piece counts, every square, both King and Amazon locations, the empty center, and the five metadata fields. This establishes setup and serialization agreement, not general move-generator correctness. [S1; direct validation]

### 10.4 En passant representation

**Recommended writer convention for this project:** record the crossed square after every legal Pawn or Prince double advance, even when no opposing Pawn can actually capture. Clear it after every other move. This preserves a simple, literal last-double-advance record.

The existing FEN-TSF specification accepts such input but its canonical writer may omit an ineffective target. Therefore two interoperable writers can produce different strings for positions with the same legal continuations. Do not use raw FEN string equality as repetition equality. [S5; project serialization convention]

From an en passant target `(x,y)` and the side to move's forward direction `f`, the last advancing piece's landing square is `(x,y−f)` and its previous origin is `(x,y+f)`. Its color is opposite the side to move. The target and previous origin must be empty in the current position. The advancing piece was a Pawn or Prince before moving. If the double advance reached its promotion rank, the current piece is a Queen or Amazon instead. This can occur in an ordinary reachable game, and a validator for the literal-target writer must accept that metadata even though no en passant capture is possible there from the standard setup. The boundary case of an actual capture in a constructed position is described in Section 11.3.

For repetition, use an **effective en passant component**: retain the target in the repetition key only if at least one *legal* en passant capture exists, including King-safety checks. A merely adjacent Pawn that is pinned or otherwise unable to make the capture is insufficient. This is a recommended equivalence convention to finalize with the draw profile, not a claim about the preset's server implementation.

### 10.5 Counters

For compatibility with the existing FEN-TSF counter convention, reset the halfmove clock after any capture or any move of an actual Pawn (`P/p` before the move); otherwise increment it by one. Quiet Prince and Troll moves, and quiet non-Pawn promotions, do not reset it under this convention. The fullmove number increments after Black moves. [S5]

This defines what the stored number means. It does **not** silently establish an automatic 50-move or 75-move draw rule for Terachess II. If a different counter-reset or adjudication policy is selected, give the resulting rules profile a new version and document the change.

### 10.6 What FEN can and cannot encode

For ordinary immediate board-move legality, the state needed here is:

```text
board + side to move + two King-jump rights + en passant target
```

The two counters add move-count information. No separate “has Pawn moved” flag is necessary: double advances are not limited to the first move. No persistent Troll-promotion flag is necessary: the arriving move determines promotion.

**A single six-field FEN does not contain repetition history.** To resume a game with exact repetition adjudication, retain a replayable move log from a known starting state, or a suitable record of prior repetition keys, as additional game state. A position-only file also does not record resignation, agreement to draw, clocks, or which history-dependent claims were made.

An engine's future search state and training records should therefore identify the rules profile and carry whatever history and counter information the selected terminal policy requires. The board alone is not a complete state representation.

### 10.7 Input validation contract

Separate these questions instead of treating every syntactically plausible string as a legal position:

1. **Parsing:** six fields, valid symbols, 16 ranks of width 16, a valid side, valid rights syntax, an on-board en passant coordinate or `-`, and valid integer counters.
2. **Local position validation:** one King of each color; consistent rights and en passant metadata; legal royal configuration; no unpromoted piece stranded on its compulsory promotion rank, except a Troll legitimately allowed to remain there. In the fixed-start profile, a retained King-jump right requires its King to be on `h2` or `h15`. A nonmoving King in check cannot be the result of a normal legal previous move.
3. **Reachability from this start:** a separate, stronger property. Satisfying local checks does not prove that a sequence of legal moves reaches the position.

The later move-generator interface should return a clear parse/validation error for rejected input. It should not silently invent a missing King, default away unknown rights, or claim an invalid position has a normal legal-move list. Whether deliberately constructed but unreachable positions are accepted should be an explicit mode; Section 11.3 identifies a consequence of accepting them.

## 11. Interpretation and decision register

These items are concrete inputs to the later formalization. The first three steps are documented; resolving the remaining operational choices is part of fixing the exact rule model for implementation and proof.

### 11.1 Draw adjudication

**Source:** ordinary-chess endings are referenced, but no detailed protocol is given. [S2, S3]

Before training, choose and version:

- Whether repetition draws require a claim or occur automatically, and the relevant repetition counts.
- Whether move-count draws use claims, automatic termination, or both; the thresholds and reset events.
- The meaning and implementation policy for dead positions with fairy pieces. Orthodox material-only shortcuts must not be assumed valid for this game.
- Whether a maximum training length produces truncation, a separate adjudication, or a draw label.

The existing engine's automatic threefold/50-move choices are marked as assumptions in its own specification. They are one implementation's policy, not proof of the intended preset policy. [S5]

### 11.2 King-jump intermediate attacks

**Known:** crossing occupied squares is allowed; the specified intermediate square or at least one of the two intermediate squares must be safe; source and final King positions must also be safe. [S1, S2, S4]

**Not fully defined:** whether intermediate threat is evaluated on the current board, after removing the King from its origin, or after hypothetically placing it on the intermediate square. A Cannon-family attack can differ between those boards; an intermediate square may also contain a piece that the King is permitted to jump over.

The existing engine chooses current-board pseudo-attacks and labels that an assumption. Before claiming full agreement with Game Courier, obtain an explicit interpretation or inspect/test the relevant server implementation. The present research has not done that server audit. [S5]

Once chosen, define a dedicated transit-safety predicate. Ordinary final-destination safety must still use the actual resulting board.

### 11.3 Double advance that promotes, followed by en passant

Pawn and Prince double advances can reach their last rank. Promotion is immediate. The sources do not separately discuss an en passant reply against the resulting Queen or Amazon. [S1–S4]

**Reachability observation:** from the documented initial position, an en passant capture of a White double advance to rank 16 would require a Black Pawn on rank 16. Black Pawns start on rank 13, never move backward, and are never created by another promotion. The reverse case would require a White Pawn on rank 1, while White Pawns start on rank 4 and only advance. Thus the capture interaction cannot occur from the standard setup. This is a derivation from the movement and promotion rules, not an additional rule.

An actual en passant capture in this situation can occur in a deliberately constructed position that a permissive FEN importer accepts. A consistent completion, also used by the existing engine, is: promote immediately, retain the en passant target, and allow the replying Pawn to remove that newly promoted piece from the double advance's landing square. [S5]

Separately, merely recording the target after a double advance that promotes is required by this document's literal-target writer even in an ordinary reachable game. A metadata validator must therefore allow a Queen or Amazon as the last advancing piece in this final-rank case. Only the possible capture reply, not the promotion or the stored target, requires an artificial position.

Alternatively, a strict reachable-position interface can reject such constructed inputs. Choose explicitly; do not let the parser and move application disagree. The FEN fields already contain enough information for either policy; an extra persistent flag is not needed.

### 11.4 Artificial unpromoted pieces on the last rank

Except for a Troll arriving by a jump, an unpromoted promotable piece already on its promotion rank is not a normal reachable state. The recommended normal-play validator rejects it. A problem-composition mode that accepts it must specify when promotion happens; it must not depend on an unstated engine convention.

### 11.5 Source differences already resolved

| Issue | Resolution for this document |
|---|---|
| Terachess I versus II | Use II with Trolls; exclude obsolete pieces and movements. |
| Squirrel versus Troll | Use Troll, explicitly identified in the selected preset. |
| Crocodile versus Archer | One type, code `V`; Archer is the canonical name here. |
| King on second versus third row | Use `h2/h15`, as the preset and Interactive Diagram specify. |
| Personal-site artwork back-rank ordering | Use the requested preset's `SJYHXFDOODFXHYJS`. |
| “May promote” in individual preset descriptions versus compulsory-promotion section | Follow the explicit global promotion rule and fixed mapping: promotion is immediate and compulsory. |
| Machine paragraph accidentally referring to Elephant | Machine is orthogonal; its diagram and the other sources agree. |
| FEN empty-run prose allowing `8 8` | Reject internal whitespace; decimal `16` is the canonical empty rank. |
| Six-field FEN described as a complete game state | Qualify: it does not serialize repetition history or external game status. |

## 12. Initial move-list reference for the next step

The retrieved preset supplies 54 distinct board moves from this starting position. The following table transcribes those entries into coordinate notation. This is a useful first fixture for the future move generator, not a substitute for special-rule tests. [S1]

| Moving type | Initial moves | Count |
|---|---|---:|
| Pawn | For every file `x` in `a…p`: `x4→x5` and `x4→x6`. | 32 |
| Elephant | `a3→c5`, `p3→n5` | 2 |
| Machine | `e3→e5`, `l3→l5` | 2 |
| Knight | `c3→b5`, `c3→d5`, `n3→m5`, `n3→o5` | 4 |
| Camel | `b2→a5`, `b2→c5`, `o2→n5`, `o2→p5` | 4 |
| Giraffe | `c2→a5`, `c2→e5`, `n2→l5`, `n2→p5` | 4 |
| Troll | `d2→a5`, `d2→d5`, `d2→g5`, `m2→j5`, `m2→m5`, `m2→p5` | 6 |
| **Total** | All other types have no initial board move. | **54** |

The page appends the interface entry `skip`; it is not included because the published game rules do not grant passing. No deeper perft counts are certified by this document.

## 13. Handoff to implementation and Lean

The later implementation can now start from a fixed piece alphabet, exact setup, movement definitions, promotion table, and position format. Fix the open interpretations and terminal policy before declaring the rules profile final.

Useful formal obligations include:

- Parsing and printing preserve a valid position's data, up to the explicitly chosen en passant normalization.
- Move application is deterministic for every accepted state and legal move.
- The move generator is sound and complete with respect to the independently defined legal-move relation.
- Every legal transition preserves the chosen state invariants, including one royal per side and the promotion requirements.
- King-jump rights are consumed correctly and cannot be recovered by returning home.
- En passant expires at the right time and removes the correct victim.
- Troll promotion is determined by the move component, not by destination alone.
- Terminal rules and ordinary move generation have an explicit precedence, including checkmate, draw claims, and automatic draws once those are fixed.

Lean can verify these statements about the formal model. It cannot determine the designer's intended reading of an ambiguous sentence or establish that an omitted natural-language case was never intended. Agreement between the model and the selected game still requires the source comparisons and explicit decisions recorded above.

## Appendix A. Retrieval fingerprints

These fingerprints identify the exact research snapshots used, not a promise that the dynamic site will return byte-identical HTML later. [Directly computed from retrieved files]

| Snapshot | SHA-256 |
|---|---|
| Requested preset, HTTP mirror | `e3d991323d23549ddc5a872cb545c0038dca7fb6250213b06af9e84b04fc3f20` |
| ChessVariants rule article, HTTP mirror | `b4e8b3c6a7a504d851361106991651ecf967caa07e82c501512c4df43003aeb9` |
| Existing engine specification at pinned commit | `dcf29a6717aba9e20186275a870aa83c8fdfbda6fd74f6e7a204928d6807566a` |

The public-source snapshots were used for research; the delivered Markdown is an original operational restatement with source links, rather than a reproduction of the source pages.
