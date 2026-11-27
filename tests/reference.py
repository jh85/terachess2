"""Independent destination-first rules oracle for differential testing."""
from dataclasses import dataclass
from functools import lru_cache

FILES = "abcdefghijklmnop"
SQUARES = [(x, y) for y in range(16) for x in range(16)]
PROMOTES = dict(P="Q", I="A", N="F", M="F", Z="F", E="L", W="L", J="L")


def coord(s):
    return FILES.index(s[0]), int(s[1:]) - 1


def name(sq):
    return FILES[sq[0]] + str(sq[1] + 1)


def move_name(move):
    return "-".join(map(name, move))


def fen(pieces, side="w", rights="-", ep="-", half=0, full=1):
    board = {coord(sq) if isinstance(sq, str) else sq: pc for sq, pc in pieces.items()}
    return State(board, side == "w", rights.replace("-", ""),
                 None if ep == "-" else coord(ep), half, full).fen()


def parse(text):
    board = {}
    diagram, side, rights, ep, half, full = text.split()
    for y, row in enumerate(reversed(diagram.split("/"))):
        x, i = 0, 0
        while i < len(row):
            if row[i].isdigit():
                j = i + 1
                while j < len(row) and row[j].isdigit():
                    j += 1
                x += int(row[i:j])
                i = j
            else:
                board[x, y] = row[i]
                x += 1
                i += 1
    return State(board, side == "w", rights.replace("-", ""),
                 None if ep == "-" else coord(ep), int(half), int(full))


@lru_cache(None)
def route(kind, dx, dy, f, capturing):
    """Return all required interior squares, in relative coordinates, and screen count."""
    a, b = abs(dx), abs(dy)
    high, low = max(a, b), min(a, b)
    if high == 0:
        return None
    sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
    straight, diagonal = low == 0, a == b
    knight, camel, giraffe = (high, low) == (2, 1), (high, low) == (3, 1), (high, low) == (3, 2)
    pawn = dy == f and (a == 1 if capturing else a == 0)
    # Every nonempty pattern below uses leap geometry or has an adjacent destination.
    leaps = {
        "A": knight, "D": (straight or diagonal) and high <= 3,
        "E": diagonal and high <= 2, "F": knight or camel or giraffe,
        "H": knight, "I": high == 1, "J": high == 1 or knight,
        "K": high == 1, "L": high <= 2, "M": camel, "N": knight,
        "P": pawn, "S": diagonal and high == 1, "T": pawn or (high == 3 and (straight or diagonal)),
        "W": straight and high <= 2, "X": knight, "Y": straight and high == 1, "Z": giraffe,
    }
    if leaps.get(kind):
        return (), 0
    if kind in "PI" and not capturing and (dx, dy) == (0, 2 * f):
        return ((0, f),), 0
    if ((straight and kind in "ACHOQRS") or (diagonal and kind in "ABOQVXY")):
        return tuple((n * sx, n * sy) for n in range(1, high)), int(capturing and kind in "COV")
    # Give the actual polyline for the two crooked riders.
    if kind == "G" and low == 1:
        if a == b:
            return (), 0
        if a > b:
            return tuple((n * sx, sy) for n in range(1, a)), 0
        return tuple((sx, n * sy) for n in range(1, b)), 0
    if kind == "U" and high == low + 1:
        if a > b:
            return tuple(((n + 1) * sx, n * sy) for n in range(b)), 0
        return tuple((n * sx, (n + 1) * sy) for n in range(a)), 0
    return None


def attack(board, dst, white):
    x, y = dst
    for (a, b), piece in board.items():
        if piece.isupper() != white:
            continue
        req = route(piece.upper(), x-a, y-b, 1 if white else -1, True)
        if req is not None:
            between, need = req
            if not between:
                if not need:
                    return True
            elif sum((a + dx, b + dy) in board for dx, dy in between) == need:
                return True
    return False


@dataclass
class State:
    board: dict
    white: bool
    rights: str
    ep: tuple | None
    half: int
    full: int

    def fen(self):
        rows = []
        for y in range(15, -1, -1):
            row, empty = "", 0
            for x in range(16):
                if (x, y) not in self.board:
                    empty += 1
                else:
                    row += (str(empty) if empty else "") + self.board[x, y]
                    empty = 0
            rows.append(row + (str(empty) if empty else ""))
        return " ".join(["/".join(rows), "w" if self.white else "b", self.rights or "-",
                         name(self.ep) if self.ep else "-", str(self.half), str(self.full)])

    def king(self, white):
        return next(q for q, p in self.board.items() if p == ("K" if white else "k"))

    def check(self):
        return attack(self.board, self.king(self.white), not self.white)

    def victim(self, piece, src, dst):
        if piece.upper() == "P" and dst == self.ep and src[0] != dst[0] and dst not in self.board:
            return dst[0], src[1]
        return dst

    def apply(self, move):
        src, dst = move
        board = self.board.copy()
        original = piece = board.pop(src)
        typ = piece.upper()
        victim = self.victim(piece, src, dst)
        captured = board.pop(victim, None)
        if dst[1] == (15 if self.white else 0):
            new = PROMOTES.get(typ, typ)
            if typ == "T" and abs(dst[1] - src[1]) == 1:
                new = "Q"
            piece = new if self.white else new.lower()
        board[dst] = piece
        jumped = None
        if typ in "PI" and abs(dst[1] - src[1]) == 2 and dst[0] == src[0]:
            jumped = (src[0], (src[1] + dst[1]) // 2)
        return State(board, not self.white, self.rights.replace(original, "") if typ == "K" else self.rights,
                     jumped, 0 if captured or typ == "P" else self.half + 1,
                     self.full + int(not self.white))

    def jump(self, src, dst, origin_safe):
        if not origin_safe or dst in self.board:
            return False
        dx, dy = dst[0]-src[0], dst[1]-src[1]
        if max(abs(dx), abs(dy)) != 2:
            return False
        # A transit square must be adjacent to both endpoints. For straight or equal
        # diagonal jumps, the rule restricts that set to the geometric midpoint.
        if abs(dx) in (0, 2) and abs(dy) in (0, 2):
            return not attack(self.board, (src[0] + dx//2, src[1] + dy//2), not self.white)
        return any(not attack(self.board, mid, not self.white)
                   for mid in SQUARES
                   if max(abs(mid[0]-src[0]), abs(mid[1]-src[1])) == 1
                   and max(abs(mid[0]-dst[0]), abs(mid[1]-dst[1])) == 1)

    def legal(self):
        royal = self.king(self.white)
        f = 1 if self.white else -1
        jump_available = self.board[royal] in self.rights and not self.check()
        for src, piece in self.board.items():
            if piece.isupper() != self.white:
                continue
            kind = piece.upper()
            for dst, between, need in candidate_targets(kind, src, f):
                target = self.board.get(dst)
                if target and (target.isupper() == self.white or target.upper() == "K"):
                    continue
                capture = target is not None
                ep_capture = kind == "P" and dst == self.ep and route(kind, dst[0]-src[0], dst[1]-src[1], f, True)
                if not (ep_capture or (between[capture] is not None and
                                       sum(q in self.board for q in between[capture]) == need[capture])
                        or (kind == "K" and jump_available and self.jump(src, dst, True))):
                    continue
                move = src, dst
                result = self.apply(move)
                if not attack(result.board, dst if kind == "K" else royal, not self.white):
                    yield move


@lru_cache(None)
def candidate_targets(kind, src, f):
    x, y = src
    targets = []
    for dst in SQUARES:
        dx, dy = dst[0] - x, dst[1] - y
        if not (dx or dy):
            continue
        patterns = [route(kind, dx, dy, f, capture) for capture in (False, True)]
        if not any(patterns) and (kind != "K" or max(abs(dx), abs(dy)) != 2):
            continue
        paths = [None if r is None else tuple((x + a, y + b) for a, b in r[0]) for r in patterns]
        counts = [None if r is None else r[1] for r in patterns]
        targets.append((dst, paths, counts))
    return targets


def perft(state, depth):
    if depth == 0:
        return 1
    if depth == 1:
        return sum(1 for _ in state.legal())
    return sum(perft(state.apply(move), depth - 1) for move in state.legal())
