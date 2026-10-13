#!/usr/bin/env python3
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--name', required=True)
ap.add_argument('--model', required=True)
ap.add_argument('--timeout', type=int, default=600)
args = ap.parse_args()
fixture = BASE / 'fixtures/catalog'
(BASE / 'runs').mkdir(exist_ok=True)
workspace = BASE / 'runs' / args.name
shutil.copytree(fixture, workspace)
print(f'START {args.name}', flush=True)
completed = subprocess.run([sys.executable, str(BASE / 'run_dsh.py'),
                           '--name', args.name, '--model', args.model,
                           '--workspace', str(workspace), '--prompt', str(BASE / 'task.txt'),
                           '--timeout', str(args.timeout)])
logdir = BASE / 'logs' / args.name
if not (logdir / 'result.json').exists():
    raise SystemExit(completed.returncode or 1)
result = json.loads((logdir / 'result.json').read_text())
test_run = subprocess.run(['node', '--test', '--test-reporter=tap'], cwd=workspace,
                          capture_output=True, text=True)
(logdir / 'verification.tap').write_text(test_run.stdout + test_run.stderr)
holdout = subprocess.run(['node', str(BASE / 'heldout.mjs'), str(workspace / 'src/catalog.js')],
                         capture_output=True, text=True)
(logdir / 'heldout.jsonl').write_text(holdout.stdout + holdout.stderr)
changed = []
diffs = []
for file in sorted(fixture.rglob('*')):
    if not file.is_file():
        continue
    rel = file.relative_to(fixture)
    after = workspace / rel
    if not after.exists() or after.read_bytes() != file.read_bytes():
        changed.append(str(rel))
        diffs.extend(difflib.unified_diff(file.read_text().splitlines(keepends=True),
                                        after.read_text().splitlines(keepends=True) if after.exists() else [],
                                        fromfile='before/' + str(rel), tofile='after/' + str(rel)))
added = [str(p.relative_to(workspace)) for p in workspace.rglob('*')
         if p.is_file() and not (fixture / p.relative_to(workspace)).exists()]
(logdir / 'changes.diff').write_text(''.join(diffs))
events = []
for line in (logdir / 'events.jsonl').read_text().splitlines():
    try:
        events.append(json.loads(line))
    except json.JSONDecodeError:
        pass
steps = [e for e in events if e.get('type') == 'status' and e.get('phase') == 'step_end']
calls = [e for e in events if e.get('type') == 'tool_call']
usage = {k: sum(e.get('usage', {}).get(k, 0) for e in steps)
         for k in ['inputTokens', 'outputTokens', 'totalTokens']}
summary = {'run': args.name, 'testsExitCode': test_run.returncode,
           'heldoutExitCode': holdout.returncode,
           'existingFilesChanged': changed, 'filesAdded': added,
           'protectedFilesUnchanged': all(p not in changed for p in ['README.md', 'package.json', 'test/catalog.test.js']),
           'steps': len(steps), 'toolCalls': len(calls), 'usage': usage,
           'testsSummary': [line for line in test_run.stdout.splitlines()
                            if line.startswith(('# tests', '# pass', '# fail'))],
           'heldoutSummary': holdout.stdout.splitlines()[-1] if holdout.stdout else '',
           'finalAnswer': next((e for e in reversed(events) if e.get('type') == 'final'), None)}
(logdir / 'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({**result, **summary}, ensure_ascii=False, indent=2), flush=True)
