## 4 Diskusjon

### 4.1 Hva resultatet faktisk er

Utfallet er negativt og inkonklusivt, men det er ikke tomt. Vi avgjorde ikke fenomenet. Vi avgjorde at fenomenet ikke kan avgjøres med denne terskel-tilnærmingen på oppnåelig compute, og vi vet presist hvorfor: målbarheten er seed-variabel. Det er forskjellen mellom «vi vet ikke» og «vi vet hvorfor vi ikke kan vite med denne metoden». Det andre er et resultat.

### 4.2 Hvorfor gaten er bidraget

Uten gaten ville kriterie-validitet-reanalysens M' = 3/5 blitt rapportert som et borderline-funn om agenten, og N=15-escaleringens nye seeds ville produsert et M''-tall som så ut som data. Gaten viste at begge i virkeligheten ville vært funn om måle-vinduet, ikke om agenten, og nektet å produsere et rent tall der tallet ville vært en artefakt. Innenfor RL-evaluering generaliserer dette så langt og ikke lenger: enhver terskel-basert reproduserbarhets-vurdering der terskelen er forankret i ett regime og anvendt i et annet er sårbar for denne feilen, og gaten er en billig sjekk mot den. Den er en sjekk mot én feilklasse, ikke en løsning på RL-evaluering.

### 4.3 Begrensninger

Simulatoren er ikke virkelighetstro; sim-to-real-gapet er udokumentert til v0.4. Resultatene gjelder agent-evaluering i simulator, ikke kattatferd, og vi hevder ikke annet. N=15 er lite — men det er nettopp poenget. Mer N løser ikke problemet når målbarheten selv er seed-variabel, og det er grunnen til at midtbåndet ble pre-registrert som et sluttpunkt heller enn et sted å hente flere kjøringer fra. Diagnosen er diagnose, ikke fiks: vi peker på at sliden er optimaliserings-side, vi løser den ikke. Warm-start, KL-anker og reward-reshaping er alle ikke-valgte og ligger nedstrøms.









Det vi tilbyr feltet er ikke et svar på climb-then-slide. Det er en metode som nektet å gi et falskt svar, og et eksplisitt spor av hvorfor nektelsen var den riktige vitenskapelige handlingen. I et felt der overpåstand er den dokumenterte feilmoden, er evaluerings-infrastruktur som kan si «dette kan ikke avgjøres ennå, og her er hvorfor» en forutsetning for å ikke bli det man kritiserer.
