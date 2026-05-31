# chatcat-litterbox

An ethological simulator for testing Animal-Computer Interaction (ACI) agent
policies against simulated cats, before any real cat is involved.

This is an experiment, not a product. Stage 1 is simulator-only: a SimCat
modelled on published feline ethology interacts with a rule-based ChatCatAgent
inside a browser sandbox we call the Litterbox. No real cats are used at this
stage. The system is designed so that cats can always say no, and the system
listens.

Built on published ACI research, following the lineage of Cat Royale (Blast
Theory, Mancini, Mills, Nottingham; CHI Best Paper 2024, Webby Award 2024) and
grounded in Clara Mancini's Animal-Computer Interaction framework. The cat is
the primary user; the human is observer.

Stavros Ntalampiras, who provided the scientific basis for MeowTalk, told the
New York Times: "It's not pure science at this stage." That is exactly the
failure mode we are designing against. Every behaviour parameter in this
simulator traces back to a published, peer-reviewed source.

## What this is NOT

- **Not a cat translator.** We do not claim to decode cat language into human
  sentences. Vocalisation types are modelled from Schötz's Meowsic
  categorisation for simulation fidelity, not for "translation".
- **Not a substitute for veterinary care.** Stress scores are research
  instruments (Kessler & Turner 1997), not diagnostic tools.
- **Not entertainment for humans at cats' expense.** The ethics monitor
  enforces session caps, stress thresholds, and opt-out detection. It was built
  before the UI.
- **Not a finished system.** This is v0.1 of a simulator. The path from here
  to real-cat interaction requires ethics review, institutional oversight, and
  iterative validation.

## Architecture

The Litterbox contains three independent subsystems:

1. **SimCat** — A state-machine model of domestic cat behaviour, parameterised
   by Litchfield et al.'s Feline Five personality dimensions and driven by
   Kappel et al.'s ethogram. Five named archetypes provide starting points;
   continuous interpolation is supported.

2. **ChatCatAgent** — A rule-based policy (v0) that selects actions from a
   constrained action space. Hard-coded ethical safeguards prevent the agent
   from escalating when the cat signals stress or withdrawal. Learned policies
   come later; this version establishes the safety envelope.

3. **Ethics Monitor** — A separate module that the agent cannot bypass. It
   tracks CSS trajectory, opt-out events, habituation curves, and
   time-in-stress ratios. It forces agent pauses at CSS >= 5 and locks
   sessions at CSS >= 6. Hard action-level invariants — e.g., the
   retreat-state restriction (`side_glance` / `soft_purr` only, intensity
   capped at 0.3 in RETREATING/LEAVING) — are enforced in
   `EthicsMonitor.enforce()`, the gate every action path passes through
   before the simulator sees the action. All events are logged; the
   dashboard exposes everything the monitor sees. See
   [ADR 0009](docs/decisions/0009-ethics-enforcement-point.md) for the
   enforcement architecture.

## Running

```bash
pnpm install
pnpm dev        # opens the Litterbox in your browser
pnpm test       # runs ethics-regression, archetype-coverage, opt-out-detection
pnpm build      # produces a static build
```

Requires Node 20+.

## Scientific sources

See [CITATIONS.md](CITATIONS.md) for the full list of papers, DOIs, and how
each is used. Key sources: Kappel et al. 2024 (ethogram), Litchfield et al.
2017 (Feline Five), Kessler & Turner 1997 (Cat Stress Score), Humphrey et al.
2020 (slow blink), de Mouzon et al. 2022 (cat-directed speech), Schötz
(Meowsic vocalisations), Mancini & Nannoni 2023 (ACI ethics).

## Ethics

See [ETHICS.md](ETHICS.md) for how Mancini & Nannoni's four principles
(Relevance, Impartiality, Welfare, Consent) are operationalised in this
system. The ethics monitor is not optional infrastructure; it is the core
feature.

## Research direction

Architectural and methodological decisions are tracked as ADRs. See
[docs/decisions/](docs/decisions/README.md) for the full index. The v0.2+
work items are self-play RL against SimCat
([ADR 0002](docs/decisions/0002-self-play-research-track.md)) and
habituation-rate calibration against real-cat data
([ADR 0003](docs/decisions/0003-habituation-calibration.md)); the
resolved ADRs document what we found along the way — reward design in
[0007](docs/decisions/0007-reward-calibration.md) /
[0008](docs/decisions/0008-reward-baseline-normalization.md), and the
ethics-enforcement architecture in
[0009](docs/decisions/0009-ethics-enforcement-point.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
