// Fixture driver: replays each fixture's actions against the real modules and
// projects the resulting state onto whatever keys the fixture expects.
// Generic by construction: no fixture-specific values live in this file.

import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createFormSession } from "./src/form/session.mjs";
import { createApprovalSession } from "./src/approval/session.mjs";

const CLASS_IDS = ["form", "approval"];

const BUILDERS = {
  form: (input) =>
    createFormSession({
      profile: input.profile,
      initialState: input.initial_state,
      user: input.user,
    }),
  approval: (input) =>
    createApprovalSession({
      applicant: input.applicant,
      approver: input.approver,
      request: input.request,
      initialState: input.initial_state,
    }),
};

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value === undefined ? null : value);
}

async function listFixtureDirs(root, classId) {
  const dir = path.join(root, classId);
  const entries = await readdir(dir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

function project(snapshot, expected) {
  const actual = {};
  for (const key of Object.keys(expected)) {
    if (key === "fixture_id" || key === "assertions") continue;
    const value = snapshot[key];
    actual[key] = value === undefined ? null : value;
  }
  return actual;
}

function diff(actual, expected) {
  const keys = Object.keys(expected).filter((key) => key !== "fixture_id" && key !== "assertions");
  return keys.filter((key) => canonical(actual[key]) !== canonical(expected[key]));
}

async function runFixture(root, classId, name) {
  const base = path.join(root, classId, name);
  const input = await readJson(path.join(base, "input.json"));
  const expected = await readJson(path.join(base, "expected.json"));

  const build = BUILDERS[input.class ?? classId];
  const session = build(input);
  const trace = [];

  for (const action of input.actions ?? []) {
    const outcome = session.apply(action);
    trace.push({ seq: action.seq, action: action.action, outcome });
  }

  const actual = project(session.snapshot(), expected);
  const mismatchKeys = diff(actual, expected);

  return {
    fixture_id: expected.fixture_id ?? input.fixture_id ?? name,
    class: input.class ?? classId,
    match: mismatchKeys.length === 0,
    actual,
    expected: Object.fromEntries(
      Object.entries(expected).filter(([key]) => key !== "fixture_id" && key !== "assertions"),
    ),
    mismatch_keys: mismatchKeys,
  };
}

async function main() {
  const root = process.argv[2];
  if (!root) {
    console.error("usage: node run-fixtures.mjs <fixtures-root>");
    process.exit(2);
  }

  const fixtures = [];
  for (const classId of CLASS_IDS) {
    for (const name of await listFixtureDirs(root, classId)) {
      try {
        fixtures.push(await runFixture(root, classId, name));
      } catch (error) {
        fixtures.push({
          fixture_id: name,
          class: classId,
          match: false,
          actual: {},
          expected: {},
          mismatch_keys: ["driver_error"],
          error: String(error && error.message ? error.message : error),
        });
      }
    }
  }

  const allMatch = fixtures.every((fixture) => fixture.match);
  const report = { fixtures, all_match: allMatch };

  await writeFile(path.join(process.cwd(), ".run-fixtures-result.json"), `${JSON.stringify(report)}\n`, "utf8");
  console.log(JSON.stringify(report));
  process.exit(allMatch ? 0 : 1);
}

main().catch((error) => {
  console.error(error);
  process.exit(3);
});
