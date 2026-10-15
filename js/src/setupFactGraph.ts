// ytax Tax Rules
// ytax is a product and project of TRIPLE J AI LLC.
// Product website: https://ytax.ai
// Copyright (c) 2026 TRIPLE J AI LLC, solely in its original
// copyrightable contributions to this file.
//
// Contains original tax-rule material from the ytax project.
//
// The PolyForm Strict License 1.0.0 (LicenseRef-PolyForm-Strict-1.0.0)
// applies only to original copyrightable ytax contributions in this file
// that TRIPLE J AI LLC owns or is authorized to license. Other material
// in this file keeps its own status and terms.
//
// See the release-root LICENSE, LICENSING.md and legal/COMPONENT-SCOPE.md.
// Other permissions need a separate written agreement with
// TRIPLE J AI LLC: license@ytax.ai
//
// No rights are claimed in tax law, facts, methods, or public-domain
// material. Provided as is, without warranty; see LICENSE.
// This is not an official IRS release.
//
// Based on IRS-origin material.
// Upstream repository: IRS-Public/direct-file
// Upstream revision: e365f9f43446010af36cccf7edecc52953c00fe9
// Original path: direct-file/df-client/df-client-app/src/test/setupFactGraph.ts

// LOCAL ADAPTATION (js/fact-dictionary/VENDORED.md, "## Local adaptations"):
// upstream's setupFactGraph() built a `new InterceptingFactGraph(existingFacts)` --
// InterceptingFactGraph is a df-client UI class (window.location-aware save() hooks,
// flow-config-driven field clearing) that we do not vendor and will not vendor. Every
// change in this file exists to remove ONLY that one construction; the default-seeding
// behavior below (empty collections for every writable Collection fact, the filer UUIDs,
// the default email, the optional primary-filer TIN) is otherwise byte-for-byte what
// upstream wrote. See the inline comments at each changed line for the specific reason.
// `ConcretePath` is used only in a type position (`path as ConcretePath` below) --
// `import type` makes that explicit and guarantees esbuild/tsc elide it at transform time
// regardless of import mechanism, so it never resolves at runtime. It comes from the LOCAL
// engine-type shim (src/factgraphTypes.ts): the engine artifact ships no `.d.ts`, so this
// type cannot actually be imported from `factgraph.js` under tsc.
import type { ConcretePath } from './factgraphTypes.js';
// LOCAL ADAPTATION: the linked engine (`../engine/factgraph.js`) is, since the re-vendor of
// IRS-Public/fact-graph @ 5599f75b (2026-09-15), a Scala.js ES MODULE (`ModuleKind.ESModule`,
// `.mjs` output copied here by js/scripts/build-engine.sh). Its top-level exports are real
// `export { ... }` bindings, so the named import below resolves under node, tsx and vitest alike.
// (Before the sync it was closure-compiled CommonJS whose aliased `exports` assignments defeated
// Node's cjs-module-lexer, which is why this block used to go through `createRequire`; Node 18
// cannot `require()` an ES module, so that route is closed now.) The artifact ships no `.d.ts`
// and is build output, so tsc sees an untyped module: the single-line import keeps the one
// ts-ignore pinned to the specifier that raises TS7016.
// @ts-ignore TS7016 -- untyped Scala.js build artifact (see above)
import { CollectionFactory, DigestMetaWrapper, DigestNodeWrapper, DigestNodeWrapperFactory, EmailAddress, FactDictionaryConfig, FactDictionaryFactory, GraphFactory, TinFactory } from '../engine/factgraph.js';
import { CURRENT_TAX_YEAR } from './constants.js';
import { Path } from './flow/Path.js';
// was: `import { v4 as uuidv4 } from 'uuid';` -- see the `randomUUID()` comment below.
import { randomUUID } from 'node:crypto';
import { wrappedFacts, paths } from './generatedDictionary.js';
import { AbsolutePath } from '../fact-dictionary/Path.js';
import { createCollectionWrapper } from './persistenceWrappers.js';
import { normalizePersistedEnums } from './persisterCompat.js';

const writableFactPaths = wrappedFacts.filter(({ writable }) => !!writable).map(({ path }) => path as AbsolutePath);

function existingFactsHasEmail(existingFacts: object) {
  // `Object.hasOwn` is Node's own native replacement for upstream's `hasOwn` polyfill
  // (`../utils/polyfills.ts`); that file's own header says it exists only for "functions
  // we can't use because unsupported on older browsers" -- irrelevant in this Node-only
  // test harness, so it is not vendored at all.
  return Object.hasOwn(existingFacts, `/email`);
}

/**
 * LOCAL ADDITION, not upstream: the one piece of `InterceptingFactGraph`'s constructor that
 * matters here (everything else in that class is UI plumbing) -- build the plain engine
 * graph the same way `InterceptingFactGraph` did internally, using our linked engine
 * artifact directly instead of a df-client wrapper class. See
 * `direct-file/df-client/df-client-app/src/factgraph/InterceptingFactGraph.ts` (vendored
 * nowhere, read only for this recipe) lines 117-133 at the pinned SHA for the original.
 *
 * EXPORTED (unit `js-batch-gate`, 2026-08-22) so a JVM-runner-EQUIVALENT snapshot driver can
 * build the graph WITHOUT `setupFactGraph`'s default seeding. That seeding — empty collections
 * for every writable Collection fact, two filer UUIDs, `/email`, the primary filer's TIN — is a
 * df-client UI convenience with NO counterpart in `ScenarioRunner.resolveScenario`, which does
 * exactly `InMemoryPersister(json)` -> `Graph(dictionary, persister)` -> `checkPersister()` and
 * nothing else. A scenario that omits `/email` gets a `/email` row (plus `/emailString`, plus
 * anything downstream) on the seeded path and none on the JVM; a scenario whose primary filer
 * has no TIN gets a fabricated `123456789` — and `/filers/*\/tin` IS a spine-registry member
 * (`dictionary/manifest/spine-registry.tsv`), so that seed would surface as a `check_spine.py`
 * "new-member" FAIL invented by the harness rather than by the dictionary. `js/scripts/
 * scenario-snapshots.ts` calls THIS function directly for that reason. Nothing else changes:
 * the only edit is the `export` keyword. [2026-09-15: the node-test driver,
 * `js/scripts/node-test-snapshots.ts`, now builds through `setupUnseededFactGraph` below for
 * the same reason — the seeding was NOT harmless there either.]
 *
 * SECOND PARAMETER (unit `js-default`, 2026-08-22), defaulting to the statically-imported L1
 * `wrappedFacts` so every existing caller is byte-for-byte unaffected: the fact list may be
 * supplied by the caller. That is the second of the two blocks that kept the L2 strategy spine
 * leg JVM-only — the graph builder reached its fact list through a static import of the SINGLE
 * generated tree, so there was no per-run way to point one process at another one.
 * `js/scripts/scenario-snapshots.ts --generated <dir>` now loads a different generated tree
 * (fact-dictionary/generated-l2/, built from "dictionary/ty2025:dictionary/ty2025-strategies")
 * and hands its `wrappedFacts` in here. It is a PARAMETER, never module-level mutable state:
 * one process resolves against exactly one dictionary, chosen at the call site, so an L1-only
 * leg can never pick up an L2 fact through a leaked global.
 */
// ONE DICTIONARY PER FACT LIST (2026-09-27). Building the FactDictionary from ~20,000 digests took
// ~1.1-1.5 s and was repeated for every case a driver resolved, which made it most of a node-test
// run (a selected resolve is ~2 ms). The dictionary is the graph's read-only schema — Direct File
// builds it once per session and a graph per return — so it is built once per fact list and reused.
const dictionaryCache = new WeakMap<object, unknown>();
function factDictionaryFor(factsList: typeof wrappedFacts) {
  let factDictionary = dictionaryCache.get(factsList);
  if (factDictionary === undefined) {
    const meta = new DigestMetaWrapper(CURRENT_TAX_YEAR).toNative();
    const digestFacts = factsList.map((fact) =>
      DigestNodeWrapperFactory.toNative(
        // 5599f75b added overrideCondition / overrideDefault to the constructor. The generator emits
        // no <Override>, so both are an explicit null (an omitted argument would be undefined).
        new DigestNodeWrapper(fact.path, fact.writable, fact.derived, fact.placeholder, null, null)
      )
    );
    const config = FactDictionaryConfig.create(meta, digestFacts);
    factDictionary = FactDictionaryFactory.fromConfig(config);
    dictionaryCache.set(factsList, factDictionary);
  }
  return factDictionary;
}

export function buildFactGraph(existingFacts: object, factsList: typeof wrappedFacts = wrappedFacts) {
  const factDictionary = factDictionaryFor(factsList) as ReturnType<typeof FactDictionaryFactory.fromConfig>;
  // upickle 4 (5599f75b) reads Enum.value as `"x"` / null; the corpus persists upickle 3's `["x"]`.
  // Rewritten here, the one JS load chokepoint — persisterCompat.ts carries the full account.
  const existingFactJsonString = JSON.stringify(normalizePersistedEnums(existingFacts));
  // 5599f75b removed GraphFactory.apply(dictionary, persister) (a 2-argument call would now bind to
  // the 1-argument apply and silently drop the persister). fromJSON builds the identical graph:
  // `new JSGraph(dictionary, InMemoryPersister(json))`, which is what JSPersister.create(json) fed.
  return GraphFactory.fromJSON(factDictionary, existingFactJsonString);
}


// A NESTED collection the scenario persisted concretely (`/casualtyEvents/#e/properties`) is
// keyed by its concrete path, so `hasOwn` on the abstract path misses it and the default seed
// would set() the populated collection empty. Every persisted key's abstract path, once.
function persistedAbstractPathsOf(existingFacts: object): Set<string> {
  return new Set(Object.keys(existingFacts).map((key) => Path.fromConcretePath(key as ConcretePath) as string));
}

/**
 * LOCAL ADDITION (2026-09-15): the node-test graph — build + fixture validation,
 * and NO default seeding. This is `setupFactGraph` with its seeding half split off; the
 * validation half is unchanged, and `setupFactGraph` below is now exactly this call followed by
 * the seeding, so every seeded caller is byte-for-byte unaffected.
 *
 * WHY. `js/scripts/node-test-snapshots.ts` (the default `node_test.py` engine, and the
 * fixture-flip census driver) used to build through `setupFactGraph`. When a case persisted no
 * `/filers`, that seeded an EMPTY collection for every writable Collection fact, two filers, and
 * a primary TIN; it always seeded `/email`. `ScenarioRunner.resolveScenario` (the JVM runner)
 * seeds none of it: `InMemoryPersister(json)` -> `Graph(dictionary, persister)` ->
 * `checkPersister()`. A seeded empty collection is Complete, so every `IsComplete(<collection>)`
 * read true on JS and false on the JVM, and a fixture pinning the wrong value passed on JS.
 * Five did, and only the JVM cross-check caught them.
 *
 * The one intentional asymmetry with the JVM: the validation below (unknown path, non-writable
 * path, bad collection id, `checkPersister()` issues) THROWS, where the runner snapshots
 * anyway. It never changes a resolved value; it only turns a malformed fixture red on JS.
 */
export function setupUnseededFactGraph(existingFacts = {}, factsList: typeof wrappedFacts = wrappedFacts) {
  // was: `new InterceptingFactGraph(existingFacts)` -- see the file-header comment.
  // factsList: the constraint harness (dictionary/FACT-CONSTRAINT.md §9) passes the tree composed
  // with the test-only `*-constraints` overlay. The overlay adds derived facts only, so the
  // writable checks below against the shipping lists stay exact.
  const factGraph = buildFactGraph(existingFacts, factsList);

  for (const path of Object.keys(existingFacts)) {
    const absolutePath = Path.fromConcretePath(path as ConcretePath);

    if (!paths.includes(absolutePath)) {
      throw new Error(`Existing facts include unrecognized fact '${path}`);
    }

    // Flag any attempts to write to unwritable paths
    if (!writableFactPaths.includes(absolutePath)) {
      throw new Error(`Existing facts included non-writable fact ${path}`);
    }

    // Flag any invalid collection ids in paths
    if (Path.isAbstract(absolutePath)) {
      const collectionIdMatches = path.match(/#[0-9a-z-]+/g);
      if (!collectionIdMatches) {
        throw new Error(`Collection path appears malformed.  Unable to identify collection ID in path '${path}'`);
      }
      // Each collection id must exist in ITS enclosing collection; for a nested collection
      // (`/casualtyEvents/#e/properties/#p/leaf`) the inner collection's persisted path is the
      // concrete path up to that id (`/casualtyEvents/#e/properties`).
      const segments = path.split(`/`);
      for (let i = 0; i < segments.length; i++) {
        if (!segments[i].startsWith(`#`)) continue;
        const collectionId = segments[i].slice(1);
        const prefix = segments.slice(0, i).join(`/`);
        const collection = (existingFacts as Record<string, ReturnType<typeof createCollectionWrapper>>)[prefix];
        if (!collection) {
          throw new Error(`Collection path '${path}' names collection '${prefix}', which the existing facts do not persist`);
        }
        if (!collection.item.items.includes(collectionId)) {
          throw new Error(`Collection id in path '${path}' was not found in collection '${prefix}'`);
        }
      }
    }
  }

  const existingFactIssues = factGraph
    .checkPersister()
    .map((issue: { message: string; path: string }) => `${issue.message} \`${issue.path}\``)
    .join(`\n`);
  if (existingFactIssues.length > 0) {
    throw new Error(`The test data does not align with the fact dictionary ...\n${existingFactIssues}`);
  }

  return { factGraph };
}

export function setupFactGraph(existingFacts = {}) {
  const { factGraph } = setupUnseededFactGraph(existingFacts);

  const persistedAbstractPaths = persistedAbstractPathsOf(existingFacts);
  const hasPrimaryFiler = factGraph.get(Path.concretePath(`/primaryFiler`, null)).complete;
  // Respect an explicitly persisted filer collection even when its primary designation is
  // intentionally unanswered. Replacing it with seeded UUIDs calls set() as a collection
  // removal (unsupported by the engine) and, more importantly, destroys the incomplete state
  // that fixtures such as Schedule H's attribution-before-designation case are testing.
  const hasPersistedFilers = Object.hasOwn(existingFacts, `/filers`);
  if (!hasPrimaryFiler && !hasPersistedFilers) {
    // Seed only the collections the scenario did NOT persist: set() on an already-populated
    // collection is a removal, which the engine refuses ("Cannot use set() to remove items"),
    // and a fixture that persists an intake collection without a filer (a bare Schedule K-1 or
    // 1099 document) is a legitimate minimal shape.
    const collections = wrappedFacts
      .filter((f) => f.writable?.typeName === `Collection`)
      .map((f) => f.path)
      .filter((c) => !Object.hasOwn(existingFacts, c) && !persistedAbstractPaths.has(c));
    collections.map((c) => factGraph.set(c, CollectionFactory([])));

    const filersPath = Path.concretePath(`/filers`, null);
    // was: `uuidv4()` from the `uuid` npm package -- Node's own `crypto.randomUUID()`
    // (stable since Node 14.17/16) produces an equivalent RFC 4122 v4 UUID string, so no
    // new dependency is added for this one call.
    const primaryFilerId = randomUUID();
    const secondaryFilerId = randomUUID();
    factGraph.set(filersPath, CollectionFactory([primaryFilerId, secondaryFilerId]));

    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
    factGraph.set(Path.concretePath(`/filers/*/isPrimaryFiler`, primaryFilerId), true);
    factGraph.set(Path.concretePath(`/filers/*/isPrimaryFiler`, secondaryFilerId), false);
    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
  }

  const emailFact = factGraph.get(Path.concretePath(`/email`, null));
  if (!emailFact.complete) {
    factGraph.set(Path.concretePath(`/email`, null), EmailAddress(`user.0000@example.com`));
    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
  }

  const currentPrimaryFiler = factGraph.get(Path.concretePath(`/primaryFiler`, null));
  if (currentPrimaryFiler.complete) {
    const primaryTin = factGraph.get(Path.concretePath(`/primaryFiler/tin`, null));
    if (primaryTin.complete) return { factGraph };
    // `TinFactory` (like every other `*Factory` validating constructor our engine
    // exports -- DollarFactory, EnumFactory, DayFactory, ...) returns a JSEither, not the
    // raw Tin value: confirmed empirically against js/engine/factgraph.js, which is the
    // bare `sbt fullLinkJS` output with no convenience wrapper
    // layer. The officially published `@irs/js-factgraph-scala` npm package upstream
    // depends on apparently unwraps this for its own `.set()` (or ships a JS-side helper
    // that does); ours does not, so `.right` is taken explicitly here. `.set()` throws a
    // clear "expecting 'Tin', received 'JSEither$Right'" error otherwise -- verified by
    // reproducing it, not guessed.
    factGraph.set(Path.concretePath(`/primaryFiler/tin`, null), TinFactory(`123456789`).right);
    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
  }

  return { factGraph };
}

/**
 * Deprecated! Legacy tests expect that we don't have tin/primary filers in our fact graph
 * but that isn't an accurate representation of the world. Try to use the above setup whenever possible.
 */
export function setupFactGraphDeprecated(existingFacts = {}) {
  const persistedAbstractPaths = persistedAbstractPathsOf(existingFacts);
  // was: `new InterceptingFactGraph(existingFacts)` -- see the file-header comment.
  const factGraph = buildFactGraph(existingFacts);
  const numExistingFacts = Object.keys(existingFacts).length;

  // These conditions are totally legacy but there are 100s of tests that rely on them existing like this.
  //
  // This basically ensures that there are two filers and one is primary which is also what the backend now does
  // in every environment.
  if (numExistingFacts === 0 || (numExistingFacts === 1 && existingFactsHasEmail(existingFacts))) {
    // Seed only the collections the scenario did NOT persist: set() on an already-populated
    // collection is a removal, which the engine refuses ("Cannot use set() to remove items"),
    // and a fixture that persists an intake collection without a filer (a bare Schedule K-1 or
    // 1099 document) is a legitimate minimal shape.
    const collections = wrappedFacts
      .filter((f) => f.writable?.typeName === `Collection`)
      .map((f) => f.path)
      .filter((c) => !Object.hasOwn(existingFacts, c) && !persistedAbstractPaths.has(c));
    collections.map((c) => factGraph.set(c, CollectionFactory([])));

    const filersPath = Path.concretePath(`/filers`, null);
    const primaryFilerId = randomUUID();
    const secondaryFilerId = randomUUID();
    factGraph.set(filersPath, CollectionFactory([primaryFilerId, secondaryFilerId]));

    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
    factGraph.set(Path.concretePath(`/filers/*/isPrimaryFiler`, primaryFilerId), true);
    factGraph.set(Path.concretePath(`/filers/*/isPrimaryFiler`, secondaryFilerId), false);
    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
  }

  const emailFact = factGraph.get(Path.concretePath(`/email`, null));
  if (!emailFact.complete) {
    factGraph.set(Path.concretePath(`/email`, null), EmailAddress(`user.0000@example.com`));
    // no save(): since fact-graph 5599f75b Graph.set() saves itself, and save() is not exported to JS
  }

  return { factGraph };
}
