# Qwen-Image 2.1 × TaylorSeer cache on M1 Max

記事: [JA](https://www.lilting.ch/articles/qwen-image-2-1-taylorseer-cache-m1-max) / [EN](https://www.lilting.ch/en/articles/qwen-image-2-1-taylorseer-cache-m1-max)

DiffusersのTaylorSeerキャッシュをQwen-Image 2.1に入れて、M1 Max 64GBでの生成を約2.7倍にした実験のスクリプト。

| ファイル | 内容 |
|---|---|
| `generate.py` | TaylorSeer Lite＋KVキャッシュで生成する。KVキャッシュとの併用で落ちる問題の回避パッチ入り。`--image` で参照画像つきの編集、`--cache-interval 0` でキャッシュなし |
| `repro_issue_14829.py` | [huggingface/diffusers#14829](https://github.com/huggingface/diffusers/issues/14829) の最小再現。`--workaround` を付けると回避パッチを当てて通る |
| `prompt_from_above.txt` | 記事の俯瞰のプロンプト |

修正は [huggingface/diffusers#14831](https://github.com/huggingface/diffusers/pull/14831) として出している。取り込まれた版のDiffusersでは、`generate.py` のパッチ部分は不要になる。

## 環境

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
  'torch==2.14.0' 'torchvision==0.29.0' 'transformers==5.17.0' 'accelerate==1.15.0' 'pillow==12.3.0' \
  'git+https://github.com/huggingface/diffusers@80c7ed262aeffbeb43ef13ae04baeb9b84515a69'
```

## 実行

```sh
.venv/bin/python generate.py --model Qwen/Qwen-Image-2.1 --prompt-file prompt_from_above.txt --out from-above.png
```

## 実測（M1 Max 64GB、MPS、BF16、832×1216、40ステップ、シード42、各1回）

| ケース | キャッシュなし | TaylorSeer＋KVキャッシュ（間隔3） |
|---|---|---|
| T2I 俯瞰 | 614.7秒 | 218.8秒 |
| 参照画像1枚の編集 | 721.2秒 | 277.6秒 |

モデルはQwen Research License（非商用の研究・評価向け）。
