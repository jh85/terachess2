#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace tera {

inline constexpr std::string_view profile = "terachess-ii/default-alternate@2";
inline constexpr int halfmove_limit = 200;
inline constexpr std::string_view initial =
    "sjyhxfdoodfxhyjs/cmztuvlkalvutzmc/ernbwigqqgiwbnre/pppppppppppppppp/"
    "16/16/16/16/16/16/16/16/PPPPPPPPPPPPPPPP/ERNBWIGQQGIWBNRE/"
    "CMZTUVLKALVUTZMC/SJYHXFDOODFXHYJS w Kk - 0 1";

enum Side { White, Black };
inline Side other(Side side) { return side == White ? Black : White; }

struct Move {
    int from, to;
    bool operator==(const Move&) const = default;
    int code() const { return from * 256 + to; }
    static Move decode(int code) { return {code / 256, code % 256}; }
};

std::string square_name(int sq);
int parse_square(std::string_view s);
std::string move_name(Move move);
Move parse_move(std::string_view name);

struct Undo {
    char moved, taken;
    int capture_square, rights, ep;
    std::string halfmove, fullmove;
};

struct Position {
    std::array<char, 256> board{};
    std::array<std::array<std::uint64_t, 4>, 2> occupied{};
    std::array<int, 2> king{-1, -1};
    Side turn = White;
    int rights = 0, ep = -1;
    std::string halfmove = "0", fullmove = "1";

    static Position from_fen(std::string_view fen, bool composition = false);
    std::string fen() const;
    int capped_halfmove() const;
    void put(int square, char piece);
    bool attacked(int square, Side by) const;
    bool check() const { return attacked(king[turn], other(turn)); }
    std::vector<Move> legal();
    Undo make(Move move, bool counters = true);
    void undo(Move move, const Undo& state, bool counters = true);
    std::string repetition_key();
};

enum class End { Playing, Checkmate, Stalemate, Repetition, MoveCount, BareKings };
const char* end_name(End end);

struct Game {
    explicit Game(Position position);
    Position pos;
    std::unordered_map<std::string, int> history;
    std::vector<std::string> keys;

    int occurrences() const { return history.at(keys.back()); }
    Undo push(Move move);
    void pop(Move move, const Undo& undo);
    End end(const std::vector<Move>& moves) const;
};

std::uint64_t perft(Position& pos, int depth);
int material(const Position& pos);
Move best_material(Game& game, int depth);

} // namespace tera
