# `MAP_ALIGNMENT/*.DAT` — the maps' logical grid

**Status: layout solved, passage semantics solved.** Five fields of the record
and the tag values are still to be named.
Parser: [`tools/mapdat.py`](../tools/mapdat.py).

170 files in `PS3_GAME/USRDIR/DATA/MAP/MAP_ALIGNMENT/`, 34 MB. They are the
**only little-endian files on the disc**: everything else in 3D Dot Game
Heroes is big-endian, as the PS3's PPC wants. If a field makes no sense here,
the first thing to try is the other endianness.

They describe a map's *logical* grid — where events, enemies and passages
are. `D_1_1_1` has a 112 × 96 logical grid and a 7 × 8 grid of screens in the
`.pac`.

The two grids are not independent: **the ratio is always an integer**, and it
is the size of one screen in cells (16 × 12 in dungeons, 16 × 16 in the
overworld). A cell is **1.6 world units**, the same as a character's height.
The map is composed from this — see [`format_pac.md`](format_pac.md) — and
from this comes the coordinate system the scripts speak in: origin at a
corner, positive X to the right, negative Z downwards,
`SetPlayerPosition(cx, cy, floor)`.

This file is also the **external oracle** the composition is checked against:
its field at +0x00 is `0xFFFFFFFF` outside the map, so it says cell by cell
where the geometry has to be. `python tools/view.py layout` runs the
comparison over every map on the disc.

## Format

```
header
  +0x00 u32       8, 16 or 32 — constant per group of maps (16 in 140 files)
  +0x04 u32       w, cells across
  +0x08 u32       h, cells down
  +0x0C u32       ?
  +0x10 u32       len
  +0x14 char[len] map level string

then exactly w*h records, one per cell, in row order
  +0x00 u32       region identifier, 0xFFFFFFFF outside the map
  +0x04 u32       ?   (0 in 91%)
  +0x08 u32       ?   (0xFFFFFFFF in 56%)
  +0x0C u32       ?
  +0x10 u32       ?   (0 in 97%)
  +0x14 u32       ?
  +0x18 u32       len1
  +0x1C u32       len2
  then len1+len2 bytes of text, with no terminator and no alignment
```

### Why it is certain

A format of variable-length records offers a very hard oracle, and it pays to
use it: walking it record by record — string lengths included — has to end
**exactly** on the last byte of the file after `w*h` records. It does in
**170 files out of 170**.

With a wrong record size the walk leaves the file almost at once. Before that,
the size had already been narrowed to 32 bytes by comparing
`len(file) − w·h·size`:

| Size | Mean remainder |
|---:|---:|
| 16 | 50.3% |
| 24 | 25.4% |
| 28 | 13.0% |
| **32** | **0.5%** (max 1.9%) |

36 gives a negative remainder everywhere. Only 32 leaves something of the
order of 1% over, which is exactly the strings.

## The strings

The first is the **parameters**, in the same flag syntax as the Lua API; the
second is usually the object's **class**.

```
params = "D_1_2;-gfrom_d_1;-right"     cls = "Warp"
params = "-g11;-o02;-f0;-e1;-ex0;"     cls = ""
params = "-g112;-o112;"                cls = "destructionWall"
```

> **But "usually" is not enough.** In 14% of cases (294 of 2,170) the second
> string itself contains a `;` and is a *second specification*, not a class
> name:
>
> ```
> params = "-g110;-o102;"              cls = "D_7_1_2;-g212;-o102;"
> ```
>
> Reading only the first string, or filtering on the `Warp` class, loses half
> the graph: 192 edges instead of 320. The symptom that gave it away was that
> reciprocity was only 64% — too low for a world you can walk through.

Across the disc: 1,111,469 cells, 56% of them empty, **14,099 with an
object** and 615 distinct classes. The most frequent are `Exit` (397), `Warp`
(240), `observer` / `Observer` (303 together), `SwitchObserver` (80),
`EnemyObserver` (65), `destructionWall` (46), `PitFall` (21). In 11,929 cells
the class is empty and there are only parameters.

The most used flags: `-s` (10,196), `-g` (3,357), `-o` (2,795), `-i`
(1,161), `-f`, `-e`, `-ex`, `-p`, plus direction words (`right`, `up`,
`down`).

## Passages — how the world is navigated

This is the part that is actually needed, and it is solved.

> A `Warp` carries `<destination map>;-g<name of the arrival point>;-<direction>`.
> In the destination map there is an object — usually an `Exit` — that
> **declares that name** with the same `-g` flag.

The gate name is therefore the key that joins the two maps, not a coordinate.
A complete example:

```
D_7_1_1  cell (87,60)  Warp  "D_7_2_1;-gd_7_1o;-right"
D_7_2_1                Exit  "-gd_7_1o"
```

Three independent checks, all over the whole corpus:

| | |
|---|---|
| arrival point present in the destination | **508 of 511** |
| destinations that match a `.pac` | **140 of 143** |
| edges that also have the way back | **305 of 320 (95%)** |

Reciprocity at 95% is the strongest proof: a world is crossed in both
directions, and a wrong extraction does not produce that number by chance —
the first version, which read only the first string, stopped at 64%.

The few exceptions explain themselves and are defects of the published data,
not of the parser: `D_7_3` points at `D_7_2` when the real maps are
`D_7_2_1`…`D_7_2_9`; one file writes `d7_1_4` without the underscore; there is
a destination called `test`; and `D_0_2` — a map that contains a single
object, that warp — looks in `Field_11` for a gate that does not exist there,
in the company of the various `-gDebug` and `CAPTURE0000` scattered through
the corpus.

The final graph has **146 maps and 320 edges**, and it reads well:
`d_1_1_1 → d_1_2 → d_1_3` is the chain of rooms of the first dungeon,
`d_1_1_1 ↔ field_16` is the way out to the outside, and `field_16` alone opens
onto eight maps, dungeons and neighbouring areas.

## Map NPCs

271 cells across the disc have as their class **an NPC's identifier and
nothing else** — `a1_010`, `b8_010`, `a11_120`: a letter, one or two area
digits, an underscore, three digits — with no parameters and nothing more. 236
distinct identifiers.

These are the positions of the characters that stand on the map before an
event begins. The scripts name them as *archetype + identifier*
(`OldWomana6_010`), so the tail of the name is the join key, as the gate name
is for passages. See [`entities.md`](entities.md).

```python
mapdat.npc_spots(dat_bytes)   # -> {'a1_010': (7, 11), ...}
```

## What is missing

- The five record fields between +0x04 and +0x14.
- The exact meaning of the field at +0x00, which has 215 distinct values on
  the disc. It is **not** an object identifier, and that is an easy mistake to
  make: in `D_1_2` the value `0x7D1` covers 360 cells out of 520 while there
  are 10 objects. It is rather a **region** identifier — `0xFFFFFFFF` in 56% of
  the disc's cells, that is outside the map, and otherwise low values (`0x1`,
  `0x15`, `0x25`) or values in the `0x7D1`…`0x7DD` band, depending on the map.
  Nor is it the object's class: `Exit` appears with `0x1`, `0x15` and `0x25`.

  **One value does have a name** (session 6): `119` is **water**.

  As always in this project, an external oracle says so. The collision file
  says which cells have the backdrop stretched under the map as their only
  surface — the sea, the moat, the gorge between two plateaus — and there are
  40,964 of them across the disc (see [`walk.md`](walk.md)). Compared with the
  tag:

  ```
  88.4% of water cells carry tag 119
  85.1% of cells with tag 119 are water      (the tag is one cell wider)
  ```

  Map by map, where `119` appears it carries **98–100%** of them. And it is
  **a single value across the disc**, not one per group of maps as written in
  session 5: that hypothesis came from confusing two different things.

  They are different because **water** (the backdrop is the only surface) and
  **void** (no collision at all, 55,477 cells) do not coincide, and the tag
  declares only the first — among void cells `119` is barely 10%. The void is
  rather the gap between the declared rectangular region and the real map, and
  that needs no tag.
- The header field at +0x0C.
- The join with the `map_manager` enum extracted from the Lua, which has 216
  members such as `MS_FIELD_50`, `MS_DUNGEON_5_1_1`, `MT_FIELD`: they are the
  same map names, but the numeric values are native and arrive with Phase 3.

## Use

```
python tools/mapdat.py info  <file.DAT>
python tools/mapdat.py cells <file.DAT>                 histogram of the tags
python tools/mapdat.py graph <dir> --pac <dir of .pac>  graph of the passages
```

`--pac` turns the checks on: how many destinations really exist and how many
edges have the way back.
