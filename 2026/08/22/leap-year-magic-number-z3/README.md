# Z3で18bitうるう年判定の定数を合成する

`((y * f) & m) <= t` が0年から499年まで通常のうるう年判定と一致する、18bitの `f`、`m`、`t` をZ3で合成する。

記事: [JA](https://www.lilting.ch/articles/leap-year-magic-number-z3) / [EN](https://www.lilting.ch/en/articles/leap-year-magic-number-z3)

## 実行方法

```sh
uv run --with-requirements requirements.txt python synthesize.py
```

Z3 5.1.0では次の解が得られる。

```text
f = 65623  = 0x10057
m = 197119 = 0x301FF
t = 496    = 0x001F0
```

スクリプトは次の3点も確認する。

- 0年から499年までをPythonの通常判定と全数照合する
- 0、100、200、300、400、500年の積とマスク後の値を表示する
- 0年から500年まで正しい18bit定数は存在しないことをZ3で確認する
