"""Train, resume, evaluate, and play with a native-search Transformer."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
from statistics import mean
import time

import torch

from native import Game, move_code, move_name, profile
from network import Inference, TeraNet, tensors

FORMAT = 1


def log(event, **data):
    print(json.dumps(dict(event=event, **data), sort_keys=True), flush=True)


def sparse_fen(pieces, side):
    ranks = []
    for y in reversed(range(16)):
        row = ""
        empty = 0
        for x in range(16):
            if (x, y) in pieces:
                if empty:
                    row += str(empty)
                row += pieces[x, y]
                empty = 0
            else:
                empty += 1
        if empty:
            row += str(empty)
        ranks.append(row)
    return "/".join(ranks) + f" {side} - - 0 1"


def curriculum(rng):
    # A rook can mate along the edge with king support. Randomizing the file, orientation,
    # rook distance, color, and piece gives sparse real rule outcomes early in training.
    x = rng.randrange(1, 15)
    offset = rng.choice([k for k in range(16) if abs(k - x) >= 2])
    pieces = {(x, 15): "k", (x, 13): "K", (offset, rng.randrange(3, 13)): rng.choice("QRS")}
    symmetry = rng.randrange(8)
    white = rng.choice([True, False])
    result = {}
    for (f, r), p in pieces.items():
        if symmetry & 1:
            f, r = r, f
        if symmetry & 2:
            f = 15 - f
        if symmetry & 4:
            r = 15 - r
        result[f, r] = p if white else p.swapcase()
    # The sparse template must satisfy the same local validator as the initial position.
    return sparse_fen(result, "w" if white else "b")


def choose(moves, visits, rng, stochastic):
    if stochastic:
        return rng.choices(moves, weights=visits, k=1)[0]
    best = max(visits)
    return rng.choice([m for m, n in zip(moves, visits) if n == best])


def self_game(task, infer, args):
    seed, use_curriculum = task
    rng = random.Random(seed)
    fen = None
    if use_curriculum:
        # A queen can incidentally attack the nonmoving king on an oblique ray.
        while True:
            fen = curriculum(rng)
            try:
                with Game(fen):
                    break
            except ValueError:
                continue
    samples, moves_played = [], []
    with Game(fen) as game:
        initial = game.fen()
        for ply in range(args.max_plies):
            if game.end() != "playing":
                break
            features = game.features()
            moves, visits, _ = game.search(args.sims, rng.getrandbits(64), True, infer)
            samples.append((features, moves, visits))
            selected = choose(moves, visits, rng, ply < args.temperature_plies)
            game.play(selected)
            moves_played.append(move_name(selected))
        end = game.end()
        if end == "playing":
            end = "truncated"
        winner = 1 - game.features()[256] if end == "checkmate" else None
        labelled = [(f, m, v, None if end == "truncated" else
                     0.0 if winner is None else 1.0 if f[256] == winner else -1.0)
                    for f, m, v in samples]
        return labelled, dict(seed=seed, curriculum=use_curriculum, start=initial,
                              moves=moves_played, end=end, winner=winner,
                              material_white=game.material())


def optimize(model, optimizer, replay, rng, args):
    model.train()
    losses = []
    for _ in range(args.steps):
        rows = rng.sample(replay, min(args.batch, len(replay)))
        features, moves, visits, outcomes = zip(*rows)
        x, m = tensors(features, moves, args.device)
        width = m.size(1)
        target = torch.tensor([v + [0] * (width - len(v)) for v in visits],
                              dtype=torch.float32, device=args.device)
        target = target / target.sum(1, keepdim=True)
        legal = torch.arange(width, device=args.device)[None] < torch.tensor(
            [len(row) for row in moves], device=args.device)[:, None]
        known = torch.tensor([v is not None for v in outcomes], device=args.device)
        value_target = torch.tensor([v if v is not None else 0 for v in outcomes],
                                    device=args.device)
        logits, value = model(x, m)
        policy_loss = -(target * logits.masked_fill(~legal, -1e9).log_softmax(1)).sum(1).mean()
        value_loss = ((value - value_target).square() * known).sum() / known.sum().clamp_min(1)
        optimizer.zero_grad(set_to_none=True)
        (policy_loss + value_loss).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()
        losses.append((policy_loss.item(), value_loss.item()))
    return [mean(values) for values in zip(*losses)]


def load(path, device):
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if checkpoint["format"] != FORMAT or checkpoint["profile"] != profile:
        raise ValueError(f"checkpoint uses format {checkpoint['format']} and profile "
                         f"{checkpoint['profile']}; expected format {FORMAT} and profile {profile}")
    model = TeraNet(**checkpoint["network"]).to(device)
    model.load_state_dict(checkpoint["weights"])
    return model, checkpoint


def save(path, model, optimizer, replay, iteration, seed):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(format=FORMAT, profile=profile, network=model.config, weights=model.state_dict(),
                    optimizer=optimizer.state_dict(), replay=replay, iteration=iteration, seed=seed),
               temporary)
    temporary.replace(path)


def train(args):
    if args.resume:
        model, checkpoint = load(args.resume, args.device)
        replay = checkpoint["replay"]
        first = checkpoint["iteration"] + 1
        seed = checkpoint["seed"]
    else:
        model = TeraNet().to(args.device)
        replay, first, seed = [], 1, args.seed
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    if args.resume:
        optimizer.load_state_dict(checkpoint["optimizer"])
        for group in optimizer.param_groups:
            group["lr"] = args.lr
    if args.games_log:
        args.games_log.parent.mkdir(parents=True, exist_ok=True)
    log("train_start", profile=profile, device=args.device, seed=seed, first_iteration=first,
        parameters=sum(p.numel() for p in model.parameters()), games=args.games, sims=args.sims,
        max_plies=args.max_plies, torch=torch.__version__)
    for iteration in range(first, first + args.iterations):
        start = time.monotonic()
        rng = random.Random(seed + 1_000_003 * iteration)
        tasks = [(rng.getrandbits(63), i < round(args.games * args.curriculum))
                 for i in range(args.games)]
        rng.shuffle(tasks)
        with Inference({"model": model}, args.device, args.workers) as inference:
            with ThreadPoolExecutor(args.workers) as pool:
                results = list(pool.map(lambda task: self_game(task, inference.evaluator("model"), args),
                                        tasks))
        records = []
        for samples, record in results:
            replay.extend(samples)
            records.append(record)
        replay = replay[-args.replay:]
        if args.games_log:
            with args.games_log.open("a") as out:
                for row in records:
                    out.write(json.dumps(dict(iteration=iteration, profile=profile, **row)) + "\n")
        policy_loss, value_loss = optimize(model, optimizer, replay, rng, args)
        save(args.output, model, optimizer, replay, iteration, seed)
        log("iteration", iteration=iteration, endings=dict(Counter(r["end"] for r in records)),
            curriculum_games=sum(r["curriculum"] for r in records),
            plies=sum(len(r["moves"]) for r in records), replay=len(replay),
            labelled_in_replay=sum(row[3] is not None for row in replay), steps=args.steps,
            policy_loss=policy_loss, value_loss=value_loss, elapsed_s=round(time.monotonic()-start, 2),
            inferred=inference.positions, inference_batches=inference.batches)


def evaluate_game(task, inference, args):
    seed, agent_side, baseline = task
    opening_rng = random.Random(seed)
    rng = random.Random(seed + 377)
    with Game() as game:
        opening = []
        for _ in range(args.opening_plies):
            if game.end() != "playing":
                break
            move = opening_rng.choice(game.legal())
            game.play(move)
            opening.append(move_name(move))
        played = []
        for ply in range(args.max_plies):
            if game.end() != "playing":
                break
            side = (len(opening) + ply) % 2
            if side == agent_side or baseline == "untrained":
                key = "trained" if side == agent_side else "untrained"
                moves, visits, _ = game.search(args.sims, rng.getrandbits(64), False,
                                              inference.evaluator(key))
                move = choose(moves, visits, rng, False)
            elif baseline == "random":
                move = rng.choice(game.legal())
            else:
                move = game.baseline(args.material_depth)
            game.play(move)
            played.append(move_name(move))
        end = game.end()
        if end == "checkmate":
            result = "loss" if game.features()[256] == agent_side else "win"
        else:
            result = "truncated" if end == "playing" else "draw"
        return dict(profile=profile, seed=seed, baseline=baseline, agent_side=agent_side, result=result,
                    end="truncated" if end == "playing" else end, opening=opening,
                    moves=played, material_agent=game.material() * (1 if agent_side == 0 else -1))


def evaluate(args):
    model, checkpoint = load(args.checkpoint, args.device)
    models = {"trained": model, "untrained": TeraNet(**model.config).to(args.device)}
    tasks = [(args.seed + p, c, base) for base in args.baselines
             for p in range(args.pairs) for c in (0, 1)]
    with Inference(models, args.device, args.workers) as inference:
        with ThreadPoolExecutor(args.workers) as pool:
            results = list(pool.map(lambda task: evaluate_game(task, inference, args), tasks))
    for base in args.baselines:
        games = [row for row in results if row["baseline"] == base]
        log("evaluation", profile=profile, baseline=base, iteration=checkpoint["iteration"], games=len(games),
            outcomes=dict(Counter(r["result"] for r in games)),
            endings=dict(Counter(r["end"] for r in games)), plies=sum(len(r["moves"]) for r in games),
            mean_final_material=mean(r["material_agent"] for r in games), seed=args.seed)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")


def play(args):
    model, _ = load(args.checkpoint, args.device)
    with Game(args.fen) as game, Inference({"trained": model}, args.device, 1) as inference:
        for move in args.moves:
            game.play(move_code(move))
        if game.end() != "playing":
            log("terminal", end=game.end(), fen=game.fen())
            return
        moves, visits, value = game.search(args.sims, args.seed, False, inference.evaluator("trained"))
        ranked = sorted(zip(moves, visits), key=lambda row: (-row[1], row[0]))
        log("move", move=move_name(ranked[0][0]), value=value,
            visits={move_name(m): n for m, n in ranked})


def positive(raw):
    val = int(raw)
    if val < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return val


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--device", default="cpu")
    common.add_argument("--threads", type=positive, default=2)
    common.add_argument("--seed", type=int, default=4102)
    common.add_argument("--sims", type=positive, default=24)
    games = argparse.ArgumentParser(add_help=False)
    games.add_argument("--workers", type=positive, default=12)
    games.add_argument("--max-plies", type=positive, default=120)
    cmd = parser.add_subparsers(required=True)
    t = cmd.add_parser("train", parents=[common, games])
    t.set_defaults(run=train)
    t.add_argument("--output", type=Path, required=True)
    t.add_argument("--resume", type=Path)
    t.add_argument("--games-log", type=Path)
    t.add_argument("--games", type=positive, default=24)
    t.add_argument("--iterations", type=positive, default=1)
    t.add_argument("--steps", type=positive, default=100)
    t.add_argument("--batch", type=positive, default=48)
    t.add_argument("--replay", type=positive, default=20000)
    t.add_argument("--temperature-plies", type=int, default=24)
    t.add_argument("--curriculum", type=float, default=0.25)
    t.add_argument("--lr", type=float, default=0.001)
    e = cmd.add_parser("evaluate", parents=[common, games])
    e.set_defaults(run=evaluate)
    e.add_argument("checkpoint", type=Path)
    e.add_argument("--pairs", type=positive, default=4)
    e.add_argument("--opening-plies", type=int, default=4)
    e.add_argument("--material-depth", type=positive, default=1)
    e.add_argument("--baselines", nargs="+", choices=("random", "material", "untrained"),
                   default=("random", "material", "untrained"))
    e.add_argument("--output", type=Path)
    p = cmd.add_parser("play", parents=[common])
    p.set_defaults(run=play)
    p.add_argument("checkpoint", type=Path)
    p.add_argument("--fen")
    p.add_argument("--moves", nargs="*", default=[])
    args = parser.parse_args()
    if args.run is train and (not 0 <= args.curriculum <= 1 or args.lr <= 0 or args.temperature_plies < 0):
        parser.error("invalid curriculum, learning rate, or temperature")
    if args.run is evaluate and args.opening_plies < 0:
        parser.error("opening plies must be nonnegative")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(args.seed)
    args.run(args)


if __name__ == "__main__":
    main()
