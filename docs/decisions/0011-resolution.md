# ADR 0011 Resolution — gate passed, M' = 3/5 (borderline, inconclusive on N=5 reanalysis-budget)

**Status:** Resolved on the pre-registered branch (2026-06-05).
Kriterie-validitet-gate PASSED (T/σ_diff = 2.7257). Climb-readout
performed against the revised buffer-full `ep_init`-window per §1.
**M' = 3/5 — borderline branch per §4.** 0011 closes inconclusive on
the N=5 reanalysis-budget; ADR 0010's phenomenon-status remains open.
Any further escalation requires a separate ADR with its own pre-
registered scope (new training, not budsjett-fri reanalysis).

**Tracks:** Climb-vindu-reanalyse per ADR 0011 stub (commit `4647ed8`),
on the existing five main-run `metrics.jsonl` files in
`~/chatcat-rl-runs/phase2_main__seed{6,7,8,9,10}__*/`. No new training,
no edits to `0010-*.md` or `0011-climb-window-reanalysis.md`.

**Files referenced:**
- `0011-climb-window-reanalysis.md` (commit `4647ed8`) — pre-reg this resolves against
- `0010-resolution.md` (commit `1ba60c0`) — the phenomenon-question this aimed to resolve

---

## §3 Kriterie-validitet-gate — PASS

Per-seed inter-update-SD of `ep_return_mean_recent` over the revised
ep_init-window (first 51 updates with `ep_return_n_recent ≥ 100`):

| seed | first buffer-full update | window | inter-update-SD |
|---:|---:|:---:|---:|
| 6 | 849 | [849, 899] | 0.021220 |
| 7 | 823 | [823, 873] | 0.028428 |
| 8 | 837 | [837, 887] | 0.018406 |
| 9 | 841 | [841, 891] | 0.023918 |
| 10 | 841 | [841, 891] | **0.078524** |

**Gate computation (pre-registered per §3, no outcome-tuning):**

| Quantity | Value |
|---|---:|
| `σ_init_revised` (median over 5 per-seed SDs) | **0.023918** |
| `σ_diff = σ_init_revised × √2` | 0.033826 |
| T (uendret fra ADR 0010) | 0.0922 |
| **T / σ_diff** | **2.7257** |

**Gate decision: PASS** (T/σ_diff = 2.7257 ≥ ~2). Climb-leddet er validt
testbart mot buffer-fullt vindu. Proceeded to climb-readout per §1.

Context (for reading, not for decision-making):
- σ in original [100,150] init window was ~0.349 (ADR 0010 dokumenterte
  dette etter F3-fyring; det var grunnlaget for konfunder-observasjonen).
- σ in late-stable [N−150, N−50] was 0.0307 (the T-anchor window).
- σ in revised buffer-full window: 0.0239 (this measurement).

The revised window's σ landed close to the late-stable σ that anchored T
— consistent with the lærdommen that the original [100,150] noise was
artefact of buffer-sparsity, not of training-phase dynamics.

**Note on seed 10's outlier SD (0.0785).** Median was the pre-registered
choice for σ_init_revised, not mean — explicitly to be robust against
exactly this kind of single-seed outlier. Mean over the five (0.0341)
would have given T/σ_diff = 1.91, which would have FAILED the gate.
The choice to use median was locked in §3 before the measurement; this
note is descriptive, not a re-decision.

---

## §1 Climb-readout — M' = 3/5

Per seed, against the revised ep_init-window:

| seed | init-window | ep_init | peak@update | ep_peak | ep_final | climb | slide | CTS' |
|---:|:---:|---:|---:|---:|---:|---:|---:|:---:|
| 6 | [849, 899] | −0.923 | 1548 | −0.761 | −0.968 | **+0.162 ✓** | +0.208 ✓ | **✓** |
| 7 | [823, 873] | +0.453 | 852 | +0.449 | −1.010 | −0.004 ✗ | +1.459 ✓ | ✗ |
| 8 | [837, 887] | −0.969 | 1603 | −0.530 | −1.311 | **+0.439 ✓** | +0.780 ✓ | **✓** |
| 9 | [841, 891] | −0.546 | 2102 | +0.179 | −0.115 | +0.724 ✓ | +0.294 ✓ | ✓ |
| 10 | [841, 891] | −0.943 | 841 | −0.857 | −1.217 | **+0.085 ✗** | +0.359 ✓ | **✗** |

**M' = 3/5** (seeds 6, 8, 9 reproduce CTS' against revised window).

`ep_peak` and `ep_final` are unchanged from ADR 0010 (same peak-update,
same final-window, same data). The reanalysis varied only `ep_init`'s
window per §1.

---

## Direct comparison with ADR 0010 (same data, only ep_init's window changed)

| seed | ep_init [100,150] (0010) | ep_init revised (0011) | Δ ep_init | climb 0010 | climb 0011 | CTS 0010 | CTS' 0011 |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 6 | −0.575 | −0.923 | −0.348 | −0.186 ✗ | +0.162 ✓ | ✗ | **✓** |
| 7 | +0.412 | +0.453 | +0.041 | +0.037 ✗ | −0.004 ✗ | ✗ | ✗ |
| 8 | −0.386 | −0.969 | −0.584 | −0.145 ✗ | +0.439 ✓ | ✗ | **✓** |
| 9 | −0.508 | −0.546 | −0.038 | +0.686 ✓ | +0.724 ✓ | ✓ | ✓ |
| 10 | −1.391 | −0.943 | +0.449 | +0.534 ✓ | +0.085 ✗ | ✓ | **✗** |

**Three of five seeds flipped CTS-status when the window changed:**
- Seed 6: ✗ → ✓ (ep_init dropped by 0.348, climb went from −0.186 to +0.162)
- Seed 8: ✗ → ✓ (ep_init dropped by 0.584, climb went from −0.145 to +0.439)
- Seed 10: ✓ → ✗ (ep_init rose by 0.449, climb dropped from +0.534 to +0.085)

This is direct evidence that **the ep_init-window matters substantially**
for amplitude-CTS classification: changing only the window flipped 60%
of the seed-classifications. The confunder ADR 0010-resolution documented
is real — both in magnitude (Δ ep_init up to 0.58 return units, comparable
to climb-amplitude itself) and in direction-symmetric way (confunder
hid CTS on seeds 6, 8 but created false-positive CTS on seed 10).

Seeds 7 and 9 were stable across the two windows (Δ ep_init small, CTS
status unchanged) — these were the cases where ep_init in the original
window was not buffer-noise-confounded.

The confunder cuts both ways: it didn't just hide robustness, it also
manufactured robustness where the cleaner window doesn't sustain it.
This is important framing: the reanalysis did not "rescue" the
phenomenon by simply granting more CTS-qualifications — it produced
a different mixture (3 new-CTS') that still doesn't reach the M' ≥ 4/5
threshold.

---

## §4 branch — M' = 3/5 (borderline)

Per pre-reg §4, locked verbatim before measurement:

> **M' = 3/5** → **borderline**. Reanalysens scope er budsjett-fri
> re-måling av eksisterende fem `metrics.jsonl`. Det er ingen "kjør 5
> ekstra seeds"-utvidelse innenfor 0011s scope — det ville bryte
> budsjett-fri-rammen og kreve ny pre-registrering. **Borderline-
> utfallet lukker derfor 0011 ambigust:** climb-vindu-konfunderen er
> delvis reell men ikke avgjørende på N=5. ADR 0010s fenomen-status
> forblir åpent. En eventuell videre escalation til ny trening med
> N>5 må pre-registreres i et separat ADR (foreløpig 0012, ikke
> planlagt nå). 0011 selv lukkes med tydelig "inconclusive on N=5
> reanalysis-budget" som rapportert utfall.

That branch fires. 0011 closes inconclusive.

**Reading honestly:** the reanalysis showed that the climb-window
confunder ADR 0010 documented is real, large, and direction-symmetric.
That is a substantive finding even though the overall M'-count is
inconclusive. The net effect on the phenomenon-question — "is
climb-then-slide robust over seeds?" — is:

- It is more robust than ADR 0010's M = 2/5 suggested (M' = 3/5 against
  a well-posed criterion).
- It is not clearly robust at the publishable threshold (M' < 4/5).
- The data on N=5 cannot distinguish "robust with noise mismeasured by
  0010" from "borderline-robust where the borderline cannot be
  resolved without more seeds".

That is the honest reading. It is not a "phenomenon mostly survives"
spin nor a "phenomenon mostly fails" spin. The N=5 reanalysis-budget
genuinely does not resolve which side of borderline the truth sits on.

---

## §5 SIG-EXPLORATION on CTS'-qualified seeds — F1 / F2 inactive

On the three CTS'-qualified seeds (6, 8, 9), with logstd_drift_peak's
init-term computed over the revised buffer-full window per §5:

| seed | logstd_init (revised) | logstd_peak | logstd_drift_peak | F1? (< −0.14) | vloss_peak (median) | vloss/K | F2? (> K) |
|---:|---:|---:|---:|:---:|---:|---:|:---:|
| 6 | +0.130 | +0.134 | +0.004 | ok | 0.001461 | 0.293 | ok |
| 8 | +0.014 | +0.124 | +0.110 | ok | 0.001651 | 0.331 | ok |
| 9 | −0.057 | −0.086 | −0.030 | ok | 0.001277 | 0.256 | ok |

- F1 fyrer på: **0/3** CTS'-kvalifiserte seeds (half-up rule per
  Precision 1: ≥ 2 av 3 ville fyrt; 0 fyrer)
- F2 fyrer på: **0/3** CTS'-kvalifiserte seeds (same)

**SIG-EXPLORATION holds on all three CTS'-qualified seeds.** The
mechanism diagnosis from `31c363e` continues to hold wherever
climb-then-slide actually occurs — consistent with both ADR 0010's
main-run finding (2/2 CTS-qualified) and 0011's reanalysis (3/3
CTS'-qualified). No reanalysis-induced flip of F1/F2 status.

This is the prediction from ADR 0010 §4's falsifiserings-balanse:
F1/F2 forventes inaktive; hovedrundens (and reanalysen's) primary
empirical innsats ligger i F3/F4 (reproduksjons-robusthet), ikke i
mekanismen. ADR 0011's reanalysis confirms that division: mechanism
holds, robustness-question remains the unresolved part.

---

## What this means for ADR 0010's phenomenon-status

ADR 0010 is **resolved** on its locked criterion (F3 fired, 2/5 CTS).
That status is unchanged by 0011's reanalysis — the locked criterion
is what it was, and re-measuring a frozen criterion does not change
its historical outcome. ADR 0010's resolution document holds as
written.

ADR 0010's **phenomenon-question**, left open in its §5, is now:

- **Not closed** by 0011. M' = 3/5 is borderline; the pre-reg locked
  borderline as inconclusive on N=5 reanalysis-budget.
- **Better understood** in light of 0011's evidence: the climb-window
  confunder is real, large (Δ ep_init up to 0.58), and
  direction-symmetric (creates false-positives as well as
  false-negatives). The amplitude-CTS classification in ADR 0010
  was substantially confunder-dependent for 3 of 5 seeds.
- **Most accurately framed** as: phenomenon-robustness sits on the
  borderline against a well-posed criterion; resolving which side
  requires either more seeds (new training, separate ADR) or accepting
  the borderline as the answer.

---

## What 0011 opens up (not done here)

- An eventual ADR 0012 with new training at N > 5 could resolve the
  borderline on the revised window. The amount of new training required
  depends on what M' over the larger N would need to land at: if M' ≥
  reaches publishable threshold on (say) 4/10 or 6/10 against the
  revised window, then phenomenon is robust; if it stays at 3/5-rate
  proportionally, then borderline is the answer at any N. That is
  itself a pre-registration decision for ADR 0012, not for this
  resolution to settle.
- Alternatively, accepting borderline as the answer is a publishable
  outcome on its own — "the phenomenon is approximately half-reproducible
  on this configuration; here is the methodology that distinguishes
  the climb-window confunder from genuine non-robustness". That framing
  is consistent with ADR 0010's preprint-pivot to "what determines
  whether the slide occurs".
- Choice between these two paths is downstream of this resolution.

---

## What this resolution does NOT do

- **Does not amend ADR 0010 or its files.** ADR 0010's locked criterion
  fired against it; that outcome is preserved as historical record.
- **Does not change T or K.** Both held fixed from ADR 0010 throughout
  the reanalysis, as §2 required.
- **Does not select a candidate fix.** That is downstream of choosing
  between the two ADR 0012 paths above.
- **Does not pre-register ADR 0012.** If new training is the chosen
  next step, ADR 0012 is its own document with its own seed-set,
  compute commitment, and pre-registered thresholds.
- **Does not change the methodology gate established here.** The
  kriterie-validitet-gate (§3) is now part of the project's
  pre-registration vocabulary — to be reused, not re-derived, in
  future ADRs.

---

## Method-lærdom carried forward

The validity-gate worked. It was the missing piece ADR 0010 identified
in its method-lærdom section, made operational here, and it produced
a meaningful PASS that justified proceeding to climb-readout. Future
ADRs that lock thresholds against measured noise should include a
validity-gate of this form: threshold against application-window noise,
not only against outcome span.

The fact that the validity-gate could have FAILED (mean over per-seed
SDs would have given T/σ_diff = 1.91 — sub-threshold) and that median
was the correct pre-registered choice, is itself a methodological
finding. Picking the right summary statistic for σ_init_revised is
not a free choice; the pre-reg locked median for spike-robustness
reasons that turned out to matter on this dataset specifically.
