#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original tax-rule material from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

# Generate the JS fact dictionary from OUR living XML (dictionary/ty2025 by default).
# The upstream generator expects generate-src/xml-src/ — we symlink, never copy,
# so dictionary/ty2025 stays the single source of truth.
#
# --dict TAKES A ':'-SEPARATED LIST (unit `js-default`, 2026-08-22), exactly like the JVM
# runner's dict spec (`runner/run.sh --reset "dictionary/ty2025:dictionary/ty2025-strategies"`
# -> ScenarioRunner.parseFactCfgs). Combined with --out, that is how the L2 strategy layer
# gets its OWN generated tree:
#
#   js/scripts/generate-dictionary.sh \
#       --dict "$PWD/dictionary/ty2025:$PWD/dictionary/ty2025-strategies" \
#       --out  "$PWD/js/fact-dictionary/generated-l2"
#
# The L1 tree (js/fact-dictionary/generated/) is generated from dictionary/ty2025 ALONE and
# stays free of every /strategies/ fact — one-way layering, the same property the JVM
# gets from parseFactCfgs reading each named dir NON-RECURSIVELY. Never point --out at the L1
# tree for an L2 dict spec: the L1-only spine legs would then see L2 facts.
set -euo pipefail

# (2026-09-13): Node 18 sizes its V8 old-space heap FROM THE CGROUP LIMIT (measured on this
# box: bare 4,144 MB; inside an 8G systemd scope 2,096 MB), and THIS generator — 11,9xx facts
# through fast-xml-parser + prettier — is what died with "Reached heap limit" in the first census
# run under the gate's new memory cap. Pin the heap here too, so the cap bounds the process tree
# and not the generator's working set, no matter who launches this script. A caller's own
# NODE_OPTIONS wins (same contract as gate_bg.sh and scripts/node_heap.py).
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GEN_SRC="$REPO_ROOT/js/fact-dictionary/generate-src"
DICT_SOURCE="$REPO_ROOT/dictionary/ty2025"
GENERATED="$REPO_ROOT/js/fact-dictionary/generated"
DEFAULT_GENERATED="$REPO_ROOT/js/fact-dictionary/generated"
DICT_SOURCE_EXPLICIT=false
GENERATED_EXPLICIT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dict) DICT_SOURCE="${2:-}"; DICT_SOURCE_EXPLICIT=true; shift ;;
    --out) GENERATED="${2:-}"; GENERATED_EXPLICIT=true; shift ;;
    -h|--help)
      echo "usage: js/scripts/generate-dictionary.sh [--dict DIR[:DIR...]] [--out DIR]"
      exit 0
      ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Validate and absolutize EVERY element of the ':'-separated spec. `[[ -d ]]` and `cd`
# both take a single path, so the pre-list code would have declared "dictionary not found"
# for any perfectly valid two-dir spec.
DICT_SOURCE_ABS=""
IFS=':' read -r -a _dict_dirs <<< "$DICT_SOURCE"
for _d in "${_dict_dirs[@]}"; do
  [[ -n "$_d" ]] || continue
  [[ -d "$_d" ]] || { echo "dictionary not found: $_d (from --dict $DICT_SOURCE)" >&2; exit 1; }
  _abs="$(cd "$_d" && pwd -P)"
  DICT_SOURCE_ABS="${DICT_SOURCE_ABS:+$DICT_SOURCE_ABS:}$_abs"
done
[[ -n "$DICT_SOURCE_ABS" ]] || { echo "--dict named no directory: $DICT_SOURCE" >&2; exit 1; }
DICT_SOURCE="$DICT_SOURCE_ABS"

# LAYERING GUARD: a MULTI-DIRECTORY spec may NEVER be written into the default
# (L1) tree. The L1-only spine legs — upstream and every scenarios/units/* leg — resolve against
# js/fact-dictionary/generated/, and node_test's staleness marker is keyed on the dictionary XML,
# not on which SPEC produced the tree. So a hand-run `--dict "L1:L2"` with no --out would leave
# /strategies/ facts sitting in the L1 tree AND `js_generated_stale` would go on reading the
# unchanged marker as FRESH: the pollution would survive every later run, and check_spine.py's
# registry filter would keep the extra rows out of sight. Silent, durable, and invisible — the
# exact class this repo's corrections exist for. Refuse before anything is created, and name --out.
#
# Checked BOTH ways on purpose: `--out` omitted entirely, and `--out` pointed at the default path
# by hand. The second is the one a copy-pasted command produces.
if [[ "$DICT_SOURCE" == *:* ]]; then
  # Both dirs are created before the comparison so `cd && pwd -P` can normalise them: an
  # explicit `--out` naming a path that does not exist yet must still be recognised as the
  # default tree. Creating an empty gitignored directory is harmless — this script creates the
  # output tree anyway two lines below.
  mkdir -p "$GENERATED" "$DEFAULT_GENERATED"
  _out_is_default=false
  [[ "$GENERATED_EXPLICIT" == false ]] && _out_is_default=true
  if [[ "$(cd "$GENERATED" && pwd -P)" == "$(cd "$DEFAULT_GENERATED" && pwd -P)" ]]; then
    _out_is_default=true
  fi
  if [[ "$_out_is_default" == true ]]; then
    echo "REFUSING: --dict names more than one directory ($DICT_SOURCE) but --out is the DEFAULT" >&2
    echo "          L1 tree ($DEFAULT_GENERATED). The L1-only spine legs resolve against that" >&2
    echo "          tree and must never see an L2 /strategies/ fact (one-way layering)," >&2
    echo "          and node_test's staleness marker would not notice the pollution." >&2
    echo "          Pass an explicit --out, e.g. --out \"\$PWD/js/fact-dictionary/generated-l2\"." >&2
    exit 2
  fi
fi

mkdir -p "$GENERATED"
GENERATED="$(cd "$GENERATED" && pwd -P)"

# The vendored default generator historically reads this symlink. Explicit dictionaries use
# FACT_DICTIONARY_SOURCE_DIR and must not mutate shared checkout state during target gates.
if [[ "$DICT_SOURCE_EXPLICIT" == false ]]; then
  rm -f "$GEN_SRC/xml-src"
  ln -s "$REPO_ROOT/dictionary/ty2025" "$GEN_SRC/xml-src"
fi

# fs.writeFileSync (in the vendored generate.ts) does not create directories.
mkdir -p "$GENERATED"

cd "$REPO_ROOT/js"
FACT_DICTIONARY_SOURCE_DIR="$DICT_SOURCE" FACT_DICTIONARY_OUTPUT_DIR="$GENERATED" \
  node --import tsx fact-dictionary/generate-src/generate.ts

# LOCAL ADAPTATION (see js/fact-dictionary/VENDORED.md, "## Local adaptations"): the
# vendored generator emits TypeScript (facts.ts, paths.ts, wrappedFacts.ts,
# submissionBlockingFacts.ts, exportToStateFacts.ts) exactly as upstream does — that part
# of generate.ts is untouched. Our harness has no separate tsc build step for generated
# output, so we transpile those five files to plain CommonJS .js right here, outside the
# vendored generator, using esbuild (already a transitive devDependency via tsx/vite; now
# pinned directly too). This is the artifact the rest of the harness (setupFactGraph.ts,
# snapshot.ts, and the require()-based verification in task-3-brief.md Step 4) consumes.
for f in facts paths wrappedFacts submissionBlockingFacts exportToStateFacts; do
  npx esbuild "$GENERATED/$f.ts" --format=cjs --platform=node --outfile="$GENERATED/$f.js" --log-level=warning
done

# js/package.json declares "type": "module", so a plain .js file under it is parsed as
# ESM by default — but esbuild's --format=cjs output uses require()/exports.  Same fix
# already used for js/engine/package.json: a nested package.json pins this subtree back
# to CommonJS. generated/ is gitignored, so this is (re)written on every generate run.
cat > "$GENERATED/package.json" <<'EOF'
{"type": "commonjs"}
EOF

echo "generated $DICT_SOURCE -> $GENERATED"
