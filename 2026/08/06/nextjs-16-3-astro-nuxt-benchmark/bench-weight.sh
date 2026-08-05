#!/bin/zsh
# Production page weight: start prod server, fetch pages, sum raw/gzip asset bytes.
# Build each app first (pnpm --dir <app> run build).
# Usage: ./bench-weight.sh <next-app|astro-app|nuxt-app> <port>
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
APP=$1
PORT=$2

cd $BASE/$APP
case $APP in
  next-app) pnpm exec next start -p $PORT > $BASE/log-$APP-prod.txt 2>&1 & ;;
  astro-app) pnpm exec astro preview --port $PORT > $BASE/log-$APP-prod.txt 2>&1 & ;;
  nuxt-app) PORT=$PORT node .output/server/index.mjs > $BASE/log-$APP-prod.txt 2>&1 & ;;
esac
SRVPID=$!

for i in {1..100}; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:$PORT/ 2>/dev/null)
  [ "$code" = "200" ] && break
  sleep 0.2
done

python3 - "$APP" "$PORT" <<'EOF'
import re, sys, urllib.request, gzip, io

app, port = sys.argv[1], sys.argv[2]
base = f"http://localhost:{port}"

def fetch(url, encoding=True):
    req = urllib.request.Request(url)
    if encoding:
        req.add_header('Accept-Encoding', 'gzip')
    with urllib.request.urlopen(req) as r:
        data = r.read()
        gz = r.headers.get('Content-Encoding') == 'gzip'
    return data, gz

def gzsize(raw):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=6) as f:
        f.write(raw)
    return len(buf.getvalue())

for path in ['/', '/posts/hello-benchmark']:
    html_raw, was_gz = fetch(base + path)
    html = gzip.decompress(html_raw).decode() if was_gz else html_raw.decode()
    html_bytes = len(html.encode())
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
    inline_scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', html, re.S)
    css_links = re.findall(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"', html)
    js_raw = js_gz = 0
    for s in scripts:
        url = s if s.startswith('http') else base + s
        data, gz = fetch(url)
        raw = gzip.decompress(data) if gz else data
        js_raw += len(raw)
        js_gz += gzsize(raw)
    inline_bytes = sum(len(s.encode()) for s in inline_scripts)
    css_raw = 0
    for c in css_links:
        url = c if c.startswith('http') else base + c
        data, gz = fetch(url)
        raw = gzip.decompress(data) if gz else data
        css_raw += len(raw)
    print(f"{app} {path}: html={html_bytes}B, external_js={len(scripts)} files {js_raw}B raw / {js_gz}B gz, inline_js={inline_bytes}B, css={len(css_links)} files {css_raw}B raw")
EOF

kill $SRVPID 2>/dev/null
pkill -P $SRVPID 2>/dev/null
sleep 1
pkill -f "$BASE/$APP" 2>/dev/null
echo "$APP weight: done"
