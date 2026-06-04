# ADR 0010 Resolution — main run outcome and method-lærdom

**Status:** Resolved on the locked criterion (2026-06-05); OPEN on the
phenomenon question pending the budsjett-fri reanalyse pre-registered
by a follow-on ADR (planned 0011).

**Tracks:** Hovedrunden N=5 mot frosne terskler (T = 0.0922,
K = 0.004986) utført; F3 fyrte; climb-leddets måletekniske svakhet
oppdaget etter at kriteriet fyrte; partial retraksjon av `31c363e`'s
framing (2)-løfte.

**Files referenced:**
- `0010-holding-question.md` (commit `31c363e`) — stub framing
- `0010-step2-preregistration.md` (commits `0140536` + `6f838e9`) — pre-reg + seed-set-amendment

**Main-run artefacts:** `~/chatcat-rl-runs/phase2_main__seed{6,7,8,9,10}__*/`
(`metrics.jsonl`, `agent.pt`, `best_so_far.pt`, `run_config.json` per
seed; verified intact post-kjøring).

---

## Hovedutfall — F3 fyrte mot det låste kriteriet

**F3 fyrte. Udiskutabelt, ingen re-telling.**

Per pre-reg Precision 4: M = 2/5 ≤ 2/5-terskelen → F3 fyrer umiddelbart,
ingen utvidelse. Kriteriet var låst i `0140536`, det ble anvendt
mekanisk på hovedrundens fem `metrics.jsonl`-filer, utfallet er det
utfallet.

Per-seed-tabell mot frosne terskler (T = 0.0922):

| seed | ep_init [100,150] | peak@update | ep_peak | ep_final | climb | slide | CTS |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 6 | −0.575 | 1548 | −0.761 | −0.968 | **−0.186 ✗** | +0.208 ✓ | ✗ |
| 7 | **+0.412** | 852 | +0.449 | −1.010 | **+0.037 ✗** | +1.459 ✓ | ✗ |
| 8 | −0.386 | 1603 | −0.530 | −1.311 | **−0.145 ✗** | +0.780 ✓ | ✗ |
| 9 | −0.508 | 2102 | +0.179 | −0.115 | +0.686 ✓ | +0.294 ✓ | ✓ |
| 10 | −1.391 | 841 | −0.857 | −1.217 | +0.534 ✓ | +0.359 ✓ | ✓ |

**M = 2/5.** F3-konsekvens per pre-reg §4: "The structural-finding
framing itself (Framing 2) is undermined. We do not have a robust
phenomenon to characterise — we have a sometimes-phenomenon."

F1/F2/F4 fyrte ikke:
- F1: 0/2 CTS-qualified (logstd_drift_peak = −0.062 og +0.032, godt
  over −0.14-gulvet).
- F2: 0/2 CTS-qualified (vloss_peak/K-ratio = 0.256 og 0.270, godt
  under 1.0).
- F4: 0/5 slide-flips (alle fem seeds gled fra sin egen topp; slide-
  retningen er universell, det er bare climb-amplitude som ikke
  passerer terskel for alle).

---

## Separat observert: climb-leddet i kriteriet var måleteknisk svakt

Dette står som egen observasjon, ikke som forklaring eller redning
av F3-utfallet.

Climb-formelen er `ep_peak − ep_init`, der `ep_init` er snittet av
`ep_return_mean_recent` over init-vinduet [100, 150] per pre-reg §1.
Buffer-fullhet i det vinduet er **11–19 episoder** på tvers av alle
fem seeds (mean 13.9–15.2). Buffer når N=100 først ved update
~820–850. `ep_init` er derfor ikke en stabil mean — den er en
høyvarians-estimator basert på 11–19 tidlige episoder.

Kvantitativt mot terskelen:

| Størrelse | Verdi |
|---|---:|
| T (climb/slide-terskel, låst) | 0.0922 |
| ep_init-range innenfor [100,150] per seed (max−min) | 0.668–0.973 |
| Forhold ep_init-range / T | **~7×–10×** |

Buffer-støyen i ep_init er én størrelsesorden over climb-terskelen.
Climb-leddet `ep_peak − ep_init`, slik det ble anvendt, måler derfor
ikke seed-egenskap mot pre-registrert terskel — det måler seed-egenskap
PLUSS init-vindu-buffer-tilfeldighet mot pre-registrert terskel, og
buffer-tilfeldigheten dominerer.

Konsekvens for amplitude-CTS-tellingen: hvilke 2 av 5 seeds som passerte
climb er i praksis nær tilfeldig — et coin-flip på et måleteknisk svakt
kriterium, ikke en seed-egenskap. Form-CTS (klatret-så-gled
kvalitativt) var 5/5; F4-fraværet bekrefter det.

Buffer-konfunderen er **strukturell og jevnt fordelt på tvers av alle
fem seeds**, ikke en seed-7-spesifikk patologi (mean buffer N over
init-vindu: seed 6 = 14.47, seed 7 = 13.90, seed 8 = 15.22, seed 9 =
14.27, seed 10 = 14.76).

---

## Disse to fakta eksisterer side om side

**F3 fyrte mot det låste kriteriet.** Det er hovedutfallet. Climb-then-
slide reproduserte ikke robust over N=5 mot den pre-registrerte
amplitude-definisjonen.

**Climb-leddet i det kriteriet hadde en strukturell måleteknisk
svakhet vi oppdaget etter at F3 fyrte.** Det er metode-lærdommen.

Den første er det låste-kriterium-utfallet vi er bundet av —
pre-registrerings-disiplin tillater ikke at vi re-teller fordi vi i
ettertid ser at climb-vinduet var svakt. F3 fyrte. Det står.

Den andre er en presis observasjon om vår egen pre-registrering som
vi skylder en ærlig regnskap for — ikke som unnskyldning for F3, men
fordi den forklarer **hva som faktisk feilet**: det som feilet er
ikke nødvendigvis fenomenet, det er climb-leddet i kriteriet vi brukte
for å måle om fenomenet reproduserte. Det er to forskjellige feil; den
ene kan være sann uten å oppheve den andre.

Den ærlige lesningen: F3 fyrte ærlig mot et kriterium hvis climb-halvdel
var ugyldig fra start. Begge setningene står.

---

## Metode-lærdom — pre-registrering beskytter ikke mot ugyldig utgangspunkt

Vi flyttet T-forankringen vekk fra [100,150] i pre-reg-amendmentet
(`0010-step2-preregistration.md` Precision 3, commit `0140536`) fordi
forankrings-seedens måling viste at vinduet var buffer-støyete (mean
N_recent 12–17 episoder, ikke 100, og inter-update-SD 0.349 mot
sen-stabil 0.031 — vinduet lå i selve climb-fasen). Det var en
metodisk riktig avgjørelse for forankringen.

Vi BEHOLDT [100,150] som anvendelsesvindu for `ep_init` i climb-
formelen fordi pre-reg §1 definerte det slik og vi anvendte det
mekanisk. **Det var en metodisk inkonsistens vi bygde inn:**
forankringen ble flyttet vekk fra et vindu vi visste var svakt, men
anvendelsen ble ikke. Hovedrunden viste konsekvensen — climb-leddet
ble dominert av samme buffer-støyen forankringen ble flyttet vekk
fra, og rammet kriteriet der det er måleteknisk svakest.

Meningsfullhets-gaten vi bygde for T (Precision 3, "T må ligge mellom
~5 % og ~80 % av peak−end-spennet") fanget ikke dette. T = 0.0922 var
~10 % av peak−end-spennet (~0.9) og passerte gaten med margin. Men
gaten testet ikke forholdet mellom T og **anvendelses-vinduets**
noise-skala — kun forholdet mellom T og det observerte utfalls-spennet.
Et kriterium kan være meningsfullt mot utfalls-spennet og samtidig
ugyldig mot anvendelsesvindu-støyen, og vi designet gaten kun for
den første sjekken. Det er et ekte hull i en gate vi trodde var
komplett.

**Lærdom:** pre-registrering beskytter mot post-hoc-tukling med
kriterier, men ikke mot et kriterium som er ugyldig fra start. Det
neste ADR-arbeidet må inkludere en **kriterie-validitet-gate** som
sjekker terskelen mot noise-skalaen i hvert anvendelsesvindu — ikke
bare mot utfalls-spennet. Forskjellen er en gate som spør "vil dette
kriteriet meningsfullt skille signal fra støy?" mot en gate som spør
"vil dette kriteriet meningsfullt skille signal fra spennet jeg
forventer å se?". Vi bygde den andre; vi trengte begge.

Denne lærdommen er metodisk sett **mer verdifull enn fenomen-funnet**
ADR 0010 søkte. Den hører eksplisitt i ADR-treet, ikke pakket inn
som en fotnote, fordi den endrer hvordan framtidig pre-registrering
skal designes.

---

## Neste ADR-spørsmål — budsjett-fri reanalyse av climb mot buffer-fullt vindu

Spørsmålet "er M = 2/5 en ekte fenomen-egenskap eller et artefakt av
climb-vindu-støyen" er **åpent** etter denne kjøringen. Det kan
besvares budsjett-fritt: re-måle climb mot et **buffer-fullt** vindu
(første 51 updates med N_recent ≥ 100, som for hovedrundens fem seeds
starter rundt update 820–850) på de eksisterende `metrics.jsonl`-
filene. **Ingen ny trening kreves**, kun reanalyse av disk-artefakter.

Den reanalysen gjøres **IKKE i denne resolusjonen**. Den må
pre-registreres rent i et neste ADR (foreløpig planlagt 0011) FØR
reanalysen kjøres, fordi å re-måle et fryst kriterium etter å ha sett
det fyre er post-hoc med mindre selve reanalysen pre-registreres
separat. Det er den samme disiplinen som styrte forankrings-seedens
scope ("skala-måling, ikke utfalls-lesning") i Step 1.5.

Konkret skal ADR 0011's pre-registrering inkludere:
- Buffer-fullt anvendelsesvindu for `ep_init` (første 51 updates med
  `ep_return_n_recent ≥ 100`).
- Samme T-anker som i ADR 0010 (sen-stabil noise, 0.030737 × 3 =
  0.0922 — uendret).
- Pre-registrerte konsekvenser:
  - M' ≥ 4/5 mot revidert vindu → climb-vindu-artefakt **bekreftet**;
    fenomenet ER robust, ADR 0010's amplitude-kriterium var bare
    ugyldig.
  - M' ≤ 2/5 mot revidert vindu → fenomenet er IKKE robust selv mot
    buffer-fullt vindu; F3-konklusjonen i ADR 0010 holder
    uavhengig av climb-vindu-konfunderen.
  - M' = 3/5 → borderline (samme disiplin som ADR 0010 Precision 4).
- **Kriterie-validitet-gate** inkludert FØR måling: sjekk at climb-
  terskelen er meningsfull mot noise-skalaen i det reviderte
  anvendelsesvinduet, ikke bare mot utfalls-spennet.

Først når den reanalysen er pre-registrert og kjørt, kan ADR 0010's
**phenomenon-status** lukkes. Inntil da er ADR 0010 resolved på det
**låste kriteriet** (F3 fyrte) men **åpen på fenomen-spørsmålet** (er
"ikke-robust" en ekte fenomen-egenskap eller en climb-vindu-artefakt).
De to statusene er forskjellige; resolusjonen anerkjenner den
forskjellen åpent.

---

## Retraksjons-trekk fra `31c363e`

`0010-holding-question.md` (commit `31c363e`) framet tre veier for
hvordan ADR 0010 kunne bevege seg fra SIG-EXPLORATION-diagnose på
0008-partial-data til en publiserbar konklusjon: (1) deployable,
(2) structural finding med publisering i sikte, (3) online. Eirik
valgte (2) — strukturell funn — på grunnlag av at SIG-EXPLORATION-
mekanismen pekte mot et reproduserbart fenomen verdig en preprint.

**Det som retracterer:** framing (2)'s løfte om "publiserbart
strukturelt funn" som det stod i `31c363e`. Hovedrundens F3-fyring
forutsetter en pivotering — preprinten kan ikke skrives som "her er
et reproduserbart strukturelt fenomen vi karakteriserer", den må
skrives som (a) "her er et delvis reproduserbart fenomen og her er
metode-lærdommen om kriterie-design", eller (b) hvis ADR 0011's
budsjett-frie reanalyse bekrefter climb-vindu-artefakt: "her er et
robust fenomen og her er den metode-lærdommen om hvorfor vår
opprinnelige måling skjulte det". Hvilket av (a)/(b) preprinten
faktisk blir er en avgjørelse nedstrøms av ADR 0011's utfall.

**Det som IKKE retracterer:** SIG-EXPLORATION-mekanisme-diagnosen i
`31c363e`. F1/F2 var ikke fyrt på de 2/5 seedene der CTS faktisk
reproduserte (logstd_drift_peak −0.062 og +0.032 mot −0.14-gulvet;
vloss/K-ratio 0.256 og 0.270 mot 1.0-taket). Der climb-then-slide
skjedde i hovedrunden, holdt SIG-EXPLORATION-mekanismen. Det matcher
prediksjonen fra pre-reg §4's falsifiserings-balanse-avsnitt: F1 og
F2 forventes inaktive før hovedrunden; hovedrundens innsats ligger
i F3 og F4. F3 fyrte, F1/F2 ikke. Mekanisme-diagnosen står.

**Retraksjons-form:** dette dokumentet flagger retraksjonen.
`31c363e`-stubens tekst **endres ikke**. Hvem som leser ADR-treet i
fremtiden ser stubens opprinnelige framing, pre-regens metodologi
(med seed-set-amendment), denne resolusjonens utfall, og pekeren mot
ADR 0011 — hele avgjørelses-trailen bevart i sin tidsorden, ingenting
stille omskrevet.

---

## Hva denne resolusjonen IKKE gjør

- **Velger ikke kandidat-fiks** (std-annealing, KL-anker, reward-
  reshaping, etc.). Det er nedstrøms av at fenomen-spørsmålet er
  fastslått, og fenomen-spørsmålet er åpent inntil ADR 0011's
  reanalyse er kjørt.
- **Endrer ikke `31c363e`-stubens tekst.** Retraksjonen flagges her,
  ikke skrives inn i stuben.
- **Endrer ikke pre-reg-dokumentet (`0140536`).** Pre-regen står som
  den var; den definerte det låste kriteriet, det ble anvendt, denne
  resolusjonen rapporterer utfallet.
- **Endrer ikke `T` eller `K`.** Forankringene er låst; reanalysen i
  ADR 0011 vil anvende samme T mot et revidert anvendelsesvindu, ikke
  ankret om.
- **Velger ikke seed-sett for evt. ADR 0011-reanalyse.** Reanalysen
  bruker eksisterende disk-artefakter ({6, 7, 8, 9, 10}). Hvis ny
  trening senere kreves, skal seed-sett pre-registreres på samme
  disjunkthets-grunnlag som hovedrundens var.
