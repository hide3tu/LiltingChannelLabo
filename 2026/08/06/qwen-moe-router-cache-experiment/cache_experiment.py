"""
task5: 対照実験本体（LRU相当のベースライン vs 観測ベースの固定ウォームアップキャッシュ）

【まだ未実行・未検証】モデルロードが必要なため、2026-08-06時点ではコードのみ。
Macを空ける必要があるとの指示で実機での検証は保留中。次回、安全な環境が整ってから
まずsmoke testで動作確認すること。

## 設計

SwitchLinear/QuantizedSwitchLinear (mlx_lm/models/switch_layers.py) を確認した結果、
各MoE層のエキスパート重みは (num_experts, output_dims, input_dims) の単一mx.array
として格納されていて、`gather_qmm`(量子化版)/`gather_mm`(非量子化版)が
`rhs_indices=indices` でexpert indexをgatherしながら行列積する。

safetensorsはmmapされるため、`gather_qmm`が実際に触れた行(=選ばれたexpert)の
バイト範囲だけがOSページキャッシュに乗る。過去記事(swiftlm-m1max-hands-on)で
`ssd_stream=true`なのにSSD I/Oが発火せずmmap+page cacheで足りていた、という
発見はこの仕組みと整合する。

この性質を利用して、2条件を同一モデル・同一プロセス内で比較する。

- **条件A(ベースライン)**: 素のgenerate。ページキャッシュは実行時のアクセス順にしか
  乗らない。初回アクセスのエキスパートは必ずディスクI/O(またはコールドmmap fault)を
  伴う。過去記事で見た「mmap+page cacheがLRU相当として自然に働く」状態そのもの。
- **条件B(観測ベースの事前ウォームアップ)**: router_hook.pyのログ(runs/*.json)から
  判明したホットエキスパート上位Nをgenerate前にダミー入力で1回`gather_qmm`させ、
  該当ページを先にページキャッシュへ乗せておいてから同じプロンプトを生成する。

同一プロンプト・同一max_tokensでgeneration tok/sを比較する。差が出れば「事前の
observabilityがコールドスタートのレイテンシを短縮できる」という主張の裏付けになる。
差が出ない/誤差の範囲なら、「Apple Siliconのmmap+page cacheは十分賢く、事前観測の
価値が薄い」という結論になる。どちらの結果でも記事にできる設計。

## 未解決の懸念(実行前に検討が必要)

- ウォームアップの「ダミー入力」がgather_qmmの実装上、本当に対象expertの重み全体を
  読みに行くか未確認。SIMD/タイルの都合で部分的にしか触れない可能性がある
- mx.eval()の後、対象データが本当にOSページキャッシュに残り続ける保証はない
  (macOSのメモリ圧迫時にpage cacheは容赦なく解放される)。条件Aとの計測の間隔が
  空くとウォームアップの効果が消えている可能性がある。同一プロセス内で直後に測る設計
  にしているのはこのため
- 対象は決め打ちで「router_hook.pyの5プロンプトの集計で最頻出のexpert」にしているが、
  条件Bで生成するプロンプトが条件Aと同じでない場合、ウォームアップしたexpert集合が
  実際のアクセスパターンとズレる可能性がある。今回は同一プロンプトで測るので影響は
  小さいはずだが、汎化性の主張はできない
"""
import argparse
import json
import time
from collections import Counter

import mlx.core as mx
import mlx_lm
from mlx_lm.models.qwen3_next import Qwen3NextSparseMoeBlock

# 2026-08-06早朝の教訓: 122B-A10B-4bitはこのM1 Max 64GB機でMetalのOOM例外を
# 出して動かなかった(router_hook.py参照)。デフォルトを35B-A3Bに変更した。
DEFAULT_MODEL_ID = "unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit"

PROMPTS = {
    "bst": "Pythonで、二分探索木に値を挿入する関数 insert(root, val) を書いて。短く。",
    "bbs": "簡易BBS、投稿だけ、localStorage、日本語UI、単一HTMLファイル",
    "kana_intro": (
        "あなたは『かなちゃん』というキャラ。中性的でやや女性寄り、一人称は『わたし』。"
        "口調はやわらかく、語尾に『〜だよ』『〜かな』を時々使う。おたくでゲームとAIが好き。"
        "自己紹介して。"
    ),
    "math": "フィボナッチ数列の第100項を、行列累乗を使って高速に求める方法を説明して。",
    "cn": "请用中文简要介绍一下你自己，并说明你能帮助完成哪些任务。",
}


def load_hot_experts(router_log_path, top_n):
    """router_hook.pyの出力から層ごとの上位N expert indexを取り出す"""
    with open(router_log_path) as f:
        data = json.load(f)

    # 全プロンプトのper_layer_expert_countsを合算してから上位Nを取る
    merged = {}
    for prompt_result in data.values():
        for layer_str, counts in prompt_result["per_layer_expert_counts"].items():
            layer = int(layer_str)
            merged.setdefault(layer, Counter())
            for expert_idx, cnt in counts:
                merged[layer][expert_idx] += cnt

    hot = {}
    for layer, counter in merged.items():
        hot[layer] = [idx for idx, _ in counter.most_common(top_n)]
    return hot


def warm_up_layer(moe_block, expert_indices, hidden_size):
    """指定expertの重みをダミー入力でgather_qmmさせ、page cacheへ先読みする"""
    if not expert_indices:
        return
    idx = mx.array(expert_indices, dtype=mx.uint32).reshape(1, 1, -1)
    dummy_x = mx.zeros((1, 1, 1, hidden_size), dtype=mx.bfloat16)
    # SwitchLinear.__call__ / QuantizedSwitchLinear.__call__ は (x, indices, sorted_indices) を取る
    _ = moe_block.switch_mlp.gate_proj(dummy_x, idx, sorted_indices=False)
    mx.eval(_)


def run_generation(model, tokenizer, prompt, max_tokens):
    messages = [{"role": "user", "content": prompt}]
    chat_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    t0 = time.time()
    text = ""
    last_resp = None
    for resp in mlx_lm.stream_generate(model, tokenizer, chat_prompt, max_tokens=max_tokens):
        text += resp.text
        last_resp = resp
    dt = time.time() - t0
    return {
        "text": text,
        "elapsed_sec": dt,
        "generation_tps": last_resp.generation_tps if last_resp else None,
        "prompt_tps": last_resp.prompt_tps if last_resp else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    ap.add_argument("--router-log", required=True, help="router_hook.pyの出力json")
    ap.add_argument("--prompt-key", default="bst", choices=list(PROMPTS.keys()))
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=100)
    ap.add_argument("--out", default="runs/cache_experiment_result.json")
    args = ap.parse_args()
    model_id = args.model

    hot_experts = load_hot_experts(args.router_log, args.top_n)
    print(f"loaded hot experts for {len(hot_experts)} layers from {args.router_log}", flush=True)

    # router_hook.pyでの検証の結論: set_memory_limitは「ガイドライン」で早期の
    # ハード停止ではない。ここでは念のため設定だけしておくが、実効的な安全策としては
    # 期待しない(実測はswapが動かないことで確認する)。
    MEMORY_LIMIT_GB = 20
    prev_limit = mx.set_memory_limit(MEMORY_LIMIT_GB * 1024**3)
    print(f"set MLX memory_limit to {MEMORY_LIMIT_GB}GB (was {prev_limit / 1024**3:.1f}GB)", flush=True)

    print(f"loading {model_id} (lazy=True) ...", flush=True)
    model, tokenizer = mlx_lm.load(model_id, lazy=True)
    hidden_size = model.language_model.args.hidden_size
    print(f"loaded, hidden_size={hidden_size}", flush=True)

    layers = model.language_model.model.layers
    moe_layers = {
        i: layer.mlp
        for i, layer in enumerate(layers)
        if isinstance(layer.mlp, Qwen3NextSparseMoeBlock)
    }

    prompt = PROMPTS[args.prompt_key]

    # 条件A: ベースライン(素のgenerate、ウォームアップなし)
    print("=== condition A: baseline (no warmup) ===", flush=True)
    result_a = run_generation(model, tokenizer, prompt, args.max_tokens)
    print(f"A: {result_a['generation_tps']:.2f} tok/s, {result_a['elapsed_sec']:.1f}s", flush=True)

    # 条件B: 観測ベースの事前ウォームアップ
    print(f"=== condition B: warm-up top-{args.top_n} hot experts per layer ===", flush=True)
    t_warm0 = time.time()
    for layer_idx, expert_ids in hot_experts.items():
        if layer_idx in moe_layers:
            warm_up_layer(moe_layers[layer_idx], expert_ids, hidden_size)
    warm_dt = time.time() - t_warm0
    print(f"warmup took {warm_dt:.2f}s", flush=True)

    result_b = run_generation(model, tokenizer, prompt, args.max_tokens)
    print(f"B: {result_b['generation_tps']:.2f} tok/s, {result_b['elapsed_sec']:.1f}s", flush=True)

    out = {
        "model": model_id,
        "prompt_key": args.prompt_key,
        "top_n": args.top_n,
        "max_tokens": args.max_tokens,
        "warmup_sec": warm_dt,
        "condition_a_baseline": result_a,
        "condition_b_warmed": result_b,
    }
    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
