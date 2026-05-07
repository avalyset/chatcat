# ADR 0003: Habituation rate values are placeholders pending real-cat data

## Status
Accepted (limitation, v0.1 onward until v0.4)

## Context
SimCat archetypes carry habituation_rate values in the range 0.005–0.015 per
tick. These values control how quickly engagement probability decays over a
session and were chosen by the v0.1 implementer as plausible defaults.

Ellis et al. 2008 ("Influence of visual stimulation on the behaviour of cats",
Applied Animal Behaviour Science 113:166–174) reports that attention to TV
monitors falls significantly across 3 hours of daily presentation, but does not
provide quantitative per-tick decay rates applicable to a 10 Hz simulator.
Hirskyj-Douglas & Webber on novelty effect in ACI documents the phenomenon but
not in our simulator's units.

The honest position is: v0.1 habituation values are reasonable placeholders,
not derived constants.

## Decision
Document this transparently. Do not pretend the values are empirically derived.
Treat habituation calibration as an open research question to be addressed in
v0.4 (real-cat phase) using session-duration distributions from actual chatcat
usage compared against simulator-predicted distributions.

## Consequences

- v0.1 README and CITATIONS.md must note that habituation rates are
  placeholders.

- The simcat-v0.1 model card adds a "Limitations" section listing habituation
  calibration as known unmet requirement.

- When real-cat sessions become available, fit habituation_rate per archetype
  against observed engagement-decay curves. Report as a follow-up ADR.

- Until then, do not draw conclusions about long-session dynamics from
  litterbox simulations. Short-session behaviour (under 5 minutes simulated)
  is more trustworthy.

## References

- Ellis, S. L. H., Wells, D. L. (2008). The influence of visual stimulation
  on the behaviour of cats housed in a rescue shelter. Applied Animal Behaviour
  Science, 113, 166–174.
- Hirskyj-Douglas, I., Webber, S. (2020). Reflecting on Methods in ACI:
  Novelty Effect and Habituation. Proc. Eight Intl. Conf. on Animal-Computer
  Interaction.
