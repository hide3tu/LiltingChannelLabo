# Qwen-Image 2.1の部分編集と位置ずれの測定

記事: [JA](https://www.lilting.ch/articles/qwen-image-2-1-edit-pixel-perfect-output-resolution) / [EN](https://www.lilting.ch/en/articles/qwen-image-2-1-edit-pixel-perfect-output-resolution)

Diffusersの `QwenImage21Pipeline` は参照画像を約1MP・32の倍数の寸法へリサイズする。832×1216の画像は832×1248になり、出力と格子が合わなくなる。`output_resolution=round(sqrt(W*H))`（832×1216なら1006）を渡すとリサイズが何もしなくなり、位置ずれが0.1px以下になった。

| ファイル | 内容 |
|---|---|
| `measure_edit.py` | 元画像と出力のずれ（エッジマップの位相相関、全体と3×3ブロック）と、変化画素率（顔の枠の内外）を出す。差分ヒートマップとエッジの重ね合わせ画像も保存する |
| `prompts/` | 記事で使った編集の指示 |

生成は [TaylorSeerの記事のディレクトリ](../qwen-image-2-1-taylorseer-cache-m1-max/) の `generate.py` を使う。

```sh
python ../qwen-image-2-1-taylorseer-cache-m1-max/generate.py --model Qwen/Qwen-Image-2.1 \
  --prompt-file prompts/edit-smile-min.txt --image source.png \
  --width 832 --height 1216 --output-resolution 1006 --out smile.png
python measure_edit.py source.png smile.png
```

`measure_edit.py` の `FACE_BOXES` は記事の元画像（832×1216、2人の立ち絵）用の座標。別の画像で使うときは書き換える。
