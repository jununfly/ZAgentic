#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import re
import sys

ROOT = Path('.')
ACTIVE_BUCKETS = ['engineering', 'productivity', 'misc', 'personal']
SKIP_PARTS = {'.git', '.workbuddy', '.codegraph'}
TEXT_SUFFIXES = {'.md', '.json', '.sh'}

failures: list[str] = []

def active_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if set(path.parts) & SKIP_PARTS:
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        files.append(path)
    return files

def read(path: Path) -> str:
    return path.read_text(errors='ignore')

# 1. Public branding leftovers.
for path in active_text_files():
    if path == Path('scripts/check-private-naming.sh'):
        continue
    text = read(path)
    for forbidden in ['Matt ' + 'Pocock', 'matt' + 'pocock']:
        if forbidden in text:
            failures.append(f'{path}: forbidden public branding {forbidden!r}')

# 2. Active skill directories and frontmatter names must use zj-.
for bucket in ACTIVE_BUCKETS:
    bucket_dir = ROOT / 'skills' / bucket
    if not bucket_dir.exists():
        continue
    for skill_dir in sorted(p for p in bucket_dir.iterdir() if p.is_dir()):
        if not skill_dir.name.startswith('zj-'):
            failures.append(f'{skill_dir}: active skill directory must start with zj-')
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            failures.append(f'{skill_md}: missing SKILL.md')
            continue
        name = None
        for line in read(skill_md).splitlines():
            if line.startswith('name:'):
                name = line.split(':', 1)[1].strip()
                break
        if not name:
            failures.append(f'{skill_md}: missing frontmatter name')
        elif not name.startswith('zj-'):
            failures.append(f'{skill_md}: frontmatter name must start with zj- (found {name!r})')

# 3. Stale setup command.
stale_setup_command = '/' + 'setup-' + 'matt-' + 'pocock-skills'
for path in active_text_files():
    if path == Path('scripts/check-private-naming.sh'):
        continue
    text = read(path)
    if stale_setup_command in text:
        failures.append(f'{path}: stale setup command reference')

# 4. Target-repo documentation paths must use the ZJ contract.
old_path_patterns = [
    (re.compile(r'(?<!ZJ-)CONTEXT\.md'), 'use ZJ-CONTEXT.md'),
    (re.compile(r'(?<!ZJ-)CONTEXT-MAP\.md'), 'use ZJ-CONTEXT-MAP.md'),
    (re.compile('docs/' + 'agents/'), 'use docs/zj-agents/ZJ-*.md'),
    (re.compile(r'(?<!\.zj-)\.out-of-scope/'), 'use .zj-out-of-scope/'),
    (re.compile('docs/' + 'adr/'), 'use docs/zj-adr/ZJ-*.md'),
]
for path in active_text_files():
    if path == Path('scripts/check-private-naming.sh'):
        continue
    text = read(path)
    for pattern, replacement in old_path_patterns:
        for match in pattern.finditer(text):
            failures.append(f'{path}: stale target repo path {match.group(0)!r}; {replacement}')

# 5. New contract anchors must remain documented.
required_new_refs = [
    'jununfly/ZAgentic',
    'ZJ-CONTEXT.md',
    'ZJ-CONTEXT-MAP.md',
    'docs/zj-agents/ZJ-ISSUE-TRACKER.md',
    'docs/zj-agents/ZJ-TRIAGE-LABELS.md',
    'docs/zj-agents/ZJ-DOMAIN.md',
    '.zj-out-of-scope',
    'docs/zj-adr',
    'ZJ-0001',
]
all_text = '\n'.join(read(path) for path in active_text_files())
for required in required_new_refs:
    if required not in all_text:
        failures.append(f'missing required private naming reference {required!r}')

if failures:
    print('Private naming check failed:')
    for failure in failures:
        print(f'- {failure}')
    sys.exit(1)

print('Private naming check passed')
PY
