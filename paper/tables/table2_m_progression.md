# Table 2 — Phenomenon-reproduction count across measurement passes

Climb-then-slide reproduction count `M / M' / M''` across the three ADR measurement passes on the same phenomenon-question. T = 0.0922 (locked from ADR 0010); the only thing that changes is the ep_init-window definition.

| pass | ADR | seeds | ep_init window | gate | count | reading |
|---|---|---|---|---|---:|---|
| M | 0010 main run | {6..10} | original [100, 150] | not built yet | **2/5** | F3 fires on locked criterion |
| M' | 0011 reanalysis | {6..10} | revised buffer-full | PASS (T/σ_diff = 2.73) | **3/5** | borderline, inconclusive on N=5 reanalysis-budget |
| M'' | 0012 escalation | {11..20} added | revised buffer-full | **FAIL (T/σ_diff = 1.80)** | not tallied | climb-readout not performed per pre-reg §3 |

**Per-seed flips between M and M' (same data, only ep_init window changed):**

| seed | climb (M, [100,150]) | climb (M', revised) | CTS M | CTS M' | flip |
|---:|---:|---:|:---:|:---:|:---|
| 6 | -0.1860 | +0.1624 | ✗ | ✓ | ✗→✓ (confunder hid CTS) |
| 7 | +0.0373 | -0.0040 | ✗ | ✗ | no change |
| 8 | -0.1445 | +0.4391 | ✗ | ✓ | ✗→✓ (confunder hid CTS) |
| 9 | +0.6863 | +0.7242 | ✓ | ✓ | no change |
| 10 | +0.5340 | +0.0852 | ✓ | ✗ | ✓→✗ (confunder fabricated CTS) |

The phenomenon-question is now empirically unreachable at the available compute budget: ADR 0010's locked criterion was noise-confunded (M = 2/5 mismeasures phenomenon); ADR 0011's reanalysis produced a borderline (M' = 3/5, three seeds flipped, no clear side); ADR 0012's escalation to N=15 was blocked at the validity-gate by an unexpected noise-scale difference between same-config batches. This is itself a substantive finding about training-dynamics seed-variability.
