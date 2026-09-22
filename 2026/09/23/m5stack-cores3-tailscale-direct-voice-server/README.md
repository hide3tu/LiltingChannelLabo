# CoreS3からTailscale経由でWAVを取得する最小構成

ESP-IDF 6.0の独立プロジェクト。Wi-Fi接続、時刻同期、Tailscaleへの参加、
音声サーバーのWAV取得を順に行う。画面、マイク、スピーカー、SDは使わない。
既存のArduino用コードへの統合前に、通信だけを実機で確認する。

記事: [日本語](https://lilting.ch/articles/m5stack-cores3-tailscale-direct-voice-server) / [English](https://lilting.ch/en/articles/m5stack-cores3-tailscale-direct-voice-server)

`components/` の出典と固定コミットは [UPSTREAM.md](UPSTREAM.md) に記録した。

## 接続設定

このフォルダーで `config.example.h` を `config.h` へコピーし、Wi-Fi設定と接続先を編集する。
設定例の `100.64.0.1` は仮の値なので、自分のサーバーのTailscale IPv4へ変更する。
すでに設定済みの `config.h` がある場合はコピーせず、そのファイルを編集する。

```powershell
Copy-Item config.example.h config.h
```

`config.h` とビルド成果物はGitの対象外。
Tailscaleの認証キーが空なら、USBシリアルに出る端末承認URLをブラウザで開き、
音声サーバーと同じtailnetへ登録する。承認URLや認証キーは記事に載せない。

接続先は `PROBE_SERVER_BASE`、音声のパスは `PROBE_WAV_PATH` で指定する。
音声ファイルのパスの例は `/filler/filler_0.wav`。接続先に存在するWAVを指定する。
音声サーバー側でCoreS3からTCP 8357への接続が許可されている必要がある。

現在の最小構成では `CONFIG_TAILSCALE_DERP_ONLY=y` と
`CONFIG_TAILSCALE_PREFERRED_DERP_REGION=7` を設定し、東京のDERP中継を使う。
VPSのPHP中継は不要だが、UDPで端末間を直接接続する構成ではない。
取り込んだ実装はDERP接続を1本だけ持つため、接続先の音声サーバーが使う
DERPリージョンに合わせている。別の環境で使う場合はこの設定も確認する。

## ビルド

Docker DesktopのLinuxエンジンを起動して実行する。

```powershell
.\build.ps1
```

使用イメージは `espressif/idf:v6.0`。ネイティブESP-IDF 6.0環境がある場合は
このディレクトリで `idf.py build` でもビルドできる。

## 実機への書き込み

CoreS3本体のUSB-C端子を接続し、ポートとESP32-S3であることを確認する。
先に16MiBフラッシュ全体をバックアップし、その後で `build/flash_args` にある
アドレスへブートローダー、パーティション表、アプリを書き込む。
Windowsではコンテナ内からUSBへ書き込まず、ホスト側のesptoolを使う。

ホスト側のツールは `python -m pip install -r requirements-tools.txt` で用意できる。
通常の `read-flash` が止まる場合は、esptool 5.3.0を入れたPython環境で
`backup_rom.py --chip esp32s3 --port COM3 --baud 921600 --no-stub read-flash 0 0x1000000 <バックアップ先>`
を実行する。64KiBごとにデバイス側のMD5を確認し、消去状態と一致するブロックは
0xffで復元する。それ以外はROM経由で実データを読み、各ブロックと最後の16MiB全体の
MD5がデバイス側と一致した場合だけファイルを保存する。

ESP-IDF 6.0が生成するesptool 5系向けコマンド:

```powershell
esptool --chip esp32s3 --port COM3 --baud 921600 --no-stub write-flash --flash-mode dio --flash-size 16MB --flash-freq 80m 0x0 build/bootloader/bootloader.bin 0x8000 build/partition_table/partition-table.bin 0x10000 build/cores3_tailscale_probe.bin
python monitor.py COM3 --seconds 600
```

COM番号は接続時の値へ変更する。書き込み中はシリアルモニターを閉じておく。
通常のNVS初期化が失敗しても、このアプリはNVSを自動消去しない。

## 成功の判定

`Tailscale IP assigned` はIP割り当てまでの確認。
続いてHTTP 200、WAV全体の受信、RIFF/WAVE識別子とRIFFサイズの一致を確認し、
`PASS: WAV bytes=... time_ms=... rate_KiB_s=...` が出れば通信検証成功。
最大2MiB、1回90秒、最大6回の取得試行に制限している。

データは4KiBずつ受信して破棄するため、WAV全体を置くPSRAMは使わない。
転送前後の内部RAM残量と最小残量も出す。音声再生を含む性能試験ではない。
メイン処理のスタックは16KiB。TLSの送受信は同じミューテックスで保護し、
待機中に片側が通信を止めないよう、接続確立後は非ブロッキングI/Oを使う。
TLSの動的バッファは、受信カウンターのNULL参照が発生したため無効にした。

再起動すると再試行する。Tailscaleの端末鍵はNVSへ保存される。

実測値と未確認項目は [RESULTS.md](RESULTS.md) を参照。
