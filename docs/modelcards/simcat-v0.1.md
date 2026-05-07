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
- Habituation is modelled as simple exponential decay.

## Parameters
- Personality: Feline Five (Litchfield et al. 2017)
- States: 10 (ABSENT through LEAVING)
- Tick rate: 10 Hz
- CSS: Kessler & Turner 1997, 7-point scale

## Ethical considerations
This model exists specifically so that no real cat is subjected to untested
agent policies. It is a tool for policy development, not a replacement for
real-world validation.
