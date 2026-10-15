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
import gov.irs.factgraph.operators.ReduceOperator
import gov.irs.factgraph.types.*
import gov.irs.factgraph.util.Seq.itemsHaveSameRuntimeClass
import scala.annotation.unused

object LesserOf extends CompNodeFactory:
  override val Key: String = "LesserOf"

  def apply(nodes: Seq[CompNode]): CompNode =
    if (!itemsHaveSameRuntimeClass(nodes))
      throw new UnsupportedOperationException(
        s"cannot compare nodes of different classes",
      )

    nodes.head match
      case node: IntNode =>
        IntNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[IntNode]].map(_.expr),
            summon[LesserOfOperator[Int]],
          ),
        )
      case node: DollarNode =>
        DollarNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[DollarNode]].map(_.expr),
            summon[LesserOfOperator[Dollar]],
          ),
        )
      case node: RationalNode =>
        RationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[RationalNode]].map(_.expr),
            summon[LesserOfOperator[Rational]],
          ),
        )
      case node: ExactRationalNode =>
        ExactRationalNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[ExactRationalNode]].map(_.expr),
            summon[LesserOfOperator[ExactRational]],
          ),
        )
      case node: DayNode =>
        DayNode(
          Expression.Reduce(
            nodes.asInstanceOf[List[DayNode]].map(_.expr),
            summon[LesserOfOperator[Day]],
          ),
        )
      case _ =>
        throw new UnsupportedOperationException(
          s"cannot compare a ${nodes.head.getClass.getName}",
        )

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using
      Factual,
  )(using
      FactDictionary,
  ): CompNode =
    this(CompNode.getConfigChildNodes(e))

final private class LesserOfOperator[A: Ordering] extends ReduceOperator[A]:
  override protected def reduce(x: A, y: A): A =
    if (Ordering[A].lteq(x, y)) x else y

@unused
private object LesserOfOperator:
  implicit val intOperator: LesserOfOperator[Int] =
    LesserOfOperator[Int]
  implicit val dollarOperator: LesserOfOperator[Dollar] =
    LesserOfOperator[Dollar]
  implicit val rationalOperator: LesserOfOperator[Rational] =
    LesserOfOperator[Rational]
  implicit val exactRationalOperator: LesserOfOperator[ExactRational] =
    LesserOfOperator[ExactRational]
  implicit val dayOperator: LesserOfOperator[Day] =
    LesserOfOperator[Day]

  // implicit def numericOperator[A: Numeric]: LesserOfOperator[A] =
  //   LesserOfOperator[A]
