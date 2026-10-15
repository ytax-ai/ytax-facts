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

package gov.irs.factgraph.limits

import gov.irs.factgraph.{ FactDefinition, FactDictionary, Graph }
import gov.irs.factgraph.definitions.fact.*
import gov.irs.factgraph.monads.Result
import gov.irs.factgraph.types.{ Collection, Day, Dollar, WritableType }
import java.util.UUID
import org.scalatest.funspec.AnyFunSpec

class CollectionLimitContextSpec extends AnyFunSpec:
  private val docA = UUID.fromString("ad990100-0000-4000-8000-000000000001")
  private val docB = UUID.fromString("ad990100-0000-4000-8000-000000000002")
  private val rowA = UUID.fromString("ad990200-0000-4000-8000-000000000001")
  private val rowB = UUID.fromString("ad990200-0000-4000-8000-000000000002")

  private def literal(kind: String, value: String): CompNodeConfigTrait =
    new CompNodeConfigElement(kind, Seq.empty, CommonOptionConfigTraits.value(value))

  private case class Example(
      label: String,
      kind: String,
      operation: String,
      boundKind: String,
      bound: String,
      valid: WritableType,
      invalid: WritableType,
      reportedActual: String,
  )

  private val examples = Seq(
    Example("negative cent", "Dollar", "Min", "Dollar", "0", Dollar("0.01"), Dollar("-0.01"), "-0.01"),
    Example("negative dollar", "Dollar", "Min", "Dollar", "0", Dollar("1.00"), Dollar("-1.00"), "-1.00"),
    Example("dollar maximum", "Dollar", "Max", "Dollar", "10", Dollar("10.00"), Dollar("10.01"), "10.01"),
    Example("integer minimum", "Int", "Min", "Int", "1", 1, 0, "0"),
    Example("date minimum", "Day", "Min", "Day", "2025-01-01", Day("2025-01-01"), Day("2024-12-31"), "2024-12-31"),
    Example("currency format", "String", "Match", "String", "^[A-Z]{3}$", "USD", "usd", "usd"),
    Example("minimum length", "String", "MinLength", "Int", "2", "US", "U", "1"),
    Example("maximum length", "String", "MaxLength", "Int", "3", "USD", "USDX", "4"),
    Example("collection size", "Collection", "MaxCollectionSize", "Int", "1", Collection(Vector(rowA)), Collection(Vector(rowA, rowB)), "2"),
  )

  private def addWritable(dictionary: FactDictionary, path: String, kind: String,
                          limits: Seq[LimitConfigTrait] = Seq.empty): Unit =
    FactDefinition.fromConfig(
      FactConfigElement(path, Some(new WritableConfigElement(kind, Seq.empty, limits)), None, None),
    )(using dictionary)

  private def limit(example: Example, rhs: CompNodeConfigTrait,
                    severity: LimitLevel = LimitLevel.Error): LimitConfigTrait =
    new LimitConfigTrait:
      override def operation: String = example.operation
      override def level: LimitLevel = severity
      override def node: CompNodeConfigTrait = rhs

  private def makeGraph(example: Example, docs: Vector[UUID] = Vector(docA),
                        rows: Vector[UUID] = Vector(rowA, rowB),
                        severity: LimitLevel = LimitLevel.Error): Graph =
    val dictionary = FactDictionary()
    val limits = Seq(limit(example, literal(example.boundKind, example.bound), severity))
    addWritable(dictionary, "/documents", "Collection")
    addWritable(dictionary, "/documents/*/rows", "Collection")
    addWritable(dictionary, "/documents/*/rows/*/value", example.kind, limits)
    addWritable(dictionary, "/standalone", example.kind, limits)
    val graph = Graph(dictionary)
    assert(graph.set("/documents", Collection(docs))._1)
    docs.foreach(id => assert(graph.set(s"/documents/#$id/rows", Collection(rows))._1))
    graph

  private def path(doc: UUID, row: UUID): String = s"/documents/#$doc/rows/#$row/value"

  private def assertViolation(report: (Boolean, Seq[LimitViolation]), target: String,
                              example: Example): Unit =
    assert(!report._1, s"${example.label}: $target must reject its own invalid value")
    val failures = report._2
    assert(failures.size == 1)
    assert(failures.head.factPath == target)
    assert(failures.head.limitName == example.operation)
    assert(failures.head.actual == example.reportedActual)
    assert(failures.head.LimitLevel == LimitLevel.Error)

  describe("collection limits use the concrete fact being validated") {
    examples.foreach { example =>
      describe(example.label) {
        Seq(false, true).foreach { firstAnswered =>
          it(s"rejects an invalid later row when the first row is answered=$firstAnswered") {
            val graph = makeGraph(example)
            val first = path(docA, rowA)
            val target = path(docA, rowB)
            if firstAnswered then assert(graph.set(first, example.valid)._1)
            assertViolation(graph.set(target, example.invalid), target, example)
            assert(graph.get(target) == Result.Incomplete)
            if firstAnswered then assert(graph.get(first) == Result.Complete(example.valid))
            else assert(graph.get(first) == Result.Incomplete)
          }
        }
        it("does not validate a later row against another row's rejected working value") {
          val graph = makeGraph(example)
          val first = path(docA, rowA)
          val target = path(docA, rowB)
          assertViolation(graph.set(first, example.invalid), first, example)
          val report = graph.set(target, example.valid)
          assert(report._1)
          assert(report._2.isEmpty)
          assert(graph.get(target) == Result.Complete(example.valid))
        }
        Seq(false, true).foreach { reversed =>
          it(s"keeps reused child identifiers local to each document, reversed=$reversed") {
            val docs = if reversed then Vector(docB, docA) else Vector(docA, docB)
            val rows = if reversed then Vector(rowB, rowA) else Vector(rowA, rowB)
            val graph = makeGraph(example, docs, rows)
            val first = path(docs.head, rows.head)
            val target = path(docs.last, rows.last)
            assert(graph.set(first, example.valid)._1)
            assertViolation(graph.set(target, example.invalid), target, example)
            assert(graph.get(first) == Result.Complete(example.valid))
            assert(graph.get(target) == Result.Incomplete)
          }
        }
        it("preserves validation for a single nested row") {
          val graph = makeGraph(example, rows = Vector(rowA))
          val target = path(docA, rowA)
          assertViolation(graph.set(target, example.invalid), target, example)
          assert(graph.get(target) == Result.Incomplete)
        }
        it("preserves standalone validation and recovery after a rejected working value") {
          val graph = makeGraph(example, rows = Vector(rowA))
          assertViolation(graph.set("/standalone", example.invalid), "/standalone", example)
          assert(graph.get("/standalone") == Result.Incomplete)
          val report = graph.set("/standalone", example.valid)
          assert(report._1)
          assert(report._2.isEmpty)
          assert(graph.get("/standalone") == Result.Complete(example.valid))
        }
      }
    }

    it("preserves a relative bound from the target row") {
      val dictionary = FactDictionary()
      val example = examples.head
      addWritable(dictionary, "/documents", "Collection")
      addWritable(dictionary, "/documents/*/rows", "Collection")
      addWritable(dictionary, "/documents/*/rows/*/minimum", "Dollar")
      val rhs = new CompNodeConfigElement("Dependency", Seq.empty, CommonOptionConfigTraits.path("../minimum"))
      addWritable(dictionary, "/documents/*/rows/*/value", "Dollar", Seq(limit(example, rhs)))
      val graph = Graph(dictionary)
      assert(graph.set("/documents", Collection(Vector(docA)))._1)
      assert(graph.set(s"/documents/#$docA/rows", Collection(Vector(rowA, rowB)))._1)
      assert(graph.set(s"/documents/#$docA/rows/#$rowA/minimum", Dollar("0"))._1)
      assert(graph.set(s"/documents/#$docA/rows/#$rowB/minimum", Dollar("10"))._1)
      assert(graph.set(path(docA, rowA), Dollar("20"))._1)
      val target = path(docA, rowB)
      val report = graph.set(target, Dollar("5"))
      assert(!report._1)
      assert(report._2.size == 1)
      assert(report._2.head.actual == "5.00")
      assert(report._2.head.limit == "10.00")
      assert(graph.set(target, Dollar("10"))._1)
    }

    Seq(false, true).foreach { placeholder =>
      it(s"keeps an unknown bound nonblocking, placeholder=$placeholder") {
        val dictionary = FactDictionary()
        addWritable(dictionary, "/documents", "Collection")
        addWritable(dictionary, "/documents/*/rows", "Collection")
        if placeholder then
          FactDefinition.fromConfig(
            FactConfigElement("/documents/*/rows/*/minimum", Some(new WritableConfigElement("Dollar", Seq.empty, Seq.empty)), None, Some(literal("Dollar", "10"))),
          )(using dictionary)
        else addWritable(dictionary, "/documents/*/rows/*/minimum", "Dollar")
        val rhs = new CompNodeConfigElement("Dependency", Seq.empty, CommonOptionConfigTraits.path("../minimum"))
        addWritable(dictionary, "/documents/*/rows/*/value", "Dollar", Seq(limit(examples.head, rhs)))
        val graph = Graph(dictionary)
        assert(graph.set("/documents", Collection(Vector(docA)))._1)
        assert(graph.set(s"/documents/#$docA/rows", Collection(Vector(rowA, rowB)))._1)
        val target = path(docA, rowB)
        val report = graph.set(target, Dollar("-0.01"))
        assert(report._1)
        assert(report._2.isEmpty)
        assert(graph.get(target) == Result.Complete(Dollar("-0.01")))
      }
    }

    it("preserves warning severity and reports the attempted later-row amount") {
      val example = examples.head
      val graph = makeGraph(example, severity = LimitLevel.Warn)
      val target = path(docA, rowB)
      val report = graph.set(target, example.invalid)
      assert(report._1)
      assert(report._2.size == 1)
      assert(report._2.head.LimitLevel == LimitLevel.Warn)
      assert(report._2.head.factPath == target)
      assert(report._2.head.actual == "-0.01")
      assert(graph.get(target) == Result.Complete(example.invalid))
    }
  }
