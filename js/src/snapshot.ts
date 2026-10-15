// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original tax-rule material from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

import { readFileSync, writeFileSync } from 'node:fs';
// scalaListToJsArray is a plain wire-format converter (not a validating `*Factory` --
// no JSEither trap here; confirmed empirically against the linked engine). Sourced from our
// own linked engine artifact, same as setupFactGraph.ts.
// eslint-disable-next-line node/no-missing-import
import { scalaListToJsArray } from '../engine/factgraph.js';
import { createDayWrapper } from './persistenceWrappers.js';
import { resolvePeriodDates } from '../scripts/periodDates.js';

export interface SnapshotRow {
  path: string;
  completeness: 'Complete' | 'Placeholder';
  type: string;
  value: string;
}

/** The JVM runner's own default when no scenario-supplied /todayOverride exists
 * (the JVM runner's ScenarioRunner.scala under runner/src/main/scala, `pinnedToday`).
 * Kept in lockstep with that literal so a JS-vs-JVM differential run pins the same date
 * unless RUNNER_TODAY overrides both sides identically. */
export const DEFAULT_PINNED_TODAY = '2026-06-13';

/**
 * Mirror the JVM runner's `extractFactsJson`: inject a `/todayOverride` DayWrapper when the
 * scenario doesn't supply its own, so date-derived facts (ages, filing deadlines, ...) resolve
 * identically regardless of the wall-clock day either engine actually runs on. Never mutates
 * the input; returns it unchanged (same reference) when a `/todayOverride` is already present.
 */
export function withTodayOverride(
  facts: Record<string, unknown>,
  pinnedToday: string = process.env.RUNNER_TODAY ?? DEFAULT_PINNED_TODAY
): Record<string, unknown> {
  if (Object.hasOwn(facts, '/todayOverride')) return facts;
  return { ...facts, '/todayOverride': createDayWrapper(pinnedToday) };
}

/** Serialise to the exact format the JVM runner emits: path\tcompleteness\ttype\tvalue, path-sorted. */
export function snapshotToTsv(rows: SnapshotRow[]): string {
  return (
    [...rows]
      .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0))
      .map((r) => `${r.path}\t${r.completeness}\t${r.type}\t${r.value}`)
      .join('\n') + '\n'
  );
}

// The JVM runner's own path-skip (ScenarioRunner.resolveScenario): /todayOverride is the
// test-harness date pin, not a fact under test -- keeping it out of the snapshot means the
// pin itself never shows up as a spurious diff line.
const EXCLUDED_PATHS = new Set(['/todayOverride']);

/**
 * The JVM's own class-boxing artifact, not a JS quirk: on the JVM every fact whose Scala
 * static type is Int boxes to `java.lang.Integer` regardless of the value's actual magnitude
 * (`ScenarioRunner.formatValue` does a bare `v.getClass.getSimpleName`, no normalization).
 * Scala.js instead picks the *narrowest* JS-representable boxed class for small values
 * (`java.lang.Byte` for 0, `java.lang.Short` for 1961, ...) -- confirmed empirically against
 * `js/engine/factgraph.js`. The JVM
 * baselines never emit "Byte"/"Short"/"Long"
 * for any of ~134k BigDecimal/Integer rows, only ever "Integer".
 *
 * `Long` is deliberately NOT in this set (a review finding). `Byte` and `Short` were
 * both empirically observed as JS-side boxing artifacts of a real `Integer`-typed fact --
 * `Long` never was (re-confirmed across all 161 `scenarios/upstream/{generic,ty2024}/*.json` scenarios: the
 * JS engine's raw `typeName` set is exactly `{..., Byte, ..., Short, ...}`, never `Long`).
 * Unlike Byte/Short, `Long` is a genuinely
 * different-width numeric type, not merely a narrower boxing of the same value -- folding it
 * in without evidence would mean a REAL future divergence (JS emitting `Long` where the JVM
 * says `Integer`) gets silently equalized here and the gate passes when it should fail. If a
 * genuine JS-side `Long` boxing artifact is ever observed, add it back with the concrete
 * example recorded in this comment -- never speculatively.
 */
const INTEGER_BOXING_CLASSES = new Set(['Byte', 'Short', 'Integer']);

/**
 * `res.typeName` is a Java Class OBJECT (`.toString()` renders `"class gov.irs...Foo"`), not a
 * plain string -- verified empirically. The JVM runner's own `formatValue` just
 * does `v.getClass.getSimpleName`, i.e. the last dot-segment of the fully qualified name, with
 * NO further remapping (mangled Scala names like `$colon$colon` pass straight through --
 * confirmed identical in the committed baselines, which literally contain that mangled string
 * as the type column for List-typed facts). The only normalization this project's own JVM
 * source lacks but the JS side needs is the numeric-boxing fold above.
 */
function simpleTypeName(typeName: unknown): string {
  let raw: string;
  try {
    raw = (typeName as { toString?: () => string })?.toString?.() ?? String(typeName);
  } catch {
    raw = String(typeName);
  }
  const stripped = raw.replace(/^class\s+/, '');
  const simple = stripped.includes('.') ? (stripped.split('.').pop() as string) : stripped;
  return INTEGER_BOXING_CLASSES.has(simple) ? 'Integer' : simple;
}

/** The JVM runner escapes embedded newlines so every fact occupies exactly one TSV line
 * (`ScenarioRunner.formatValue`: `.replace("\n","\\n").replace("\r","\\r")`) -- Address values
 * are the case that actually exercises this (multi-line street/city/zip rendering). */
function renderValue(value: unknown): string {
  return String(value).replace(/\n/g, '\\n').replace(/\r/g, '\\r');
}

/** Resolve one concrete (non-wildcard) path to a snapshot row, or null if it's Incomplete /
 * unresolvable in this scenario -- the JVM runner's `resolveScenario` silently skips both
 * (`case Result.Incomplete => ()` and a swallowed `catch case _: Exception => ()`), so an
 * Incomplete fact never appears as a row at all; it's not a third completeness value emitted
 * in the TSV, despite the JVM's own `Result` trichotomy having that case. */
function rowForConcretePath(factGraph: any, path: string): SnapshotRow | null {
  let res;
  try {
    res = factGraph.get(path);
  } catch {
    return null;
  }
  if (res == null) return null;
  if (res.complete) {
    return { path, completeness: 'Complete', type: simpleTypeName(res.typeName), value: renderValue(res.get) };
  }
  if (res.hasValue) {
    return { path, completeness: 'Placeholder', type: simpleTypeName(res.typeName), value: renderValue(res.get) };
  }
  return null;
}

/**
 * List every concrete collection-item id under a collection root path (e.g. `/form1099Rs`),
 * for expanding a wildcard fact path (`/form1099Rs/*\/filer`) into one row per item -- mirrors
 * the JVM's `Graph.getCollectionPaths`/`Path.populateFirstWildcard`, which resolves the
 * collection's own Vector of `CollectionItem`s (`engine/fact-graph-scala/shared/src/main/
 * scala/gov/irs/factgraph/Path.scala`, read-only). The JS engine has no direct
 * `getCollectionPaths` (verified empirically -- Graph's own prototype has no such member); the
 * equivalent is calling `.getItemsAsStrings()` on the collection fact's resolved `Collection`
 * value, which returns a Scala `List` requiring `scalaListToJsArray` to read as a JS array
 * (also verified empirically -- the raw return is a `$colon$colon`/`Nil` linked-list node).
 */
function collectionItemIds(factGraph: any, collectionPath: string): string[] {
  let res;
  try {
    res = factGraph.get(collectionPath);
  } catch {
    return [];
  }
  if (!res || (!res.complete && !res.hasValue)) return [];
  try {
    const v = res.get;
    if (!v || typeof v.getItemsAsStrings !== 'function') return [];
    return scalaListToJsArray(v.getItemsAsStrings()) as string[];
  } catch {
    return [];
  }
}

/**
 * Resolve every fact in `paths` against `factGraph` and collect the rows the JVM runner would
 * emit for the same scenario: Complete/Placeholder only (Incomplete is omitted, see
 * `rowForConcretePath`), `/todayOverride` excluded, and every wildcard path expanded into one
 * concrete row per actual collection item instead of being resolved literally (which the engine
 * cannot do -- `*` is not a real path segment). The FEDERAL dictionary has exactly one `/*\/`
 * per wildcard path (confirmed empirically against every path in `facts-manifest.json`: all
 * 1,375 wildcard paths have exactly one); composed STATE targets do not (see below).
 *
 * NESTED WILDCARDS ARE EXPANDED (unit `ny-node-tests`, 2026-08-22). This
 * function used to THROW on a second `/*\/`, and its own comment named the condition for
 * changing that: "If a future dictionary unit ever introduces one ... Extend resolveAll's
 * wildcard expansion to handle nested collections before adding a path shaped like this."
 * The composed state target `state/NY/ty2025` is that unit. Form Y-203 declares a collection
 * INSIDE a collection item -- `/ny/y203/returns/*\/wageAllocations` and
 * `/ny/y203/returns/*\/businessAllocations` -- giving 36 nested-wildcard fact paths (measured
 * against the generated composed tree, not asserted). Every one of them made the OLD code
 * throw, which is why no snapshot of the composed NY dictionary could be taken at all: the
 * first such path aborted the whole scenario, so `scenario-snapshots.ts` wrote no TSV.
 *
 * The expansion is LEFT-TO-RIGHT and recursive, which is not an implementation detail: a
 * nested collection's item ids are a property of the OUTER item that owns it, so the inner
 * collection path must already be concrete before its ids can be read. The id cache is
 * therefore keyed on the fully concrete collection path (`/outer/#uuid/inner`), never on the
 * wildcard form -- keying it on the wildcard form would serve one outer item's inner ids to
 * every other outer item, which is a silent wrong-answer, not a crash. Federal behavior is
 * unchanged by construction: with exactly one `/*\/` the recursion bottoms out after one
 * level and emits precisely the rows the previous loop emitted, in the same order.
 */
export function resolveAll(factGraph: any, paths: string[]): SnapshotRow[] {
  const rows: SnapshotRow[] = [];
  const collectionIdCache = new Map<string, string[]>();

  const idsFor = (collectionPath: string): string[] => {
    let ids = collectionIdCache.get(collectionPath);
    if (ids === undefined) {
      ids = collectionItemIds(factGraph, collectionPath);
      collectionIdCache.set(collectionPath, ids);
    }
    return ids;
  };

  const expand = (p: string): void => {
    const starIdx = p.indexOf('/*/');
    if (starIdx === -1) {
      const row = rowForConcretePath(factGraph, p);
      if (row) rows.push(row);
      return;
    }
    const collectionPath = p.slice(0, starIdx);
    const suffix = p.slice(starIdx + 2); // drop "/*", keep the leading "/" of the rest
    for (const id of idsFor(collectionPath)) {
      expand(`${collectionPath}/#${id}${suffix}`);
    }
  };

  for (const p of paths) {
    if (EXCLUDED_PATHS.has(p)) continue;
    expand(p);
  }

  return rows;
}

/** Concrete path -> its wildcard universe form (`/c/#id/x` -> `/c/*\/x`), every item segment. */
export function wildcardForm(path: string): string {
  return path.replace(/\/#[^/]+/g, '/*');
}

/**
 * SELECTED resolution (SPEED-3, 2026-09-27): the rows `resolveAll(factGraph, universe)` would
 * emit, restricted to (a) the concrete `paths` asked for and (b) every row whose path carries
 * one of the `probeItems` ids (`#<id>`) as a segment. It is a FILTER over resolveAll's output,
 * never a different resolution: a row is emitted here only if resolveAll would emit the same
 * row for the same graph, and every requested row resolveAll would emit is emitted.
 *
 * Why (b): scripts/node_test.py's Incomplete-by-absence guard asks whether an asserted
 * collection item id appears as a segment of ANY snapshot row (a mistyped item id must not read
 * as a refusal). Item ids only enter rows through wildcard expansion, so expanding every
 * wildcard universe path and resolving just the expansions that carry a probe id reproduces that
 * segment set exactly for the probed ids.
 *
 * Exactness rules, each mirroring resolveAll:
 *  - `/todayOverride` is excluded;
 *  - a requested path whose wildcard form is not in `universe` gets no row (resolveAll never
 *    asks the graph for it, whatever `factGraph.get` would say);
 *  - a concrete item path resolves only if, left to right, every item id is among its (already
 *    concrete) collection's items -- resolveAll only ever builds such paths.
 * It relies on the engine resolving lazily: a fact's result must not depend on which other facts
 * were asked first. node_test.py's full-corpus two-mode proof is what established that.
 */
export function resolveSelected(
  factGraph: any,
  universe: string[],
  paths: string[],
  probeItems: string[] = []
): SnapshotRow[] {
  const universeSet = new Set(universe);
  const collectionIdCache = new Map<string, string[]>();
  const idsFor = (collectionPath: string): string[] => {
    let ids = collectionIdCache.get(collectionPath);
    if (ids === undefined) {
      ids = collectionItemIds(factGraph, collectionPath);
      collectionIdCache.set(collectionPath, ids);
    }
    return ids;
  };
  const byPath = new Map<string, SnapshotRow>();
  const emit = (p: string): void => {
    if (byPath.has(p)) return;
    const row = rowForConcretePath(factGraph, p);
    if (row) byPath.set(p, row);
  };
  // Would resolveAll's left-to-right expansion ever build this concrete path?
  const reachable = (p: string): boolean => {
    const segs = p.split('/');
    for (let i = 0; i < segs.length; i++) {
      if (!segs[i].startsWith('#')) continue;
      if (!idsFor(segs.slice(0, i).join('/')).includes(segs[i].slice(1))) return false;
    }
    return true;
  };

  for (const p of paths) {
    if (EXCLUDED_PATHS.has(p) || p.includes('*')) continue;
    if (!universeSet.has(wildcardForm(p))) continue;
    if (!reachable(p)) continue;
    emit(p);
  }

  if (probeItems.length > 0) {
    const probeSegs = new Set(probeItems.map((id) => (id.startsWith('#') ? id : `#${id}`)));
    const expand = (p: string, hit: boolean): void => {
      const starIdx = p.indexOf('/*/');
      if (starIdx === -1) {
        if (hit) emit(p);
        return;
      }
      const collectionPath = p.slice(0, starIdx);
      const suffix = p.slice(starIdx + 2);
      for (const id of idsFor(collectionPath)) {
        expand(`${collectionPath}/#${id}${suffix}`, hit || probeSegs.has(`#${id}`));
      }
    };
    for (const p of universe) {
      if (EXCLUDED_PATHS.has(p) || p.indexOf('/*/') === -1) continue;
      expand(p, false);
    }
  }

  return [...byPath.values()];
}

/**
 * The engine's own real fact-path universe: `dictionary/manifest/facts-manifest.json`
 * (a frozen contract: the engine's own dependency export, never a fresh XML parse). This is
 * deliberately NOT `fact-dictionary/generated/paths.js` -- verified empirically to be the
 * wrong source: `paths.js` is
 * produced by the vendored df-client generator's alias-expansion pass (`getExtendedPaths()`
 * in `generate.ts`, backed by `aliases.ts`), which synthesizes extra UI-convenience paths
 * that are NOT real Fact Graph paths at all -- e.g. `/address/city` as if `Address` had
 * per-field sub-facts, or per-collection-item aliases like
 * `/dependentWhoCausedContradictory8832Knockout/bothFilersNotClaiming`. Diffing a real JS
 * snapshot against a JVM baseline
 * surfaced ~800 such extra rows with no JVM counterpart at all. The JVM
 * runner's own `allPaths` comes from `dictionary.getPaths()` -- a straight parse of the real
 * XML (the JVM runner's ScenarioRunner.scala under runner/src/main/scala, line 34) -- and
 * `facts-manifest.json` is exactly that same set, committed with its baseline tag
 * (`generated.baseline_tag`), so it is the correct path universe to iterate for a snapshot
 * meant to diff against a JVM baseline.
 */
export function loadManifestPaths(): string[] {
  const manifestUrl = new URL('../../dictionary/manifest/facts-manifest.json', import.meta.url);
  const manifest = JSON.parse(readFileSync(manifestUrl, 'utf8')) as { facts: Record<string, unknown> };
  return Object.keys(manifest.facts);
}

// CLI: npx tsx src/snapshot.ts <scenario.json> <out.tsv>
if (process.argv[1]?.endsWith('snapshot.ts')) {
  const [, , scenarioPath, outPath] = process.argv;
  if (!scenarioPath || !outPath) {
    console.error('usage: npx tsx src/snapshot.ts <scenario.json> <out.tsv>');
    process.exit(1);
  }
  const scenario = resolvePeriodDates(JSON.parse(readFileSync(scenarioPath, 'utf8')));
  const facts = withTodayOverride(scenario.facts ?? scenario);
  // 2026-09-15: the runner's graph, no df-client seeding. This CLI is the JS side of
  // scripts/engine_differential.py; the seeded setupFactGraph made it compare a seeded JS graph
  // (empty collections, filers, TIN, /email) against the unseeded JVM ScenarioRunner graph.
  const { setupUnseededFactGraph } = await import('./setupFactGraph.js');
  const { factGraph } = setupUnseededFactGraph(facts);
  writeFileSync(outPath, snapshotToTsv(resolveAll(factGraph, loadManifestPaths())));
}
