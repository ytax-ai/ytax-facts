# `schema/` — the single source

The five operations are defined **once** here as JSON Schemas. The REST OpenAPI document
(`server/generated/openapi.json`) and the MCP tool definitions (`server/generated/mcp_tools.json`) are **generated**
from these files — never hand-written twice. The `[gate: schema-drift]` step
regenerates both and requires them to be **byte-identical**, so the two surfaces cannot drift.

## Layout

- `common/` — the shared shapes: `facts.schema.json` (the **derivative-only** fact set),
  `response-envelope.schema.json`, `errors.schema.json` (codes + refusals), `citation.schema.json`,
  `compute-request.schema.json` (`tax_year` + `facts`|`return_id`).
- `operations/manifest.json` — the **single list** of the five operations (name, REST path/method,
  request/response schema refs). Both generators read it, so the operation set is defined once.
- `operations/<op>.request.schema.json` / `<op>.response.schema.json` — per-operation shapes.
- `rename-table.json` — **data**: maps this repo's derivative service fact fields to the dictionary's
  writable fact paths (validated to exist at the engine pin). Not code logic.

## Invariants encoded here (structurally, not by policy)

- **No identifiers, ever.** `facts.schema.json` has no fields for names, addresses, TIN digits, or
  birth days, and `additionalProperties:false` at every level makes them **impossible to add** — only
  `tin_type`, `birth_year`, `birth_month`. Enforced by `tests/test_schema.py`.
- **Integer cents only.** Every money field is `#/$defs/cents` (integer).
- **`tax_year` is a field**, never part of a path or tool name.
- **Provenance is the payload.** Every response carries the envelope (engine version, dictionary
  hash, input hash, per-line citations). **World #1:** no accuracy claims, no recommendation
  language — provenance only.

## Regenerating

```
python3 server/scripts/generate_openapi.py       # -> server/generated/openapi.json
python3 server/scripts/generate_mcp_tools.py     # -> server/generated/mcp_tools.json
```

Both are deterministic; committing a schema change **without** regenerating (or hand-editing a
generated file) turns the gate red. Generated files are self-contained (local `$ref`s bundled into
`$defs` by `scripts/schema_bundle.py`) so MCP/OpenAPI consumers need no external fetches.
