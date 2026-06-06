# Table 1 — Kriterie-validitet-gate: ADR 0011 PASS vs ADR 0012 FAIL

Per-seed inter-update-SD of `ep_return_mean_recent` over each seed's revised buffer-full ep_init-window (first 51 updates with `ep_return_n_recent ≥ 100`). Gate fires if `T / (σ_median × √2) ≥ ~2`.

| seed | inter-update-SD | group |
|---:|---:|:---|
| 6 | 0.021220 | {6..10} (ADR 0011) |
| 7 | 0.028428 | {6..10} (ADR 0011) |
| 8 | 0.018406 | {6..10} (ADR 0011) |
| 9 | 0.023918 | {6..10} (ADR 0011) |
| 10 | 0.078524 | {6..10} (ADR 0011) |
| 11 | 0.030381 | {11..20} (ADR 0012) |
| 12 | 0.033319 | {11..20} (ADR 0012) |
| 13 | 0.026707 | {11..20} (ADR 0012) |
| 14 | 0.069636 | {11..20} (ADR 0012) |
| 15 | 0.039013 | {11..20} (ADR 0012) |
| 16 | 0.053293 | {11..20} (ADR 0012) |
| 17 | 0.027316 | {11..20} (ADR 0012) |
| 18 | 0.061690 | {11..20} (ADR 0012) |
| 19 | 0.053154 | {11..20} (ADR 0012) |
| 20 | 0.025466 | {11..20} (ADR 0012) |

**Aggregate (per group):**

| | {6..10} (ADR 0011) | {11..20} (ADR 0012) |
|---|---:|---:|
| n seeds | 5 | 10 |
| median σ | **0.023918** | **0.036166** |
| σ_diff = σ × √2 | 0.033826 | 0.051146 |
| T / σ_diff | **2.7257** | **1.8027** |
| Gate decision (threshold ≥ ~2) | **PASS** | **FAIL** |

T = 0.0922 (locked since 0140536). The gate fired in opposite directions on the two batches despite identical training configuration — evidence that the gate is not a formality and that same-config noise-scale is itself substantial.
