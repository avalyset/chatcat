#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26", "scipy>=1.11"]
# ///
"""
ADR 0013 analysis — gate-verdict stability over the 15 frozen seeds.

This is the NEW analysis. It operates on sigma_init ONLY (the quantity
the criterion-validity gate operates on); it does not touch CTS, so it
does not read any gate-gated outcome.

It does TWO things:

(a) VARIANCE PARTITION between the two seed-batches:
    - descriptive between-seed spread of sigma_init across all 15,
    - the {6..10} vs {11..20} sigma_init scale comparison (the ~50%
      discrepancy), tested for equality-of-scale with a Brown-Forsythe
      / Levene test (median-centred Levene == Brown-Forsythe). Reports
      the test statistic and p-value as a descriptive scale-equality
      check, not a hypothesis "result" the paper claims.

(b) GATE-VERDICT RESAMPLING over the 15 seeds:
    - for resample sizes k in {5, 10, 15}, the distribution of
      gate_verdict().ratio and the PASS-rate (fraction of resamples
      with ratio >= 2.0),
    - exhaustive leave-k-out / choose-k where C(15, k) is tractable
      (<= EXHAUSTIVE_MAX combinations), bootstrap with B draws
      otherwise,
    - output per k: pass-rate, ratio quantiles, and the fraction of
      draws on each side of the 2.0 threshold.

DISCIPLINE BOUNDARY (ADR 0013, locked before data):
  This module must NOT be run on the real frozen summary and its
  verdict reported until the ADR 0013 pre-registration is approved and
  the run is explicitly triggered. The pre-registered decision bands
  (PASS-rate at k=5) live in docs/decisions/0013-gate-verdict-stability.md
  and are fixed BEFORE the real distribution is read. The CLI guards
  against accidental real-data execution (see --i-have-the-trigger).
  The function compute_distribution() is pure and is exercised by the
  synthetic smoke test in __main__ on SHUFFLED/synthetic sigma values.
"""

import argparse
import math
from itertools import combinations

import numpy as np
from scipy import stats

T = 0.0922
GATE_THRESHOLD = 2.0
RESAMPLE_K = (5, 10, 15)
EXHAUSTIVE_MAX = 10000   # use exhaustive choose-k if C(15,k) <= this
BOOTSTRAP_B = 10000
QUANTILES = (0.025, 0.25, 0.5, 0.75, 0.975)


# ---------------------------------------------------------------------------
# Pure analysis functions (no I/O, no real-data coupling)
# ---------------------------------------------------------------------------
def gate_ratio(sigmas: np.ndarray) -> float:
    """T / (median(sigma) * sqrt(2)) for a 1-D array of per-seed sigma_init."""
    sigma_diff = float(np.median(sigmas)) * math.sqrt(2)
    return T / sigma_diff


def variance_partition(sigma_orig: np.ndarray, sigma_esc: np.ndarray) -> dict:
    """Between-batch scale comparison + Brown-Forsythe (median-Levene)."""
    allv = np.concatenate([sigma_orig, sigma_esc])
    # Brown-Forsythe = Levene with center='median'.
    bf_stat, bf_p = stats.levene(sigma_orig, sigma_esc, center="median")
    return {
        "n_total": int(allv.size),
        "sigma_all_mean": float(np.mean(allv)),
        "sigma_all_sd": float(np.std(allv, ddof=1)),
        "sigma_all_min": float(np.min(allv)),
        "sigma_all_max": float(np.max(allv)),
        "median_orig": float(np.median(sigma_orig)),
        "median_esc": float(np.median(sigma_esc)),
        "ratio_of_medians_esc_over_orig": float(np.median(sigma_esc) / np.median(sigma_orig)),
        "brown_forsythe_W": float(bf_stat),
        "brown_forsythe_p": float(bf_p),
    }


def resample_ratios(sigmas: np.ndarray, k: int, rng: np.random.Generator,
                    exhaustive_max: int = EXHAUSTIVE_MAX,
                    bootstrap_b: int = BOOTSTRAP_B):
    """Raw gate-ratio array over resamples of size k. Returns (method, ratios).

    Exhaustive choose-k (without replacement) when C(n, k) <= exhaustive_max;
    otherwise bootstrap (with replacement) of `bootstrap_b` draws.
    k == n is the degenerate single-sample case (the full-set verdict).
    The exhaustive path is RNG-free and therefore fully deterministic — this is
    what makes the persisted k=5 distribution reproducible from the frozen CSV.
    """
    n = sigmas.size
    if k > n:
        raise ValueError(f"k={k} > n={n}")

    if k == n:
        return "full-set (single verdict)", np.array([gate_ratio(sigmas)])
    n_comb = math.comb(n, k)
    if n_comb <= exhaustive_max:
        return (f"exhaustive choose-k (C({n},{k})={n_comb})",
                np.array([gate_ratio(sigmas[list(idx)])
                          for idx in combinations(range(n), k)]))
    return (f"bootstrap (B={bootstrap_b}, with replacement)",
            np.array([gate_ratio(rng.choice(sigmas, size=k, replace=True))
                      for _ in range(bootstrap_b)]))


def resample_gate(sigmas: np.ndarray, k: int, rng: np.random.Generator,
                  exhaustive_max: int = EXHAUSTIVE_MAX,
                  bootstrap_b: int = BOOTSTRAP_B) -> dict:
    """Distribution summary of the gate ratio over resamples of size k."""
    method, ratios = resample_ratios(sigmas, k, rng, exhaustive_max, bootstrap_b)

    pass_mask = ratios >= GATE_THRESHOLD
    qs = np.quantile(ratios, QUANTILES)
    return {
        "k": k,
        "method": method,
        "n_draws": int(ratios.size),
        "pass_rate": float(np.mean(pass_mask)),
        "frac_at_or_above_2.0": float(np.mean(ratios >= GATE_THRESHOLD)),
        "frac_below_2.0": float(np.mean(ratios < GATE_THRESHOLD)),
        "ratio_quantiles": {f"q{int(q*1000)/10}": float(v) for q, v in zip(QUANTILES, qs)},
        "ratio_min": float(np.min(ratios)),
        "ratio_max": float(np.max(ratios)),
    }


def compute_distribution(sigma_orig, sigma_esc, seed: int = 0) -> dict:
    """Full ADR 0013 analysis output for given per-seed sigma_init arrays."""
    sigma_orig = np.asarray(sigma_orig, dtype=float)
    sigma_esc = np.asarray(sigma_esc, dtype=float)
    all_sigmas = np.concatenate([sigma_orig, sigma_esc])
    rng = np.random.default_rng(seed)
    return {
        "variance_partition": variance_partition(sigma_orig, sigma_esc),
        "resampling": {k: resample_gate(all_sigmas, k, rng) for k in RESAMPLE_K},
    }


# ---------------------------------------------------------------------------
# I/O + CLI guard
# ---------------------------------------------------------------------------
def _load_real_sigmas():
    """Read sigma_init from the frozen CSV, split by group. Real data —
    only used when the explicit trigger flag is passed."""
    import csv
    from pathlib import Path
    path = Path(__file__).parent / "seed_summary_frozen.csv"
    orig, esc = [], []
    with path.open() as f:
        for row in csv.DictReader(f):
            (orig if row["group"] == "original" else esc).append(float(row["sigma_init"]))
    return orig, esc


def persist_k5_distribution(sigmas: np.ndarray, path) -> tuple:
    """Write the exhaustive k=5 gate-ratio distribution (all C(15,5)=3003 draws)
    to `path` as CSV. This is the committed substrate Fig 4 reads from — the
    figure must come from a committed artefact, not a stdout number. The k=5
    exhaustive path is RNG-free, so the CSV is fully reproducible from the
    frozen summary. Returns (method, ratios)."""
    import csv
    rng = np.random.default_rng(0)  # unused on the exhaustive k=5 path
    method, ratios = resample_ratios(np.asarray(sigmas, dtype=float), 5, rng)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["draw_index", "ratio"])
        for i, r in enumerate(ratios):
            w.writerow([i, float(r)])
    return method, ratios


def _print_report(out: dict) -> None:
    vp = out["variance_partition"]
    print("=== Variance partition (sigma_init) ===")
    for k, v in vp.items():
        print(f"  {k}: {v}")
    print("\n=== Gate-verdict resampling ===")
    for k, r in out["resampling"].items():
        print(f"  k={k} [{r['method']}] draws={r['n_draws']} "
              f"pass_rate={r['pass_rate']:.4f} "
              f"below_2.0={r['frac_below_2.0']:.4f}")
        print(f"      ratio quantiles: {r['ratio_quantiles']}")


def _synthetic_sigmas(seed: int = 0):
    """Synthetic per-seed sigma_init for the smoke test — NOT the real
    frozen values. Drawn from two arbitrary log-normal-ish scales so the
    output schema and code paths are exercised without reading real data."""
    rng = np.random.default_rng(seed)
    orig = list(np.round(rng.uniform(0.015, 0.080, size=5), 6))
    esc = list(np.round(rng.uniform(0.020, 0.090, size=10), 6))
    return orig, esc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--i-have-the-trigger", action="store_true",
                   help="Run on the REAL frozen summary. Without this flag the "
                        "script refuses real data (ADR 0013 discipline boundary).")
    p.add_argument("--smoke-test", action="store_true",
                   help="Run on SYNTHETIC sigma values to verify code paths and "
                        "output schema. Reads no real data; reports no real verdict.")
    p.add_argument("--persist", metavar="PATH", default=None,
                   help="With --i-have-the-trigger: write the exhaustive k=5 "
                        "gate-ratio distribution (all C(15,5)=3003 draws) to PATH "
                        "as CSV. The committed substrate Fig 4 reads from.")
    args = p.parse_args()

    if args.smoke_test:
        orig, esc = _synthetic_sigmas(seed=0)
        print("[SMOKE TEST — synthetic sigma_init, NOT real frozen data]")
        print(f"  synthetic orig (n=5):  {orig}")
        print(f"  synthetic esc  (n=10): {esc}")
        print()
        out = compute_distribution(orig, esc, seed=0)
        _print_report(out)
        return

    if not args.i_have_the_trigger:
        raise SystemExit(
            "REFUSING to run on the real frozen summary without --i-have-the-trigger.\n"
            "ADR 0013's pre-registered decision bands must be locked and the run\n"
            "explicitly triggered first (circularity guard, ADR §2.3 lineage).\n"
            "For a code/schema check that reads no real data, use --smoke-test."
        )

    orig, esc = _load_real_sigmas()
    out = compute_distribution(orig, esc, seed=0)
    _print_report(out)

    if args.persist:
        all_sigmas = np.concatenate([np.asarray(orig, dtype=float),
                                     np.asarray(esc, dtype=float)])
        method, ratios = persist_k5_distribution(all_sigmas, args.persist)
        print(f"\n[PERSISTED] k=5 distribution ({method}) -> {args.persist}")
        print(f"  rows={ratios.size} "
              f"pass_rate(>=2.0)={float(np.mean(ratios >= GATE_THRESHOLD)):.4f} "
              f"median={float(np.median(ratios)):.4f}")


if __name__ == "__main__":
    main()
