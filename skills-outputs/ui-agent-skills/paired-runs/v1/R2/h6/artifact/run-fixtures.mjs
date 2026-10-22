// Fixture driver：逐个 fixture 用 input.actions 驱动实现，再按 expected.json 的键名取实际值比对。
// 不读 expected 的值做任何决策；expected 只用来决定要比对哪些键。
import { existsSync, readFileSync, readdirSync, writeFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createProfileFlow } from './src/form/profile-machine.mjs';
import { createApprovalFlow } from './src/approval/request-machine.mjs';

const FIXTURES_ROOT = resolve(process.argv[2] ?? '');
const RESULT_FILE = '.run-fixtures-result.json';
const TARGET_CLASSES = ['form', 'approval'];

const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'));

function listFixtureDirs(root) {
  const out = [];
  for (const cls of readdirSync(root).sort()) {
    const classDir = join(root, cls);
    if (!statSync(classDir).isDirectory()) continue;
    if (!TARGET_CLASSES.includes(cls)) continue;
    for (const id of readdirSync(classDir).sort()) {
      const dir = join(classDir, id);
      if (!statSync(dir).isDirectory()) continue;
      if (id.startsWith('.')) continue;
      if (!existsSync(join(dir, 'input.json')) || !existsSync(join(dir, 'expected.json'))) continue;
      out.push({ id, class: cls, dir });
    }
  }
  return out;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = canonical(value[key]);
        return acc;
      }, {});
  }
  return value;
}

const sameJson = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

function pick(actual, expected) {
  const out = {};
  for (const key of Object.keys(expected)) {
    if (key === 'fixture_id' || key === 'assertions') continue;
    out[key] = actual[key];
  }
  return out;
}

async function runFormFixture(input) {
  const flow = createProfileFlow({
    user: input.user,
    profile: input.profile ?? {},
    initialState: input.initial_state ?? 'idle',
  });
  for (const action of input.actions ?? []) {
    const actor = action.role ?? 'user';
    const confirmed = actor !== 'system';
    await flow.dispatch({
      ...action,
      confirmed,
      value: action.value ?? action.value_to ?? undefined,
    });
  }
  return flow.snapshot();
}

async function runApprovalFixture(input) {
  const flow = createApprovalFlow({
    applicant: input.applicant,
    approver: input.approver ?? null,
    request: input.request ?? {},
    initialState: input.initial_state ?? 'draft',
  });
  for (const action of input.actions ?? []) {
    const actor = action.role ?? 'applicant';
    const confirmed = actor !== 'system';
    await flow.dispatch({
      ...action,
      confirmed,
      actor: action.actor ?? (typeof action.role === 'string' && action.role.startsWith('user-') ? action.role : null),
    });
  }
  return flow.snapshot();
}

async function main() {
  const fixtures = listFixtureDirs(FIXTURES_ROOT);
  const results = [];

  for (const fixture of fixtures) {
    const input = readJson(join(fixture.dir, 'input.json'));
    const expected = readJson(join(fixture.dir, 'expected.json'));
    const snapshot = fixture.class === 'approval' ? await runApprovalFixture(input) : await runFormFixture(input);
    const actual = pick(snapshot, expected);
    const comparableExpected = pick(expected, expected);
    const mismatchKeys = Object.keys(actual).filter((key) => !sameJson(actual[key], comparableExpected[key]));
    const missingKeys = Object.keys(comparableExpected).filter((key) => !(key in actual));
    mismatchKeys.push(...missingKeys);
    const match = mismatchKeys.length === 0;
    results.push({
      fixture_id: fixture.id,
      class: fixture.class,
      match,
      actual,
      expected: comparableExpected,
      mismatch_keys: mismatchKeys,
      conflicts: snapshot.conflicts ?? [],
    });
  }

  const allMatch = results.every((result) => result.match);
  const payload = { fixtures: results, all_match: allMatch };
  writeFileSync(join(process.cwd(), RESULT_FILE), `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  for (const result of results) {
    process.stdout.write(
      `${result.fixture_id} ${result.match ? 'PASS' : 'FAIL'} ${
        result.match ? '' : `mismatch=${JSON.stringify(result.mismatch_keys)}`
      }\n`,
    );
  }
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  process.exit(allMatch ? 0 : 1);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
  process.exit(2);
});
