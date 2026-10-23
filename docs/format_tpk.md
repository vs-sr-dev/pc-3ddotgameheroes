# Formato TPKG — texture package

**Stato: risolto.** Validato su tutti i 763 pacchetti del disco, 4.033 texture,
622,9 MB di pixel, zero discrepanze. Parser di riferimento:
[`tools/tpk.py`](../tools/tpk.py).

Tutti i campi sono **big-endian**.

## Header — 0x20 byte

| Off | Tipo | Campo |
|---|---|---|
| 0x00 | char[4] | `'TPKG'` |
| 0x04 | char[4] | `'ps3\0'` — identificatore di piattaforma |
| 0x08 | u16 | versione. `4` su tutto il disco |
| 0x0A | u16 | numero di texture |
| 0x0C | u32 | offset dell'area dati |
| 0x10 | u32 | dimensione dell'area dati |
| 0x14 | u32 | fine della tabella dei mip |
| 0x18 | u32[2] | zero su tutti i pacchetti |

Invariante: `0x0C + 0x10 == dimensione del file`.

## Entry — 0x20 byte ciascuna, da 0x20

| Off | Tipo | Campo |
|---|---|---|
| +0x00 | u32 | offset **assoluto** del nome (stringa NUL-terminated) |
| +0x04 | u32 | dimensione totale del dato |
| +0x08 | u32 | offset del dato, **relativo** all'area dati |
| +0x0C | u32 | **formato pixel**: 9 = DXT1, 10 = DXT3, 11 = DXT5 |
| +0x10 | u16 | larghezza |
| +0x12 | u16 | altezza |
| +0x14 | u8 | **numero di livelli mip** |
| +0x15 | u8[3] | zero su tutte le entry |
| +0x18 | u32 | ignoto, varia per entry — 666 valori distinti, forse un indice |
| +0x1C | u32 | timestamp Unix di build, uguale per tutte le entry del pacchetto |

## Tabelle in coda

1. **Nomi** — stringhe NUL-terminated consecutive, puntate da +0x00.
2. **Mip** — inizia alla fine dei nomi **allineata a 4 byte** e finisce
   all'offset dichiarato in header 0x14. Contiene un `u32` con la dimensione
   di ogni livello, per ogni texture, nell'ordine delle entry. Il numero di
   livelli varia da texture a texture *anche all'interno dello stesso
   pacchetto*: va letto da +0x14, non dedotto dalle dimensioni.
3. Padding di zeri fino all'area dati.

## Distribuzione osservata

| Formato | Texture | % |
|---|---:|---:|
| DXT3 | 3.870 | 96,0% |
| DXT1 | 116 | 2,9% |
| DXT5 | 47 | 1,2% |

Numero di mip: `1:737, 5:491, 6:17, 7:20, 8:1249, 9:1244, 10:209, 11:66`.
Dimensioni più comuni: 256×256 (1.329), 128×128 (1.261), 16×16 (494),
1280×720 (361, schermate a schermo intero), 512×512 (216).

Timestamp di build: 441 distinti, da **2009-04-20** a **2010-02-01**.

## Due insidie

**Il formato pixel non è deducibile dalla dimensione.** DXT3 e DXT5 occupano
entrambi 16 byte per blocco 4×4 — e 16 byte per blocco 4×4 equivale
esattamente a 1 byte per pixel, quindi coincide anche con una texture a 8 bit
non compressa. Le tre ipotesi sono numericamente indistinguibili: il codice va
letto da +0x0C. La distinzione DXT3/DXT5 è stata risolta confrontando il canale
alfa decodificato nei due modi (l'interpretazione sbagliata produce bande
orizzontali regolari o bordi sfrangiati).

**DXT3 domina al 96%.** Insolito per un gioco del 2009, ma coerente con
l'estetica: l'alfa esplicita a 4 bit di DXT3 mantiene netti i bordi dei
sprite a voxel, dove l'alfa interpolata di DXT5 li sfrangerebbe.

## Cubemap

Una sola texture su 4.033 è una cubemap: `shaders/graphics.ps3.tpk` →
`ref_01.dds`, 256×256 DXT5, 9 mip per faccia. **Non esiste un flag esplicito**:
le 6 facce sono consecutive, ciascuna con la propria catena di mip, mentre la
tabella elenca i mip una volta sola. Il numero di facce si ricava dal rapporto
`size / somma(mip)`, che vale 6 solo per questa entry e 1 per tutte le altre.

## Conversione

Il payload è DXT standard, quindi la conversione a `.dds` è una semplice
riscrittura di header — nessuna trasformazione dei pixel, nessuno swizzle RSX.

```
python tools/tpk.py info   <file.tpk>
python tools/tpk.py survey <dir>              censimento e validazione
python tools/tpk.py export <file.tpk> <out>   scrive .dds e .png
python tools/tpk.py sheet  <file.tpk> <png>   provino a contatto
```

## Aggancio con le scene

Le texture sono referenziate **per nome `.dds`** dalla tabella stringhe dei
blocchi `DSBF` dentro i `.pac` delle mappe (vedi RECON §5). Il nome è quindi
la chiave di join fra scene e pacchetti texture: non servono indici numerici.
