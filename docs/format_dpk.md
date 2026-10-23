# `MAPCOLLISION/*.DPK` — the maps' collision

**Status: solved.** Layout, coordinate system and use.
Parser: [`tools/dpk.py`](../tools/dpk.py).

171 files in `PS3_GAME/USRDIR/DATA/MAPCOLLISION/`, **5.4 MB in all**: one
triangle mesh per map, 256,985 vertices and 420,301 triangles. That is a
hundredth of the polygons the same maps are drawn with (30.9 million), and it
is the wall the game actually uses.

```
python tools/dpk.py check              171 of 171, to the last byte
python tools/dpk.py info <file.DPK>
```

## Format

```
+0x00 u32                   number of meshes
then n pairs (u32, u32)     offset and size of each mesh

each mesh, at its own offset:
  +0x00 u32                 number of FLOATS, that is 3 × the vertices
  then n float32 big-endian (x, y, z)
  +0x00 u32                 number of indices
  then n u16 big-endian     three per triangle
```

The number of meshes runs from 1 to 5; 301 meshes in all across the 171 files.

### Why it is certain

The same oracle that solved `MAP_ALIGNMENT`: walking each mesh from its
offset has to end **exactly** at the declared size, and the last one on the
last byte of the file. It does in **171 files out of 171**, for all 301
meshes. With one field misread, the walk leaves the file at the first block.

The only field that cannot be guessed is the count of **floats** rather than
vertices. In `PLANE.DPK` — the smallest file, 80 bytes — it is 12 for four
vertices; read as a vertex count, it sends the offset of the indices 96 bytes
past the end.

`PLANE.DPK` is also the right place to start reading this format: a square of
102.4 units (64 cells) made of 4 vertices and 2 triangles, the minimal case in
which every field is visible to the naked eye.

## The coordinate system is the `.pac`'s

The **same** as the `.pac`: origin at the centre of the map, X to the right,
Z towards the top of the grid. There is nothing to convert.

It checks out side by side, map by map:

```
DUNGEON_21_1   dpk  x [-20.0, 18.4]   z [-18.4, 20.0]
               pac  x [-20.0, 18.4]   z [-18.4, 20.0]      grid 24 × 24
```

The two extents coincide, and they coincide with `w × 1.6`. Where they
differ — `DUNGEON_1_2` has a `.pac` 3.3 units wider — it is decorative
geometry sticking out past the collision, not a misalignment.

## The names do not match the maps'

The collision of `D_1_1_1` is called `DUNGEON_1_1_1.DPK`, that of `FIELD_9` is
called `FIELD_09.DPK`, and in one file the developer wrote
**`DANGEON_8_2.DPK`**. The typo is on the pressed disc, so the parser handles
it alongside the correct spelling.

`PLANE.DPK` is the only one without a matching map: it is the developers' test
floor. **170 maps out of 170** have their collision.

## How tall the world is

It has to be measured, not assumed, and assuming it cost dearly (see
[`walk.md`](walk.md)):

```
global y over 171 files:  [-4.35 ; 51.20]
going below zero:         69 files of 171
above 25.6:               2 files        (FIELD_07 is a mountain and reaches 51.2)
```

And zero is not a clean floor even where it looks like one: the floor of
`d_1_2` sits at `−0.000002`, the residue of a `float32` that went through a
barycentric sum. Truncating to zero does not lose a margin, it loses the floor.

## From meshes to columns

Something that walks does not need triangles but two answers per cell — where
the foot comes down, and what is there at body height. `dpk.seed()` seeds the
triangles with points at a quarter-cell pitch, which is the resolution of the
columns in [`walk.md`](walk.md), and returns each point with **the normal of
its triangle**.

The normal is not an extra: it tells a floor from a wall, and taken from the
triangle rather than the vertex it is exact rather than interpolated.

Seeding instead of taking the vertices is necessary because in a collision
mesh the triangles **are large**: a floor twenty cells across is two
triangles, and its vertices alone would leave every cell in between empty.

**How large**: in `FIELD_07` the longest edge measures 190.3 units, that is
119 cells, and 2,238 triangles out of 6,747 exceed 38.4 units. A cap of 96
subdivisions — which looked like the cautious choice — made the seeding pitch
of those triangles 2.0 units, **wider than a cell**, and so left whole cells
uncovered: among them fourteen map entry points, which came out as not
walkable. Without the cap it costs 27% more points across the disc (139
million against 109) and leaves no holes; seeding goes in batches because a
single map reaches 22 million points.

## The backdrop

Under every overworld map there is a single flat quad stretched from edge to
edge, at about −3.2. In `FIELD_22` it is **two triangles** covering 10,368
cells, on a map that has 16,384; in `FIELD_30` it is 32 triangles covering
13,628 cells.

It faces up, so reading the normals takes it for a floor — except that it has
metres of rock above it. How to recognise it, and what can be got out of it
(the water mask), is in [`walk.md`](walk.md).

## What having it changes

`view.py walkabout` walks every map on foot. With the columns taken from the
render geometry, and with the columns taken from the `.DPK`:

| | geometry | `.DPK` |
|---|---:|---:|
| cells reached on foot | 18% | **63%** |
| inhabitants reached | 65% | **96%** |
| passages reached | 194 | **303** |

Above all, the gap between dungeons and the overworld — 26% against 13% of
cells, 76% against 51% of inhabitants — **is gone**. With the real collision
both families stand at 63% of cells, and the overworld reaches 99% of
inhabitants.

But not all of it is this file's doing: half the gain comes from recognising
that a step is worth **one cell**, which is an independent finding (see
[`walk.md`](walk.md)). The `.DPK` on its own took inhabitants from 65% to 78%.

## What is missing

- **Multiple meshes.** One file in five has more than one (up to 5), and it is
  not clear what separates them: areas, collision materials, or only the
  65,536-vertex limit of 16-bit indices. The maps with several meshes are also
  the largest, which points to the third.
- **Collision materials.** There is no per-triangle field: no terrain type, no
  footstep sound, no "water". If they exist they live elsewhere — and for water
  they really do live elsewhere, in the region tag of the logical grid.
- **Triangle winding.** Only the geometric normal is used here; if the format
  declared a winding, solid geometry could be told apart from flat,
  two-dimensional surfaces.
