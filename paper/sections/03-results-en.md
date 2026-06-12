## 3 Results

### 3.1 The phenomenon in form

All five seeds in {6..10} climb to a peak and slide back. In form, climb-then-slide is universal — 5/5 — and this is what the curves show directly (Fig 1). But form is not the same as amplitude against a threshold. Whether the climb leg actually passes T depends on which window we measure it in, and that distinction — form versus amplitude-against-threshold — is the whole point of what follows.

### 3.2 The direction-symmetric confounder

We write CTS (climb-then-slide) when we refer to whether a seed reproduced the phenomenon against the threshold, and M, M', M'' for the reproduction count in each of the three measurement passes. The same measurement window lied both ways (Fig 3). With the original ep_init window [100,150], seeds 6 and 8 measured their climb leg below T — not reproduced. Moved to the buffer-full window, the same two passed above T. The window had hidden real climb-then-slide. At the same time seed 10 went the other way: above T in the original window, below T in the revised one. The window had fabricated a phenomenon that was not there.

That is the key finding. A window change that had only hidden, or only fabricated, could be dismissed as a one-way bias one corrects for. That the same change moved two seeds into a positive result and a third out of it, simultaneously, shows that which seeds pass is governed by the measurement choice, not by the agent. The numbers shifted accordingly: M against the original window was 2/5, M' against the buffer-full one was 3/5 (Table 2).

### 3.3 The mechanism

On the seeds that reproduce climb-then-slide, the SIG-EXPLORATION signature holds (Fig 2). The variance in the policy does not collapse during peak, and the critic is converged low. The slide is the optimisation side of a wide-variance policy, not a result of variance collapse. The pattern is the same on all reproducing seeds, across both measurement passes.

### 3.4 The gate passed, then failed

In the criterion-validity reanalysis the gate passed — T/σ_diff = 2.73 — and M' landed at 3/5. Borderline, and inconclusive on five seeds. The N=15 escalation added ten new seeds, {11..20}, for N=15. There the gate failed: T/σ_diff = 1.80. The same training configuration produced a median noise scale roughly 50% higher on the new seed set, 0.0362 against 0.0239 (Table 1). The stop rule was triggered before M'' was tallied.

The finding sits there. Measurability itself is seed-variable: the noise scale T was anchored against on one seed set does not hold on another under identical configuration. That is one level deeper than the phenomenon. We cannot decide whether climb-then-slide is robust — not because we lack data, but because the threshold is not stably applicable across seeds.

### 3.5 The gate verdict is itself seed-variable

The FAIL was a slice outcome. The N=15 escalation computed its FAIL — T/σ_diff = 1.80 — on the ten new seeds {11..20}. But the verdict depends on which seeds are drawn: the full set {6..20} gives T/σ_diff = 2.1459 — a bare PASS. Same corpus, different slice, opposite verdict.

The verdict-stability resampling pre-registered this as a question and measured it. Resampling across the fifteen seeds — exhaustive choose-k for k=5 and k=10, the full set for k=15 — yields the distribution of the gate verdict itself. At k=5 the PASS rate is 0.5734, a coin flip; at k=10 it is 0.7063. The distribution sits centered just above the threshold — k=5 median ratio 2.146 — yet 43% of draws fall below 2.0. The verdict landed in the pre-registered mid-band [0.20, 0.80): the gate verdict is intrinsically seed-variable.

The mechanism is not the one §3.4 implied — and the resampling corrects it. A Brown-Forsythe test on {6..10} against {11..20} gives W = 0.000159, p = 0.99: there is no detectable scale difference between the batches. The apparent ~50% gap in median noise (0.0239 against 0.0362) is not a noisier second batch. It is seed-wander across the noise floor σ* = T/(2√2) = 0.0326. The population straddles the floor, so the median's position — and with it the verdict — depends on the draw, not on the batch. Where §3.4 read the two seed sets as genuinely different, they are one set straddling a common floor.

This is the endpoint the resampling named in advance, now realized — the earned, quantified form of "measurability is seed-variable": a real endpoint, not a call for more compute.
