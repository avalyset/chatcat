# arXiv Submission Checklist

The final submit-button is Eirik's. This list walks the manual steps and flags potential blockers. The package itself is built (LaTeX + bib + vector figures + metadata draft in this directory); what remains is the human action on arxiv.org.

---

## Blocker check — endorsement (resolve BEFORE upload)

**arXiv cs.LG requires endorsement for first-time submitters.**

If this is Eirik's first arXiv submission in `cs.*`:

- Check status at `https://arxiv.org/auth/endorse` after logging in to arXiv account
- If endorsement is required:
  1. Identify a potential endorser — someone who has previously submitted to `cs.LG` recently (within the last 3 years) and has at least the minimum endorser eligibility (typically 2+ cs.LG submissions accepted)
  2. Request endorsement via arXiv's endorsement system (it generates a code; the endorser confirms)
  3. Wait for endorsement before uploading
- Reference: `https://arxiv.org/help/endorsement`

If Eirik already has cs.LG submission history, endorsement is automatic and this step is satisfied.

**Do not proceed to upload until endorsement status is confirmed.** Uploading without endorsement wastes the submission slot and gives an unhelpful error.

---

## Step-by-step submission flow

### 1. arXiv account

- [ ] Log in at `https://arxiv.org/login` (or create account if first time)
- [ ] Confirm email-verified status
- [ ] Confirm endorsement for cs.LG (see Blocker check above)

### 2. Local LaTeX compilation (recommended before upload)

- [ ] Install MacTeX if not present: `brew install --cask mactex-no-gui` (~2GB download, one-time)
- [ ] Compile locally:
  ```bash
  cd /Users/eirikbottennicolaysen/ClaudeWork/chatcat/paper/arxiv
  pdflatex chatcat-methods.tex
  bibtex chatcat-methods
  pdflatex chatcat-methods.tex
  pdflatex chatcat-methods.tex
  ```
- [ ] Verify the generated PDF (`chatcat-methods.pdf`) renders:
  - All four figures appear with correct captions
  - All references resolve (no `[?]` markers)
  - All section numbers match the source
  - Tables render cleanly (check the wide Table 2 — may need landscape or `\small` already applied)
  - Math expressions ($T$, $K$, $\sigma_\mathrm{diff}$, $\sqrt{2}$) render correctly
  - Page count is reasonable (target ~12-18 pages)

If local compilation fails:
- Most likely cause: missing LaTeX packages — `pdflatex` will report which. Install via `tlmgr install <package>`.
- Second most likely: bibliography style (`plainnat`) — should ship with MacTeX, but if missing, `tlmgr install natbib`.
- Last resort: skip local compilation and rely on arXiv's compilation — arXiv will surface errors at upload time, but iterating is slower.

### 3. Start arXiv submission

- [ ] At `https://arxiv.org/submit`, click "Start new submission"
- [ ] License: select **CC BY 4.0** (per metadata recommendation) — or arXiv non-exclusive default if Eirik prefers
- [ ] Archive: **cs** (Computer Science)
- [ ] Subject class: **cs.LG** (primary), no secondary cross-list (cs.LG-only — see submission-metadata.md)

### 4. Upload files

- [ ] Upload as a `.zip` or `.tar.gz` bundle:
  ```bash
  cd /Users/eirikbottennicolaysen/ClaudeWork/chatcat/paper/arxiv
  tar -czf chatcat-methods-arxiv-submission.tar.gz chatcat-methods.tex refs.bib chatcat-methods.bbl figures/
  ```
  Note: ship `chatcat-methods.bbl` deliberately — arXiv does not reliably re-run bibtex, and a missing `.bbl` is the most common submission failure. The verified bundle (built+tested this session) is committed at `paper/arxiv/chatcat-methods-arxiv-submission.tar.gz`.
- [ ] Alternative: upload individual files via web form (in this order: .tex, .bib, .bbl, then figures)
- [ ] arXiv will queue for compilation; check the "Processing" status
- [ ] When compilation finishes, **review the arXiv-generated PDF carefully** — this is what readers will see
- [ ] Fix any compilation errors and re-upload until clean

### 5. Fill metadata fields

From `submission-metadata.md`:

- [ ] **Title**: paste selected candidate from metadata
- [ ] **Authors**: `Eirik Botten Nicolaysen` (confirm full name spelling)
- [ ] **Affiliation**: `EcoDeco AS` (confirm)
- [ ] **Abstract**: paste plain-text version from metadata (verify no Unicode issues; convert `×` to `x` if the form complains)
- [ ] **Comments**: page count + figure count + repo URL (update repo URL once confirmed)
- [ ] **ACM classification**: skip unless requested
- [ ] **MSC classification**: skip unless requested
- [ ] **Journal reference**: leave blank (this is a preprint, not a journal submission)
- [ ] **DOI**: leave blank (arXiv assigns)
- [ ] **Report number**: leave blank unless institution requires

### 6. Review

- [ ] Read the arXiv-rendered PDF cover-to-cover one more time
- [ ] Verify abstract reads cleanly in the form preview
- [ ] Confirm all metadata fields look right in the preview
- [ ] **Do not click Submit yet** if anything is uncertain

### 7. Final submit

- [ ] **The final submit-button is Eirik's** — at this point arXiv will publish the preprint within ~24h
- [ ] Once submitted: receive arXiv ID (e.g., `arXiv:2606.NNNNN`)
- [ ] Save the arXiv ID in `paper/arxiv/SUBMITTED.md` for the repo record

---

## After submission

- [ ] Add arXiv link to project `README.md`
- [ ] Add arXiv link to project `docs/decisions/README.md` (ADR index) as a "Public preprint" row
- [ ] Tweet / announce per Eirik's preference (out of scope for this checklist)
- [ ] If reviewers / readers send corrections: prepare v2 with explicit changelog (arXiv preserves all versions)

---

## What this checklist does NOT cover

- Endorser-search if endorsement is needed (Eirik's social/professional network)
- Journal / conference submission (arXiv is preprint-only; if targeting CHI/NeurIPS later, that is a separate submission)
- Code-archive (Zenodo) if reviewers ask for a citable code DOI
- LaTeX troubleshooting beyond the basics above

---

## Status at package-build time

- LaTeX source: `chatcat-methods.tex` ✓
- Bibliography: `refs.bib` ✓ (5 entries: Ntalampiras 2019, Anthes 2022, Schneiders et al. 2024, Van Patter & Blattner 2020, Mancini & Nannoni 2023)
- Vector figures: `figures/fig1_climb_then_slide.pdf`, `fig2_sig_exploration.pdf`, `fig3_confounder_symmetric.pdf`, `fig4_gate_ratio_distribution.pdf` ✓ (all 4 generated from `plot_methods_figures.py` with dejargonized English captions; fig4 reads the committed `analysis/gate_ratio_distribution_k5.csv`)
- Metadata draft: `submission-metadata.md` ✓
- This checklist: `SUBMISSION-CHECKLIST.md` ✓
- **Local LaTeX compilation: NOT VERIFIED** — pdflatex not available in the toolchain that built this package. Eirik to compile locally before upload, or rely on arXiv compilation (slower iteration on errors).
