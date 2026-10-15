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

object LessThan extends CompNodeFactory:
  override val Key: String = "LessThan"

  def apply(lhs: CompNode, rhs: CompNode): BooleanNode =
    BooleanNode(
      (lhs, rhs).match
        case (lhs: IntNode, rhs: IntNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[LessThanBinaryOperator[Int]],
          )
        case (lhs: DollarNode, rhs: DollarNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[LessThanBinaryOperator[Dollar]],
          )
        case (lhs: RationalNode, rhs: RationalNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[LessThanBinaryOperator[Rational]],
          )
        case (lhs: ExactRationalNode, rhs: ExactRationalNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[LessThanBinaryOperator[ExactRational]],
          )
        case (lhs: DayNode, rhs: DayNode) =>
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[LessThanBinaryOperator[Day]],
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

final private class LessThanBinaryOperator[A: Ordering] extends BinaryOperator[Boolean, A, A]:
  override protected def operation(x: A, y: A): Boolean = Ordering[A].lt(x, y)

@unused
private object LessThanBinaryOperator:
  implicit val intOperator: LessThanBinaryOperator[Int] =
    LessThanBinaryOperator[Int]
  implicit val dollarOperator: LessThanBinaryOperator[Dollar] =
    LessThanBinaryOperator[Dollar]
  implicit val rationalOperator: LessThanBinaryOperator[Rational] =
    LessThanBinaryOperator[Rational]
  implicit val exactRationalOperator: LessThanBinaryOperator[ExactRational] =
    LessThanBinaryOperator[ExactRational]
  implicit val dayOperator: LessThanBinaryOperator[Day] =
    LessThanBinaryOperator[Day]

  // implicit def numericOperator[A: Numeric]: LessThanBinaryOperator[A] =
  //   LessThanBinaryOperator[A]
