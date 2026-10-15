# Building ytax-facts

This package contains the IRS Fact Graph engine source at its upstream pin, with ytax changes, the complete federal TY2025 fact dictionary tree, the adapted XML-to-JavaScript dictionary generator, and one prebuilt artifact: the linked JavaScript engine `js/engine/factgraph.js` with the TypeScript runtime sources that load it. The ytax application is under `prep/`, with its own `prep/BUILD.md`; the printed-form field maps it fills IRS forms from are under `dictionary/pdf/2025` (the blank IRS forms are not shipped). The package does not include the private development harness, test corpora, governance records, or any other prebuilt artifact. The packaging script performs no sbt/npm build, full schema validation, runtime differential test, or tax test.

Use the Node, JDK, and sbt versions that the engine's `build.sbt` and `js/package.json` declare. Python 3.10+ and Git are sufficient to *assemble* the source tree, but not to compile Scala or run the JavaScript generator.

These steps are published for transparency and for the uses the license allows. The PolyForm Strict License in `LICENSE` does not allow changes, new works based on the software, or distribution; building it does not change that. See `LICENSING.md`.

The exact source pins are in `UPSTREAM.md`; the application's engine pin (development commit and dictionary content hash) is recorded under `checks.service_pin` in `provenance/release.json`.

## Engine source

From the package root:

```sh
cd engine/fact-graph-scala
sbt "factGraphJS/fullLinkJS"
```

The release ships the output of that link as `js/engine/factgraph.js` (the development repository's committed link, the bytes its JavaScript/JVM differential checked; its SHA-256 is in `SHA256SUMS`). A Scala.js link is not byte-stable: a fresh link at the same pin can order the exported methods differently, so a rebuilt file is equivalent but not byte-identical. `js/engine/factgraph.libraries.tsv` lists the modules of sbt's resolved compile classpath that the link can contain, with each module's license.

At this pin, `build.sbt` declares Scala `3.3.6`, version `3.1.0-SNAPSHOT`, and ES-module JavaScript output. The `SNAPSHOT` version string is not a release identifier; the source pin is.

The upstream source, build files, and notices are retained in `engine/fact-graph-scala/`. The files ytax changed or added there are listed under `checks.frozen_engine` in `provenance/release.json`.

## Dictionary generator

From the package root:

```sh
(cd js && npm ci)
bash js/scripts/generate-dictionary.sh \
  --dict "$PWD/dictionary/ty2025" \
  --out "$PWD/js/fact-dictionary/generated"
```

The generator loads the top-level TY2025 XML nonrecursively; the baseline under `upstream/` must not be loaded implicitly. The engine pin hashes the complete `dictionary/ty2025` tree.

The exporter preserves the exact package lock and generator sources. It does not run package install scripts. Fetched dependencies keep their own licenses. A public release of this package has passed `npm audit` on this lockfile with no high or critical advisories.

## Clean source tree

`provenance/release.json` and `SHA256SUMS` describe the clean source tree. Builds add ignored artifacts; run source-tree verification on a clean checkout, not on a directory populated by sbt/npm.
