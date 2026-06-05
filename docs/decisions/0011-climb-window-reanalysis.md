# ADR 0011: Climb-vindu-reanalyse — pre-registrering før reanalyse

## Status

**Proposed (pre-registered, not yet executed).** This document locks the
methodology for re-measuring climb on the existing main-run
`metrics.jsonl` artefacts (commit `0140536` / `6f838e9` decision-chain,
runs executed 2026-06-04, artefacts at `~/chatcat-rl-runs/`) **before**
the reanalysis is performed. The reanalysis itself is a separate step
executed only after Eirik has approved the pre-registration.

This is the same discipline that governed Step 1.5 of ADR 0010
(forankrings-seedens scope locked before measurement) and ADR 0006's
methodology pre-commitment. Re-measuring a frozen criterion after
seeing it fire would be post-hoc unless the reanalysis itself is
pre-registered separately. This document is that pre-registration.

## Context

ADR 0010 fyrte F3 (climb-then-slide not robust over N=5 main-run seeds:
M = 2/5 mot låst kriterium per Precision 4). The resolution document
(`0010-resolution.md`, commit `1ba60c0`) recorded F3 as the
locked-criterion outcome — undisputed, no re-counting.

The same resolution documented, side-by-side and explicitly NOT as
exculpation of F3, that the climb half of the locked criterion was
measurement-technically weak: `ep_init` was measured over the init
window `[100, 150]` per pre-reg §1, where buffer N_recent was 11–19
episodes (not 100). The ep_init-range within that window was 0.668–0.973
per seed across all five — ~7×–10× the locked climb threshold
T = 0.0922. Climb amplitude was dominated by buffer noise, not seed
property. All three non-CTS-qualifying seeds (6, 7, 8) failed on the
climb leg, not slide. Form-CTS (climbed-then-slid qualitatively) was
5/5; F4 confirmed slide-direction universal.

ADR 0010's resolution §5 left the phenomenon-question open:

> Spørsmålet "er M = 2/5 en ekte fenomen-egenskap eller et artefakt av
> climb-vindu-støyen" er **åpent** etter denne kjøringen. Det kan
> besvares budsjett-fritt: re-måle climb mot et **buffer-fullt** vindu
> på de eksisterende `metrics.jsonl`-filene. Ingen ny trening kreves,
> kun reanalyse av disk-artefakter.

That budget-free reanalysis is what ADR 0011 pre-registers.

**Artefakt-status verifisert (2026-06-05, før denne stubben skrives):**
Alle fem hovedrunde-`metrics.jsonl` ligger på `~/chatcat-rl-runs/`
(seed 6: 2441 rader, seed 7: 2441, seed 8: 2441, seed 9: 2441,
seed 10: 2441). Reanalysen er derfor faktuelt budsjett-fri — ingen
ny trening kreves, kun lesning av eksisterende disk-data.

## Pre-commitment — det stubben låser FØR reanalyse

### 1. Revidert anvendelsesvindu for `ep_init`

`ep_init` re-defineres som snittet av `ep_return_mean_recent` over
**de første 51 updates der `ep_return_n_recent ≥ 100`** for hver seed.

This is structurally defined by buffer-state (a property of the run),
not by an arbitrary update number. The window starts when the rolling-100
buffer first becomes full, ensuring that each `ep_return_mean_recent`
reading averages over 100 episodes (the buffer's design) rather than
11–19 (the original [100, 150] window's actual buffer fill).

For the existing main-run seeds, the first buffer-full update is
documented as observed-but-not-yet-used-in-measurement:

| seed | first update with `ep_return_n_recent ≥ 100` |
|---:|---:|
| 6 | 849 |
| 7 | 823 |
| 8 | 837 |
| 9 | 841 |
| 10 | 841 |

These values are read directly from `~/chatcat-rl-runs/phase2_main__seed{N}__*/metrics.jsonl`
during stub-writing (artefakt-verifikasjon, ikke utfalls-lesning) so the
window-definition can be stated concretely. The values are properties of
the runs' episode-length distributions, not properties of the climb
outcome.

`ep_peak` and `ep_final` remain **unchanged** from ADR 0010:
- `ep_peak` = mean over `[peak_update − 25, peak_update + 25]`, where
  `peak_update = argmax ep_return_mean_recent` over the eligible-peak
  region (`ep_return_n_recent ≥ 100`).
- `ep_final` = mean over `[N − 50, N]`, N = 2441 per seed.

Only `ep_init`'s application window is revised. This is the locus of
the measurement weakness documented in `0010-resolution.md` §4 — narrowing
the revision to that locus is the disciplined response.

### 2. T uendret

T = **0.0922** return-units, anchored at `M_T = 3 × inter-update-SD =
3 × 0.030737` over the late-stable window `[N−150, N−50]` of the
forankrings-seed (per ADR 0010 Precision 3, locked in commit
`0140536`).

**T is not re-derived.** Re-anchoring T against the new application
window's noise would conflate the two questions this reanalysis is
designed to separate: "is the criterion well-posed against application-
window noise?" (the validity-gate question) and "does the phenomenon
reproduce against a well-posed criterion?" (the substantive question).
Keeping T fixed and varying only the application window means a
positive reanalysis result attributes the change to the window
specifically, not to terskel-tuning.

This is the whole point of the reanalysis: distinguish whether
**the window** or **the phenomenon** failed, with the threshold held
fixed.

### 3. Kriterie-validitet-gate (NY — låst FØR climb-måling)

Before climb is re-measured, the criterion must be verified well-posed
against the noise scale of the revised application window. This is the
gate ADR 0010 missed: Precision 3's meningsfullhets-gate checked T
against the peak−end outcome span (~0.9), but not against the
application window's noise scale. Re-introducing the gate at the
correct point is the most important method-lærdom from ADR 0010 made
operational in 0011.

**Measurement (pre-registered, computed BEFORE climb-readout):**

1. Compute inter-update-SD of `ep_return_mean_recent` over the revised
   `ep_init`-window per seed (first 51 buffer-full updates per seed).
2. Compute the median of those five per-seed SDs, denoted `σ_init_revised`.
3. Compute differential noise: `σ_diff = σ_init_revised × √2` (the noise
   of the difference between two window-means under a simplifying
   independence assumption; same logic as ADR 0010 Precision 3's M_T
   derivation).
4. Compute the ratio `T / σ_diff`.

**Gate decision (locked before measurement):**

- **PASS** if `T / σ_diff ≥ ~2` (i.e., T is at least ~2 SD outside the
  differential-noise floor). Climb-leddet is then validly testable
  against the buffer-full window. Proceed to climb-readout.

- **FAIL** if `T / σ_diff < ~2`. Climb is **still noise-dominated** in
  the revised window. The reanalysis cannot then distinguish artefact
  from phenomenon, and a positive or negative climb-readout would be
  inconclusive against this question regardless of outcome. In that
  case, **STOP**. Do not proceed to climb-readout. The stub must be
  revised with a different climb-definition (e.g., wider window, or
  a different baseline construction) before reanalysis — that revision
  is itself a pre-registration decision and must be committed
  separately, not added as a fallback to this stub.

The threshold "~2" is the same prinsipp som M_T = 3 in ADR 0010
Precision 3 — not an exact statistical guarantee, but a principled
anchor that the threshold lies a meaningful number of SDs outside
the differential noise. The gate is **not** an outcome test — it is
a criterion-validity test. It checks whether the construction is
well-posed against the application-window noise, before any climb
outcome is read.

### 4. Pre-registrerte konsekvenser

Per ADR 0010 resolution §5, locked verbatim:

- **M' ≥ 4/5** mot revidert vindu → **climb-vindu-artefakt bekreftet**.
  Fenomenet ER robust; ADR 0010's amplitude-kriterium var ugyldig på
  climb-leddet specifically. Framing (2) (strukturelt funn) er delvis
  gjenopprettet: det finnes et robust fenomen å karakterisere, med
  metode-lærdommen om hvorfor den opprinnelige målingen skjulte det.
  ADR 0010's F3-fyring står (det fyrte ærlig mot et låst kriterium),
  men dens **fenomen-implikasjon** revurderes.

- **M' ≤ 2/5** mot revidert vindu → **fenomenet er IKKE robust** selv
  mot buffer-fullt vindu. ADR 0010's F3-konklusjon holder uavhengig av
  climb-vindu-konfunderen. Konfunderen var reell (alle tre 0010-feilene
  på climb, støy ~10× T) men ikke avgjørende — selv med konfunderen
  fjernet, reproduserer fenomenet ikke robust. Framing (2)
  retracteres permanent.

- **M' = 3/5** → **borderline**. Reanalysens scope er budsjett-fri
  re-måling av eksisterende fem `metrics.jsonl`. Det er ingen "kjør 5
  ekstra seeds"-utvidelse innenfor 0011s scope — det ville bryte
  budsjett-fri-rammen og kreve ny pre-registrering. **Borderline-
  utfallet lukker derfor 0011 ambigust:** climb-vindu-konfunderen er
  delvis reell men ikke avgjørende på N=5. ADR 0010s fenomen-status
  forblir åpent. En eventuell videre escalation til ny trening med
  N>5 må pre-registreres i et separat ADR (foreløpig 0012, ikke
  planlagt nå). 0011 selv lukkes med tydelig "inconclusive on N=5
  reanalysis-budget" som rapportert utfall.

### 5. SIG-EXPLORATION på CTS'-reproduserende seeds

Reads identically to ADR 0010 Precision 2 / §3, on the subset of
seeds that reproduce climb-then-slide against the revised window:

- `logstd_drift_peak = mean(actor_logstd[peak_window]) −
  mean(actor_logstd[ep_init_revised_window])` per seed.
- `vloss_peak = median(value_loss[peak_window])` per seed.

**SIG-EXPLORATION holds iff BOTH:**
- `logstd_drift_peak ≥ −0.14`
- `vloss_peak ≤ K = 0.004986`

F1/F2 forventes inaktive (samme begrunnelse som ADR 0010 §4
falsifiserings-balanse — both inactive on the 2/5 CTS-qualified seeds
in ADR 0010's main run; reanalysis on the same `metrics.jsonl` cannot
flip F1/F2 status for those two seeds since their data hasn't changed,
only ep_init's denominator window). If reanalysis admits 1, 2, or 3
additional seeds into the CTS-qualified subset (per M'-branches above),
SIG-EXPLORATION is checked on those new seeds against the same
thresholds. F1/F2 on the expanded subset are reported per Precision 1's
denominator convention (half-up over CTS'-qualified seeds).

The init-window for `logstd_drift_peak`'s init-term **also changes**
to the revised buffer-full window, for consistency with the new
`ep_init` definition. This is a pre-registered consequence of §1's
window-revision, not an independent methodology change.

## Disiplin (0006/0010-mønster)

- Pre-registration locked BEFORE reanalyse. This document is committed
  before any of the four numbered measurements (§1's window-anchor,
  §3's σ_init_revised, §3's gate decision, §4's climb-readout) are
  computed on the existing `metrics.jsonl` files.
- The reanalysis itself is a separate step, executed only after Eirik
  has approved the pre-registration. The execution will produce a
  resolution document (planned `0011-resolution.md`) parallel to ADR
  0010's three-file structure (stub / pre-reg / resolution).
- All four measurements are read from the five existing `metrics.jsonl`
  files on `~/chatcat-rl-runs/` — verified present at stub-write time
  (2026-06-05, sjekklisten over). The reanalysis is budsjett-fri only
  while those files survive on disk. If they are wiped (the `/tmp`-
  wipe lesson from ADR 0010 Step 1.5), the budsjett-fri claim fails
  and the situation must be re-evaluated.
- Negative finding (M' ≤ 2/5) is a real answer — phenomenon-ikke-robust
  is as publishable as artefakt-bekreftet. The stub does not privilege
  any of the three branches.

## Out of scope for 0011

- **No new training.** 0011 is reanalyse av eksisterende disk-artefakter
  only. Any new training (e.g., for borderline-extension or candidate-
  fix verification) requires a separate ADR with its own pre-registered
  seed-set, compute commitment, and budget.
- **No candidate-fix selection.** What to do about the phenomenon (if
  artefakt is confirmed, characterise; if non-robust is confirmed,
  pivot to "what determines whether it occurs") is downstream of 0011's
  resolution. The stub does not propose remedies.
- **No re-anchoring of T or K.** T = 0.0922 and K = 0.004986 are held
  fixed from ADR 0010 throughout 0011.
- **No editing of 0010-stub, 0010-pre-reg, or 0010-resolution.** Their
  text stays as it is. 0011 cross-references them but does not amend
  their content.

## Gate (resolution of this ADR)

ADR 0011 is **resolved** when:

1. The kriterie-validitet-gate (§3) has been measured against the
   revised window and a PASS/FAIL decision has been recorded.
2. If PASS: climb-readout against the revised window has been performed
   per §1, M' has been tallied, the appropriate branch of §4 has been
   reported, and the resolution document records the M' value, the
   per-seed climb/slide table against the revised window, and the
   SIG-EXPLORATION readings on CTS'-qualified seeds.
3. If FAIL: the resolution document records the gate-failure, the
   measured σ_init_revised and T/σ_diff ratio, and the explicit
   non-decision on the phenomenon-question. Climb-readout is **not**
   performed in this case (per §3's locked gate).

Either outcome is a resolution. The gate is genuine — not a formality.
