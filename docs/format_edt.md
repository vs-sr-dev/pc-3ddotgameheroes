# Formato EDT — i personaggi voxel dell'editor

**Stato: risolto.** Il percorso arriva **esattamente sull'ultimo byte in 90 file
su 90**, per 260.860 voxel. Parser: [`tools/edt.py`](../tools/edt.py).

È il formato con cui il gioco descrive un personaggio disegnato dot per dot —
quello che gli dà il titolo. Leggerlo vuol dire poter mostrare il protagonista
che il giocatore ha fatto invece di un modello di riserva.

```
python tools/edt.py info  <file.edt>        intestazione, pose, voxel
python tools/edt.py sheet <dir> out.png     il provino a contatto dei 90
python tools/edt.py check                   le verifiche interne (6 proprietà)
```

Tutto big-endian, e **niente allineamento**: è un flusso di byte, quindi una
stringa di lunghezza dispari sposta di uno tutto quel che segue. È il motivo per
cui `angel.edt` ha il corpo a `0x36` e `default_01.edt` a `0x30`.

## Il file

| | campo |
|---|---|
| `'EDTFILE1.9'` + 2 byte a zero | magic, 12 byte |
| `u32 len` + `len` byte | **autore**, UTF-8 (`プレイヤー`) |
| `u32` | bandiera, 0 o 1 |
| `u32 len` + `len` byte | **nome del personaggio** (`勇者の子孫`) |
| `float[14]` | parametri dell'editor, tutti interi piccoli (0–10) |
| `u32` | **numero di parti**, che è 6 in tutti e 90 i file |

e poi, per ogni parte:

| | campo |
|---|---|
| `u32` | numero di voxel |
| `voxel[]` | 20 byte l'uno |
| `float[6]` | coda della parte |

La coda sta **dopo** ogni parte, anche l'ultima: è così che il conto torna al
byte. Trovarla è stata la sola cosa che il primo percorso ha sbagliato — si
fermava 24 byte prima della fine, e 24 è esattamente sei float.

## Il voxel

Venti byte: `u32` posizione più `float[4]`.

```
posizione   0x00 XX YY ZZ    il primo byte è sempre zero, e i tre seguenti
                             stanno tutti fra 0 e 15
float[0..2] colore RGB in 0..1
float[3]    da 0 a 6, sette valori interi: la finitura
```

**Sedici per lato non è un numero qualsiasi**: è la stessa griglia di
`data/shaders/water_col.dds`, che ha 16 quadretti per lato perché una casella
del mondo è sedici dot (sessione 5). Il personaggio dell'editor sta quindi in
un cubo di **16×16×16 per parte**, cioè una casella — e una casella è anche
l'altezza di un personaggio, misurata a sua volta per un'altra strada in
sessione 4. Tre file che non si conoscono, la stessa unità.

## Le sei parti sono sei pose

I conti lo dicono da soli: in `angel.edt` sono 261, 256, 246, 240, 263, 267
voxel. Sei numeri così vicini non sono sei pezzi di un corpo — la testa e un
braccio non hanno lo stesso volume — sono sei volte lo stesso personaggio.

Lo confermano due misure:

- fra la prima parte e le altre cinque, il **60,4%** dei voxel sta nella stessa
  posizione;
- le sei scatole si sovrappongono tutte, e occupano lo stesso volume.

Che è la stessa cosa già letta da un'altra parte in
[`entities.md`](entities.md): i personaggi di questo gioco **non hanno
scheletro**, e i figli di un nodo sono fotogrammi interi. Là erano da 2 a 6;
qui sono sei, sempre — perché l'editor ne fa sempre sei, e il gioco ne usa
quanti gliene servono.

## Avanti è la Z minima

Il primo provino usciva **di spalle**, e a dirlo è stato chi lo guardava senza
sapere cosa aspettarsi. Non era un difetto di lettura: prendendo la Z massima
si ottengono le nuche — niente occhi, solo capelli — e prendendo la minima
compaiono le facce.

Cioè i personaggi dell'editor sono authorati **verso −Z**, che è esattamente la
convenzione che [`entities.md`](entities.md) aveva già dedotto in un'altra
sessione, guardando le mesh del gioco con `view.py char c_npc_05 --azim 180`.
Due file diversi, scritti per scopi diversi, la stessa convenzione.

E si misura senza guardare, il che la rende una proprietà e non un'impressione:
in `black_smith.edt` il piano davanti porta **9** voxel e quello dietro **40**.
Una faccia è incavata — occhi, bocca — e una nuca è piena.

## La verifica che conta

Il provino a contatto: 90 personaggi disegnati prendendo, per ogni colonna, il
voxel più avanti. Non è un render — è un modo di guardare i dati — e basta a
riconoscerli tutti: cavalieri, maghi, Babbo Natale, un re con la corona,
draghi, scheletri con gli occhi rossi, un orso, una zucca. E i quattro preset
che si controllano a occhio tornano col proprio nome di file: `angel` ha
l'aureola e le ali, `dragon` le corna, `black_smith` la barba bianca e il
grembiule, `boxer` i guantoni.

## Cosa resta

- **I 14 parametri dell'intestazione**: interi fra 0 e 10, e cambiano da
  personaggio a personaggio. Hanno la forma degli attributi che l'editor
  dichiara, ma nessun oracolo li lega ancora a niente.
- **La coda di sei float** per parte.
- **La finitura** (0–6): sette valori, e non si sa cosa scelgano.
- **I `.SAV`**: sono un'altra cosa. Nessun magic, cominciano subito con la
  stessa coppia `u32 len + UTF-8`, e `test.SAV` porta dentro
  `edt/preset/pumpkin.edt` — quindi un salvataggio **riferisce** un preset per
  percorso invece di incorporarlo. Tre file, ~210 kB l'uno.
