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
    print()

    # PC1 and PC2 loadings: per-state weights, sorted by absolute value.
    # pca.components_ has shape (n_components, n_features); each row is a unit
    # eigenvector in the original 10-dim state-share basis. Sign is arbitrary
    # (PCA returns one of two valid orientations per axis).
    for pc_idx in (0, 1):
        comp = pca.components_[pc_idx]
        order = np.argsort(-np.abs(comp))
        print(f"PC{pc_idx + 1} loadings (sorted by |weight|, sign as returned by sklearn)")
        print(f"  {'state':<16} {'weight':>12}  {'|weight|':>12}")
        for j in order:
            print(f"  {STATE_ORDER[j]:<16} {comp[j]:>+12.6f}  {abs(comp[j]):>12.6f}")
        print()

    # ─── Pairwise distributional structure (KL-based MDS) ──────────────
    # Choice of symmetric divergence: Jensen-Shannon, not averaged-KL.
    # Rationale:
    # (1) JS is bounded (0, ln 2] in nats; averaged-KL is unbounded and
    #     blows up whenever one distribution puts near-zero mass on a state
    #     the other visits — both common here (e.g. ABSENT vs RESTING-heavy
    #     sessions). The unbounded tail of averaged-KL would dominate the
    #     pairwise matrix and the MDS spectrum, drowning structural signal.
    # (2) sqrt(JS) is a proper metric (Endres & Schindelin 2003), so
    #     classical MDS on D = sqrt(JS) has a well-defined geometric
    #     interpretation — eigenvalues of the double-centred Gram matrix
    #     read as squared embedding scales, with negative eigenvalues
    #     quantifying non-Euclidean residue.
    # (3) Numerically robust at the floor we use below.
    run_kl_mds(X)


def run_kl_mds(X: np.ndarray) -> None:
    n = X.shape[0]

    # Epsilon floor. The smallest non-zero share in this dataset is
    # 1 / max_ticks = 1/18000 ~ 5.6e-5. EPS = 1e-12 sits ~7 orders of
    # magnitude below that, so it prevents log(0) without perturbing the
    # observed distributional structure. After flooring we renormalise so
    # rows remain probability distributions (sum to 1).
    EPS = 1e-12
    P = X + EPS
    P = P / P.sum(axis=1, keepdims=True)
    print(f"KL-MDS preprocessing")
    print(f"  epsilon floor:    {EPS:.0e}")
    print(f"  smallest pre-floor non-zero share: {X[X > 0].min():.3e}")
    print(f"  rows renormalised to sum 1 after flooring")
    print()

    # Pairwise Jensen-Shannon divergence via broadcasting.
    # JS(P_i, P_j) = 0.5 * (KL(P_i || M) + KL(P_j || M)), M = (P_i + P_j)/2.
    # Memory: (n, n, k) doubles. For n=1000, k=10 → ~80 MB.
    Pi = P[:, None, :]
    Pj = P[None, :, :]
    M = 0.5 * (Pi + Pj)
    log_Pi = np.log(Pi)
    log_Pj = np.log(Pj)
    log_M = np.log(M)
    kl_im = np.sum(Pi * (log_Pi - log_M), axis=2)
    kl_jm = np.sum(Pj * (log_Pj - log_M), axis=2)
    JS = 0.5 * (kl_im + kl_jm)
    # Numerical hygiene: clip tiny negatives from FP cancellation, zero diagonal.
    JS = np.clip(JS, 0.0, None)
    np.fill_diagonal(JS, 0.0)

    # JS-distance (a true metric) for classical MDS.
    D = np.sqrt(JS)

    # JS-divergence sanity stats (off-diagonal).
    iu = np.triu_indices(n, k=1)
    js_off = JS[iu]
    print(f"Pairwise JS divergence (nats; theoretical max = ln 2 ≈ {np.log(2):.4f})")
    print(f"  pairs:        {js_off.size}")
    print(f"  min:          {js_off.min():.6e}")
    print(f"  median:       {np.median(js_off):.6e}")
    print(f"  mean:         {js_off.mean():.6e}")
    print(f"  max:          {js_off.max():.6e}")
    print()

    # Classical (Torgerson) MDS on D:
    #   B = -0.5 * H * D^2 * H,   H = I - (1/n) * 1 1^T
    # Eigenvalues of B are the squared scales of the embedding. For a true
    # Euclidean distance matrix, all eigenvalues are >= 0; negative
    # eigenvalues quantify how far D is from Euclidean-embeddable.
    D2 = D * D
    H = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * H @ D2 @ H
    # Force symmetry to absorb FP asymmetry.
    B = 0.5 * (B + B.T)
    eigvals_all = np.linalg.eigvalsh(B)  # ascending
    eigvals_all = eigvals_all[::-1]      # descending

    total_abs = np.abs(eigvals_all).sum()
    pos = eigvals_all[eigvals_all > 0]
    neg = eigvals_all[eigvals_all < 0]
    total_pos = pos.sum()
    total_neg_abs = (-neg).sum() if neg.size else 0.0

    print(f"Classical MDS on D = sqrt(JS) — eigenvalues of -0.5 H D^2 H (n={n})")
    print(f"  total positive mass:        {total_pos:.6e}")
    print(f"  total |negative| mass:      {total_neg_abs:.6e}")
    print(f"  negative / positive ratio:  {total_neg_abs / total_pos:.6e}")
    print(f"  count of negative eigvals:  {neg.size}")
    print()

    TOP = 20
    print(f"Top {TOP} eigenvalues")
    print(f"  {'k':>3}  {'eigenvalue':>14}  {'ratio(pos)':>12}  {'cum(pos)':>12}")
    cum = 0.0
    for k, lam in enumerate(eigvals_all[:TOP], start=1):
        ratio = lam / total_pos if lam > 0 else float('nan')
        if lam > 0:
            cum += ratio
        print(f"  {k:>3}  {lam:>+14.6e}  {ratio:>12.6f}  {cum:>12.6f}")
    print()

    # Coverage milestones over positive eigenvalues (which are the
    # ones with a geometric reading in classical MDS).
    pos_sorted = np.sort(pos)[::-1]
    pos_cum = np.cumsum(pos_sorted) / total_pos
    for thresh in (0.80, 0.90, 0.95, 0.99, 0.999):
        idx = int(np.searchsorted(pos_cum, thresh) + 1)
        print(f"  components for cum(pos) >= {thresh:.3f}: {idx}")
    print()

    # Participation ratio over positive eigenvalues.
    pr_pos = (pos.sum() ** 2) / (pos ** 2).sum()
    # Participation ratio over all eigenvalues (signed); using |lam|.
    pr_abs = (np.abs(eigvals_all).sum() ** 2) / (eigvals_all ** 2).sum()
    print(f"Participation ratio (positive eigvals only):  {pr_pos:.4f}")
    print(f"Participation ratio (|eigvals|, all {n}):       {pr_abs:.4f}")


if __name__ == "__main__":
    main()
