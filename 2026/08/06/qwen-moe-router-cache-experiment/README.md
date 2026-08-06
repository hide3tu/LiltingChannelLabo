# QwenのMoEルーター観測と観測ベースキャッシュの対照実験

Qwen3系MoE（`qwen3_5_moe`アーキ、`Qwen3NextSparseMoeBlock`を共有）のルーターをモンキーパッチして層ごとのエキスパート選択を実測し、観測ベースの事前ウォームアップと素の`mlx_lm.stream_generate`のtok/sを比較したときのソース一式。M1 Max 64GB unified memoryで計測。

記事: [日本語](https://www.lilting.ch/articles/qwen-moe-router-cache-experiment)

## 構成

| パス | 内容 |
|---|---|
| `router_hook.py` | `Qwen3NextSparseMoeBlock.__call__`をモンキーパッチし、層・トークンごとに選ばれたexpert indexを記録する |
| `cache_experiment.py` | `router_hook.py`のログから層ごとの上位Nホットエキスパートを取り出し、事前ウォームアップあり/なしのgeneration tok/sを比較する |
| `guarded_run.sh` | モデルロード・生成をバックグラウンドで走らせつつswap使用量を監視し、危険域で強制終了する安全ラッパー |

## 実行

```sh
# ルーター観測（5プロンプト、layer別のexpert選択回数をJSONへ）
python3 router_hook.py --prompt-set bst,bbs,kana_intro,math,cn --max-tokens 150 --out runs/full_sweep.json

# 観測ログを使った対照実験（条件A: 素の生成、条件B: 上位20エキスパートを事前ウォームアップ）
python3 cache_experiment.py --router-log runs/full_sweep.json --prompt-key bst --top-n 20 --max-tokens 100

# 安全に実行したい場合（推奨）
./guarded_run.sh /tmp/run.log -- python3 router_hook.py --prompt-set bst --max-tokens 150 --out runs/full_sweep.json
```

デフォルトの対象モデルは`unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit`（`--model`で上書き可能）。65GB級の`mlx-community/Qwen3.5-122B-A10B-4bit`をこのスクリプトで直接動かそうとすると、この機体ではMetalが`Insufficient Memory`例外を出して落ちる。

`guarded_run.sh`はswap使用量の増加のみを危険シグナルにしている。空きメモリ（`vm_stat`の`Pages free`）はmmapされた大きいモデルファイルの正常なページキャッシュ成長でも大きく変動するノイズの多い指標で、危険域の判定には向かない。

計測値は環境依存。記事の数字は2026-08-06にこの環境・このモデルバージョンで取ったもので、このディレクトリは更新しない。
