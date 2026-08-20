"use strict";
// one function per process: node bench_v8.js <name>
const impls = {
  naive: (rd) => ((rd % 7) + 11) % 7,
  naive_branch: (rd) => { const r = (rd + 4) % 7; return r < 0 ? r + 7 : r; },
  joffe_posZ: (rd) => ((Math.imul(rd, 613566757) + 0x94920000) | 0) >>> 29,
  joffe_negZ: (rd) => ((Math.imul(rd, 613566757) - 1802371072) | 0) >>> 29,
};
const name = process.argv[2];
const fn = impls[name];
if (!fn) throw new Error("unknown impl");

let xsState = 0x243f6a88 | 0;
function xs() { let x = xsState; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; xsState = x | 0; return xsState >>> 0; }
const N = 2_000_000, REPS = 7;
const data = new Int32Array(N);
for (let i = 0; i < N; i++) data[i] = (xs() % 178_000_001) - 89_000_000;

// warmup (monomorphic)
for (let r = 0; r < 3; r++) { let a = 0; for (let i = 0; i < N; i++) a += fn(data[i]); if (a === -1) console.log("x"); }

let best = Infinity;
for (let r = 0; r < REPS; r++) {
  let acc = 0;
  const t0 = process.hrtime.bigint();
  for (let i = 0; i < N; i++) acc += fn(data[i]);
  const dt = Number(process.hrtime.bigint() - t0);
  if (acc === -1) console.log("impossible");
  if (dt < best) best = dt;
}
console.log(`${name.padEnd(14)} throughput ${(best / N).toFixed(4)} ns/op`);

best = Infinity;
for (let r = 0; r < REPS; r++) {
  let w = 0;
  const t0 = process.hrtime.bigint();
  for (let i = 0; i < N; i++) w = fn(data[i] + w);
  const dt = Number(process.hrtime.bigint() - t0);
  if (w === -1) console.log("impossible");
  if (dt < best) best = dt;
}
console.log(`${name.padEnd(14)} latency    ${(best / N).toFixed(4)} ns/op`);
