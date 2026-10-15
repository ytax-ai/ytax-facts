// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original software from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

// The engine runner on JavaScript: the same command line and the same standard-input protocol as
// the JVM runner (runner/), over the engine compiled to JavaScript (js/engine/factgraph.js) and
// the fact dictionary generated from dictionary/ty2025 (js/fact-dictionary/generated/).
//
//   node runner.mjs <dictDir> <scenDir> <goldenDir>     one directory of scenarios
//   node runner.mjs --batch                              one `dict<TAB>scen<TAB>golden` per line
//
// For every scenarios/*.json (name order) it resolves every fact path of the dictionary and
// writes <goldenDir>/<name>.tsv when that file is absent (`path<TAB>status<TAB>type<TAB>value`,
// path sorted: the JVM runner's format, through the same resolveAll/snapshotToTsv the JS
// harness checks against the JVM cent for cent), or compares it when present. Each command ends
// with the JVM runner's own line, `[runner] Done. N scenarios.`, which is what the application's
// long-lived engine waits for.
//
// The dictionary directory argument is accepted for the protocol's sake: the dictionary this
// runner resolves against is the generated one it was packaged with, and the application checks
// that it was generated from the pinned dictionary before it starts this process. A scenario that
// carries a tax-year-relative test date (TY-MM-DD) is refused: the application never sends one.
//
// Bundled into one file at packaging time (esbuild), with `ytax-js/` resolving to the release's
// js/ tree.
import { mkdirSync, readFileSync, readdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { buildFactGraph } from 'ytax-js/src/setupFactGraph.js';
import { resolveAll, snapshotToTsv, withTodayOverride } from 'ytax-js/src/snapshot.js';
import { wrappedFacts } from 'ytax-js/src/generatedDictionary.js';

const PATHS = wrappedFacts.map((fact) => fact.path);
const RELATIVE_DATE = /^TY(?:[+-]\d+)?-\d{2}-\d{2}$/;

function refuseRelativeDates(value, where) {
  if (Array.isArray(value)) {
    value.forEach((item) => refuseRelativeDates(item, where));
  } else if (value !== null && typeof value === 'object') {
    Object.values(value).forEach((item) => refuseRelativeDates(item, where));
  } else if (typeof value === 'string' && RELATIVE_DATE.test(value)) {
    throw new Error(`${where}: a tax-year-relative test date (${value}) is not an input this runner takes`);
  }
}

function resolveScenario(json, name) {
  const scenario = JSON.parse(json);
  const facts = scenario.facts ?? scenario;
  refuseRelativeDates(facts, name);
  const graph = buildFactGraph(withTodayOverride(facts), wrappedFacts);
  try {
    for (const issue of graph.checkPersister()) {
      console.error(`[runner] ${name}: persister sync issue: ${issue.path} — ${issue.message}`);
    }
  } catch (e) {
    console.error(`[runner] ${name}: checkPersister threw: ${e instanceof Error ? e.message : String(e)}`);
  }
  return snapshotToTsv(resolveAll(graph, PATHS));
}

function processDir(dictDir, scenDir, goldenDir) {
  console.log(`[runner] dict=${dictDir}  scen=${scenDir}  golden=${goldenDir}`);
  if (!existsSync(scenDir)) throw new Error(`Scenarios directory not found: ${scenDir}`);
  mkdirSync(goldenDir, { recursive: true });
  const files = readdirSync(scenDir).filter((f) => f.endsWith('.json')).sort();
  console.log(`[runner] ${files.length} scenarios to process`);
  let diffs = 0;
  for (const file of files) {
    const name = file.slice(0, -'.json'.length);
    const snapshot = resolveScenario(readFileSync(join(scenDir, file), 'utf8'), name);
    const golden = join(goldenDir, `${name}.tsv`);
    if (!existsSync(golden)) {
      writeFileSync(golden, snapshot);
    } else if (readFileSync(golden, 'utf8') !== snapshot) {
      console.error(`[runner] DIFF: ${name}`);
      diffs += 1;
    }
  }
  console.log(`[runner] Done. ${files.length} scenarios.`);
  return diffs;
}

async function runBatch() {
  let commands = 0;
  let diffs = 0;
  for await (const raw of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
    const line = raw.trim();
    if (!line) continue;
    const parts = line.split('\t');
    if (parts.length !== 3) {
      console.error(`[runner] batch: bad command (need dict<TAB>scen<TAB>golden): ${line}`);
      process.exit(2);
    }
    try {
      diffs += processDir(parts[0], parts[1], parts[2]);
    } catch (e) {
      // the command produced nothing; the frame still ends it, and the caller finds no output
      console.error(`[runner] FAIL: ${e instanceof Error ? e.message : String(e)}`);
      console.log('[runner] Done. 0 scenarios.');
    }
    commands += 1;
  }
  console.log(`[runner] batch done — ${commands} command(s), ${diffs} total diff(s).`);
  process.exit(diffs > 0 ? 1 : 0);
}

const args = process.argv.slice(2);
if (args[0] === '--batch') {
  await runBatch();
} else if (args.length === 3) {
  const diffs = processDir(args[0], args[1], args[2]);
  if (diffs > 0) {
    console.error(`[runner] ${diffs} golden snapshot(s) differ — exiting 1`);
    process.exit(1);
  }
} else {
  console.error('[runner] usage: runner.mjs <dictDir> <scenDir> <goldenDir> | --batch');
  process.exit(2);
}
