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
// Original path: shared/src/main/scala/gov/irs/factgraph/compnodes/TruncateCents.scala

package gov.irs.factgraph.compnodes

import gov.irs.factgraph.{ Expression, FactDictionary, Factual }
import gov.irs.factgraph.definitions.fact.{ CommonOptionConfigTraits, CompNodeConfigTrait }
import gov.irs.factgraph.operators.UnaryOperator
import gov.irs.factgraph.types.Rational

object TruncateCents extends CompNodeFactory:
  override val Key: String = "TruncateCents"

  private val operator = TruncateOperator()

  def apply(node: CompNode): RationalNode =
    node match
      case node: RationalNode =>
        RationalNode(
          Expression.Unary(
            node.expr,
            operator,
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot execute AsDecimalString on a ${node.getClass.getName}",
        )

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    CompNode.getConfigChildNode(e) match
      case x: RationalNode => this(x)
      case _               =>
        throw new UnsupportedOperationException(
          s"invalid child type: ${e.typeName}",
        )

final private class TruncateOperator extends UnaryOperator[Rational, Rational]:
  override protected def operation(x: Rational): Rational =
    val value = (BigDecimal(x.numerator) / BigDecimal(x.denominator))
      .setScale(2, scala.math.BigDecimal.RoundingMode.DOWN)
    val numerator = value.bigDecimal.unscaledValue().longValue()
    val denominator = BigDecimal(10).pow(value.scale).longValue
    Rational(numerator, denominator).simplify
