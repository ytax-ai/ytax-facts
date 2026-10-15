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
// Original path: direct-file/df-client/df-client-app/src/fact-dictionary/generate-src/readRawFacts.ts

import fs from 'fs';
import { XMLParser, XMLValidator, X2jOptions } from 'fast-xml-parser';
import { RawFact } from '../FactTypes.js';

export default function readRawFacts(): RawFact[] {
  // LOCAL ADAPTATION (see js/fact-dictionary/VENDORED.md): allow the batch dictionary
  // builder to validate an isolated target. The default remains the symlink used by the
  // ordinary ty2025 generator.
  //
  // LOCAL ADAPTATION (unit `js-default`, 2026-08-22): the value may be a ':'-separated LIST
  // of directories, exactly like the JVM runner's dict spec
  // (`ScenarioRunner.parseFactCfgs`, which does `dirSpec.split(":")` and merges the modules
  // of every dir into ONE dictionary). This is what makes the L2 strategy layer loadable on
  // JS at all: `dictionary/ty2025:dictionary/ty2025-strategies`. Reading stays NON-RECURSIVE
  // per directory — the same property that keeps `dictionary/ty2025` alone free of
  // `/strategies/` facts on both engines, i.e. one-way layering.
  //
  // Two deliberate differences from the JVM, neither observable in a snapshot:
  //   * the JVM sorts every file across every dir by BASENAME before parsing; this keeps the
  //     per-directory `readdirSync` order and concatenates the dirs in spec order. Fact ORDER
  //     affects only the order of the generated arrays, and every consumer that emits rows
  //     (`js/src/snapshot.ts`'s `snapshotToTsv`) sorts by fact PATH — so the two agree row for
  //     row. Keeping readdirSync order also makes the single-dir case byte-identical to what
  //     this generator produced before this change.
  //   * a basename appearing in TWO dirs is rejected below rather than silently shadowed:
  //     `fact.srcFile` is a bare basename, so two same-named modules would be indistinguishable
  //     downstream, and the JVM would parse BOTH (yielding a duplicate-path dictionary error
  //     far from the cause). Fail here, naming both directories.
  const FACT_DICTIONARY_SPEC =
    process.env.FACT_DICTIONARY_SOURCE_DIR || `./fact-dictionary/generate-src/xml-src/`;
  const FACT_DICTIONARY_FOLDERS = FACT_DICTIONARY_SPEC.split(`:`)
    .map((d) => d.trim())
    .filter((d) => d.length > 0);
  if (FACT_DICTIONARY_FOLDERS.length === 0) {
    throw new Error(`FACT_DICTIONARY_SOURCE_DIR named no directory: ${FACT_DICTIONARY_SPEC}`);
  }

  const XML_PARSER_OPTIONS: X2jOptions = {
    ignoreAttributes: false,
    attributeNamePrefix: `@`,
    ignoreDeclaration: true,
    trimValues: true,
    parseAttributeValue: false,
    // LOCAL ADAPTATION (see js/fact-dictionary/VENDORED.md, "## Local adaptations"): upstream
    // leaves parseTagValue at fast-xml-parser's default (numeric coercion ON). That silently
    // turns tag text into a JS number -- `<String>0.</String>` becomes the number `0` (the
    // trailing dot is dropped, corrupting a `[^0.]`-equivalent StripChars Allow-list into
    // `[^0]`), and every `<Dollar>` literal (money!) becomes a bare JS Number instead of a
    // string. Money in this project is BigDecimal end-to-end; it must never round-trip
    // through a JS float, even transiently in generator output. Forcing this off is the
    // minimal fix -- tag text now stays a verbatim string, exactly like attribute values
    // already do two lines up.
    parseTagValue: false,
  };

  // We assume all xml files in the tax folder are Fact Dictionary Fragments.
  const dictionaryFiles: { dir: string; file: string }[] = [];
  const seenBasenames = new Map<string, string>();
  for (const dir of FACT_DICTIONARY_FOLDERS) {
    for (const file of fs.readdirSync(dir).filter((f) => f.endsWith(`.xml`))) {
      const previousDir = seenBasenames.get(file);
      if (previousDir !== undefined) {
        throw new Error(
          `Duplicate fact-dictionary module basename "${file}": present in both "${previousDir}" and ` +
            `"${dir}". srcFile is a bare basename, so the two would be indistinguishable downstream.`
        );
      }
      seenBasenames.set(file, dir);
      dictionaryFiles.push({ dir, file });
    }
  }

  const allRawFacts: RawFact[] = [];

  for (const { dir, file: dictionaryFile } of dictionaryFiles) {
    // eslint-disable-next-line no-console
    console.log(`Reading file ${dictionaryFile}`);
    // nosemgrep: eslint.detect-non-literal-fs-filename
    const rawXmlString = fs.readFileSync(`${dir}/${dictionaryFile}`, `utf-8`);

    const xmlValidationResult = XMLValidator.validate(rawXmlString, {
      allowBooleanAttributes: true,
    });

    // must use strict equality here, since this will return an object if untrue
    if (xmlValidationResult !== true) {
      // not client facing, so we'll allow console here
      // eslint-disable-next-line no-console
      console.error(`XML validation error`, xmlValidationResult);
      throw new Error(`XML validation error`);
    }

    const parser = new XMLParser(XML_PARSER_OPTIONS);
    const parsedDictionary = parser.parse(rawXmlString);

    if (!parsedDictionary.FactDictionaryModule) {
      throw new Error(`XML did not start with element "FactDictionaryModule`);
    }

    // A module may carry no facts yet (a home-module stub declared for a printed form before
    // the sweep promotes anything into it): an empty <Facts/> is a module, not an error.
    const rawFacts: RawFact[] = [].concat(parsedDictionary.FactDictionaryModule.Facts?.Fact ?? []);
    rawFacts.forEach((fact: RawFact) => {
      fact.srcFile = dictionaryFile;
    });
    allRawFacts.push(...rawFacts);
  }
  return allRawFacts;
}
