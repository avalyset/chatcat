# ADR 0015: Paper revision before arXiv submission — template, structure, related work

## Status
Proposed (pre-registered before edits; ADR-before-fix discipline).
Non-destructive (normal commits on public main; no history rewrite).

## Context
An arXiv endorsement request to Eike Schneiders (HCI/cs.HC) came back a decline
— not cs.LG-qualified — with unsolicited but usable feedback on
paper/arxiv/chatcat-methods.tex. Three points: (1) weak structure — no
subsection heading text in §1, a figure rendering inside the reference region,
appendix structuring; (2) adopt a standard conference LaTeX template; (3)
stronger engagement with prior literature.

A read-only diagnosis against HEAD 55fd58b (compiled and verified) confirmed all
three, surfaced two latent issues, and separated real bugs from style/decision
items:

- §1 has four \subsection{} (lines 63/72/79/86) with EMPTY titles — render as
  numbers with no heading text. §2–§4 are fine; problem isolated to §1.
- Figure float bug (real): source float order is 1, 3, 2, 4. In the compiled
  11-page PDF, fig2_sig_exploration (discussed §3.3, ~p5–6) defers to p8, into
  the reference/appendix region. Figures cluster on p5/p6/p8/p10, far from their
  discussion.
- Latent label↔number mismatch: LaTeX numbers floats by position, so
  fig3_confounder renders "Figure 2" and fig2_sig_exploration renders "Figure 3"
  (tables: tab:1→"Table 2", tab:2→"Table 1"). No broken \refs, but label names
  are misleading — a maintenance trap.
- Appendix is flat: one \section + one \subsection*{Reproducibility}.
- Template: bare \documentclass[11pt,a4paper]{article}. No venue/preprint
  template; a4paper unusual for ML (US-letter is the norm).
- Related work (largest gap): no dedicated section; refs.bib has 5 entries, all
  cat/ACI domain. No RL-reproducibility canon (Henderson, Agarwal/rliable,
  Colas, Gundersen). The paper makes a reproducibility-methodology contribution
  without citing the literature it contributes to.

## Decision
One disciplined revision round before arXiv submission.

### 1. Template — vendored NeurIPS 2024, preprint mode (NOT ACM)
No ML preprint style is available via tlmgr; vendor paper/arxiv/neurips_2024.sty
into the repo and use \usepackage[preprint]{neurips_2024} (shows "Preprint.
Under review.", not anonymized, not venue-locked, US-letter automatic). NOT ACM:
Eike's diagnosis (structure needs a real template) is right; his prescription
(ACM/IEEE) is field-coloured — ACM is cs.HC. This is cs.LG; ACM mis-signals to
ML reviewers and to the likely endorsers (Colas/Agarwal/Henderson/Gundersen all
in ML). A full submission template would over-claim a venue not chosen; preprint
mode signals the field without binding to one. Remove packages NeurIPS provides:
geometry(margin=1in), lmodern, hyperref + \hypersetup{} block, titlesec + both
\titlespacing* lines, caption. Keep amsmath, amssymb, graphicx, booktabs, array,
natbib, xcolor (after neurips), inputenc, fontenc, microtype, \newcommand{\code}.
Remove a4paper.

### 2. Related work — substantive job; CC delivers SKELETON, Eirik/Brevet write prose
Add a dedicated Related Work / Background section positioning the gate against
the RL-reproducibility canon. Add the verified entries to refs.bib:
henderson2018deep (AAAI 2018), agarwal2021deep (NeurIPS 2021, the rliable paper),
colas2018howmany (arXiv 2018), colas2019hitchhiker (RML@ICLR 2019),
gundersen2018state (AAAI 2018 — CORRECTION from the first ADR draft: the JAIR
2024 "four mechanisms" paper is editorial policy, wrong Gundersen; use the AAAI
2018 reproducibility survey). The cat/ACI refs stay (test bench + overclaiming
motivation). These names are also the endorser pool — closing the gap helps both.
CC places \cite{} in a real section skeleton with explicit [POSITIONING]
placeholders; Eirik/Brevet write the argument.

### 3. §1 subsection titles
Give the four §1 subsections real heading text, or collapse if it reads better
flat. No empty-title subsections.

### 4. Figure/table label/number hygiene (MANUAL — template does NOT fix this)
Swap source order of the fig:2 and fig:3 float blocks so label name == rendered
number. Swap tab:1/tab:2 label names and update every \ref. Improve placement so
each float renders near its discussion. Verify in the compiled PDF.

### 5. Appendix subdivision
Split Appendix A into A.1 (ADR evidence trail + SCX59 DOI note) and A.2
(Reproducibility). Keep hash-independent.

## Out of scope
No new findings, no re-analysis, no gate-chain scope change. Appendix stays
hash-independent (ADR refs + SCX59 DOI). ZNSDM stays OUT (Decision C). Sealed
C-thesis stays out (ADR 0014). No venue commitment.

## Consequences
arXiv bundle rebuilt from the new template; from-scratch build-verify without
bibtex must pass (.bbl regenerated for expanded refs). Page count changes —
expected. Quality upgrade, not a submission blocker. Endorsement track unaffected
(Gundersen out; Colas next). Gives an honest line for the thank-you to Eike.

## Verification (before commit)
Compiled PDF: §1 subsections titled; floats render near their discussion;
figure/table numbers match labels; appendix A.1/A.2. refs.bib includes the canon;
related-work section exists (skeleton with [POSITIONING] pending prose). arXiv
bundle compiles from scratch without bibtex; no raw commit hashes; no sealed
terms (truth-grounding/determinerthet/double-layer).

## References
ADR-before-fix discipline. Read-only paper diagnosis + template/citation recon,
2026-06-16 (NeurIPS-2024-vendored; Gundersen JAIR-2024→AAAI-2018 resolved).
