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
// Original path: direct-file/df-client/df-client-app/src/flow/Path.ts

// LOCAL ADAPTATION (js/fact-dictionary/VENDORED.md): path prefix only -- our copy sits at
// js/src/flow/Path.ts (two levels below js/), whereas upstream's sits at src/flow/Path.ts
// (one level below src/, same depth as its own fact-dictionary/ sibling). No other line
// changed.
import { AbstractPath, Path as FDPath } from '../../fact-dictionary/Path.js';
import type { ConcretePath } from '../factgraphTypes.js';

export class Path {
  static isAbstract(path: FDPath) {
    return path.includes(`*`);
  }

  static isAbstractPathType(path: FDPath): path is AbstractPath {
    return this.isAbstract(path);
  }

  static concretePath(path: FDPath, collectionId: string | null) {
    return path.replace(`*`, `#${collectionId}`) as ConcretePath;
  }

  static fromConcretePath(concretePath: ConcretePath) {
    const regexPattern = /\/#([a-fA-F0-9-]+)\//g;
    return concretePath.replace(regexPattern, `/*/`) as FDPath;
  }
}
