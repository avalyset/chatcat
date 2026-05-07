# Ethics

This document operationalises the four principles from Mancini & Nannoni
(2023) as concrete policies in the chatcat system.

## Foundation

Clara Mancini's Animal-Computer Interaction (ACI) framework positions animals
as legitimate users of technology, not as subjects or props. The four
principles below, drawn from Mancini & Nannoni (2023, "Ethical Frameworks for
ACI"), govern every design decision in chatcat.

Cat Royale (Blast Theory, Mancini, Mills, University of Nottingham; CHI 2024
Best Paper) demonstrated that ACI systems can be built with genuine ethical
rigour. We follow their precedent.

## The Four Principles

### 1. Relevance

> Every feature must answer: "Is this relevant for the cat?"

**In chatcat:**
- The action space contains only signals with empirical evidence of cat
  perception: slow blink (Humphrey et al. 2020), trill, soft purr, side
  glance, pause.
- The agent's visual form uses cat-vision dichromatic palette (S-cone 460nm,
  ML-cone 556nm, neutral point 505nm) rather than human-aesthetic colours.
- No prey-mimicry actions are included in v0. The risk of Laser Pointer
  Syndrome (frustration from uncatchable prey; see Dial-A-Vet consensus
  literature) means prey-shaped stimuli require closed-loop reward validation
  before inclusion.
- Habituation tracking (Ellis et al. 2008) ensures the system does not
  mistake declining engagement for a signal to escalate.

### 2. Impartiality

> No commercial pressure overrides cat welfare.

**In chatcat:**
- The ethics monitor is a separate module that the agent cannot bypass or
  configure. Its thresholds are hard-coded, not tuneable via settings.
- There are no engagement metrics, no "session length" KPIs, no features
  designed to maximise time-on-screen.
- The daily session cap (30 minutes per cat per simulated day) exists because
  cats are crepuscular and have limited attention budgets, not because it is a
  "feature".
- This repository will never contain A/B tests optimised for human engagement
  with cat interaction.

### 3. Welfare

> Measurable positive welfare, not just absence of suffering.

**In chatcat:**
- The Cat Stress Score (Kessler & Turner 1997) provides a validated 7-point
  scale. The system tracks CSS trajectory, not just instantaneous values.
- Hard thresholds:
  - CSS >= 5 for two consecutive ticks: agent must pause for 30 seconds.
  - CSS >= 6: agent enters cooldown for 60 minutes (sim time).
  - CSS >= 6 in two consecutive sessions: session locked for 24 hours (sim
    time).
- Time-in-stress vs. time-in-engagement ratio is logged per session. An
  ethical system produces sessions where engagement dominates.
- Pain ethogram behaviours (Marangoni et al. 2023) are encoded so the
  simulator can model scenarios the agent must recognise and respond to by
  withdrawing.

### 4. Consent

> Contingent, withdrawal-based, monitored continuously.

**In chatcat:**
- Consent is modelled as continuous, not binary. A cat entering the arena is
  not consenting to the entire session.
- LEAVING and RETREATING states are treated as withdrawal of consent. The
  agent's action space is immediately constrained (side_glance + soft_purr
  only, intensity capped at 0.3).
- The opt-out counter is prominently displayed on the dashboard. High opt-out
  counts across sessions indicate a policy failure, not a cat failure.
- Abuse detection: the system models "force-feeding" scenarios (where an
  external actor prevents the cat from leaving) and locks down when detected.
  In the litterbox this is simulated; in future real-cat systems it would
  trigger alerts.
- The agent never initiates contact when the SimCat is ABSENT. The cat must
  enter the interaction space voluntarily.

## Prey-mimicry policy

Prey-mimicry (laser dots, moving prey shapes, erratic motion patterns) is
explicitly excluded from v0. Inclusion in future versions requires:

1. Published evidence of closed-loop reward (the cat can "catch" something).
2. CSS monitoring showing no sustained stress increase.
3. Habituation curve analysis showing the interaction does not become
   compulsive.
4. External welfare review.

This is documented here because the most commercially obvious "cat app" feature
is exactly the one most likely to cause harm.

## External review

Any person may open an issue on this repository raising a welfare concern. Such
issues receive the `ethics-required-review` label and must be addressed before
any release.

## References

- Mancini, C. & Nannoni, E. (2023). Ethical Frameworks for ACI.
- Kessler, M. R. & Turner, D. C. (1997). Stress and Adaptation of Cats
  (Felis silvestris catus) Housed Singly, in Pairs and in Groups in Boarding
  Catteries. Animal Welfare, 6, 243-254.
- Humphrey, T., Proops, L., Forman, J., Spooner, R., & McComb, K. (2020).
  The Role of Cat Eye Narrowing Movements in Cat-Human Communication.
  Scientific Reports, 10, 16503.
- Marangoni, A. et al. (2023). PLOS ONE, 18(9), e0292224.
- Ellis, S. L. H. et al. (2008). The influence of body region, handler
  familiarity and order of region handled on the domestic cat's response to
  being stroked. Applied Animal Behaviour Science.
- Blast Theory, Mancini, C., Mills, D. S., University of Nottingham (2024).
  Cat Royale. CHI 2024 Best Paper.
