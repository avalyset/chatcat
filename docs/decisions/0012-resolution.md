# ADR 0012 Resolution — kriterie-validitet-gate FAILED on new ten seeds; no climb-readout performed

**Status:** Resolved on the pre-registered FAIL branch (2026-06-06).
Kriterie-validitet-gate on the ten new seeds (`{11..20}`) FAILED with
T/σ_diff_new = **1.8027** (below the locked ~2 threshold). Per pre-reg
§3, climb-readout was **not** performed. ADR 0011's borderline status
on the phenomenon-question is **unchanged** by 0012 — the reanalysis
this stub designed was not run, so it contributes no new M''-count.

The FAIL is itself a substantive finding: the new seeds have a
meaningfully larger noise-scale than the hovedrundens fem despite
identical training configuration. That finding is reported as-is,
not patched or interpreted into a climb-readout the pre-reg
explicitly forbade in this case.

**Tracks:** N=15 escalation per ADR 0012 stub (commit `3e45ac7`), to
resolve the borderline ADR 0011 closed inconclusive. Ten new training
runs (seeds {11..20}, sequential, ~5.3h wall time, 2026-06-05 20:22 →
2026-06-06 01:40) executed against the locked configuration. All ten
produced complete artefacts (`metrics.jsonl` + `agent.pt` +
`best_so_far.pt`) at `~/chatcat-rl-runs/`.

**Files referenced:**
- `0012-escalation-to-n15.md` (commit `3e45ac7`) — pre-reg this resolves against
- `0011-resolution.md` (commit `8e977f1`) — the borderline 0012 was meant to resolve

---

## §3 Kriterie-validitet-gate — FAIL

Per-seed inter-update-SD of `ep_return_mean_recent` over the revised
buffer-full ep_init-window (first 51 updates with
`ep_return_n_recent ≥ 100`) for the ten new seeds:

| seed | first buffer-full update | window | inter-update-SD |
|---:|---:|:---:|---:|
| 11 | 830 | [830, 880] | 0.030381 |
| 12 | 834 | [834, 884] | 0.033319 |
| 13 | 844 | [844, 894] | 0.026707 |
| 14 | 826 | [826, 876] | **0.069636** |
| 15 | 867 | [867, 917] | 0.039013 |
| 16 | 838 | [838, 888] | **0.053293** |
| 17 | 849 | [849, 899] | 0.027316 |
| 18 | 852 | [852, 902] | **0.061690** |
| 19 | 829 | [829, 879] | **0.053154** |
| 20 | 848 | [848, 898] | 0.025466 |

**Gate computation (per pre-reg §3, no outcome-tuning):**

| Quantity | Value |
|---|---:|
| `σ_init_revised_new` (median over 10 seeds) | **0.036166** |
| `σ_diff_new = σ × √2` | 0.051146 |
| T (locked from ADR 0010) | 0.0922 |
| **T / σ_diff_new** | **1.8027** |
| Gate threshold | ~2 |
| **Decision** | **FAIL** |

For comparison (ADR 0011 measurement on the original five seeds
`{6..10}`):

| | {6..10} (ADR 0011) | {11..20} (ADR 0012) |
|---|---:|---:|
| σ_init_revised (median per-seed SD) | 0.023918 | **0.036166** |
| σ_diff | 0.033826 | 0.051146 |
| T / σ_diff | 2.7257 (PASS) | **1.8027 (FAIL)** |

The new ten seeds have a median noise-scale ~50 % larger than the
original five, despite identical training configuration. Three to four
of the new seeds (14, 16, 18, 19) have SDs above 0.05 — the original
five had one outlier (seed 10 at 0.079) and four tightly clustered
values (0.018–0.028).

---

## Per pre-reg §3 — STOP, no climb-readout

The FAIL branch was locked verbatim in ADR 0012 stub §3:

> **FAIL** if `T / σ_diff_new < ~2`. The new seeds have a meaningfully
> different noise-scale than the hovedrundens fem despite identical
> configuration. **STOP**. Do not proceed to climb-readout. Report
> the gate-failure, the measured `σ_init_revised_new`, and the ratio.
> This would be an unexpected finding (same config should produce
> same noise-scale) and warrants investigation before climb-readout —
> not a patch to the climb-definition in 0012.

That branch fires. **No climb-readout was performed on the 15 seeds.**
No M'' was tallied. The three-way outcome locked in §4 (M''≥11/15
robust, M''≤6/15 not-robust, M''=7–10/15 intrinsically seed-variable)
is **not engaged** because the gate that gates it failed.

This is not a methodology failure — it is the pre-reg working as
designed. The pre-reg locked a STOP rule, and the STOP rule fired
on data the pre-reg explicitly anticipated could trigger it.

---

## What the FAIL means substantively

The FAIL is itself an unexpected finding worth reporting plainly:

**The same training configuration produces meaningfully different
noise-scales across seed-samples.** Specifically:

- ADR 0011's σ_init_revised on `{6..10}` was 0.024 (median over five).
- ADR 0012's σ_init_revised_new on `{11..20}` is 0.036 (median over
  ten).
- The two samples were trained under identical config: baseline-
  normalised reward, Box(7,), `ppo_continuous_action`, ent_coef=0.0,
  5M steps, LR=3e-4, same instrumentation (commit `cd5def3`), same
  persistent path (`~/chatcat-rl-runs/`).

The difference of ~50 % in median noise-scale across two random
samples of seeds is large enough to flip the gate-decision (2.73 PASS
→ 1.80 FAIL with the same T). This implies one of:

1. **The {6..10} sample's lower noise was statistically lucky.** Five
   seeds is a small sample; the true population noise-scale may be
   closer to {11..20}'s estimate, and {6..10} happened to under-sample
   the high-noise tail. The seed-10 outlier at 0.079 in {6..10} was
   still surrounded by four tightly-clustered low values.
2. **The {11..20} sample is itself unrepresentative on the high
   side.** Three of ten seeds with SD > 0.05 might be a high-noise
   tail in the new sample that washed out the median upward.
3. **Per-seed noise-scale is intrinsically high-variance.** Training
   dynamics at this configuration may produce wide seed-to-seed
   variation in early-training noise that is not predictable from
   the configuration itself.

ADR 0012's pre-reg does not authorise interpreting which of these is
true. If such investigation is pursued at all — and that is a
research-prioritisation decision Eirik makes downstream, not implied
by this resolution — it belongs in a separate ADR with its own
pre-registration. What 0012 does report is the **unexpected magnitude
of the difference**, on disk and committed, so that any future ADR
addressing it starts from the documented data rather than from the
framing of this resolution.

Note that the third FAIL-interpretation above is itself a kind of
endpoint, not a deferral. If per-seed noise-scale is intrinsically
high-variance at this configuration, then whether the phenomenon
"reproduces" is itself seed-measurement-dependent at the threshold
the pre-reg locked, and ADR 0011's borderline may be the honest
answer for this configuration rather than a measurement to escalate
past. The pre-reg discipline that locked midtbåndet as an endpoint
in ADR 0012's §4 applies in spirit here too: not every gate-FAIL is
an invitation to more compute.

---

## What this means for ADR 0011's borderline status

**ADR 0011's M' = 3/5 borderline status on the phenomenon-question is
unchanged.** ADR 0012 was the path to resolve that borderline via
N=15 climb-readout; that path was not traversed because the gate
failed. The phenomenon-question therefore stands exactly where ADR
0011 left it: borderline on N=5, inconclusive on the reanalysis-budget,
**not yet resolvable** because the escalation-path encountered an
unexpected obstacle.

This is not a regression. ADR 0011's resolution is intact; its
"phenomenon-status open" framing remains accurate; the three-way
outcome it pointed to as the next decision point is now empirically
unreachable on the ADR 0012-budget specifically because the new seeds
did not satisfy the validity-gate the same way the original five did.

---

## What ADR 0012 opens up (not done here)

The gate-FAIL leaves the phenomenon-question in the same state ADR
0011 left it — borderline on N=5, the N=15 escalation-path blocked by
an unanticipated noise-scale discrepancy. Three responses are
possible. Choosing among them is a research-prioritisation decision
Eirik makes downstream; **none is implied or recommended by this
resolution**. The three are presented below in order of compute-cost
(lowest to highest), not in order of preference.

- **Path 1 — Accept ADR 0011's borderline as the answer for this
  configuration.** The N=5 reanalysis-budget gave a borderline; the
  N=15 escalation-path is blocked by a different problem (seed-to-seed
  noise variability itself substantial); the phenomenon-question
  simply doesn't resolve cleanly at this configuration. Publishable
  framing: "we attempted N=15 escalation; the validity-gate revealed
  that seed-to-seed noise variability is itself substantial enough to
  block the resolution path. Borderline is the answer this
  configuration supports." Zero new compute. This path is also where
  the third FAIL-interpretation (intrinsic high-variance) lands
  naturally: if noise itself is seed-dependent, "borderline" IS the
  configuration-answer.

- **Path 2 — Pivot the preprint to "what determines training-dynamics
  variability"** rather than "is climb-then-slide robust". That
  framing acknowledges both ADR 0011's borderline (real but
  unresolvable on N=5) and ADR 0012's gate-fail (real and informative
  about seed-to-seed variability) as parts of a larger story about
  training-dynamics heterogeneity. No further training needed; the
  existing fifteen seeds' artefacts are sufficient evidence for this
  framing. Zero new compute, different framing.

- **Path 3 — Open a separate ADR (e.g., 0013) to investigate the
  noise-scale discrepancy directly.** Possible measurements: re-run
  selected high-noise and low-noise seeds to check for reproducibility
  of the noise-scale itself; compare per-update RNG state across
  seeds; examine whether episode-length distributions differ
  systematically between the two batches. None of that is
  pre-registered here; if pursued, it would be the new ADR's job —
  with its own pre-registration locked before any new analysis or
  training, same discipline as 0011/0012. This is the only path that
  re-opens compute, and it should not be taken by default just because
  it is the most "active" option. The midtbånd-as-endpoint principle
  pre-registered in ADR 0012 §4 was specifically to prevent that
  default; a gate-FAIL outcome does not undo that principle.

Which path to take is downstream of this resolution. Not chosen here.
Documenting the three explicitly, with the no-compute paths listed
first, is itself an act of pre-registration discipline against
escalation-by-default.

---

## What this resolution does NOT do

- **Does not perform climb-readout on any of the 15 seeds.** The
  pre-reg locked STOP on gate FAIL; STOP fired.
- **Does not amend ADR 0010, 0011, or the ADR 0012 stub.** Their
  text stays intact; this resolution adds the FAIL outcome as a new
  document.
- **Does not change T, K, the revised ep_init-window, or any other
  locked quantity.** All held fixed.
- **Does not select between the three "what 0012 opens up" paths
  above.** That is a separate research-prioritisation decision.
- **Does not pre-register any follow-on ADR.** Of the three paths in
  §"What 0012 opens up", two (accept-borderline, pivot-framing)
  require no new ADR at all; only Path 3 (investigate noise-scale
  discrepancy) would. If Path 3 is chosen, the follow-on ADR is its
  own document with its own pre-registered scope locked before any
  new analysis or training.
- **Does not re-run any seeds.** All ten new seeds completed cleanly
  with deterministic state_dict_sha256 values; re-running them would
  produce bit-identical artefacts. The FAIL is reproducible from
  the existing data without new compute.

---

## Method-lærdom carried forward

The kriterie-validitet-gate established in ADR 0011 and reused here did
its job: it caught a problem before the climb-readout would have run
against an invalid criterion. The gate's STOP rule prevented exactly
the kind of post-hoc rationalisation the pre-reg discipline exists to
prevent — namely, "the gate is borderline, just barely sub-threshold,
let's call it close enough and proceed". The pre-reg said "FAIL if
ratio < ~2"; the ratio was 1.80; the STOP fired. No fudge factor.

This is the gate worth keeping in the project's pre-registration
vocabulary. It is now operational across two resolutions (PASS in ADR
0011, FAIL in ADR 0012). Future pre-registrations that lock thresholds
against measured noise should continue to include a validity-gate of
this form: locked threshold, locked STOP rule, no patches when the gate
fails.

The lesson from the FAIL itself — that same-config seeds can show ~50%
variation in measured noise-scale — is a substantive finding about
training dynamics that ADR 0010's main run on N=5 and ADR 0011's
reanalysis on the same five could not have surfaced. That finding
would not exist if ADR 0012 had not been pre-registered with a gate
that could fail. The honest negative outcome is the outcome that made
the finding visible.
