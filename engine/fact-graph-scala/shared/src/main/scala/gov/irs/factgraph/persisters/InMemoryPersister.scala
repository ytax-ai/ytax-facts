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
package gov.irs.factgraph.persisters

import gov.irs.factgraph.compnodes.{ BooleanNode, CompNode, DollarNode, IntNode, StringNode }
import gov.irs.factgraph.definitions.fact.LimitLevel
import gov.irs.factgraph.limits.LimitViolation
import gov.irs.factgraph.monads.Result
import gov.irs.factgraph.types._
import gov.irs.factgraph.Fact
import gov.irs.factgraph.FactDictionary
import gov.irs.factgraph.Graph
import gov.irs.factgraph.Migrations
import gov.irs.factgraph.Path
import gov.irs.factgraph.PersisterSyncIssue
import java.util.UUID
import scala.collection.mutable
import scala.scalajs.js
import scala.scalajs.js.annotation.{ JSExport, JSExportTopLevel }
import ujson.Value
import upickle.default.{ read, write };

final class InMemoryPersister(var store: Map[Path, WritableType]) extends Persister:
  private val live = mutable.Map[Path, WritableType]() ++= store
  private val toValidate = mutable.Queue[Fact]()
  // this may need to be changed into an actual FSM at some point if it gets more complicated
  private var validating = false
  private var validationStore: Map[Path, WritableType] = store
  override def getSavedResult[A](path: Path, klass: Class[A]): Result[A] =
    val st = if validating then validationStore else store
    st.get(path) match
      case Some(value) => Result.Complete(value.asInstanceOf[A])
      case None        => Result.Incomplete

  // Counts the writes that may have made `live` differ from `store`: a set whose value is not the
  // very object already held for that path, and every delete. syncWithDictionary reads it to know
  // whether the next save can change what `store` holds (see the account there).
  private var liveWrites: Long = 0

  override def setFact(fact: Fact, value: WritableType): Unit =
    require(fact.path.isKnown)

    live.get(fact.path) match
      case Some(held) if held.asInstanceOf[AnyRef] eq value.asInstanceOf[AnyRef] =>
      case _                                                                     => liveWrites += 1
    live(fact.path) = value
    toValidate += fact

  /** Delete a fact from this persister.
    *
    * @param fact
    *   The fact to delete.
    * @param deleteSubpaths
    *   Whether to cascade the delete (e.g., `fact.path` is for a collection item).
    */
  override def deleteFact(fact: Fact, deleteSubpaths: Boolean = false): Unit =
    require(fact.path.isKnown)
    // If `toValidate` contains this fact, we need to delete that fact from `toValidate`.
    // Otherwise, our limit validator will attempt to fetch the result of a deleted fact.
    toValidate.dequeueAll(f => f.path == fact.path)
    liveWrites += 1
    deleteSubpaths match
      case true =>
        for ((path, writeable) <- live) do
          path.toString.startsWith(
            s"${fact.path.toString}${Path.Delimiter}",
          ) match
            case true  => fact.graph.delete(path)
            case false =>
      case false =>
        live -= fact.path

  private def pathHasBadItemId(
      path: Path,
      graph: Graph,
  ) =
    path.getMemberId match
      case None     => false
      case Some(id) =>
        !graph
          .getCollectionPaths(path.asAbstract.toString)
          .exists(collectionPath => collectionPath.contains(id.toString))

  // A keyed lookup on the dictionary's own definitions map. It answers exactly what the former
  // linear scan over `dictionary.getPaths()` answered: the map's keys are unique under `Path`
  // equality, and `Path` (a case class over `PathItem`s) has a hashCode consistent with that
  // equality, so at most one key matches and `get` finds the same one. `dictionary(path)` with a
  // `Path` argument is `FactDictionary.apply(path: Path) = definitions.get(path)`, the exact
  // lookup; it is NOT the String overload, which also resolves wildcard and alias paths.
  private def pathExistsAndIsWritable(
      path: Path,
      dictionary: FactDictionary,
  ) =
    dictionary(path).exists(_.isWritable)

  private def checkTypeMapping(
      writableType: WritableType,
      dictionaryType: Class[? <: CompNode],
  ) =
    val persistedValString = writableType.toString()
    val dictionaryTypeName = dictionaryType.getSimpleName()
    writableType match
      case _: java.lang.String if (dictionaryType != classOf[StringNode]) =>
        (
          false,
          Some(
            s"Removed String type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _: java.lang.Byte if dictionaryType != classOf[IntNode] =>
        (
          false,
          Some(
            s"Removed Byte type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _: java.lang.Short if dictionaryType != classOf[IntNode] =>
        (
          false,
          Some(
            s"Removed Short type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _: java.lang.Integer if dictionaryType != classOf[IntNode] =>
        (
          false,
          Some(
            s"Removed Integer type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _: java.lang.Boolean if dictionaryType != classOf[BooleanNode] =>
        (
          false,
          Some(
            s"Removed Boolean type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _: scala.math.BigDecimal if dictionaryType != classOf[DollarNode] =>
        (
          false,
          Some(
            s"Removed BigDecimal type value persisted with ${dictionaryTypeName} path",
          ),
        )
      case _ =>
        (true, None)

  /** Validate every persisted fact against the dictionary, dropping the ones that do not fit.
    *
    * Each kept fact is set and then saved, one at a time, exactly as `graph.set` always did: the
    * same `save()` runs after each fact, with the same `toValidate` and `validationStore`, the same
    * commit rule, and so the same limit outcomes, in the same order, and the same `store`. A
    * rejected fact leaves `live` at once and leaves `store` at the next commit, as before.
    *
    * What changes is only that `graph.save()`'s cache clearing is skipped where it cannot be
    * observed:
    *   - `factCache` holds Fact objects built from the dictionary alone (`makeFact`,
    *     `makeExtract`); none reads the store, so clearing it never changes a result.
    *   - `resultCache` holds values computed from `store` (or from `validationStore` while
    *     validating). A value can go stale only when the content of `store` changes, and `store`
    *     changes only when a save commits `live` and `live` differs from `store`.
    *   - `storeMatchesLive` tracks exactly that. It starts false, so the first save in a sync is
    *     always a full `graph.save()` (whatever the caches held before is dropped, as before). A
    *     committed save makes it true. A rejection (`live -= path`) or a set that writes a value
    *     other than the object already held (`liveWrites`, e.g. the per-item writes of a persisted
    *     wildcard path) makes it false. While it is true, `store`, `live` and every
    *     `validationStore` hold the same content, so every cached value equals what a fresh
    *     evaluation would give, and the save can skip the clearing. Otherwise the full
    *     `graph.save()` runs, as before.
    *   - The trailing `save()` below commits `live` without clearing the caches, as it always
    *     did, so the caches it leaves behind are visible to the caller. When that save changes
    *     `store`, the caches must hold exactly what the per-fact saves left: the values computed
    *     after the last per-fact save, from the store as it then stood. They are rebuilt by
    *     clearing them and repeating, in order, the reads made after that save: its own limit
    *     validation (when it committed) and the bad-item-id checks of the facts that followed.
    *     The store and `validationStore` have not changed since, so the same values result.
    */
  override def syncWithDictionary(graph: Graph): Seq[PersisterSyncIssue] =
    var storeMatchesLive = false
    var savedInSync = false
    var lastSaveValidated: List[Fact] = Nil
    val checkedSinceLastSave = mutable.ArrayBuffer[Path]()
    val results = live.flatMap { (path, writableType) =>
      val dictionaryPath = path.isCollectionMember match
        case true  => path.asAbstract
        case false => path

      val (keepFact, optionalMessage) =
        if (pathHasBadItemId(path, graph))
          (false, Some("Removed bad item ID path from persister"))
        else if (!pathExistsAndIsWritable(dictionaryPath, graph.dictionary))
          (false, Some("Removed unknown or non-writable path from persister"))
        else
          writableType match
            case _: WritableType =>
              checkTypeMapping(
                writableType,
                graph.dictionary(dictionaryPath).get.value.getClass,
              )

      if (keepFact)
        val toWrite = writableType match
          case _ => writableType
        val writesBefore = liveWrites
        graph.setWithoutSave(path, toWrite)
        if (liveWrites != writesBefore) storeMatchesLive = false
        val validated = toValidate.toList
        val committed =
          if (storeMatchesLive)
            val (ok, _) = saveStoreHoldsLive()
            // graph.save() clears the result cache again after a failed save; so does this.
            if (!ok) graph.resultCache.clear()
            ok
          else graph.save()._1
        if (committed) storeMatchesLive = true
        savedInSync = true
        lastSaveValidated = if (committed) validated else Nil
        checkedSinceLastSave.clear()
        if (optionalMessage.nonEmpty)
          Some(PersisterSyncIssue(path.toString, optionalMessage.get))
        else None
      else
        live -= path
        storeMatchesLive = false
        checkedSinceLastSave += path
        Some(
          PersisterSyncIssue(
            path.toString,
            optionalMessage.getOrElse("Description is missing for this error"),
          ),
        )
    }.toSeq

    if (savedInSync && !storeMatchesLive)
      graph.factCache.clear()
      graph.resultCache.clear()
      if (lastSaveValidated.nonEmpty)
        validating = true
        lastSaveValidated.foreach(_.validate())
        validating = false
      checkedSinceLastSave.foreach(pathHasBadItemId(_, graph))
    save()
    results

  // save() for the case where `store` already holds exactly what `live` holds and `live` has not
  // been restructured since `store` was copied from it (syncWithDictionary's `storeMatchesLive`):
  // save()'s two `live.toMap` copies would equal `store`, entry for entry and in iteration order,
  // so `store` itself serves as the validation store and stays the committed store. The limit
  // validation and the commit decision are save()'s own.
  private def saveStoreHoldsLive(): (Boolean, Seq[LimitViolation]) =
    validationStore = store
    validating = true
    val issues = toValidate.flatMap(x => x.validate()).toSeq
    toValidate.clear()
    validating = false
    if (issues.exists(x => x.LimitLevel == LimitLevel.Error)) (false, issues)
    else (true, issues)

  override def save(): (Boolean, Seq[LimitViolation]) =
    validationStore = live.toMap
    validating = true
    val issues = toValidate.flatMap(x => x.validate()).toSeq
    toValidate.clear()
    validating = false
    // The only level that should stop us from saving
    // is an actual error
    if (issues.exists(x => x.LimitLevel == LimitLevel.Error)) (false, issues)
    else
      store = live.toMap
      (true, issues)

  // toStringMap is a purely debug function for just inspecting your graph
  def toStringMap(): Map[String, String] =
    store
      .map((path, value) => (path.toString, s"${value.toString}"))

  def toJson(indent: Int = -1): String =
    // Because migrations are applied prior to initializing the InMemoryPersister,
    // all in-memory persisters are guaranteed to have all the most recent migrations.
    // Therefore, upon serializing it, we simply add the current number of migrations;
    // when it's deserialized into a possibly-new Persister, any new migrations will be applied.
    val wrappedStore = store
      .map((path, value) => (path.toString, TypeContainer(value)))
      + (Migrations.MigrationsFieldName -> TypeContainer(Migrations.TotalMigrations))
    write(wrappedStore, indent)

object InMemoryPersister:
  def apply(): InMemoryPersister = new InMemoryPersister(
    Map[Path, WritableType](),
  )

  def apply(seeds: (String, WritableType)*): InMemoryPersister =
    val pathSeeds = seeds.map((path, value) => (Path(path), value))
    new InMemoryPersister(Map(pathSeeds*))

  def apply(jsonString: String): InMemoryPersister =
    val jsonData = read[Map[String, Value]](jsonString)

    // Migrations are applied only to fact graphs that were persisted via JSON string;
    // everything else is initialized in-memory, and therefore assumed to be current
    val totalMigrations = jsonData
      .get(Migrations.MigrationsFieldName)
      .flatMap(data => data("item").numOpt)
      .getOrElse(0.0)
      .toInt

    // The migrations field is not actually stored in-memory (it only appears on serialization)
    // so we drop it before converting the JSON to actual facts
    val unwrappedData = jsonData.-(Migrations.MigrationsFieldName)
    val migratedData = Migrations.run(unwrappedData, totalMigrations)

    new InMemoryPersister(migratedData)
