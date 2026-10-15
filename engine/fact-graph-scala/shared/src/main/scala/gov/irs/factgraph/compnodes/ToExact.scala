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
import gov.irs.factgraph.operators.UnaryOperator
import gov.irs.factgraph.types.*

object ToExact extends CompNodeFactory:
  override val Key: String = "ToExact"
  private val operator = new UnaryOperator[ExactRational, Dollar]:
    override protected def operation(value: Dollar): ExactRational = ExactRational.fromDollar(value)

  def apply(amount: DollarNode): ExactRationalNode =
    ExactRationalNode(Expression.Unary(amount.expr, operator))

  override def fromDerivedConfig(e: CompNodeConfigTrait)(using Factual)(using FactDictionary): CompNode =
    CompNode.getConfigChildNode(e) match
      case node: DollarNode => this(node)
      case other => throw new UnsupportedOperationException(s"ToExact requires Dollar, got ${other.getClass.getName}")
