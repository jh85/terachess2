#include "engine.hpp"
#include "mcts.hpp"

#include <algorithm>
#include <cassert>
#include <numeric>
#include <random>
#include <stdexcept>

using namespace tera;

namespace {

Position make_position(std::initializer_list<std::pair<std::string_view, char>> pieces,
                       Side turn = White, std::string_view ep = {}) {
    Position p;
    p.turn = turn;
    p.ep = ep.empty() ? -1 : parse_square(ep);
    for (auto [name, pc] : pieces) p.put(parse_square(name), pc);
    return Position::from_fen(p.fen());
}

void same(const Position& a, const Position& b) {
    assert(a.fen() == b.fen());
    assert(a.board == b.board);
    assert(a.occupied == b.occupied);
    assert(a.king == b.king);
}

void roundtrip() {
    Game game(Position::from_fen(initial));
    auto original = game.pos;
    auto hist = game.history;
    std::mt19937 rng(271828);
    std::vector<std::pair<Move, Undo>> undo;
    for (int i = 0; i < 120; ++i) {
        auto before = game.pos;
        auto moves = game.pos.legal();
        same(before, game.pos);
        if (game.end(moves) != End::Playing) break;
        for (Move m : moves) {
            auto saved = game.pos.make(m);
            same(game.pos, Position::from_fen(game.pos.fen()));
            game.pos.undo(m, saved);
            same(before, game.pos);
        }
        Move m = moves[rng() % moves.size()];
        undo.emplace_back(m, game.push(m));
    }
    while (!undo.empty()) {
        auto& [m, saved] = undo.back();
        game.pop(m, saved);
        undo.pop_back();
    }
    same(original, game.pos);
    assert(hist == game.history);
    assert(game.keys.size() == 1);
}

void repetition_ep() {
    auto live = make_position({{"a9",'K'}, {"p16",'k'}, {"c9",'P'}, {"d9",'i'}}, White, "d10");
    auto absent = live;
    absent.ep = -1;
    assert(live.repetition_key() != absent.repetition_key());

    live.put(parse_square("h9"), 'r');
    absent.put(parse_square("h9"), 'r');
    assert(live.repetition_key() == absent.repetition_key()); // Pawn can reach target but is pinned.
    live.put(parse_square("c9"), 0);
    absent.put(parse_square("c9"), 0);
    assert(live.repetition_key() == absent.repetition_key()); // No adjacent Pawn.

    auto a = Position::from_fen(initial);
    auto b = a;
    b.halfmove = "12"; b.fullmove = "72";
    assert(a.repetition_key() == b.repetition_key());
    b.rights = 0;
    assert(a.repetition_key() != b.repetition_key());
}

void halfmove_limit_and_features() {
    auto p = make_position({{"d14",'K'}, {"d16",'k'}, {"a8",'R'}});
    p.halfmove = "199";
    Game game(p);
    assert(features(game)[259] == 199);
    assert(game.end(game.pos.legal()) == End::Playing);
    auto saved = game.push(parse_move("a8-a9"));
    assert(features(game)[259] == 200);
    assert(game.end(game.pos.legal()) == End::MoveCount);
    game.pop(parse_move("a8-a9"), saved);
    assert(features(game)[259] == 199);
    game.pos.halfmove = std::string(40, '9');
    assert(features(game)[259] == 200);
    assert(game.end(game.pos.legal()) == End::MoveCount);
}

void search_and_rollback() {
    auto p = make_position({{"d14",'K'}, {"d16",'k'}, {"a8",'R'}});
    Game g(p);
    auto mate = parse_move("a8-a16");
    auto evaluate = [&](const Features&, std::span<const int> moves, std::span<float> logits) {
        for (std::size_t i = 0; i < moves.size(); ++i) logits[i] = moves[i] == mate.code() ? 20 : 0;
        return 0.f;
    };
    auto result = mcts(g, 24, 987, false, evaluate);
    assert(std::accumulate(result.visits.begin(), result.visits.end(), 0) == 24);
    assert(result.moves[std::max_element(result.visits.begin(), result.visits.end()) - result.visits.begin()] == mate);
    assert(result.value == 1.f);
    assert(best_material(g, 1) == mate);
    same(g.pos, p);
    assert(g.keys.size() == 1 && g.occurrences() == 1);
    auto repeat = mcts(g, 24, 987, true, evaluate);
    assert(repeat.visits == mcts(g, 24, 987, true, evaluate).visits);
    int calls = 0;
    try {
        mcts(g, 24, 0, false, [&](const auto&, auto, auto) {
            if (++calls == 2) throw std::runtime_error("test error");
            return 0.f;
        });
        assert(false);
    } catch (const std::runtime_error&) {
        same(g.pos, p);
        assert(g.keys.size() == 1 && g.occurrences() == 1);
    }
    g.push(mate);
    assert(g.end(g.pos.legal()) == End::Checkmate);
    auto terminal = mcts(g, 3, 0, false, evaluate);
    assert(terminal.moves.empty() && terminal.value == -1.f);
}

} // namespace

int main() {
    roundtrip();
    repetition_ep();
    halfmove_limit_and_features();
    search_and_rollback();
}
