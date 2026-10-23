# Il renderer, ricavato dagli shader

Ottenuto estraendo le stringhe dai pacchetti shader in `data/shaders/`:
**1.200 programmi Cg** (magic `CGB`) e **107 identificatori distinti**, con
convenzione `at*` per gli attributi di vertice e `g*` per gli uniform.

Nessun reverse engineering del bytecode: sono le tabelle dei simboli dei
programmi compilati.

## Modello

Renderer **forward**, fino a **4 luci** simultanee, con matrici e vettori
disponibili in tre spazi (model, view, world) — tipico di un motore che sceglie
lo spazio di illuminazione in base al materiale.

## Attributi di vertice (13)

```
atPosition0  atNormal0  atColor / atColur0  atTexCoord0
atTangent0   atBinormal0
atBlendIndex atBlendWeight
atWorld0 atWorld1 atWorld2 atWorld3
```

Tre conferme incrociate importanti:

- `atPosition0 · atNormal0 · atColor · atTexCoord0 · atTangent0 · atBinormal0`
  sono **esattamente i sei attributi** del vertice a stride 76 decodificato in
  [`format_dsb.md`](format_dsb.md). Conferma indipendente di quel lavoro.
- `atBlendIndex` + `atBlendWeight`, insieme a `gWorldViewMtxPalette`,
  confermano lo **skinning con palette di matrici**. Da qui era nata la
  predizione che il vertice a stride 88 fosse i 76 byte più indici e pesi degli
  ossi: **smentita**. La dichiarazione del vertice, che nel frattempo si è
  trovata nel formato DSBF, dice che gli 8 attributi sono i sei soliti più un
  secondo set di UV e un `ubyte4` ignoto — e che *nessun* vertice sul disco
  porta pesi. Lo skinning vive quindi tutto nei 77 record `skin`.
- `atWorld0..3` è una **matrice di mondo per istanza nello stream di vertici**:
  hardware instancing.

`atColur0` è un refuso degli sviluppatori rimasto nel binario, come
`SetDofApaerture` nell'API Lua (RECON §6.7).

## Illuminazione

Per ciascuna delle 4 luci: `gLightAmbient`, `gLightColor`, `gLightAttenuation`,
`gSpotLightCutoff`, più direzione e posizione in model/view/world space e
`gSpotLightDir` — quindi **direzionali, puntiformi e spot**.

In più un blocco di **rim lighting**: `gRimSpecularLightColor0..3` e
`gRimSpecularParam`. Materiale: `gMaterialDiffuse`,
`gMaterialDiffuseAttenuation`, `gMaterialEmission`, `gMaterialSpecularPow`,
`gGlobalAmbientAndMateAlpha`.

## La luce, e chi ce l'ha già — `view.sky_profile`, `view.py light`

Gli uniform qui sopra dicono *quali* luci la pipeline accetta. Quali siano
**accese in una mappa** è un'altra domanda, e la risposta è che nel dato di
mappa non ci sono affatto:

```
record `light` (tipo 9) nei 167 .pac delle mappe        0
record `light` in tutto il disco                      400   una per file
  di nome `ambient-environment-light`                 399
  cono 0,69813 rad = 40 gradi, decadimento +inf     400/400
```

Quaranta gradi e decadimento infinito sono i valori di partenza
dell'esportatore, e il colore lo conferma: 336 luci bianche e 62 dello stesso
beige, distribuite su un insieme che non ha senso di gioco — otto boss, sette
mappe d'interfaccia del sotterraneo, `NameEntry`, `Option`. È l'ambiente di
lavoro di chi ha esportato, non l'illuminazione della scena. Il colore
ambiente dell'header (`+0x60`) vale `0,8 0,8 0,8` in 399 file su 399.

### Perché non serve: è cotta nei vertici, e in un mondo di cubi si rilegge

Le normali di questa geometria sono **sei**, quindi basta raggruppare i colori
di vertice per faccia. Su `field_16`:

| faccia | vertici | luminanza |
|---|---:|---:|
| in su | 409.989 | 0,969 |
| sud | 132.357 | 0,709 |
| ovest | 167.995 | 0,703 |
| nord | 208.204 | 0,697 |
| est | 172.619 | 0,695 |
| in giù | 31.305 | 0,494 |

I **quattro fianchi concordano entro l'1%**: non è una lambertiana, che avrebbe
un lato chiaro e uno scuro, ma una luce d'ambiente **verticale** — il cielo. E
non è un caso di una mappa: sulle 40 di campagna la mediana dello scarto fra i
quattro fianchi è **2,8%**, e la faccia in su è più chiara in 38 su 40.

**La prova è che il verso si inverte.** Al chiuso la stessa misura dà il
contrario, e con i fianchi ancora più concordi:

```
                su/fianchi   giù/fianchi   scarto fra i fianchi
campagna  40       1,415         0,661            2,8%
chiuso   126       0,822         1,000            0,1%
```

Dove c'è un soffitto la faccia in su è la **più scura**, e quella in giù torna
al livello dei fianchi perché sotto non c'è più un cielo da cui distinguersi.
Un numero che si comporta così è luce.

### E i posti si mettono in fila da soli

Il rapporto su/fianchi, letto per località — i nomi sono quelli che
`MapParameter` dichiara, non nostri:

```
1,52  Dash Circuit          0,82  i sette templi (0,814-0,822)
1,47  Lake Garland          0,78  Sacred Cave
1,45  Nuntra Desert         0,75  Fairy's Cave, Rat Hole, Cave
1,40  Gilgamesh Beach       0,73  Grave of the Hero
1,38  Brilord Plains        0,68  Mountain Path, Fairy Spring
```

Spiagge, pianure e deserto in cima; in fondo, **sotto i templi, le grotte**. La
misura ordina i posti del gioco come li ordinerebbe chi ci cammina, e nessuno
di questi nomi è entrato nel conto.

Le due sole mappe `field_*` che si comportano da chiuso sono `field_50` e
`field_91`, che è **la corte del castello**.

### Chi va illuminato, e con che luce

La regola non è «mappa sì, personaggi no», ed è misurata due volte. Il colore
di vertice è illuminazione dove **varia dentro una stessa direzione di
faccia** — dove cioè c'è occlusione cotta vertice per vertice, che il cielo da
solo non spiega:

```
campagna   scarto entro i fianchi  42%     241 livelli distinti
chiuso                              3%       8 livelli
```

I sotterranei ne portano **due soli** (`d_1_1_1`: un verde muschio e il nero),
e due livelli non sono una luce: lì la geometria va illuminata come tutto il
resto, o le pareti diventano una massa sola. La soglia (30%) non è a occhio —
una seconda misura che non sa niente della prima, *«la faccia in su è più
chiara dei fianchi?»*, taglia le mappe nello stesso posto: **165 su 167**.

Non possono portarla, per costruzione, i **modelli di libreria**: un vaso
istanziato 1.022 volte non ha nei propri vertici la luce di 1.022 posti. E
infatti `c_obj_all` ha le sei facce entro il **5%** l'una dall'altra — lì il
colore di vertice è la tinta.

A chi resta si dà **ambiente più sole**, che è la forma che il disco dichiara,
con i suoi numeri:

- `Event:SetSunLightAngle(5.65,62.59); -- yaw, pitch` — il commento è degli
  autori. 16 chiamate, 8 valori distinti, **tutti i pitch fra 57,75 e 86
  gradi**: il sole di questo gioco è sempre alto. Mediana 73,5.
- `SetParallelLight(0.15,0.15,0.15, 0.08,0.08,0.08)` — due terne, la prima
  sempre più chiara: diffusa e ambiente. Il rapporto `amb/(amb+dif)` vale 0,29,
  0,35 e 0,43, mediana **0,35**.

E l'ambiente non è piatto: segue il profilo verticale che *quella* mappa
mostra nei propri vertici, così chi cammina in una grotta prende la luce della
grotta. L'unica cosa rimasta nostra è che gli yaw, a differenza dei pitch, sono
sparsi da −180 a 31 — sono della scena, non del mondo — e qui se ne prende uno.

### Cosa cambia in un fotogramma

Quel che è sparito è una **direzione orizzontale che il dato non ha**: la
lambertiana di prima veniva da `(0,4 0,8 0,45)`, cioè 42 gradi di azimut, e
spegneva a 0,35 i due fianchi che le davano le spalle — sopra un colore che era
già la luce del posto. Su `field_16`:

```
                   luminanza media   sotto 0,15   mediana
prima                    0,195          47,9%      0,160
dopo                     0,295           5,9%      0,281
```

Metà schermo stava sotto 0,15. Gli alberi rivolti a nord e a ovest erano neri.

## Chi brilla di suo — il campo `emission`

Cercando le torce si è trovato l'opposto: le torce **non** sono sorgenti
dichiarate, e qualcos'altro sì. Il campo `emission` del record `material` non
era mai stato usato dal renderer, ed è pieno:

```
materiali con emissione non nulla      277 su 1.792 = 15,5%
  la tavolozza del CharEditor          166   emissione 1 su tutti i canali
  in c_obj_all                          33   di cui 21 lame magiche
  gli altari delle sfere                  5
```

**Il caso limite dice come va letta.** I 166 del `CharEditor` sono la tavolozza
dell'editor del personaggio e valgono `1, 1, 1`: un pannello d'interfaccia non
riceve luce, si mostra a colore pieno. Quindi l'emissione non è un addendo — che
li saturerebbe a bianco — ma un **pavimento**: `luce = max(illuminazione,
emissione)`, per canale. Con questa lettura il caso dell'interfaccia torna da
solo e niente satura.

E gli altri sono esattamente le cose che in un gioco brillano:

```
MR_i_mwp_06_light   emis (1.00, 0.32, 0.11)   diff bianco     lama rosso fuoco
MR_i_mwp_12_light   emis (0.15, 0.64, 0.87)   diff bianco     lama azzurra
MR_i_mwp_15_light   emis (0.22, 0.83, 0.18)   diff bianco     lama verde
MR_i_mwp_22_light   emis (1.00, 0.38, 0.99)   diff bianco     lama magenta
MR_c_enm_10tamaa    emis 0,30                 玉, il proiettile del nemico
RM_c_bos_bullet     emis 0,60                 il proiettile del boss
```

Le **21 lame magiche** hanno diffuse bianco e tutto il colore nell'emissione:
la lama è una sorgente, e il colore di ciascuna è dichiarato uno per uno. Il
nome del materiale finisce in `_light` in 21 casi su 21.

### Le sei sfere, e uno scambio di materiale

I cinque emissivi della libreria di mappa sono le sfere degli altari, e
leggerne il colore chiude un cerchio della sessione 12 — che aveva stabilito
l'ordine degli altari dai nomi degli item, senza poterlo vedere:

| altare | mappa | l'item dello script | materiale | colore | il walkthrough |
|---|---|---|---|---|---|
| 4116 | `D_1_3` | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `D_2_3` | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `D_3_3` | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `D_4_3` | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `D_5_3` | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `D_6_3` | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

**Sei su sei** con i nomi che il walkthrough usa, e i due nomi interni che non
descrivono un colore — `gray` e `white` — sono proprio i due che il modello
smentisce: la sfera è arancione e viola. Il nome che il gioco mostra vince su
quello che gli autori si sono scritti.

Due cose viste per averle guardate invece che dedotte:

- `m_obj_118_b` usa il materiale `orb_121` e `m_obj_121_b` usa `orb_118` — uno
  **scambio esatto**, negli altri quattro il numero combacia. Dedurre il
  materiale dal numero del modello avrebbe dato due colori sbagliati; a dirlo è
  l'indice a `+0x00` del chunk.
- `orb_121` è **l'unico dei sei senza emissione**. L'anomalia segue il
  materiale e non il posto, quindi finisce sulla sfera del terzo tempio, che è
  l'unica delle sei a non brillare.

## Ombre

Due shadow map: `gShadowMap0_stage4`, `gShadowMap1_stage8`, con
`gShadowMapParams`, `gShadowMapPolygonOffset` e le matrici di proiezione
ombra nei tre spazi (`gModelShadowMtx0/1`, `gViewShadowMtx0/1`,
`gWorldShadowMtx0`). Due mappe possono voler dire cascade oppure due
proiettori distinti.

## Superfici

- **Normal mapping**: `gNormalMap_stage2`, con `gNormalMapBaseAxisR` e
  `gNormalMapBaseAxisG` — la convenzione dei canali è configurabile, quindi
  l'orientamento del verde non va dato per scontato.
- **Parallax mapping**: `gParallaxMapParams`.
- **Environment mapping**: `gCubeEnvironmentMap_stage3` oppure
  `gSphereEnvironmentMap_stage3`, con `gEnvironmentMapColor` e
  `gEnvironmentMapFresnel`. È qui che entra `ref_01.dds`, l'unica cubemap del
  gioco, e il riflesso pesato per Fresnel dell'acqua descritto da YEBIS.
- **Depth of field**: `gDOFParams` — il DOF di YEBIS arriva agli shader come
  uniform, pilotato dal Lua (RECON §6.7).
- Vari: `gAlphaTestParams`, `gPolygonOffset`, `gTexCoordMatrix0..2`,
  `gUtilityColorTexture_stage1` / `gUtilityColorCubeTexture_stage1`.

## Assegnazione degli stage di texture

| Stage | Contenuto |
|---:|---|
| 0 | colore base |
| 1 | utility color (2D o cube) |
| 2 | normal map |
| 3 | environment map (cube o sphere) |
| 4 | shadow map 0 |
| 8 | shadow map 1 |

## Perché conta

Questo è, di fatto, **la specifica del sistema di materiali** che l'host dovrà
fornire: quali attributi accetta la pipeline, quali uniform pilotano il
materiale, quante luci, quali mappe e in quali stage. Riscrivere gli shader in
GLSL o HLSL diventa un lavoro di traduzione a interfaccia nota, invece che di
ricostruzione per tentativi.

L'assegnazione degli stage qui sopra ha poi trovato una **conferma indipendente
nei dati**: i record `material` dei `DSBF` hanno quattro slot di texture, e la
posizione nello slot coincide con lo stage. Nello slot 2 finiscono solo file
`*_nm` / `*_nml`, nello slot 3 solo `forref_*`, e lo slot 1 non è mai usato —
vedi [`format_dsb.md`](format_dsb.md) §material. Sono agganciati anche diffuse,
ambient, emission, specular e l'esponente speculare.

Resta da collegare gli uniform rimanenti: i 43 identificativi di shader del
campo material +0x28, e i **tag numerici** delle tabelle di binding dei `DSBF`,
che associano ogni `float4` a un registro di costanti.
