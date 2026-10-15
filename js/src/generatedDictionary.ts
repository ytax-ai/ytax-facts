// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original tax-rule material from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

// The runtime entry point for the L1 generated dictionary (js/fact-dictionary/generated/) in every
// module that tsx or vitest executes. js-heap (2026-09-26).
//
// WHY THIS EXISTS. generate-dictionary.sh writes each generated module twice: a `.ts` source
// (wrappedFacts.ts is ~42 MB) and an esbuild-built CommonJS `.js` next to it. A plain
// `import { wrappedFacts } from '../fact-dictionary/generated/wrappedFacts.js'` in a `.ts` file
// never reaches that `.js` under tsx: tsx maps a `.js` specifier from a TypeScript parent to the
// `.ts` sibling (it does the same for `require()` with a TypeScript parent), so every
// node-test and spine process transformed the 42 MB source again. Measured: the resolve hook
// sees `./fact-dictionary/generated/paths.ts`, and require.cache holds `.../paths.ts`.
//
// The `require` below is anchored at the generated tree's own package.json, so its parent is
// not a TypeScript file and tsx leaves the `.js` specifier alone: Node's own CommonJS loader
// loads the prebuilt `.js`, with no transform and no source map. Under vitest this module is
// transformed like any other, but the `require` is Node's, so vite never sees the generated
// code either. Every importer that ends up in one process gets the same `require.cache` entry,
// and so does a test that imports a generated `.js` directly: vitest.config.ts externalizes
// those, and Node's ESM loader reads CommonJS through that same cache.
//
// The types still come from the generated `.ts` files, through `import type`, which esbuild and
// tsc erase: nothing below imports the `.ts` at runtime.
import { createRequire } from 'node:module';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import type * as WrappedFactsModule from '../fact-dictionary/generated/wrappedFacts.js';
import type * as PathsModule from '../fact-dictionary/generated/paths.js';

// FACT_DICTIONARY_GENERATED_DIR (2026-09-27): a test driver that resolves against another generated
// tree (the constraint harness's overlay tree, a state target's tree) names it here, so the process
// loads THAT tree once instead of the L1 tree plus its own (~1 GB saved per node-test process). Unset,
// this is the L1 tree exactly as before.
const generatedDir = process.env.FACT_DICTIONARY_GENERATED_DIR;
const requireGenerated = createRequire(
  generatedDir
    ? pathToFileURL(join(resolve(generatedDir), 'package.json'))
    : new URL('../fact-dictionary/generated/package.json', import.meta.url)
);

export const { wrappedFacts } = requireGenerated('./wrappedFacts.js') as typeof WrappedFactsModule;
export const { paths, writablePaths } = requireGenerated('./paths.js') as typeof PathsModule;
