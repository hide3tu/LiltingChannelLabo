#!/bin/bash
# ガード付き実行ラッパー。指定コマンドをバックグラウンドで走らせつつ2秒おきに
# メモリ/swapを監視し、危険域に入ったら即kill -9する。
#
# 使い方: ./guarded_run.sh <log_path> -- <command...>
#
# 判定はプロセス起動時点のベースラインからの相対値。実機は起動直後でも
# swap使用量が数GBある状態が普通なので、絶対値ではなくベースラインからの
# 増分で判定する(2026-08-06早朝の実測: 空きメモリ約52GB, swap使用3.7GB/5GBが平常時)。
set -uo pipefail

LOG="$1"
shift
if [ "$1" != "--" ]; then
  echo "usage: guarded_run.sh <log_path> -- <command...>" >&2
  exit 2
fi
shift

: > "$LOG"

free_mb() {
  local pages
  pages=$(vm_stat | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
  echo $(( pages * 16384 / 1024 / 1024 ))
}

swap_used_mb() {
  sysctl -n vm.swapusage | sed -E 's/.*used = ([0-9.]+)M.*/\1/' | cut -d. -f1
}

BASE_FREE=$(free_mb)
BASE_SWAP=$(swap_used_mb)
echo "BASELINE free_mb=$BASE_FREE swap_used_mb=$BASE_SWAP" | tee -a "$LOG"

"$@" >> "$LOG" 2>&1 &
PID=$!
echo "STARTED pid=$PID cmd=$*" | tee -a "$LOG"

# 危険域の判定基準
#  2026-08-06早朝、6回連続で試した結果、決定的な切り分けができた。
#  6回目でMLX自身の内部計測(mx.get_active_memory等)をロード直後に見たところ
#  active=0.00GB/peak=0.00GB/cache=0.00GBで、MLXは何も使っていないと申告して
#  いた。にもかかわらずOS側のvm_statの空きメモリは数秒で数十GB吹き飛んで
#  いた。つまりこの「空きメモリの減少」は、mmapされた65GBの安全性テンソル
#  ファイルをOSがpage cacheへ読み込んでいるだけで、MLXの実ワーキングセット
#  とは無関係。読み取り専用ファイルのキャッシュは書き戻しが要らないため
#  swapを経由せず即座に破棄できる。これは6回中6回、swap使用量が完全に不変
#  (3722MB固定)だったことと整合する。
#  結論: 「空きメモリの絶対値」は誤検知の元凶だったので危険判定から外し、
#  唯一6回通じて信頼できた指標である「swapの実増加」だけを危険シグナルにする。
#  空きメモリはHEARTBEATでログには残すが、killのトリガーにはしない。
MAX_ITERS=3600   # 0.5秒間隔で最大1800秒(30分)。長い生成にも耐えるが青天井にはしない
i=0
while [ $i -lt $MAX_ITERS ]; do
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID"
    rc=$?
    echo "FINISHED rc=$rc iter=$i" | tee -a "$LOG"
    exit $rc
  fi

  CUR_FREE=$(free_mb)
  CUR_SWAP=$(swap_used_mb)
  FREE_DROP=$(( BASE_FREE - CUR_FREE ))
  SWAP_GROWTH=$(( CUR_SWAP - BASE_SWAP ))

  if [ $((i % 60)) -eq 0 ]; then
    echo "HEARTBEAT iter=$i free_mb=$CUR_FREE swap_used_mb=$CUR_SWAP free_drop=$FREE_DROP swap_growth=$SWAP_GROWTH" | tee -a "$LOG"
  fi

  # swapが実際に増加(3GB超)したときだけ危険とみなす。空きメモリの絶対値は
  # mmap page cacheの正常な成長で乱高下するノイズの多い指標と判明したため
  # killトリガーから除外した
  if [ "$SWAP_GROWTH" -gt 3000 ]; then
    echo "DANGER free_mb=$CUR_FREE swap_used_mb=$CUR_SWAP free_drop=$FREE_DROP swap_growth=$SWAP_GROWTH -- killing pid=$PID" | tee -a "$LOG"
    kill -9 "$PID" 2>/dev/null
    pkill -9 -P "$PID" 2>/dev/null
    echo "KILLED" | tee -a "$LOG"
    exit 1
  fi

  sleep 0.5
  i=$((i + 1))
done

echo "TIMEOUT iter=$i -- killing pid=$PID as precaution" | tee -a "$LOG"
kill -9 "$PID" 2>/dev/null
pkill -9 -P "$PID" 2>/dev/null
echo "TIMEOUT_KILLED" | tee -a "$LOG"
exit 1
