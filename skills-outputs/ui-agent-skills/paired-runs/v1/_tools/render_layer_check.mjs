// render_layer_check.mjs — BLK-3 closure: real Chromium 155 (DOM-assertion level)
//
// For each lane in LANES, serve the artifact over http (so ES modules resolve),
// launch Chrome 155 headless, run a battery of machine-determinable render-layer
// assertions (boot errors, DOM presence, aria-describedby linkage, keyboard
// focusability of critical transition controls, failure/timeout NOT rendered as
// success). Outputs render-layer-report.json.
//
// No screenshots / no image reading (per environment constraints): every signal
// is a DOM fact or an exit code.
//
// b1 extension (2026-10-22): added R2-h5 (single-page tabs, uses runLane) and
// R2-h6 (two-page app: index.html + approval.html, uses runLaneMultiPage). The
// cohort now covers the full R2+R3+R4 graduation set (all 6 lanes).

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const BASE = '/Users/bilibili/Documents/workspace/github/jununfly/ZAgentic/skills-outputs/ui-agent-skills/paired-runs/v1';
const OUT = process.env.RL_OUT || path.join(BASE, '_tools', 'render-layer-report.json');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

function makeServer(rootDir) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let urlPath = decodeURIComponent(req.url.split('?')[0]);
      if (urlPath === '/') urlPath = '/index.html';
      if (urlPath === '/favicon.ico') { res.writeHead(204); res.end(); return; }
      const filePath = path.join(rootDir, urlPath);
      if (!filePath.startsWith(rootDir)) { res.writeHead(403); res.end(); return; }
      fs.readFile(filePath, (err, buf) => {
        if (err) { res.writeHead(404); res.end('not found'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
        res.end(buf);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

// ---- lane registry (selectors + drive recipes) -------------------------------
const LANES = [
  {
    id: 'R2-h5', run: 'R2', lane: 'direct-prompt', dir: `${BASE}/R2/h5/artifact`,
    kind: 'tabs', confirm: 'checkbox', forceMathRandom: false,
    sel: {
      tabAppr: '#tab-approval', profLoad: null, profSubmit: '#f-submit',
      profInputs: ['#f-nickname', '#f-email', '#f-bio'],
      apprInputs: ['#a-amount', '#a-reason'],
      apprSubmit: '#a-submit', apprRoute: '#a-route', apprApprove: '#a-approve',
      apprReject: '#a-reject', apprRole: null, scenario: '#f-response',
      panelAppr: '#panel-approval', profState: '#f-state', profBanner: null,
      apprState: '#a-state', apprBanner: null,
    },
    toUnderReview: async (page) => {
      await page.click('#tab-approval');
      await page.click('#a-confirm');
      await page.click('#a-submit');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'submitted', { timeout: 4000 });
      await page.click('#a-route');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'under_review', { timeout: 4000 });
    },
    forceFail: async (page) => {
      await page.click('#tab-form');
      // prefilled fields (e.g. nickname="zj"); set value + dispatch input so machine sees the new value
      const setVal = (sel, v) => page.$eval(sel, (el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); }, v);
      await setVal('#f-nickname', 'Alice');
      await setVal('#f-email', 'alice@example.com');
      await setVal('#f-bio', 'test bio');
      await page.select('#f-response', '0'); // timeout -> error
      await page.click('#f-confirm');
      await page.click('#f-submit');
      await page.waitForFunction(() => {
        const s = document.querySelector('#f-state')?.textContent;
        return s === 'error' || s === 'success';
      }, { timeout: 8000 });
    },
    timeoutAction: async (page) => { await page.click('#a-timeout'); },
    timeoutStateOk: (s) => s === 'under_review',
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
  {
    id: 'R2-h6', run: 'R2', lane: 'skills-path', dir: `${BASE}/R2/h6/artifact`,
    kind: 'multi', confirm: 'inpage', forceMathRandom: false, runner: 'multi',
    sel: {
      profInputs: ['#nickname', '#email', '#bio'],
      apprInputs: ['#amount', '#reason'],
      profSubmit: '#submit-btn', apprSubmit: '#submit-btn', apprRoute: '#route-btn',
      apprApprove: '#approve-btn', apprReject: '#reject-btn',
      profState: '#state-badge', profBanner: '#banner',
      apprState: '#state-badge', apprBanner: '#banner',
    },
    toUnderReview: async (page) => {
      await page.type('#amount', '1200');
      await page.type('#reason', 'client visit');
      await page.click('#submit-btn');
      try { await page.waitForSelector('#confirm-dialog[open]', { timeout: 3000 }); } catch (_) {}
      const ok = await page.$('#confirm-ok'); if (ok) await ok.click();
      // badge text is "submitted · v1" / "under_review · v1" — match by substring
      await page.waitForFunction(() => (document.querySelector('#state-badge')?.textContent || '').includes('submitted'), { timeout: 4000 });
      await page.click('#route-btn');
      await page.waitForFunction(() => (document.querySelector('#state-badge')?.textContent || '').includes('under_review'), { timeout: 4000 });
    },
    forceFail: async (page) => {
      await page.select('#server-behavior', '0'); // timeout
      await page.click('#submit-btn');
      try { await page.waitForSelector('#confirm-dialog[open]', { timeout: 3000 }); } catch (_) {}
      const ok = await page.$('#confirm-ok'); if (ok) await ok.click();
      try {
        await page.waitForFunction(() => {
          const s = document.querySelector('#state-badge')?.textContent;
          return s === 'error' || s === 'success';
        }, { timeout: 5000 });
      } catch (_) {}
    },
    timeoutAction: async (page) => { await page.click('#escalate-btn'); },
    timeoutStateOk: (s) => (s || '').includes('under_review'),
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
  {
    id: 'R4-h9', run: 'R4', lane: 'skills-path', dir: `${BASE}/R4/h9/artifact`,
    kind: 'tabs', confirm: 'dialog', forceMathRandom: false,
    sel: {
      tabAppr: '#tab-approval', profLoad: '#pf-load', profSubmit: '#pf-submit',
      profInputs: ['#pf-nickname', '#pf-email', '#pf-bio'],
      apprInputs: ['#ap-amount', '#ap-reason'],
      apprSubmit: '#ap-submit', apprRoute: '#ap-route', apprApprove: '#ap-approve',
      apprReject: '#ap-reject', apprRole: '#ap-role', scenario: '#pf-scenario',
      panelAppr: '#panel-approval', profState: '#pf-state', profBanner: '#pf-banner',
      apprState: '#ap-state', apprBanner: '#ap-banner',
    },
    toUnderReview: async (page) => {
      await page.click('#tab-approval');
      await page.click('#ap-submit'); // confirm dialog auto-accepted
      await page.waitForFunction(() => document.querySelector('#ap-state')?.textContent === 'submitted', { timeout: 4000 });
      await page.click('#ap-route');
      await page.waitForFunction(() => document.querySelector('#ap-state')?.textContent === 'under_review', { timeout: 4000 });
      await page.select('#ap-role', 'approver');
    },
    forceFail: async (page) => {
      await page.click('#tab-profile');
      await page.click('input[name="pf-scenario"][value="0"]'); // timeout
      await page.click('#pf-load');
      await page.click('#pf-submit'); // confirm dialog auto-accepted
      await page.waitForFunction(() => {
        const s = document.querySelector('#pf-state')?.textContent;
        return s === 'error' || s === 'success';
      }, { timeout: 5000 });
    },
    timeoutAction: async (page) => { await page.click('#ap-timeout'); },
    timeoutStateOk: (s) => s === 'under_review',
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
  {
    id: 'R4-h10', run: 'R4', lane: 'direct-prompt', dir: `${BASE}/R4/h10/artifact`,
    kind: 'tabs', confirm: 'none', forceMathRandom: 0.9,
    sel: {
      tabAppr: '#tab-approval', profLoad: '#btn-load', profSubmit: '#btn-submit',
      profInputs: ['#nickname', '#email', '#bio'],
      apprInputs: ['#amount', '#reason'],
      apprSubmit: '#btn-areq', apprRoute: '#btn-route', apprApprove: '#btn-approve',
      apprReject: '#btn-reject', apprRole: null, scenario: null,
      panelAppr: '#approval', profState: '#profile-state', profBanner: '#profile-banner',
      apprState: '#approval-state', apprBanner: '#approval-banner',
    },
    toUnderReview: async (page) => {
      await page.click('#tab-approval');
      await page.type('#amount', '1200');
      await page.type('#reason', 'client visit');
      await page.click('#btn-areq');
      await page.waitForFunction(() => document.querySelector('#approval-state')?.textContent === 'submitted', { timeout: 4000 });
      await page.click('#btn-route');
      await page.waitForFunction(() => document.querySelector('#approval-state')?.textContent === 'under_review', { timeout: 4000 });
    },
    forceFail: async (page) => {
      await page.click('#tab-profile');
      // Math.random overridden to 0.9 -> mockServer returns 422 -> error
      await page.click('#btn-load');
      await page.click('#btn-submit');
      await page.waitForFunction(() => {
        const s = document.querySelector('#profile-state')?.textContent;
        return s === 'error' || s === 'success';
      }, { timeout: 5000 });
    },
    timeoutAction: async (page) => { await page.click('#btn-timeout'); },
    timeoutStateOk: (s) => s === 'under_review',
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
  {
    id: 'R3-h8', run: 'R3', lane: 'skills-path', dir: `${BASE}/R3/h8/artifact`,
    kind: 'single', confirm: 'checkbox', forceMathRandom: false,
    sel: {
      tabAppr: null, profLoad: null, profSubmit: '#f-submit',
      profInputs: ['#f-nickname', '#f-email', '#f-bio'],
      apprInputs: ['#a-amount', '#a-reason'],
      apprSubmit: '#a-submit', apprRoute: '#a-route', apprApprove: '#a-approve',
      apprReject: '#a-reject', apprRole: null, scenario: '#f-scenario',
      panelAppr: null, profState: '#form-state', profBanner: '#f-banner',
      apprState: '#a-state', apprBanner: '#a-banner',
    },
    toUnderReview: async (page) => {
      await page.click('#a-confirm');
      await page.click('#a-submit');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'submitted', { timeout: 4000 });
      await page.click('#a-route');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'under_review', { timeout: 4000 });
    },
    forceFail: async (page) => {
      await page.select('#f-scenario', 'timeout');
      await page.click('#f-confirm');
      await page.click('#f-submit'); // handler waits 600ms then persist code 0 -> error
      await page.waitForFunction(() => {
        const s = document.querySelector('#form-state')?.textContent;
        return s === 'error' || s === 'success';
      }, { timeout: 5000 });
    },
    timeoutAction: async (page) => { await page.click('#a-timeout'); },
    timeoutStateOk: (s) => s === 'under_review',
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
  {
    id: 'R3-h7', run: 'R3', lane: 'direct-prompt', dir: `${BASE}/R3/h7/artifact`,
    kind: 'tabs', confirm: 'checkbox', forceMathRandom: false,
    sel: {
      tabAppr: '#tab-approval', profLoad: null, profSubmit: '#f-submit',
      profInputs: ['#f-nickname', '#f-email', '#f-bio'],
      apprInputs: ['#a-amount', '#a-reason'],
      apprSubmit: '#a-submit', apprRoute: '#a-route', apprApprove: '#a-approve',
      apprReject: '#a-reject', apprRole: null, scenario: '#f-scenario',
      panelAppr: '#panel-approval', profState: '#f-state', profBanner: '#f-feedback',
      apprState: '#a-state', apprBanner: '#a-feedback',
    },
    toUnderReview: async (page) => {
      await page.click('#tab-approval');
      await page.click('#a-confirm');
      await page.click('#a-submit');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'submitted', { timeout: 4000 });
      await page.click('#a-route');
      await page.waitForFunction(() => document.querySelector('#a-state')?.textContent === 'under_review', { timeout: 4000 });
    },
    forceFail: async (page) => {
      await page.click('#tab-form');
      await page.select('#f-scenario', 'timeout');
      await page.click('#f-confirm');
      await page.click('#f-submit'); // parks
      await page.click('#f-respond'); // delivers response -> error
      await page.waitForFunction(() => {
        const s = document.querySelector('#f-state')?.textContent;
        return s === 'error' || s === 'success';
      }, { timeout: 5000 });
    },
    timeoutAction: async (page) => { await page.click('#a-timeout'); },
    timeoutStateOk: (s) => s === 'under_review',
    timeoutBannerNotOk: (cls) => !cls.includes('ok'),
  },
];

// ---- assertion helpers -------------------------------------------------------
function visibleAndEnabled(page, selector) {
  return page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return { exists: false, disabled: null, visible: false };
    let p = el; let visible = true;
    while (p) {
      const st = getComputedStyle(p);
      if (st.display === 'none' || st.visibility === 'hidden' || p.hidden) { visible = false; break; }
      p = p.parentElement;
    }
    return { exists: true, disabled: el.disabled, visible };
  }, selector);
}

function ariaLinkageOk(page, selector) {
  return page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return { present: false, linked: false, reason: 'input missing' };
    const ref = el.getAttribute('aria-describedby');
    if (!ref) return { present: true, linked: false, reason: 'no aria-describedby' };
    const ids = ref.trim().split(/\s+/);
    const missing = ids.filter((id) => !document.getElementById(id));
    return { present: true, linked: missing.length === 0, reason: missing.length ? `missing: ${missing.join(',')}` : 'ok' };
  }, selector);
}

async function runLane(browser, lane) {
  const server = await makeServer(lane.dir);
  const port = server.address().port;
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  if (lane.forceMathRandom !== false) {
    await page.evaluateOnNewDocument((v) => { Math.random = () => v; }, lane.forceMathRandom);
  }
  if (lane.confirm === 'dialog') {
    page.on('dialog', async (d) => { await d.accept(); });
  }

  const results = [];
  const add = (id, label, pass, detail) => results.push({ id, label, pass, detail });

  try {
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 300));

    // A1 boot without JS errors
    add('A1-boot-no-error', 'page boots with no pageerror/console error', pageErrors.length === 0 && consoleErrors.length === 0,
      { pageErrors, consoleErrors: consoleErrors.slice(0, 5) });

    // A2 DOM presence of critical controls
    const sel = lane.sel;
    const needed = [sel.profSubmit, sel.apprSubmit, sel.apprRoute, sel.apprApprove, sel.apprReject, ...sel.profInputs, ...sel.apprInputs];
    const presence = await page.evaluate((ids) => {
      const missing = ids.filter((id) => !document.querySelector(id));
      return { missing };
    }, needed);
    add('A2-dom-present', 'critical controls + required inputs present in DOM', presence.missing.length === 0, presence);

    // A3 aria-describedby linkage (profile + approval)
    const profLinks = [];
    for (const s of sel.profInputs) profLinks.push({ sel: s, ...(await ariaLinkageOk(page, s)) });
    const apprLinks = [];
    for (const s of sel.apprInputs) apprLinks.push({ sel: s, ...(await ariaLinkageOk(page, s)) });
    const profLinked = profLinks.every((x) => x.linked);
    const apprLinked = apprLinks.every((x) => x.linked);
    add('A3-aria-linkage-profile', 'required profile inputs linked to error msg via aria-describedby', profLinked, profLinks);
    add('A4-aria-linkage-approval', 'required approval inputs linked to error msg via aria-describedby', apprLinked, apprLinks);

    // A5 keyboard focusability of approve control after reaching under_review
    await lane.toUnderReview(page);
    if (sel.tabAppr) {
      await page.evaluate((s) => { const t = document.querySelector(s); if (!t) return true; t.click(); return true; }, sel.tabAppr);
    }
    const focusInfo = await page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return { exists: false };
      el.focus();
      const focused = document.activeElement === el;
      let p = el, visible = true;
      while (p) { const st = getComputedStyle(p); if (st.display === 'none' || st.visibility === 'hidden' || p.hidden) { visible = false; break; } p = p.parentElement; }
      return { exists: true, focused, disabled: el.disabled, visible };
    }, sel.apprApprove);
    add('A5-keyboard-approve-reachable', 'approve control keyboard-focusable in under_review (not disabled, visible, focus() lands)',
      focusInfo.exists && focusInfo.focused && !focusInfo.disabled && focusInfo.visible, focusInfo);

    // A6 failure NOT rendered as success
    await lane.forceFail(page);
    const failState = await page.evaluate((s) => document.querySelector(s)?.textContent, sel.profState);
    const failBanner = await page.evaluate((s) => {
      const el = document.querySelector(s); if (!el) return '';
      return el.className || '';
    }, sel.profBanner);
    const notSuccess = failState !== 'success' && !failBanner.includes('ok');
    add('A6-failure-not-success', 'forced server failure renders as error, never as success', notSuccess,
      { state: failState, bannerClass: failBanner });

    // A7 timeout NOT faked as success
    try { await lane.toUnderReview(page); } catch (_) { /* already progressed */ }
    const beforeTO = await page.evaluate((s) => document.querySelector(s)?.textContent, sel.apprState);
    await lane.timeoutAction(page);
    await new Promise((r) => setTimeout(r, 200));
    const afterTO = await page.evaluate((s) => document.querySelector(s)?.textContent, sel.apprState);
    const toBanner = await page.evaluate((s) => { const el = document.querySelector(s); return el ? (el.className || '') : ''; }, sel.apprBanner);
    const toOk = lane.timeoutStateOk(afterTO) && lane.timeoutBannerNotOk(toBanner);
    add('A7-timeout-no-fake-success', 'timeout/escalation keeps state under_review, never fakes success', toOk,
      { before: beforeTO, after: afterTO, bannerClass: toBanner });
  } catch (e) {
    add('FATAL', 'harness threw', false, { error: String(e) });
  } finally {
    await page.close();
    server.close();
  }

  const passed = results.filter((r) => r.pass).length;
  return {
    id: lane.id, run: lane.run, lane: lane.lane, dir: lane.dir,
    assertions: results, passed, total: results.length,
    consoleErrors, pageErrors,
  };
}

// Two-page variant for R2-h6 (index.html = profile, approval.html = approval flow).
async function runLaneMultiPage(browser, lane) {
  const server = await makeServer(lane.dir);
  const port = server.address().port;
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(String(e)));

  const results = [];
  const add = (id, label, pass, detail) => results.push({ id, label, pass, detail });

  let bootClean = true, bootDetail = { pageErrors: [], consoleErrors: [] };
  let profPresentOk = true, profPresentDetail = {};
  let profAriaOk = true, profAriaDetail = [];
  let apprPresentOk = true, apprPresentDetail = {};
  let apprAriaOk = true, apprAriaDetail = [];
  let failOk = false, failDetail = {};
  let focusOk = false, focusDetail = {};
  let toOk = false, toDetail = {};

  try {
    // ---- page 1: profile (index.html) ----
    await page.goto(`http://127.0.0.1:${port}/index.html`, { waitUntil: 'networkidle0', timeout: 15000 });
    await wait(300);
    bootClean = pageErrors.length === 0 && consoleErrors.length === 0;
    bootDetail = { pageErrors: pageErrors.slice(0, 5), consoleErrors: consoleErrors.slice(0, 5) };

    const profNeeded = [lane.sel.profSubmit, ...lane.sel.profInputs];
    const pres = await page.evaluate((ids) => ({ missing: ids.filter((i) => !document.querySelector(i)) }), profNeeded);
    profPresentOk = pres.missing.length === 0; profPresentDetail = pres;

    const profLinks = [];
    for (const s of lane.sel.profInputs) profLinks.push({ sel: s, ...(await ariaLinkageOk(page, s)) });
    profAriaOk = profLinks.every((x) => x.linked); profAriaDetail = profLinks;

    // A6 forced failure on profile
    await lane.forceFail(page);
    const fState = await page.evaluate((s) => document.querySelector(s)?.textContent, lane.sel.profState);
    const fBanner = await page.evaluate((s) => { const e = document.querySelector(s); return e ? (e.className || '') : ''; }, lane.sel.profBanner);
    failOk = fState !== 'success' && !fBanner.includes('ok');
    failDetail = { state: fState, bannerClass: fBanner };
  } catch (e) {
    add('FATAL-profile', 'harness threw on profile page', false, { error: String(e) });
  }

  try {
    // ---- page 2: approval (approval.html) ----
    await page.goto(`http://127.0.0.1:${port}/approval.html`, { waitUntil: 'networkidle0', timeout: 15000 });
    await wait(300);
    const boot2 = pageErrors.length === 0 && consoleErrors.length === 0;
    bootClean = bootClean && boot2;
    if (!boot2) bootDetail = { pageErrors: pageErrors.slice(0, 5), consoleErrors: consoleErrors.slice(0, 5) };

    const apprNeeded = [lane.sel.apprSubmit, lane.sel.apprRoute, lane.sel.apprApprove, lane.sel.apprReject, ...lane.sel.apprInputs];
    const pres2 = await page.evaluate((ids) => ({ missing: ids.filter((i) => !document.querySelector(i)) }), apprNeeded);
    apprPresentOk = pres2.missing.length === 0; apprPresentDetail = pres2;

    const apprLinks = [];
    for (const s of lane.sel.apprInputs) apprLinks.push({ sel: s, ...(await ariaLinkageOk(page, s)) });
    apprAriaOk = apprLinks.every((x) => x.linked); apprAriaDetail = apprLinks;

    await lane.toUnderReview(page);
    const focusInfo = await page.evaluate((s) => {
      const el = document.querySelector(s); if (!el) return { exists: false };
      el.focus(); const focused = document.activeElement === el;
      let p = el, visible = true; while (p) { const st = getComputedStyle(p); if (st.display === 'none' || st.visibility === 'hidden' || p.hidden) { visible = false; break; } p = p.parentElement; }
      return { exists: true, focused, disabled: el.disabled, visible };
    }, lane.sel.apprApprove);
    focusOk = focusInfo.exists && focusInfo.focused && !focusInfo.disabled && focusInfo.visible; focusDetail = focusInfo;

    await lane.timeoutAction(page);
    await wait(200);
    const afterTO = await page.evaluate((s) => document.querySelector(s)?.textContent, lane.sel.apprState);
    const toBanner = await page.evaluate((s) => { const e = document.querySelector(s); return e ? (e.className || '') : ''; }, lane.sel.apprBanner);
    toOk = lane.timeoutStateOk(afterTO) && lane.timeoutBannerNotOk(toBanner);
    toDetail = { after: afterTO, bannerClass: toBanner };
  } catch (e) {
    add('FATAL-approval', 'harness threw on approval page', false, { error: String(e) });
  } finally {
    await page.close();
    server.close();
  }

  add('A1-boot-no-error', 'page boots with no JS error (profile+approval)', bootClean, bootDetail);
  add('A2-dom-present', 'critical controls + required inputs present (profile+approval)', profPresentOk && apprPresentOk, { profile: profPresentDetail, approval: apprPresentDetail });
  add('A3-aria-linkage-profile', 'required profile inputs linked to error msg via aria-describedby', profAriaOk, profAriaDetail);
  add('A4-aria-linkage-approval', 'required approval inputs linked to error msg via aria-describedby', apprAriaOk, apprAriaDetail);
  add('A5-keyboard-approve-reachable', 'approve control keyboard-focusable in under_review', focusOk, focusDetail);
  add('A6-failure-not-success', 'forced server failure renders as error, never as success', failOk, failDetail);
  add('A7-timeout-no-fake-success', 'timeout/escalation keeps state under_review, never fakes success', toOk, toDetail);

  const passed = results.filter((r) => r.pass).length;
  return { id: lane.id, run: lane.run, lane: lane.lane, dir: lane.dir, multiPage: true, assertions: results, passed, total: results.length, consoleErrors, pageErrors };
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });
  const report = { generated_at: new Date().toISOString(), chrome: CHROME, cohort_scope: 'R2+R3+R4 (full graduation set, b1 extended)', lanes: [] };
  try {
    for (const lane of LANES) {
      const fn = lane.runner === 'multi' ? runLaneMultiPage : runLane;
      report.lanes.push(await fn(browser, lane));
    }
  } finally {
    await browser.close();
  }
  // cohort comparison: skills vs direct per run
  const byRun = {};
  for (const l of report.lanes) {
    byRun[l.run] = byRun[l.run] || {};
    byRun[l.run][l.lane] = l;
  }
  report.cohort = byRun;
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(`WROTE ${OUT}`);
  for (const l of report.lanes) {
    console.log(`${l.id} (${l.lane}): ${l.passed}/${l.total} passed; errors=${l.pageErrors.length + l.consoleErrors.length}`);
  }
}

main().catch((e) => { console.error('FATAL', e); process.exit(1); });
