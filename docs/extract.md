# L'estrattore — `tools/iso.py`

Fase 1a. Serve a rendere `extract/` **riproducibile**: 3,1 GB che finora
esistevano come stato locale non ricostruibile, e che per la politica BYOA non
possono stare nel repository. Ora sono una funzione del disco.

```
python tools/iso.py index                 riscrive tools/iso_index.tsv
python tools/iso.py sets                  cosa e' dichiarato, con i totali
python tools/iso.py manifest              calcola tools/manifest.tsv (sha256)
python tools/iso.py extract [set ...]     estrae in extract/
python tools/iso.py verify [set ...]      confronta extract/ col manifesto
python tools/iso.py magic '<glob>' [n]    primi byte dei file che corrispondono
```

Sul disco di riferimento: **2.799 file, 3,3 GB**; il manifesto ne dichiara
**2.793 per 3,1 GB**, calcolati in 26 secondi.

## UDF, non ISO9660

Il disco monta entrambi i filesystem e non sono equivalenti: i nomi ISO9660
sono **troncati a 31 caratteri** e maiuscolizzati, quindi `d_1_1_1.ps3.pac.gz`
diventa `D_1_1_1_PS3_PAC.GZ`. Non è cosmesi. In questo gioco i nomi sono dati:
il materiale riferisce la texture *per nome di file*, la cella della griglia è
codificata nel nome della mesh, e le destinazioni di `MAP_ALIGNMENT` sono nomi
di mappa. Si estrae via UDF.

La verifica lo ha mostrato subito: i `.pac.gz` presenti in locale risultavano
**mancanti**, perché erano stati estratti in passato con 7-Zip e portavano i
nomi troncati.

### Perché un lettore scritto a mano

`pycdlib` è installato e rifiuta questo disco:

```
PyCdlibInvalidISO: UDF File Set Tag identifier not 256
```

Ha ragione a modo suo. I Blu-ray PS3 usano UDF 2.50 con **partizione di
metadati**: la seconda mappa di partizione del Logical Volume Descriptor,
identificata da `*UDF Metadata Partition`. Gli inode non stanno nella
partizione fisica, ma dentro un *file* di metadati (tipo 250) che la ricopre; le
estensioni di quel file **sono** i blocchi della partizione logica dove vivono
il File Set Descriptor e tutte le directory. Chi ignora quel livello di
indirezione va a leggere dove si aspetta un FSD (tag 256) e ci trova un File
Entry (tag 261) — esattamente l'errore qui sopra.

La catena completa dei descrittori è nel docstring di `tools/iso.py`. Sono circa
150 righe di Python e tolgono una dipendenza esterna dal punto più basso della
pila.

Nota di merito al metodo: il file dichiara sempre dove sta la cosa successiva.
Non c'è stato niente da indovinare, solo da seguire — la stessa proprietà che
ha risolto `DSBF`.

## Il manifesto

`tools/manifest.tsv` è `path · size · sha256` per ogni file dichiarato: è
l'**impronta del disco supportato**, non contenuto del gioco, quindi sta nel
repository (è quello che fanno devilutionX e Ship of Harkinian). Permette tre
cose che prima non c'erano:

- riconoscere che un disco è quello giusto, prima di estrarre;
- verificare `extract/` senza rileggere la ISO (`verify`, ~30 s con `--deep`);
- accorgersi di un'estrazione fatta con lo strumento sbagliato.

Il disco di riferimento è **3D Dot Game Heroes (Europe), BLES-00860**.

## I set

`extract` senza argomenti estrae tutto; l'elenco dei set *è* la definizione di
cosa vuol dire "`extract/` completo".

| set | file | byte | contenuto |
|---|---:|---:|---|
| `script` | 618 | 5,3 MB | i `.lua.eu`, sorgente di gioco |
| `texture` | 763 | 623,3 MB | TPKG |
| `model` | 460 | 176,7 MB | DSBF |
| `map` | 167 | 441,5 MB | `.pac.gz`, + derivato: gunzip in `extract/pac/` |
| `collision` | 171 | 5,4 MB | DPK |
| `align` | 170 | 34,0 MB | griglia logica e grafo del mondo |
| `voxel` | 93 | 5,6 MB | EDT/SAV, editor dei personaggi |
| `shader` | 4 | 1,2 MB | pacchetti Cg (serve la tabella dei simboli) |
| `image` | 11 | 1,0 MB | PNG e DDS sciolti |
| `audio` | 326 | 638,3 MB | WAV |
| `movie` | 5 | 1,2 GB | Bink |
| `boot` | 2 | 21,6 MB | `EBOOT.BIN`, `PARAM.SFO` (Fase 3) |
| `font` | 1 | 1,3 kB | `Font.bin`, metriche del font di interfaccia |
| `devtool` | 2 | 24,0 kB | eseguibili Windows lasciati sul disco |

I passi **derivati** fanno parte del manifesto: senza di essi `extract/` non è
completo. Per ora ce n'è uno solo, la decompressione dei `.pac.gz` in
`extract/pac/`, perché tutto il resto della catena legge il `.pac` in chiaro.

Restano fuori apposta: `PS3UPDAT.PUP` (il firmware, 256 MB), `TROPHY.TRP`,
`LICDIR/LIC.DAT`, `PS3LOGO.DAT`, `PS3_DISC.SFB` — infrastruttura di
piattaforma — e `IconData/Thumbs.db`, che è una cache di miniature di Windows
finita sul master per distrazione.

## Due ritrovamenti

L'inventario dichiarato ha fatto emergere cose che nessuno stava cercando,
perché prima non esisteva un elenco di *tutto*:

- **`data/MakeLuaDump.exe`** (9,5 kB) e **`data/edt/addition/AdditionEditCharMessage.exe`**
  (14,5 kB): due utility Windows degli sviluppatori, rimaste sul disco stampato.
  Sono PE x86 minuscoli e, dal nome, uno serve proprio a *scaricare le tabelle
  Lua* — cioè fa il lavoro di `tools/lua_tables.py`. Vanno guardati: costano
  poco e possono confermare la semantica.
- **`Font.bin`** (1,3 kB): troppo piccolo per contenere glifi, quindi sono
  metriche o una mappa di caratteri, con le texture del font a parte in
  `UserInterface/Font`. Servirà alla milestone "primo dialogo".
