#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
Freeze the 15 main-run seeds into a reproducible per-seed summary CSV.

NO retraining. Reads the on-disk metrics.jsonl for seeds {6..20} from
~/chatcat-rl-runs/phase2_main__seed{N}__*/ and computes, under the
REVISED buffer-full ep_init window (ADR 0011 §1), the scale and
climb/slide quantities the gate and the ADR-0013 stability analysis
operate on.

This is the from-repo reproducible substrate the paper previously
lacked: the raw metrics.jsonl live in $HOME (not in the repo), so this
script + its committed output CSV are the in-repo record.

Windows / thresholds (frozen, per ADR 0010/0011 — applied, not derived):
- T = 0.0922 (climb/slide threshold).
- ep_init window: first 51 updates with ep_return_n_recent >= 100
  (the revised buffer-full window from ADR 0011 §1).
- ep_peak window: [peak_update - 25, peak_update + 25], where
  peak_update = argmax ep_return_mean_recent over the eligible region
  (ep_return_n_recent >= 100).
- ep_final window: [N - 50, N], N = total updates.
- climb = ep_peak - ep_init ; slide = ep_peak - ep_final.
- sigma_init = inter-update SD of ep_return_mean_recent over the
  ep_init window (this is the quantity the criterion-validity gate
  operates on).
- cts = (climb >= T) and (slide >= T).

DISCIPLINE — CTS gating for {11..20} (ADR 0012 gate-STOP, circularity
guard, same class as ADR §2.3 anchoring-seed):
  ADR 0012's gate FAILED on the escalation seeds {11..20}, so its
  pre-registration STOPPED before computing the climb-readout (the
  per-seed CTS) for those seeds — reading a coin-flip outcome under a
  noise-dominated criterion would present noise as a finding. This
  script therefore does NOT compute or record CTS for {11..20}: the
  cts column for those seeds is the explicit sentinel "gate-gated".
  An empty/null value would read ambiguously ("not computed" vs
  "computed false") and invite a future contributor to "fill it in";
  the sentinel states the absence is a pre-registration decision,
  to be revisited only when ADR 0013 resolves the gate-stability
  question. sigma_init / climb / slide ARE computed for all 15 (they
  are the scale quantities the gate operates ON; computing them is not
  reading the gated outcome).
"""

import csv
import json
import math
import os
import statistics
from pathlib import Path

T = 0.0922
RUNS_DIR = Path(os.path.expanduser("~/chatcat-rl-runs"))

ORIGINAL_SEEDS = [6, 7, 8, 9, 10]      # ADR 0010 main run / ADR 0011 reanalysis
ESCALATION_SEEDS = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]  # ADR 0012; CTS gate-gated
ALL_SEEDS = ORIGINAL_SEEDS + ESCALATION_SEEDS

CTS_GATED_SENTINEL = "gate-gated"

OUT_CSV = Path(__file__).parent / "seed_summary_frozen.csv"


def run_dir(seed: int) -> Path:
    matches = sorted(RUNS_DIR.glob(f"phase2_main__seed{seed}__*"))
    if len(matches) != 1:
        raise SystemExit(
            f"seed {seed}: expected exactly 1 run dir, found {len(matches)} "
            f"in {RUNS_DIR}. Cannot freeze against an ambiguous artefact."
        )
    return matches[0]


def load_metrics(seed: int) -> list[dict]:
    return [json.loads(l) for l in (run_dir(seed) / "metrics.jsonl").open()]


def first_buffer_full(rows: list[dict]) -> int:
    """First update where the rolling-100 buffer is full (n_recent >= 100)."""
    return next(r["update"] for r in rows if r["ep_return_n_recent"] >= 100)


def window_mean(rows, lo, hi, field) -> float:
    vs = [r[field] for r in rows if lo <= r["update"] <= hi]
    vs = [v for v in vs if isinstance(v, (int, float)) and not math.isnan(v)]
    return statistics.mean(vs) if vs else float("nan")


def window_sd(rows, lo, hi, field) -> float:
    vs = [r[field] for r in rows if lo <= r["update"] <= hi]
    vs = [v for v in vs if isinstance(v, (int, float)) and not math.isnan(v)]
    return statistics.stdev(vs) if len(vs) > 1 else float("nan")


def summarise_seed(seed: int) -> dict:
    rows = load_metrics(seed)
    N = len(rows)

    # Revised buffer-full ep_init window: first 51 updates with n_recent >= 100.
    ff = first_buffer_full(rows)
    iw_lo, iw_hi = ff, ff + 50

    eligible = [r for r in rows if r["ep_return_n_recent"] >= 100]
    peak_row = max(eligible, key=lambda r: r["ep_return_mean_recent"])
    peak_update = peak_row["update"]
    pw_lo, pw_hi = peak_update - 25, peak_update + 25
    fw_lo, fw_hi = N - 50, N

    ep_init = window_mean(rows, iw_lo, iw_hi, "ep_return_mean_recent")
    ep_peak = window_mean(rows, pw_lo, pw_hi, "ep_return_mean_recent")
    ep_final = window_mean(rows, fw_lo, fw_hi, "ep_return_mean_recent")
    sigma_init = window_sd(rows, iw_lo, iw_hi, "ep_return_mean_recent")

    climb = ep_peak - ep_init
    slide = ep_peak - ep_final

    # CTS: computed for ORIGINAL_SEEDS (public since ADR 0011); gate-gated
    # for ESCALATION_SEEDS (ADR 0012 gate-STOP — see module docstring).
    if seed in ORIGINAL_SEEDS:
        cts = bool((climb >= T) and (slide >= T))
        cts_field = str(cts)
    else:
        cts_field = CTS_GATED_SENTINEL

    return {
        "seed": seed,
        "group": "original" if seed in ORIGINAL_SEEDS else "escalation",
        "N": N,
        "ep_init_window_lo": iw_lo,
        "ep_init_window_hi": iw_hi,
        "peak_update": peak_update,
        "sigma_init": round(sigma_init, 6),
        "ep_init": round(ep_init, 6),
        "ep_peak": round(ep_peak, 6),
        "ep_final": round(ep_final, 6),
        "climb": round(climb, 6),
        "slide": round(slide, 6),
        "cts": cts_field,
    }


def main() -> None:
    summaries = [summarise_seed(s) for s in ALL_SEEDS]
    fields = list(summaries[0].keys())
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summaries)

    print(f"wrote {OUT_CSV} ({len(summaries)} seeds)")
    print(f"  T = {T}; ep_init = first 51 updates with n_recent>=100 (revised window)")
    print(f"  CTS computed for {ORIGINAL_SEEDS}; "
          f"'{CTS_GATED_SENTINEL}' sentinel for {ESCALATION_SEEDS} (ADR 0012 gate-STOP)")
    # sigma_init is the gate input — echo the two committed medians as a
    # self-check the frozen file matches the ADR record.
    orig = statistics.median([s["sigma_init"] for s in summaries if s["group"] == "original"])
    esc = statistics.median([s["sigma_init"] for s in summaries if s["group"] == "escalation"])
    print(f"  median sigma_init: original={orig:.6f} (ADR 0011: 0.023918), "
          f"escalation={esc:.6f} (ADR 0012: 0.036166)")


if __name__ == "__main__":
    main()
