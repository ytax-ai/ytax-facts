# Interpretation and verification tags

Two kinds of status tag appear as XML comments on a `Fact` in this dictionary. Every other note
about a rule is in the fact's `Description`.

## `interpretation:<status>`: a choice between readings of the law

Some rules admit more than one defensible reading of the law. Where the dictionary picked one,
the fact carries an `interpretation:` tag. Its text states the reading chosen, the alternative
not taken, and the authority for the choice.

| status | meaning |
|---|---|
| `interpretation:provisional` | The authors chose this reading; no one else has signed it off yet. |
| `interpretation:operator-ratified` | The project owner signed off on this reading. |
| `interpretation:delegated-ratified` | A reviewer acting on the project owner's delegation signed off on this reading. |

The two ratified statuses are kept separate so that a reader can always tell who approved a reading.

## `verified:<level>`: the evidence behind a fact's numbers

| level | meaning |
|---|---|
| `verified:ai-only` | The numbers are checked only by the authors' own tests. No independent example confirms them. |
| `verified:worksheet-verified` | The dictionary reproduces, to the cent, a worked example the IRS published. |
| `verified:oracle-verified` | An independently built tax calculator computes the same result, to the cent. |
| `verified:cleanroom-verified` | A separate implementation, written from the published sources without this dictionary, computes the same result. |

An interpretation status says which reading of the law a fact follows. A verification level says what
evidence backs its arithmetic. A fact can carry both.
