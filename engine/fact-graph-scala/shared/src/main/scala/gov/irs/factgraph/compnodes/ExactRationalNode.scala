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
import gov.irs.factgraph.definitions.fact.{ CommonOptionConfigTraits, CompNodeConfigTrait }
import gov.irs.factgraph.types.ExactRational

/** Derived-only: exact fractions are not taxpayer writable/persisted money. */
final case class ExactRationalNode(expr: Expression[ExactRational]) extends CompNode:
  type Value = ExactRational
  override def ValueClass = classOf[ExactRational]
  override private[compnodes] def fromExpression(expr: Expression[ExactRational]): CompNode =
    ExactRationalNode(expr)

object ExactRationalNode extends CompNodeFactory:
  override val Key: String = "ExactRational"
  def apply(value: ExactRational): ExactRationalNode =
    new ExactRationalNode(Expression.Constant(Some(value)))
  override def fromDerivedConfig(e: CompNodeConfigTrait)(using Factual)(using FactDictionary): CompNode =
    this(ExactRational(e.getOptionValue(CommonOptionConfigTraits.VALUE).get))
