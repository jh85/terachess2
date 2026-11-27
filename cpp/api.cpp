#include "api.h"
#include "mcts.hpp"
#include <algorithm>
#include <stdexcept>

struct tera_game {
    tera::Game game;
};

namespace {
thread_local std::string error, fen;
template<class F, class T>
T guard(F fn, T failure) {
    try {
        error.clear();
        return fn();
    } catch (const std::exception& e) {
        error = e.what();
        return failure;
    }
}

void write_moves(const std::vector<tera::Move>& moves, int* out, int capacity) {
    if (capacity < static_cast<int>(moves.size())) throw std::invalid_argument("move buffer too small");
    std::transform(moves.begin(), moves.end(), out, [](tera::Move m) { return m.code(); });
}
}

const char* tera_profile() { return tera::profile.data(); }
const char* tera_error() { return error.c_str(); }

tera_game* tera_create(const char* input, int composition) {
    return guard([&] {
        return new tera_game{tera::Game(tera::Position::from_fen(input ? input : tera::initial, composition))};
    }, static_cast<tera_game*>(nullptr));
}

void tera_destroy(tera_game* g) { delete g; }
const char* tera_fen(tera_game* g) {
    return guard([&] { fen = g->game.pos.fen(); return fen.c_str(); }, static_cast<const char*>(nullptr));
}

int tera_features(tera_game* g, int* out) {
    auto input = tera::features(g->game);
    std::copy(input.begin(), input.end(), out);
    return 0;
}

int tera_legal(tera_game* g, int* out, int cap) {
    return guard([&] {
        auto moves = g->game.pos.legal();
        write_moves(moves, out, cap);
        return static_cast<int>(moves.size());
    }, -1);
}

int tera_play(tera_game* g, int code) {
    return guard([&] {
        auto moves = g->game.pos.legal();
        auto move = tera::Move::decode(code);
        if (g->game.end(moves) != tera::End::Playing)
            throw std::invalid_argument("game has ended");
        if (std::find(moves.begin(), moves.end(), move) == moves.end())
            throw std::invalid_argument("illegal move");
        g->game.push(move);
        return 0;
    }, -1);
}

int tera_end(tera_game* g) {
    return guard([&] { return static_cast<int>(g->game.end(g->game.pos.legal())); }, -1);
}

int tera_material(tera_game* g) { return tera::material(g->game.pos); }
int tera_best_material(tera_game* g, int depth) {
    return guard([&] { return tera::best_material(g->game, depth).code(); }, -1);
}

int tera_search(tera_game* g, int sims, uint64_t seed, int noise,
                tera_evaluator eval, void* context, int* moves, int* visits, int cap, float* value) {
    return guard([&] {
        auto result = tera::mcts(g->game, sims, seed, noise, [&](const auto& features, auto codes, auto logits) {
            float v;
            if (eval(context, features.data(), codes.data(), static_cast<int>(codes.size()), logits.data(), &v))
                throw std::runtime_error("inference callback failed");
            return v;
        });
        write_moves(result.moves, moves, cap);
        std::copy(result.visits.begin(), result.visits.end(), visits);
        *value = result.value;
        return static_cast<int>(result.moves.size());
    }, -1);
}
