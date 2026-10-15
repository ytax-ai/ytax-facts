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
// Original path: direct-file/df-client/df-client-app/src/constants/taxConstants.ts

/**
 * LOCAL ADAPTATION, not a verbatim vendor (see js/fact-dictionary/VENDORED.md, "## Local
 * adaptations"): upstream's `../constants/taxConstants.ts` is a large file
 * (filing-deadline `Date` arithmetic, EITC income-threshold tables for TY2023/TY2024) that
 * is entirely UI/product-flow scoped and irrelevant to this engine test harness. Our
 * vendored `setupFactGraph.ts` and `testData.ts` use exactly one export from it,
 * `CURRENT_TAX_YEAR`. Rather than vendor the whole file (and its stale, TY2024-hardcoded
 * value), this trims to that single constant and corrects the value to match THIS
 * project's actual target tax year (`dictionary/ty2025`). The full upstream file remains
 * available at the pinned SHA (see VENDORED.md) if a later task needs the other constants.
 */
export const CURRENT_TAX_YEAR = `2025`;
