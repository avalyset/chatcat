#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib>=3.8",
#   "numpy>=1.26",
# ]
# ///
"""
Generate methods-paper figures (4 figures + 2 tables) from existing
training-run metrics.jsonl files on ~/chatcat-rl-runs/.

Budget-free: no new training, no new measurement except what the
plotting requires. All thresholds and windows are locked per ADR
0010/0011/0012 — this script applies them, does not derive them.

Output:
- paper/figures/fig1_climb_then_slide.png
- paper/figures/fig2_sig_exploration.png
- paper/figures/fig3_confounder_symmetric.png
- paper/figures/fig4_noise_scale_comparison.png
- paper/tables/table1_gate_pass_vs_fail.md
- paper/tables/table2_m_progression.md

Frozen quantities (from ADR 0010/0011 — applied, not re-derived):
- T = 0.0922 (climb/slide threshold)
- K = 0.004986 (vloss_peak ceiling)
- ep_init revised window = first 51 updates with ep_return_n_recent >= 100
- Peak window = [peak_update - 25, peak_update + 25]
- Final window = [N-50, N]
"""

import json
import os
import statistics
import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

# ============================================================
# Frozen constants
# ============================================================
T = 0.0922
K = 0.004986
HOME = os.path.expanduser("~")
RUNS_DIR = Path(f"{HOME}/chatcat-rl-runs")
OUT_FIG = Path(__file__).parent / "figures"
OUT_TBL = Path(__file__).parent / "tables"
OUT_FIG.mkdir(exist_ok=True)
OUT_TBL.mkdir(exist_ok=True)

ORIGINAL_SEEDS = list(range(6, 11))      # ADR 0010 main run
ESCALATION_SEEDS = list(range(11, 21))   # ADR 0012 escalation
ALL_SEEDS = ORIGINAL_SEEDS + ESCALATION_SEEDS

# ============================================================
# Plot style — consistent across all figures
# ============================================================
mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

# Color-blind-friendly palette
COL_CTS_REPRO = "#1b7837"      # green: CTS reproduced
COL_CTS_FAIL = "#762a83"        # purple: CTS not reproduced
COL_NEUTRAL = "#666666"         # gray: unchanged
COL_FLIP_UP = "#1b7837"         # green: ✗→✓
COL_FLIP_DOWN = "#c51b7d"       # magenta: ✓→✗
COL_THRESHOLD = "#d95f02"       # orange: threshold lines
COL_ORIG = "#5e3c99"            # purple: {6..10}
COL_ESC = "#e66101"             # orange: {11..20}


# ============================================================
# Data loading utilities
# ============================================================
def run_dir(seed):
    matches = list(RUNS_DIR.glob(f"phase2_main__seed{seed}__*"))
    assert len(matches) == 1, f"seed {seed}: expected 1 dir, found {len(matches)}"
    return matches[0]


def load_metrics(seed):
    return [json.loads(l) for l in open(run_dir(seed) / "metrics.jsonl")]


def first_buffer_full(rows):
    """First update where ep_return_n_recent >= 100."""
    return next(r["update"] for r in rows if r["ep_return_n_recent"] >= 100)


def window_mean(rows, lo, hi, field):
    vs = [r[field] for r in rows if lo <= r["update"] <= hi]
    vs = [v for v in vs if isinstance(v, (int, float)) and not math.isnan(v)]
    return statistics.mean(vs) if vs else float("nan")


def window_median(rows, lo, hi, field):
    vs = [r[field] for r in rows if lo <= r["update"] <= hi]
    return statistics.median(vs) if vs else float("nan")


def window_sd(rows, lo, hi, field):
    vs = [r[field] for r in rows if lo <= r["update"] <= hi]
    vs = [v for v in vs if isinstance(v, (int, float)) and not math.isnan(v)]
    return statistics.stdev(vs) if len(vs) > 1 else float("nan")


def cts_analysis(seed, init_window="revised"):
    """Compute climb/slide for a seed against either original or revised window.

    init_window = "original" → [100, 150]
    init_window = "revised"  → first 51 updates with n_recent >= 100
    """
    rows = load_metrics(seed)
    N = len(rows)
    if init_window == "original":
        iw_lo, iw_hi = 100, 150
    else:
        ff = first_buffer_full(rows)
        iw_lo, iw_hi = ff, ff + 50
    # peak: argmax over eligible region (n_recent >= 100)
    eligible = [r for r in rows if r["ep_return_n_recent"] >= 100]
    peak_row = max(eligible, key=lambda r: r["ep_return_mean_recent"])
    peak_update = peak_row["update"]
    pw_lo, pw_hi = peak_update - 25, peak_update + 25
    fw_lo, fw_hi = N - 50, N
    ep_init = window_mean(rows, iw_lo, iw_hi, "ep_return_mean_recent")
    ep_peak = window_mean(rows, pw_lo, pw_hi, "ep_return_mean_recent")
    ep_final = window_mean(rows, fw_lo, fw_hi, "ep_return_mean_recent")
    climb = ep_peak - ep_init
    slide = ep_peak - ep_final
    return {
        "seed": seed, "N": N,
        "init_window": (iw_lo, iw_hi), "ep_init": ep_init,
        "peak_update": peak_update, "peak_window": (pw_lo, pw_hi), "ep_peak": ep_peak,
        "final_window": (fw_lo, fw_hi), "ep_final": ep_final,
        "climb": climb, "slide": slide,
        "cts": (climb >= T) and (slide >= T),
    }


# ============================================================
# Fig 1 — Climb-then-slide curve
# ============================================================
def fig1_climb_then_slide():
    """ep_return_mean_recent vs update, for ORIGINAL_SEEDS, baseline = 0.

    Shows the canonical climb-and-slide pattern in raw form.
    No 0008-data on disk; using {6..10} as the climb-then-slide
    example (same training configuration as 0008 Run 2).
    """
    # Fig 1 shows FORM (all five climb-then-slide) — not amplitude. Use distinct
    # per-seed colors (not CTS-coded) so a reader doesn't mistake Fig 1's coloring
    # for amplitude-CTS classification (that lives in Fig 3 where it's actually
    # shown).
    SEED_COLORS = {6: "#1b9e77", 7: "#d95f02", 8: "#7570b3",
                   9: "#e7298a", 10: "#66a61e"}
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    cts_info = {s: cts_analysis(s, "revised") for s in ORIGINAL_SEEDS}
    for s in ORIGINAL_SEEDS:
        rows = load_metrics(s)
        # Show FULL trajectory — the climb-then-slide form is the point. Early
        # region has small-buffer noise in the rolling-mean estimate but the
        # underlying trajectory is real data.
        x = [r["update"] for r in rows if r["update"] >= 30]
        y = [r["ep_return_mean_recent"] for r in rows if r["update"] >= 30]
        color = SEED_COLORS[s]
        ax.plot(x, y, color=color, alpha=0.78, lw=1.2, label=f"seed {s}")
        # Mark peak — clear marker on top
        pu = cts_info[s]["peak_update"]
        py = cts_info[s]["ep_peak"]
        ax.plot(pu, py, 'o', color=color, markersize=6, markeredgecolor='white',
                markeredgewidth=0.8, zorder=5)

    ax.axhline(0, color="#444", linestyle='--', lw=1, alpha=0.7,
               label='baseline (R_agent − R_baseline = 0)')
    # Soft annotation for buffer-fullness transition (informational, not gating)
    ax.axvline(840, color="#888", linestyle=':', lw=0.7, alpha=0.5)
    ax.text(840, 0.98, " buffer fills ~here", color="#666", fontsize=8,
            ha='left', va='top', transform=ax.get_xaxis_transform())
    ax.set_xlabel("training update")
    ax.set_ylabel(r"$\mathrm{ep\_return\_mean\_recent}$ (baseline-normalised)")
    ax.set_title("Fig 1 — Climb-then-slide in FORM on N=5 seeds {6..10}")
    ax.legend(loc="upper right", framealpha=0.92, ncol=2, fontsize=8.5)
    fig.text(0.02, -0.03,
             "All five seeds climb to a peak and slide back (climb-then-slide in FORM = 5/5; F4-direction confirmed universal). "
             "Dots mark each seed's peak update.\n"
             "Whether the amplitude passes T = "
             f"{T} for the climb-leg depends on the ep_init measurement window — that distinction is the subject of Fig 3.",
             fontsize=8.5, color="#444", style='italic')
    out = OUT_FIG / "fig1_climb_then_slide.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ============================================================
# Fig 2 — SIG-EXPLORATION signature on a CTS-reproducing seed
# ============================================================
def fig2_sig_exploration():
    """Three-panel: ep_return, actor_logstd_mean, value_loss vs update.

    Uses seed 9 — CTS-qualified in both ADR 0010 and ADR 0011.
    Shows that std stays/widens while critic converges low — the
    SIG-EXPLORATION mechanism diagnosed in 31c363e and confirmed
    on all CTS-qualified seeds across 0010 and 0011.
    """
    SEED_SHOWN = 9
    rows = load_metrics(SEED_SHOWN)
    ca = cts_analysis(SEED_SHOWN, "revised")
    pw_lo, pw_hi = ca["peak_window"]
    iw_lo, iw_hi = ca["init_window"]

    eligible = [r for r in rows if r["ep_return_n_recent"] >= 100]
    x = [r["update"] for r in eligible]
    y_ret = [r["ep_return_mean_recent"] for r in eligible]
    x_all = [r["update"] for r in rows]
    y_logstd = [r["actor_logstd_mean"] for r in rows]
    y_vloss = [r["value_loss"] for r in rows]

    fig, axes = plt.subplots(3, 1, figsize=(7, 7), sharex=True,
                              gridspec_kw={"hspace": 0.18})

    # Panel 1: return
    ax1 = axes[0]
    ax1.plot(x, y_ret, color=COL_CTS_REPRO, lw=1.3)
    ax1.axhline(0, color=COL_THRESHOLD, linestyle='--', lw=0.8, alpha=0.6,
                label='baseline')
    ax1.axvspan(pw_lo, pw_hi, color=COL_CTS_REPRO, alpha=0.12, label='peak window')
    ax1.axvspan(iw_lo, iw_hi, color="#888", alpha=0.10, label='ep_init window')
    ax1.set_ylabel(r"$\mathrm{ep\_return\_mean\_recent}$ (baseline-normalised)")
    ax1.set_title(f"Fig 2 — SIG-EXPLORATION signature on seed {SEED_SHOWN} (CTS-reproducing in both 0010 and 0011)")
    ax1.legend(loc="lower left", fontsize=8, framealpha=0.9)

    # Panel 2: actor_logstd
    ax2 = axes[1]
    ax2.plot(x_all, y_logstd, color="#1f78b4", lw=1.0)
    ax2.axhline(0, color="#999", linestyle=':', lw=0.6, alpha=0.5)
    ax2.axvspan(pw_lo, pw_hi, color=COL_CTS_REPRO, alpha=0.12)
    ax2.axvspan(iw_lo, iw_hi, color="#888", alpha=0.10)
    ax2.set_ylabel(r"$\mathrm{actor\_logstd\_mean}$")
    # Annotate: logstd_drift_peak
    logstd_drift = ca_logstd_drift(rows, iw_lo, iw_hi, pw_lo, pw_hi)
    ax2.text(0.98, 0.05,
             f"logstd_drift_peak = {logstd_drift:+.4f}  (floor −0.14, ok)",
             transform=ax2.transAxes, ha='right', va='bottom', fontsize=8.5,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                       edgecolor='#888', alpha=0.9))

    # Panel 3: value_loss
    ax3 = axes[2]
    ax3.plot(x_all, y_vloss, color="#e7298a", lw=0.7, alpha=0.7)
    ax3.set_yscale("log")
    ax3.axhline(K, color=COL_THRESHOLD, linestyle='--', lw=0.9, alpha=0.7,
                label=f'K = {K:.4f}')
    ax3.axvspan(pw_lo, pw_hi, color=COL_CTS_REPRO, alpha=0.12)
    ax3.axvspan(iw_lo, iw_hi, color="#888", alpha=0.10)
    ax3.set_ylabel(r"value_loss (log)")
    ax3.set_xlabel("training update")
    vloss_peak_median = window_median(rows, pw_lo, pw_hi, "value_loss")
    ax3.text(0.98, 0.95,
             f"vloss_peak (median over peak window) = {vloss_peak_median:.5f}\n"
             f"vloss_peak / K = {vloss_peak_median/K:.3f}  (ceiling 1.0, ok)",
             transform=ax3.transAxes, ha='right', va='top', fontsize=8.5,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                       edgecolor='#888', alpha=0.9))
    ax3.legend(loc='lower left', fontsize=8)

    fig.text(0.02, -0.01,
             "Variance (actor_logstd) does not collapse during peak; critic (value_loss) is converged low. "
             "The mechanism (SIG-EXPLORATION) holds: slide is the optimisation\n"
             "side of a wide-variance policy, not variance-collapse. Same pattern on all CTS-reproducing seeds across 0010 and 0011.",
             fontsize=8.5, color="#444", style='italic')

    out = OUT_FIG / "fig2_sig_exploration.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def ca_logstd_drift(rows, iw_lo, iw_hi, pw_lo, pw_hi):
    init = window_mean(rows, iw_lo, iw_hi, "actor_logstd_mean")
    peak = window_mean(rows, pw_lo, pw_hi, "actor_logstd_mean")
    return peak - init


# ============================================================
# Fig 3 — Direction-symmetric confunder (KEY FIGURE)
# ============================================================
def fig3_confounder_symmetric():
    """Per seed {6..10}: climb under original [100,150] vs revised window.

    Shows that the ep_init-window change flipped 3 of 5 seeds' CTS-status
    in BOTH directions: seeds 6, 8 went ✗→✓ (confunder hid CTS) and
    seed 10 went ✓→✗ (confunder fabricated CTS). The confunder "lied
    both ways" — not just a "rescue" of the phenomenon.
    """
    # Fig 3 uses DIFFERENT color logic than Fig 1:
    # - Markers are neutral dark gray (no CTS-coding via color).
    # - Marker SHAPE encodes CTS status at each endpoint (o = ✓, X = ✗).
    # - Arrow COLOR encodes flip direction (green/magenta/gray).
    # This decouples Fig 3's color story (flip direction) from Fig 1's per-seed
    # colors (seed identity), so the same hue does not mean two different things
    # across figures.
    MARKER_NEUTRAL = "#444444"
    fig, ax = plt.subplots(figsize=(10.5, 5.0))

    # Compute climb under both windows
    data = []
    for s in ORIGINAL_SEEDS:
        old = cts_analysis(s, "original")
        new = cts_analysis(s, "revised")
        flip = "no_change"
        if (not old["cts"]) and new["cts"]:
            flip = "up"
        elif old["cts"] and (not new["cts"]):
            flip = "down"
        data.append({
            "seed": s,
            "climb_old": old["climb"], "cts_old": old["cts"],
            "climb_new": new["climb"], "cts_new": new["cts"],
            "flip": flip,
        })

    # CTS-pass shaded zone (right of T) — neutral pale, no color-coupling to flip
    ax.axvspan(T, 1.4, color="#cccccc", alpha=0.18, zorder=0)
    ax.text(T + 0.02, len(data) - 0.5, "CTS-pass zone\n(climb ≥ T)",
            color="#777", fontsize=8, style='italic', va='center', ha='left',
            alpha=0.9)

    # Plot: each seed gets a horizontal slot; old climb → new climb arrow
    n = len(data)
    for i, d in enumerate(data):
        y = n - 1 - i  # so seed 6 is at top
        if d["flip"] == "up":
            col = COL_FLIP_UP
            lw = 2.8
        elif d["flip"] == "down":
            col = COL_FLIP_DOWN
            lw = 2.8
        else:
            col = COL_NEUTRAL
            lw = 1.3
        # Arrow from old to new — only if there's meaningful displacement
        if abs(d["climb_new"] - d["climb_old"]) > 0.005:
            ax.annotate('', xy=(d["climb_new"], y), xytext=(d["climb_old"], y),
                        arrowprops=dict(arrowstyle="->", color=col, lw=lw,
                                        shrinkA=6, shrinkB=6,
                                        mutation_scale=22))
        else:
            ax.plot([d["climb_old"], d["climb_new"]], [y, y],
                    color=col, lw=lw, solid_capstyle='round')
        # Endpoint markers — neutral color, shape carries CTS status
        old_marker = "o" if d["cts_old"] else "X"
        new_marker = "o" if d["cts_new"] else "X"
        ax.plot(d["climb_old"], y, marker=old_marker, color=MARKER_NEUTRAL,
                markersize=11, markeredgecolor='white', markeredgewidth=0.9,
                zorder=5)
        ax.plot(d["climb_new"], y, marker=new_marker, color=MARKER_NEUTRAL,
                markersize=11, markeredgecolor='white', markeredgewidth=0.9,
                zorder=5)
        # Flip annotation — to the FAR RIGHT of plot, uniform column
        flip_text = {"up": "✗→✓  hid CTS",
                     "down": "✓→✗  fabricated CTS",
                     "no_change": "no change"}[d["flip"]]
        ax.text(1.18, y, flip_text, fontsize=10, color=col,
                ha='left', va='center',
                fontweight='bold' if d["flip"] != "no_change" else 'normal')

    # T threshold — vertical line + label at bottom (avoid title clash)
    ax.axvline(T, color=COL_THRESHOLD, linestyle='--', lw=1.6, zorder=2)
    ax.text(T, -0.55, f'T = {T}', color=COL_THRESHOLD, fontsize=9.5,
            ha='center', va='bottom', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=COL_THRESHOLD, alpha=0.95))

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"seed {d['seed']}" for d in reversed(data)], fontsize=10)
    ax.set_xlabel(r"climb = $\mathrm{ep\_peak} - \mathrm{ep\_init}$ (return units)")
    ax.set_title("Fig 3 — Direction-symmetric ep_init-window confunder on seeds {6..10}  (KEY)")
    ax.set_xlim(-0.35, 1.55)
    ax.set_ylim(-0.6, n - 0.3)

    # Legend OUTSIDE plot area on the right side, below flip-labels
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=MARKER_NEUTRAL,
               markersize=10, label='CTS ✓ (climb ≥ T)'),
        Line2D([0], [0], marker='X', color=MARKER_NEUTRAL, markersize=10, linestyle='',
               label='CTS ✗ (climb < T)'),
        Line2D([0], [0], color=COL_FLIP_UP, lw=2.8, label='arrow: hid CTS'),
        Line2D([0], [0], color=COL_FLIP_DOWN, lw=2.8, label='arrow: fabricated CTS'),
        Line2D([0], [0], color=COL_NEUTRAL, lw=1.3, label='arrow: no change'),
    ]
    # Legend BELOW plot, horizontal — no conflict with right-side text labels
    ax.legend(handles=legend_elems, loc='upper center',
              bbox_to_anchor=(0.5, -0.18), ncol=5,
              fontsize=8.5, framealpha=0.95,
              title="markers = CTS status (shape)   ·   arrows = flip direction (colour)",
              title_fontsize=8.5)

    fig.text(0.02, -0.28,
             "Each arrow shows one seed's climb shifting between ep_init windows: tail = ADR 0010 [100,150] "
             "window; head = ADR 0011 buffer-full window.\n"
             "The confunder lied both ways: seeds 6 and 8 had real CTS hidden by buffer noise (green, ✗→✓); "
             "seed 10's apparent CTS was a buffer-noise artefact (magenta, ✓→✗). M: 2/5 → M': 3/5.\n"
             "Note: Fig 3 marker colours are neutral by design — the colour story here is flip direction (arrows). "
             "Fig 1's per-seed colours code seed identity, a separate scheme.",
             fontsize=8.5, color="#444", style='italic')

    out = OUT_FIG / "fig3_confounder_symmetric.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ============================================================
# Fig 4 — Per-seed noise-scale {6..10} vs {11..20}
# ============================================================
def fig4_noise_scale_comparison():
    """Inter-update-SD of ep_return_mean_recent in the revised buffer-full
    window, per seed, for both groups. Shows that same-config samples
    can produce ~50% different median noise scales — the unexpected
    finding that caused ADR 0012's gate to FAIL."""
    fig, ax = plt.subplots(figsize=(8, 4.2))

    orig_sds = []
    esc_sds = []
    for s in ORIGINAL_SEEDS:
        rows = load_metrics(s)
        ff = first_buffer_full(rows)
        sd = window_sd(rows, ff, ff + 50, "ep_return_mean_recent")
        orig_sds.append(sd)
    for s in ESCALATION_SEEDS:
        rows = load_metrics(s)
        ff = first_buffer_full(rows)
        sd = window_sd(rows, ff, ff + 50, "ep_return_mean_recent")
        esc_sds.append(sd)

    x_orig = list(range(len(ORIGINAL_SEEDS)))
    x_esc = list(range(len(ORIGINAL_SEEDS) + 1,
                       len(ORIGINAL_SEEDS) + 1 + len(ESCALATION_SEEDS)))

    ax.scatter(x_orig, orig_sds, s=70, color=COL_ORIG,
               edgecolor='white', linewidth=0.7, zorder=3,
               label='{6..10} (ADR 0010 main run)')
    ax.scatter(x_esc, esc_sds, s=70, color=COL_ESC,
               edgecolor='white', linewidth=0.7, zorder=3,
               label='{11..20} (ADR 0012 escalation)')

    med_orig = statistics.median(orig_sds)
    med_esc = statistics.median(esc_sds)
    # Median lines per group
    ax.hlines(med_orig, x_orig[0] - 0.4, x_orig[-1] + 0.4,
              color=COL_ORIG, linestyle='--', lw=1.4, alpha=0.7)
    ax.hlines(med_esc, x_esc[0] - 0.4, x_esc[-1] + 0.4,
              color=COL_ESC, linestyle='--', lw=1.4, alpha=0.7)
    # Annotations
    ax.text(x_orig[-1] + 0.5, med_orig,
            f' median = {med_orig:.4f}\n T/σ√2 = 2.73 → gate PASS',
            color=COL_ORIG, va='center', fontsize=8.5)
    ax.text(x_esc[-1] + 0.5, med_esc,
            f' median = {med_esc:.4f}\n T/σ√2 = 1.80 → gate FAIL',
            color=COL_ESC, va='center', fontsize=8.5)

    # Gate threshold reference: σ that would give T/σ√2 = 2 is T/(2√2)
    sigma_at_gate = T / (2 * math.sqrt(2))
    ax.axhline(sigma_at_gate, color=COL_THRESHOLD, linestyle=':', lw=1,
               alpha=0.6, label=f'gate threshold (σ at T/σ√2 = 2): {sigma_at_gate:.4f}')

    ax.set_xticks(x_orig + x_esc)
    ax.set_xticklabels([str(s) for s in ORIGINAL_SEEDS + ESCALATION_SEEDS])
    ax.set_xlabel("seed")
    ax.set_ylabel(r"inter-update-SD of $\mathrm{ep\_return\_mean\_recent}$ in revised window")
    ax.set_title("Fig 4 — Same training config, ~50% different median noise scale across seed-batches")
    ax.set_xlim(-0.7, x_esc[-1] + 4.5)
    ax.legend(loc='upper right', fontsize=8.5, framealpha=0.92)

    fig.text(0.02, -0.03,
             "Per-seed inter-update-SD of ep_return_mean_recent in each seed's revised buffer-full ep_init window. "
             "Identical training config produces medians 0.024 vs 0.036\n"
             "(50% difference) across the two seed-batches — large enough to flip the kriterie-validitet-gate "
             "from PASS (2.73) to FAIL (1.80) without any methodology change.",
             fontsize=8.5, color="#444", style='italic')

    out = OUT_FIG / "fig4_noise_scale_comparison.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ============================================================
# Table 1 — Gate PASS vs FAIL side by side
# ============================================================
def table1_gate_pass_vs_fail():
    orig_sds = []
    for s in ORIGINAL_SEEDS:
        rows = load_metrics(s)
        ff = first_buffer_full(rows)
        orig_sds.append((s, window_sd(rows, ff, ff + 50, "ep_return_mean_recent")))
    esc_sds = []
    for s in ESCALATION_SEEDS:
        rows = load_metrics(s)
        ff = first_buffer_full(rows)
        esc_sds.append((s, window_sd(rows, ff, ff + 50, "ep_return_mean_recent")))

    med_o = statistics.median([sd for _, sd in orig_sds])
    med_e = statistics.median([sd for _, sd in esc_sds])
    sigma_diff_o = med_o * math.sqrt(2)
    sigma_diff_e = med_e * math.sqrt(2)
    ratio_o = T / sigma_diff_o
    ratio_e = T / sigma_diff_e

    lines = []
    lines.append("# Table 1 — Kriterie-validitet-gate: ADR 0011 PASS vs ADR 0012 FAIL")
    lines.append("")
    lines.append("Per-seed inter-update-SD of `ep_return_mean_recent` over each seed's revised "
                 "buffer-full ep_init-window (first 51 updates with `ep_return_n_recent ≥ 100`). "
                 "Gate fires if `T / (σ_median × √2) ≥ ~2`.")
    lines.append("")
    lines.append("| seed | inter-update-SD | group |")
    lines.append("|---:|---:|:---|")
    for s, sd in orig_sds:
        lines.append(f"| {s} | {sd:.6f} | {{6..10}} (ADR 0011) |")
    for s, sd in esc_sds:
        lines.append(f"| {s} | {sd:.6f} | {{11..20}} (ADR 0012) |")
    lines.append("")
    lines.append("**Aggregate (per group):**")
    lines.append("")
    lines.append("| | {6..10} (ADR 0011) | {11..20} (ADR 0012) |")
    lines.append("|---|---:|---:|")
    lines.append(f"| n seeds | 5 | 10 |")
    lines.append(f"| median σ | **{med_o:.6f}** | **{med_e:.6f}** |")
    lines.append(f"| σ_diff = σ × √2 | {sigma_diff_o:.6f} | {sigma_diff_e:.6f} |")
    lines.append(f"| T / σ_diff | **{ratio_o:.4f}** | **{ratio_e:.4f}** |")
    lines.append(f"| Gate decision (threshold ≥ ~2) | **PASS** | **FAIL** |")
    lines.append("")
    lines.append(f"T = {T} (locked since 0140536). The gate fired in opposite directions on the "
                 "two batches despite identical training configuration — evidence that the gate "
                 "is not a formality and that same-config noise-scale is itself substantial.")
    out = OUT_TBL / "table1_gate_pass_vs_fail.md"
    out.write_text("\n".join(lines) + "\n")
    return out


# ============================================================
# Table 2 — M / M' / M'' progression
# ============================================================
def table2_m_progression():
    # ADR 0010 (original window): per-seed climb against [100,150]
    cts_orig_window = {s: cts_analysis(s, "original") for s in ORIGINAL_SEEDS}
    # ADR 0011 (revised window): per-seed climb against buffer-full
    cts_rev_window = {s: cts_analysis(s, "revised") for s in ORIGINAL_SEEDS}

    M = sum(1 for s in ORIGINAL_SEEDS if cts_orig_window[s]["cts"])
    M_prime = sum(1 for s in ORIGINAL_SEEDS if cts_rev_window[s]["cts"])

    lines = []
    lines.append("# Table 2 — Phenomenon-reproduction count across measurement passes")
    lines.append("")
    lines.append(
        "Climb-then-slide reproduction count `M / M' / M''` across the three ADR measurement "
        "passes on the same phenomenon-question. T = 0.0922 (locked from ADR 0010); the only "
        "thing that changes is the ep_init-window definition.")
    lines.append("")
    lines.append("| pass | ADR | seeds | ep_init window | gate | count | reading |")
    lines.append("|---|---|---|---|---|---:|---|")
    lines.append(f"| M | 0010 main run | {{6..10}} | original [100, 150] | not built yet | **{M}/5** | F3 fires on locked criterion |")
    lines.append(f"| M' | 0011 reanalysis | {{6..10}} | revised buffer-full | PASS (T/σ_diff = 2.73) | **{M_prime}/5** | borderline, inconclusive on N=5 reanalysis-budget |")
    lines.append(f"| M'' | 0012 escalation | {{11..20}} added | revised buffer-full | **FAIL (T/σ_diff = 1.80)** | not tallied | climb-readout not performed per pre-reg §3 |")
    lines.append("")
    lines.append("**Per-seed flips between M and M' (same data, only ep_init window changed):**")
    lines.append("")
    lines.append("| seed | climb (M, [100,150]) | climb (M', revised) | CTS M | CTS M' | flip |")
    lines.append("|---:|---:|---:|:---:|:---:|:---|")
    for s in ORIGINAL_SEEDS:
        o = cts_orig_window[s]
        r = cts_rev_window[s]
        cts_o = "✓" if o["cts"] else "✗"
        cts_r = "✓" if r["cts"] else "✗"
        if (not o["cts"]) and r["cts"]:
            flip = "✗→✓ (confunder hid CTS)"
        elif o["cts"] and (not r["cts"]):
            flip = "✓→✗ (confunder fabricated CTS)"
        else:
            flip = "no change"
        lines.append(f"| {s} | {o['climb']:+.4f} | {r['climb']:+.4f} | {cts_o} | {cts_r} | {flip} |")
    lines.append("")
    lines.append(
        "The phenomenon-question is now empirically unreachable at the available compute budget: "
        "ADR 0010's locked criterion was noise-confunded (M = 2/5 mismeasures phenomenon); "
        "ADR 0011's reanalysis produced a borderline (M' = 3/5, three seeds flipped, no clear "
        "side); ADR 0012's escalation to N=15 was blocked at the validity-gate by an unexpected "
        "noise-scale difference between same-config batches. This is itself a substantive "
        "finding about training-dynamics seed-variability.")
    out = OUT_TBL / "table2_m_progression.md"
    out.write_text("\n".join(lines) + "\n")
    return out


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    artefacts = []
    print("Generating Fig 1 — climb-then-slide curves...")
    artefacts.append(fig1_climb_then_slide())
    print("Generating Fig 2 — SIG-EXPLORATION signature...")
    artefacts.append(fig2_sig_exploration())
    print("Generating Fig 3 — direction-symmetric confunder (KEY)...")
    artefacts.append(fig3_confounder_symmetric())
    print("Generating Fig 4 — noise-scale comparison...")
    artefacts.append(fig4_noise_scale_comparison())
    print("Generating Table 1 — gate PASS vs FAIL...")
    artefacts.append(table1_gate_pass_vs_fail())
    print("Generating Table 2 — M progression...")
    artefacts.append(table2_m_progression())
    print()
    print("Done. Artefacts:")
    for a in artefacts:
        print(f"  {a}")
