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
import gov.irs.factgraph.operators.{ BinaryOperator, ReduceOperator }
import gov.irs.factgraph.types.{ *, given }
import gov.irs.factgraph.util.Seq.itemsHaveSameRuntimeClass
import scala.annotation.unused

object Subtract extends CompNodeFactory:
  override val Key: String = "Subtract"

  def apply(nodes: Seq[CompNode]): CompNode =
    if (itemsHaveSameRuntimeClass(nodes))
      reduceSubtract(nodes)
    else
      nodes.reduceLeft(binarySubtract)

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    val minuend = CompNode.getConfigChildNode(e, "Minuend")
    val subtrahends = CompNode.getConfigChildNodes(e, "Subtrahends")
    this(minuend +: subtrahends)

  private def reduceSubtract(nodes: Seq[CompNode]): CompNode =
    nodes.head match
      case node: IntNode =>
        IntNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[IntNode]].map(_.expr),
            summon[SubtractReduceOperator[Int]],
          ),
        )
      case node: DollarNode =>
        DollarNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[DollarNode]].map(_.expr),
            summon[SubtractReduceOperator[Dollar]],
          ),
        )
      case node: RationalNode =>
        RationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[RationalNode]].map(_.expr),
            summon[SubtractReduceOperator[Rational]],
          ),
        )
      case node: ExactRationalNode =>
        ExactRationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[ExactRationalNode]].map(_.expr),
            summon[SubtractReduceOperator[ExactRational]],
          ),
        )
      case node: DayNode => nodes.reduceLeft(binarySubtract)
      case _             =>
        throw new UnsupportedOperationException(
          s"cannot Subtract a ${nodes.head.getClass.getName}",
        )

  private def binarySubtract(lhs: CompNode, rhs: CompNode): CompNode =
    (lhs, rhs).match
      case (lhs: IntNode, rhs: IntNode) =>
        IntNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Int, Int, Int]],
          ),
        )
      case (lhs: DollarNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Dollar, Dollar, Dollar]],
          ),
        )
      case (lhs: RationalNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Rational, Rational, Rational]],
          ),
        )
      case (lhs: ExactRationalNode, rhs: ExactRationalNode) =>
        ExactRationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[ExactRational, ExactRational, ExactRational]],
          ),
        )
      case (lhs: IntNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Dollar, Int, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: IntNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Dollar, Dollar, Int]],
          ),
        )
      case (lhs: IntNode, rhs: RationalNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Rational, Int, Rational]],
          ),
        )
      case (lhs: RationalNode, rhs: IntNode) =>
        RationalNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Rational, Rational, Int]],
          ),
        )
      case (lhs: RationalNode, rhs: DollarNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Dollar, Rational, Dollar]],
          ),
        )
      case (lhs: DollarNode, rhs: RationalNode) =>
        DollarNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Dollar, Dollar, Rational]],
          ),
        )
      case (lhs: DayNode, rhs: DaysNode) =>
        DayNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Day, Day, Days]],
          ),
        )
      case (lhs: DayNode, rhs: DayNode) =>
        IntNode(
          Expression.Binary(
            lhs.expr,
            rhs.expr,
            summon[SubtractBinaryOperator[Int, Day, Day]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot Subtract a ${lhs.getClass.getName} and a ${rhs.getClass.getName}",
        )

final private class SubtractReduceOperator[A: Numeric] extends ReduceOperator[A]:
  override protected def reduce(x: A, y: A): A = Numeric[A].minus(x, y)

@unused
private object SubtractReduceOperator:
  implicit val intOperator: SubtractReduceOperator[Int] =
    SubtractReduceOperator[Int]
  implicit val dollarOperator: SubtractReduceOperator[Dollar] =
    SubtractReduceOperator[Dollar]
  implicit val rationalOperator: SubtractReduceOperator[Rational] =
    SubtractReduceOperator[Rational]
  implicit val exactRationalOperator: SubtractReduceOperator[ExactRational] =
    SubtractReduceOperator[ExactRational]
  // implicit def numericOperator[A: Numeric]: SubtractReduceOperator[A] =
  //   SubtractReduceOperator[A]

private trait SubtractBinaryOperator[A, L, R] extends BinaryOperator[A, L, R]

@unused
private object SubtractBinaryOperator:
  implicit val intIntOperator: SubtractBinaryOperator[Int, Int, Int] =
    (lhs: Int, rhs: Int) => lhs - rhs
  implicit val dollarDollarOperator: SubtractBinaryOperator[Dollar, Dollar, Dollar] =
    (lhs: Dollar, rhs: Dollar) => lhs - rhs
  implicit val dayDaysOperator: SubtractBinaryOperator[Day, Day, Days] =
    (lhs: Day, rhs: Days) => lhs - rhs
  implicit val dayDayOperator: SubtractBinaryOperator[Int, Day, Day] =
    (lhs: Day, rhs: Day) => lhs - rhs
  implicit val rationalRationalOperator: SubtractBinaryOperator[Rational, Rational, Rational] =
    (lhs: Rational, rhs: Rational) => lhs - rhs
  implicit val exactRationalExactRationalOperator: SubtractBinaryOperator[ExactRational, ExactRational, ExactRational] =
    (lhs: ExactRational, rhs: ExactRational) => lhs - rhs
  implicit val dollarIntOperator: SubtractBinaryOperator[Dollar, Dollar, Int] =
    (lhs: Dollar, rhs: Int) => Numeric[Dollar].minus(lhs, rhs)
  implicit val intDollarOperator: SubtractBinaryOperator[Dollar, Int, Dollar] =
    (lhs: Int, rhs: Dollar) => Numeric[Dollar].minus(lhs, rhs)
  implicit val rationalIntOperator: SubtractBinaryOperator[Rational, Rational, Int] =
    (lhs: Rational, rhs: Int) => Numeric[Rational].minus(lhs, rhs)
  implicit val intRationalOperator: SubtractBinaryOperator[Rational, Int, Rational] =
    (lhs: Int, rhs: Rational) => Numeric[Rational].minus(lhs, rhs)
  implicit val dollarRationalOperator: SubtractBinaryOperator[Dollar, Dollar, Rational] =
    (lhs: Dollar, rhs: Rational) => Numeric[Dollar].minus(lhs, rhs)
  implicit val rationalDollarOperator: SubtractBinaryOperator[Dollar, Rational, Dollar] =
    (lhs: Rational, rhs: Dollar) => Numeric[Dollar].minus(lhs, rhs)
