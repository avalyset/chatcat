## 1 Introduction

### 1.1

Reproducibility assessment for reinforcement-learning agents rests on thresholds: a metric crosses a line and a run is called clean, or it does not and the run is flagged. The line is the whole judgment. But a threshold can look principled and still be noise-dominated inside the window it is applied to — and when that happens, a result that reads as clean is a measurement artifact, not a finding. Pre-registration does not catch this on its own. Fixing the threshold and the analysis in advance guards against the obvious failure — choosing a cutoff after seeing the data — but it says nothing about whether the chosen cutoff sits above or below the noise floor of the very quantity it gates. A pre-registered threshold that lands inside the noise band is still a clean-looking artifact. It is just an honestly arrived-at one.

We demonstrate the method on an RL agent trained against an ethological simulator — chatcat, a companion-AI substrate for animal behavior. The domain is not incidental, and it is not the subject of the paper. We name it because its documented failure mode is overclaiming, which makes it a high-stakes test case: here, a false clean result costs something. The reference point is MeowTalk. Ntalampiras et al. (2019) established, as a proof of concept, that the emission context of a meow can be classified into three contexts — narrow, falsifiable science, and it holds. The product built on top of it stretched that foundation into translation claims it could not support — a gap one of the app's own creators later conceded to the New York Times (Anthes 2022). The distance between what the science carried and what the product asserted is the failure mode, and a field that fails this way is exactly where an evaluation that refuses to overclaim earns its keep. Companion-AI for animals is not what the paper is about; it is the sharpest place to show a method that does not fool itself.

The simulator itself is seriously constructed, not a toy dressed up for the argument. Its design is litterbox-first and uses no live animal, following the animal-computer-interaction lineage — the Cat Royale work (Schneiders et al. 2024) and the ethical position set out by Van Patter & Blattner (2020) and Mancini & Nannoni (2023), where non-maleficence and voluntary participation are treated as design constraints rather than disclaimers. That lineage is why the substrate is the kind of thing a method can be tested against at all. But the substrate is the test bench, not the contribution. What this paper offers is an evaluation method — a criterion-validity gate — that stopped us from reporting a clean result we had not in fact earned, and that generalizes to any threshold-based reproducibility assessment in RL. §1.2 sets out the gap — a threshold validated against outcome-spread rather than window-noise — and §1.3, the gate that closes it.

### 1.2

RL evaluation rarely pre-registers. When it does, the threshold is registered, but not whether the threshold is separable from the noise in the window it is measured against. That is the gap.

A threshold T can be validated against the outcome span — peak to end — and look meaningful. The same T can be noise-dominated in the window where T is actually applied — ep_init, the mean of returns over a defined early-training window. When it is, whether a given seed passes is close to a coin flip. The result reads as a finding about the agent; it is a finding about the window.

### 1.3

Our contribution is a criterion-validity gate: a pre-registered check, run before the threshold is applied, that T is separable from the noise-difference in its application window. Operationally we require that T sit at least roughly twice above the noise-difference in the window. The gate is registered together with the methodology, not added afterwards.

We report three cases in which the gate changed the outcome. None are hypothetical — each is measured, and each points to a committed assumption in an ADR chain that forms the paper's reproducible appendix. The negative outcome is the contribution: that we could not decide the phenomenon, together with the precise reason no reasonable amount of compute would have changed that, is a stronger methodological result than a number we would have had to force.

### 1.4

The paper delimits what it claims. It does not claim that the phenomenon we observed — climb-then-slide, where the agent reaches baseline and does not hold it — is solved. It claims no fix; warm-start, KL-anchoring, and reward-reshaping are all unchosen and lie downstream. It does not claim the simulator is realistic; the sim-to-real gap is undocumented until v0.4, and we note this explicitly. The diagnosis we made — that the slide sits on the optimisation side, not in the reward landscape — is diagnosis, not fix, and is presented as such.
