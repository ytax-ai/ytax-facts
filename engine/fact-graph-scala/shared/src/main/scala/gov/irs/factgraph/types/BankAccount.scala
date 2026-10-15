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
// Original path: shared/src/main/scala/gov/irs/factgraph/types/BankAccount.scala

package gov.irs.factgraph.types
import gov.irs.factgraph.validation.{ ValidationFailure, ValidationFailureReason }
import java.lang.Enum
import scala.beans.BeanProperty
import scala.scalajs.js
import scala.scalajs.js.annotation.{ JSExport, JSExportAll, JSExportTopLevel }
import scala.util.matching.Regex
import upickle.default.ReadWriter

@JSExportAll
enum UserFriendlyBankAccountFailureReason:
  case InvalidBankAccount
  case InvalidAccountType
  case InvalidRoutingNumber
  case MalformedRoutingNumber
  case MalformedAccountNumber
  case InvalidAllZerosAccountNumber

@JSExportAll
enum BankAccountFailureReason extends Enum[BankAccountFailureReason], ValidationFailureReason:
  type UserFriendlyReason = UserFriendlyBankAccountFailureReason

  case InvalidBankAccount

  // AccountType errors
  case InvalidAccountType

  // RoutingNumber errors
  case MalformedRoutingNumber
  case InvalidRoutingNumberChecksum
  case InvalidRoutingNumber

  // AccountNumber errors
  case MalformedAccountNumber
  case InvalidAllZerosAccountNumber

  def toUserFriendlyReason() = this match
    case InvalidBankAccount =>
      UserFriendlyBankAccountFailureReason.InvalidBankAccount
    case InvalidAccountType =>
      UserFriendlyBankAccountFailureReason.InvalidAccountType
    case MalformedRoutingNumber | InvalidRoutingNumberChecksum =>
      UserFriendlyBankAccountFailureReason.MalformedRoutingNumber
    case InvalidRoutingNumber =>
      UserFriendlyBankAccountFailureReason.InvalidRoutingNumber
    case MalformedAccountNumber =>
      UserFriendlyBankAccountFailureReason.MalformedAccountNumber
    case InvalidAllZerosAccountNumber =>
      UserFriendlyBankAccountFailureReason.InvalidAllZerosAccountNumber

@JSExportAll
final case class BankAccountFieldValidationFailure(
    val message: String = "",
    private val cause: Throwable = None.orNull,
    val validationMessage: BankAccountFailureReason,
) extends IllegalArgumentException(message, cause),
      ValidationFailure[BankAccountFailureReason];

type BankAccountFieldName = "accountType" | "routingNumber" | "accountNumber"

@JSExportAll
final case class BankAccountValidationFailure(
    val message: String = "",
    private val cause: Throwable = None.orNull,
    val validationMessage: BankAccountFailureReason,
    val fieldErrors: collection.Map[
      BankAccountFieldName,
      BankAccountFieldValidationFailure,
    ] = collection.Map(),
) extends IllegalArgumentException(message, cause),
      ValidationFailure[BankAccountFailureReason];

@JSExportAll
enum BankAccountType extends Enum[BankAccountType]:
  case Checking
  case Savings

@JSExportTopLevel("BankAccount")
@JSExportAll
final case class BankAccount(
    /** The account type. Must be one of Checking or Savings
      */
    @BeanProperty accountType: String,

    /** A 9 character, numeric id, representing the routing number of the account
      *
      * Represented as a string to allow leading zeroes
      */
    @BeanProperty routingNumber: String,
    /** The account number of the account: 1-17 characters, each an uppercase letter, a digit or a
      * hyphen, with at least one letter or digit, and not only zeros (hyphens aside).
      *
      * ytax change (2026-09-27), from the 2025 Instructions for Form 1040, line 35d: "The account
      * number can be up to 17 characters (both numbers and letters). Include hyphens but omit
      * spaces and special symbols." (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 63). The
      * former rule, [0-9A-Z]{5,17}, refused a hyphenated account number and one under five
      * characters. Lowercase letters stay refused: no MeF schema pattern was found to widen the
      * case rule, so a caller uppercases before writing.
      */
    @BeanProperty accountNumber: String,
) derives ReadWriter:
  final val AllowedAccountTypes = BankAccountType.values.map(v => v.name())

  private[this] var fieldErrors = collection.mutable
    .Map[BankAccountFieldName, BankAccountFieldValidationFailure]()

  // Validate accountType
  try
    precondition(
      AllowedAccountTypes.contains(accountType),
      "accountType must be a valid BankAccountType",
      BankAccountFailureReason.InvalidAccountType,
    )
  catch {
    case e: BankAccountFieldValidationFailure => fieldErrors("accountType") = e
    case _                                    =>
      fieldErrors("accountType") = BankAccountFieldValidationFailure(
        "accountType preconditions failed with unknown failure",
        None.orNull,
        BankAccountFailureReason.InvalidAccountType,
      )
  }

  // Validate routingNumber
  try {
    val RoutingNumberPattern: Regex = """[0-9]{9}""".r
    precondition(
      RoutingNumberPattern.matches(routingNumber),
      "routingNumber must be a 9 character string containing only numbers ",
      BankAccountFailureReason.InvalidRoutingNumber,
    )

    val RoutingNumberPrefixPattern: Regex =
      """(01|02|03|04|05|06|07|08|09|10|11|12|21|22|23|24|25|26|27|28|29|30|31|32)[0-9]{7}""".r
    precondition(
      RoutingNumberPrefixPattern.matches(routingNumber),
      "routingNumber must be a 9 character string containing only numbers and only have certain prefixes",
      BankAccountFailureReason.MalformedRoutingNumber,
    )

    val checksum = routingNumberChecksum(routingNumber)
    precondition(
      checksum % 10 == 0,
      s"routingNumber checksum is invalid ($checksum)",
      BankAccountFailureReason.InvalidRoutingNumberChecksum,
    )
  } catch {
    case e: BankAccountFieldValidationFailure =>
      fieldErrors("routingNumber") = e
    case _ =>
      fieldErrors("routingNumber") = BankAccountFieldValidationFailure(
        "routingNumber preconditions failed with unknown failure",
        None.orNull,
        BankAccountFailureReason.InvalidBankAccount,
      )
  }

  // Validate accountNumber
  try {
    // Only zeros once the hyphens are set aside ("0", "0000", "0-0-0").
    val AllZerosPattern: Regex = """^[0-]*0[0-]*$""".r

    precondition(
      !AllZerosPattern.matches(accountNumber),
      "accountNumber must not contain only zeros",
      BankAccountFailureReason.InvalidAllZerosAccountNumber,
    )
  } catch {
    case e: BankAccountFieldValidationFailure =>
      fieldErrors("accountNumber") = e
    case _ =>
      fieldErrors("accountNumber") = BankAccountFieldValidationFailure(
        "accountNumber preconditions failed with unknown failure",
        None.orNull,
        BankAccountFailureReason.InvalidBankAccount,
      )
  }
  try {
    val AccountNumberPattern: Regex = """[0-9A-Z-]{1,17}""".r
    val AccountNumberHasLetterOrDigit: Regex = """.*[0-9A-Z].*""".r

    precondition(
      AccountNumberPattern.matches(accountNumber) && AccountNumberHasLetterOrDigit.matches(accountNumber),
      "accountNumber must be 1 to 17 characters of uppercase letters, digits and hyphens, with at least one letter or digit",
      BankAccountFailureReason.MalformedAccountNumber,
    )
  } catch {
    case e: BankAccountFieldValidationFailure =>
      fieldErrors("accountNumber") = e
    case _ =>
      fieldErrors("accountNumber") = BankAccountFieldValidationFailure(
        "accountNumber preconditions failed with unknown failure",
        None.orNull,
        BankAccountFailureReason.InvalidBankAccount,
      )
  }

  if (!fieldErrors.isEmpty)
    val fieldErrorDescription = fieldErrors
      .map((fieldName, error) => s"$fieldName: \"${error.message}\"")
      .mkString("\n")

    throw BankAccountValidationFailure(
      s"One or more fields are invalid:\n\n$fieldErrorDescription",
      None.orNull,
      BankAccountFailureReason.InvalidBankAccount,
      fieldErrors,
    )

  private[this] def precondition(
      test: Boolean,
      message: String,
      validationMessage: BankAccountFailureReason,
  ): Unit =
    if (!test)
      throw BankAccountFieldValidationFailure(
        message,
        None.orNull,
        validationMessage,
      )

  private def routingNumberChecksum(routingNumber: String): Int =
    routingNumber
      .grouped(3)
      .foldLeft(0)((sum, triplet) =>
        sum + (
          // NOTE: toString needed to ensure character is parsed rather than cast directly to an int
          triplet(0).toString().toInt * 3
        )
          + (triplet(1).toString().toInt * 7)
          + triplet(2).toString().toInt,
      )
