// Ben Joffe fast day-of-week (Mersenne trick) vs naive %7 -- M4 bench
// weekday: 0=Sun .. 6=Sat, rd = days since 1970-01-01 (Thu=4)
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// ---- implementations ----

static inline uint32_t naive_signed(int32_t rd) {
    return ((rd % 7) + 11) % 7;
}

// clang/rustc are told nothing; this is what a human writes with rem_euclid semantics
static inline uint32_t naive_rem_euclid(int32_t rd) {
    int32_t r = (int32_t)(((int64_t)rd + 4) % 7);
    return r < 0 ? r + 7 : r;
}

// Joffe full range (all int32), benjoffe.hpp get_weekday_32unix
static inline uint32_t joffe_full(int32_t rd) {
    const uint32_t M = 613566756u;      // (1<<32)/7
    const uint32_t Z = 0x95000000u;
    const uint32_t a = (uint32_t)rd * M + Z;
    const uint32_t b = (uint32_t)((rd >> 1) + (rd >> 4));
    return (a + b) >> 29;
}

// Joffe narrow (+-89M days = +-245k years), get_weekday_32unix_narrow
static inline uint32_t joffe_narrow(int32_t rd) {
    const uint32_t M = 613566757u;      // (1<<32)/7 + 1
    const uint32_t Z = 0x94920000u;
    return ((uint32_t)rd * M + Z) >> 29;
}

// unsigned lane (rd >= 0 only)
static inline uint32_t naive_unsigned(uint32_t rd) {
    return (rd + 4u) % 7u;
}

// get_weekday_u32unix_narrow (0 .. 178,956,975)
static inline uint32_t joffe_unsigned(uint32_t rd) {
    const uint32_t M = 613566757u;
    return ((rd - 3u) * M) >> 29;
}

// ---- correctness ----

static int check_all(void) {
    // exhaustive over full int32 for full-range impls
    for (int64_t i = INT32_MIN; i <= INT32_MAX; i++) {
        int32_t rd = (int32_t)i;
        uint32_t ref = naive_signed(rd);
        if (joffe_full(rd) != ref) {
            printf("MISMATCH joffe_full at %d: %u vs %u\n", rd, joffe_full(rd), ref);
            return 1;
        }
        if (naive_rem_euclid(rd) != ref) {
            printf("MISMATCH rem_euclid at %d\n", rd);
            return 1;
        }
    }
    // narrow: documented input range
    for (int64_t i = -89434796; i <= 89522175; i++) {
        int32_t rd = (int32_t)i;
        if (joffe_narrow(rd) != naive_signed(rd)) {
            printf("MISMATCH joffe_narrow at %d\n", rd);
            return 1;
        }
    }
    // unsigned narrow: 0 .. 178,956,975
    for (int64_t i = 0; i <= 178956975; i++) {
        uint32_t rd = (uint32_t)i;
        if (joffe_unsigned(rd) != naive_unsigned(rd)) {
            printf("MISMATCH joffe_unsigned at %u\n", rd);
            return 1;
        }
    }
    printf("correctness: all OK\n");
    return 0;
}

// ---- bench harness ----

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static uint32_t xs_state = 0x243F6A88u;
static uint32_t xs(void) {
    uint32_t x = xs_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return xs_state = x;
}

#define N 2000000
#define REPS 7
static int32_t data_s[N];
static uint32_t data_u[N];

volatile uint64_t sink;

#define BENCH_TP(name, fn, arr) do { \
    double best = 1e30; \
    for (int r = 0; r < REPS; r++) { \
        uint64_t acc = 0; \
        double t0 = now_ns(); \
        for (int i = 0; i < N; i++) acc += fn(arr[i]); \
        double t1 = now_ns(); \
        sink = acc; \
        if (t1 - t0 < best) best = t1 - t0; \
    } \
    printf("%-24s throughput %8.4f ns/op\n", name, best / N); \
} while (0)

#define BENCH_LAT(name, fn, arr) do { \
    double best = 1e30; \
    for (int r = 0; r < REPS; r++) { \
        uint32_t w = 0; \
        double t0 = now_ns(); \
        for (int i = 0; i < N; i++) w = fn(arr[i] + (int32_t)w); \
        double t1 = now_ns(); \
        sink = w; \
        if (t1 - t0 < best) best = t1 - t0; \
    } \
    printf("%-24s latency    %8.4f ns/op\n", name, best / N); \
} while (0)

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "check") == 0) return check_all();

    for (int i = 0; i < N; i++) {
        // +-89,000,000: inside every signed variant's range
        data_s[i] = (int32_t)(xs() % 178000001u) - 89000000;
        // 0 .. 178,000,000: inside unsigned narrow range
        data_u[i] = xs() % 178000001u;
    }

    BENCH_TP("naive_signed",     naive_signed,     data_s);
    BENCH_TP("naive_rem_euclid", naive_rem_euclid, data_s);
    BENCH_TP("joffe_full",       joffe_full,       data_s);
    BENCH_TP("joffe_narrow",     joffe_narrow,     data_s);
    BENCH_TP("naive_unsigned",   naive_unsigned,   data_u);
    BENCH_TP("joffe_unsigned",   joffe_unsigned,   data_u);

    BENCH_LAT("naive_signed",     naive_signed,     data_s);
    BENCH_LAT("naive_rem_euclid", naive_rem_euclid, data_s);
    BENCH_LAT("joffe_full",       joffe_full,       data_s);
    BENCH_LAT("joffe_narrow",     joffe_narrow,     data_s);

    return 0;
}
