#include "engine.hpp"
#include <algorithm>
#include <charconv>
#include <iostream>
#include <stdexcept>

namespace {

void print_moves(tera::Position& p) {
    auto moves = p.legal();
    std::sort(moves.begin(), moves.end(), [](auto a, auto b) { return a.code() < b.code(); });
    std::cout << '[';
    const char* separator = "";
    for (auto m : moves) {
        std::cout << separator << '"' << tera::move_name(m) << '"';
        separator = ",";
    }
    std::cout << "]\n";
}

void replay(tera::Game& g, int at, int argc, char** argv) {
    for (; at < argc; ++at) {
        auto moves = g.pos.legal();
        auto m = tera::parse_move(argv[at]);
        if (g.end(moves) != tera::End::Playing ||
            std::find(moves.begin(), moves.end(), m) == moves.end())
            throw std::invalid_argument("cannot play " + std::string(argv[at]));
        g.push(m);
    }
}

int depth(std::string_view str, int low, int high) {
    int value;
    auto [ptr, ec] = std::from_chars(str.data(), str.data() + str.size(), value);
    if (ec != std::errc{} || ptr != str.data() + str.size() || value < low || value > high)
        throw std::invalid_argument("invalid search depth");
    return value;
}

} // namespace

int main(int argc, char** argv) {
    try {
        int at = 1;
        bool composition = at < argc && std::string_view(argv[at]) == "--composition";
        if (composition) ++at;
        if (at == argc) throw std::invalid_argument(
            "usage: tera [--composition] moves|fen|status|apply|perft|divide|material|batch ...");
        std::string_view cmd = argv[at++];
        if (cmd == "batch") {
            std::string line;
            while (std::getline(std::cin, line)) {
                try {
                    auto p = tera::Position::from_fen(line, composition);
                    print_moves(p);
                } catch (const std::invalid_argument&) {
                    std::cout << "null\n";
                }
            }
            return 0;
        }
        int d = 0;
        if (cmd == "perft" || cmd == "divide" || cmd == "material") {
            if (at == argc) throw std::invalid_argument("expected depth");
            d = depth(argv[at++], cmd == "perft" ? 0 : 1, cmd == "material" ? 8 : 10);
        }
        std::string_view fen = at == argc ? "start" : argv[at++];
        tera::Game g(tera::Position::from_fen(fen == "start" ? tera::initial : fen, composition));
        replay(g, at, argc, argv);
        if (cmd == "moves") print_moves(g.pos);
        else if (cmd == "apply" || cmd == "fen") std::cout << g.pos.fen() << '\n';
        else if (cmd == "status")
            std::cout << "{\"end\":\"" << tera::end_name(g.end(g.pos.legal()))
                      << "\",\"check\":" << (g.pos.check() ? "true" : "false")
                      << ",\"repetitions\":" << g.occurrences() << "}\n";
        else if (cmd == "perft") std::cout << tera::perft(g.pos, d) << '\n';
        else if (cmd == "divide") {
            std::cout << '{';
            const char* separator = "";
            for (auto m : g.pos.legal()) {
                auto u = g.pos.make(m, false);
                std::cout << separator << '"' << tera::move_name(m) << "\":" << tera::perft(g.pos, d - 1);
                g.pos.undo(m, u, false);
                separator = ",";
            }
            std::cout << "}\n";
        } else if (cmd == "material") {
            std::cout << '"' << tera::move_name(tera::best_material(g, d)) << "\"\n";
        } else throw std::invalid_argument("unknown command");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "tera: " << e.what() << '\n';
        return 2;
    }
}
