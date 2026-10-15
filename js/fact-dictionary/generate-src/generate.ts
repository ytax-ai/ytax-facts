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
// Original path: direct-file/df-client/df-client-app/src/fact-dictionary/generate-src/generate.ts

import fs from 'fs';
import path from 'node:path';
import * as prettier from 'prettier';
import stringifyObject from 'stringify-object';
import processFactsToDigestWrapper from './processFactsToDigestWrapper.js';
import readRawFacts from './readRawFacts.js';
import {
  individualFilerAliases,
  w2Aliases,
  w2Slices,
  form1099MiscAliases,
  form1099RAliases,
  dependentCollectionAliases,
  individualDependentAliases,
  bankAccountFields,
  addressFields,
  filerFields,
  aliasPaths,
  filerCollectionAliases,
} from '../aliases.js';
import { addressSubfields, filerSubfields, tinSubfields } from './subfields.js';
const generatedWarning = `
/**
 * DO NOT MODIFY DIRECTLY. GENERATED FILE.
 * MODIFY \`generate-src/generate.ts\` INSTEAD
 */
`;
// Prettier over the generated TypeScript (facts.ts ~32 MB, wrappedFacts.ts ~43 MB) was most of a
// generation's wall time and memory (measured 2026-09-27: ~3.8 GB RSS, minutes per run, several runs
// at once across worktrees). The output is gitignored and machine-read only (esbuild compiles it to
// the .js every consumer loads), so formatting is opt-in: FACT_DICTIONARY_PRETTY=1 restores it.
const formatGenerated = (source: string): string =>
  process.env.FACT_DICTIONARY_PRETTY === `1` ? prettier.format(source, { parser: `typescript` }) : source;
const generatedDir = process.env.FACT_DICTIONARY_OUTPUT_DIR || `./fact-dictionary/generated`;
const generatedFile = (name: string) => path.join(generatedDir, name);

const rawFacts = readRawFacts();

const rawFactInterfaces = `
import { RawFact } from "../FactTypes.js";
`;
// LOCAL ADAPTATION (see js/fact-dictionary/VENDORED.md): output paths below drop the
// upstream `src/` prefix (our js/ package has no src/ nesting for fact-dictionary/).
const factsFileName = generatedFile(`facts.ts`);
const factsString = `${generatedWarning} ${rawFactInterfaces} 
// ts-ignore as the typescript compiler cannot check a literal type with over 1000 facts
// because we cast the export again, the export is type safe.
// the only unsafe thing would be if the generator built something that did not match the WrappedFact interface
// @ts-ignore
const tsIgnoredFacts: RawFact[] = ${stringifyObject(rawFacts)} 
export const facts = tsIgnoredFacts as RawFact[] 
`;
const prettyFactsString = formatGenerated(factsString);

fs.writeFileSync(factsFileName, prettyFactsString);

const paths = rawFacts.map((f) => f[`@path`]);
const writablePaths = rawFacts.filter((f) => f.Writable !== undefined).map((f) => f[`@path`]);

const getExtendedPaths = (paths: string[]) => {
  return Array.from(
    new Set([
      ...paths,
      ...aliasPaths,

      // Hack until we have the types broken out a little better
      // This got out of hand faster than I expected it to
      // Aliases
      ...paths
        .filter((p: string) => p.includes(`filers`))
        .flatMap((p: string) => individualFilerAliases.map((filerAlias) => `${filerAlias}${p.split(`/`).slice(-1)}`)),

      ...paths
        .filter((p: string) => p.includes(`filers`))
        .flatMap((p: string) => filerCollectionAliases.map((filerAlias) => `${p.replace(`/filers/`, filerAlias)}`)),

      ...paths
        .filter((p: string) => p.includes(`familyAndHousehold`))
        .flatMap((p: string) => individualDependentAliases.map((alias) => `${alias}${p.split(`/`).slice(-1)}`)),
      ...paths
        .filter((p: string) => p.includes(`familyAndHousehold`))
        .flatMap((p: string) => dependentCollectionAliases.map((alias) => `${alias}*/${p.split(`/`).slice(-1)}`)),

      ...paths
        .filter((p: string) => p.includes(`form1099Miscs`))
        .flatMap((p: string) =>
          form1099MiscAliases.map((form1099MiscAlias) => `${p.replace(`/form1099Miscs/`, form1099MiscAlias)}`)
        ),

      ...paths
        .filter((p: string) => p.includes(`form1099Rs`))
        .flatMap((p: string) =>
          form1099RAliases.map((form1099RAlias) => `${p.replace(`/form1099Rs/`, form1099RAlias)}`)
        ),

      ...paths
        .filter((p: string) => p.includes(`formW2s`))
        .flatMap((p: string) => w2Aliases.map((w2Alias) => `${w2Alias}*/${p.split(`/`).slice(-1)}`)),

      ...paths
        .filter((p: string) => p.includes(`formW2s`))
        .flatMap((p: string) => w2Slices.map((w2Slice) => `${w2Slice}${p.split(`/`).slice(-1)}`)),

      // Date subpaths
      ...paths.filter((p: string) => p.includes(`dateOfBirth`)).flatMap((p: string) => [`${p}/year`]),
      ...paths.filter((p: string) => p.includes(`dateOfBirth`)).flatMap((p: string) => [`${p}/month`]),
      ...paths.filter((p: string) => p.includes(`dateOfBirth`)).flatMap((p: string) => [`${p}/day`]),

      // TIN subpaths
      ...paths
        .filter((p: string) => p.split(`/`).slice(-1)[0] === `tin`)
        .flatMap((p: string) => {
          return tinSubfields.map((subfield) => `${p}/${subfield}`);
        }),

      // Filer Tin Subpaths
      ...paths
        .filter((p: string) => individualFilerAliases.includes(p.split(`/`).slice(-1)[0]))
        .flatMap((p: string) => tinSubfields.map((subfield) => `${p}/tin/${subfield}`)),

      // Address subpaths
      ...paths
        .filter((p: string) => p.split(`/`).slice(-1)[0] === `address`)
        .flatMap(() => addressFields.flatMap((field) => addressSubfields.map((subfield) => `${field}/${subfield}`))),

      // Bank account subpaths
      ...bankAccountFields.flatMap((p) => [`${p}/accountType`, `${p}/accountNumber`, `${p}/routingNumber`]),

      // Filer subpaths
      ...paths
        .filter((p: string) => p.split(`/`).slice(-1)[0] === `filer`)
        .flatMap(() => filerFields.flatMap((field) => filerSubfields.map((subfield) => `${field}/${subfield}`))),
    ])
  );
};

const extendedPaths = getExtendedPaths(paths);
const extendedWritablePaths = getExtendedPaths(writablePaths);
const pathsFileName = generatedFile(`paths.ts`);
const pathsString = `${generatedWarning} export const paths = ${stringifyObject(
  extendedPaths
)} as const \n export const writablePaths = ${stringifyObject(extendedWritablePaths)} as const`;
const prettyPathsString = formatGenerated(pathsString);

fs.writeFileSync(pathsFileName, prettyPathsString);

const interfaces = `
import { WrappedFact } from "@irs/js-factgraph-scala";
// @ts-ignore: Union type is too complex for CI to represent
`;

const wrappedFacts = processFactsToDigestWrapper(rawFacts);
const wrappedFactsFileName = generatedFile(`wrappedFacts.ts`);
// eslint-disable-next-line max-len
const wrappedFactsString = `${generatedWarning}  ${interfaces} export const wrappedFacts: WrappedFact[] = ${stringifyObject(
  wrappedFacts
)} as any
// cast to any as the typescript compiler cannot check a literal type with over 1000 facts
// because we cast again at the top of the file, the export is type safe.
// the only unsafe thing would be if the generator built something that did not match the WrappedFact interface
`;
const prettyWrappedFactsString = formatGenerated(wrappedFactsString);

fs.writeFileSync(wrappedFactsFileName, prettyWrappedFactsString);

const submissionBlockingFacts = rawFacts.filter((f) => f.BlockSubmissionOnTrue !== undefined).map((f) => f[`@path`]);

const submissionBlockingFactsFilename = generatedFile(`submissionBlockingFacts.ts`);
// eslint-disable-next-line max-len
const submissionBlockingFactsString = `${generatedWarning} import { AbsolutePath } from "../Path.js"; export const submissionBlockingFacts: AbsolutePath[] = ${stringifyObject(
  submissionBlockingFacts
)}`;
const prettySubmissionBlockingFactsString = formatGenerated(submissionBlockingFactsString);

fs.writeFileSync(submissionBlockingFactsFilename, prettySubmissionBlockingFactsString);

//ExportToState
const exportToStateFacts = rawFacts
  .filter((f) => f.Export !== undefined && f.Export[`@stateSystems`] === `true`)
  .map((f) => f[`@path`]);
const exportToStateFactsFilename = generatedFile(`exportToStateFacts.ts`);
// eslint-disable-next-line max-len
const exportToStateFactsString = `${generatedWarning} export const exportToStateFacts = ${stringifyObject(
  exportToStateFacts
)} as const`;
const prettyExportToStateFactsString = formatGenerated(exportToStateFactsString);

fs.writeFileSync(exportToStateFactsFilename, prettyExportToStateFactsString);
