#!/bin/zsh
# Dev server benchmark: startup time to first HTTP 200, per-page first compile, RSS.
# Usage: ./bench-dev.sh <next-app|astro-app|nuxt-app> <port>
# NOTE: zsh reserves the variable name `path` (tied to PATH) — loop vars below
# deliberately avoid it.
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
APP=$1
PORT=$2

cd $BASE/$APP

case $APP in
  next-app) CMD=(pnpm exec next dev -p $PORT) ;;
  astro-app) CMD=(pnpm exec astro dev --port $PORT) ;;
  nuxt-app) CMD=(pnpm exec nuxt dev --port $PORT) ;;
esac

START=$(python3 -c 'import time; print(time.time())')
"${CMD[@]}" > $BASE/log-$APP-dev.txt 2>&1 &
DEVPID=$!

READY=""
for i in {1..300}; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:$PORT/ 2>/dev/null)
  if [ "$code" = "200" ]; then
    READY=$(python3 -c 'import time; print(time.time())')
    break
  fi
  sleep 0.2
done

if [ -z "$READY" ]; then
  echo "$APP dev: FAILED to become ready"
else
  echo "$APP dev first-200: $(printf '%.1f' $(($READY - $START)))s"
fi

for pg in /posts/hello-benchmark /posts/build-cache /posts/client-js-weight; do
  t=$(curl -s -o /dev/null -w '%{time_total}' http://localhost:$PORT$pg)
  echo "$APP dev $pg: ${t}s"
done
t=$(curl -s -o /dev/null -w '%{time_total}' http://localhost:$PORT/)
echo "$APP dev / (second hit): ${t}s"

sleep 3
# RSS of the dev server process tree. Some tools exec in place (single PID),
# others spawn workers — cross-check with `ps` if the tree looks too small.
python3 - <<EOF
import subprocess
def children(pid):
    out = subprocess.run(['pgrep','-P',str(pid)],capture_output=True,text=True).stdout.split()
    result = [int(p) for p in out]
    for p in list(result):
        result += children(p)
    return result
pids = [$DEVPID] + children($DEVPID)
total = 0
for p in pids:
    try:
        rss = int(subprocess.run(['ps','-o','rss=','-p',str(p)],capture_output=True,text=True).stdout.strip() or 0)
        total += rss
    except Exception:
        pass
print(f"$APP dev RSS (tree, {len(pids)} procs): {total/1024:.0f} MB")
EOF

pkill -P $DEVPID 2>/dev/null
kill $DEVPID 2>/dev/null
sleep 1
pkill -f "$BASE/$APP" 2>/dev/null
sleep 1
echo "$APP dev: done"
