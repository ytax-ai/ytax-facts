// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original tax-rule material from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

// Local type declarations that mirror the public types of our Fact Graph engine
// artifact (js/engine/factgraph.js — the bare `sbt fullLinkJS` Scala.js output).
//
// WHY THIS FILE EXISTS: the engine artifact is a generated `.js`
// with NO companion `.d.ts`, so its types cannot be imported from it. The upstream
// world gets these from the published `@irs/js-factgraph-scala` npm package — but we
// do NOT vendor or install that package (our engine is the local Scala.js link, not
// the npm build). Importing a type from `@irs/js-factgraph-scala` therefore created a
// PHANTOM dependency: it "worked" only because every such import was type-only and
// esbuild elided it, so the first runtime value import from that specifier would have
// crashed, and — with no tsconfig — nothing type-checked it either. This module is the
// honest local home for those engine-mirroring types; import them from here, never
// from a `@irs/*` specifier that is not in package.json.

/**
 * A resolved (non-abstract) fact path — every `*` collection wildcard replaced by a
 * concrete `#<uuid>` member id. Modeled as the set of leading-slash path strings; the
 * engine treats it as an opaque string key. Matches how upstream's
 * `@irs/js-factgraph-scala` exposes `ConcretePath` (a `/`-rooted string), so the
 * `x as ConcretePath` casts and `Record<ConcretePath, …>` uses across the harness
 * behave identically to before.
 */
export type ConcretePath = `/${string}`;
