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
// Original path: shared/src/main/scala/gov/irs/factgraph/compnodes/Multiply.scala

package gov.irs.factgraph.compnodes

import gov.irs.factgraph.{ Expression, FactDictionary, Factual }
import gov.irs.factgraph.definitions.fact.CompNodeConfigTrait
import gov.irs.factgraph.operators.{ BinaryOperator, ReduceOperator }
import gov.irs.factgraph.types.{ *, given }
import gov.irs.factgraph.util.Seq.itemsHaveSameRuntimeClass
import scala.annotation.unused

object Multiply extends CompNodeFactory:
  override val Key: String = "Multiply"

  def apply(nodes: Seq[CompNode]): CompNode =
    if (itemsHaveSameRuntimeClass(nodes))
      reduceMultiply(nodes)
    else
      nodes.reduceLeft(binaryMultiply)

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    val factors = CompNode.getConfigChildNodes(e)
    this(factors)

  private def reduceMultiply(nodes: Seq[CompNode]): CompNode =
    nodes.head match
      case node: IntNode =>
        IntNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[IntNode]].map(_.expr),
            summon[MultiplyReduceOperator[Int]],
          ),
        )
      case node: DollarNode =>
        DollarNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[DollarNode]].map(_.expr),
            summon[MultiplyReduceOperator[Dollar]],
          ),
        )
      case node: RationalNode =>
        RationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[RationalNode]].map(_.expr),
            summon[MultiplyReduceOperator[Rational]],
          ),
        )
      case node: ExactRationalNode =>
        ExactRationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[ExactRationalNode]].map(_.expr),
            summon[MultiplyReduceOperator[ExactRational]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot Multiply a ${nodes.head.getClass.getName}",
        )

  private def binaryMultiply(lhs: CompNode, rhs: CompNode): CompNode =
    (lhs, rhs).match
      case (lhs: IntNode, rhs: IntNode) =>
        IntNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Int, Int, Int]],
          ),
        )
      case (lhs: DollarNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Dollar, Dollar, Dollar]],
          ),
        )
      case (lhs: RationalNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Rational, Rational, Rational]],
          ),
        )
      case (lhs: ExactRationalNode, rhs: ExactRationalNode) =>
        ExactRationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[ExactRational, ExactRational, ExactRational]],
          ),
        )
      case (lhs: IntNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Dollar, Int, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: IntNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Dollar, Dollar, Int]],
          ),
        )
      case (lhs: IntNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Rational, Int, Rational]],
          ),
        )
      case (lhs: RationalNode, rhs: IntNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Rational, Rational, Int]],
          ),
        )
      case (lhs: RationalNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Dollar, Rational, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: RationalNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[MultiplyBinaryOperator[Dollar, Dollar, Rational]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot Multiply a ${lhs.getClass.getName} and a ${rhs.getClass.getName}",
        )

final private class MultiplyReduceOperator[A: Numeric] extends ReduceOperator[A]:
  override protected def reduce(x: A, y: A): A = Numeric[A].times(x, y)

@unused
private object MultiplyReduceOperator:
  implicit val intOperator: MultiplyReduceOperator[Int] =
    MultiplyReduceOperator[Int]
  implicit val dollarOperator: MultiplyReduceOperator[Dollar] =
    MultiplyReduceOperator[Dollar]
  implicit val rationalOperator: MultiplyReduceOperator[Rational] =
    MultiplyReduceOperator[Rational]
  implicit val exactRationalOperator: MultiplyReduceOperator[ExactRational] =
    MultiplyReduceOperator[ExactRational]
  // implicit def numericOperator[A: Numeric]: MultiplyReduceOperator[A] =
  //   MultiplyReduceOperator[A]

private trait MultiplyBinaryOperator[A, L, R] extends BinaryOperator[A, L, R]

@unused
private object MultiplyBinaryOperator:
  implicit val intIntOperator: MultiplyBinaryOperator[Int, Int, Int] =
    (lhs: Int, rhs: Int) => lhs * rhs
  implicit val dollarDollarOperator: MultiplyBinaryOperator[Dollar, Dollar, Dollar] =
    (lhs: Dollar, rhs: Dollar) => lhs * rhs
  implicit val rationalRationalOperator: MultiplyBinaryOperator[Rational, Rational, Rational] =
    (lhs: Rational, rhs: Rational) => lhs * rhs
  implicit val exactRationalExactRationalOperator: MultiplyBinaryOperator[ExactRational, ExactRational, ExactRational] =
    (lhs: ExactRational, rhs: ExactRational) => lhs * rhs
  implicit val dollarIntOperator: MultiplyBinaryOperator[Dollar, Dollar, Int] =
    (lhs: Dollar, rhs: Int) => Numeric[Dollar].times(lhs, rhs)
  implicit val intDollarOperator: MultiplyBinaryOperator[Dollar, Int, Dollar] =
    (lhs: Int, rhs: Dollar) => Numeric[Dollar].times(lhs, rhs)
  implicit val rationalIntOperator: MultiplyBinaryOperator[Rational, Rational, Int] =
    (lhs: Rational, rhs: Int) => Numeric[Rational].times(lhs, rhs)
  implicit val intRationalOperator: MultiplyBinaryOperator[Rational, Int, Rational] =
    (lhs: Int, rhs: Rational) => Numeric[Rational].times(lhs, rhs)
  implicit val dollarRationalOperator: MultiplyBinaryOperator[Dollar, Dollar, Rational] =
    (lhs: Dollar, rhs: Rational) =>
      Fractional[Dollar].div(
        Numeric[Dollar].times(lhs, Dollar(BigDecimal(rhs.numerator))),
        Dollar(BigDecimal(rhs.denominator)),
      )
  implicit val rationalDollarOperator: MultiplyBinaryOperator[Dollar, Rational, Dollar] =
    (lhs: Rational, rhs: Dollar) =>
      Fractional[Dollar].div(
        Numeric[Dollar].times(rhs, Dollar(BigDecimal(lhs.numerator))),
        Dollar(BigDecimal(lhs.denominator)),
      )
