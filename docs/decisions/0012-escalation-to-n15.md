# ADR 0012: Escalation to N=15 — resolve borderline from ADR 0011

## Status

**Proposed (pre-registered, not yet executed).** This document locks the
methodology for ten additional training runs against the revised
buffer-full criterion — extending the existing five main-run seeds to
N=15 — **before** any new training is started. The training itself is
a separate step executed only after Eirik has approved this pre-
registration. Stub-writing does NOT trigger compute.

Same discipline as ADR 0010 step 2 pre-reg and ADR 0011: lock the
sample size, the criterion threshold, the validity-gate, and the
falsification structure **before** the data exists, so the result is
read against a frozen criterion rather than tuned against the data.

## Context

ADR 0010 fyrte F3 (M = 2/5 mot låst kriterium med buffer-støyet
ep_init-vindu, climb-vindu-konfunder dokumentert i resolusjonen).

ADR 0011 reanalyserte mot et **buffer-fullt** ep_init-vindu, gate PASS
(T/σ_diff = 2.7257), M' = 3/5. Det er **borderline** per pre-reg §4 —
0011 lukket eksplisitt inconclusive på N=5 reanalysis-budget. Tre av
fem seeds flippet CTS-status mellom de to vinduene (seed 6, 8 ✗→✓;
seed 10 ✓→✗), så konfunderen er reell og direksjons-symmetrisk: den
både skjulte CTS og fabrikkerte CTS avhengig av hvor [100,150]-buffer-
støyen tilfeldigvis landet per seed.

0011s resolusjon §"What 0011 opens up" anerkjente to gjenstående
muligheter ved N=5:
1. Fenomenet er robust men ble mismålt av 0010 (climb-vindu-artefakt
   bare delvis fanget av reanalysen — M' = 3/5 underestimerer en sann
   M ≥ 4/5 ved tilfeldig N=5-utvalg).
2. Fenomenet er genuint borderline — climb-then-slide skjer omtrent
   halvparten av tiden, seed-avhengig, uten skjult struktur.

ADR 0012s spørsmål: **resolverer en større prøve disse to mulighetene?**
Krever ny trening (N>5 nye seeds), ikke reanalyse — det er den
tunge-compute-grenen 0011 ikke kunne ta innenfor sin budsjett-frie scope.

**Pre-conditions verified (2026-06-05, before this stub is written):**
Alle fem eksisterende hovedrunde-`metrics.jsonl` + `agent.pt` +
`best_so_far.pt` for seeds {6,7,8,9,10} ligger på
`~/chatcat-rl-runs/`. Deres climb-vurdering mot det reviderte vinduet er
allerede gjort i 0011-resolusjonen. De gjenbrukes som 5 av N=15; kun
10 nye seeds krever ny trening.

## Pre-commitment — det stubben låser FØR ny trening

### 1. Sample-størrelse og seed-sett

**N = 15 totalt.** Eksisterende fem hovedrunde-seeds (`{6, 7, 8, 9, 10}`)
gjenbrukes — deres CTS'-vurdering mot det reviderte buffer-fulle
vinduet er allerede målt i 0011-resolusjonen (3/5 CTS': seeds 6, 8, 9
✓; seeds 7, 10 ✗). De teller som 5 datapunkter mot N=15-tellingen.
Bare 10 nye seeds krever ny trening.

**10 nye seed-verdier: `{11, 12, 13, 14, 15, 16, 17, 18, 19, 20}`.**

**Disjunkthet (verifisert ved stub-skriving):**
- `{11..20} ∩ {6..10} = ∅` (hovedrunde-seeds)
- `{11..20} ∩ {12345} = ∅` (forankrings-seed)
- `{11..20} ∩ {1} = ∅` (ADR 0008-historikkens single brukte seed-verdi)

Alle ti nye seeds er derfor utfalls-blinde ved konstruksjon; ingen
overlapper med en kjent prior-kjøring som kunne gjøre én av dem
ikke-uavhengig. Samme disiplin som ADR 0010-amendmentet (`6f838e9`).

**Begrunnelse for N=15 (ikke 10, ikke 20):** en borderline på 3/5
trenger en prøve stor nok til at de tre utfall-båndene som låses i §4
er statistisk meningsfulle og separerte. N=15 gir terskler 11/15
(≥ ~0.73, klar majoritet) og 6/15 (≤ 0.4, klar minoritet) med et
4-utfall midtbånd 7/15–10/15 som er en ekte forskjellig avgjørelse
heller enn et målglipp på en av majoritets-/minoritets-grensene.
Mindre N (f.eks. 10) ville gitt tett-spaced terskler uten skikkelig
midtbånd; større N (f.eks. 20) ville krevd mer compute uten klart
større oppløsnings-gevinst på det tre-veis utfallet.

Hvis Eirik velger annen N basert på compute-begrensninger, revider
denne stubben FØR kjøring, ikke etter. Ny pre-registrering, ny commit.

### 2. Frosne størrelser — alt fra 0010/0011 holdt fast

- **T = 0.0922** (locked since 0140536 / ADR 0010 Precision 3).
- **K = 0.004986** (locked since 0140536 / ADR 0010 Precision 2).
- **`vloss_peak` = median over peak-vindu `[peak−25, peak+25]`** (locked
  in `0010-step2-preregistration.md` Precision 2 / §3).
- **`ep_init` window = revised buffer-full window from ADR 0011 §1**:
  first 51 updates with `ep_return_n_recent ≥ 100` per seed. **IKKE**
  the original [100, 150] from ADR 0010 §1. The 0011 reanalysis
  demonstrated that the revised window passes the kriterie-validitet-
  gate; using the original window for the new seeds would re-introduce
  the noise-dominated climb-leg ADR 0010 documented and 0011 reanalysed
  past.
- **`ep_peak`, `ep_final` windows** unchanged (`[peak−25, peak+25]` and
  `[N−50, N]` respectively, per ADR 0010 §1).
- **Training config identical to main run:** baseline-normalised reward,
  `Box(7,)` action space, `ppo_continuous_action`, `ent_coef = 0.0`,
  `total_timesteps = 5_000_000`, `LR = 3e-4`, full instrumentation
  (`actor_logstd` per update, checkpoint-on-best, `expanduser` on
  `--output-dir`) per commit `cd5def3`.
- **Persistent path:** `~/chatcat-rl-runs/` per ADR 0010 Step 1.5
  decision. The /tmp wipe lesson is operationalised; no run writes
  to /tmp.

### 3. Kriterie-validitet-gate på de 10 NYE seeds (locked BEFORE climb-readout)

Same gate as ADR 0011 §3, run on the new seeds' `metrics.jsonl` files
after they are produced and before any climb-readout is performed.

**Measurement (pre-registered, computed BEFORE climb-readout):**

1. Per new seed (`{11..20}`): compute inter-update-SD of
   `ep_return_mean_recent` over the first 51 updates with
   `ep_return_n_recent ≥ 100`.
2. Compute the median of those ten per-seed SDs, denoted
   `σ_init_revised_new`.
3. Compute `σ_diff_new = σ_init_revised_new × √2`.
4. Compute the ratio `T / σ_diff_new`.

**Gate decision (locked before measurement):**

- **PASS** if `T / σ_diff_new ≥ ~2`. The new seeds have a noise-scale
  consistent with the hovedrundens fem, and climb-readout against the
  revised window is valid for all fifteen seeds. Proceed.

- **FAIL** if `T / σ_diff_new < ~2`. The new seeds have a meaningfully
  different noise-scale than the hovedrundens fem despite identical
  configuration. **STOP**. Do not proceed to climb-readout. Report
  the gate-failure, the measured `σ_init_revised_new`, and the ratio.
  This would be an unexpected finding (same config should produce
  same noise-scale) and warrants investigation before climb-readout —
  not a patch to the climb-definition in 0012.

The gate is computed only on the 10 new seeds, not on all 15 combined.
The hovedrundens fem already passed the gate in 0011-resolution (median
over five = 0.023918; T/σ_diff = 2.7257). Re-mixing them into the new
gate computation would conflate the two questions: "are the new seeds
consistent with the prior measurement?" (this gate) versus "does the
combined population pass?" (post-hoc rationalisation). Keep them
separate.

If both gates pass independently (0011's on the original five and
0012's on the new ten), the combined N=15 climb-readout is valid by
construction.

### 4. Pre-registrert tre-veis suksesskriterium (locked BEFORE training)

`M''` = number of seeds among the 15 that reproduce climb-then-slide
against the revised window: `climb ≥ T = 0.0922` AND `slide ≥ T =
0.0922`.

For the five existing seeds, `M''` includes ADR 0011's already-measured
CTS' status: seeds 6, 8, 9 contribute ✓; seeds 7, 10 contribute ✗.
For the ten new seeds, CTS'' is measured per §1's window definition
after the gate (§3) passes.

**Three-way outcome (verbatim, locked):**

- **M'' ≥ 11/15** (≥ ~0.73): **fenomenet er robust**. Borderline
  resolved upward; ADR 0011's "robust-men-mismålt"-mulighet bekreftet.
  Framing (2) (strukturelt funn med publisering i sikte) **gjenopprettet**.
  ADR 0010s F3-fyring står som historisk record (kriteriet fyrte
  ærlig mot det den ble pekt mot), men dens fenomen-implikasjon er
  endelig revidert: fenomenet var robust hele tiden, ADR 0010s
  amplitude-kriterium var måleteknisk svakt på climb-leddet i [100,150].

- **M'' ≤ 6/15** (≤ 0.4): **fenomenet er IKKE robust**. Borderline
  resolved downward; selv mot et buffer-fullt vindu reproduserer
  climb-then-slide på færre enn 40 % av seedene over større prøve.
  ADR 0010s F3-konklusjon holder uavhengig av climb-vindu-konfunderen
  på større prøve. Framing (2) **permanent retractert**. Preprint
  pivoter til "what determines whether this slide occurs" som ADR 0010
  resolution antydet.

- **M'' = 7, 8, 9, eller 10 av 15** (~0.47 til ~0.67): **fenomenet er
  intrinsisk seed-variabelt**. Borderline består på N=15 — det er ikke
  en sample-size-mangel som mer compute kan løse, det ER fenomenets
  natur. Climb-then-slide skjer omtrent halvparten av tiden, seed-
  avhengig, uten skjult struktur som N=15 kan oppløse.

**Midtbåndet er et ekte funn, ikke en feilet test.** This is pre-
registered now, before any training, specifically to prevent post-hoc
spinning of an inconvenient ~50% outcome as "needs more compute". A
phenomenon that reliably reproduces approximately half the time is a
genuinely informative result about the training dynamics — different
in kind from "robust" or "not robust", and worth reporting as its own
category. The midtbåndet outcome closes the phenomenon-question as
"intrinsically seed-variable", not as "uavklart pending ADR 0013".

The borders (11/15 and 6/15) are integer-anchored to ~0.73 and 0.4
respectively. The asymmetry around 50% (5 outcomes above the 11/15
robust border vs. 7 outcomes below the 6/15 not-robust border vs. 4
outcomes in the midtbånd) is structural: the asymmetry exists because
N=15 has a slight up-skew at integer divides, and pre-registering the
exact integer thresholds is more useful than insisting on round
percentages.

### 5. SIG-EXPLORATION på CTS''-reproduserende seeds

Read identically to ADR 0010 §3 / ADR 0011 §5, on the subset of seeds
that reproduce climb-then-slide against the revised window:

- `logstd_drift_peak = mean(actor_logstd[peak_window]) −
  mean(actor_logstd[ep_init_revised_window])` per seed.
- `vloss_peak = median(value_loss[peak_window])` per seed.

**SIG-EXPLORATION holds iff BOTH:**
- `logstd_drift_peak ≥ −0.14`
- `vloss_peak ≤ K = 0.004986`

F1/F2 forventes inaktive (consistent with ADR 0010's main run and ADR
0011's reanalysis — both found 0/CTS'-qualified seeds firing F1 or F2;
hovedrundens 5 + 0011s reanalyse = 5 of 5 CTS'-qualified seeds passed
SIG-EXPLORATION on both legs). If on the new ten seeds, F1 or F2 starts
firing on CTS''-qualified seeds, that is a substantive new finding —
the mechanism diagnosis from `31c363e` would no longer hold uniformly,
and ADR 0012 resolution would document it as a mechanism-level finding
on top of the M''-bucketing.

F1/F2 fyring reported per Precision 1 denominator convention (half-up
over CTS''-qualified seeds).

## Disiplin (0006/0010/0011-mønster)

- Pre-registrer N + tre-veis kriterium + gate + falsifisering FØR
  trening. This stub is committed before any new training is started.
- Training itself is a separate step executed only after Eirik has
  approved this pre-registration. Execution will produce
  `0012-resolution.md` parallel to ADR 0010 / 0011's stub-resolution
  structure.
- All measurements (gate σ, climb-readout, M'', SIG-EXPLORATION)
  are read mechanically from the new ten seeds' `metrics.jsonl`
  files + the existing five from `~/chatcat-rl-runs/`. No threshold
  is re-tuned post-hoc.
- The three-way outcome is genuine — particularly the midtbånd outcome
  is pre-committed as a real finding, not as a deferred decision.
- Negative result (M'' ≤ 6/15) and midtbånd result (7–10/15) are both
  real answers, equal in publishability to the robust result.

## Out of scope for ADR 0012

- **No new pre-registration of T or K.** Both held fixed from ADR 0010.
- **No new pre-registration of ep_init-window.** Held fixed from ADR
  0011 (the revised buffer-full window). The decision to use the
  revised window is taken in this stub by reference to 0011, not
  re-litigated.
- **No further escalation pre-registered here.** If somehow the N=15
  result is itself ambiguous in a way the three-way outcome does not
  cover (e.g., gate FAIL on new seeds, or a methodology problem
  discovered during training), the response is a separate ADR with
  its own pre-registration, not a fallback in this stub.
- **No candidate-fix selection.** Same scope discipline as 0010 / 0011.
- **No edits to ADR 0010, 0011, or the stub of 0012 itself.** Their
  text stays as it is; the resolution of 0012 will live in
  `0012-resolution.md`.

## Compute commitment

10 new seeds × ~33 min per seed = **~5.5 hours total compute**. Run
sequentially via the same loop pattern as ADR 0010's main run; each
seed produces its own `metrics.jsonl` + `agent.pt` + `best_so_far.pt`
under `~/chatcat-rl-runs/phase2_main__seed{N}__<ts>/` (same naming
convention as the existing five — `phase2_main` exp-name preserves
the index-friendly clustering).

The compute commitment is documented here so the cost is on-paper
before kjøring; the actual run is a separate step requiring Eirik's
go-ahead.

## Gate (resolution of this ADR)

ADR 0012 is **resolved** when:

1. The ten new seeds' training runs have completed and their
   `metrics.jsonl` + `agent.pt` + `best_so_far.pt` artefacts are on
   disk at `~/chatcat-rl-runs/`.
2. The kriterie-validitet-gate (§3) has been measured against the ten
   new seeds and PASS/FAIL has been recorded.
3. If PASS: M'' has been tallied across all 15 seeds against the
   revised window per §1, the appropriate branch of §4 has been
   reported, and SIG-EXPLORATION readings on CTS''-qualified seeds
   have been recorded.
4. If FAIL: the resolution document records the gate-failure, the
   measured σ_init_revised_new and T/σ_diff_new, and the explicit
   non-decision. No climb-readout is performed in this case.

Either PASS-with-M''-reported or FAIL-with-gate-stoppage is a
resolution. The pre-registration is honoured by both outcomes.
