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
// Upstream repository: IRS-Public/fact-graph
// Upstream revision: 5599f75ba3047294c1b46e16eb3141dcde046643
// Original path: shared/src/main/scala/gov/irs/factgraph/limits/Match.scala

package gov.irs.factgraph.limits

import gov.irs.factgraph.{ FactDictionary, Factual, Path }
import gov.irs.factgraph.compnodes.{ BooleanNode, CompNode, Dependency, Not, Regex, StringNode }
import gov.irs.factgraph.definitions.fact.LimitConfigTrait

case class Match(limiter: BooleanNode, context: LimitContext) extends Limit

object Match extends LimitFactory {
  override val Key: String = "Match"
  def apply(e: LimitConfigTrait)(using Factual)(using FactDictionary): Limit =
    val pattern = CompNode.fromDerivedConfig(e.node)
    val lhs = Dependency(Path.Relative)
    if (!pattern.isInstanceOf[StringNode] || !lhs.isInstanceOf[StringNode])
      throw new UnsupportedOperationException(
        "String node required for match limit",
      )
    Match(
      Regex(lhs.asInstanceOf[StringNode], pattern.asInstanceOf[StringNode]),
      new LimitContext(Key, e.level, lhs, pattern),
    )

  override def fromConfig(e: LimitConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): Limit =
    this(e)
}
