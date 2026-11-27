"""Systematic coverage of RULES.md through the public CLI and Python binding."""
from dataclasses import replace
import json
import random
import string
import sys
import unittest

from reference import PROMOTES, SQUARES, State, attack, coord, fen, move_name, name, parse
from test_engine import INITIAL, ROOT, batch, cli, moves, run

sys.path.insert(0, str(ROOT / "python"))
from native import Game, move_code, move_name as native_move_name


def anchored_position(source, kind, white, blockers=()):
    """Find distant Kings for a controlled geometry test without an illegal prior check."""
    allies = "K" if white else "k"
    enemy = allies.swapcase()
    piece = kind if white else kind.lower()
    occupied = dict(blockers)
    anchors = [coord(s) for s in ("a1", "p16", "a16", "p1", "d4", "m13", "d13", "m4")]
    for royal in [source] if kind == "K" else anchors:
        if royal in occupied or (kind != "K" and royal == source):
            continue
        for opposing in reversed(anchors):
            if opposing in (source, royal) or opposing in occupied:
                continue
            board = occupied | {royal: allies, opposing: enemy, source: piece}
            if not attack(board, opposing, white):
                return State(board, white, "", None, 0, 1)
    raise AssertionError((source, kind, white, blockers))


def geometry_positions():
    for kind in string.ascii_uppercase:
        for white in (True, False):
            last = 15 if white else 0
            for source in SQUARES:
                if kind in PROMOTES and source[1] == last:
                    continue
                yield anchored_position(source, kind, white)


def occupancy_positions():
    for kind in string.ascii_uppercase:
        for white in (True, False):
            for source in map(coord, ("b2", "o2", "b15", "o15", "h8", "i9")):
                x, y = source
                for arrangement in range(4):
                    blockers = []
                    for i, (dx, dy) in enumerate(((1, 1), (1, 0), (1, -1), (0, 1),
                                                  (-1, -1), (-1, 0), (-1, 1), (0, -1))):
                        step = 2 if arrangement & 2 else 1
                        target = x + dx * step, y + dy * step
                        if target not in SQUARES or (i + arrangement) % 3 == 0:
                            continue
                        own = (i + arrangement) % 2 == 0
                        blockers.append((target, "N" if own == white else "n"))
                    # Knights used as screens may not sit unpromoted on their last rank.
                    blockers = [(sq, ("F" if p.isupper() else "f")
                                 if sq[1] == (15 if p.isupper() else 0) else p)
                                for sq, p in blockers]
                    yield anchored_position(source, kind, white, blockers)


def ep_positions():
    for white in (True, False):
        forward = 1 if white else -1
        for x in range(16):
            for y in range(1, 15):
                landing = (x, y - forward)
                promoted = landing[1] == (0 if white else 15)
                for kind in "QA" if promoted else "PI":
                    victim = kind.lower() if white else kind
                    capturer = "P" if white else "p"
                    target = (x, y)
                    origin = (x, y + forward)
                    board = {landing: victim}
                    for dx in (-1, 1):
                        adjacent = (x + dx, landing[1])
                        if adjacent in SQUARES:
                            board[adjacent] = capturer
                    for k in ((0, 3), (15, 12), (0, 12), (15, 3), (8, 8)):
                        for enemy in ((15, 15), (0, 0), (15, 0), (0, 15), (7, 7)):
                            if k in board or enemy in board or k == origin or enemy == origin:
                                continue
                            if k == target or enemy == target:
                                continue
                            position = board | {k: "K" if white else "k",
                                                enemy: "k" if white else "K"}
                            if not attack(position, enemy, white):
                                yield State(position, white, "", target, 7, 13)
                                break
                        else:
                            continue
                        break
                    else:
                        raise AssertionError((white, target, kind))


class RulesMatrixTests(unittest.TestCase):
    def compare_positions(self, generated):
        positions = list(generated)
        texts = [p.fen() for p in positions]
        received = batch(texts)
        self.assertEqual(len(received), len(positions))
        for position, text, actual in zip(positions, texts, received):
            self.assertIsNotNone(actual, text)
            expected = sorted(move_name(m) for m in position.legal())
            self.assertEqual(sorted(actual), expected, text)
        return len(positions)

    def test_every_piece_on_every_permitted_square_in_both_colors(self):
        self.assertEqual(self.compare_positions(geometry_positions()), 13_056)

    def test_blockers_and_capture_targets_near_edges_and_center(self):
        self.assertEqual(self.compare_positions(occupancy_positions()), 1_248)

    def test_every_en_passant_square_and_victim_type(self):
        positions = list(ep_positions())
        self.assertEqual(self.compare_positions(positions), 896)
        captures = 0
        for p in positions:
            with Game(p.fen()) as game:
                self.assertEqual(game.fen(), p.fen())
            for m in p.legal():
                if m[1] != p.ep or p.board[m[0]].upper() != "P":
                    continue
                with Game(p.fen()) as game:
                    game.play(move_code(move_name(m)))
                    self.assertEqual(game.fen(), p.apply(m).fen(), p.fen())
                    captures += 1
        self.assertGreaterEqual(captures, 1_600)

    def test_fen_syntax_mutations_and_batch_recovery(self):
        fields = INITIAL.split()
        ranks = fields[0].split("/")
        invalid = ["", " ", "start", INITIAL + " extra"]
        invalid.extend(" ".join(fields[:i] + fields[i + 1:]) for i in range(6))
        for i in range(16):
            for row in ("", "0", "01", "016", "17", "88", "8 8", "١٦", "16@", "16.", "9" * 300):
                invalid.append(" ".join(["/".join(ranks[:i] + [row] + ranks[i + 1:]), *fields[1:]]))
            invalid.append(" ".join(["/".join(ranks[:i] + ranks[i + 1:]), *fields[1:]]))
        for field, values in {
            1: ("W", "B", "-", "ww", "white", "0"),
            2: ("kK", "KK", "kk", "K-k", "Q", "KQkq", "--", "kq"),
            3: ("a0", "a00", "a01", "p17", "q8", "A8", "a+8", "a-8", "a١", "a1", "p16"),
            4: ("-0", "-1", "+0", "0.0", "0x1", "١", "０"),
            5: ("0", "0000", "-1", "+1", "1e2", "1.0", "١"),
        }.items():
            for value in values:
                invalid.append(" ".join(fields[:field] + [value] + fields[field + 1:]))
        invalid += [INITIAL + "\0", INITIAL.replace(" w ", "\0 w "), INITIAL.replace(" w ", "\u00a0w ")]
        records = [item for i, bad in enumerate(invalid) for item in ([bad, INITIAL] if i % 9 == 0 else [bad])]
        expected_opening = sorted(moves(INITIAL))
        results = batch(records)
        self.assertEqual(len(results), len(records))
        for raw, result in zip(records, results):
            self.assertEqual(None if result is None else sorted(result),
                             expected_opening if raw == INITIAL else None, repr(raw))

    def test_fen_local_checks(self):
        invalid = []
        home = {"h2": "K", "h15": "k"}
        for piece in PROMOTES:
            for white in (True, False):
                invalid.append(fen(home | {"c16" if white else "c1": piece if white else piece.lower()}))
        for side in ("w", "b"):
            invalid.extend([
                fen({"h2": "K"}, side), fen({"h15": "k"}, side),
                fen(home | {"e8": "K"}, side), fen(home | {"e8": "k"}, side),
                fen({"h2": "K", "i3": "k"}, side),
            ])
        valid_ep = "e8"
        ep_home = {"a1": "K", "p16": "k"}
        invalid.append(fen(ep_home, ep=valid_ep))
        for piece in sorted(set(string.ascii_letters) - set("Kkpi")):
            invalid.append(fen(ep_home | {"e7": piece}, ep=valid_ep))
        for blocker in ("e8", "e9"):
            for piece in ("P", "p"):
                invalid.append(fen(ep_home | {"e7": "p", blocker: piece}, ep=valid_ep))
        self.assertEqual(batch(invalid), [None] * len(invalid))

    def test_fen_rights_and_canonical_output_on_all_entry_points(self):
        for rights in ("-", "K", "k", "Kk"):
            for white_home in (False, True):
                for black_home in (False, True):
                    board = {"h2" if white_home else "e3": "K", "h15" if black_home else "n13": "k",
                             "a5": "T", "p12": "t"}
                    text = fen(board, "w", rights, half=9, full=22)
                    valid = (white_home or "K" not in rights) and (black_home or "k" not in rights)
                    self.assertEqual(run("fen", text).returncode, 0 if valid else 2, text)
                    self.assertEqual(cli("--composition", "fen", text), text)
                    if valid:
                        with Game(text) as game:
                            self.assertEqual(game.fen(), text)
                            self.assertEqual(set(map(native_move_name, game.legal())), moves(text))
        with Game() as game:
            self.assertEqual(game.fen(), INITIAL)
        for bad in ("", INITIAL + "\0", INITIAL + "\0 extra"):
            with self.subTest(fen=repr(bad)), self.assertRaises(ValueError):
                Game(bad)
        decorated = " \t" + "\t".join(INITIAL.split()[:4] + ["000", "0001"]) + "\t "
        self.assertEqual(cli("fen", decorated), INITIAL)
        with Game(decorated) as game:
            self.assertEqual(game.fen(), INITIAL)

    def test_king_geometry_composition_and_reflection(self):
        positions = []
        for white in (True, False):
            for source in SQUARES:
                state = anchored_position(source, "K", white)
                positions.append(replace(state, rights="K" if white else "k"))
        results = run("--composition", "batch", input="\n".join(p.fen() for p in positions) + "\n", check=True)
        lines = results.stdout.splitlines()
        self.assertEqual(len(lines), 512)
        for p, line in zip(positions, lines):
            self.assertEqual(sorted(json.loads(line)), sorted(map(move_name, p.legal())), p.fen())

    def test_en_passant_changes_cannon_screens_and_pins(self):
        def reflect(text):
            x, y = coord(text)
            return name((x, 15 - y))

        for board, allowed, denied in [
            ({"a9": "K", "p16": "k", "c9": "P", "d9": "i", "h9": "c"},
             ["c9-d10"], []),
            ({"a9": "K", "p16": "k", "c9": "P", "d9": "i", "h9": "c", "e9": "P"},
             [], ["c9-d10"]),
            ({"c1": "K", "p16": "k", "c9": "P", "e9": "P", "d9": "p", "c12": "r"},
             ["e9-d10"], ["c9-d10"]),
        ]:
            for white in (True, False):
                def mirror(m):
                    return m if white else "-".join(reflect(s) for s in m.split("-"))

                pieces = board if white else {reflect(s): p.swapcase() for s, p in board.items()}
                text = fen(pieces, "w" if white else "b", ep="d10" if white else "d7", half=199)
                legal = moves(text)
                self.assertEqual(legal, set(map(move_name, parse(text).legal())))
                for m in allowed:
                    self.assertIn(mirror(m), legal)
                    self.assertEqual(parse(cli("apply", text, mirror(m))).half, 0)
                for m in denied:
                    self.assertNotIn(mirror(m), legal)
                    self.assertEqual(run("apply", text, mirror(m)).returncode, 2)

    def test_seeded_long_games_against_independent_oracle(self):
        plies = 0
        for seed in range(16):
            rng = random.Random(0x7E120026 + seed)
            p = parse(INITIAL)
            with Game() as game:
                for _ in range(100):
                    reference_moves = list(p.legal())
                    self.assertEqual(sorted(map(native_move_name, game.legal())),
                                     sorted(map(move_name, reference_moves)), p.fen())
                    if game.end() != "playing":
                        break
                    selected = rng.choice(reference_moves)
                    game.play(move_code(move_name(selected)))
                    p = p.apply(selected)
                    self.assertEqual(game.fen(), p.fen(), (seed, move_name(selected)))
                    plies += 1
        self.assertGreaterEqual(plies, 1_500)

    def test_coordinate_move_rejections(self):
        for move in ("skip", "pass", "0-0", "a4a5", "a04-a5", "A4-a5", "a4-a17", "a4-q5",
                     "a4-a4", "a4-a7", "a4-a5Q", "a4-a5-a6", "a1-a2", "a13-a12", "a8-a9"):
            result = run("apply", "start", move)
            self.assertEqual(result.returncode, 2, move)
            self.assertFalse(result.stdout, move)
