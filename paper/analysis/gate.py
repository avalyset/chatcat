#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
Runnable criterion-validity gate + CTS tally over the frozen seed summary.

Re-instates the gate/tally logic removed from the plotting script in
commit 01d79d2 — but as PURE functions reading the committed
paper/analysis/seed_summary_frozen.csv, not regenerating any figure or
table. This is the in-repo, reproducible form of the gate the ADR
0011/0012 resolutions report.

Frozen constants (ADR 0010/0011 — applied, not derived):
- T = 0.0922 (climb/slide threshold).
- gate threshold = 2.0  (T / sigma_diff must be >= 2.0 to PASS).
- sigma_diff = median(per-seed sigma_init) * sqrt(2).

Functions:
- tally_M(seeds)      -> int    (sum of CTS over a seed subset)
- gate_verdict(seeds) -> dict   (sigma_init_median, sigma_diff, ratio, passed)

CTS gating: tally_M refuses to tally any seed whose CTS is the
"gate-gated" sentinel (ADR 0012 gate-STOP). gate_verdict uses sigma_init
only and is therefore defined on every subset, including {11..20}.
"""

import csv
import math
from pathlib import Path

T = 0.0922
GATE_THRESHOLD = 2.0
CTS_GATED_SENTINEL = "gate-gated"

FROZEN_CSV = Path(__file__).parent / "seed_summary_frozen.csv"


def load_frozen(csv_path: Path = FROZEN_CSV) -> dict[int, dict]:
    """Load the frozen per-seed summary keyed by seed int."""
    out: dict[int, dict] = {}
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            out[int(row["seed"])] = row
    return out


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty sequence")
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def tally_M(seeds, frozen: dict[int, dict] | None = None) -> int:
    """Sum of CTS booleans over `seeds`.

    Raises ValueError if any requested seed's CTS is the gate-gated
    sentinel — by ADR 0012's gate-STOP, those outcomes were never
    computed and must not be silently treated as 0 or read at all.
    """
    frozen = frozen if frozen is not None else load_frozen()
    total = 0
    for s in seeds:
        cts = frozen[s]["cts"]
        if cts == CTS_GATED_SENTINEL:
            raise ValueError(
                f"seed {s}: CTS is gate-gated (ADR 0012 gate-STOP). "
                f"Refusing to tally a gated outcome. Resolve ADR 0013 first."
            )
        total += 1 if cts == "True" else 0
    return total


def gate_verdict(seeds, frozen: dict[int, dict] | None = None) -> dict:
    """Criterion-validity gate verdict over `seeds`.

    Uses sigma_init only (the quantity the gate operates ON); does not
    touch CTS, so it is defined on every subset.
    """
    frozen = frozen if frozen is not None else load_frozen()
    sigmas = [float(frozen[s]["sigma_init"]) for s in seeds]
    sigma_median = _median(sigmas)
    sigma_diff = sigma_median * math.sqrt(2)
    ratio = T / sigma_diff
    return {
        "n_seeds": len(seeds),
        "sigma_init_median": sigma_median,
        "sigma_diff": sigma_diff,
        "ratio": ratio,
        "passed": ratio >= GATE_THRESHOLD,
    }


if __name__ == "__main__":
    frozen = load_frozen()
    for label, subset in [
        ("original {6..10}", [6, 7, 8, 9, 10]),
        ("escalation {11..20}", list(range(11, 21))),
    ]:
        v = gate_verdict(subset, frozen)
        print(f"{label}: ratio={v['ratio']:.4f} "
              f"({'PASS' if v['passed'] else 'FAIL'}), "
              f"sigma_median={v['sigma_init_median']:.6f}")
    print(f"tally_M {{6..10}} = {tally_M([6, 7, 8, 9, 10], frozen)}")
