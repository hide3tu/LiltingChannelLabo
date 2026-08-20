"use strict";
// isolate the -0 hypothesis for naive_branch
function naiveBranch(rd) { const r = (rd + 4) % 7; return r < 0 ? r + 7 : r; }
let xsState = 0x243f6a88 | 0;
function xs() { let x = xsState; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; xsState = x | 0; return xsState >>> 0; }
const N = 2_000_000, REPS = 7;
const mode = process.argv[2];
const data = new Int32Array(N);
for (let i = 0; i < N; i++) {
  let v = (xs() % 178_000_001) - 89_000_000;
  if (mode === "positive") v = Math.abs(v);
  if (mode === "neg_no_zero") { // negative allowed, but never (rd+4) ≡ 0 mod 7
    while ((v + 4) % 7 === 0) v -= 1;
  }
  data[i] = v;
}
for (let r = 0; r < 3; r++) { let a = 0; for (let i = 0; i < N; i++) a += naiveBranch(data[i]); if (a === -1) console.log("x"); }
let best = Infinity;
for (let r = 0; r < REPS; r++) {
  let acc = 0;
  const t0 = process.hrtime.bigint();
  for (let i = 0; i < N; i++) acc += naiveBranch(data[i]);
  const dt = Number(process.hrtime.bigint() - t0);
  if (acc === -1) console.log("impossible");
  if (dt < best) best = dt;
}
console.log(`naive_branch [${mode}] throughput ${(best / N).toFixed(4)} ns/op`);
