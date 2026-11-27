#include "engine.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace tera {
namespace {

constexpr bool digit(char c) { return c >= '0' && c <= '9'; }
constexpr bool upper(char c) { return c >= 'A' && c <= 'Z'; }
constexpr Side side_of(char c) { return upper(c) ? White : Black; }
constexpr char kind(char c) { return c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c; }
constexpr char color(char c, Side s) { return s == White ? c : c - 'A' + 'a'; }
constexpr int home(Side s) { return s == White ? 23 : 231; }
constexpr int forward(Side s) { return s == White ? 1 : -1; }
constexpr int last(Side s) { return s == White ? 15 : 0; }
constexpr int x(int sq) { return sq % 16; }
constexpr int y(int sq) { return sq / 16; }
constexpr int sign(int d) { return (d > 0) - (d < 0); }
constexpr int square(int f, int r) {
    return f >= 0 && f < 16 && r >= 0 && r < 16 ? 16 * r + f : -1;
}
constexpr int offset(int sq, int dx, int dy) { return square(x(sq) + dx, y(sq) + dy); }

void require(bool good, const char* message) {
    if (!good) throw std::invalid_argument(message);
}

bool decimal(std::string_view s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), digit);
}

std::string normalize(std::string_view s) {
    auto first = s.find_first_not_of('0');
    return first == s.npos ? "0" : std::string(s.substr(first));
}

void increment(std::string& counter) {
    for (auto it = counter.rbegin(); it != counter.rend(); ++it) {
        if (*it != '9') {
            ++*it;
            return;
        }
        *it = '0';
    }
    counter.insert(counter.begin(), '1');
}

char promotion(char k, int distance) {
    switch (k) {
        case 'I': return 'A';
        case 'N': case 'M': case 'Z': return 'F';
        case 'E': case 'W': case 'J': return 'L';
        case 'P': return 'Q';
        case 'T': return distance == 1 ? 'Q' : 'T';
        default: return k;
    }
}

struct Delta { int dx, dy; };
constexpr Delta dirs[] = {{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};

bool attack_from(const Position& p, int from, int to, Side by) {
    int dx = x(to) - x(from), dy = y(to) - y(from);
    int a = std::max(std::abs(dx), std::abs(dy)), b = std::min(std::abs(dx), std::abs(dy));
    if (!a) return false;
    bool ortho = b == 0, diag = a == b;
    bool knight = a == 2 && b == 1, camel = a == 3 && b == 1, giraffe = a == 3 && b == 2;
    auto ray = [&](bool geometry, int screens = 0) {
        if (!geometry) return false;
        int step = 16 * sign(dy) + sign(dx);
        for (int at = from + step; at != to; at += step)
            if (p.board[at] && --screens < 0) return false;
        return screens == 0;
    };
    auto bent = [&](bool eagle) {
        if (eagle ? (b != 1) : (a != b + 1)) return false;
        if (a == 1) return true;
        bool wide = std::abs(dx) > std::abs(dy);
        int sx = sign(dx), sy = sign(dy);
        int bend = from + (eagle || wide ? sx : 0) + 16 * (eagle || !wide ? sy : 0);
        int step = (eagle && !wide ? 0 : sx) + 16 * (eagle && wide ? 0 : sy);
        for (int at = bend; at != to; at += step)
            if (p.board[at]) return false;
        return true;
    };
    bool pawn = std::abs(dx) == 1 && dy == forward(by);
    switch (kind(p.board[from])) {
        case 'A': return knight || ray(ortho || diag);
        case 'B': return ray(diag);
        case 'C': return ray(ortho, 1);
        case 'D': return a <= 3 && (ortho || diag);
        case 'E': return a <= 2 && diag;
        case 'F': return knight || camel || giraffe;
        case 'G': return bent(true);
        case 'H': return knight || ray(ortho);
        case 'I': case 'K': return a == 1;
        case 'J': return a == 1 || knight;
        case 'L': return a <= 2;
        case 'M': return camel;
        case 'N': return knight;
        case 'O': return ray(ortho || diag, 1);
        case 'P': return pawn;
        case 'Q': return ray(ortho || diag);
        case 'R': return ray(ortho);
        case 'S': return (diag && a == 1) || ray(ortho);
        case 'T': return pawn || (a == 3 && (ortho || diag));
        case 'U': return bent(false);
        case 'V': return ray(diag, 1);
        case 'W': return a <= 2 && ortho;
        case 'X': return knight || ray(diag);
        case 'Y': return (ortho && a == 1) || ray(diag);
        case 'Z': return giraffe;
        default: return false;
    }
}

class Candidates {
    const Position& pos;
    std::vector<Move> moves;
    int from = 0;
    int f;
    Side enemy;

    void step(int dx, int dy, int mode = 0) {
        int to = offset(from, dx, dy);
        if (to < 0) return;
        char piece = pos.board[to];
        if (!piece ? mode <= 0 : mode >= 0 && side_of(piece) == enemy && kind(piece) != 'K')
            moves.push_back({from, to});
    }

    void radial(int first, int end, int low = 1, int high = 1) {
        for (int i = first; i < end; ++i)
            for (int d = low; d <= high; ++d)
                step(d * dirs[i].dx, d * dirs[i].dy);
    }

    void leap(int a, int b) {
        for (int sx : {-1, 1}) for (int sy : {-1, 1}) {
            step(sx * a, sy * b);
            step(sx * b, sy * a);
        }
    }

    void slide(int start, Delta d, bool screened) {
        bool past_screen = false;
        for (int to = offset(start, d.dx, d.dy); to >= 0; to = offset(to, d.dx, d.dy)) {
            char piece = pos.board[to];
            if (!piece) {
                if (!past_screen) moves.push_back({from, to});
                continue;
            }
            if (screened && !past_screen) {
                past_screen = true;
                continue;
            }
            if (side_of(piece) == enemy && kind(piece) != 'K') moves.push_back({from, to});
            break;
        }
    }

    void rays(int first, int end, bool screened = false) {
        for (int i = first; i < end; ++i) slide(from, dirs[i], screened);
    }

    void bent(bool eagle) {
        for (int i = eagle ? 4 : 0; i < (eagle ? 8 : 4); ++i) {
            auto [dx, dy] = dirs[i];
            int bend = offset(from, dx, dy);
            if (bend < 0) continue;
            step(dx, dy);
            if (pos.board[bend]) continue;
            if (eagle) {
                slide(bend, {dx, 0}, false);
                slide(bend, {0, dy}, false);
            } else if (dx) {
                slide(bend, {dx, 1}, false);
                slide(bend, {dx, -1}, false);
            } else {
                slide(bend, {1, dy}, false);
                slide(bend, {-1, dy}, false);
            }
        }
    }

    void jump() {
        if (!(pos.rights & (1 << pos.turn)) || pos.check()) return;
        for (int dy = -2; dy <= 2; ++dy) for (int dx = -2; dx <= 2; ++dx) {
            if (std::max(std::abs(dx), std::abs(dy)) != 2) continue;
            int to = offset(from, dx, dy);
            if (to < 0 || pos.board[to]) continue;
            int mid = offset(from, sign(dx), sign(dy));
            int other_mid = offset(from, dx / 2, dy / 2);
            if (!pos.attacked(mid, enemy) ||
                (mid != other_mid && !pos.attacked(other_mid, enemy)))
                moves.push_back({from, to});
        }
    }

    void double_advance() {
        int mid = offset(from, 0, f);
        if (mid >= 0 && !pos.board[mid]) step(0, 2 * f, -1);
    }

    void pawn_steps() {
        step(0, f, -1);
        step(-1, f, 1);
        step(1, f, 1);
    }

    void piece_moves() {
        switch (kind(pos.board[from])) {
            case 'A': rays(0, 8); leap(2, 1); break;
            case 'B': rays(4, 8); break;
            case 'C': rays(0, 4, true); break;
            case 'D': radial(0, 8, 1, 3); break;
            case 'E': radial(4, 8, 1, 2); break;
            case 'F': leap(2, 1); leap(3, 1); leap(3, 2); break;
            case 'G': bent(true); break;
            case 'H': rays(0, 4); leap(2, 1); break;
            case 'I': radial(0, 8); double_advance(); break;
            case 'J': radial(0, 8); leap(2, 1); break;
            case 'K': radial(0, 8); jump(); break;
            case 'L': radial(0, 8, 1, 2); leap(2, 1); break;
            case 'M': leap(3, 1); break;
            case 'N': leap(2, 1); break;
            case 'O': rays(0, 8, true); break;
            case 'P':
                pawn_steps();
                double_advance();
                if (pos.ep >= 0 && y(pos.ep) - y(from) == f && std::abs(x(pos.ep) - x(from)) == 1)
                    moves.push_back({from, pos.ep});
                break;
            case 'Q': rays(0, 8); break;
            case 'R': rays(0, 4); break;
            case 'S': rays(0, 4); radial(4, 8); break;
            case 'T': radial(0, 8, 3, 3); pawn_steps(); break;
            case 'U': bent(false); break;
            case 'V': rays(4, 8, true); break;
            case 'W': radial(0, 4, 1, 2); break;
            case 'X': rays(4, 8); leap(2, 1); break;
            case 'Y': rays(4, 8); radial(0, 4); break;
            case 'Z': leap(3, 2); break;
        }
    }

public:
    explicit Candidates(const Position& p) : pos(p), f(forward(p.turn)), enemy(other(p.turn)) {}
    std::vector<Move> generate() && {
        moves.reserve(192);
        for (int chunk = 0; chunk < 4; ++chunk) {
            for (auto bits = pos.occupied[pos.turn][chunk]; bits; bits &= bits - 1) {
                from = 64 * chunk + std::countr_zero(bits);
                piece_moves();
            }
        }
        return std::move(moves);
    }
};

} // namespace

std::string square_name(int sq) {
    return std::string(1, static_cast<char>('a' + x(sq))) + std::to_string(y(sq) + 1);
}

int parse_square(std::string_view s) {
    if (s.size() < 2 || s.size() > 3 || s[0] < 'a' || s[0] > 'p' ||
        s[1] == '0' || !decimal(s.substr(1))) return -1;
    int rank = s[1] - '0';
    if (s.size() == 3) rank = rank * 10 + s[2] - '0';
    return square(s[0] - 'a', rank - 1);
}

std::string move_name(Move m) { return square_name(m.from) + "-" + square_name(m.to); }

Move parse_move(std::string_view name) {
    auto split = name.find('-');
    require(split != name.npos, "expected move in source-destination form");
    Move m{parse_square(name.substr(0, split)), parse_square(name.substr(split + 1))};
    require(m.from >= 0 && m.to >= 0, "invalid move coordinates");
    return m;
}

Position Position::from_fen(std::string_view fen, bool composition) {
    std::istringstream input{std::string(fen)};
    std::string placement, side, rights, ep, half, full, extra;
    require(static_cast<bool>(input >> placement >> side >> rights >> ep >> half >> full) &&
            !(input >> extra), "FEN must have six fields");
    Position p;
    int file = 0, rank = 15;
    for (std::size_t i = 0; i < placement.size();) {
        char c = placement[i++];
        if (digit(c)) {
            require(c != '0', "empty run begins with zero");
            int empty = c - '0';
            while (i < placement.size() && digit(placement[i])) {
                empty = empty * 10 + placement[i++] - '0';
                require(empty <= 16, "empty run exceeds 16");
            }
            file += empty;
        } else if (c == '/') {
            require(file == 16 && rank > 0, "invalid rank width or count");
            file = 0;
            --rank;
        } else {
            char k = kind(c);
            require(k >= 'A' && k <= 'Z' && file < 16, "invalid placement symbol or width");
            Side s = side_of(c);
            require(k != 'K' || p.king[s] == -1, "duplicate King");
            require(rank != last(s) || k == 'T' || promotion(k, 1) == k,
                    "unpromoted piece on promotion rank");
            p.put(square(file++, rank), c);
        }
        require(file <= 16, "rank exceeds 16 squares");
    }
    require(rank == 0 && file == 16, "expected sixteen ranks of width sixteen");
    require(p.king[White] >= 0 && p.king[Black] >= 0, "expected one King per side");
    require(side == "w" || side == "b", "invalid side");
    p.turn = side == "w" ? White : Black;
    require(rights == "-" || rights == "K" || rights == "k" || rights == "Kk", "invalid jump rights");
    for (Side s : {White, Black}) {
        if (rights.find(color('K', s)) == rights.npos) continue;
        require(composition || p.king[s] == home(s), "King with jump right is off home square");
        p.rights |= 1 << s;
    }
    if (ep != "-") {
        p.ep = parse_square(ep);
        int f = forward(p.turn);
        require(p.ep >= 0 && offset(p.ep, 0, f) >= 0 && offset(p.ep, 0, -f) >= 0, "invalid ep square");
        int victim = offset(p.ep, 0, -f);
        char c = p.board[victim], k = kind(c);
        bool promoted = y(victim) == last(other(p.turn));
        require(!p.board[p.ep] && !p.board[offset(p.ep, 0, f)] && c && side_of(c) != p.turn &&
                (promoted ? k == 'Q' || k == 'A' : k == 'P' || k == 'I'), "inconsistent ep metadata");
    }
    require(decimal(half) && decimal(full), "invalid move counters");
    p.halfmove = normalize(half);
    p.fullmove = normalize(full);
    require(p.fullmove != "0", "fullmove number must be positive");
    require(!p.attacked(p.king[other(p.turn)], p.turn), "nonmoving King is in check");
    return p;
}

std::string Position::fen() const {
    std::string result;
    for (int r = 15; r >= 0; --r) {
        if (r != 15) result += '/';
        int empty = 0;
        for (int f = 0; f < 16; ++f) {
            char c = board[square(f, r)];
            if (!c) {
                ++empty;
                continue;
            }
            if (empty) result += std::to_string(empty);
            empty = 0;
            result += c;
        }
        if (empty) result += std::to_string(empty);
    }
    result += turn == White ? " w " : " b ";
    if (!rights) result += '-';
    if (rights & 1) result += 'K';
    if (rights & 2) result += 'k';
    result += ' ';
    result += ep < 0 ? "-" : square_name(ep);
    return result + " " + halfmove + " " + fullmove;
}

int Position::capped_halfmove() const {
    return halfmove.size() > 3 ? halfmove_limit : std::min(halfmove_limit, std::stoi(halfmove));
}

void Position::put(int sq, char p) {
    auto mask = std::uint64_t{1} << (sq % 64);
    char old = board[sq];
    if (old) {
        occupied[side_of(old)][sq / 64] &= ~mask;
        if (kind(old) == 'K') king[side_of(old)] = -1;
    }
    board[sq] = p;
    if (p) {
        occupied[side_of(p)][sq / 64] |= mask;
        if (kind(p) == 'K') king[side_of(p)] = sq;
    }
}

bool Position::attacked(int target, Side by) const {
    for (int chunk = 0; chunk < 4; ++chunk)
        for (auto bits = occupied[by][chunk]; bits; bits &= bits - 1)
            if (attack_from(*this, 64 * chunk + std::countr_zero(bits), target, by)) return true;
    return false;
}

std::vector<Move> Position::legal() {
    auto moves = Candidates(*this).generate();
    Side mover = turn;
    std::erase_if(moves, [&](Move m) {
        auto saved = make(m, false);
        bool unsafe = attacked(king[mover], turn);
        undo(m, saved, false);
        return unsafe;
    });
    return moves;
}

Undo Position::make(Move m, bool counters) {
    char piece = board[m.from], k = kind(piece);
    int victim = m.to;
    if (k == 'P' && m.to == ep) victim -= 16 * forward(turn);
    Undo saved{piece, board[victim], victim, rights, ep, {}, {}};
    if (counters) {
        saved.halfmove = halfmove;
        saved.fullmove = fullmove;
        if (saved.taken || k == 'P') halfmove = "0";
        else increment(halfmove);
        if (turn == Black) increment(fullmove);
    }
    if (k == 'K') rights &= ~(1 << turn);
    bool doubled = (k == 'P' || k == 'I') && m.to - m.from == 32 * forward(turn);
    ep = doubled ? (m.from + m.to) / 2 : -1;
    put(m.from, 0);
    if (victim != m.to) put(victim, 0);
    if (y(m.to) == last(turn)) {
        int dist = std::max(std::abs(x(m.to) - x(m.from)), std::abs(y(m.to) - y(m.from)));
        piece = color(promotion(k, dist), turn);
    }
    put(m.to, piece);
    turn = other(turn);
    return saved;
}

void Position::undo(Move m, const Undo& saved, bool counters) {
    turn = other(turn);
    rights = saved.rights;
    ep = saved.ep;
    if (counters) {
        halfmove = saved.halfmove;
        fullmove = saved.fullmove;
    }
    put(m.to, 0);
    put(m.from, saved.moved);
    put(saved.capture_square, saved.taken);
}

std::string Position::repetition_key() {
    int effective = -1;
    if (ep >= 0) {
        for (int dx : {-1, 1}) {
            int from = offset(ep, dx, -forward(turn));
            if (from < 0 || board[from] != color('P', turn)) continue;
            Move m{from, ep};
            Side mover = turn;
            auto saved = make(m, false);
            bool safe = !attacked(king[mover], turn);
            undo(m, saved, false);
            if (safe) {
                effective = ep;
                break;
            }
        }
    }
    std::string key(board.data(), board.size());
    key += static_cast<char>(turn);
    key += static_cast<char>(rights);
    key += static_cast<char>(effective < 0 ? 0 : effective);
    return key;
}

Game::Game(Position position) : pos(std::move(position)) {
    keys.push_back(pos.repetition_key());
    ++history[keys.back()];
}

Undo Game::push(Move m) {
    auto saved = pos.make(m);
    keys.push_back(pos.repetition_key());
    ++history[keys.back()];
    return saved;
}

void Game::pop(Move m, const Undo& saved) {
    auto it = history.find(keys.back());
    if (--it->second == 0) history.erase(it);
    keys.pop_back();
    pos.undo(m, saved);
}

End Game::end(const std::vector<Move>& moves) const {
    if (moves.empty()) return pos.check() ? End::Checkmate : End::Stalemate;
    int count = 0;
    for (const auto& chunks : pos.occupied)
        for (auto chunk : chunks) count += std::popcount(chunk);
    if (count == 2) return End::BareKings;
    if (occurrences() >= 3) return End::Repetition;
    if (pos.capped_halfmove() == halfmove_limit) return End::MoveCount;
    return End::Playing;
}

const char* end_name(End end) {
    switch (end) {
        case End::Playing: return "playing";
        case End::Checkmate: return "checkmate";
        case End::Stalemate: return "stalemate";
        case End::Repetition: return "repetition";
        case End::MoveCount: return "move_count";
        case End::BareKings: return "bare_kings";
    }
    return "unknown";
}

std::uint64_t perft(Position& pos, int depth) {
    if (depth == 0) return 1;
    auto moves = pos.legal();
    if (depth == 1) return moves.size();
    std::uint64_t count = 0;
    for (Move m : moves) {
        auto saved = pos.make(m, false);
        count += perft(pos, depth - 1);
        pos.undo(m, saved, false);
    }
    return count;
}

int material(const Position& pos) {
    constexpr int values[] = {15,4,4,9,4,9,7,8,5,6,0,9,3,3,6,1,10,6,7,5,7,4,4,7,5,3};
    int value = 0;
    for (char c : pos.board)
        if (c) value += (upper(c) ? 1 : -1) * values[kind(c) - 'A'];
    return value;
}

namespace {
int negamax(Game& g, int depth, int ply, int alpha, int beta) {
    auto moves = g.pos.legal();
    auto end = g.end(moves);
    if (end != End::Playing) return end == End::Checkmate ? ply - 10000 : 0;
    if (!depth) return (g.pos.turn == White ? 1 : -1) * material(g.pos);
    for (Move m : moves) {
        auto saved = g.push(m);
        int value = -negamax(g, depth - 1, ply + 1, -beta, -alpha);
        g.pop(m, saved);
        alpha = std::max(alpha, value);
        if (alpha >= beta) break;
    }
    return alpha;
}
} // namespace

Move best_material(Game& g, int depth) {
    auto moves = g.pos.legal();
    require(g.end(moves) == End::Playing, "game has ended");
    require(depth > 0, "search depth must be positive");
    Move choice = moves.front();
    int best = -20000;
    for (Move m : moves) {
        auto saved = g.push(m);
        int value = -negamax(g, depth - 1, 1, -20000, -best);
        g.pop(m, saved);
        if (value > best) {
            best = value;
            choice = m;
        }
    }
    return choice;
}

} // namespace tera
