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
// Original path: shared/src/test/scala/gov/irs/factgraph/types/BankAccountSpec.scala

package gov.irs.factgraph.types

import org.scalatest.funspec.AnyFunSpec

class BankAccountSpec extends AnyFunSpec:
  def buildBankAccount(
      accountType: String = "Checking",
      routingNumber: String = "323075880", // DC Credit Union
      accountNumber: String = "12345ABCDEF",
  ) =
    new BankAccount(accountType, routingNumber, accountNumber)

  describe("BankAccount") {
    it("constructs correctly when fields are valid") {
      val bankAccount = buildBankAccount()

      assert(bankAccount.accountType === "Checking")
      assert(bankAccount.routingNumber === "323075880")
      assert(bankAccount.accountNumber === "12345ABCDEF")
    }

    describe("preconditions for accountType") {
      it("throws an error when accountType is empty") {
        val e = intercept[BankAccountValidationFailure] {
          buildBankAccount(accountType = "")
        }

        assert(
          e.fieldErrors("accountType").validationMessage == BankAccountFailureReason.InvalidAccountType,
        )
      }

      it("throws an error when an invalid accountType is provided") {
        val e = intercept[BankAccountValidationFailure] {
          buildBankAccount(accountType = "Crypto")
        }

        assert(
          e.fieldErrors("accountType").validationMessage == BankAccountFailureReason.InvalidAccountType,
        )
      }
    }

    describe("preconditions for routingNumber") {
      it("throws an error when routingNumber is empty") {
        val e = intercept[BankAccountValidationFailure] {
          buildBankAccount(routingNumber = "")
        }

        assert(
          e.fieldErrors("routingNumber").validationMessage == BankAccountFailureReason.InvalidRoutingNumber,
        )
      }

      describe("when valid routingNumber is provided") {
        val ValidUsRoutingNumbers = List(
          "011000015", // Federal reserve bank
          "323075880", // OnPoint Commmunity Credit Union
          "254074455", // DC Credit Union
        )

        ValidUsRoutingNumbers.foreach { routingNumber =>
          it(s"constructs without error ($routingNumber)") {
            buildBankAccount(routingNumber = routingNumber)
          }
        }
      }

      describe("when routingNumber is invalid") {
        val MalformedUsRoutingNumbers = List(
          // Too short
          "1",
          "11011011",

          // Invalid characters
          "ABCEFGHIJ",
          "011 00 15",
          "><1|5|9#$",
        )

        MalformedUsRoutingNumbers.foreach { routingNumber =>
          it(s"throws a malformed routing number error ($routingNumber)") {
            val e = intercept[BankAccountValidationFailure] {
              buildBankAccount(routingNumber = routingNumber)
            }

            assert(
              e.fieldErrors("routingNumber").validationMessage == BankAccountFailureReason.InvalidRoutingNumber,
            )
          }
        }
      }

      describe("when routingNumber's prefix is wrong") {
        val MalformedUsRoutingNumbers = List(
          // doesn't match regex: (01|02|03|04|05|06|07|08|09|10|11|12|21|22|23|24|25|26|27|28|29|30|31|32)[0-9]{7}
          "331234567",
          "131111111",
          "177777777",
        )

        MalformedUsRoutingNumbers.foreach { routingNumber =>
          it(s"throws a malformed routing number error ($routingNumber)") {
            val e = intercept[BankAccountValidationFailure] {
              buildBankAccount(routingNumber = routingNumber)
            }

            assert(
              e.fieldErrors("routingNumber").validationMessage == BankAccountFailureReason.MalformedRoutingNumber,
            )
          }
        }
      }

      describe("when routing number fails checksum") {
        val InvalidUsRoutingNumbers = List(
          // Failing checksums
          "110110111",
          "222222222",
          "123456789",
        )

        InvalidUsRoutingNumbers.foreach { routingNumber =>
          it(s"throws a checksum error ($routingNumber)") {
            val e = intercept[BankAccountValidationFailure] {
              buildBankAccount(routingNumber = routingNumber)
            }

            assert(
              e.fieldErrors("routingNumber").validationMessage == BankAccountFailureReason.InvalidRoutingNumberChecksum,
            )
          }
        }
      }
    }

    describe("preconditions for accountNumber") {
      describe("when accountNumber is blank") {
        it("throws an MalformedAccountNumber error") {
          val e = intercept[BankAccountValidationFailure] {
            buildBankAccount(accountNumber = "")
          }

          assert(
            e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.MalformedAccountNumber,
          )
        }
      }

      describe("when a 5 digit account number is provided") {
        it("constructs without error") {
          buildBankAccount(accountNumber = "12345")
        }
      }

      describe("when a 17 digit account number is provided") {
        it("constructs without error") {
          buildBankAccount(accountNumber = "12345678901234567")
        }
      }

      // ytax change (2026-09-27): the 2025 Instructions for
      // Form 1040, line 35d, set no minimum length ("The account number can be up to 17
      // characters (both numbers and letters). Include hyphens but omit spaces and special
      // symbols."). The former 5-character floor refused a valid answer, so "1234" now
      // constructs; under the old rule it threw MalformedAccountNumber.
      describe("when accountNumber is shorter than 5 characters") {
        List("1", "12", "123", "1234", "A", "7B").foreach { accountNumber =>
          it(s"constructs without error ($accountNumber)") {
            assert(buildBankAccount(accountNumber = accountNumber).accountNumber === accountNumber)
          }
        }
      }

      describe("when accountNumber contains hyphens") {
        List(
          "12-3456-78",
          "1234-5678-9012-34", // 17 characters
          "12AB-34CD-56EF-78", // 17 characters, letters and digits
          "ABC-12345",
          "1-2",
          "-12345",
          "12345-",
          "12--345",
        ).foreach { accountNumber =>
          it(s"constructs without error ($accountNumber)") {
            assert(buildBankAccount(accountNumber = accountNumber).accountNumber === accountNumber)
          }
        }
      }

      describe("when accountNumber has a space, a special symbol, a lowercase letter, no letter or digit, or 18 characters") {
        List(
          "1234 5678",
          " 12345",
          "12345 ",
          "123_456",
          "123.456",
          "123/456",
          "#12345",
          "12345abc",
          "-",
          "---",
          "1234-5678-9012-345", // 18 characters with hyphens
          "123456789012345678", // 18 characters
        ).foreach { accountNumber =>
          it(s"throws an MalformedAccountNumber error ($accountNumber)") {
            val e = intercept[BankAccountValidationFailure] {
              buildBankAccount(accountNumber = accountNumber)
            }

            assert(
              e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.MalformedAccountNumber,
            )
          }
        }
      }

      describe("when accountNumber is only zeros once hyphens are set aside") {
        List("0", "0000", "0-0-0", "000-000", "-0").foreach { accountNumber =>
          it(s"throws an InvalidAllZerosAccountNumber error ($accountNumber)") {
            val e = intercept[BankAccountValidationFailure] {
              buildBankAccount(accountNumber = accountNumber)
            }

            assert(
              e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.InvalidAllZerosAccountNumber,
            )
          }
        }
      }

      describe("when a zero-led account number has another digit") {
        List("0001", "0-1", "00000000000000001").foreach { accountNumber =>
          it(s"constructs without error ($accountNumber)") {
            assert(buildBankAccount(accountNumber = accountNumber).accountNumber === accountNumber)
          }
        }
      }

      describe("when accountNumber is too long") {
        it("throws an MalformedAccountNumber error") {
          val e = intercept[BankAccountValidationFailure] {
            buildBankAccount(accountNumber = "123456789012345678")
          }

          assert(
            e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.MalformedAccountNumber,
          )
        }
      }

      describe("when accountNumber is all zeros") {
        it("throws an InvalidAllZerosAccountNumber error lower limit") {
          val e = intercept[BankAccountValidationFailure] {
            buildBankAccount(accountNumber = "00000")
          }

          assert(
            e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.InvalidAllZerosAccountNumber,
          )
        }
        it("throws an InvalidAllZerosAccountNumber error upper limit") {
          val e = intercept[BankAccountValidationFailure] {
            buildBankAccount(accountNumber = "00000000000000000")
          }

          assert(
            e.fieldErrors("accountNumber").validationMessage == BankAccountFailureReason.InvalidAllZerosAccountNumber,
          )
        }
      }
    }
  }
