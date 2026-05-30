#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26", "scikit-learn>=1.4"]
# ///
"""
ADR 0006 continuous PCA — raw state-share fractions.

Reads a continuous_v1 JSONL (one _meta header line, then N continuous_v1
session records) and runs PCA on the 10-dimensional state_shares vector.

Pipeline contract:
- No standardisation (no per-feature scaling to unit variance).
- No CLR (centred log-ratio) transform.
- PCA's default mean-centring is applied (subtract column means before SVD);
  this is a translation, not a scaling, and is required for the eigenvalues
  to reflect variance rather than second moments.
- n_components=10 with svd_solver='full' to get the full spectrum, including
  the trailing eigenvalue that the compositional sum-to-1 constraint forces
  to zero (rank deficiency: state_shares lives on the 9-simplex).

Outputs:
- explained_variance_ratio_ for all 10 components
- cumulative sum
- participation ratio PR = (sum lambda)^2 / sum(lambda^2)

Usage:
  uv run scripts/analyse-continuous.py <path-to-continuous.jsonl>
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

# Canonical state ordering used by litterbox/src/cli/batch.ts ALL_STATES.
# This MUST match the JSONL writer's order so the PCA loadings are
# interpretable against the ethogram.
STATE_ORDER = [
    "ABSENT", "RESTING", "ALERT", "CURIOUS", "APPROACHING",
    "ENGAGING", "OVERSTIMULATED", "STRESSED", "RETREATING", "LEAVING",
]


def load_jsonl(path: Path):
    meta = None
    records = []
    with path.open() as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            schema = row.get("schema")
            if schema == "continuous_v1_meta":
                if meta is not None:
                    raise ValueError("Multiple _meta header lines found.")
                meta = row
            elif schema == "continuous_v1":
                records.append(row)
            else:
                raise ValueError(f"Unknown schema: {schema!r}")
    if meta is None:
        raise ValueError("No continuous_v1_meta header line found.")
    return meta, records


def build_matrix(records):
    X = np.zeros((len(records), len(STATE_ORDER)), dtype=np.float64)
    for i, r in enumerate(records):
        shares = r["state_shares"]
        for j, s in enumerate(STATE_ORDER):
            X[i, j] = shares[s]
    return X


def main():
    if len(sys.argv) != 2:
        print("Usage: analyse-continuous.py <continuous.jsonl>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    meta, records = load_jsonl(path)
    X = build_matrix(records)

    row_sums = X.sum(axis=1)
    max_row_dev = float(np.max(np.abs(row_sums - 1.0)))

    print("Input")
    print(f"  file:               {path}")
    print(f"  master_seed:        {meta['master_seed']}")
    print(f"  samples (meta):     {meta['samples']}")
    print(f"  records (read):     {len(records)}")
    print(f"  habituation_rate:   {meta['habituation_rate']}")
    print(f"  max_ticks:          {meta['max_ticks']}")
    print(f"  matrix shape:       {X.shape}")
    print(f"  max |row_sum - 1|:  {max_row_dev:.2e}")
    print()

    pca = PCA(n_components=10, svd_solver="full")
    pca.fit(X)

    eigvals = pca.explained_variance_
    evr = pca.explained_variance_ratio_
    cum = np.cumsum(evr)

    print("PCA spectrum (raw fractions, mean-centred, no scaling, no CLR)")
    print(f"  {'k':>3}  {'eigenvalue':>14}  {'ratio':>12}  {'cumulative':>12}")
    for k, (lam, r, c) in enumerate(zip(eigvals, evr, cum), start=1):
        print(f"  {k:>3}  {lam:>14.6e}  {r:>12.6f}  {c:>12.6f}")
    print()

    total = eigvals.sum()
    sq = (eigvals ** 2).sum()
    pr = (total ** 2) / sq
    print(f"Participation ratio  PR = (sum lambda)^2 / sum(lambda^2) = {pr:.4f}")
    print()

    last_lam = eigvals[-1]
    last_ratio = evr[-1]
    top_lam = eigvals[0]
    print("Rank check (state_shares sums to 1 -> mathematical rank <= 9)")
    print(f"  lambda_10:            {last_lam:.6e}")
    print(f"  ratio_10:             {last_ratio:.6e}")
    print(f"  lambda_10 / lambda_1: {last_lam / top_lam:.6e}")


if __name__ == "__main__":
    main()
