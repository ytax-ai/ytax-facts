# Exact derived arithmetic

`ExactRational` is an additive, derived-only numeric type backed by arbitrary-precision integers.
It retains fractions between graph operations; it is not a writable or persisted taxpayer money
type. Existing `Dollar`, `Rational`, `Round`, and mixed numeric operations keep their behavior.

- `<ToExact><Dependency path="/payment" /></ToExact>` converts a Dollar value to an exact
  fraction in dollar units. No floating-point conversion or intermediate rounding occurs.
- `<ExactRational>3/10</ExactRational>` creates a normalized fraction. The denominator must
  be nonzero. A negative denominator is normalized to a positive denominator.
- `Add`, `Subtract`, `Multiply`, `Divide`, `LesserOf`, `GreaterOf`, all four ordered comparisons,
  and `CollectionSum` accept homogeneous ExactRational operands.
  Existing `Equal`, `NotEqual`, `Switch`, `Dependency`, `Placeholder`, and `IsComplete` work
  through their generic type-preserving paths. Mixed ExactRational/Dollar operands are rejected;
  conversion must be explicit. Collections keep the existing completeness semantics.
- `<RoundExact>...</RoundExact>` converts an exact amount directly to whole-dollar Dollar
  using HALF_UP: a half-dollar tie rounds away from zero. It never rounds to cents first.
  Keep all arithmetic, aggregate sums, threshold comparisons, and limits exact until the final
  output boundary. Independently printed lines may each need their own conversion.
- Division by zero throws ArithmeticException, as existing Rational division does. Missing
  operands remain Incomplete and placeholder operands remain Placeholder. Invalid literal
  denominators and wrong arity/types fail explicitly.

For example, a shared monetary limit remains exact until its output boundary:

```xml
<RoundExact>
  <Divide>
    <Dividend>
      <Multiply>
        <ToExact><Dependency path="/limit" /></ToExact>
        <ToExact><Dependency path="/ownPayment" /></ToExact>
      </Multiply>
    </Dividend>
    <Divisors>
      <Add>
        <ToExact><Dependency path="/ownPayment" /></ToExact>
        <ToExact><Dependency path="/othersPayment" /></ToExact>
      </Add>
    </Divisors>
  </Divide>
</RoundExact>
```

This type deliberately has no fixed numerator/denominator width. Summing fractions with
several coprime payment denominators can exceed 64 bits even when each payment is small.
The shared JVM/Scala.js regression suite covers this case, signs, ties, subcent comparisons,
large money values, collection aggregation, missing operands, type errors, and legacy behavior.

Collection `Minimum` and `Maximum` are intentionally not extended to this type.
Their inherited implementation throws when the first member is incomplete and a later
member is complete. Use the exact scalar `LesserOf`/`GreaterOf` operators for caps.
