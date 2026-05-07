# SimCat v0.1 Model Card

## Overview
SimCat is a simulated domestic cat implemented as a personality-parameterised
state machine for testing ACI agent policies in the chatcat Litterbox.

## Intended use
Testing ChatCatAgent policies before any real-cat interaction. Not a model of
any individual cat. Not validated against real behavioural data yet.

## Limitations
- State transitions are Markov-like; real cats have memory and context.
- Personality is static within a session; real cats modulate.
- Pain behaviours are encoded but not fully integrated into transition logic.
- Habituation is modelled as simple exponential decay. Habituation rate values
  (0.005–0.015) are plausible placeholders, not empirically derived constants.
  Calibration requires real-cat session data. See
  [ADR 0003](../decisions/0003-habituation-calibration.md).
- The five named archetypes are inspection presets, not a training distribution.
  Future RL training must sample from the full continuous Feline Five space. See
  [ADR 0002](../decisions/0002-self-play-research-track.md).
- Sim-to-real gap is unmeasured until v0.4 (real-cat validation phase). Do not
  treat simulator outcomes as predictions of real-cat behaviour.

## Parameters
- Personality: Feline Five (Litchfield et al. 2017)
- States: 10 (ABSENT through LEAVING)
- Tick rate: 10 Hz
- CSS: Kessler & Turner 1997, 7-point scale

## Ethical considerations
This model exists specifically so that no real cat is subjected to untested
agent policies. It is a tool for policy development, not a replacement for
real-world validation.
