# ADR 0002: Self-play research track for emergent cat-communication strategies

## Status
Proposed (target: v0.2+)

## Context
Litterbox v0.1 ships with a rule-based ChatCatAgent. Rules are derived from
published ACI literature and serve as a defensible baseline. Going beyond v0.1,
two paths exist:

(a) Hand-tune the rules indefinitely
(b) Let an agent learn against SimCat via reinforcement learning

Path (b) is attractive because it parallels methodology used by Earth Species
Project (NatureLM-audio, planned synthetic vocalisations for direct
interspecies communication tests) and the broader self-play paradigm (AlphaGo
Zero, etc.). It also lets us discover communication strategies we did not
pre-specify.

The risk is reward hacking: an agent learns to exploit SimCat's imperfections
rather than communicate with cats. The simulator becomes the territory.

## Decision
Adopt self-play as the v0.2+ research track, conditional on three mandatory
safeguards:

1. **SIM-TO-REAL VALIDATION.** Every learned policy must be validated against
   real-cat sessions before being released. Gap between SimCat performance and
   real-cat performance is itself the most important metric — it tells us how
   wrong the simulator is.

2. **CONTINUOUS PERSONALITY SAMPLING.** Training samples from the entire Feline
   Five space (Litchfield et al. 2017), not only the five named archetypes.
   Archetypes are presets for inspection, not the training distribution.

3. **ETHICS-MONITOR ANCHORED TO REAL CSS.** The Cat Stress Score thresholds
   (Kessler & Turner 1997) used in v0.1 must be recalibrated against
   observational data from real cats once available, not against
   SimCat-generated CSS values.

## Consequences

- **v0.2:** introduce RL framework (PPO baseline) training agent against
  SimCat. Reward = engagement_minutes − α·max_CSS − β·opt_outs. Document
  hyperparameters openly. Compute budget estimate: $10–50.

- **v0.3:** compare emergent strategies against ACI literature. Document where
  they agree (validation), disagree (potential discovery or simulator bug), and
  contradict ethics constraints (must be hard-blocked).

- **v0.4:** real-cat validation. Requires ethics review aligned with Mancini's
  contingent-consent framework. Earliest target: month 6.

- **Publication:** this trajectory is itself a contribution. Self-play
  methodology applied to cat-directed companion AI, with explicit sim-to-real
  protocol, is publishable at ACI conference and likely at CHI.

## References

- Mancini, C. (2011). Animal-Computer Interaction: A Manifesto.
- Mancini, C., & Nannoni, E. (2023). Editorial: Animal-computer interaction
  and beyond. Frontiers in Veterinary Science.
- Earth Species Project. NatureLM-audio (2024).
- Silver et al. (2017). Mastering the game of Go without human knowledge.
  Nature.
