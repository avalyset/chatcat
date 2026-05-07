# 2026-05-07 — Første litterbox-kjøring

Kjørte v0.1 på localhost:5173. SimCat (Bold Diplomat) sto til venstre, 
agenten i hjørnet — slow-blinket og pauset som forventet.

Skrudde opp speed til 100x og fant to bugs:

1. Reset-knappen tilbakestilte ikke ethics-monitor — cooldown fra forrige 
   sesjon hang igjen.
2. Cooldown-telleren loopet istedenfor å telle monotont ned.

Begge fikset i commit 3025246, med to nye regression-tester. 28/28 passerer 
nå.

Observasjon for fremtiden: 100x speed er et kraftig avslørings-verktøy. 
Ting som ser greit ut på 5x kan være helt galt på 100x. Bør være del av 
manuell QA-rutine før hver release.

Det første jeg la merke til da systemet faktisk fungerte: ethics-monitor 
overstyrte agenten på vegne av en simulert katt. Det er et lite øyeblikk, 
men det er hele prosjektet i miniatyr.