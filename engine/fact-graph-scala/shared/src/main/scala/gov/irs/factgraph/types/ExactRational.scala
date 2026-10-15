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
package gov.irs.factgraph.types

/** A derived-only, arbitrary-precision fraction. Unlike Dollar, arithmetic never
  * quantizes intermediates. Unlike Rational, coprime sums have no Long bound.
  * Every value is canonical with a positive denominator, so equality is numeric.
  */
final class ExactRational private (val numerator: BigInt, val denominator: BigInt):
  def +(that: ExactRational): ExactRational = ExactRational.ExactRationalIsFractional.plus(this, that)
  def -(that: ExactRational): ExactRational = ExactRational.ExactRationalIsFractional.minus(this, that)
  def *(that: ExactRational): ExactRational = ExactRational.ExactRationalIsFractional.times(this, that)
  def /(that: ExactRational): ExactRational = ExactRational.ExactRationalIsFractional.div(this, that)
  override def toString: String = s"$numerator/$denominator"
  override def equals(other: Any): Boolean = other match
    case x: ExactRational => numerator == x.numerator && denominator == x.denominator
    case _ => false
  override def hashCode(): Int = (numerator, denominator).hashCode()

object ExactRational:
  def apply(n: BigInt, d: BigInt): ExactRational =
    require(d != 0, "denominator cannot be zero")
    val divisor = n.gcd(d) * d.signum
    new ExactRational(n / divisor, d / divisor)

  def apply(text: String): ExactRational = text.split("/", -1) match
    case Array(n, d) => apply(BigInt(n), BigInt(d))
    case _ => throw new NumberFormatException(s"Invalid exact fraction: $text")

  def fromDollar(value: Dollar): ExactRational =
    // Dollar stores exact cents. Decimal string conversion avoids a floating-point bridge.
    val decimal = BigDecimal(value.toString).bigDecimal
    val scale = decimal.scale
    val unscaled = BigInt(decimal.unscaledValue)
    if scale >= 0 then apply(unscaled, BigInt(10).pow(scale))
    else apply(unscaled * BigInt(10).pow(-scale), BigInt(1))

  def roundToDollar(value: ExactRational): Dollar =
    // HALF_UP, directly in integers: ties go away from zero. No cent-rounding step.
    val whole = (value.numerator.abs * 2 + value.denominator) / (value.denominator * 2)
    Dollar(BigDecimal(whole * value.numerator.signum))

  implicit object ExactRationalIsFractional extends Fractional[ExactRational]:
    def compare(x: ExactRational, y: ExactRational): Int =
      (x.numerator * y.denominator).compare(y.numerator * x.denominator)
    def fromInt(x: Int): ExactRational = apply(BigInt(x), BigInt(1))
    def plus(x: ExactRational, y: ExactRational): ExactRational =
      apply(x.numerator * y.denominator + y.numerator * x.denominator, x.denominator * y.denominator)
    def minus(x: ExactRational, y: ExactRational): ExactRational = plus(x, negate(y))
    def negate(x: ExactRational): ExactRational = apply(-x.numerator, x.denominator)
    def times(x: ExactRational, y: ExactRational): ExactRational =
      apply(x.numerator * y.numerator, x.denominator * y.denominator)
    def div(x: ExactRational, y: ExactRational): ExactRational =
      if y.numerator == 0 then throw new ArithmeticException("divide by zero")
      apply(x.numerator * y.denominator, x.denominator * y.numerator)
    def parseString(text: String): Option[ExactRational] =
      try Some(apply(text))
      catch case _: IllegalArgumentException => None
    def toInt(x: ExactRational): Int = throw new UnsupportedOperationException("use RoundExact explicitly")
    def toLong(x: ExactRational): Long = throw new UnsupportedOperationException("use RoundExact explicitly")
    def toFloat(x: ExactRational): Float = throw new UnsupportedOperationException("floating-point conversion loses precision")
    def toDouble(x: ExactRational): Double = throw new UnsupportedOperationException("floating-point conversion loses precision")
