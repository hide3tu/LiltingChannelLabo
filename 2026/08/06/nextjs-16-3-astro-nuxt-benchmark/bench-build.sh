#!/bin/zsh
# Build benchmark: cold build -> warm build (no changes), 2 rounds each.
# Usage: ./bench-build.sh <next-app|astro-app|nuxt-app>
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
APP=$1

clean() {
  case $APP in
    next-app) rm -rf $BASE/next-app/.next ;;
    astro-app) rm -rf $BASE/astro-app/dist $BASE/astro-app/.astro $BASE/astro-app/node_modules/.astro $BASE/astro-app/node_modules/.vite ;;
    nuxt-app) rm -rf $BASE/nuxt-app/.nuxt $BASE/nuxt-app/.output $BASE/nuxt-app/node_modules/.cache ;;
  esac
}

run_build() {
  local label=$1
  local start=$(python3 -c 'import time; print(time.time())')
  pnpm --dir $BASE/$APP run build > $BASE/log-$APP-$label.txt 2>&1
  local rc=$?
  local end=$(python3 -c 'import time; print(time.time())')
  echo "$APP $label: $(printf '%.1f' $(($end - $start)))s (rc=$rc)"
}

echo "--- $APP ---"
clean
run_build cold1
run_build warm1
clean
run_build cold2
run_build warm2
