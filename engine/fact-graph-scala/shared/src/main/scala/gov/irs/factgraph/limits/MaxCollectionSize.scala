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
// Original path: shared/src/main/scala/gov/irs/factgraph/limits/MaxCollectionSize.scala

package gov.irs.factgraph.limits

import gov.irs.factgraph.{ Expression, FactDictionary, Factual, Path }
import gov.irs.factgraph.compnodes.{
  BooleanNode,
  CollectionNode,
  CollectionSize,
  CompNode,
  Dependency,
  IntNode,
  LessThanOrEqual,
}
import gov.irs.factgraph.definitions.fact.{ CompNodeConfigTrait, LimitConfigTrait }
import gov.irs.factgraph.limits.LimitFactory
import gov.irs.factgraph.types.Collection

case class MaxCollectionSize(limiter: BooleanNode, context: LimitContext) extends Limit

object MaxCollectionSize extends LimitFactory {
  override val Key: String = "MaxCollectionSize"
  def apply(e: LimitConfigTrait)(using Factual)(using FactDictionary): Limit =
    val rhs = CompNode.fromDerivedConfig(e.node)
    // 3/23/2022
    // Because of the scalajs part we shouldn't leave this to a ClassCaseException
    // Those don't work in the JS.
    val fact = summon[Factual]
    if (!fact.value.isInstanceOf[CollectionNode])
      throw new UnsupportedOperationException("collection node required")
    val lhs = CollectionSize(
      CollectionNode(Expression.Dependency(Path.Relative), None),
    )
    Max(LessThanOrEqual(lhs, rhs), new LimitContext(Key, e.level, lhs, rhs))

  override def fromConfig(e: LimitConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): Limit =
    this(e)
}
