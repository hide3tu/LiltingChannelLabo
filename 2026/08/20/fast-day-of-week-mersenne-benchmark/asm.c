#include <stdint.h>
__attribute__((noinline)) uint32_t naive_signed(int32_t rd) {
    return ((rd % 7) + 11) % 7;
}
__attribute__((noinline)) uint32_t naive_rem_euclid(int32_t rd) {
    int32_t r = (int32_t)(((int64_t)rd + 4) % 7);
    return r < 0 ? r + 7 : r;
}
__attribute__((noinline)) uint32_t naive_unsigned(uint32_t rd) {
    return (rd + 4u) % 7u;
}
__attribute__((noinline)) uint32_t joffe_full(int32_t rd) {
    const uint32_t a = (uint32_t)rd * 613566756u + 0x95000000u;
    const uint32_t b = (uint32_t)((rd >> 1) + (rd >> 4));
    return (a + b) >> 29;
}
__attribute__((noinline)) uint32_t joffe_narrow(int32_t rd) {
    return ((uint32_t)rd * 613566757u + 0x94920000u) >> 29;
}
