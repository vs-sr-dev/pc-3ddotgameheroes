# The DSBF format — scenes and models

**Status: container, geometry, scene graph and materials solved.**
The header, the tables and the record headers are validated on all 460 `.dsb`
files on the disc — 25,443 objects, 39,348 strings, zero discrepancies.
Geometry is extracted from **460 files out of 460**: 8,707 meshes, 8,770
chunks, **2,438,577 vertices** and **1,611,418 triangles**. The scene graph
reassembles: the parent, the transform and the attached geometry of every
node. The chain `node → mesh → material → texture` is closed, with the
textures assigned to their stages. What remains is skinning and a few
unnamed material parameters.
Parser: [`tools/dsb.py`](../tools/dsb.py).

Everything is big-endian.

## The file is a memory image

A 16-byte header followed by **a memory image** that the engine loads in one
piece. The practical consequence, and the thing to know before anything else:

> **Every internal offset is relative to byte 0x10 of the file, not to 0.**
> The value `0x520` means byte `0x530`.

The file has **two regions**: the *structures*, from the start up to the byte
given by header field `0x08`, and from there on the vertex and index
*buffers*. The vertex buffer offsets in the mesh records are relative to the
start of the second.

Two clues confirm that the exporter wrote C++ structs with `memcpy`: the
**`0xCC`** fill (MSVC's uninitialised stack), which shows up both in fixed
header fields and *inside* the structs, and padding consistent with the
compiler's natural alignment. The on-disc layout therefore mirrors the
original engine's in-memory layout — useful once the EBOOT is reached.

## Header

| Off | Type | Field |
|---|---|---|
| 0x00 | char[4] | `'DSBF'` |
| 0x04 | u16 | exporter version: `0x0195`, `0x019D`, `0x01A4`, `0x01A5` |
| 0x06 | u16 | `0x0027`, constant |
| 0x08 | u32 | size of the structure region = **offset of the buffers** |
| 0x0C | u32 | file size |
| 0x10 | u32 | `1`, constant |
| 0x14 | u32 | `3`, constant |
| 0x18 | u32 | size of the buffer region; `0x08 + 0x18 == filesize` |
| 0x1C | u32 | offset of the table of string offsets |
| 0x20 | u32 | number of strings |
| 0x24 | u32 | `112`, constant |
| 0x28 | u32 | number of objects |
| 0x2C | u32 | `0xFFFFFFFF`, constant |
| 0x30 | u32[2] | zero |
| 0x38 | u32 | offset of the binding list, see *Constant binding* |
| 0x3C | u32 | `0xCCCCCCCC` |
| 0x40 | float[4]×2 | scene **bounding box**: min and max |
| 0x60 | float[4] | RGBA colour (ambient) |
| 0x70 | float[4] | projection parameters (near/far observed: 1.0, 100.0, 0.001) |
| 0x80 | u32[] | **table of object offsets**, `0x28` entries |

The exporter versions on the disc: `0x01A5` (386 files), `0x01A4` (43),
`0x019D` (24), `0x0195` (7).

## String table

At offset `0x1C` there is an array of `0x20` u32s, each the offset of a
NUL-terminated string. The strings follow, consecutively.

Objects refer to each other in two different ways, and it pays not to confuse
them: by **CRC32 of the name** (the standard IEEE one, exactly `zlib.crc32`)
in the binding lists, and by **index into the object table** in the scene
graph.

The name's suffix encodes the class: `-node`, `-mesh`, `-fx`, `-skin`,
`-light`, `-camera`, or the `.dds` extension for textures.

## Object record — a 16-byte header

| Off | Type | Field |
|---|---|---|
| +0x00 | u32 | **1-based** index of its own name in the string table |
| +0x04 | u32 | CRC32 of its own name |
| +0x08 | u32 | 1-based index of the **base name** (the name without its class suffix), `0` if absent |
| +0x0C | u32 | **type code** |

Field +0x00 was checked on **25,443 objects out of 25,443**: it always matches
the index of the name whose CRC32 is at +0x04. Name and hash are redundant on
purpose, so that lookup works in both directions.

Field +0x08 points at the base name: `'CHECK-fx'` → `'CHECK'`,
`'c_etc_03a_eng.dds'` → `'c_etc_03a_eng_dds'` (the dot becomes an
underscore). It is an exact match in 92.7% of cases; the rest are
sanitisations of the same kind (`'Camera01.Target-node'` →
`'Camera01_Target'`).

### Type codes

| Code | Type | Objects | % |
|---:|---|---:|---:|
| 17 | node | 11,671 | 45.9% |
| 14 | mesh | 8,707 | 34.2% |
| 4 | effect (`-fx`) | 1,792 | 7.0% |
| 2 | material | 1,792 | 7.0% |
| 1 | texture | 992 | 3.9% |
| 9 | light | 400 | 1.6% |
| 16 | skin | 77 | 0.3% |
| 11 | camera | 12 | 0.0% |

`effect` and `material` occur in **identical** numbers: every material has
exactly one associated effect.

## `mesh` record (type 14)

The common header is **112 bytes** long — that is the meaning of the constant
at `0x24` in the header. The type-specific part begins after it.

| Off | Field |
|---|---|
| +0x20 | float[4] local bounding box, min |
| +0x30 | float[4] local bounding box, max |
| +0x44 | u32 **number of geometry chunks** |
| +0x50 | u32[] pointers to the chunks |

> A mesh **is not a single block of geometry**: it is a list of chunks.

On the disc 8,655 meshes have one chunk, 42 have two, 9 three and one has
four, for a total of 8,770 chunks, concentrated in six files (`c_obj_all`,
`Bee`, `Opening`, `map_object`, `c_bos_01_all`, `Castle`). They are few, but
they are among the largest in the game. Stopping at the first chunk raises no
error: it silently loses the rest of the mesh.

The `{pointer, count}` pattern followed by the inline array recurs in every
record type: the pointer is at +0x40, the count at +0x44, the array at +0x50.
Recognising it is the key to reading the `material` records too.

### Geometry chunk

| Off | Field |
|---|---|
| +0x00 | u32 **index of the `material` object** |
| +0x10 | u32 number of indices |
| +0x14 | u32 low byte = **primitive** (3 list, 4 strip); bit `0x100` = 32-bit indices |
| +0x18 | u32 pointer to the **vertex declaration** |
| +0x20 | u32 number of attributes |
| +0x24 | u32 number of vertices |
| +0x28 | u32 **offset of the vertex buffer**, relative to the buffer region |
| +0x2C | u32 size of the vertex buffer |

The index buffer immediately follows the vertex buffer, aligned to the index
size. No packing heuristic is needed: the buffers are addressed explicitly.

Field +0x00 is the index of the `material` object, valid in **8,770 chunks out
of 8,770**. It is also what explains multiple chunks: *one chunk per
material*.

The `0x100` flag is set in exactly 3 chunks out of 8,770 — the only ones that
exceed 65,535 vertices (`c_bos_05_all`, `c_bos_08_all`, `Castle/kabe`, up to
123,712 vertices). Read as 32-bit, the maximum index comes out *exactly*
`n_vertices − 1`.

### The vertex declares its own layout

The vertex format does not have to be guessed: every chunk **declares** it, as
an array of `n_attr` u32 pairs `(semantic, type)`. The attributes follow one
another in the vertex in the declared order, with no padding.

| Semantic | | | Type | Bytes |
|---:|---|---|---:|---:|
| 0 | position | | 0 | `float2` 8 |
| 1 | normal | | 1 | `float3` 12 |
| 2 | colour | | 2 | `float4` 16 |
| 3 | uv | | 3 | `half2` 4 |
| 6 | tangent | | 4 | `half3` 6 |
| 7 | binormal | | 5 | `half4` 8 |
| 8 | uv2 | | 6 | `ubyte4` 4 |
| 9 | (to be clarified) | | 7 | normalised `ubyte4`, RGBA 4 |

Codes 6 and 7 have the same size but are distinct: 7 is the colour (the last
byte is `0xFF` in 99% of vertices, so the order is RGBA), and 6 appears only
next to semantic 9.

Formats observed on the disc:

| Chunks | Vertices | Stride | Declaration |
|---:|---:|---:|---|
| 6,122 | 39,924 | 32 | pos:float3 nrm:float3 uv:float2 |
| 1,507 | **1,518,514** | 34 | pos:half3 nrm:half3 col:color4 uv:half2 tan:half4 binorm:half3 |
| 630 | 699,159 | 76 | pos:float3 nrm:float3 col:float4 uv:float2 tan:float4 binorm:float3 |
| 194 | 16,739 | 40 | pos:float3 nrm:float3 col:float4 |
| 71 | 37,629 | 88 | …float4 uv:float2 **uv2:float2 attr9:ubyte4** tan:float4 binorm:float3 |
| 58 | 232 | 24 | pos:float3 nrm:float3 |
| 51 | 17,622 | 20 | pos:half3 nrm:half3 col:color4 uv:half2 |
| 47 | 19,960 | 16 | pos:half3 nrm:half3 col:color4 |
| 33 | 154 | 30 | pos:half3 nrm:half3 uv:half2 tan:half4 binorm:half3 |
| 32 | 73,698 | 48 | pos:float3 nrm:float3 col:float4 uv:float2 |
| 13 | 906 | 12 | pos:half3 nrm:half3 |
| 6 | 12,414 | 60 | pos:float3 nrm:float3 col:float4 uv:float2 uv2:float2 attr9:ubyte4 |
| 4 | 234 | 16 | pos:half3 nrm:half3 uv:half2 |
| 2 | 1,392 | 36 | pos:half4 nrm:half4 uv:half2 tan:half4 binorm:half4 |

The 34-byte format alone accounts for **1.5 million vertices out of 2.4**: it
is the compressed geometry of the characters and the world. It is the same
attribute set as the 76-byte one, with positions and unit vectors in
half-float and the colour in a ubyte4.

Note that the same `n_attr` covers different attribute sets — at 3 attributes
there are both `pos/nrm/uv` (stride 32) and `pos/nrm/col` (stride 40,
per-vertex-colour meshes with no texture). That is why inferring the layout
from the number of attributes could never have worked.

Semantics 8 and 9 occur together and only in 77 chunks, all in a single file,
`Opening.ps3.dsb`. **Semantic 9 is the bone index**, that is, the
`atBlendIndex` the shaders declare (see [`renderer.md`](renderer.md)): its
values lie in `0 .. n_bones-1` of the corresponding `skin` record, and the 77
chunks that carry it are exactly the 77 skinned meshes on the disc. Semantic 8
is a second UV set.

It remains true, and has to be kept together with the rest, that **no vertex
carries weights**: there is the index but no `atBlendWeight`. Skinning is
therefore **rigid**, one bone per vertex. Two old hypotheses fall at once: that
stride 88 was 76 bytes plus indices *and* weights, and the later one that
semantics 8 and 9 had nothing to do with skinning.

### Coverage

Of 460 files, **460 yield their geometry**. Every oracle is green:

| Check | Result |
|---|---|
| sum of the declared sizes == stride | 8,707 / 8,707 meshes |
| every index < number of vertices | no violations |
| the positions **fill** the record's bbox | 8,707 / 8,707 |
| the composed scene fills the header bbox | 455 / 459 files |
| unit normals | 100.00% over 2,438,577 |
| unit tangents / binormals | 99.62% / 99.63% over 2,256,848 |
| axis-aligned faces | 87.59% over 1,611,418 triangles |
| UVs entirely within 0..1 | 78.6% of chunks; 99.8% within ±64 (tiling) |
| chunk → `material` object | 8,770 / 8,770 |
| material → `effect` object | 1,792 / 1,792 |
| texture slot → `texture` object or −1 | 1,954 assignments, 0 invalid |

The 4 files that do not fill the scene bbox (`Dragon`, `Golem`, `Water`,
`Opening`) are off by fractions of a unit on one axis: they are animated
scenes, where the declared bounding box covers the motion and not the rest
pose.

The same parser holds on the maps without a single change: counting the 167
`.pac` files as well comes to 5,297 blocks, 20,804 meshes and **54,176,741
vertices**, still with zero problems. See [`format_pac.md`](format_pac.md).

## `node` record (type 17) — the scene graph

| Off | Field |
|---|---|
| +0x40 | float[4] position |
| +0x50 | float[4] rotation **quaternion** (x, y, z, w) |
| +0x60 | float[4] scale |
| +0x70 | u32 **index of the parent object**, `0xFFFFFFFF` = root |
| +0x78 | u32 **index of the attached object**, `0xFFFFFFFF` = none |

Both fields are indices into the object table, **not** CRCs — and that is
exactly the mistake worth not making again: looking them up among the CRCs
gives small, ordered "unknown" values, which is the symptom of an index read
as a hash.

The check over all 11,671 nodes on the disc leaves no room:

- the parent is **always** another `node` (9,135) or absent (2,536); never an
  object of another type, never out of range, **no cycles**, maximum depth 8;
- the attached object is **always** a `mesh` (8,633), `light` (400), `skin`
  (77) or `camera` (12), never a `node`. The counts match the type census.

And the semantic confirmation, which is worth more than the numbers: in
`c_bos_01.ps3.dsb` the chains are `neck_04 → neck_03 → neck_02 → neck_01 →
c_bos_01` and `tale_05 → tail_04 → … → tail_01 → c_bos_01`. It is the skeleton
of a dragon.

With the chain of transforms composed up to the root, `demoplay` gives the
exact result: local bounding box (−256,0,−128)…(256,0,128), node at
(640,−360,0) rotated 90° about X, and the scene ends up **precisely** at
(384,−488,0)…(896,−232,0), which is the bounding box declared in the header.

## `material` (type 2) and `effect` (type 4) records

Both are **fixed-size**: 368 bytes for the material, 32 for the effect. And
that is the first thing to know about the effect: its 16 bytes past the common
header are `00000000 00000000 CCCCCCCC CCCCCCCC` in **all 1,792** records. An
`effect` is only a handle with a name — it carries no data. That explains the
1:1 count with materials, and there is nothing to extract from it.

| Off | Field |
|---|---|
| +0x20 | u32 **index of the associated `effect` object** |
| +0x24 | u32 pointer to the parameter block (always at +0x30) |
| +0x28 | u32 **shader / technique identifier** — 43 distinct values |
| +0x3C | float[4] **diffuse** RGBA |
| +0x58 | float[3] **ambient** |
| +0x64 | float[3] **emission** |
| +0x70 | float[3] **specular** |
| +0x7C | float specular exponent — `5.0` across the whole disc |
| +0xE4 | u32[4] **texture per stage**, `0xFFFFFFFF` = none |

Field +0x20 lands on an `effect` object in **1,792 cases out of 1,792**.

### The textures, by stage

The four slots at +0xE4 are object indices, and they land on a `texture`
object or are −1: **zero invalid references** over 1,954 assignments. The
position in the slot *is* the stage, and it matches the assignment that
[`renderer.md`](renderer.md) had derived from the shaders:

| Slot | Stage | Materials | The textures that end up there |
|---:|---|---:|---|
| +0xE4 | 0 — base colour | 1,519 | `dot_base.dds`, `loading.dds`, `background.dds` |
| +0xE8 | 1 — utility colour | **0** | never used |
| +0xEC | 2 — normal map | 377 | `dot_nm`, `dot_512_nm`, `dot_256_nm`, `editchar_nml` |
| +0xF0 | 3 — environment map | 58 | `forref_dungeon`, `forref_sword`, `forref_coin`, `forref_field` |

It is the **names** that close the check, not the counts: slot 2 receives
only files ending in `_nm` or `_nml` — normal maps — and slot 3 only files
starting with `forref_`, that is, *for reflection*. Neither prefix ever
appears in slot 0. A wrong assignment of the slots could not produce this
separation.

The four `forref_*` are the reflection textures the materials actually
reference; `ref_01.dds`, the game's only cubemap according to `renderer.md`,
does not appear here — so in practice stage 3 uses the *sphere map* variant
(`gSphereEnvironmentMap_stage3`).

### The parameters

`specular` is `(0.8, 0.8, 0.8)` in 99% of materials and the exponent `5.0` in
all of them: the game has a uniform specular response, consistent with the
voxel look. Diffuse and ambient vary; `emission` is zero in 86% of cases.

The semantic confirmation of `emission` is worth more than the statistics: of
the 26 materials with `light` in their name, **22 have non-zero emission**,
against 14% of the other 1,766. And the values read themselves —
`MR_c_bos_heart` (the boss's heart) has diffuse `(1.00, 0.49, 0.00)` and
emission `0.30`: orange and glowing.

## Constant binding

Header field `0x38` points at a list of resources used for drawing, one entry
per object: `{name index, name CRC, 0x01CCCCCC, pointer}`. The last pointer
leads to a **binding table** of 12-byte entries `{pointer to the value, 0,
tag}`, where each value is a `float4` in a 16-byte-aligned slot.

On `demoplay` the node's table has 11 entries: three with tag `0x1E1800xx`
pointing at the three components of the scale, four with `0x1F1800xx` for the
quaternion, three with `0x201800xx` for the position, plus one `0x22000000`.
That is **one component per slot**, as RSX's constant file wants.

This is the mechanism that will connect the floats of the `material` records
to the uniforms of the shaders listed in [`renderer.md`](renderer.md): not a
fixed layout to be guessed, but a table with the identifiers inside it.

## `skin` record (type 16)

A node does not always attach a mesh: in the disc's 77 cases — all in
`Opening.ps3.dsb` — it attaches a `skin`, which in turn names the mesh.
Following only `node → mesh` silently loses those 77 meshes, that is, 50,043
vertices.

```
  +0x20 u32   index of the mesh object
  +0x30 u32   number of bones
  +0x60       then n 80-byte entries:
                +0x00 float[16]  4x4 matrix
                +0x40 u32        index of the bone's node
                +0x44 u8[12]     0xCC fill
```

The record itself says the layout is this: `0x60 + n * 0x50` gives
**exactly** its size. The same proof that solved `MAP_ALIGNMENT`.

The matrix is **row-major with the translation in the last row**, the D3D
convention, and it is the **inverse bind pose**. The oracle that settles the
convention is this: `world(bone) @ Mᵀ` comes out *identical for every bone*
of a given skin — which is the property that defines the bind pose — while the
other three combinations (`M @ world`, `world @ M`, `Mᵀ @ world`) give
matrices that all differ from one another.

With the bone index in the vertex's semantic 9 and no weights, the formula
reduces to a single term:

```
v_world = world(bone[v]) @ Mᵀ[bone[v]] @ v
```

**Beware of a trap.** Drawing the parts with the *node*'s transform instead of
the bone's gives a plausible-looking 3D village with a few pieces out of
place — it looks like a detail error and is instead the wrong reading
altogether. The right composition is **flat**: the chain of nodes goes through
`oka_s-node` (Y scale 0.04) and `Dummy_2D_pos-node`, and squashes everything
onto a vertical plane. The opening scene is a **2D backdrop seen from
above** — village, paths, fence, trees — not a three-dimensional scale model.
The "almost right" result was the more deceptive of the two.

## The complete chain

Every link is now explicit, and each is an object index checked over the whole
corpus:

```
node --+0x78--> mesh --chunk +0x00--> material --+0xE4[stage]--> texture --name--> TPKG
  |        \                              |
  |         +--> skin --+0x20--> mesh     +0x20 --> effect (empty handle)
  +0x70 parent          +0x60 --> bones (node index + inverse bind pose)
```

The `texture` objects carry the name of the `.dds` file, which is the same key
the [`TPKG`](format_tpk.md) packages use: the last step of the join is by
name, with no numeric index.

## What is missing

- In the `skin` records, the minor fields remain: the pointers at +0x24 /
  +0x2C, which point inside the record itself, and the counters at +0x28 /
  +0x3C.
- The meaning of the binding table's tags, and of the 43 shader identifiers in
  material field +0x28.
- Material fields still unnamed: a second colour at +0xC4, a `(0.2, 0.8)` pair
  at +0xD4 that has the shape of a Fresnel bias/scale, and the state bitfields
  at +0x164 / +0x168.

## Use

```
python tools/dsb.py info   <file.dsb>
python tools/dsb.py survey <dir>                container validation
python tools/dsb.py verify <dir>                oracles on the geometry
python tools/dsb.py obj    <file.dsb> <out.obj> geometry in local space
python tools/dsb.py scene  <file.dsb> <out.obj> composed scene in world space
python tools/dsb.py names  <dir> --out x.json   CRC32 -> name dictionary
```

The commands accept `.dsb` files, the maps' `.pac` files and undecompressed
`.gz` files alike: `blocks()` resolves the container, see
[`format_pac.md`](format_pac.md). In `.pac` files the section is chosen with
`--sec N`; `verify` accepts `--every N` to sample large corpora.

`obj` and `scene` also write a `.mtl` next to the `.obj`, with colours,
specular exponent and the `.dds` names in `map_Kd` / `norm` / `refl`. The
meshes carry `usemtl`, so the model opens already assigned — the textures of
the same name only need to be extracted from the `TPKG` packages.

The `names` command builds a CRC32→name dictionary from **all** the string
tables in the corpus: a name present in one file resolves the references in
every other. On the disc the 39,348 strings reduce to **15,206 distinct
names**.
