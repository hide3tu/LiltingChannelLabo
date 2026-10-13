# DeepSeek Harness with Qwen and DeepSeek on ModelScope

DSH 0.2.0-rc.2をM4 Mac miniで動かし、ModelScopeのQwen／DeepSeek APIに、意図的な不具合を含む小さなJavaScriptプログラムを修正させた実験。

記事: [日本語](https://www.lilting.ch/articles/deepseek-harness-dsh) / [English](https://www.lilting.ch/en/articles/deepseek-harness-dsh)

実行日は2026年10月13日（JST）。ディレクトリの日付はブログ記事に指定された公開日に合わせている。

## 課題

`fixtures/catalog/`は記事メタデータから公開用一覧を作る合成課題で、本番コードの障害ではない。

| 不具合 | 期待する処理 |
|---|---|
| 公開日時と現在時刻が一致すると除外される | 同時刻も含める |
| 日時文字列をそのまま比較している | タイムゾーンを含む実時刻で降順にする |
| Windowsのパス区切りに対応していない | `/`と`\`の両方からファイル名を取り出す |

渡すテストは9件。初期状態では6件成功・3件失敗する。`heldout.mjs`の追加3件は作業フォルダーへコピーせず、エージェント終了後に評価側で実行した。初期状態では追加3件すべて失敗する。

`reference/catalog.js`は陽性対照として人間側で用意した修正例。既存9件と追加3件をすべて通過する。エージェントの作業フォルダーにはコピーしない。

## 再実行

Node.js 22.19.0以降の22系または24以降、Python 3、利用可能なModelScope APIキーが必要。`ps -axo pid,ppid,rss`によるメモリ採取はmacOS/Linux向け。

```sh
npm ci --prefix runtime
export MODELSCOPE_API_KEY='利用するキー'

python3 run_trial.py \
  --name qwen-local-1 \
  --model Qwen-Ambassador/Qwen3.8-Flash-Next

python3 run_trial.py \
  --name deepseek-local-1 \
  --model deepseek-ai/DeepSeek-V4.1-Flash
```

`Qwen-Ambassador/`のモデルはアンバサダー向けの利用権が必要。一般アカウントでは、そのキーで利用可能なモデルIDに変更する。`MODELSCOPE_API_KEY`が未設定の場合のみ、既存の`~/.qwen/auth.json`にある`qwen-ambassador.key`を使用する。

各回で`--name`を変える。既存の実行を上書きせず、新しいコピーと新しいDSHセッションを作る。APIリクエストを逐次実行し、同時に複数の試行を走らせない。

`run_trial.py`は次の処理を行う。

1. `fixtures/catalog/`を`runs/<name>/`にコピーする。
2. `task.txt`の共通プロンプトをDSHのheadlessプロファイルへ送る。
3. DSHが終了したら、評価側で既存テストと追加テストを再実行する。
4. 入力ファイルとの差分を取り、README・package.json・テストが変わっていないか確かめる。

APIキーはDSHプロセスの環境変数へ渡し、設定ファイルや結果ファイルには保存しない。

## 接続条件

| 設定 | 値 |
|---|---|
| API | `https://api-inference.modelscope.ai/v1` |
| プロトコル | `openai-completions` |
| DSHプロファイル | `headless` |
| ツール提示 | `native` |
| 権限 | `workspace-write` |
| API互換設定 | `supportsDeveloperRole: false`、`maxTokensField: max_tokens` |
| 入力コンテキスト上限の設定 | 131,072トークン |
| 一回の出力上限の設定 | 8,192トークン |
| APIの自動再試行 | 0回 |
| 一試行のタイムアウト | 記事の測定は360秒。スクリプト既定は600秒 |

コンテキスト上限と出力上限は、この実験がDSHへ設定した値。モデル全体の仕様を主張する数字ではない。温度・seed・推論強度は指定せず、接続先の既定に任せた。

ブログ側のAGENTS.mdや既存スキルを拾わないよう、`agent-instructions`と`skill-filesystem`を無効にした。OTel送信も無効にしている。設定は各回の`logs/<name>/model.patch.yml`に保存する。

## 記録

- `events.jsonl`: DSHのheadlessイベント列。
- `result.json`: 起動から終了までの時間、終了コード、RSSサンプルの最大値。
- `verification.tap`: 評価側が再実行した9件のテスト。
- `heldout.jsonl`: 評価側の追加3件。
- `verification.json`: テストの合否、ファイル変更、モデル／ツール呼び出し回数、トークン累計。
- `changes.diff`: 初期実装との差分。

RSSは0.5秒ごとにDSHプロセスと子プロセスの値を足した観測値。共有ページの重複を除いておらず、物理メモリ消費量の厳密な測定ではない。モデルの推論はModelScope側なので、この値にモデルの重みは含まれない。

トークン数はDSHの各`step_end.usage`の合計。過去の履歴が再び送られる分を含み、キャッシュ控除後の課金トークン数や料金を示すものではない。

この課題には既知の正解と失敗テストを用意している。大規模な開発作業や未知の不具合に対する性能を測るベンチマークではない。
