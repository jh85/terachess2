#pragma once

#include "engine.hpp"
#include <functional>
#include <span>

namespace tera {

inline constexpr int feature_count = 261;
using Features = std::array<int, feature_count>;
Features features(const Game& game);

// Callback returns a value from the current side's perspective and fills legal move logits.
using Evaluate = std::function<float(const Features&, std::span<const int>, std::span<float>)>;

struct SearchResult {
    std::vector<Move> moves;
    std::vector<int> visits;
    float value;
};

SearchResult mcts(Game& game, int simulations, std::uint64_t seed, bool noise, const Evaluate& evaluate);

} // namespace tera
