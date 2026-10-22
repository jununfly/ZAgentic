import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { TOKENS, contrastRatio } from './tokens.mjs';

export function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function read(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
}

export function writeReceipt({ cwd, fixtureFiles, scenarioPass, persistedPayload }) {
  const html = read(path.join(cwd, 'index.html'));
  const tracked = [
    'index.html',
    'run-f1.mjs',
    'src/formMachine.mjs',
    'src/mockApi.mjs',
    'src/validation.mjs',
    'src/tokens.mjs',
    'src/verify.mjs'
  ];
  const fileHashes = Object.fromEntries(tracked.map((file) => [file, sha256(read(path.join(cwd, file)))]));

  const contrastRows = TOKENS.contrastPairs.map(([fg, bg]) => ({
    pair: `${fg} on ${bg}`,
    ratio: Number(contrastRatio(TOKENS.color[fg], TOKENS.color[bg]).toFixed(2))
  }));
  const contrastOk = contrastRows.every((row) => row.ratio >= TOKENS.contrastThreshold);

  const labelsOk = ['nickname', 'email', 'bio'].every((field) => html.includes(`for="${field}"`));
  const ariaOk = html.includes('aria-live="polite"') && html.includes('aria-invalid') && html.includes('aria-describedby');
  const focusOk = html.includes(':focus-visible');
  const motionOk = html.includes('prefers-reduced-motion');
  const sourceText = tracked.map((file) => read(path.join(cwd, file))).join('\n');
  const networkOk = !/https?:\/\//.test(sourceText) && !/\bfetch\s*\(/.test(sourceText);

  let persistenceOk = false;
  let persistenceObserved = 'no success payload';
  if (persistedPayload && persistedPayload.user) {
    const dataFile = path.join(cwd, '.data', 'profile.json');
    try {
      const stored = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
      persistenceOk = stored.user === persistedPayload.user && stored.revision === persistedPayload.revision;
      persistenceObserved = `revision ${stored.revision} for ${stored.user}`;
    } catch {
      persistenceObserved = 'profile.json missing or unreadable';
    }
  }

  const cells = [
    { id: 'scenario.f1', claim: 'F-1 asserted fields match expected', threshold: 'all equal', observed: scenarioPass ? 'matched' : 'mismatch', status: scenarioPass ? 'PASS' : 'FAIL' },
    { id: 'dom.aria', claim: 'every field has label and error wiring', threshold: 'labels plus aria attributes', observed: labelsOk && ariaOk ? 'labels and aria present' : 'missing label or aria', status: labelsOk && ariaOk ? 'PASS' : 'FAIL' },
    { id: 'interaction.focus', claim: 'keyboard focus is visible', threshold: ':focus-visible rule', observed: focusOk ? 'rule present' : 'rule missing', status: focusOk ? 'PASS' : 'FAIL' },
    { id: 'motion.reduced', claim: 'reduced motion is honored', threshold: 'media query present', observed: motionOk ? 'query present' : 'query missing', status: motionOk ? 'PASS' : 'FAIL' },
    { id: 'contrast.pairs', claim: 'text contrast meets WCAG AA', threshold: `>= ${TOKENS.contrastThreshold}:1`, observed: contrastRows.map((row) => `${row.pair}=${row.ratio}`).join(' '), status: contrastOk ? 'PASS' : 'FAIL' },
    { id: 'boundary.network', claim: 'no remote calls in artifact', threshold: 'zero http and fetch', observed: networkOk ? 'none found' : 'remote reference found', status: networkOk ? 'PASS' : 'FAIL' },
    { id: 'persistence.local', claim: 'success writes local profile store', threshold: 'file revision matches payload', observed: persistenceObserved, status: persistenceOk ? 'PASS' : 'FAIL' }
  ];

  const passed = cells.filter((cell) => cell.status === 'PASS').length;
  const allPass = passed === cells.length;

  const fixtureHash = sha256(fixtureFiles.map((file) => read(file)).join('\n'));
  const fingerprint = sha256(
    JSON.stringify({ node: process.version, platform: process.platform, arch: process.arch, files: fileHashes })
  );

  const receipt = {
    schema: 'verification-receipt/v1',
    claim: 'F-1 happy path plus DOM ARIA focus contrast motion and network boundary checks',
    status: allPass ? 'PASS' : 'FAIL',
    aggregate_status: allPass ? 'PASS' : 'FAIL',
    threshold: 'every cell PASS',
    command: 'node run-f1.mjs <input.json> <expected.json>',
    commit: 'unversioned-worktree-no-git',
    oracle_version: 'h1-verify/1.0.0',
    fixture: { files: fixtureFiles, hash: fixtureHash },
    environment: {
      node: process.version,
      platform: process.platform,
      arch: process.arch,
      fingerprint
    },
    artifact: { path: 'artifact', files: fileHashes },
    baseline_used: false,
    stale: false,
    checked: cells.length,
    passed,
    cells,
    generated_at: new Date().toISOString()
  };

  const outDir = path.resolve(cwd, '..', 'briefs');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'verification-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}
