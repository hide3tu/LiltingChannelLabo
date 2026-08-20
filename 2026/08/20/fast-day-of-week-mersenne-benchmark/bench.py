# CPython: naive % 7 vs Joffe Mersenne trick
import sys
import timeit

M = 613566757
Z = 0x94920000
MASK = 0xFFFFFFFF


def naive(rd):
    # Python's % already returns non-negative for positive modulus
    return (rd + 4) % 7


def joffe(rd):
    return ((rd * M + Z) & MASK) >> 29


def joffe_u32(rd):
    # unsigned lane: rd >= 0, epoch handled by -3 wrap
    return (((rd - 3) * M) & MASK) >> 29


def xorshift_data(n):
    x = 0x243F6A88
    out = []
    for _ in range(n):
        x ^= (x << 13) & MASK
        x ^= x >> 17
        x ^= (x << 5) & MASK
        out.append(x % 178000001 - 89000000)
    return out


def check():
    for rd in range(-89434796, 89522176, 8731):
        r = naive(rd)
        u = (rd % 7 + 11) % 7
        assert u == r, rd
        assert joffe(rd) == r, rd
    for rd in list(range(-700, 701)) + [-89434796, 89522175]:
        assert joffe(rd) == naive(rd), rd
    print("correctness: OK (sampled)")


def bench():
    data = xorshift_data(200000)
    n = len(data)
    for name, fn in [("naive", naive), ("joffe", joffe)]:
        best = min(timeit.repeat(lambda: sum(map(fn, data)), number=1, repeat=15))
        print(f"{name:<8} {best / n * 1e9:8.2f} ns/op (call via map)")
    # inline expression form, no function-call overhead per element
    loop_naive = "for rd in data:\n    acc += (rd + 4) % 7"
    loop_joffe = "for rd in data:\n    acc += ((rd * 613566757 + 2492596224) & 4294967295) >> 29"
    for name, body in [("naive", loop_naive), ("joffe", loop_joffe)]:
        best = min(
            timeit.repeat(body, setup="acc = 0", globals={"data": data}, number=1, repeat=15)
        )
        print(f"{name:<8} {best / n * 1e9:8.2f} ns/op (inline loop)")


if __name__ == "__main__":
    print(sys.version)
    check()
    bench()
