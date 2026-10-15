# Vendored files from IRS Direct File

This is the provenance record for the files the JavaScript harness vendors from the IRS Direct
File repository: what was taken, from where, and every local change.

## Source

- Upstream repository: `IRS-Public/direct-file`
- Commit: `e365f9f43446010af36cccf7edecc52953c00fe9` (2026-06-11 15:58:44 -0400)
- Fetched: 2026-07-14, by a shallow sparse `git clone` over https of the paths below, so the
  bytes are upstream's exactly
- Upstream root of every path below: `direct-file/df-client/df-client-app/`

## 1. Fact-dictionary generator

### Files

From `src/fact-dictionary/generate-src/`, under `js/fact-dictionary/generate-src/`:
`generate.ts`, `readRawFacts.ts`, `processFactsToDigestWrapper.ts`, `dependencyGraph.ts`,
`subfields.ts`.

From `src/fact-dictionary/`, under `js/fact-dictionary/`: `FactTypes.ts`, `Path.ts`,
`aliases.ts` (`generate.ts` imports it for the alias-path tables of `getExtendedPaths()`;
unmodified).

Not vendored: `readMeFFactPaths.ts`, `readPdfFactPaths.ts`, `generateDependencyGraph.ts`,
`generateModuleGraph.ts`, `printOrphanedFacts.ts`, `verifyModuleDependencies.ts`,
`verifyPdfFactPaths.ts`, the `*.test.ts` files other than those in section 3, and the fixture
`generate-src/schedule3.xml`. The generator reads this repository's own `dictionary/ty2025`
XML through a symlink; nothing from it is copied.

### Local adaptations

1. `readRawFacts.ts`: `FACT_DICTIONARY_FOLDER` is `./fact-dictionary/generate-src/xml-src/`
   (upstream `./src/fact-dictionary/...`; this package has no `src/` level above
   `fact-dictionary/`).
2. `generate.ts`: the same `src/` prefix is dropped from the five output file names. The
   generation logic is unchanged.
3. `readRawFacts.ts`: `parseTagValue: false` is added to `XML_PARSER_OPTIONS`, next to
   upstream's `parseAttributeValue: false`. Without it the XML parser coerces tag text to
   numbers: `<String>0.</String>` became `0`, and every `<Dollar>` literal became a
   floating-point number. Tag text now stays a verbatim string.
4. `readRawFacts.ts` reads `FACT_DICTIONARY_SOURCE_DIR` and `generate.ts` reads
   `FACT_DICTIONARY_OUTPUT_DIR`, each defaulting to the paths above.
   `FACT_DICTIONARY_SOURCE_DIR` may list several directories separated by `:`; they are read
   in order, as the JVM runner merges its dictionary directories, and a module file name found
   in two directories is refused.
5. Outside the vendored files, `js/scripts/generate-dictionary.sh` runs the generator, then
   compiles each generated `.ts` file to CommonJS with `esbuild --format=cjs --platform=node`,
   writes `generated/package.json` (`{"type": "commonjs"}`), creates `generated/` first, and
   recreates the `generate-src/xml-src` symlink. The generated tree and the symlink are not
   committed.

### Dependency pins

- `prettier` 2.8: Prettier 3's `format()` is asynchronous, and the vendored generator
  calls it synchronously.
- `stringify-object` 4: 7.x requires Node 22, and 3.3.0 does not escape backslashes (a
  regular-expression backreference such as `(?!\1)` in a `Match` pattern would become a legacy
  octal escape).

## 2. Test harness

### Files

From `src/test/`, under `js/src/`:

- `persistenceWrappers.ts`: byte-identical to upstream.
- `testData.ts`: identical except its import block (the path changes in item 6 below, and
  `constants.ts` in place of upstream's `constants/taxConstants.ts`).
- `setupFactGraph.ts`: adapted, see items 1 to 5 and 7 below.

From `src/flow/`, under `js/src/flow/`: `Path.ts`, identical except its one import line. It
is the runtime `Path` class (`concretePath`, `fromConcretePath`, `isAbstract`), a different
file from the type-only `js/fact-dictionary/Path.ts`.

Replaced, not vendored: `constants/taxConstants.ts` by `js/src/constants.ts`; the `uuid`
package and `utils/polyfills.ts` by Node built-ins.

### Local adaptations

1. `setupFactGraph.ts` builds a plain engine graph instead of upstream's
   `new InterceptingFactGraph(existingFacts)`, a browser-application class that is not
   vendored. Both call sites use a local `buildFactGraph(existingFacts)`, which repeats the
   graph-building steps of `InterceptingFactGraph`'s constructor (lines 117-133 at the pinned
   commit): `DigestMetaWrapper` → `DigestNodeWrapperFactory` → `FactDictionaryConfig.create` →
   `FactDictionaryFactory.fromConfig` → `JSPersister.create` → `GraphFactory.apply`. The seeding
   that follows (empty collections for every writable collection fact, the filer ids, the
   default email, the optional primary-filer TIN) is upstream's, unchanged.
   `buildFactGraph` also takes the fact list as an optional second parameter, so a caller can
   build from another generated tree.
2. Value imports come from the linked engine, `../engine/factgraph.js`, instead of the npm
   package `@irs/js-factgraph-scala`. The type-only import of `ConcretePath` keeps upstream's
   package name; the TypeScript transform removes it.
3. `TinFactory('123456789').right`: the linked engine's validating `*Factory` constructors
   return an either value, and `.set()` needs the value inside it. Passing the either value
   fails with `/filers/#<id>/tin is expecting 'class gov.irs.factgraph.types.Tin', received
   'class gov.irs.factgraph.monads.JSEither$Right' instead`.
4. `uuid`'s `v4` is replaced by `node:crypto`'s `randomUUID()`.
5. `hasOwn` from `utils/polyfills.ts` is replaced by `Object.hasOwn`.
6. Relative imports follow this tree, which has one directory level fewer than upstream's:
   `../flow/Path.js` becomes `./flow/Path.js` in `testData.ts` and `setupFactGraph.ts`, and
   `js/src/flow/Path.ts` imports `../../fact-dictionary/Path.js`.
7. Upstream's no-op statement `console;` (`setupFactGraph.ts` line 88) is not carried.
8. `js/src/constants.ts` exports only `CURRENT_TAX_YEAR`, the one constant the vendored files
   use, set to `'2025'` (upstream `'2024'`).

## 3. Structural tests and coverage reporter

### Files

From `src/fact-dictionary/`, under `js/test/factDictionaryTests/`:
`noCircularDeps.test.ts`, `noDuplicateFactPaths.test.ts`, `pathNaming.test.ts`.

From `src/test/`, under `js/src/`: `TaxLogicTestCoverageReporter.ts`.

### Local adaptations

1. The three tests' relative imports point to `../../fact-dictionary/...`. No other line
   changed.
2. `TaxLogicTestCoverageReporter.ts` keeps `reportTestedFactPaths` unchanged and removes
   `reportFunctionalFlowRoutes`, its two imports of upstream's screen-flow modules (not
   vendored) and the loop in `onFinished` that fed it.
3. `js/vitest.config.ts` registers the reporter; its HTML output (`coverage/`) is not
   committed.

## Development dependencies added

| Package | Version | License |
|---|---|---|
| `fast-xml-parser` | ^5.10.0 | MIT |
| `prettier` | ^2.8.8 | MIT |
| `stringify-object` | ^4.0.1 | BSD-2-Clause |
| `esbuild` | 0.28.1 | MIT |
| `assert-never` | ^1.4.0 | MIT |

`stringify-object` 4 brings `get-own-enumerable-property-symbols` (ISC), `is-obj` (MIT)
and `is-regexp` (MIT).

## Regenerating the dictionary

```bash
js/scripts/generate-dictionary.sh
```

It writes `js/fact-dictionary/generated/{facts,paths,wrappedFacts,submissionBlockingFacts,exportToStateFacts}.{ts,js}`
and `generated/package.json`, none of them committed.
