"""Replay the saved games from FEN and check all recorded terminal labels."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from native import Game, move_code, profile


ARCHIVED_PROFILE = "terachess-ii/default-alternate@1"


def ending(game, rules):
    end = game.end()
    if rules == ARCHIVED_PROFILE and end == "playing" and game.features()[259] >= 100:
        return "move_count"
    return end


def replay(record, opening=()):
    # The original evaluation records predate per-game profile tags.
    rules = record.get("profile", ARCHIVED_PROFILE)
    assert rules in (profile, ARCHIVED_PROFILE), rules
    with Game(record.get("start")) as game:
        for move in [*opening, *record["moves"]]:
            assert ending(game, rules) == "playing", record
            game.play(move_code(move))
        end = ending(game, rules)
        assert end == ("playing" if record["end"] == "truncated" else record["end"]), record
        return game.features()[256], game.material()


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "experiments"
    selfplay = [json.loads(line) for line in (folder / "selfplay.jsonl").read_text().splitlines()]
    evaluation = json.loads((folder / "evaluation_games.json").read_text())
    for r in selfplay:
        side, material = replay(r)
        assert r["winner"] == (1 - side if r["end"] == "checkmate" else None), r
        assert r["material_white"] == material, r
    for r in evaluation:
        side, material = replay(r, r["opening"])
        expected = ("loss" if side == r["agent_side"] else "win") if r["end"] == "checkmate" else (
            "truncated" if r["end"] == "truncated" else "draw")
        assert r["result"] == expected, r
        assert r["material_agent"] == material * (1 if r["agent_side"] == 0 else -1), r
    print(f"Replayed {len(selfplay)} self-play games and {len(evaluation)} evaluation games")


if __name__ == "__main__":
    main()
