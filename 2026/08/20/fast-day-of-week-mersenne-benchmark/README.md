# メルセンヌ数曜日計算 vs 素朴な%7 (M4実測)

Ben Joffe の [A faster way to calculate the day-of-the-week](https://www.benjoffe.com/fast-day-of-week) の
アルゴリズムを、clang / rustc / V8 / CPython の素朴な `% 7` と比較したベンチ一式。

記事: [JA](https://www.lilting.ch/articles/fast-day-of-week-mersenne-benchmark) / [EN](https://www.lilting.ch/en/articles/fast-day-of-week-mersenne-benchmark)

## 実行方法

```sh
# C: 正しさ網羅検証(int32全域) と ベンチ
clang -O2 -std=c11 bench.c -o bench && ./bench check && ./bench

# アセンブリ確認用の noinline 単体関数
clang -O2 -S asm.c -o asm.s

# Rust
rustc -O bench.rs -o bench_rs && ./bench_rs

# V8: 1プロセス1関数で計測（同一プロセスだと型フィードバック多態化で数字が壊れる）
for impl in naive naive_branch joffe_posZ joffe_negZ; do node bench_v8.js $impl; done

# V8: -0 による deopt の切り分け
node bench_v8_negzero.js mixed
node bench_v8_negzero.js positive
node bench_v8_negzero.js neg_no_zero

# CPython
python3 bench.py
```

環境: Mac mini (Apple M4, 16GB) / macOS 26.5.2 / Apple clang 21.0.0 / rustc 1.92.0 / Node.js 25.3.0 (V8 14.1) / CPython 3.14.4
