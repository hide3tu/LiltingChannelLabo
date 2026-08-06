"""
Qwen系MoE(qwen3_5_moe / qwen3_next系アーキ)のルーターをフックして、実プロンプトで
各層・各トークンがどのエキスパートを選んだかを記録するスクリプト。

Qwen3NextSparseMoeBlock.__call__ (mlx_lm/models/qwen3_next.py:327付近) の実装をそのまま複製し、
argpartitionで求めたexpert indices (inds) をログに残す1行だけ足した版。
site-packages自体は書き換えず、モジュールロード後にクラスの__call__を差し替えるモンキーパッチ方式。

2026-08-06早朝の教訓: Qwen3.5-122B-A10B-4bit(65GB)はこのM1 Max 64GB機では
`mlx_lm`の素のgenerate経路で動かない。7回試して7回目にMetal自身が
"Command buffer execution failed: Insufficient Memory"の例外を出して
クリーンに落ちた(システムはフリーズせず、swapも一度も動かなかった)。
デフォルトを、同じM1 Max 64GBで実測済みの35B-A3Bに変更した。

使い方:
    python3 router_hook.py --prompt-set bst,bbs,kana,math,cn --max-tokens 200 --out runs/<name>.json
    python3 router_hook.py --model mlx-community/Qwen3.5-122B-A10B-4bit ...  # 収まらない実測を再現する場合
"""
import argparse
import json
import time
from collections import defaultdict, Counter

import mlx.core as mx
import mlx_lm
from mlx.nn.layers.distributed import sum_gradients
from mlx_lm.models.qwen3_next import Qwen3NextSparseMoeBlock

DEFAULT_MODEL_ID = "unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit"

# 過去記事(swiftlm-m1max-hands-on)と同一プロンプトを含める。速度・出力比較の連続性のため。
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

expert_counts = defaultdict(Counter)  # layer_idx -> Counter(expert_idx -> count)
layer_of = {}  # id(moe_block_instance) -> layer_idx
call_order = []  # 実行順のlayer_idxログ(トークンごとにMoE層を何回通るか確認用)
_pending_inds = []  # 現在処理中トークンぶんの (layer_idx, inds_array) を貯めておく。まだeval済みでない

# 2026-08-06早朝の教訓: 最初の実装は48層×トークンごとに mx.eval(inds) を呼んでいて、
# 空きメモリが52GB→9.8GBまで数秒で急減し、ガードスクリプトにkillされた。
# MLXは遅延評価でグラフ融合・メモリ再利用をするが、ループ内で頻繁にmx.eval()を呼ぶのは
# 既知のアンチパターンで、層間のメモリ再利用を妨げる。
# 対策: indsをその場でevalせず貯めておき、そのトークンの最終MoE層(=最終レイヤー)に到達した
# 時点でまとめて1回だけevalする。48回/トークン→1回/トークンに同期ポイントを削減する。


def build_patched_call(last_moe_layer_idx):
    def patched_call(self, x):
        if self.sharding_group is not None:
            x = sum_gradients(self.sharding_group)(x)

        gates = self.gate(x)
        gates = mx.softmax(gates, axis=-1, precise=True)

        k = self.top_k
        inds = mx.argpartition(gates, kth=-k, axis=-1)[..., -k:]
        scores = mx.take_along_axis(gates, inds, axis=-1)
        if self.norm_topk_prob:
            scores = scores / scores.sum(axis=-1, keepdims=True)

        # --- ここだけ追加: 選ばれたエキスパートindexを記録(evalは最終層まで遅延) ---
        layer_idx = layer_of.get(id(self))
        if layer_idx is not None:
            _pending_inds.append((layer_idx, inds))
            call_order.append(layer_idx)
            if layer_idx == last_moe_layer_idx:
                arrays = [a for _, a in _pending_inds]
                mx.eval(*arrays)
                for li, arr in _pending_inds:
                    expert_counts[li].update(arr.reshape(-1).tolist())
                _pending_inds.clear()
                # MLX自身が報告する内部メモリ使用量をトークンごとに出す。外部vm_stat
                # だけでは「何が起きているか」が見えなかった(20GB上限にしても
                # 挙動が変わらなかった)ため、MLX側の実測値で切り分ける
                active_gb = mx.get_active_memory() / 1024**3
                peak_gb = mx.get_peak_memory() / 1024**3
                cache_gb = mx.get_cache_memory() / 1024**3
                print(f"  [mlx mem] active={active_gb:.2f}GB peak={peak_gb:.2f}GB cache={cache_gb:.2f}GB", flush=True)
        # --- ここまで ---

        y = self.switch_mlp(x, inds)
        y = (y * scores[..., None]).sum(axis=-2)

        shared_y = self.shared_expert(x)
        shared_y = mx.sigmoid(self.shared_expert_gate(x)) * shared_y

        y = y + shared_y

        if self.sharding_group is not None:
            y = mx.distributed.all_sum(y, group=self.sharding_group)

        return y

    return patched_call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL_ID)
    ap.add_argument("--prompt-set", default="bst,bbs,kana_intro,math,cn")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    model_id = args.model

    # 2026-08-06早朝の教訓その2: lazy=Trueにしても、生成のprefill 1回でMLXが
    # 数秒のうちに数十GBを消費する。mx.device_info()で確認したところ、この機体
    # (M1 Max 64GB)でMLXのデフォルトmemory_limitは約77.7GB
    # (max_recommended_working_set_size 51.8GBの1.5倍)で、物理メモリ64GBを
    # 上回っていた。つまりMLX自身のブレーキが物理RAMより先に効かない状態だった。
    # 外部shellの2秒間隔ポーリング監視では検知が間に合わなかった(1回目は空きメモリ
    # 9.8GBで検知、2回目はeval頻度を減らしたのに悪化して61MBまで落ちてから検知)。
    # ここでMLXに明示的にハード上限を設定し、超えたら例外を吐かせて安全に止める。
    # 40GBだと4回試して4回ともガードにkillされた(空きメモリが33GB→14.4GB、
    # 25GB→61MBまで急減)。swap使用量は4回とも完全に不変(3722MB固定)だったため
    # 実際のOOM危険ではなくmmap+page cache成長の範囲内だった可能性が高いが、
    # 安全側に倒して上限をさらに下げる。A10Bのsparsity(122B中10Bだけ活性)を
    # 踏まえれば20GBでも理論上は足りるはず。
    # 訂正(2026-08-06早朝5回目後): 40GB→20GBに下げても空きメモリの落ち方は
    # 変わらなかった(どちらも58〜61MBまで落ちた)。ドキュメントを読み直すと
    # set_memory_limitは「ガイドライン」であって早期のハード停止ではなく、
    # 実際にRAM+swapが尽きた時だけ例外を出す仕様だった。値を下げても無意味
    # だったので、以降は診断目的(get_active_memory等)で実測値を見て判断する。
    MEMORY_LIMIT_GB = 20
    prev_limit = mx.set_memory_limit(MEMORY_LIMIT_GB * 1024**3)
    print(f"set MLX memory_limit to {MEMORY_LIMIT_GB}GB (was {prev_limit / 1024**3:.1f}GB)", flush=True)

    print(f"loading {model_id} (lazy=True) ...", flush=True)
    t0 = time.time()
    # lazy=True必須。デフォルト(lazy=False)だとload()内でmx.eval(model.parameters())が
    # 走り、量子化重み全部を即座に強制評価する。実機64GB統合メモリでこれをやると
    # 起動直後にswap thrashingでシステムごと固まる(2026-08-06早朝に実際に踏んだ)。
    model, tokenizer = mlx_lm.load(model_id, lazy=True)
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    print(f"  [mlx mem after load] active={mx.get_active_memory()/1024**3:.2f}GB "
          f"peak={mx.get_peak_memory()/1024**3:.2f}GB cache={mx.get_cache_memory()/1024**3:.2f}GB", flush=True)

    layers = model.language_model.model.layers
    moe_layer_idx = []
    for i, layer in enumerate(layers):
        if isinstance(layer.mlp, Qwen3NextSparseMoeBlock):
            layer_of[id(layer.mlp)] = i
            moe_layer_idx.append(i)
    print(f"MoE layers: {len(moe_layer_idx)} / {len(layers)} total -> {moe_layer_idx}", flush=True)

    last_moe_layer_idx = max(moe_layer_idx)
    Qwen3NextSparseMoeBlock.__call__ = build_patched_call(last_moe_layer_idx)

    names = args.prompt_set.split(",")
    results = {}
    for name in names:
        prompt = PROMPTS[name]
        expert_counts.clear()
        call_order.clear()
        _pending_inds.clear()
        messages = [{"role": "user", "content": prompt}]
        chat_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)

        t0 = time.time()
        text = ""
        for resp in mlx_lm.stream_generate(model, tokenizer, chat_prompt, max_tokens=args.max_tokens):
            text += resp.text
        dt = time.time() - t0

        per_layer = {
            str(layer): counter.most_common()
            for layer, counter in expert_counts.items()
        }
        results[name] = {
            "prompt": prompt,
            "output": text,
            "elapsed_sec": dt,
            "moe_calls": len(call_order),
            "per_layer_expert_counts": per_layer,
        }
        n_unique = {layer: len(c) for layer, c in expert_counts.items()}
        print(f"[{name}] {dt:.1f}s, moe_calls={len(call_order)}, unique experts/layer(avg)="
              f"{sum(n_unique.values()) / max(len(n_unique), 1):.1f}", flush=True)

    out_path = args.out or f"runs/{'-'.join(names)}.json"
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
