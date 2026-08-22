"""Synthesize and inspect an 18-bit leap-year classifier with Z3."""

import z3

BITS = 18
MAX_YEAR = 499
WORD_MASK = (1 << BITS) - 1


def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def make_solver(
    max_year: int,
) -> tuple[z3.Solver, z3.BitVecRef, z3.BitVecRef, z3.BitVecRef]:
    f, m, t = z3.BitVecs("f m t", BITS)
    solver = z3.Solver()

    # The input range is finite, so spell out every year as a constraint.
    for year in range(max_year + 1):
        y = z3.BitVecVal(year, BITS)
        candidate = z3.ULE((y * f) & m, t)
        solver.add(candidate == is_leap_year(year))

    return solver, f, m, t


def synthesize() -> tuple[int, int, int]:
    solver, f, m, t = make_solver(MAX_YEAR)
    result = solver.check()
    assert result == z3.sat, result

    model = solver.model()
    values = tuple(model[v].as_long() for v in (f, m, t))
    print(f"0..{MAX_YEAR}: {result}")
    print(f"f = {values[0]:6} = 0x{values[0]:05X}")
    print(f"m = {values[1]:6} = 0x{values[1]:05X}")
    print(f"t = {values[2]:6} = 0x{values[2]:05X}")
    return values


def verify(f: int, m: int, t: int) -> None:
    for year in range(MAX_YEAR + 1):
        product = (year * f) & WORD_MASK
        candidate = (product & m) <= t
        assert candidate == is_leap_year(year), year
    print(f"exhaustive verification: 0..{MAX_YEAR} all matched")


def show_boundary(f: int, m: int, t: int) -> None:
    print("\nyear  product  masked   candidate  calendar")
    for year in (0, 100, 200, 300, 400, 500):
        product = (year * f) & WORD_MASK
        masked = product & m
        candidate = masked <= t
        calendar = is_leap_year(year)
        print(
            f"{year:4}  0x{product:05X}  0x{masked:05X}  "
            f"{str(candidate):>9}  {str(calendar):>8}"
        )


def prove_no_solution_through_500() -> None:
    solver, _, _, _ = make_solver(500)
    result = solver.check()
    assert result == z3.unsat, result
    print(f"\n0..500 with any {BITS}-bit f, m, t: {result}")


def check_cycle_widths() -> None:
    print("\n0..400 full-cycle constraints:")
    for bits in (16, 17):
        f, m, t = z3.BitVecs(f"f{bits} m{bits} t{bits}", bits)
        solver = z3.Solver()
        for year in range(401):
            y = z3.BitVecVal(year, bits)
            solver.add(z3.ULE((y * f) & m, t) == is_leap_year(year))
        print(f"{bits} bits: {solver.check()}")


if __name__ == "__main__":
    constants = synthesize()
    verify(*constants)
    show_boundary(*constants)
    prove_no_solution_through_500()
    check_cycle_widths()
