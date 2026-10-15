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
// Original path: shared/src/main/scala/gov/irs/factgraph/compnodes/Divide.scala

package gov.irs.factgraph.compnodes

import gov.irs.factgraph.{ Expression, FactDictionary, Factual }
import gov.irs.factgraph.definitions.fact.CompNodeConfigTrait
import gov.irs.factgraph.operators.{ BinaryOperator, ReduceOperator }
import gov.irs.factgraph.types.{ *, given }
import gov.irs.factgraph.util.Seq.itemsHaveSameRuntimeClass
import scala.annotation.unused

object Divide extends CompNodeFactory:
  override val Key: String = "Divide"

  def apply(nodes: Seq[CompNode]): CompNode =
    if (itemsHaveSameRuntimeClass(nodes))
      reduceDivide(nodes)
    else
      nodes.reduceLeft(binaryDivide)

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    val dividend = CompNode.getConfigChildNode(e, "Dividend")
    val divisors = CompNode.getConfigChildNodes(e, "Divisors")

    this(dividend +: divisors)

  private def reduceDivide(nodes: Seq[CompNode]): CompNode =
    nodes.head match
      case node: IntNode =>
        nodes.reduceLeft(binaryDivide)
      case node: DollarNode =>
        DollarNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[DollarNode]].map(_.expr),
            summon[DivideReduceOperator[Dollar]],
          ),
        )
      case node: RationalNode =>
        RationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[RationalNode]].map(_.expr),
            summon[DivideReduceOperator[Rational]],
          ),
        )
      case node: ExactRationalNode =>
        ExactRationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[ExactRationalNode]].map(_.expr),
            summon[DivideReduceOperator[ExactRational]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot Divide a ${nodes.head.getClass.getName}",
        )

  private def binaryDivide(lhs: CompNode, rhs: CompNode): CompNode =
    (lhs, rhs).match
      case (lhs: IntNode, rhs: IntNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Rational, Int, Int]],
          ),
        )
      case (lhs: DollarNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Dollar, Dollar, Dollar]],
          ),
        )
      case (lhs: RationalNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Rational, Rational, Rational]],
          ),
        )
      case (lhs: ExactRationalNode, rhs: ExactRationalNode) =>
        ExactRationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[ExactRational, ExactRational, ExactRational]],
          ),
        )
      case (lhs: IntNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Dollar, Int, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: IntNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Dollar, Dollar, Int]],
          ),
        )
      case (lhs: IntNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Rational, Int, Rational]],
          ),
        )
      case (lhs: RationalNode, rhs: IntNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Rational, Rational, Int]],
          ),
        )
      case (lhs: RationalNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Dollar, Rational, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: RationalNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[DivideBinaryOperator[Dollar, Dollar, Rational]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot Divide a ${lhs.getClass.getName} and a ${rhs.getClass.getName}",
        )

final private class DivideReduceOperator[A: Fractional] extends ReduceOperator[A]:
  override protected def reduce(x: A, y: A): A = Fractional[A].div(x, y)

@unused
private object DivideReduceOperator:
  implicit val dollarOperator: DivideReduceOperator[Dollar] =
    DivideReduceOperator[Dollar]
  implicit val rationalOperator: DivideReduceOperator[Rational] =
    DivideReduceOperator[Rational]
  implicit val exactRationalOperator: DivideReduceOperator[ExactRational] =
    DivideReduceOperator[ExactRational]
  // implicit def fractionalOperator[A: Fractional]: DivideReduceOperator[A] =
  //   DivideReduceOperator[A]

private trait DivideBinaryOperator[A, L, R] extends BinaryOperator[A, L, R]

@unused
private object DivideBinaryOperator:
  implicit val intIntOperator: DivideBinaryOperator[Rational, Int, Int] =
    (lhs: Int, rhs: Int) => Rational(lhs, rhs)
  implicit val dollarDollarOperator: DivideBinaryOperator[Dollar, Dollar, Dollar] =
    (lhs: Dollar, rhs: Dollar) => lhs / rhs
  implicit val rationalRationalOperator: DivideBinaryOperator[Rational, Rational, Rational] =
    (lhs: Rational, rhs: Rational) => lhs / rhs
  implicit val exactRationalExactRationalOperator: DivideBinaryOperator[ExactRational, ExactRational, ExactRational] =
    (lhs: ExactRational, rhs: ExactRational) => lhs / rhs
  implicit val intDollarOperator: DivideBinaryOperator[Dollar, Int, Dollar] =
    (lhs: Int, rhs: Dollar) => Fractional[Dollar].div(lhs, rhs)
  implicit val dollarIntOperator: DivideBinaryOperator[Dollar, Dollar, Int] =
    (lhs: Dollar, rhs: Int) => Fractional[Dollar].div(lhs, rhs)
  implicit val intRationalOperator: DivideBinaryOperator[Rational, Int, Rational] =
    (lhs: Int, rhs: Rational) => Fractional[Rational].div(lhs, rhs)
  implicit val rationalIntOperator: DivideBinaryOperator[Rational, Rational, Int] =
    (lhs: Rational, rhs: Int) => Fractional[Rational].div(lhs, rhs)
  implicit val dollarRationalOperator: DivideBinaryOperator[Dollar, Dollar, Rational] =
    (lhs: Dollar, rhs: Rational) =>
      Fractional[Dollar].div(
        Numeric[Dollar].times(lhs, Dollar(BigDecimal(rhs.denominator))),
        Dollar(BigDecimal(rhs.numerator)),
      )
  implicit val rationalDollarOperator: DivideBinaryOperator[Dollar, Rational, Dollar] =
    (lhs: Rational, rhs: Dollar) =>
      Fractional[Dollar].div(
        Dollar(BigDecimal(lhs.numerator)),
        Numeric[Dollar].times(rhs, Dollar(BigDecimal(lhs.denominator))),
      )
