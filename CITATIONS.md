# Citations

Every behaviour parameter in chatcat traces to a published source. This
document lists each source, its DOI, its licence where relevant, and how it is
used in the codebase.

## 1. Ethogram

**Kappel, I., Riedel, M.-C., Becker, F., Hicks, S., Warlich-Zach, N., & Ganslosser, U. (2024).** Ethogram of
the Domestic Cat. *Pets* (MDPI), 1(3), 21.
DOI: [10.3390/pets1030021](https://doi.org/10.3390/pets1030021)
Licence: CC BY 4.0

**Used in:** `litterbox/src/simcat/ethogram.ts`
117 behaviours in 12 categories. We encode the 12 categories and a subset of
~30 behaviours most relevant to human-cat and agent-cat interaction.

## 2. Feline Five personality model

**Litchfield, C. A., Quinton, G., Tindle, H., Chiera, B., Kikillus, K. H., &
Roetman, P. (2017).** The 'Feline Five': An exploration of personality in pet
cats (*Felis catus*). *PLOS ONE*, 12(8), e0183455.
DOI: [10.1371/journal.pone.0183455](https://doi.org/10.1371/journal.pone.0183455)

**Used in:** `litterbox/src/simcat/personality.ts`, `litterbox/src/simcat/archetypes.ts`
Five validated dimensions (Neuroticism, Extraversion, Dominance, Impulsiveness,
Agreeableness) on 2802 cats. Used to parameterise SimCat behaviour and
transition probabilities.

*Author list corrected 2026-05-12: previous entry erroneously listed Senior,
K. H. and Gaultier, E. instead of Kikillus and Roetman. Verified against
PubMed PMID 28832622.*

## 3. Cat Stress Score (CSS)

**Kessler, M. R. & Turner, D. C. (1997).** Stress and Adaptation of Cats
(*Felis silvestris catus*) Housed Singly, in Pairs and in Groups in Boarding
Catteries. *Animal Welfare*, 6, 243-254.
DOI: [10.1017/S0962728600019898](https://doi.org/10.1017/S0962728600019898)

**Used in:** `litterbox/src/simcat/stress-score.ts`, `litterbox/src/world/ethics-monitor.ts`
7-point scale based on 11 postural/behavioural categories. Used as the primary
welfare metric and for hard intervention thresholds.

## 4. Pain ethogram

**Marangoni, A. et al. (2023).** Development of a pain ethogram for acute pain
assessment in cats. *PLOS ONE*, 18(9), e0292224.
DOI: [10.1371/journal.pone.0292224](https://doi.org/10.1371/journal.pone.0292224)

**Used in:** `litterbox/src/simcat/ethogram.ts`
24 validated acute pain behaviours. Encoded so the simulator can model pain
scenarios and verify the agent withdraws appropriately.

## 5. Slow blink

**Humphrey, T., Proops, L., Forman, J., Spooner, R., & McComb, K. (2020).**
The Role of Cat Eye Narrowing Movements in Cat-Human Communication.
*Scientific Reports*, 10, 16503.
DOI: [10.1038/s41598-020-73426-0](https://doi.org/10.1038/s41598-020-73426-0)

**Used in:** `litterbox/src/agent/actions.ts`, `litterbox/src/agent/policy.ts`
Half-blink, eye-narrow, eye-closure protocol. The single best empirical
evidence for any cat-directed visual signal. The agent's primary affiliative
action.

## 6. Cat-directed speech

**de Mouzon, C., Gonthier, M., & Leboucher, G. (2022).** Discrimination of
cat-directed speech from human-directed speech in a population of indoor
companion cats (*Felis catus*). *Animal Cognition*, 25, 1745-1755.
DOI: [10.1007/s10071-022-01674-w](https://doi.org/10.1007/s10071-022-01674-w)

**Used in:** `litterbox/src/simcat/vocalizations.ts` (reference parameters)
Acoustic features of cat-directed speech: elevated pitch, larger pitch
modulation. Referenced for future audio-based agent actions.

## 7. Meowsic vocalisations

**Schötz, S.** The Meowsic Project (Lund University).
Categorisation: purr, trill/chirrup, meow/miaow, growl, hiss, yowl, mating
call.

**Used in:** `litterbox/src/simcat/vocalizations.ts`
Vocalization type taxonomy for SimCat output.

## 8. CatMeows dataset

**Ntalampiras, S., Ludovico, L. A., Presti, G., Ferrara, A., & Prato
Previde, E.** CatMeows: A Publicly-Available Dataset of Cat Vocalizations.
*Zenodo*, 4008297. Licence: CC BY 4.0.
DOI: [10.5281/zenodo.4008297](https://doi.org/10.5281/zenodo.4008297)

**Used in:** Referenced as distribution baseline. Not yet pulled into repo.
440 meows from 21 cats in 3 contexts (brushing, isolation, food). Used as
reference for vocalization intensity distributions.

**Note — three distinct Ntalampiras sources, do not confuse:**
- This entry (Section 8): the CatMeows *dataset* (Zenodo 4008297, 2020).
- Section 13: Ntalampiras et al. (2019), the *proof-of-concept classifier
  paper* (Animals 9(8):543) that established that meow emission context
  can be algorithmically identified. This is what MeowTalk's scientific
  basis traces to.
- Ntalampiras et al. (2020), "What's in a Meow? A Study on Human
  Classification" (Animals 10(12):2390) — a separate study on *human*
  classification of meows, not cited in this project. Listed here to
  prevent accidental conflation.

## 9. ACI ethics framework

**Mancini, C. & Nannoni, E. (2023).** Ethical Frameworks for Animal-Computer
Interaction.

**Used in:** `ETHICS.md`, `litterbox/src/world/ethics-monitor.ts`
Four principles: Relevance, Impartiality, Welfare, Consent. Operationalised
as hard-coded system constraints.

## 10. Cat Royale

**Schneiders, E., Benford, S., Mancini, C., Mills, D. S., et al. (2024).**
Designing Multispecies Worlds for Robots, Cats, and Humans. *CHI 2024*.
(Academic primary citation.)

**Project credit:** Blast Theory, Mancini, C., Mills, D. S., University of
Nottingham (2024). Cat Royale. CHI 2024 Best Paper, Webby Award 2024.

**Used in:** Project framing, `ETHICS.md`, `docs/ideas/theoretical-foundations.md`
Closest precedent for ethically grounded ACI systems. Our explicit lineage.
The CHI 2024 paper is the academic source; the project name and the
Blast Theory / Mancini / Mills / Nottingham attribution is how the field
refers to the work — both citations belong here.

## 11. Habituation and attention

**Ellis, S. L. H. et al. (2008).** The influence of body region, handler
familiarity and order of region handled on the domestic cat's response to being
stroked. *Applied Animal Behaviour Science*.

**Hirskyj-Douglas, I. & Webber, S.** Research on novelty effect in animal-
computer interaction.

**Used in:** `litterbox/src/simcat/state-machine.ts`
Habituation rate parameterisation. Attention decline over session duration.
NOTE: habituation rates are placeholders pending real-cat data — see ADR 0003.

## 12. State-change rate plausibility

**Stanton, L. A. et al. (2015).** Cited in Kappel et al. 2024.
**Used in:** `litterbox/tests/ethological-plausibility.test.ts`
Reference for plausible state-change rates per session. Used as anchor for
the regression tests that catch state-machine flicker — see ADR 0004.

## 13. Cat-vocalisation context classification (proof-of-concept)

**Ntalampiras, S., Ludovico, L. A., Presti, G., Prato Previde, E., Battini,
M., Cannas, S., Palestrini, C., & Mattiello, S. (2019).** Automatic
Classification of Cat Vocalizations Emitted in Different Contexts.
*Animals*, 9(8), 543.
DOI: [10.3390/ani9080543](https://doi.org/10.3390/ani9080543)

**Used in:** `README.md` (framing of MeowTalk overreach).
Proof-of-concept showing that the emission context of a meow can be
algorithmically classified across three contexts (waiting for food,
isolation in unfamiliar environment, brushing) with a DAG-HMM model
reaching 95.94% accuracy. The authors describe this themselves as "a
proof of concept" for context identification — narrow, peer-reviewed
scope. This is the scientific basis MeowTalk traces back to; MeowTalk's
translation claims went beyond what this work supports (see Section 14).

See also the cross-reference note in Section 8 distinguishing this from
the CatMeows dataset and from the 2020 human-classification paper.

## 14. MeowTalk overreach (popular-press source)

**Anthes, E. (2022).** Did My Cat Just Hit On Me? An Adventure in Pet
Translation. *The New York Times*, 29 August 2022.

**Used in:** `README.md` (the "It's not pure science at this stage" quote).
Anthes attributes the "not pure science at this stage" admission to one of
MeowTalk's own inventors, not to the underlying scientific authors. This
matters: the framing is "proof-of-concept overstretched to product, admitted
by the product itself", not "external scientific criticism of MeowTalk".

## 15. ACI ethical principles (academic primary)

**Van Patter, L. E. & Blattner, C. (2020).** Advancing Ethical Principles
for Non-Invasive, Respectful Research with Nonhuman Animal Participants.
*Society & Animals*, 28(2), 171–190.

**Used in:** Project framing, `ETHICS.md` (when referencing the
non-maleficence / beneficence / voluntary-participation triad).
Source of the three principles (non-maleficence, beneficence, voluntary
participation) that Cat Royale adopted and that this project inherits via
Cat Royale's lineage. When citing Cat Royale's ethical structure, also
cite Van Patter & Blattner as the academic origin of the principle set.
