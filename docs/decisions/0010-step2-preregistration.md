# ADR 0010, Step 2 — Pre-registration of the instrumented re-run

> **Status: Committed (`0140536`), amended (`6f838e9`), resolved (`1ba60c0`).**
> Locks the publication-grade criterion BEFORE the new training runs
> produce data. Per 0006-discipline, editing this file after the runs
> complete would reopen the post-hoc-rationalisation door — specifically
> in the material that ends up in a preprint.
>
> The internal-milestone diagnosis (commit `31c363e`) stands as-is.
> This step adds Framing (2) — structural-finding-with-publication —
> and the publication-grade pre-registration. The resolution of ADR 0010
> waits for the new disk-permanent artefacts.

## Framing chosen: (2) — Structural finding, publication in view

Per the three framings in `0010-holding-question.md` section (a):

- Framing 1 (deployable policy) rejected: not what the project is for
  at this stage.
- **Framing 2 (structural finding) chosen.** Robust climb-then-slide
  across the three 0008 runs is the finding; ADR 0010 characterises
  *why*, with disk-permanent evidence for a preprint (arXiv target,
  month 6).
- Framing 3 (online holding required) rejected: no downstream
  requirement currently demands an online-stable trained policy.

The framing choice elevates the evidence threshold. The internal
diagnosis in `31c363e` is honest as a milestone but relies on
prior-verified numbers no longer disk-reproducible after the
`/tmp/chatcat-rl-runs/` wipe of ≈ 2026-06-02. A preprint cannot stand
on "the numbers were on disk, /tmp was wiped." Step 2 produces what
the preprint needs.

## Persistent path (instrumentation-debt fix)

All Step 2 artefacts (`metrics.jsonl`, `agent.pt`, periodic
checkpoints, the new explicit `actor_logstd` log) are written to
**`~/chatcat-rl-runs/`** — under user home, decoupled from the repo
tree, demonstrated persistent across reboots and day-boundaries on
macOS (the wiped `/tmp` is per-day-policy; `~` is not).

The path is not in `.gitignore` — it does not need to be, since it
lives outside the repo tree entirely. It survives a `rm -rf` of the
repo as well as a reboot.

**Verification before Step 2 counts as valid:** the persistence of
this path must be confirmed (i.e., the directory exists, is writable,
and has survived at least one day-boundary) before any run is treated
as the publication evidence. If a future macOS update or a manual
`rm` removes the directory, Step 2 has to restart — the
instrumentation-debt fix is part of the experiment's validity.

## Pre-registration of publication criteria (LOCKED)

These are frozen at commit time of this file. Any post-hoc edit to
the thresholds or definitions below — after the new runs have
produced data — invalidates the pre-registration and any preprint
that draws on the runs would need to retract or disclose the edit.

### 1. Peak-update-window

- **Eligible-peak region:** updates `u` with
  `ep_return_n_recent ≥ 100` (the rolling-mean buffer must be full).
- **Peak update:** `argmax_u ep_return_mean_recent[u]` over the
  eligible-peak region.
- **Peak window:** updates `[peak_update − 25, peak_update + 25]`,
  i.e., **W = 50 updates** centred on peak. All readings at "peak"
  refer to means over this window, not single-update values, to
  reduce spike sensitivity.
- **Init window:** updates `[100, 150]` — the first 50 updates after
  the buffer fills. The same width as the peak window, so init-vs-peak
  comparisons are like-for-like.
- **Final window:** updates `[N − 50, N]` for `N = total updates`
  (≈ 2441 for 5M / 2048).

Single-update extremes do not tip readings; only windowed means do.

### 2. "Climb-then-slide confirmed with publishable evidence"

Per seed, three quantities are computed from the
`ep_return_mean_recent` series:

- `ep_init = mean(ep_return_mean_recent[init_window])`
- `ep_peak = mean(ep_return_mean_recent[peak_window])`
- `ep_final = mean(ep_return_mean_recent[final_window])`

A seed **reproduces climb-then-slide** iff BOTH:

- **Climb:** `ep_peak − ep_init ≥ T`
- **Slide:** `ep_peak − ep_final ≥ T`

where T is the per-seed-comparable threshold anchored to inter-update
noise (Precision 3 below).

### Precision 3 — Climb/slide threshold T, anchored in return-scale

> `≥ 1.0` return-enheter er udefinert mot baseline-normalisert returns
> skala. Forankre i inter-update-spredning:
>
> **Climb/slide-terskel (låst):** climb og slide krever hver en endring
> på `≥ T` return-enheter, der
>
> **T = 3 × inter-update-SD av `ep_return_mean_recent` målt over den
> sen-stabile vindu-regionen `[N−150, N−50]` i forankrings-seedens
> `metrics.jsonl` (N = 2441 totale updates).**
>
> **Multiplikator-begrunnelse (prinsipiell forankring, ikke eksakt
> differanse-statistikk):** T = 3σ plasserer terskelen ~2 SD utenfor
> den støy-differansen sen-stabil noise kan produsere mellom to
> vindu-snitt, under en forenklende antakelse om at peak- og
> end-vinduene har sammenlignbar, uavhengig støy. σ er målt i
> end-vinduet alene; peak-vinduets støy er ikke uavhengig målt, og
> vindu-størrelsene er ikke garantert identiske. Dette er en
> prinsipiell forankring som motiverer størrelsesordenen 3, ikke en
> eksakt statistisk garanti. Multiplikatoren er låst FØR måling og er
> ikke valgt for å matche noen forhåndsforestilling om T-størrelse.
>
> **Vindu-begrunnelse (strukturell, ikke utfalls-valgt):** sen-stabilt
> vindu (samme som K) reflekterer noise-skalaen i det konvergerte
> systemet. Initial-vinduet [100, 150] som var foreslått i tidligere
> utkast ble forkastet fordi det viste seg å ligge i selve climb-fasen,
> så SD-en der målte klatre-dynamikk, ikke støy-gulv. Co-anchoring av
> T og K i samme sen-stabile vindu er en metodisk fordel: begge
> tersklene refererer til samme "skala av variasjon i det konvergerte
> regimet", ikke til to ulike noise-definisjoner som tilfeldigvis
> havnet ved siden av hverandre.
>
> **Meningsfullhets-gate (låst FØR måling):** hvis målt SD gir en T
> som faller utenfor `[~5 %, ~80 %]` av peak−end-spennet observert i
> forankrings-seeden (~0.9 return-enheter, kun synlig fra training-
> scriptets endelige summary-utskrift og brukt kun som
> degenerasjons-sjekk, IKKE som mål for T), STOPP og flagg før
> innfylling. Revurder M_T og/eller vindu med NY strukturell
> begrunnelse — aldri ved å justere mot ønsket utfall. Gaten finnes
> for å fange tilfellet "den valgte konstruksjonen ga en T som var
> trivielt liten eller trivielt stor"; den er ikke en utfalls-test.
> Peak−end-tallet ble eksponert utilsiktet via training-scriptets
> final-summary (best_so_far ep_return ≈ 0.05 ved update 1353; end
> ep_return ≈ −0.85 ved update 2441) før T og K var låst. Anker-
> formelen er pre-registrert (T = M_T × inter-update-SD; K = M_K ×
> vloss_stable) og avhenger ikke av disse to tallene, så lekkasjen
> påvirker ikke selve anker-utregningen — men den er dokumentert her
> for å holde fullstendig avgjørelses-trail på papir.
>
> Rapportér den målte inter-update-SD-en eksplisitt i pre-reg, og
> uttrykk T som multiplum av den (f.eks. "T = X.XX = 3 × målt SD
> Y.YY"). Slik er terskelen lesbar som signifikant-mot-støy, ikke et
> nakent absolutt på en relativ skala.
>
> **Målt (anchoring seed `--seed 12345`, `metrics.jsonl` i
> `~/chatcat-rl-runs/phase2_anchoring__seed12345__1780549182/`,
> N = 2441 updates, vindu [2291, 2391], buffer fullt N=100 gjennom hele
> vinduet):**
>
> - inter-update-SD av `ep_return_mean_recent` = **0.030737** return-enheter
> - **T = 3 × 0.030737 = 0.0922 return-enheter** (låst)
> - Meningsfullhets-gate (`[5 %, 80 %]` av ~0.9 peak−end-spenn = `[0.045, 0.720]`):
>   T = 0.0922 → PASS (10.2 % av spennet).

A **publication-grade reproduction** of the finding is:

- **N = 5 seeds, with M ≥ 4 of 5 seeds reproducing climb-then-slide
  as defined above.**

### Precision 4 — Borderline-extension stopping rule (locked)

> "M=3/5 → kjør 5 til" mangler en terskel på den utvidede prøven og en
> absolutt stopp. Lås begge:
>
> **Borderline-utvidelse (låst før kjøring):** hvis M = 3/5 (borderline),
> kjør nøyaktig 5 ekstra seeds (totalt N=10). Reproduksjon på utvidet
> prøve krever **M ≥ 7/10**. Ingen ytterligere utvidelse uansett utfall —
> N=10 er det absolutte taket for denne pre-registreringen.
>
> - **M ≥ 4/5** → publiserbar reproduksjon (CTS bekreftet, ingen utvidelse).
> - **M = 3/5** → utvid til N=10 (kjør 5 ekstra). Da:
>   - **M ≥ 7/10** → publiserbar reproduksjon (CTS bekreftet på utvidet prøve).
>   - **M ≤ 6/10** → ikke robust; F3 fyrer; framing (2) revurderes.
> - **M ≤ 2/5** → ikke robust; F3 fyrer; framing (2) revurderes.
>   Ingen utvidelse.
>
> Det finnes ingen "kjør litt til"-gren utover dette. Optional stopping
> er eksplisitt utelukket: utvidelsen skjer én gang, til en
> forhåndsbestemt størrelse, mot en forhåndsbestemt terskel.

### 3. SIG-EXPLORATION confirmation criterion at peak

Per seed, two quantities are computed at the peak window:

- `logstd_drift_peak = mean(actor_logstd[peak_window]) −
                      mean(actor_logstd[init_window])`

  (Computed directly from the new logged `actor_logstd` parameter,
  not from `entropy` as proxy. With `actor_logstd` initialised to
  zeros and `action_dim = 7`, `entropy_t = 7 · (0.5 · log(2πe) +
  mean_t(log σ))`, so `mean(actor_logstd)` per dim is exactly
  recoverable; we log it directly to remove any indirection.)

- `vloss_peak = median(value_loss[peak_window])` over the peak window
  `[peak_update − 25, peak_update + 25]` defined in §1. **Median, not
  mean**, chosen for consistency with `vloss_stable`'s definition (also
  a median) and because `value_loss` is bimodal: the anchoring seed
  showed stable median (~0.0015–0.0018 across all windows from early
  training to end) but sporadic spikes (max 2.54 at update 993; spikes
  observed throughout, not concentrated in any phase). A point reading
  at `peak_update` itself could land on either a spike or the stable
  baseline depending on accident of timing; a windowed median is
  robust to spikes and reflects the regional level of the critic.
  The mean over the same window is dragged by spikes (in the anchoring
  seed's K-window: mean = 0.0487 vs median = 0.00166, a 29× gap), so
  mean would conflate "occasional spike" with "elevated convergence
  level" — exactly what the bimodality argument disqualifies.
- `vloss_max_seed = max(value_loss)` over the seed's full training
  (kept as deskriptiv kolonne; not used in the F2 decision — see
  Precision 2).

**SIG-EXPLORATION holds for a seed iff BOTH:**

- `logstd_drift_peak ≥ −0.14` (variance not collapsed — matches the
  internal milestone's threshold).
- `vloss_peak ≤ K · vloss_stable` (critic converged at peak — see
  Precision 2 below for K and vloss_stable definitions).

### Precision 2 — F2 normalisation, anchored against converged critic

> `0.1 · vloss_max_seed` normaliserer mot seedens egen tidlige, ufittede
> maks — en svær, ustabil verdi, og 0.1× av den er en vilkårlig linje.
> Ved peak-avlesning (ikke end-state) er critic ikke nødvendigvis like
> konvergert, så F2 kan fyre på en arbitrær normaliserings-artefakt. Bytt
> til et mål som ikke avhenger av den tidlige spiken:
>
> **vloss_peak-kriterium (revidert):** critic regnes som konvergert ved
> peak hvis `vloss_peak ≤ K · vloss_stable`, der `vloss_stable` er median
> value_loss over et stabilt sent vindu `[N−150, N−50]` (etter at critic
> har satt seg, før helt slutt).
>
> **M_K = 3** (låst). **K = M_K × vloss_stable**.
>
> **Multiplikator-begrunnelse (margin over observert variasjon, ikke
> statistisk parallellitet til M_T):** forankrings-seedens
> `metrics.jsonl` viser at median `value_loss` varierer ~10 % på tvers
> av nærliggende sen-stabile vinduer (median over `[N−300, N−200]` =
> 0.001556, `[N−250, N−150]` = 0.001793, `[N−200, N−100]` = 0.001526,
> valgt `[N−150, N−50]` = 0.001662, `[N−100, N]` = 0.001669). M_K = 3
> gir romslig margin over denne ~10 % vindu-variasjonen og fyrer F2
> bare hvis `vloss_peak` er vesentlig forhøyet over sent-stabilt-nivå.
> Tallet er samme som M_T, men begrunnelsen er forskjellig: M_T = 3
> hviler på normal-fordelings-σ-statistikk for differanser; medianer
> over bimodale data har ikke samme tolkning, så paralleliteten er
> kosmetisk og kunne villedet hvis den ble lent på som primær
> begrunnelse.
>
> **Målt (anchoring seed `--seed 12345`, vindu `[N−150, N−50] =
> [2291, 2391]`, N = 2441 updates):**
>
> - `vloss_stable` = median value_loss = **0.001662**
> - **K = 3 × 0.001662 = 0.004986** (låst)
>
> Begrunnelse for ankerformen (peker tilbake på Precision 2's
> opprinnelige motivasjon): dette måler peak-value_loss mot critic-ens
> *konvergerte* nivå, ikke mot dens verste tidlige verdi. En reviewer
> kan ikke angripe nevneren som en artefakt av tidlig ufittethet.
>
> Behold `vloss_peak / vloss_max_seed` i rapporten som *deskriptiv*
> kolonne (kontinuitet med intern-diagnosens 50–200×-tall), men
> F2-avgjørelsen hviler utelukkende på `vloss_stable`-kriteriet.
>
> **Forventning til F2 (dokumentert som egenskap ved kriteriet, ikke
> ettertanke):** forankrings-seeden viser at `value_loss` har stabil
> median allerede tidlig i trening (~0.0015–0.0018 fra `[1, 50]` og
> utover) og holder seg der gjennom hele 2441-update-løpet. Hvis
> hovedrundens fem seeds oppfører seg konsistent med forankrings-seeden
> i dette henseendet, vil `vloss_peak` (median over peak-vinduet) ligge
> i samme størrelsesorden som `vloss_stable`, og F2 vil derfor
> **sannsynligvis ikke fyre**. Dette er en pre-registrert egenskap ved
> kriteriet, ikke en ettertanke: F2's rolle er å være en
> "no-confounding-by-critic-divergence"-garanti — den utelukker den
> degenererte forklaringen "peak-avlesning er meningsløs fordi
> kritikkeren ikke har konvergert dit" — ikke en aktiv del av
> CTS-funnets evidens-vekt. At F2 forventes å passere stille er
> akkurat hvordan en slik garanti skal oppføre seg når den ikke
> trigges. Hvis F2 fyrer på flere seeds, *er* det meningsfullt —
> det betyr kritikken faktisk divergerer ved peak — og det rapporteres
> som split (per Precision 1) snarere enn glattet bort.

### Precision 1 — Denominator convention for SIG-EXPLORATION and F1/F2

> **Nevner-konvensjon (låst før kjøring):** F1 og F2 leses som andel av
> de seedene som reproduserer climb-then-slide (CTS-kvalifiserte seeds),
> IKKE som andel av alle N. Begrunnelse: SIG-EXPLORATION er en påstand om
> *mekanismen bak sliden*, så den er bare meningsfull på seeds der slide
> faktisk forekom. Et seed uten slide har ingen peak-til-slide-mekanisme
> å diagnostisere.
>
> - **Publiserbar SIG-EXPLORATION:** **alle CTS-kvalifiserte seeds må
>   passere begge SIG-betingelsene** for ren bekreftelse. Hvis en
>   delmengde feiler, rapporteres det som split (se F1/F2), ikke glattet
>   bort.
> - **F1 fyrer:** `logstd_drift_peak < −0.14` på ≥ halvparten av de
>   CTS-kvalifiserte seedene (rund opp ved oddetall: 2 av 3, 3 av 5).
> - **F2 fyrer:** `vloss_peak`-kriteriet (Precision 2) feiler på ≥
>   halvparten av de CTS-kvalifiserte seedene (samme opprundings-regel).
>
> Ved borderline-utvidelse (Precision 4) reberegnes nevneren mot den
> utvidede CTS-kvalifiserte mengden, med samme halvparts-regel.

If a seed reproduces climb-then-slide but fails SIG-EXPLORATION at
peak (e.g., its `actor_logstd` collapsed, or its `value_loss` was
high at peak), report that seed as a SIG-LANDSCAPE counter-example
and discuss explicitly.

### 4. Falsification — what would topple the mechanism story

These conditions, if observed, invalidate the SIG-EXPLORATION reading.
Denominator convention per Precision 1: F1 and F2 are read against
the CTS-qualified subset (seeds that reproduced climb-then-slide),
not against all N. Each is stated affirmatively (this would falsify,
not "we hope it doesn't happen"):

- **F1 — variance collapses at peak.** `logstd_drift_peak < −0.14`
  on ≥ half of the CTS-qualified seeds (round up: 2 of 3, 3 of 5,
  4 of 7, 5 of 9; rebase against the extended CTS set on borderline
  extension). The variance-stays-wide premise of SIG-EXPLORATION
  fails. Reward-landscape interpretation is back on the table; the
  internal-milestone diagnosis was wrong about the mechanism.

- **F2 — critic non-converged at peak.** `vloss_peak > K ·
  vloss_stable` (per Precision 2) on ≥ half of the CTS-qualified
  seeds (same up-rounding rule as F1). The "reward signal is coherent
  because the critic learned it" premise weakens. SIG-LANDSCAPE's
  critic-non-converged branch lights up.

- **F3 — climb-then-slide not robust.** Reproduction rule per
  Precision 4: if `M ≤ 2` of 5 seeds reproduce, F3 fires immediately
  (no extension). If `M = 3/5`, the extension to N=10 must reach
  `M ≥ 7/10`; if it reaches only `M ≤ 6/10`, F3 fires. The
  structural-finding framing itself (Framing 2) is undermined. We
  do not have a robust phenomenon to characterise — we have a
  sometimes-phenomenon. The preprint pivots to "what determines
  whether this slide occurs" rather than "why this slide occurs",
  which is a different paper.

- **F4 — slide direction flips.** If `ep_final − ep_peak > 0` (no
  slide) on a majority of seeds — i.e., the runs hold or climb past
  peak — then the entire phenomenon we are characterising does not
  reliably exist on this instrumentation. Either the original three
  0008 runs were idiosyncratic, or the instrumentation change itself
  altered training dynamics. Either way: ADR 0010 closes negatively
  on the climb-then-slide question and the prior `31c363e` diagnosis
  is also retracted.

**Falsifiserings-balanse (dokumentert egenskap):** F1 og F2 er
mekanisme-falsifiserere og forventes begge inaktive før hovedrunden —
F1 fordi `actor_logstd`-driftens fortegn allerede utelukker
varians-kollaps (intern milepæl `31c363e`), F2 fordi forankrings-seeden
viser median value_loss stabil fra `[1, 50]` og utover. Hovedrundens
primære empiriske innsats ligger derfor i F3 og F4, som tester
REPRODUSERBARHETEN av climb-then-slide over N=5 seeds — ikke i
mekanismen, som forankrings-seeden og `31c363e` allerede understøtter.
Den ærlige framstillingen ved en eventuell publisering: forankrings-
arbeidet etablerte mekanismen; hovedrunden tester reproduserbarheten.
F1/F2 beholdes som aktive falsifiserere fordi en enkelt seed med
varians-kollaps eller forhøyet peak-region-median FORTSATT ville fyre
dem — de er forhåndsforventet inaktive, ikke deaktiverte.

### 5. What is reported regardless of outcome

A null or negative result is publishable and committed to here:

- All N seeds' full `metrics.jsonl` and final `agent.pt` artefacts,
  on persistent disk.
- Per-seed climb, slide, `logstd_drift_peak`, `vloss_peak / vloss_max`
  values in a table.
- Aggregated mean ± std across seeds for each quantity.
- Plain prose statement of which of {confirmed, F1, F2, F3, F4,
  inconclusive} the result falls into. No selective reporting.
- If F1–F4 fires, the `31c363e` internal-milestone diagnosis is
  *amended* in a follow-on commit to flag the retraction; the
  original stub is not silently rewritten.

## Step 1.5 — Anchoring seed (scale measurement, before commit)

### Why this step exists

T (climb/slide threshold) and K (critic-convergence threshold) are
thresholds in a pre-registered criterion. They cannot be anchored in
empirics that do not exist: `/tmp/chatcat-rl-runs/` was wiped, the
three 0008 runs' `metrics.jsonl` files are gone, and inter-update-SD
over [100,150] and median value_loss over [N−150, N−50] were never
reported separately — so they cannot be recovered from session reports
either. Setting T and K as guessed default values would make exactly
the mistake pre-registration exists to prevent: a threshold undefined
against the scale it operates on.

The anchoring seed produces the missing scale measurements
disk-permanent, and simultaneously validates that the instrumentation
(`actor_logstd` logging, checkpoint-on-best) and the persistent path
(`~/chatcat-rl-runs/`) actually work before the main run trusts them.

### What the anchoring seed is

One seed, full instrumentation, identical configuration to the
planned main run:

- Baseline-normalised reward, Box(7,) action space,
  `ppo_continuous_action`, `ent_coef = 0.0`, ~5M steps.
- `LR = 3e-4` (matches the main run's locked configuration).
- `actor_logstd` logged per update (direct state-independent
  parameter; not entropy as proxy).
- Checkpoint-on-best policy, plus periodic checkpoints.
- Writes to `~/chatcat-rl-runs/` (persistent path, verified to
  survive a day-boundary before measurements count).
- **A separate seed value** that is not reused for any of the N=5
  main-run seeds.

### Locked seeds (pre-registered before kjøring)

The main-run seed set is committed to this document before the main run
is started, so disjointness vs. forankrings-seeden and vs. the
0008-historikkens used seeds is a pre-registration property of the
design rather than something chosen after seeing run identifiers or
results.

**Amended (2026-06-04, before any main-run kjøring):** the main-run
seed set was originally locked at `{1, 2, 3, 4, 5}` with seed 1
explicitly chosen as the value all three ADR 0008 training runs used.
After Step 1.5 was complete but before main-run kjøring began, three
observations made that choice untenable:

1. ADR 0008's Run 2 was executed at `--seed 1` against the
   post-0009-fix env at LR=3e-4 — the exact configuration the main run
   would use. Run 2's `state_dict_sha256`, `ep_init @ update 100`,
   `ep_peak`, and `ep_final @ update 2441` are documented in
   ADR 0008's resolution. Seed 1 in the main run is therefore not
   outcome-blind: its result is partially knowable from a prior
   committed artefact.
2. Run 2's `metrics.jsonl` itself was lost when `/tmp` was wiped
   between 2026-05-31 and 2026-06-03. Disambiguation between "main-run
   seed 1 is a fresh independent observation" and "main-run seed 1
   reproduces Run 2 with possibly RNG-shifted late SHA" cannot be done
   against the full Run 2 series; only against the four documented
   fingerprint points in ADR 0008.
3. Even if disambiguation against the documented fingerprint succeeded
   ("genuinely different trajectory"), claiming seed 1 as a fresh
   replication while knowing the original Run 2 outcome is methodically
   awkward — it requires a footnote rather than being self-evidently
   clean.

Conservative resolution: swap the main-run seed set proactively to one
disjoint from both `{12345}` (forankrings-seeden) AND `{1}`
(0008-historikkens used seed value across all three runs). All N=5
seeds become outcome-blind by construction, no per-seed disclaimer is
required, and the "five genuinely new observations" claim the pre-reg
makes is uncomplicated.

This amendment is committed BEFORE the main run is started, so
pre-registration-temporal-discipline holds (locked-before-data). The
prior `{1..5}` set is preserved in git history (commit `0140536`); the
amendment supersedes it from this commit forward.

- **Main run (Step 2, amended):** N=5 seeds = `{6, 7, 8, 9, 10}`.
  Chosen as the smallest contiguous integer set above `5` that
  remains disjoint from `{1}` (0008-historikkens single used value)
  and `{12345}` (forankrings-seeden). The choice of `{6..10}` rather
  than e.g. `{100..104}` is irrelevant to determinism (every seed
  value is equally a fresh trajectory under the script's RNG seeding),
  but `{6..10}` keeps the integer-set notation compact and
  human-readable.
- **Anchoring seed (Step 1.5):** seed value = `12345` (unchanged).
- **0008-historikk:** seed value = `{1}` (the only seed value used
  across ADR 0008's three runs; preserved here as a pre-registered
  exclusion set, not as data).
- **Disjointness:** `{6, 7, 8, 9, 10} ∩ {12345} = ∅` AND
  `{6, 7, 8, 9, 10} ∩ {1} = ∅`. All five main-run seeds are
  outcome-blind by construction.

### Persistent-path verification (pre-registered decision)

Step 1.5's rule "verify day-boundary survival on `~/chatcat-rl-runs/`
before measurements count" can be satisfied two ways. The choice is
itself a pre-registered methodology decision, not an ad-hoc judgement
made after seeing the anchoring-seed output:

- **Full verification (rejected):** run anchoring seed → wait for a
  calendar-day boundary to pass → re-read `metrics.jsonl` + checkpoint
  files → confirm bit-identical contents → only then read scale
  quantities and fill T and K. This serialises the schedule across at
  least one overnight gap before pre-reg can be committed.
- **Weakened verification (chosen):** path-persistence of
  `~/chatcat-rl-runs/` is established by macOS policy
  (`~` is not subject to the per-boot `/tmp` cleanup that wiped the
  ADR 0008 artefacts; `~` survives reboot, log-out, sleep, and
  calendar-day boundaries). The anchoring seed writes to that path,
  measurements are taken from the file when training finishes, and
  the pre-reg is allowed to commit in the same session. The
  persistence claim is the same in both options; only the
  ceremony of measuring it differs.

**Chosen: weakened verification.** Rationale: the ADR 0008 artefact
loss was caused by `/tmp`'s documented per-boot wipe, not by an
unmeasured property of `~`. Treating an overnight wait as a stronger
test of persistence than reading the same file twice in one session
inflates a calendar-day delay into a methodological gain it does not
actually deliver. The persistent-path claim is the file-write actually
landing on `~/chatcat-rl-runs/` and being readable later in the same
process and on the same disk — both options measure exactly that.

If `~/chatcat-rl-runs/` for any reason fails to retain the anchoring
run's `metrics.jsonl` and checkpoint within this session
(file missing, content not the same bytes as written), STOP and
report — that would invalidate the weakened-verification premise
and require switching to full verification or to a different
persistent location.

### What it measures (and fills into the pre-reg)

- **inter-update SD of `ep_return_mean_recent` over the late-stable
  window [N−150, N−50]** → anchors T per Precision 3.
  T = M_T × measured-SD with M_T = 3 (locked, see Precision 3 for
  statistical justification). The initial-window choice [100, 150]
  appearing in earlier drafts was discarded after the anchoring seed
  showed that window sits in the climb phase itself; the late-stable
  window co-anchors T with K and reflects converged-system noise.

- **median `value_loss` over the stable late window [N−150, N−50]**
  (`vloss_stable`) → anchors K per Precision 2. K is expressed as a
  number ("K · vloss_stable with K = M_K"). M_K locked separately
  (see Precision 2).

Both T and K are measured from the same `[N−150, N−50]` window of
the same anchoring-seed `metrics.jsonl`. The window is identical;
the statistics differ (inter-update-SD for T, median for K).

**Meaningfulness-gate (locked BEFORE measurement):** if the measured
T falls outside `[~5 %, ~80 %]` of the peak−end span observed in the
anchoring seed (~0.9 return units, exposed unintentionally via the
training script's final-summary print before T and K were locked,
used here ONLY as a degeneracy-check, NOT as a target for T's value),
STOP and flag before filling. Revurder M_T and/or window with a NEW
structural justification — never by adjusting against desired outcome.
The gate catches "construction gave a trivially small or trivially
large T"; it is not an outcome-test of the trajectory.

Both measured values are reported explicitly in the pre-reg (in the
T and K placeholders of Precisions 3 and 2) before commit.

### What it does NOT do — pre-reg-critical rule

> **The anchoring seed is used exclusively for scale-anchoring of T
> and K. Its own climb/slide/SIG-EXPLORATION outcomes are NOT read,
> NOT reported, and do NOT count as one of the N=5 main-run seeds.
> It is run on a separate seed value that is not reused in the main
> run.**
>
> Rationale: scale (inter-update-SD, converged value_loss level) is
> a property of the environment and the normalisation, not of the
> outcome being tested. Anchoring thresholds in scale does not leak
> the outcome into the criterion. But if the anchoring seed were also
> allowed to count as a data point against the same thresholds it
> helped set, the criterion would be circular — the seed would have
> defined the threshold it is judged against. Therefore: read the
> scale quantities, lock T and K, and discard the seed's own
> outcome reading. Do not look at whether the anchoring seed itself
> reproduced climb-then-slide before T and K are frozen.

### Sequence (explicit)

1. Run the anchoring seed (full instrumentation, persistent path,
   separate seed value).
2. Measure inter-update-SD over [100, 150] and median value_loss
   over [N−150, N−50] from its `metrics.jsonl`. **Verify that the
   files survive a day-boundary on `~/chatcat-rl-runs/` before the
   measurements count** (persistent-path validity check).
3. Fill T and K in Precisions 3 and 2 from the measurements. Report
   the measured scale quantities explicitly in the pre-reg.
4. Pre-reg is now complete and empirically anchored → show finished
   draft to Eirik → commit (after review).
5. Step 2: main run with N=5 seeds, against the now-frozen thresholds.

### Compute commitment

The anchoring seed is heavy in the "requires compute" sense (~33 min
training plus measurement); it is NOT heavy in the "large investment"
sense (one seed). It de-risks the main run in addition to setting the
thresholds — if the persistent-path verification fails, or if
instrumentation has a bug, the anchoring seed catches it before five
seeds depend on it.

Total compute budget so far for ADR 0010: one anchoring seed
(~33 min). The main run (Step 2, locked at 5 seeds) is the next
compute commitment after the pre-reg is committed.

## Out of scope for Step 2

- **Candidate-mechanism selection.** Variance/entropy annealing
  schedules, KL anchors, target-KL early-stopping are downstream of
  Step 3's reading. Picking among them now would pre-empt the
  falsification check.
- **Reward redesign or holding-bonus terms.** Per ADR 0010's main
  Ethics flag, any holding-bonus term must clear the same
  Impartiality review as a new reward term, not be treated as
  optimisation tuning. This pre-registration does not propose any
  reward change.
- **Touching ADRs 0007 / 0008 / 0009.** They are resolved; Step 2
  re-runs do not amend them.
- **Re-running with different hyperparameters or different
  reward params.** The point is re-instrumentation of the *same*
  experiment (baseline-normalised, crossover α/β/scale, Box(7,),
  ppo_continuous_action, ent_coef=0, ~5M steps, same LR-values as
  the original three runs: 3e-4 for Runs 1+2, 1e-4 for Run 3). The
  only differences from the originals: explicit `actor_logstd`
  logging, periodic + best-checkpoint saving, persistent path, and
  N seeds per LR configuration.

## Sample-size budget

Per LR-configuration, 5 seeds × 2 LR configurations (3e-4 and 1e-4)
= 10 training runs at ~33 min each on Apple Silicon ≈ 5.5 hours
wall time. Eval (grid_scan) over each: 10 × ~6 min = 1 hour. Total
≈ 6.5 hours autonomous compute. Within ADR 0002's $10–50 compute
budget by ≥100× margin on CPU.

If LR=1e-4 was only run once originally (Run 3) and we want
parsimony, an alternative budget is **5 seeds at LR=3e-4 only**
(matching the original Run 2's configuration which is the cleanest
post-0009-fix run), with the LR-stability ablation from the original
Run 3 cited rather than re-replicated. That cuts wall time to ~3.5
hours and uses one ablation level rather than two.

**Default choice locked here: 5 seeds at LR=3e-4 only** (Run 2's
config — enforced env, default LR). The LR-stability story is already
established by the original Run 3 and does not need fresh
replication; what needs disk-permanent reproduction is the
climb-then-slide phenomenon and the SIG-EXPLORATION mechanism at
the canonical training regime.

If the publication review requires the LR-stability angle to be
re-replicated for completeness, that is a +5 seeds at LR=1e-4
follow-on, post-hoc to this pre-registration but acknowledged here
as an expected possible extension.

## Gate

This file is committed only after Eirik has reviewed and approved
the peak-window definition, the climb-then-slide and SIG-EXPLORATION
criteria, the falsification conditions, and the sample-size budget.
After commit, the runs in Step 2 are executed; the pre-registered
criteria are applied; the resolution amendment to
`0010-holding-question.md` is written against the new disk-permanent
artefacts.
