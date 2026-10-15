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

import gov.irs.factgraph.definitions.fact.*
import gov.irs.factgraph.monads.Result
import gov.irs.factgraph.*
import gov.irs.factgraph.types.*
import java.util.UUID
import org.scalatest.funsuite.AnyFunSuite

/** Independent arithmetic contracts, not tax-law golden values. */
class ExactArithmeticSpec extends AnyFunSuite:
  private def literal(kind: String, value: String) =
    CompNodeConfigElement(kind, Seq.empty, CommonOptionConfigTraits.value(value))
  private def op(kind: String, children: CompNodeConfigElement*) =
    new CompNodeConfigElement(kind, children.toList)
  private def exact(value: String) = literal("ExactRational", value)
  private def money(value: String) = op("ToExact", literal("Dollar", value))
  private def divide(a: CompNodeConfigElement, b: CompNodeConfigElement) =
    op("Divide", op("Dividend", a), op("Divisors", b))
  private def value(config: CompNodeConfigElement): String =
    CompNode.fromDerivedConfig(config).get(0).get.toString

  test("Dollar to exact conversion preserves cents, signs and arbitrarily large amounts") {
    for ((input, expected) <- Seq("12.34" -> "617/50", "-0.01" -> "-1/100", "0" -> "0/1",
      "1000000000000000000000000.01" -> "100000000000000000000000001/100"))
      assert(value(money(input)) == expected)
  }

  test("exact constants normalize signs and equivalent fractions") {
    for ((input, expected) <- Seq("2/4" -> "1/2", "1/-2" -> "-1/2", "-1/-2" -> "1/2", "0/-2" -> "0/1"))
      assert(value(exact(input)) == expected)
    assert(value(op("Equal", op("Left", exact("1/2")), op("Right", exact("2/4")))) == "true")
  }

  test("round once directly from the exact fraction, HALF_UP for both signs") {
    for ((input, expected) <- Seq("2694999/10000" -> "269.00", "539/2" -> "270.00",
      "-2694999/10000" -> "-269.00", "-539/2" -> "-270.00", "1/-2" -> "-1.00",
      "-1/-2" -> "1.00", "0/1" -> "0.00", "499999/1000000" -> "0.00",
      "999999999999999999999999999999999/2" -> "500000000000000000000000000000000.00"))
      assert(value(op("RoundExact", exact(input))) == expected)
  }

  test("exact products and quotients never quantize to cents") {
    val fraction = divide(op("Multiply", money("250"), money("1")), money("3"))
    assert(value(fraction) == "250/3")
    assert(value(op("Add", fraction, fraction, fraction)) == "250/1")
    assert(value(op("RoundExact", op("Add", exact("125000/1001"), exact("144624/1000")))) == "269.00")
  }

  test("coprime denominators beyond 64 bits remain exact") {
    val denominators = Seq("1000003", "1000033", "1000037", "1000039")
    val terms = denominators.map(d => divide(money("250"), money(d)))
    val sum = op("Add", terms*)
    assert(value(sum) == "1000084002139014868000/1000112004278059472142857")
    assert(value(op("RoundExact", sum)) == "0.00")
  }

  test("a subcent increment changes an exact threshold comparison") {
    val total = op("Add", money("500"), op("Multiply", exact("3/10"), money("0.01")))
    assert(value(total) == "500003/1000")
    assert(value(op("GreaterThan", op("Left", total), op("Right", money("500")))) == "true")
    assert(value(op("LessThanOrEqual", op("Left", total), op("Right", money("500")))) == "false")
    assert(value(op("LesserOf", total, money("500"))) == "500/1")
    assert(value(op("GreaterOf", total, money("500"))) == "500003/1000")
  }

  test("zero denominators and invalid child types fail explicitly") {
    assertThrows[IllegalArgumentException] { value(exact("1/0")) }
    assertThrows[ArithmeticException] { value(divide(money("1"), money("0"))) }
    assertThrows[UnsupportedOperationException] { value(op("ToExact", literal("String", "1"))) }
    assertThrows[UnsupportedOperationException] { value(op("RoundExact", literal("Dollar", "1"))) }
    assertThrows[UnsupportedOperationException] { value(op("Add", money("1"), literal("Dollar", "1"))) }
    assertThrows[IllegalArgumentException] { value(op("ToExact")) }
    assertThrows[IllegalArgumentException] { value(op("RoundExact", exact("1/1"), exact("2/1"))) }
  }

  test("existing Dollar and Rational arithmetic remains unchanged") {
    assert(value(divide(literal("Dollar", "1"), literal("Dollar", "3"))) == "0.33")
    assert(value(op("Round", literal("Dollar", "269.50"))) == "270.00")
    assert(value(divide(literal("Rational", "1/1"), literal("Rational", "3/1"))) == "1/3")
  }

  test("exact subtraction and signed comparisons use numerical order") {
    assert(value(op("Subtract", op("Minuend", exact("1/3")), op("Subtrahends", exact("1/2")))) == "-1/6")
    assert(value(op("LessThan", op("Left", exact("1/-2")), op("Right", exact("0/1")))) == "true")
    assert(value(op("GreaterThanOrEqual", op("Left", exact("1/-2")), op("Right", exact("-2/4")))) == "true")
  }

  test("conversion and rounding propagate incomplete and placeholder values") {
    val missingDollar = DollarNode(Expression.Constant(None))
    val missingExact = ExactRationalNode(Expression.Constant(None))
    assert(ToExact(missingDollar).get(0) == Result.Incomplete)
    assert(RoundExact(missingExact).get(0) == Result.Incomplete)
    val placeholderDollar = Placeholder(missingDollar, DollarNode(Dollar("1.50"))).asInstanceOf[DollarNode]
    assert(ToExact(placeholderDollar).get(0) == Result.Placeholder(ExactRational("3/2")))
    assert(RoundExact(ToExact(placeholderDollar)).get(0) == Result.Placeholder(Dollar("2.00")))
  }

  test("collection aggregation remains exact and requires each item's answer") {
    val dictionary = FactDictionary()
    def add(path: String, writable: Option[WritableConfigElement], derived: Option[CompNodeConfigElement]): Unit =
      FactDefinition.fromConfig(FactConfigElement(path, writable, derived, None))(using dictionary)
    def dep(path: String) = new CompNodeConfigElement("Dependency", Seq.empty, path)
    add("/items", Some(new WritableConfigElement("Collection")), None)
    add("/items/*/amount", Some(new WritableConfigElement("Dollar")), None)
    add("/items/*/exact", None, Some(op("ToExact", dep("../amount"))))
    add("/sum", None, Some(op("CollectionSum", dep("/items/*/exact"))))
    val graph = Graph(dictionary)
    val a = UUID.fromString("00000000-0000-0000-0000-000000000001")
    val b = UUID.fromString("00000000-0000-0000-0000-000000000002")
    graph(Path("/items"))(0).get.set(Collection(Vector(a, b)))
    graph.save()
    graph(Path(s"/items/#$a/amount"))(0).get.set(Dollar("12.34"))
    graph.save()
    assert(graph(Path("/sum"))(0).get.get(0) == Result.Incomplete)
    graph(Path(s"/items/#$b/amount"))(0).get.set(Dollar("-0.01"))
    graph.save()
    assert(graph(Path("/sum"))(0).get.get(0) == Result.Complete(ExactRational("1233/100")))
    val firstMissing = Graph(dictionary)
    firstMissing(Path("/items"))(0).get.set(Collection(Vector(a, b)))
    firstMissing.save()
    firstMissing(Path(s"/items/#$b/amount"))(0).get.set(Dollar("1.00"))
    firstMissing.save()
    assert(firstMissing(Path("/sum"))(0).get.get(0) == Result.Incomplete)
    val emptyGraph = Graph(dictionary)
    emptyGraph(Path("/items"))(0).get.set(Collection(Vector.empty))
    emptyGraph.save()
    assert(emptyGraph(Path("/sum"))(0).get.get(0) == Result.Complete(ExactRational("0/1")))
  }

  test("exact Switch preserves type and mixed comparisons are rejected") {
    val config = op("Switch",
      op("Case", op("When", op("False")), op("Then", exact("1/3"))),
      op("Case", op("When", op("True")), op("Then", exact("2/3"))))
    assert(value(config) == "2/3")
    assertThrows[UnsupportedOperationException] {
      value(op("GreaterThan", op("Left", money("1")), op("Right", literal("Dollar", "1"))))
    }
  }
