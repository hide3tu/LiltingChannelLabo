# WordPress MCP AdapterからQwenに記事を要約させる

2026年10月13日にM4 Mac miniで実施したローカル実験。記事の公開日指定に合わせて `2026/10/05/` に置いている。

MCP AdapterはWordPressのAbilityをMCPクライアントから呼べるようにするプラグイン。この実験では、Abilityの中からModelScopeのQwen APIを呼び、結果を別のAbilityで下書きとして保存する。AIエージェント役もQwenで、Pythonがそのツール呼び出しをMCPへ中継する。

## 構成

| 部品 | 実測バージョン・用途 |
|---|---|
| WordPress | 7.1.3 / PHP 8.3.35 |
| MCP Adapter | 0.7.0 |
| MariaDB | 11.4.13 |
| WP-CLI | 2.12.0 |
| Qwen | `Qwen-Ambassador/Qwen3.8-Flash-Next` |
| API | `https://api-inference.modelscope.ai/v1/chat/completions` |
| MCP | `http://localhost:8889/wp-json/mcp/mcp-adapter-default-server` |

WordPress AI Clientは使っていない。実験プラグインの `wp_remote_post()` が直接AI APIを呼ぶ。DockerイメージはCompose内でダイジェストを固定している。

## 起動

Docker DesktopなどのDocker環境、Docker Compose v2、Python 3.9以降が必要。Docker APIが応答する状態で実行する。初回にWordPressとAdapterをダウンロードする。

```bash
# このREADMEがあるディレクトリで実行する
export MODELSCOPE_API_KEY='利用可能なModelScope APIキー'
python3 lab.py prepare
python3 lab.py start
python3 lab.py smoke --with-ai
python3 lab.py agent
python3 lab.py negative
```

`MODELSCOPE_API_KEY` が未設定の場合だけ、既存の `~/.qwen/auth.json` にある `qwen-ambassador.key` を使う。キーは標準出力や実験結果へ出さない。

既定の `Qwen-Ambassador/` モデルには対応する利用権が必要。一般のModelScopeアカウントでは利用可能なモデルIDに置き換える。エージェント側のモデルはツール呼び出し対応が必要。

```bash
python3 lab.py prepare --model '利用可能なモデルID'
python3 lab.py start
python3 lab.py agent --model '利用可能なモデルID'
```

資材は既定で `.runtime/` に置く。別の場所に置く場合は `prepare --work-dir /absolute/path` を指定する。`.env` と `.runtime/` はgitignore対象。APIキーなどの秘密ファイルは親ディレクトリを0700にして保持し、必要なファイルだけコンテナへ読み取り専用で渡す。

Docker上のDBとWordPress本体は、このComposeプロジェクト専用の名前付きボリュームに保存する。公開ポートは `127.0.0.1:8889` のみ。ポートを変える場合は最初の `prepare` に `--port` を指定する。既存DBを使う再実行でURLは自動変更しない。

管理画面は `http://localhost:8889/wp-admin/`。ユーザー名は `labo_admin`、自動生成したパスワードは作業ディレクトリの `private/credentials.json` にある。MCP用のApplication Passwordは `private/connection.json` に保存される。これらを公開リポジトリへ入れない。

日本語表示にする場合は次を追加する。

```bash
docker compose run --rm -T cli language core install ja
docker compose run --rm -T cli option update WPLANG ja
```

## 実験用Ability

| 名前 | 処理 |
|---|---|
| `labo/get-post` | `_labo_fixture=1` のダミー記事だけを取得 |
| `labo/summarize-post` | WordPressからQwen APIへ本文を送り、要約と `summary_id` を返す |
| `labo/save-summary-draft` | 同じユーザーが生成した有効な `summary_id` を指定し、下書きを保存 |

要約は15分間だけ一時保存される。保存時にAIを再呼び出ししない。同じ `summary_id` を逐次再送した場合は既存の下書きを返すが、並行実行時の重複防止は検証していない。

AIが操作する `labo_agent` ロールには `read` と `edit_posts` だけを付けている。投稿を公開する権限は付けず、保存処理も `draft` 固定。比較用の `labo_reader` はsubscriberで、要約の実行は拒否される。Application PasswordによるHTTP認証をローカル環境で使うため、`WP_ENVIRONMENT_TYPE=local` を設定している。

## 記録

| ファイル | 内容 |
|---|---|
| `results/versions.json` | 実行した環境のバージョン |
| `results/tools.json` / `discovery.json` | MCPツール一覧とAbility一覧 |
| `results/smoke.jsonl` | 手動のMCP呼び出しと結果。最初の失敗も含む |
| `results/direct-summary.json` | WordPress側のAI呼び出し単独の結果 |
| `results/agent.jsonl` | AIへの指示、ツールの選択、最終応答 |
| `results/agent-mcp.jsonl` | エージェントが使ったMCP通信 |
| `results/agent-summary.json` | 所要時間とツール呼び出し回数 |
| `results/negative-summary.json` | 拒否・API失敗時の結果 |
| `results/verification.json` | 投稿状態と元記事本文のハッシュ照合 |
| `results/resources.json` | 実行後に取得したコンテナメモリの瞬間値。ピークではない |

実行結果は各コマンドで追記または上書きされる。保存済みの結果と比較する再実行は、このディレクトリを別の場所へコピーして行う。

今回の自然文からの実行は1回。7回のMCPツール呼び出しで25.603秒、WordPress内の要約API呼び出しは4.39秒だった。元記事のハッシュは入力ファイルと一致し、生成物は投稿ID5、状態は `draft`。速度の平均や性能比較を示す実験ではない。

`negative` は未認証、subscriberの権限不足、不正な投稿ID、無効なAIモデルID、存在しない要約IDを試す。無効なモデルIDのテストは実際のAI APIに1回リクエストする。失敗を確認した後はモデル指定を元に戻す。前後で下書きが増えないことも確認する。

## 終了

```bash
docker compose stop wordpress db
```

再開は `docker compose start db wordpress`。停止ではDBと下書きを消さない。

## 参照

- [MCP Adapter 0.7.0](https://github.com/WordPress/mcp-adapter/releases/tag/v0.7.0)
- [0.7.0のDefault MCP Server](https://github.com/WordPress/mcp-adapter/blob/v0.7.0/docs/guides/default-server.md)
- [0.7.0のCreating Abilities](https://github.com/WordPress/mcp-adapter/blob/v0.7.0/docs/guides/creating-abilities.md)
- [WordPress HTTP API](https://developer.wordpress.org/reference/functions/wp_remote_post/)
