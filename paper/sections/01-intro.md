## 1 Introduksjon

### 1.1

I companion-AI for dyr er overpåstand den dokumenterte feilmoden. Stavros Ntalampiras' arbeid fra 2019 viste at en algoritme kunne skille kattens mjau i tre kontekster — en smal, etterprøvbar påstand med dekning i dataene [ref]. MeowTalk bygde på det grunnlaget og markedsførte oversettelse av kattens vokalisering; en av appens egne skapere innrømmet overfor New York Times at dette ikke er ren vitenskap på dette stadiet [ref]. Avstanden mellom de to — solid smal vitenskap og produkt-påstanden som strakk den — er feilmoden vi designer mot.

Animal-computer interaction har et motstykke. Cat Royale-arbeidet argumenterer for at designet av selve verdenen et system opererer i — og menneskelig involvering i dyrevelferd og breakdown-recovery — er like sentralt som teknologien selv, ikke en ramme rundt den [ref], forankret i eksplisitte etiske prinsipper: non-maleficence, beneficence, voluntary participation [ref]. Det er den linjen vi plasserer oss i.

Men dette papiret handler ikke om et ACI-resultat. Det handler om evaluerings-metoden som hindret oss i å gjøre den samme feilen i motsatt retning — å rapportere et rent negativt funn som var like ufundert som et overdrevet positivt.

### 1.2

RL-evaluering pre-registrerer sjelden. Når den gjør det, registreres terskelen, men ikke om terskelen er adskillbar fra støyen i vinduet den måles mot. Det er hullet.

En terskel T kan valideres mot utfalls-spennet — avstanden fra peak til slutt — og se meningsfull ut. Den samme T kan være støy-dominert i ep_init-vinduet den faktisk anvendes mot. Når den er det, er spørsmålet om en gitt seed passerer nær et myntkast. Resultatet leses som et funn om agenten; det er et funn om vinduet.

### 1.3

Vårt bidrag er en kriterie-validitet-gate: en pre-registrert sjekk, kjørt før terskelen anvendes, på at T er adskillbar fra støy-differansen i sitt anvendelsesvindu. Operasjonelt krever vi at T ligger minst rundt to ganger over støy-differansen i vinduet. Gaten er registrert sammen med metoden, ikke lagt til etterpå.

Vi rapporterer tre tilfeller der gaten endret utfallet. Ingen av dem er hypotetiske — hver er målt, og hver peker på en committed forutsetning i en ADR-kjede som utgjør papirets reproduserbare appendiks. Det negative utfallet er bidraget: at vi ikke kunne avgjøre fenomenet, sammen med den presise grunnen til at ingen rimelig mengde compute ville endret det, er et sterkere metodisk resultat enn et tall vi måtte presse fram.

### 1.4

Papiret avgrenser hva det påstår. Det påstår ikke at fenomenet vi observerte — climb-then-slide, der agenten når baseline og ikke holder den — er løst. Det påstår ingen fiks; warm-start, KL-anker og reward-reshaping er alle ikke-valgt og ligger nedstrøms. Det påstår ikke at simulatoren er virkelighetstro; sim-to-real-gapet er udokumentert til v0.4, og vi noterer det eksplisitt. Diagnosen vi gjorde — at sliden ligger på optimaliserings-siden, ikke i reward-landskapet — er diagnose, ikke fiks, og presenteres som det.

### 1.5


