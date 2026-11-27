#include "mcts.hpp"

#include <algorithm>
#include <cmath>
#include <memory>
#include <numeric>
#include <random>
#include <stdexcept>

namespace tera {

Features features(const Game& g) {
    Features out{};
    for (int i = 0; i < 256; ++i) {
        char c = g.pos.board[i];
        out[i] = !c ? 0 : c >= 'a' ? c - 'a' + 27 : c - 'A' + 1;
    }
    out[256] = g.pos.turn;
    out[257] = g.pos.rights;
    out[258] = g.pos.ep + 1;
    out[259] = g.pos.capped_halfmove();
    out[260] = std::min(g.occurrences(), 3);
    return out;
}

namespace {

struct Node;
struct Edge {
    Move move;
    float prior;
    int visits = 0;
    float total = 0;
    std::unique_ptr<Node> child;
};
struct Node {
    bool expanded = false;
    float value = 0;
    int visits = 0;
    std::vector<Edge> edges;
};

void expand(Node& node, Game& game, const Evaluate& evaluate) {
    auto moves = game.pos.legal();
    auto status = game.end(moves);
    node.expanded = true;
    if (status != End::Playing) {
        node.value = status == End::Checkmate ? -1 : 0;
        return;
    }
    std::vector<int> codes;
    codes.reserve(moves.size());
    for (Move m : moves) codes.push_back(m.code());
    std::vector<float> logits(moves.size());
    node.value = evaluate(features(game), codes, logits);
    if (!std::isfinite(node.value) ||
        !std::all_of(logits.begin(), logits.end(), [](float x) { return std::isfinite(x); }))
        throw std::runtime_error("evaluator returned a nonfinite value");
    node.value = std::clamp(node.value, -1.0f, 1.0f);
    float top = *std::max_element(logits.begin(), logits.end());
    for (auto& x : logits) x = std::exp(x - top);
    float sum = std::accumulate(logits.begin(), logits.end(), 0.0f);
    node.edges.reserve(moves.size());
    for (std::size_t i = 0; i < moves.size(); ++i)
        node.edges.push_back({moves[i], logits[i] / sum, 0, 0, nullptr});
}

Edge& select(Node& node) {
    float scale = 1.5f * std::sqrt(static_cast<float>(node.visits + 1));
    auto score = [scale](const Edge& e) {
        float mean = e.visits ? e.total / e.visits : 0.0f;
        return mean + scale * e.prior / (1 + e.visits);
    };
    return *std::max_element(node.edges.begin(), node.edges.end(),
                             [&](const Edge& a, const Edge& b) { return score(a) < score(b); });
}

void add_noise(Node& node, std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::gamma_distribution<float> gamma(std::clamp(10.0f / node.edges.size(), 0.03f, 0.3f));
    std::vector<float> samples(node.edges.size());
    for (auto& sample : samples) sample = gamma(rng);
    float sum = std::accumulate(samples.begin(), samples.end(), 0.0f);
    if (sum <= 0) return;
    for (std::size_t i = 0; i < samples.size(); ++i)
        node.edges[i].prior = 0.75f * node.edges[i].prior + 0.25f * samples[i] / sum;
}

} // namespace

SearchResult mcts(Game& game, int simulations, std::uint64_t seed, bool noise, const Evaluate& evaluate) {
    if (simulations < 1) throw std::invalid_argument("MCTS requires at least one simulation");
    Node root;
    expand(root, game, evaluate);
    if (root.edges.empty()) return {{}, {}, root.value};
    if (noise) add_noise(root, seed);
    struct Step { Edge* edge; Node* parent; Undo saved; };
    std::vector<Step> path;
    float total = 0;
    for (int i = 0; i < simulations; ++i) {
        Node* node = &root;
        while (node->expanded && !node->edges.empty()) {
            auto& e = select(*node);
            if (!e.child) e.child = std::make_unique<Node>();
            path.push_back({&e, node, game.push(e.move)});
            node = e.child.get();
        }
        try {
            if (!node->expanded) expand(*node, game, evaluate);
        } catch (...) {
            for (auto it = path.rbegin(); it != path.rend(); ++it) game.pop(it->edge->move, it->saved);
            throw;
        }
        float value = node->value;
        while (!path.empty()) {
            auto& step = path.back();
            value = -value;
            ++step.edge->visits;
            step.edge->total += value;
            ++step.parent->visits;
            game.pop(step.edge->move, step.saved);
            path.pop_back();
        }
        total += value;
    }
    SearchResult out{{}, {}, total / simulations};
    for (auto& e : root.edges) {
        out.moves.push_back(e.move);
        out.visits.push_back(e.visits);
    }
    return out;
}

} // namespace tera
