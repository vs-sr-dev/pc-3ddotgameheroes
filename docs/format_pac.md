# The `.pac` format — the maps

**Status: solved, composition included.** The 167 map files open in full and
their geometry is extracted with the same parser as the models: 4,837
sections, 54,110 objects, **51,738,164 vertices**. Zero validation errors.
The sections are **screens to be composed**, and the composition is checked
against a file outside the format at 91.2% — see *A section is a screen*,
which corrects the opposite conclusion held until session 3.
Parser: [`tools/dsb.py`](../tools/dsb.py) (`blocks()`),
composition: [`tools/view.py`](../tools/view.py) (`screens()`, `load()`).

## Where they are

`PS3_GAME/USRDIR/DATA/MAP/PAC_DATA/` holds 167 `*_PS3_PAC.GZ` files and 338
`.TPK`. The `.GZ` files are ordinary gzip, with the original name in the
header — `D_1_2.ps3.pac` — and they weigh 441 MB compressed against **1.95 GB**
decompressed. The `.TPK` files beside them are the maps' textures, with names
that follow those of the `.pac` files.

167 maps: **127 dungeons** (`d_*`) and **40 overworld areas** (`field_*`).
The `field_*` maps are all 8×8 grids.

## The container

Trivial, once decompressed:

| Off | Field |
|---|---|
| 0x00 | u32 `n0` — columns |
| 0x04 | u32 `n1` — rows |
| 0x08 | u32[`n0*n1 + 1`] offsets of the sections |

Each section is a complete `DSBF` block, in the format described in
[`format_dsb.md`](format_dsb.md). The last offset is the file size.

Two traps:

- **sections are aligned to 0x80**, so the slice between two offsets is longer
  than the block. It has to be cut to the size the `DSBF` declares at its own
  offset 0x0C, or validation fails on the padding — and the failure looks like
  "the format does not add up", not like padding;
- **empty sections exist**: `field_01` has 32 of them out of 64, with zero
  objects and a sentinel bounding box `(1e8, 1e8, 1e8)…(−1e8, −1e8, −1e8)`,
  that is, inverted.

The count `n0 * n1` holds across all 167 files.

## The grid is in the mesh names

The section index breaks down into a cell: `c = i % n0`, `r = i // n0`.

This is not an inference: **the mesh names contain the cell**. A mesh of
section 8 of a 7×8 grid (so `c=1, r=1`) is called `md_kbe_L0_01_01-mesh`. The
match holds in **12,097 cases out of 12,097** — every single mesh of every map
on the disc.

The same name also carries the **LOD level**: `_L0_` and `_L1_` occur in
exactly equal numbers, in pairs on the same cell. Some of the meshes (the
scattered objects, not the terrain) have no LOD suffix.

## A section is a screen

**A section is one screen**, drawn around its own origin, and the map is
obtained by putting section `(c, r)` in its place in the grid:

```
offset(c, r) = ( ((c + ½)·cw − w/2)·1.6 ,  0 ,  −((r + ½)·ch − h/2)·1.6 )
```

where `w × h` is the logical grid declared by the
[`MAP_ALIGNMENT`](format_mapdat.md) of the same name, and `cw = w/n0`,
`ch = h/n1` is the size of one screen in cells. **A cell is 1.6**, which is
also the height of a character (see [`entities.md`](entities.md)).

The ratio is an integer, never an arbitrary number: **16 × 12 cells** per
screen in dungeons (43 maps) and **16 × 16** in the overworld (39), plus the
single-screen maps where the screen is the whole map. `d_1_1_1` has 7 × 8
screens and a 112 × 96 logical grid.

### The proof, and the error it corrected

Until session 4 this document claimed the exact opposite: that the sections
were *cullings* already in the map's own coordinate system, to be drawn
without composing anything. It is worth keeping here how that belief came
about and what disproved it, because the error was a reasonable one.

The three observations that seemed to prove it:

- mesh names are all distinct across sections — true, but they are names, not
  geometry;
- 79% of a section's vertex positions reappear **identical** in the
  neighbouring one, with no translation — true, and it looked decisive. But a
  dungeon is built from **repeated blocks**: two screens of the same corridor,
  each drawn around its own origin, necessarily have the same vertices at the
  same local coordinates. The observation was right, the conclusion was not;
- the centre of the bounding box moves with the cell — true, but by ±12 units
  in all, not by the 25.6 of a screen. What moves is the **culling**, that is,
  how far the geometry sticks out past its own screen, not the screen.

And the picture agreed: a map drawn stacked *looks like* a plausible dungeon,
with rooms and corridors. That is the worst case — the almost-right result.

The test that decides lies outside the format. `MAP_ALIGNMENT` declares, cell
by cell, whether there is map there or not (`0xFFFFFFFF`). It is another file,
written for another purpose, in the only other endianness on the disc. If the
composition is right, the geometry has to fall **where that file says there is
map**:

```
python tools/view.py layout

167 maps checked (0 without a declared grid)
map cells covered by geometry:          436.043/480.731 = 90,7%
  of the solid cells only (collision):  374.430/375.867 = 99,6%
  the rest is water and void:           104.864 cells
geometry outside the map:                 14.192/625.861 =  2,3%
```

> **The missing 9% was not missing** (session 5). For two sessions that 90.7%
> was read as "geometry we cannot find", and there were three hypotheses on
> the list. It was the first: the logical grid also marks as region the cells
> of **water and void** — the moat, the sea, the gorge between two plateaus —
> where the game itself puts nothing. They are 104,864 cells, 22% of the
> declared ones, and the map tells them apart: they carry a region identifier
> of their own.
>
> It was a file not yet opened that said so,
> [`MAPCOLLISION/*.DPK`](format_dpk.md): measured against what the game
> considers solid, the composition covers **99.6%**. The denominator was
> wrong, not the numerator.

On the 82 multi-screen maps — the only ones where the two readings differ —
the direct comparison:

| | map cells covered |
|---|---|
| **composed** | 379,600 / 420,335 = **90.3%** |
| stacked | 16,291 / 420,335 = 3.9% |

Twenty-three times as much. 3.9% is not "a bit worse": it is the signature of
two things that have nothing to do with each other.

One implementation trap: the container's header is **big-endian** like the
whole disc, `MAP_ALIGNMENT` is **little-endian**. These are the only two lines
in the project where the two worlds touch, and reading them with the same
format gives a `117440512 × 134217728` grid — that is, `screens()` returning
`None` and no composition, silently.

The maps contain no `light`, `camera` or `skin`: only `node`, `mesh`,
`material`, `effect` and `texture`. Lighting and camera come from elsewhere.

## Geometry

| | |
|---|---|
| sections | 4,837 |
| objects | 54,110 |
| meshes | 12,097 |
| chunks | 14,666 |
| vertices | 51,738,164 |
| indices | 84,224,102 |

Only two vertex formats, both compressed:

| Chunks | Stride | Declaration |
|---:|---:|---|
| 12,203 | 34 | pos:half3 nrm:half3 col:color4 uv:half2 tan:half4 binorm:half3 |
| 2,463 | 30 | pos:half3 nrm:half3 uv:half2 tan:half4 binorm:half3 |

The sum of the declared sizes matches the stride in **14,666 chunks out of
14,666**.

A geometric check on a sample of 121 sections (1.46 M vertices, 820 k
triangles), with the same oracles used on the models:

| Check | Result |
|---|---|
| mesh bounding box filled | 377 / 377 |
| composed scene against the header bbox | 85 / 85 |
| unit normals | 100.00% |
| unit tangents / binormals | 99.60% |
| axis-aligned faces | **93.92%** |
| chunk → `material` | 466 / 466 |

At 93.9%, axis-aligned faces run higher than in the character corpus (87.6%):
the maps' terrain is almost pure voxel geometry.

On the **whole disc** — models and maps together, 627 files and 5,297
blocks — the full check (no sampling) gives **zero problems**:

| | |
|---|---|
| meshes / chunks | 20,804 / 23,436 |
| vertices | **54,176,741** |
| triangles | 30,909,102 |
| mesh bounding box filled | 20,804 / 20,804 |
| composed scene against the header bbox | 3,462 / 3,466 |
| unit normals | **100.00%** over 54.2 million |
| unit tangents / binormals | 99.65% |
| axis-aligned faces | 94.65% |
| chunk → `material` | 23,436 / 23,436 |
| material → `effect` | 10,458 / 10,458 |

One figure is worth isolating: **2,342 chunks are declared `strip` even though
their index count is divisible by 3**. The old heuristic "divisible by 3 →
list" would have got every one of them wrong, silently.

Every map material uses exactly two stages, base colour and normal map.

## The logical grid

Beside the `.pac`'s streaming grid there is a second, **logical** one, in
`MAP_ALIGNMENT/*.DAT`: where events, enemies and passages are. It has its own
dimensions — `d_1_1_1` is 7 × 8 for streaming and 112 × 96 for logic — and it
is solved: see [`format_mapdat.md`](format_mapdat.md), which also yields the
**graph of how the world is navigated** (146 maps, 320 edges, 95% with the way
back).

## Still to clarify

- The `.DAT` header gives `(16, 112, 96)` for `d_1_1_1`, and the two numbers
  relate to the `.pac` grid as 112 = 7×16 and 96 = 8×12. But the factor to
  world units does not come out cleanly on every map: the geometric extent of
  `d_1_1_1` is 25.6 × 19.2, and 25.6/112 is not a round number. It is not
  needed for drawing; it is needed for understanding the units.

## Use

```
python tools/dsb.py survey extract/pac
python tools/dsb.py verify extract/pac --every 40
python tools/dsb.py info  extract/pac/d_1_1_1.ps3.pac --sec 9
python tools/dsb.py scene extract/pac/d_1_1_1.ps3.pac mappa.obj --sec 9
```

Without `--sec` the export commands pick the section with the most objects,
which is the cell from which the most can be seen.

`blocks()` accepts `.dsb`, `.pac` and `.gz` alike: the `.GZ` files can be
handed to the parser without decompressing them first. Take care not to give
`survey` a folder that holds both the `.GZ` files and the already-extracted
`.pac` files, or everything is counted twice.
