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
package gov.irs.factgraph.compnodes

import gov.irs.factgraph.{ Expression, FactDictionary, Factual }
import gov.irs.factgraph.definitions.fact.CompNodeConfigTrait
import gov.irs.factgraph.operators.BinaryOperator
import gov.irs.factgraph.types.*
import scala.annotation.unused

object GreaterThanOrEqual extends CompNodeFactory:
  override val Key: String = "GreaterThanOrEqual"

  def apply(lhs: CompNode, rhs: CompNode): BooleanNode =
    BooleanNode(
      (lhs, rhs).match
        case (lhs: IntNode, rhs: IntNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[GreaterThanOrEqualBinaryOperator[Int]],
          )
        case (lhs: DollarNode, rhs: DollarNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[GreaterThanOrEqualBinaryOperator[Dollar]],
          )
        case (lhs: RationalNode, rhs: RationalNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[GreaterThanOrEqualBinaryOperator[Rational]],
          )
        case (lhs: ExactRationalNode, rhs: ExactRationalNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[GreaterThanOrEqualBinaryOperator[ExactRational]],
          )
        case (lhs: DayNode, rhs: DayNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[GreaterThanOrEqualBinaryOperator[Day]],
          )
        case _ =>
          throw new UnsupportedOperationException(
            s"cannot compare a ${lhs.getClass.getName} and a ${rhs.getClass.getName}",
          ),
    )

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    val lhs = CompNode.getConfigChildNode(e, "Left")
    val rhs = CompNode.getConfigChildNode(e, "Right")
    this(lhs, rhs)

final private class GreaterThanOrEqualBinaryOperator[A: Ordering] extends BinaryOperator[Boolean, A, A]:
  override protected def operation(x: A, y: A): Boolean = Ordering[A].gteq(x, y)

@unused
private object GreaterThanOrEqualBinaryOperator:
  implicit val intOperator: GreaterThanOrEqualBinaryOperator[Int] =
    GreaterThanOrEqualBinaryOperator[Int]
  implicit val dollarOperator: GreaterThanOrEqualBinaryOperator[Dollar] =
    GreaterThanOrEqualBinaryOperator[Dollar]
  implicit val rationalOperator: GreaterThanOrEqualBinaryOperator[Rational] =
    GreaterThanOrEqualBinaryOperator[Rational]
  implicit val exactRationalOperator: GreaterThanOrEqualBinaryOperator[ExactRational] =
    GreaterThanOrEqualBinaryOperator[ExactRational]
  implicit val dayOperator: GreaterThanOrEqualBinaryOperator[Day] =
    GreaterThanOrEqualBinaryOperator[Day]

  // implicit def numericOperator[A: Numeric]
  //     : GreaterThanOrEqualBinaryOperator[A] =
  //   GreaterThanOrEqualBinaryOperator[A]
