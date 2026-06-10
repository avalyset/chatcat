# arXiv Submission Metadata

This file holds the fields Eirik will paste into the arXiv submission form.
Source-of-truth: `paper/sections/*-en.md` + `paper/chatcat-methods-preprint-draft-en.md`
on commit `13b8889` (origin/main).

---

## Title (Eirik picks one — three candidates, lead with the evaluation method)

1. **A Criterion-Validity Gate for Threshold-Based Reproducibility Assessment in RL** *(recommended — direct, names the contribution, mirrors §1.3)*
2. **Pre-Registration Is Not Enough: Gating Thresholds Against Application-Window Noise**
3. **When Measurability Is Seed-Variable: A Pre-Registration Discipline for RL Evaluation Under Noise-Dominated Thresholds**

Selected: `[PLACEHOLDER — Eirik to mark]`

---

## Authors

- **Name:** Eirik Botten Nicolaysen
- **Affiliation:** EcoDeco AS  `[PLACEHOLDER — Eirik to confirm exact affiliation string]`
- **Email:** `[PLACEHOLDER — Eirik to fill]`
- **ORCID:** `[PLACEHOLDER — Eirik to fill or mark "not applicable"]`
- **Co-authors:** `[PLACEHOLDER — Eirik to confirm none or list]`

---

## Abstract (plain text, arXiv-form-ready, copied verbatim from `00-abstract-en.md`)

```
RL agents are evaluated against thresholds that are rarely validated against the noise inside their own measurement window. A threshold can be meaningful against the outcome span and at the same time noise-dominated in the window where it is actually applied — and when that happens, an apparently clean result is a measurement artefact. Which seeds pass is closer to a coin flip than to a finding.

We pre-registered an evaluation of an RL agent against an ethological simulator in an ACI (animal-computer interaction) context, and introduced a criterion-validity gate: a check, registered together with the methodology, that verifies the threshold is separable from the noise in its application window before it is applied. The gate changed the outcome in three documented cases. A climb-leg was being measured against a window where the noise sat at roughly 10x the threshold — an inconsistency we had built in ourselves. The measurement window turned out to be direction-symmetric: it hid the observed phenomenon on some seeds and fabricated it on others. And on escalation, the gate failed on a fresh seed batch because the noise scale was roughly 50% higher under identical configuration.

The last result is the point. The phenomenon could not be decided as robust or not-robust on attainable compute — not for lack of data, but because measurability itself is seed-variable, at a level deeper than the phenomenon. The contribution is the method that made that refusal pre-registered and visible instead of producing a false clean number. Wherever a reproducibility threshold risks sitting inside the noise of the window it is applied to — a common case in RL evaluation — gate-protected pre-registration is the infrastructure that lets pre-registration deliver what it promises: honest assessment instead of clean-looking artefacts.
```

Note: arXiv abstract field accepts plain text only (no LaTeX commands except `\(...\)` math). Em-dashes are fine. The `10x` was converted from Unicode `×` since not all arXiv input fields handle Unicode reliably; double-check on submission form.

---

## arXiv Categories

### Primary: `cs.LG` (Machine Learning)

**Justification:** The paper's contribution is a methodological gate for RL evaluation — a check that verifies thresholds are separable from noise in their application window. The empirical content is RL training (PPO over a continuous action space) and the analysis is reproducibility-threshold methodology. Fits cs.LG's scope of "all aspects of machine learning research."












---

## MSC / ACM Classification

- **MSC 2020:** Not strictly required for arXiv. If filling: `68T05` (Learning and adaptive systems in artificial intelligence) or `68T07` (Artificial neural networks and deep learning).
- **ACM CCS (2012):** Not required. If filling: `Computing methodologies → Machine learning → Reinforcement learning`.

Skip unless the submission form requests explicitly.

---

## Comments field (arXiv "Comments" — visible on listing)

Draft text:

```
20 pages, 4 figures, 2 tables. Reproducible code, ADR chain, and figure-generation scripts available at the project repository (link to be added at submission).
```

Update page count after compilation (current LaTeX estimate: ~12-15 pages with current figure sizing — verify by compiling locally).

---

## License (Eirik to choose at arXiv submission)

arXiv requires a license selection. Two reasonable options:

1. **arXiv non-exclusive license** (default): permissive for arXiv distribution, you retain copyright, can submit to journals/conferences later.
2. **CC BY 4.0**: permissive open licence, allows reuse with attribution. Recommended if you want the methodology gate to be readily reusable.

Recommended: **CC BY 4.0** — the gate methodology is the contribution, and a permissive license maximises uptake. Eirik decides.

---

## Files to upload to arXiv

```
chatcat-methods.tex
refs.bib
figures/fig1_climb_then_slide.pdf
figures/fig2_sig_exploration.pdf
figures/fig3_confounder_symmetric.pdf
figures/fig4_noise_scale_comparison.pdf
```

Total: 6 files (1 .tex, 1 .bib, 4 figures). arXiv accepts these as a single .tar.gz or .zip upload, or as individual files via the web form. arXiv will run pdflatex + bibtex on the source.

---

## Post-acceptance / future-update notes

- If a follow-on paper (ADR 0013 path or similar) addresses the noise-scale discrepancy from N=15 escalation, link from arXiv as a new version (v2) or as a related submission.
- Project repository URL goes in the Comments field once Eirik confirms the public-facing repo address (currently `https://github.com/avalyset/chatcat.git` — confirm whether to use that or a release-tagged URL).
