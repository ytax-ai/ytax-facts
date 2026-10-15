// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2026 TRIPLE J AI LLC
// Contains original tax-rule material from the ytax project.
// See the release-root LICENSING.md for scope and separate licensing options.

// persisterCompat — accept the pre-sync persisted-JSON shape on the post-sync runtime.
//
// IRS-Public/fact-graph @ 5599f75b (re-vendored 2026-09-15) bumped upickle 3.1.0 -> 4.2.1
// (build.sbt). upickle 4 changed the DEFAULT encoding of `Option[T]`: `Some(x)` is now `x` and
// `None` is `null`, where upickle 3 wrote `[x]` and `[]`. `gov.irs.factgraph.types.Enum` is
// `Enum(value: Option[String], enumOptionsPath: String) derives ReadWriter` — its reader comes from
// the library, so the vendored Scala is byte-identical across the sync and yet every persisted
// `EnumWrapper` written under upickle 3 (`{"value": ["single"], ...}`) now fails to load with
// `upickle.core.Abort: expected string got sequence`. That is what turned node_test uniformly RED
// after the re-vendor: 6,206 corpus files carry 69,843 such values.
//
// Upstream's idiomatic fix is a `Migrations.scala` entry; that file is inside the frozen vendored
// tree (invariant #4), so the adaptation lives here, at OUR load chokepoints: `buildFactGraph`
// (every JS harness entry) and, on the JVM, `ScenarioRunner.extractFactsJson` (both runner
// entries). The corpus and its writers are left in the upickle-3 shape on purpose: the engine PR
// stays engine-only and both shapes load. `Enum` is the only persisted type with an `Option`
// field; `MultiEnum.values` is a `Set[String]` and stays an array under both versions.
//
// Pure: returns a new top-level object and new wrapper objects for the facts it rewrites; the
// caller's input is never mutated (setupFactGraph reads `existingFacts[prefix].item.items` after
// buildFactGraph returns).

// The corpus spells the long tag; the post-sync engine's own toJSON() writes the short one.
const ENUM_WRAPPER_TAGS = new Set([`gov.irs.factgraph.persisters.EnumWrapper`, `EnumWrapper`]);

type Wrapper = { $type?: unknown; item?: unknown };

export function normalizePersistedEnums<T extends object>(existingFacts: T): T {
  const out: Record<string, unknown> = {};
  for (const [path, raw] of Object.entries(existingFacts as Record<string, unknown>)) {
    const w = raw as Wrapper;
    const item = w?.item as { value?: unknown } | undefined;
    if (
      typeof w === `object` && w !== null &&
      ENUM_WRAPPER_TAGS.has(String(w.$type)) &&
      typeof item === `object` && item !== null &&
      Array.isArray(item.value)
    ) {
      const value = item.value as unknown[];
      if (value.length > 1) {
        // Never silently take [0]: an Enum holds one value, so this is a malformed fixture.
        throw new Error(`EnumWrapper at '${path}' has ${value.length} values; an Enum holds at most one`);
      }
      out[path] = { ...w, item: { ...item, value: value.length === 1 ? value[0] : null } };
    } else {
      out[path] = raw;
    }
  }
  return out as T;
}
