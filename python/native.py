"""Synchronous C ABI binding. Each Game owns its native repetition history."""
import ctypes as C
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lib = C.CDLL(os.environ.get("TERA_LIB", ROOT / "build/libtera.so"))
IP = C.POINTER(C.c_int)
FP = C.POINTER(C.c_float)
CALLBACK = C.CFUNCTYPE(C.c_int, C.c_void_p, IP, IP, C.c_int, FP, FP)


def bind(name, result, *args):
    func = getattr(lib, f"tera_{name}")
    func.argtypes = args
    func.restype = result
    return func


profile = bind("profile", C.c_char_p)().decode()
error = bind("error", C.c_char_p)
create = bind("create", C.c_void_p, C.c_char_p, C.c_int)
destroy = bind("destroy", None, C.c_void_p)
fen_of = bind("fen", C.c_char_p, C.c_void_p)
features_of = bind("features", C.c_int, C.c_void_p, IP)
legal = bind("legal", C.c_int, C.c_void_p, IP, C.c_int)
play = bind("play", C.c_int, C.c_void_p, C.c_int)
end = bind("end", C.c_int, C.c_void_p)
material = bind("material", C.c_int, C.c_void_p)
best_material = bind("best_material", C.c_int, C.c_void_p, C.c_int)
search = bind("search", C.c_int, C.c_void_p, C.c_int, C.c_uint64, C.c_int,
              CALLBACK, C.c_void_p, IP, IP, C.c_int, FP)

FEATURES = 261
CAPACITY = 65536
STATUS = ("playing", "checkmate", "stalemate", "repetition", "move_count", "bare_kings")


def check(result):
    if result is None or result == -1:
        raise ValueError(error().decode())
    return result


def move_name(code):
    def square(n):
        return f"{chr(ord('a') + n % 16)}{n // 16 + 1}"
    return f"{square(code // 256)}-{square(code % 256)}"


def move_code(text):
    def square(s):
        return ord(s[0]) - ord("a") + 16 * (int(s[1:]) - 1)
    a, b = text.split("-")
    code = square(a) * 256 + square(b)
    if not 0 <= code < CAPACITY or move_name(code) != text:
        raise ValueError(f"invalid move: {text}")
    return code


class Game:
    def __init__(self, fen=None):
        if fen is not None and "\0" in fen:
            raise ValueError("FEN cannot contain a NUL character")
        self.handle = check(create(fen.encode() if fen is not None else None, 0))
        self.moves = (C.c_int * CAPACITY)()
        self.visits = (C.c_int * CAPACITY)()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        destroy(self.handle)
        self.handle = None

    def fen(self):
        return check(fen_of(self.handle)).decode()

    def features(self):
        out = (C.c_int * FEATURES)()
        check(features_of(self.handle, out))
        return out[:]

    def legal(self):
        count = check(legal(self.handle, self.moves, CAPACITY))
        return self.moves[:count]

    def play(self, code):
        check(play(self.handle, code))

    def end(self):
        return STATUS[check(end(self.handle))]

    def material(self):
        return material(self.handle)

    def baseline(self, depth):
        return check(best_material(self.handle, depth))

    def search(self, sims, seed, noise, evaluate):
        failure = None

        @CALLBACK
        def callback(_, features, codes, count, logits, value):
            nonlocal failure
            try:
                scores, v = evaluate(features[:FEATURES], codes[:count])
                if len(scores) != count:
                    raise ValueError("inference returned the wrong number of policy logits")
                C.cast(logits, C.POINTER(C.c_float * count)).contents[:] = scores
                value[0] = v
                return 0
            except Exception as exc:
                failure = exc
                return -1

        value = C.c_float()
        count = search(self.handle, sims, seed, noise, callback, None, self.moves,
                       self.visits, CAPACITY, C.byref(value))
        if failure is not None:
            raise failure
        check(count)
        return self.moves[:count], self.visits[:count], value.value
