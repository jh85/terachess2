"""Patch Transformer with a policy conditioned on both endpoints of every legal move."""
from queue import Empty, Queue
from threading import Thread
from concurrent.futures import Future

import torch
from torch import nn


class TeraNet(nn.Module):
    def __init__(self, width=64, layers=2, heads=4, piece_dim=12, policy_dim=24):
        super().__init__()
        self.config = dict(width=width, layers=layers, heads=heads, piece_dim=piece_dim,
                           policy_dim=policy_dim)
        self.piece = nn.Embedding(53, piece_dim)
        self.patch = nn.Linear(16 * piece_dim, width)
        self.position = nn.Parameter(torch.randn(17, width) * 0.02)
        self.side = nn.Embedding(2, width)
        self.rights = nn.Embedding(4, width)
        self.ep = nn.Embedding(257, width)
        self.draw = nn.Linear(2, width)
        block = nn.TransformerEncoderLayer(width, heads, width * 2, dropout=0.0,
                                           batch_first=True, norm_first=True, activation="gelu")
        self.encoder = nn.TransformerEncoder(block, layers, norm=nn.LayerNorm(width),
                                             enable_nested_tensor=False)
        # 4x4 spatial patches. Each square gets its position in a patch and its own piece embedding.
        grid = torch.arange(256).reshape(16, 16)
        patch_order = grid.reshape(4, 4, 4, 4).transpose(1, 2).reshape(-1)
        self.register_buffer("patch_order", patch_order, persistent=False)
        self.register_buffer("square_order", patch_order.argsort(), persistent=False)
        self.local = nn.Embedding(16, piece_dim)
        self.register_buffer("local_ids", torch.arange(16).repeat(16), persistent=False)
        self.source = nn.Linear(width + 2 * piece_dim, policy_dim)
        self.target = nn.Linear(width + 2 * piece_dim, policy_dim)
        self.src_bias = nn.Linear(width + 2 * piece_dim, 1)
        self.dst_bias = nn.Linear(width + 2 * piece_dim, 1)
        self.offset = nn.Embedding(31 * 31, 1)
        nn.init.zeros_(self.offset.weight)
        self.value = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 1),
                                   nn.Tanh())

    def forward(self, inputs, moves):
        batch = inputs.size(0)
        pieces = self.piece(inputs[:, self.patch_order])
        patches = self.patch(pieces.reshape(batch, 16, -1))
        draw_features = torch.stack((inputs[:, 259] / 200, inputs[:, 260] / 100), dim=1)
        global_token = (self.side(inputs[:, 256]) + self.rights(inputs[:, 257]) +
                        self.ep(inputs[:, 258]) + self.draw(draw_features))
        tokens = self.encoder(torch.cat([global_token[:, None], patches], dim=1) + self.position)
        per_square = tokens[:, 1:].repeat_interleave(16, dim=1)
        local = self.local(self.local_ids).expand(batch, -1, -1)
        square = torch.cat([per_square, pieces, local], dim=2)[:, self.square_order]
        src, dst = moves // 256, moves % 256
        row = torch.arange(batch, device=inputs.device)[:, None]
        a, b = square[row, src], square[row, dst]
        dx = dst % 16 - src % 16
        dy = dst // 16 - src // 16
        logits = ((self.source(a) * self.target(b)).sum(-1) / self.config["policy_dim"] ** 0.5 +
                  self.src_bias(a).squeeze(-1) + self.dst_bias(b).squeeze(-1) +
                  self.offset((dy + 15) * 31 + dx + 15).squeeze(-1))
        return logits, self.value(tokens[:, 0]).squeeze(-1)


def tensors(features, moves, device):
    width = max(map(len, moves))
    return (torch.tensor(features, device=device),
            torch.tensor([m + [0] * (width - len(m)) for m in moves], device=device))


class Inference:
    """Batch synchronous native callbacks across independent game threads."""
    def __init__(self, models, device, batch):
        self.models = {key: model.eval() for key, model in models.items()}
        self.device = device
        self.batch = batch
        self.queue = Queue()
        self.worker = Thread(target=self.run)
        self.positions = 0
        self.batches = 0

    def __enter__(self):
        self.worker.start()
        return self

    def __exit__(self, *_):
        self.queue.put(None)
        self.worker.join()

    def evaluator(self, key):
        def evaluate(features, moves):
            result = Future()
            self.queue.put((key, features, moves, result))
            return result.result()
        return evaluate

    @torch.inference_mode()
    def run(self):
        while (item := self.queue.get()) is not None:
            requests = [item]
            while len(requests) < self.batch:
                try:
                    requests.append(self.queue.get(timeout=0.0005))
                except Empty:
                    break
            for key in dict.fromkeys(row[0] for row in requests):
                group = [row for row in requests if row[0] == key]
                _, features, moves, futures = zip(*group)
                try:
                    x, m = tensors(features, moves, self.device)
                    logits, values = self.models[key](x, m)
                    self.positions += len(group)
                    self.batches += 1
                    for scores, value, codes, result in zip(logits.tolist(), values.tolist(),
                                                            moves, futures):
                        result.set_result((scores[:len(codes)], value))
                except Exception as exc:
                    for result in futures:
                        if not result.done():
                            result.set_exception(exc)
