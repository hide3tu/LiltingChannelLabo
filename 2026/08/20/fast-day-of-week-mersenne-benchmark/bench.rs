// rem_euclid vs Joffe Mersenne trick -- weekday 0=Sun..6=Sat, rd days since 1970-01-01
use std::hint::black_box;
use std::time::Instant;

#[inline(always)]
fn naive_rem_euclid(rd: i32) -> u32 {
    ((rd as i64 + 4).rem_euclid(7)) as u32
}

#[inline(always)]
fn naive_i32(rd: i32) -> u32 {
    (((rd % 7) + 11) % 7) as u32
}

#[inline(always)]
fn joffe_narrow(rd: i32) -> u32 {
    ((rd as u32).wrapping_mul(613_566_757).wrapping_add(0x9492_0000)) >> 29
}

fn xs(state: &mut u32) -> u32 {
    let mut x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    x
}

const N: usize = 2_000_000;
const REPS: usize = 7;

fn bench_tp(name: &str, data: &[i32], f: impl Fn(i32) -> u32) {
    let mut best = f64::MAX;
    for _ in 0..REPS {
        let t0 = Instant::now();
        let mut acc: u64 = 0;
        for &rd in data {
            acc += f(rd) as u64;
        }
        let dt = t0.elapsed().as_secs_f64() * 1e9;
        black_box(acc);
        if dt < best {
            best = dt;
        }
    }
    println!("{:<20} throughput {:8.4} ns/op", name, best / N as f64);
}

fn bench_lat(name: &str, data: &[i32], f: impl Fn(i32) -> u32) {
    let mut best = f64::MAX;
    for _ in 0..REPS {
        let t0 = Instant::now();
        let mut w: u32 = 0;
        for &rd in data {
            w = f(rd + w as i32);
        }
        let dt = t0.elapsed().as_secs_f64() * 1e9;
        black_box(w);
        if dt < best {
            best = dt;
        }
    }
    println!("{:<20} latency    {:8.4} ns/op", name, best / N as f64);
}

fn main() {
    // correctness over narrow signed range
    for rd in -89_434_796i32..=89_522_175 {
        let r = naive_rem_euclid(rd);
        assert_eq!(naive_i32(rd), r, "naive_i32 at {rd}");
        assert_eq!(joffe_narrow(rd), r, "joffe at {rd}");
    }
    println!("correctness: all OK");

    let mut state = 0x243F_6A88u32;
    let data: Vec<i32> = (0..N)
        .map(|_| (xs(&mut state) % 178_000_001) as i32 - 89_000_000)
        .collect();

    bench_tp("rem_euclid", &data, naive_rem_euclid);
    bench_tp("naive_i32", &data, naive_i32);
    bench_tp("joffe_narrow", &data, joffe_narrow);
    bench_lat("rem_euclid", &data, naive_rem_euclid);
    bench_lat("naive_i32", &data, naive_i32);
    bench_lat("joffe_narrow", &data, joffe_narrow);
}
