# ADR 0001: Litterbox first

## Status
Accepted

## Context
We are building an ACI system that will eventually interact with real cats.
The question is whether to start with real-cat sensing or with simulation.

## Decision
Build the Litterbox (ethological simulator) first. Test all agent policies
against SimCat before any real cat is involved.

## Rationale
- Ethics-first: untested policies should never reach a real animal.
- Cat Royale (CHI 2024) demonstrated that simulation and careful policy
  design precede effective real-world ACI systems.
- The simulator lets us validate the ethics monitor, stress thresholds,
  and opt-out detection before the cost of getting it wrong is borne by
  a cat.
- Faster iteration: simulation runs at 100x speed.

## Consequences
- v0.1 delivers no real-cat interaction. This is a feature, not a limitation.
- All behaviour parameters must be cited from literature, since we cannot
  yet validate against our own observational data.
- The simulator's fidelity is bounded by published ethology. We will document
  known gaps in the model card.
