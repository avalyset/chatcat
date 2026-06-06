## 2 Metode

### 2.1 Oppsett

Vi trente en RL-agent mot en etologisk simulator (SimCat) i en companion-AI-kontekst. Agenten er CleanRLs `ppo_continuous_action` over et kontinuerlig handlingsrom Box(7,), med en stdio-bridge mellom Python-siden som kjører RL og TypeScript-runtimen som kjører simulatoren. Reward er baseline-normalisert: R_agent − R_baseline. Det er i dette oppsettet fenomenet vi studerer oppstår — climb-then-slide, der agenten klatrer til baseline-linja og ikke holder den.

Hver kjøring er rundt 5M steg, omtrent 33 minutter CPU. Kjøringene er deterministiske per seed; vi verifiserte det ved at 1391 updates overlappet bit-identisk mot en avbrutt kjøring. Artefaktene ligger på persistent lagring, ikke på flyktig path — et punkt vi kommer tilbake til, fordi et tidligere datasett gikk tapt og tvang rekonstruksjon.

### 2.2 Pre-registrerings-disiplin

Hver metodisk beslutning ble låst og pushet til versjonskontroll før data ble samlet eller trening kjørt. Metrikker, terskler, suksesskriterier og falsifiserings-betingelser er committed på forhånd. Pre-registrering er ikke nytt i prinsipp — det vi gjør er å anvende det med en presisjon RL-evaluering sjelden har: det fulle beslutnings-sporet ligger kronologisk i versjonshistorikken, og hver påstand i resultatene peker på den committen som låste forutsetningen den hviler på. Mønsteret gjentok seg over fire iterasjoner gjennom arbeidet.

### 2.3 Forankrings-seed

Tersklene er målt, ikke gjettet. To terskler styrer evalueringen: T for climb/slide, K for critic-konvergens. Begge forankres i målt skala fra én dedikert forankrings-kjøring i stedet for i et valgt tall. Forankrings-seeden måler skala-størrelsene — inter-update-SD i et definert vindu, median value_loss i et sent vindu — og T og K settes som multiplum av disse.

Én disiplin her er avgjørende. Forankrings-seedens eget utfall — om den selv reproduserte fenomenet — leses aldri og teller ikke som datapunkt. Den setter skala, ikke resultat. Lot vi den telle som begge deler, ville kriteriet blitt sirkulært: en seed som var med på å definere terskelen kunne ikke samtidig være et uavhengig test av den.

Tallene: T = 0.0922, tre ganger den sen-stabile inter-update-SD-en på 0.0307. K = 0.004986, tre ganger median value_loss på 0.001662. Multiplikatorene ble låst før måling og begrunnet støy-statistisk — rundt to standardavvik utenfor støy-differansen — ikke justert for å treffe et ønsket utfall.

### 2.4 Kriterie-validitet-gate

Dette er bidraget. Før en terskel anvendes, verifiserer vi at den er adskillbar fra støyen i sitt eget anvendelsesvindu: T må ligge minst rundt to ganger over støy-differansen, σ√2, i det vinduet.

Hvorfor det trengs: standard pre-registrering låser terskelen og validerer den mot utfalls-spennet, peak minus slutt. Den validerer den ikke mot støyen i vinduet terskelen faktisk måles mot. En terskel kan passere den første sjekken og likevel være støy-dominert i anvendelsesvinduet. Når den er det, er hvilke seeds som passerer nær tilfeldig — og resultatet leses som et funn om agenten når det er et funn om vinduet.

Gaten har et pre-registrert binært utfall. PASS: terskelen er gyldig, evalueringen fortsetter. FAIL: terskelen er støy-dominert i dette vinduet, og vi stopper i stedet for å anvende den. Vi kjørte gaten to ganger. Den passerte første gang (T/σ_diff = 2.73) og feilet andre gang (T/σ_diff = 1.80). At den feilet på et reelt datasett (ADR 0012, T/σ_diff = 1.80) viser at PASS i ADR 0011 (T/σ_diff = 2.73) ikke var forhåndsbestemt av konstruksjonen.

### 2.5 Falsifiserings-struktur

Suksesskriteriet og falsifiseringen var pre-registrert: hvor mange seeds som må reprodusere fenomenet for at det regnes robust, og hva som teller som ikke-robust. Escaleringen la til et tredje utfall som er det viktigste designvalget i hele strukturen. Midtbåndet er et ekte funn, ikke en feilet test. Hvis fenomenet inntreffer omtrent halvparten av gangene uten skjult struktur under, *er* det svaret — fenomenet er intrinsisk seed-variabelt — og ikke et rop om mer compute. Vi pre-registrerte det utfallet nettopp for å lukke uendelig-escalation-fellen: uten et definert midtbånd kan et tvetydig resultat alltid begrunne én kjøring til, i det uendelige.

For å skille et optimaliserings-artefakt fra et trekk ved reward-landskapet pre-registrerte vi en diagnostisk signatur, SIG-EXPLORATION: hvis variansen i policyen (`actor_logstd_mean`) ikke kollapser samtidig som critic-en (`value_loss`) konvergerer lavt, ligger sliden på optimaliserings-siden. Signaturen leses av logger som allerede finnes — den koster ingen ny trening.

### 2.6 Reproduserbarhet

Hele beslutnings- og evidens-sporet ligger som en ADR-kjede i versjonshistorikken, kronologisk, stub før resolusjon. Hver terskel, hver gate, hvert utfall peker på en commit-hash. Alle kjøringene papiret bygger på kommer fra ett seed-sett mot identisk konfig, og figurene og tabellene er sporbare til det samme datasettet — ikke til et tidligere sett som gikk tapt. ADR-kjeden er den reproduserbare appendiksen; plotting-scriptene ligger ved siden av figurene de genererer.
