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
// Original path: shared/src/main/scala/gov/irs/factgraph/types/Rational.scala

package gov.irs.factgraph.types

import scala.scalajs.js.annotation.{ JSExport, JSExportAll, JSExportTopLevel }
import scala.util.matching.Regex
import upickle.default.ReadWriter

// 64-BIT RATIONAL (ytax change, Rational overflow, 2026-09-28).
// The numerator and denominator are Long. Until this change they were Int and every product
// was formed in 32 bits, so `333333/1000000 * 10000` wrapped at 2^31 and resolved to
// -60102331/62500 on the JVM and on Scala.js alike (Form 8962 line 8a went negative above
// $2,526,451 of household income). Arithmetic now runs in Long with overflow-checked
// intermediates (Math.multiplyExact / addExact / subtractExact); when an intermediate would pass
// 2^63 the operation is redone exactly in BigInt and reduced before it is narrowed back to
// Long, so the only case that still throws is a REDUCED result that does not fit in Long.
// Wherever the old Int arithmetic did not overflow, every result is the same Rational as
// before, including the unsimplified same-denominator sums.
@JSExportTopLevel("Rational")
final case class Rational(private val n: Long, private val d: Long) derives ReadWriter:
  import Rational.RationalIsFractional._

  def numerator: Long = n
  def denominator: Long = d

  def reciprocal: Rational = n match
    case 0L => throw new ArithmeticException("reciprocal of zero")
    case _  => Rational(d, n)

  def simplify: Rational = Rational.reduced(n, d)

  def +(that: Rational): Rational = plus(this, that)
  def -(that: Rational): Rational = minus(this, that)
  def *(that: Rational): Rational = times(this, that)
  def /(that: Rational): Rational = div(this, that)

  def <(that: Rational): Boolean = lt(this, that)
  def >(that: Rational): Boolean = gt(this, that)
  def <=(that: Rational): Boolean = lteq(this, that)
  def >=(that: Rational): Boolean = gteq(this, that)

  override def toString: String = s"$n/$d"

given Conversion[Int, Rational] = Rational(_)

object Rational:
  private val Pattern: Regex = """^(-?\d+)/(-?\d+)$""".r

  @JSExportTopLevel("RationalFactory")
  def apply(n: Int, d: Int): Rational = apply(n.toLong, d.toLong)

  def apply(n: Long, d: Long): Rational = d match
    case 0L => throw new IllegalArgumentException("denominator cannot be zero")
    case _  => new Rational(n, d)

  @JSExportTopLevel("RationalFactory")
  def apply(i: Int): Rational = new Rational(i.toLong, 1L)

  @JSExportTopLevel("RationalFactory")
  def apply(str: String): Rational =
    Numeric[Rational].parseString(str) match
      case Some(x) => x
      case None    =>
        throw new NumberFormatException(s"""For input string: "$str"""")

  @annotation.tailrec
  private def gcd(a: Long, b: Long): Long = a match
    case 0L => b.abs
    case _  => gcd(b % a, a)

  // n/d in lowest terms with a positive denominator (the rule `simplify` always applied).
  private[types] def reduced(n: Long, d: Long): Rational =
    val divisor = gcd(n, d) * (if (d < 0L) -1L else 1L)
    Rational(n / divisor, d / divisor)

  // The exact path, taken only when a Long intermediate would overflow.
  private def reducedBig(n: BigInt, d: BigInt): Rational =
    val g = n.gcd(d) * (if (d < 0) -1 else 1)
    val rn = n / g
    val rd = d / g
    if (!rn.isValidLong || !rd.isValidLong)
      throw new ArithmeticException(
        s"Rational overflow: $rn/$rd does not fit in 64-bit integers",
      )
    Rational(rn.toLong, rd.toLong)

  private def big(x: Long): BigInt = BigInt(x)

  implicit object RationalIsFractional extends Fractional[Rational]:
    def compare(x: Rational, y: Rational): Int =
      try java.lang.Long.compare(Math.multiplyExact(x.n, y.d), Math.multiplyExact(y.n, x.d))
      catch case _: ArithmeticException => (big(x.n) * y.d).compare(big(y.n) * x.d)

    def fromInt(x: Int): Rational = Rational(x)

    def minus(x: Rational, y: Rational): Rational =
      if (x.d == y.d)
        try Rational(Math.subtractExact(x.n, y.n), x.d)
        catch case _: ArithmeticException => reducedBig(big(x.n) - y.n, big(x.d))
      else
        try
          reduced(
            Math.subtractExact(Math.multiplyExact(x.n, y.d), Math.multiplyExact(y.n, x.d)),
            Math.multiplyExact(x.d, y.d),
          )
        catch case _: ArithmeticException => reducedBig(big(x.n) * y.d - big(y.n) * x.d, big(x.d) * y.d)

    def negate(x: Rational): Rational = Rational(-x.n, x.d)

    def plus(x: Rational, y: Rational): Rational =
      if (x.d == y.d)
        try Rational(Math.addExact(x.n, y.n), x.d)
        catch case _: ArithmeticException => reducedBig(big(x.n) + y.n, big(x.d))
      else
        try
          reduced(
            Math.addExact(Math.multiplyExact(x.n, y.d), Math.multiplyExact(y.n, x.d)),
            Math.multiplyExact(x.d, y.d),
          )
        catch case _: ArithmeticException => reducedBig(big(x.n) * y.d + big(y.n) * x.d, big(x.d) * y.d)

    def times(x: Rational, y: Rational): Rational =
      try reduced(Math.multiplyExact(x.n, y.n), Math.multiplyExact(x.d, y.d))
      catch case _: ArithmeticException => reducedBig(big(x.n) * y.n, big(x.d) * y.d)

    def div(x: Rational, y: Rational): Rational = y.n match
      case 0L => throw new ArithmeticException("divide by zero")
      case _  =>
        try reduced(Math.multiplyExact(x.n, y.d), Math.multiplyExact(x.d, y.n))
        catch case _: ArithmeticException => reducedBig(big(x.n) * y.d, big(x.d) * y.n)

    def parseString(str: String): Option[Rational] =
      Pattern.findFirstMatchIn(str) match
        case Some(m) => Some(Rational(m.group(1).toLong, m.group(2).toLong))
        case None    => None

    override def toDouble(x: Rational): Double =
      throw new UnsupportedOperationException(
        "toDouble might result in a loss of precision",
      )
    override def toFloat(x: Rational): Float =
      throw new UnsupportedOperationException(
        "toFloat might result in a loss of precision",
      )
    override def toInt(x: Rational): Int =
      throw new UnsupportedOperationException(
        "toInt might result in a loss of precision",
      )
    override def toLong(x: Rational): Long =
      throw new UnsupportedOperationException(
        "toLong might result in a loss of precision",
      )
