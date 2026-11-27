"""Compare the executable Lean model with C++ on moves and selected state transitions."""
import os
from pathlib import Path
import subprocess

from reference import SQUARES, coord, fen, move_name, parse
from test_engine import INITIAL, batch, cli, random_positions, sparse_positions

ROOT = Path(__file__).resolve().parents[1]


def wire(pos):
    cells = "".join(pos.board.get(q, ".") for q in SQUARES)
    ep = "-" if not pos.ep else str(index(pos.ep))
    rights = int("K" in pos.rights) + 2 * int("k" in pos.rights)
    return f"{cells} {'w' if pos.white else 'b'} {rights} {ep} {pos.half} {pos.full}"


def index(q):
    return q[0] + 16 * q[1]


def code(move):
    return index(move[0]) * 256 + index(move[1])


def convert(text):
    return tuple(coord(sq) for sq in text.split("-"))


def main():
    curated = [
        (INITIAL, "a4-a6"),
        (fen({"h2": "K", "p16": "k", "a2": "c", "g11": "p"}, rights="K"), "h2-j3"),
        (fen({"h2": "K", "p16": "k", "i2": "E"}, rights="K"), "h2-j2"),
        (fen({"a1": "K", "p16": "k", "a9": "P", "b9": "i"}, ep="b10"), "a9-b10"),
        (fen({"a9": "K", "p16": "k", "c9": "P", "d9": "i", "h9": "r"}, ep="d10"), None),
        (fen({"a2": "K", "p11": "k", "f14": "I", "e16": "p"}), "f14-f16"),
        (fen({"a2": "K", "p11": "k", "f16": "A", "e16": "p"}, "b", ep="f15"), "e16-f15"),
        (fen({"a1": "K", "p16": "k", "f13": "T"}), "f13-f16"),
        (fen({"a1": "K", "p16": "k", "f15": "T", "g16": "r"}), "f15-g16"),
        (fen({"d14": "K", "d16": "k", "a16": "R"}, "b", half=200), None),
        (fen({"d14": "K", "d16": "k", "a8": "R"}, half=199), "a8-a16"),
    ]
    fixtures = [(parse(f), convert(m) if m else None) for f, m in curated]
    fixtures += list(random_positions())
    fixtures += [(parse(f), None) for f in sparse_positions()]
    positions = [p.fen() for p, _ in fixtures]
    legal = batch(positions)
    rolls = [wire(p) + " " + (str(code(m)) if m else "-") for p, m in fixtures]
    output = subprocess.run([os.environ.get("LEAN", "lean"), "--run", "tests/LeanCheck.lean"],
                            cwd=ROOT, text=True, input="\n".join(rolls) + "\n",
                            capture_output=True, check=False)
    if output.returncode != 0:
        raise RuntimeError(output.stdout + output.stderr)
    start, *lines = output.stdout.splitlines()
    assert start == wire(parse(INITIAL)), (start, INITIAL)
    assert len(lines) == len(legal) == len(positions), (len(lines), len(positions))
    transitions = 0
    for line, (p, m), names in zip(lines, fixtures, legal):
        mv, after = line.split("|")
        got = list(map(int, mv.split(","))) if mv else []
        assert names is not None, p.fen()
        expected = sorted(code(convert(t)) for t in names)
        assert sorted(got) == expected, (p.fen(), sorted(got), expected)
        if m:
            expected_after = cli("apply", p.fen(), move_name(m))
            assert after == wire(parse(expected_after)), (p.fen(), m, after, expected_after)
            transitions += 1
    print(f"Lean/C++ agree on {len(lines)} move lists and {transitions} transitions")


if __name__ == "__main__":
    main()
