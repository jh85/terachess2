#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// A game owns its repetition history. Use distinct games for simultaneous calls.
typedef struct tera_game tera_game;
typedef int (*tera_evaluator)(void* context, const int* features, const int* moves,
                              int count, float* logits, float* value);
const char* tera_profile(void);
const char* tera_error(void);
tera_game* tera_create(const char* fen, int composition);
void tera_destroy(tera_game* game);
const char* tera_fen(tera_game* game);
int tera_features(tera_game* game, int* out); // 261 integers
int tera_legal(tera_game* game, int* out, int capacity);
int tera_play(tera_game* game, int move);
int tera_end(tera_game* game); // 0 playing, 1 mate, 2 stalemate, 3 repetition, 4 move count, 5 bare kings
int tera_material(tera_game* game); // White perspective
int tera_best_material(tera_game* game, int depth);
int tera_search(tera_game* game, int simulations, uint64_t seed, int noise,
                tera_evaluator eval, void* context, int* moves, int* visits,
                int capacity, float* value);
// Move codes are from*256+to, with a1=0 and p16=255.
// Fallible integer-returning functions return -1 on error. String results live until the next
// write to the respective thread-local string. Search callbacks are synchronous.

#ifdef __cplusplus
}
#endif
