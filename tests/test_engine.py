import json
import os
from pathlib import Path
import random
import subprocess
import unittest

from reference import SQUARES, attack, coord, fen, move_name, parse, perft

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("TERA_BIN", str(ROOT / "build/tera"))
INITIAL = (ROOT / "terachess_ii_initial.fen").read_text().strip()


def run(*args, **kw):
    return subprocess.run([BIN, *args], text=True, capture_output=True, **kw)


def cli(*args):
    result = run(*args, check=True)
    return result.stdout.strip()


def moves(fen_text, composition=False):
    flags = ["--composition"] if composition else []
    out = json.loads(cli(*flags, "moves", fen_text))
    assert len(out) == len(set(out)), "duplicate coordinate move"
    return set(out)


def batch(positions):
    result = run("batch", input="\n".join(positions) + "\n", check=True)
    return [json.loads(row) for row in result.stdout.splitlines()]


def source_opening():
    return {f"{f}4-{f}{r}" for f in "abcdefghijklmnop" for r in (5, 6)} | set(
        "a3-c5 p3-n5 e3-e5 l3-l5 c3-b5 c3-d5 n3-m5 n3-o5 b2-a5 b2-c5 o2-n5 o2-p5 "
        "c2-a5 c2-e5 n2-l5 n2-p5 d2-a5 d2-d5 d2-g5 m2-j5 m2-m5 m2-p5".split())


def random_positions():
    rng = random.Random(2042026)
    for _ in range(8):
        pos = parse(INITIAL)
        for _ in range(24):
            legal = list(pos.legal())
            if not legal:
                break
            move = rng.choice(legal)
            yield pos, move
            pos = pos.apply(move)


def sparse_positions():
    rng = random.Random(162016)
    for piece in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for white in (True, False):
            for occupancy in (0, 9, 32):
                for _ in range(500):
                    chosen = rng.sample(SQUARES, occupancy + (2 if piece == "K" else 3))
                    board = {chosen[0]: "K", chosen[1]: "k"}
                    allies, enemies = "WOPN", "cevt"
                    idx = 2
                    if piece != "K":
                        board[chosen[idx]] = piece if white else piece.lower()
                        idx += 1
                    for q in chosen[idx:]:
                        board[q] = rng.choice(allies + enemies)
                    banned = "PIMNZEWJ"
                    if any((p.isupper() and y == 15 or p.islower() and y == 0)
                           and p.upper() in banned for (_, y), p in board.items()):
                        continue
                    if not attack(board, chosen[1 if white else 0], white):
                        yield fen(board, "w" if white else "b")
                        break
                else:
                    raise AssertionError(f"no fixture for {piece}")


class EngineTests(unittest.TestCase):
    def assert_moves(self, position, yes="", no=""):
        actual = moves(position)
        self.assertTrue(set(yes.split()) <= actual, (yes, actual))
        self.assertTrue(set(no.split()).isdisjoint(actual), (no, actual))
        self.assertEqual(actual, {move_name(move) for move in parse(position).legal()})

    def test_start_source_and_perft(self):
        self.assertEqual(cli("fen"), INITIAL)
        self.assertEqual(moves(INITIAL), source_opening())
        pos = parse(INITIAL)
        self.assertEqual(perft(pos, 2), 2916)
        self.assertEqual(int(cli("perft", "0")), 1)
        self.assertEqual(int(cli("perft", "1")), 54)
        self.assertEqual(int(cli("perft", "2")), 2916)
        self.assertEqual(int(cli("perft", "3")), 175508)
        self.assertEqual(set(json.loads(cli("divide", "2"))), source_opening())
        if os.getenv("TERA_SLOW"):
            self.assertEqual(perft(pos, 3), 175508)
            self.assertEqual(int(cli("perft", "4")), 10562564)

    def test_every_piece_both_colors_and_occupancy(self):
        fixtures = list(sparse_positions())
        self.assertEqual(len(fixtures), 26 * 2 * 3)
        actual = batch(fixtures)
        self.assertEqual(len(actual), len(fixtures))
        for position, received in zip(fixtures, actual):
            with self.subTest(position=position):
                expected = {move_name(move) for move in parse(position).legal()}
                self.assertIsNotNone(received)
                self.assertEqual(set(received), expected)
                self.assertEqual(len(received), len(expected))

    def test_random_reachable_positions_and_transitions(self):
        fixtures = list(random_positions())
        actual = batch([pos.fen() for pos, _ in fixtures])
        self.assertEqual(len(actual), len(fixtures))
        for (pos, selected), received in zip(fixtures, actual):
            with self.subTest(position=pos.fen()):
                expected = {move_name(move) for move in pos.legal()}
                self.assertEqual(set(received), expected)
                self.assertEqual(len(received), len(expected))
                canonical = cli("apply", pos.fen(), move_name(selected))
                self.assertEqual(canonical, pos.apply(selected).fen())
                self.assertEqual(cli("fen", canonical), canonical)

    def test_cannon_archer_sorceress(self):
        for kind, attack_target, screen, extra, first, beyond in [
            ("C", "h8", "e8", "f8", "d8", "g8"),
            ("V", "h13", "e10", "f11", "d9", "g12"),
            ("O", "c13", "c10", "c11", "c9", "c12"),
        ]:
            for screen_piece in ("P", "p"):
                with self.subTest(kind=kind, screen=screen_piece):
                    b = {"a1": "K", "p16": "k", "c8": kind, attack_target: "n"}
                    yes = f"c8-{first}"
                    capture = f"c8-{attack_target}"
                    self.assert_moves(fen(b), yes=yes, no=capture)
                    b[screen] = screen_piece
                    self.assert_moves(fen(b), yes=yes + " " + capture,
                                      no=f"c8-{screen} c8-{beyond}")
                    after = parse(cli("apply", fen(b), capture))
                    self.assertEqual(after.board[coord(screen)], screen_piece)
                    b[extra] = "p"
                    self.assert_moves(fen(b), yes=f"c8-{extra}", no=capture)

    def test_crooked_riders_paths(self):
        for kind, bend, second, target, wrong in [
            ("G", "e5", "f5", "g5", "g6"), ("U", "e4", "f5", "g6", "g5"),
        ]:
            b = {"a1": "K", "p16": "k", "d4": kind, target: "n"}
            self.assert_moves(fen(b), yes=f"d4-{bend} d4-{target}", no=f"d4-{wrong}")
            b[second] = "p"
            self.assert_moves(fen(b), yes=f"d4-{second}", no=f"d4-{target}")
            b[bend] = "p"
            self.assert_moves(fen(b), yes=f"d4-{bend}", no=f"d4-{second} d4-{target}")
            b[bend] = "P"
            self.assert_moves(fen(b), no=f"d4-{bend} d4-{target}")

    def test_checks_screens_and_pins(self):
        self.assert_moves(fen({"h2": "K", "p16": "k", "h4": "B", "h8": "r"}), no="h4-g5")
        self.assert_moves(fen({"h2": "K", "p16": "k", "h4": "B", "h8": "c"}), yes="h4-g5")
        self.assert_moves(fen({"h2": "K", "p16": "k", "h4": "B", "h6": "B", "h8": "c"}),
                          no="h4-g5 h6-g7")
        self.assert_moves(fen({"b7": "K", "f10": "k", "f8": "r", "f1": "R"}), no="b7-b8")
        self.assertEqual(json.loads(cli("status", fen({"h2": "K", "p16": "k", "h8": "c"})))["check"],
                         False)
        self.assertEqual(json.loads(cli("status", fen({"h2": "K", "p16": "k", "h8": "c",
                                                      "h5": "B"})))["check"], True)

    def test_capture_attacks_for_each_nonroyal(self):
        # Put each type in a position with a known checking move. These calls exercise
        # attack detection directly through status, independent of move enumeration.
        offsets = {
            "A": (2, 1), "B": (4, 4), "C": (5, 0), "D": (-3, 3),
            "E": (-2, -2), "F": (3, -2), "G": (5, 1), "H": (-2, 1),
            "I": (0, -1), "J": (1, -2), "L": (-2, 1), "M": (3, -1),
            "N": (-1, 2), "O": (4, -4), "P": (1, 1), "Q": (0, -5),
            "R": (0, 5), "S": (-1, -1), "T": (1, 1), "U": (-5, 4),
            "V": (3, 3), "W": (0, 2), "X": (-2, 1), "Y": (0, -1), "Z": (-3, -2),
        }
        for piece, (dx, dy) in offsets.items():
            for white in (True, False):
                b = {(0, 0): "K", (7, 7): piece, (7 + dx, 7 + dy): "k"}
                if piece in "COV":
                    b[(8, 7 + ((dy > 0) - (dy < 0)))] = "P"
                if not white:
                    b = {(x, 15 - y): p.swapcase() for (x, y), p in b.items()}
                position = fen(b, "b" if white else "w")
                with self.subTest(piece=piece, white=white):
                    self.assertTrue(parse(position).check())
                    self.assertTrue(json.loads(cli("status", position))["check"])

    def test_jump(self):
        origin = {"h2": "K", "h15": "k"}
        sparse = fen(origin, rights="Kk")
        jumps = {f"h2-{s}" for s in "f1 f2 f3 f4 g4 h4 i4 j1 j2 j3 j4".split()}
        self.assertTrue(jumps <= moves(sparse))
        self.assert_moves(fen(origin | {"i2": "B"}, rights="Kk"), yes="h2-j2")
        self.assert_moves(fen(origin | {"j2": "p"}, rights="Kk"), no="h2-j2")
        self.assert_moves(fen(origin | {"f5": "b"}, rights="Kk"), yes="h2-j3", no="h2-j2")
        self.assert_moves(fen(origin | {"i8": "r"}, rights="Kk"), no="h2-j3")
        self.assert_moves(fen(origin | {"a2": "c"}, rights="Kk"), no="h2-j2")
        self.assert_moves(fen(origin | {"j8": "r"}, rights="Kk"), no="h2-j2")
        self.assert_moves(fen(origin | {"h8": "r"}, rights="Kk"), no="h2-f2")
        playable = fen(origin | {"a4": "P"}, rights="Kk")
        after = cli("apply", playable, "h2-j3")
        self.assertEqual(after.split()[1:], ["b", "k", "-", "1", "1"])
        self.assertEqual(cli("apply", playable, "h2-h3", "h15-h14", "h3-h2").split()[2], "-")
        off_home = fen({"h8": "K", "h15": "k"}, rights="K")
        self.assertEqual(run("moves", off_home).returncode, 2)
        self.assertIn("h8-j10", moves(off_home, composition=True))

    def test_pawn_prince_troll_and_ep(self):
        for kind in "PI":
            p = fen({"a1": "K", "p16": "k", "a9": "P", "b11": kind.lower()}, "b", half=3, full=13)
            after = cli("apply", p, "b11-b9")
            self.assertEqual(after.split()[1:], ["w", "-", "b10", "0" if kind == "P" else "4", "14"])
            self.assert_moves(after, yes="a9-b10")
            parsed = parse(cli("apply", after, "a9-b10"))
            self.assertEqual(parsed.board[coord("b10")], "P")
            self.assertNotIn(coord("b9"), parsed.board)
            self.assertIsNone(parsed.ep)
            self.assertEqual(parsed.half, 0)
            self.assertIsNone(parse(cli("apply", after, "a9-a10")).ep)
        b = {"a1": "K", "p16": "k", "d9": "p"}
        for kind in "IT":
            self.assert_moves(fen(b | {"c9": kind}, ep="d10"),
                              yes="c9-d10" if kind == "I" else "",
                              no="" if kind == "I" else "c9-d10")
            if kind == "I":
                self.assertEqual(parse(cli("apply", fen(b | {"c9": kind}, ep="d10"),
                                           "c9-d10")).board[coord("d9")], "p")
        self.assert_moves(fen({"a9": "K", "p16": "k", "c9": "P", "d9": "i", "h9": "r"},
                              ep="d10"), no="c9-d10")
        self.assert_moves(fen({"e8": "K", "p16": "k", "c9": "P", "d9": "p"},
                              ep="d10"), yes="c9-d10")
        self.assert_moves(fen({"a1": "K", "p16": "k", "e8": "P", "e9": "p"}),
                          no="e8-e9 e8-e10 e8-d9")
        self.assert_moves(fen({"a1": "K", "p16": "k", "e8": "I", "e9": "p", "d7": "r"}),
                          yes="e8-e9 e8-d7", no="e8-e10")
        self.assert_moves(fen({"a1": "K", "p16": "k", "e8": "T", "e9": "p", "f9": "p"}),
                          yes="e8-f9 e8-e11", no="e8-e9 e8-e10 e8-d9")

    def test_promotion_and_ep_of_promoted_double(self):
        for piece, src, dst, result in [
            ("P", "f15", "f16", "Q"), ("P", "f14", "f16", "Q"),
            ("I", "f14", "f16", "A"), ("I", "f15", "f16", "A"),
            ("N", "f14", "g16", "F"), ("M", "f13", "g16", "F"),
            ("Z", "f13", "h16", "F"), ("E", "f14", "h16", "L"),
            ("W", "f14", "f16", "L"), ("J", "f14", "g16", "L"),
            ("T", "f15", "f16", "Q"), ("T", "f15", "g16", "Q"), ("T", "f13", "f16", "T"),
        ]:
            for black in (False, True):
                def flip(s):
                    return s if not black else s[0] + str(17 - int(s[1:]))
                b = {"a2": "K", "p11": "k", src: piece}
                if piece == "T" and src == "f15" and dst == "g16":
                    b[dst] = "r"
                if black:
                    b = {flip(s): p.swapcase() for s, p in b.items()}
                p = fen(b, "b" if black else "w", half=7)
                m = flip(src) + "-" + flip(dst)
                after = parse(cli("apply", p, m))
                self.assertEqual(after.board[coord(flip(dst))], result.lower() if black else result)
                self.assertNotIn(coord(flip(src)), after.board)
                self.assertEqual(after.half, 0 if piece == "P" or dst in {"g16"} and piece == "T" else 8)
        for piece in "PI":
            p = fen({"a2": "K", "p11": "k", "f14": piece, "e16": "p"})
            after = cli("apply", p, "f14-f16")
            self.assertEqual(after.split()[3], "f15")
            result = parse(cli("apply", after, "e16-f15"))
            self.assertNotIn(coord("f16"), result.board)
            self.assertEqual(result.board[coord("f15")], "p")
            self.assertEqual(result.half, 0)

    def test_fen_errors_and_decimal_counters(self):
        b = {"a1": "K", "p16": "k"}
        p = fen(b)
        invalid = [
            p + " extra", "start w - - 0 1", p.replace("16/", "88/", 1),
            p.replace("16/", "08/", 1), p.replace("16/", "8 8/", 1),
            p.replace("16/", "17/", 1), p.replace("16/", "16/16/", 1),
            p.replace("16/", "", 1), p.replace("15k", "15?"),
            p.replace("15k", "15K"), p.replace("15k", "16"),
            p.replace(" w ", " x "), p.replace(" w -", " w kK"),
            p.replace(" w -", " w K"), p.replace("- -", "- a0"),
            p.replace("- -", "- a01"), p.replace("- -", "- q3"),
            p.replace("- -", "- a17"), p.replace("- -", "- b8"),
            p.replace("0 1", "-1 1"), p.replace("0 1", "0 0"), p.replace("0 1", "1x 1"),
            fen({"a1": "K", "b2": "k"}), fen(b | {"i16": "E"}), fen(b | {"p10": "R"}),
            fen(b | {"b7": "p", "b8": "n"}, ep="b8"),
            fen(b | {"b7": "p", "b9": "n"}, ep="b8"),
            fen(b | {"b7": "P"}, ep="b8"), fen(b | {"b7": "a"}, ep="b8"),
        ]
        for text in invalid:
            with self.subTest(text=text):
                result = run("moves", text)
                self.assertEqual(result.returncode, 2)
                self.assertIn("tera:", result.stderr)
        self.assertEqual(cli("fen", "  " + p.replace("0 1", "000 0001") + "  "), p)
        large = 10**50 - 1
        q = fen(b | {"h7": "n"}, "b", full=large)
        self.assertEqual(cli("apply", q, "h7-f6").split()[-1], str(large + 1))
        self.assertEqual(cli("fen", fen(b, half=large)).split()[-2], str(large))

    def test_adjudication_and_external_history(self):
        def end(p, *played):
            return json.loads(cli("status", p, *played))
        mate = fen({"d14": "K", "d16": "k", "a16": "R"}, "b", half=200)
        stale = fen({"b14": "K", "a16": "k", "c15": "Q"}, "b", half=200)
        self.assertEqual(end(mate)["end"], "checkmate")
        self.assertEqual(end(stale)["end"], "stalemate")
        b = {"a1": "K", "p16": "k"}
        self.assertEqual(end(fen(b))["end"], "bare_kings")
        material = b | {"d4": "P"}
        for half, expected in [(100, "playing"), (199, "playing"), (200, "move_count"),
                               (201, "move_count"), (10**50, "move_count")]:
            self.assertEqual(end(fen(material, half=half))["end"], expected)
        before = fen(material, half=199)
        self.assertEqual(end(before, "a1-a2")["end"], "move_count")
        self.assertEqual(end(before, "d4-d5")["end"], "playing")
        mate_next = fen({"d14": "K", "d16": "k", "a8": "R"}, half=199)
        self.assertEqual(end(mate_next, "a8-a16")["end"], "checkmate")
        p = fen(b | {"a5": "N", "p12": "n"})
        loop = ("a5-b7", "p12-o10", "b7-a5", "o10-p12")
        self.assertEqual(end(p, *loop)["repetitions"], 2)
        self.assertEqual(end(p, *(loop * 2)), {"end": "repetition", "check": False, "repetitions": 3})
        self.assertEqual(end(cli("apply", p, *(loop * 2)))["repetitions"], 1)

    def test_special_perft_divides(self):
        for p in [
            fen({"h2": "K", "p16": "k", "h5": "B", "h8": "c", "c9": "P", "d9": "i"},
                rights="K", ep="d10"),
            fen({"a1": "K", "p16": "k", "g15": "T", "e14": "W", "f13": "u", "d8": "V"}),
        ]:
            pos = parse(p)
            expected = {move_name(move): perft(pos.apply(move), 2) for move in pos.legal()}
            self.assertEqual(json.loads(cli("divide", "3", p)), expected)


if __name__ == "__main__":
    unittest.main()
