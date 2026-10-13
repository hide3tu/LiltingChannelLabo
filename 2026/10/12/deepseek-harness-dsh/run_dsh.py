#!/usr/bin/env python3
"""Run one DSH task with an isolated home and a ModelScope model.

Credentials stay in the child environment and are never written to result files.
Each named run gets its own logs; existing run names are refused.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parent


def rss_tree_kib(root_pid):
    rows = {}
    for line in subprocess.check_output(['ps', '-axo', 'pid,ppid,rss'], text=True).splitlines()[1:]:
        fields = line.split()
        if len(fields) == 3:
            pid, parent, rss = map(int, fields)
            rows[pid] = (parent, rss)
    found = {root_pid}
    while True:
        more = {pid for pid, (parent, _) in rows.items() if parent in found} - found
        if not more:
            break
        found.update(more)
    return sum(rows[pid][1] for pid in found if pid in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--prompt', type=Path, required=True)
    ap.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args()
    for directory in ['logs', 'home', 'runs']:
        (BASE / directory).mkdir(exist_ok=True)
    logdir = BASE / 'logs' / args.name
    logdir.mkdir(exist_ok=False)
    patch = logdir / 'model.patch.yml'
    patch.write_text(f'''- id: agent-default-model
  config:
    provider: modelscope-experiment
    model: {json.dumps(args.model)}
- id: llm-pi-ai
  config:
    providers:
      modelscope-experiment:
        apiKeyEnv: DSH_EXPERIMENT_API_KEY
        api: openai-completions
        baseURL: https://api-inference.modelscope.ai/v1
        compat:
          supportsDeveloperRole: false
          maxTokensField: max_tokens
        retryPolicy:
          mode: normal
          maxRetries: 0
        models:
          - id: {json.dumps(args.model)}
            contextWindow: 131072
            maxTokens: 8192
- id: agent-instructions
  disabled: true
- id: skill-filesystem
  disabled: true
- id: session-telemetry-otel
  disabled: true
''')
    env = os.environ.copy()
    api_key = env.get('MODELSCOPE_API_KEY')
    if not api_key:
        auth_path = Path.home() / '.qwen/auth.json'
        if auth_path.exists():
            api_key = json.loads(auth_path.read_text()).get('qwen-ambassador', {}).get('key')
    if not api_key:
        raise SystemExit('Set MODELSCOPE_API_KEY before running this experiment.')
    env['DSH_EXPERIMENT_API_KEY'] = api_key
    env['DSH_HOME'] = str(BASE / 'home')
    env['DSH_TELEMETRY_MODE'] = 'DISABLED'
    env['DSH_TOOLS_MODE'] = 'native'
    env['DSH_PERMISSION_MODE'] = 'workspace-write'
    command = ['node', str(BASE / 'runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'),
               '--profile', 'headless', '--patch', str(patch), '--json']
    start_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
    start = time.monotonic()
    peak = 0
    timed_out = False
    prompt = args.prompt.read_text()
    (logdir / 'prompt.txt').write_text(prompt)
    with (logdir / 'events.jsonl').open('w') as stdout, (logdir / 'stderr.txt').open('w') as stderr:
        proc = subprocess.Popen(command, cwd=args.workspace.resolve(), env=env,
                                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                start_new_session=True, text=True)
        proc.stdin.write(prompt)
        proc.stdin.close()
        while proc.poll() is None:
            peak = max(peak, rss_tree_kib(proc.pid))
            if time.monotonic() - start > args.timeout:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(0.5)
        returncode = proc.wait()
    result = {'run': args.name, 'model': args.model, 'startedAt': start_at,
              'wallSeconds': round(time.monotonic() - start, 3),
              'sampledProcessTreePeakRssMiB': round(peak / 1024, 2),
              'samplingIntervalSeconds': 0.5, 'exitCode': returncode,
              'timedOut': timed_out, 'workspace': str(args.workspace.resolve()),
              'dshVersion': '0.2.0-rc.2', 'toolsMode': 'native',
              'permissionMode': 'workspace-write'}
    (logdir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with (BASE / 'logs/results.jsonl').open('a') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
