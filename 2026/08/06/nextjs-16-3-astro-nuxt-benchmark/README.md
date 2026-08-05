# Next.js 16.3 / Astro 7 / Nuxt 4.5 同一デザイン実測比較

同じデザインのミニブログをNext.js 16.3.0、Astro 7.1.6、Nuxt 4.5.1で1つずつ実装し、ビルド時間・開発サーバー・ページ転送量をM4 Mac mini（16GB、Node.js 25.3.0、pnpm 10.27.0）で計測したときのソース一式。

記事: [日本語](https://www.lilting.ch/articles/nextjs-16-3-astro-nuxt-benchmark) / [English](https://www.lilting.ch/en/articles/nextjs-16-3-astro-nuxt-benchmark)

## 構成

| パス | 内容 |
|---|---|
| `next-app/` | Next.js 16.3.0（App Router、JSX） |
| `astro-app/` | Astro 7.1.6 |
| `nuxt-app/` | Nuxt 4.5.1（app/ディレクトリ構成） |
| `shared/` | 3実装で共有した原本（style.css と posts.json） |
| `bench-build.sh` | コールド/ウォームのビルド時間計測 |
| `bench-dev.sh` | 開発サーバーの起動時間・ページ初回コンパイル・RSS計測 |
| `bench-weight.sh` | 本番ページのHTML/JS/CSS転送量（raw/gzip）計測 |

3実装はHTML構造を手書きで揃え、CSSと記事データのJSONはバイト単位で同一。`shared/` の2ファイルを各実装へコピーして使っている。

`next-app/AGENTS.md` と `next-app/CLAUDE.md` は書いたものではなく、Next.js 16.3の `next dev` がAIエージェント環境を検出して自動生成したファイルをそのまま残したもの。

## 実行

```sh
pnpm --dir next-app install && pnpm --dir astro-app install && pnpm --dir nuxt-app install

./bench-build.sh next-app        # astro-app / nuxt-app も同様
./bench-dev.sh next-app 3101
pnpm --dir next-app run build && ./bench-weight.sh next-app 3111
```

1行変更の差分ビルドは、任意のページソースを1文字変えて `pnpm --dir <app> run build` を手で計るだけなのでスクリプト化していない。

計測値は環境依存。記事の数字は2026-08-05にこのバージョン固定で取ったもので、このディレクトリは更新しない。
