# Theoretical Foundations for Cross-Species Attentional Communication

**Status:** Working draft. Position paper, not architectural decision.
**Date:** 2026-05-08

This document sketches the theoretical scaffolding behind chatcat's
design choices. It is not a citation of authority — it is an attempt
to articulate why the specific actions in ChatCatAgent's space
(slow-blink, trill, soft-purr, side-glance, pause) are not arbitrary,
and why "communication with cats" is a coherent design goal rather
than anthropomorphic projection.

The framing draws on three converging research traditions: embodied
cognition, joint attention theory, and Mancini's multispecies design
framework. None of these were developed for cat-AI interaction
specifically. Their convergence on chatcat's action space is the
argument.

---

## 1. Embodied cognition: signals as shared body states

The dominant tradition in 20th-century linguistics treated language
as symbol manipulation — abstract tokens that refer to meanings
through convention. Pulvermüller's work (2005, *Brain and Language*;
2018, *Nature Reviews Neuroscience*) and Friederici's neurolinguistic
research (2017, *The Neural Basis of Language*) propose an alternative:
language understanding recruits sensorimotor cortex. Hearing "kick a
ball" activates motor circuits for the foot. Meaning is grounded in
shared embodied states between speaker and listener.

If this is correct for human language, it is a fortiori correct for
cross-species communication. We share no symbolic conventions with
cats. What we can share is body states: relaxed musculature,
oriented attention, modulated breathing, gaze direction.

This is why slow-blink works. Humphrey, Proops, Forman, Spooner &
McComb (2020, *Scientific Reports*) demonstrated that cats reciprocate
slow eye-narrowing from humans they have never previously interacted
with. There is no learned convention here — slow-blink is reciprocated
because relaxed eye musculature signals non-threat as a body state
that the cat's mirror system recognises directly.

The implication for chatcat: agent actions should be embodied
signals, not symbolic ones. The action space (slow_blink, trill,
soft_purr, side_glance, pause) consists entirely of states a cat can
read as body configuration, not as message content. We are not building
a translator. We are building an interlocutor whose body the cat can
read.

## 2. Joint attention: communication requires shared attentional frame

Tomasello's work on the origins of human cognition (2008, *Origins of
Human Communication*; 2014, *A Natural History of Human Thinking*)
identifies joint attention as a precondition for communication. Two
agents communicate only when they are mutually attending — both to
each other and to a shared third object or topic. Without this triadic
structure, signals are transmitted but not received as communication.

This is empirically grounded in human infant development (joint
attention emerges around 9-12 months and predicts language
acquisition) and in primate cognition research. It is also implicit
in cat-human interaction: a cat that is sleeping, hunting, or
absorbed in territorial display is not in a state where slow-blink
can be received as social signal.

ChatCatAgent v0 enforces this implicitly. The policy permits no
action when SimCat is ABSENT, and reduces intensity when SimCat is
RESTING. Slow-blink is reserved for ALERT and CURIOUS states — the
attentional configurations where the cat could plausibly receive the
signal as directed at it.

This is sometimes summarised in the design as "the cat must be
present for the conversation to occur." The principle is not novel
to chatcat. It is the cross-species version of a constraint Tomasello
identifies as fundamental to human communication.

A related tradition — older, less academically respectable, but
operationally adjacent — is Gurdjieff's notion of "presence as
precondition." Communication between two agents only carries
information when both are in attentional states capable of registering
it. Gurdjieff is not citable in ACI literature, but the underlying
observation is reproduced in Tomasello's framework and in modern
attention research (Posner 1980, *Quarterly Journal of Experimental
Psychology*). chatcat's policy structure operationalises it.

## 3. Multispecies design: the environment is part of the message

Mancini's framing of Animal-Computer Interaction (2011, *Animal-
Computer Interaction: A Manifesto*; 2017, *International Journal of
Human-Computer Studies*) reframes the design problem. The dominant
HCI assumption — that the system is the artefact and the human is
the user — fails when the user is non-human. The artefact must
include the environment, the affordances, the withdrawal options.

Cat Royale (Schneiders et al. 2024, *CHI 2024*; Benford et al. 2024,
*CHI 2024*) operationalises this for cats specifically. The "robot
that played with cats" was inseparable from the enclosure designed
to let cats approach or retreat at will. Removing the enclosure does
not give you "the same robot in a different environment" — it gives
you a different system entirely.

For chatcat: the litterbox simulator is not just a testbed for the
agent. It is an environment in which the agent and the cat are
co-defined. The ethics monitor, the session caps, the opt-out
detection, the cooldown logic — these are not constraints on the
agent. They are part of the agent's substance.

This frames chatcat's failure modes correctly. A "good" cat-directed
AI is not one that maximises engagement minutes. It is one that
participates in a multispecies environment where the cat's withdrawal
remains meaningful at all times. An agent that gets the cat to engage
longer by removing exit affordances has not improved — it has
violated the design.

## 4. Historical precedent worth knowing, not citing

John C. Lilly's dolphin work (1958-1968, *Man and Dolphin*; *The Mind
of the Dolphin*) is the best-known historical attempt at cross-species
communication research. The early phases included serious neuroanatomy
(dolphin brain volume, neocortical development) that is still cited.
The later phases — including the Margaret Howe Lovatt experiment, LSD
administration to dolphins, and the disregard for what would now be
called consent and welfare frameworks — became a cautionary precedent
in animal research ethics.

Lilly's foundational intuition — that we must make ourselves available
to the animal on its terms, in its environment, at its tempo — is
also the foundational intuition of Mancini's ACI framework. The
difference is fifty years of welfare science, ethics review, and
institutional learning about what "on its terms" requires
operationally.

chatcat is not citing Lilly. But chatcat exists in part because
Lilly's failure mode is well-documented enough to design against.
The ethics monitor, the cooldown logic, the abuse-detection
architecture — these would have been heretical in 1965. They are
foundational in 2026.

## 5. Why this matters operationally

This document is not an academic paper. It is an articulation of why
chatcat's specific design choices — embodied action space,
attentional gating, environmental co-design, ethics-monitor-as-
substance — are coherent rather than arbitrary.

When future contributors, researchers, or critics ask "why slow-blink
and not symbolic display? why pause and not continuous stimulus? why
opt-out detection and not engagement maximisation?" — the answers are
in this scaffolding.

When chatcat is criticised — and it will be criticised, by both
"this is anthropomorphism" sceptics and "this is too restrictive to
be useful" pragmatists — the response is here. We are not anthropo-
morphising because we are not projecting human meaning. We are
building a body the cat can read. We are not over-restricting
because we are recognising that without environmental affordances
for withdrawal, no cross-species communication occurs at all — only
stimulation.

## 6. References

- Friederici, A. D. (2017). *The Neural Basis of Language*. MIT Press.
- Humphrey, T., Proops, L., Forman, J., Spooner, R., & McComb, K.
  (2020). The role of cat eye narrowing movements in cat-human
  communication. *Scientific Reports*, 10, 16503.
- Mancini, C. (2011). Animal-Computer Interaction: A Manifesto.
  *Interactions*, 18(4), 69-73.
- Mancini, C. (2017). Animal-Computer Interaction: An Emerging
  Research Discipline. *International Journal of Human-Computer
  Studies*, 98, 129-130.
- Posner, M. I. (1980). Orienting of attention. *Quarterly Journal
  of Experimental Psychology*, 32(1), 3-25.
- Pulvermüller, F. (2005). Brain mechanisms linking language and
  action. *Nature Reviews Neuroscience*, 6, 576-582.
- Schneiders, E., Benford, S., Chamberlain, A., Mancini, C., et al.
  (2024). Designing Multispecies Worlds for Robots, Cats, and
  Humans. *CHI 2024*.
- Tomasello, M. (2008). *Origins of Human Communication*. MIT Press.

### Acknowledged but not cited

- Lilly, J. C. (1961). *Man and Dolphin*. Doubleday. — Historical
  precedent for cross-species communication research; cautionary
  example regarding ethics, not methodological source.
- Gurdjieff, G. I., as transmitted in Ouspensky, P. D. (1949).
  *In Search of the Miraculous*. — Esoteric framework whose
  observation that "presence is precondition for communication"
  has modern empirical analogues in attention research and joint
  attention theory.