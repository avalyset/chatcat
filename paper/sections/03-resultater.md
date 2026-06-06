## 3 Resultater

### 3.1 Fenomenet i form

Alle fem seeds i {6..10} klatrer til en peak og glir tilbake. I form er climb-then-slide universelt — 5/5 — og det er det kurvene viser direkte (Fig 1). Men form er ikke det samme som amplitude mot en terskel. Om climb-leddet faktisk passerer T avhenger av hvilket vindu vi måler det i, og den distinksjonen — form mot amplitude-mot-terskel — er hele poenget i det som følger.

### 3.2 Den direksjons-symmetriske konfunderen

Det samme måle-vinduet løy begge veier (Fig 3). Med det opprinnelige ep_init-vinduet [100,150] målte seed 6 og 8 climb-leddet under T — ikke-reprodusert. Flyttet til det buffer-fulle vinduet passerte de samme to over T. Vinduet hadde skjult ekte climb-then-slide. Samtidig gikk seed 10 motsatt vei: over T i det opprinnelige vinduet, under T i det reviderte. Vinduet hadde fabrikkert et fenomen som ikke var der.

Det er nøkkelfunnet. En vindu-endring som bare hadde skjult, eller bare fabrikkert, kunne avskrives som enveis-bias man korrigerer for. At den samme endringen flyttet to seeds inn i et positivt resultat og en tredje ut av det, samtidig, viser at hvilke seeds som passerer er styrt av måle-valget, ikke av agenten. Tallene flyttet seg deretter: M på det opprinnelige vinduet var 2/5, M' på det buffer-fulle 3/5 (Tabell 2).

### 3.3 Mekanismen

På de seedene som reproduserer climb-then-slide holder SIG-EXPLORATION-signaturen (Fig 2). Variansen i policyen kollapser ikke under peak, og critic-en er konvergert lavt. Sliden er optimaliserings-siden av en policy med vid varians, ikke et resultat av varians-kollaps. Mønsteret er det samme på alle de reproduserende seedene, på tvers av 0010 og 0011.

### 3.4 Gaten passerte, så feilet

I 0011 passerte kriterie-validitet-gaten — T/σ_diff = 2.73 — og M' landet på 3/5. Borderline, og inkonklusivt på fem seeds. Escaleringen i 0012 la til ti nye seeds, {11..20}, for N=15. Der feilet gaten: T/σ_diff = 1.80. Den samme treningskonfigen produserte rundt 50% høyere median noise-skala på det nye seed-settet, 0.0362 mot 0.0239 (Fig 4, Tabell 1). STOP fyrte før M'' ble talt.

Funnet ligger der. Målbarheten selv er seed-variabel: noise-skalaen T ble forankret mot på ett seed-sett gjelder ikke på et annet ved identisk konfig. Det er et nivå dypere enn fenomenet. Vi kan ikke avgjøre om climb-then-slide er robust — ikke fordi vi mangler data, men fordi terskelen ikke er stabilt anvendbar på tvers av seeds.
