# 2026-05-08 — ADR 0004 og fix av flicker

Bygde batch-runner i dag. Smoke-test avdekket umiddelbart 
at SimCat skiftet state ~16 ganger per minutt — ethologisk 
umulig. En ekte katt gjør ikke det.

Diagnosen tok litt tid: transition-sannsynligheter var 
kalibrert for 1 Hz men kjørte på 10 Hz, og en separat 
CSS-noise-bug gjorde at agent og ethics-monitor så 
forskjellige verdier av samme katt.

ADR 0004 ble skrevet før noen fix. Det føltes som riktig 
disiplin: dokumenter problemet i klartekst først, så fiks det.

Fem commits senere har simulatoren ethologisk plausible tall: 
opt-outs gikk fra 481 til 29 per sesjon, MaxCSS holder seg 
under 6 unntatt for Anxious Skeptic der det er en ekte 
personlighetsdrevet måling.

Mest interessant lærdom: dwell-floor reduserte flicker, men 
kollapset også amplifikasjonen av personlighetsforskjeller 
som de gamle testene hvilte på. To tester måtte rewrites til 
å teste personlighet på sesjonsnivå (ENGAGING%, mean CSS) 
heller enn på tick-nivå (transition rates). Personlighet 
uttrykker seg over lengre tidsskalaer enn jeg først antok.

Baseline-kjøring (5000 sesjoner) venter til neste dag. 
Bedre å tolke med klart hode.