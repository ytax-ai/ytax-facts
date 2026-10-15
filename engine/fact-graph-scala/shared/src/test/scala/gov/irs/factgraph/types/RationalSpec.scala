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
// Original path: shared/src/test/scala/gov/irs/factgraph/types/RationalSpec.scala

package gov.irs.factgraph.types

import org.scalatest.funspec.AnyFunSpec

class RationalSpec extends AnyFunSpec:
  describe("Rational") {
    describe(".+") {
      it("adds the values") {
        assert(Rational("1/2") + Rational("1/3") == Rational("5/6"))
      }

      it("preserves equivalent denominators") {
        assert(Rational("12/100") + Rational("38/100") == Rational("50/100"))
      }
    }

    describe(".-") {
      it("subtracts the values") {
        assert(Rational("1/2") - Rational("1/3") == Rational("1/6"))
      }

      it("preserves equivalent denominators") {
        assert(Rational("43/100") - Rational("21/100") == Rational("22/100"))
      }
    }

    describe(".*") {
      it("multiplies the values") {
        assert(Rational("1/2") * Rational("1/3") == Rational("1/6"))
      }
    }

    describe("./") {
      it("divides the values") {
        assert(Rational("1/2") / Rational("1/3") == Rational("3/2"))
      }

      describe("when the denominator is zero") {
        it("throws an exception") {
          assertThrows[ArithmeticException] {
            Rational("2/3") / Rational(0)
          }
        }
      }
    }

    describe(".<") {
      it("returns true if the left hand side is less than the right") {
        assert(Rational("2/3") < Rational("3/4"))
        assert(!(Rational("2/3") < Rational("2/3")))
        assert(!(Rational("2/3") < Rational("1/2")))
      }
    }

    describe(".>") {
      it("returns true if the left hand side is greater than the right") {
        assert(!(Rational("2/3") > Rational("3/4")))
        assert(!(Rational("2/3") > Rational("2/3")))
        assert(Rational("2/3") > Rational("1/2"))
      }
    }

    describe(".<=") {
      it(
        "returns true if the left hand side is less than or equal to the right",
      ) {
        assert(Rational("2/3") <= Rational("3/4"))
        assert(Rational("2/3") <= Rational("2/3"))
        assert(!(Rational("2/3") <= Rational("1/2")))
      }
    }

    describe(".>=") {
      it(
        "returns true if the left hand side is greater than or equal to the right",
      ) {
        assert(!(Rational("2/3") >= Rational("3/4")))
        assert(Rational("2/3") >= Rational("2/3"))
        assert(Rational("2/3") >= Rational("1/2"))
      }
    }

    describe(".numerator") {
      it("returns the numerator") {
        assert(Rational("2/3").numerator == 2)
      }
    }

    describe(".denominator") {
      it("returns the denominator") {
        assert(Rational("2/3").denominator == 3)
      }
    }

    describe(".reciprocal") {
      it("finds the reciprocal") {
        assert(Rational("2/3").reciprocal == Rational("3/2"))
      }

      describe("when the numerator is zero") {
        it("throws an exception to prevent a zero denominator") {
          assertThrows[ArithmeticException] {
            Rational(0).reciprocal
          }
        }
      }
    }

    describe(".simplify") {
      it("simplifies the rational") {
        assert(Rational("9/81").simplify == Rational("1/9"))
      }

      it("always returns a positive denominator") {
        assert(Rational("-9/81").simplify == Rational("-1/9"))
        assert(Rational("9/-81").simplify == Rational("-1/9"))
        assert(Rational("-9/-81").simplify == Rational("1/9"))
      }
    }

    describe(".toString") {
      it("expresses the rational as a fraction") {
        assert(Rational(2, 3).toString == "2/3")
      }
    }

    describe("$apply") {
      it("rejects zero denominators") {
        assertThrows[IllegalArgumentException] {
          Rational(1, 0)
        }

        assertThrows[IllegalArgumentException] {
          Rational("1/0")
        }
      }

      it("rejects invalid strings") {
        assertThrows[NumberFormatException] {
          Rational("get/it")
        }
      }
    }
  }

  describe("Rational arithmetic past 32 bits (64-bit Rational)") {
    val r = Rational("333333/1000000")

    it("multiplies by a large Int without wrapping") {
      assert(r * Rational(10000) == Rational("333333/100"))
      assert(Rational(10000) * r == Rational("333333/100"))
      assert(r * Rational("10000/1") == Rational("333333/100"))
    }

    it("is unchanged below the old 2^31 boundary and exact above it") {
      // 333333 * 6442 = 2,147,331,186 fit in Int and resolved correctly before the change;
      // 333333 * 6443 = 2,147,664,519 wrapped to -2147302777/1000000.
      assert(r * Rational(2147) == Rational("715665951/1000000"))
      assert(r * Rational(6442) == Rational("1073665593/500000"))
      val big = r * Rational(6443)
      assert(big == Rational(2147664519L, 1000000L))
      assert(big.numerator == 2147664519L)
      assert(big.toString == "2147664519/1000000")
    }

    it("divides by a small fraction without wrapping") {
      assert(r / Rational("1/10000") == Rational("333333/100"))
    }

    it("reduces a product whose unreduced terms exceed Int (Form 8962 line 8a shape)") {
      // 3,008,075 * 850/10000: the old Int product wrapped to a negative numerator.
      assert(Rational(3008075) * Rational("850/10000") == Rational("2045491/8"))
    }

    it("adds and subtracts across denominators whose cross-product exceeds Int") {
      assert(Rational("1/60000") + Rational("1/40000") == Rational("1/24000"))
      assert(Rational("1/60000") - Rational("1/40000") == Rational("-1/120000"))
      assert(r + Rational("1/999999") == Rational(333333666667L, 999999000000L))
    }

    it("compares without wrapping the cross-products") {
      assert(Rational("3000000/7") > Rational("1/1000"))
      assert(Rational("1/1000") < Rational("3000000/7"))
      assert(Rational("333333/1000000") < Rational("10000/1"))
    }

    it("keeps an unsimplified same-denominator sum") {
      assert(Rational("12/100") + Rational("38/100") == Rational("50/100"))
      assert(Rational("850/10000") - Rational("0/10000") == Rational("850/10000"))
      assert(Rational(Int.MaxValue) + Rational(1) == Rational(2147483648L, 1L))
    }

    it("takes the exact path when a Long intermediate would pass 2^63") {
      // 3037000500^2 > 2^63: the products are formed in BigInt and reduce back into Long.
      val a = Rational(3037000500L, 3037000501L)
      val b = Rational(3037000501L, 3037000500L)
      assert(a * b == Rational(1))
      assert(a < b)
      assert(b > a)
      val c = Rational(1L, 4000000000L)
      assert(c + Rational(1L, 6000000000L) == Rational(1L, 2400000000L))
      assert(c - Rational(1L, 6000000000L) == Rational(1L, 12000000000L))
    }

    it("throws only when the REDUCED value cannot fit in 64 bits") {
      assertThrows[ArithmeticException] {
        Rational(Long.MaxValue, 1L) + Rational(1)
      }
      assertThrows[ArithmeticException] {
        Rational(1L, 3037000501L) * Rational(1L, 3037000507L)
      }
    }

    it("parses and prints numerators past 2^31") {
      assert(Rational("2147664519/1000000") == Rational(2147664519L, 1000000L))
      assert(Rational("-9000000000000/7").toString == "-9000000000000/7")
    }

    it("round-trips through the persister's JSON past 2^31 and past 2^53") {
      import upickle.default.{ read, write }
      import gov.irs.factgraph.persisters.{ RationalWrapper, TypeContainer }
      for v <- Seq(
          Rational("1/2"),
          Rational("850/10000"),
          Rational(2147664519L, 1000000L),
          Rational(-9007199254740993L, 3L),
        )
      do
        assert(read[Rational](write(v)) == v)
        val wrapped: TypeContainer = RationalWrapper(v)
        assert(read[TypeContainer](write(wrapped)) == wrapped)
    }

    it("writes a small Rational in the same JSON shape as the 32-bit type") {
      import upickle.default.write
      assert(write(Rational("1/2")) == """{"n":1,"d":2}""")
      assert(write(Rational("-850/10000")) == """{"n":-850,"d":10000}""")
    }
  }
  describe("Numeric[Rational]") {
    describe(".fromInt") {
      it("returns a rational with 1 as the denominator") {
        assert(Numeric[Rational].fromInt(3) == Rational("3/1"))
      }
    }

    describe(".negate") {
      it("negates positive rationals") {
        assert(Numeric[Rational].negate(Rational("2/3")) == Rational("-2/3"))
      }

      it("negates negative rationals") {
        assert(Numeric[Rational].negate(Rational("-2/3")) == Rational("2/3"))
      }
    }

    describe(".parseString") {
      it("parses valid strings") {
        assert(Numeric[Rational].parseString("2/3").contains(Rational("2/3")))
      }

      it("returns None if the string is not valid") {
        assert(Numeric[Rational].parseString("yo").isEmpty)
      }
    }

    describe(".toDouble") {
      it("throws an exception") {
        assertThrows[UnsupportedOperationException] {
          Numeric[Rational].toDouble(Rational("2/3"))
        }
      }
    }

    describe(".toFloat") {
      it("throws an exception") {
        assertThrows[UnsupportedOperationException] {
          Numeric[Rational].toFloat(Rational("2/3"))
        }
      }
    }

    describe(".toInt") {
      it("throws an exception") {
        assertThrows[UnsupportedOperationException] {
          Numeric[Rational].toInt(Rational("2/3"))
        }
      }
    }

    describe(".toLong") {
      it("throws an exception") {
        assertThrows[UnsupportedOperationException] {
          Numeric[Rational].toLong(Rational("2/3"))
        }
      }
    }
  }
