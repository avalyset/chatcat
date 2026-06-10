## 2 Methods

### 2.1 Setup

We trained an RL agent against an ethological simulator (SimCat) in a companion-AI context. The agent is CleanRL's `ppo_continuous_action` over a continuous action space Box(7,), with a stdio bridge between the Python side running RL and the TypeScript runtime running the simulator. Reward is baseline-normalised: R_agent − R_baseline. This is the setup in which the phenomenon we study arises — climb-then-slide, where the agent climbs to the baseline line and does not hold it.

Each run is about 5M steps, roughly 33 minutes CPU. Runs are deterministic per seed; we verified this by an interrupted run overlapping bit-identically with its restart over 1391 updates. Artefacts live on persistent storage, not on a volatile path — a point we return to, because an earlier dataset was lost and forced reconstruction.

### 2.2 Pre-registration discipline

Every methodological decision was locked and pushed to version control before data was collected or training was run. Metrics, thresholds, success criteria, and falsification conditions are committed in advance. Pre-registration is not novel in principle — what we do is apply it with a precision RL evaluation rarely has: the full decision trail lives chronologically in the version history, and every claim in the results points to the commit that locked the assumption it rests on. The pattern repeated over four iterations through the work.

### 2.3 Anchoring seed

The thresholds are measured, not guessed. Two thresholds govern the evaluation: T for climb/slide, K for critic-convergence. Both are anchored in measured scale from one dedicated anchoring run rather than in a chosen number. The anchoring seed measures the scale quantities — inter-update SD over a defined window (after the rolling 100-episode buffer has filled), median value_loss over a late window — and T and K are set as multiples of these.

One discipline here is decisive. The anchoring seed's own outcome — whether it itself reproduced the phenomenon — is never read and does not count as a data point. It sets scale, not result. If we let it count as both, the criterion would become circular: a seed that helped define the threshold could not at the same time be an independent test of it.

The numbers: T = 0.0922, three times the late-stable inter-update SD of 0.0307. K = 0.004986, three times the median value_loss of 0.001662. The multipliers were locked before measurement and justified noise-statistically — roughly two standard deviations outside the noise-difference — not tuned to hit a desired outcome.

### 2.4 Criterion-validity gate

This is the contribution. Before a threshold is applied, we verify that it is separable from the noise in its own application window: T must sit at least roughly twice above the noise-difference in that window. We write σ_diff = σ × √2 for the noise in the difference between two window means (under a simplifying independence assumption).

Why it is needed: standard pre-registration locks the threshold and validates it against the outcome span, peak minus end. It does not validate it against the noise in the window the threshold is actually measured against. A threshold can pass the first check and still be noise-dominated in the application window. When it is, which seeds pass is close to random — and the result reads as a finding about the agent when it is a finding about the window.

The gate has a pre-registered binary outcome. PASS: the threshold is valid, the evaluation proceeds. FAIL: the threshold is noise-dominated in this window, and we stop instead of applying it. We ran the gate twice. It passed the first time (T/σ_diff = 2.73) and failed the second (T/σ_diff = 1.80). That it failed on a real dataset (the N=15 escalation, T/σ_diff = 1.80) shows that the PASS in the criterion-validity reanalysis (T/σ_diff = 2.73) was not predetermined by construction.

### 2.5 Falsification structure

The success criterion and the falsification were pre-registered: how many seeds must reproduce the phenomenon for it to count as robust, and what counts as not-robust. The escalation added a third outcome that is the most important design choice in the whole structure. The middle band (the middle outcome band, pre-registered as "intrinsically seed-variable") is a real finding, not a failed test. If the phenomenon occurs about half the time without hidden structure beneath it, *that* is the answer — the phenomenon is intrinsically seed-variable — and not a call for more compute. We pre-registered that outcome precisely to close the infinite-escalation trap: without a defined middle band, an ambiguous result can always justify one more run, indefinitely.

To distinguish an optimisation artefact from a feature of the reward landscape, we pre-registered a diagnostic signature, SIG-EXPLORATION: if the variance in the policy (`actor_logstd_mean`) does not collapse while the critic (`value_loss`) converges low, the slide sits on the optimisation side. The signature is read from logs that already exist — it costs no new training.

### 2.6 Reproducibility

The entire decision-and-evidence trail lives as an ADR chain in the version history, chronological, stub before resolution. Every threshold, every gate, every outcome points to a commit hash. All the runs the paper builds on come from one seed set under identical configuration, and the figures and tables are traceable to the same dataset — not to an earlier set that was lost. The ADR chain is the reproducible appendix; the plotting scripts sit next to the figures they generate.
