# The first render — `tools/view.py`

The project's first integration test. It loads a map (or a model), assembles
the scene and draws it textured in OpenGL 3.3.

```
python tools/view.py <file.pac|.dsb|.gz> [options]
python tools/view.py sweep <extract dir>      verification pass, no screen
```

Options: `--sec N` a single section, `--only <substring>` filters by name,
`--shot out.png` draws one frame and exits (no visible window needed),
`--size`, `--azim/--elev/--dist`, `--flat` turns the light off (leaving the
colour the data carries), `--list` lists the sections. At the keyboard:
WASD/RV to move, the mouse to look around, F frames the scene, T textures,
L light, C culling.

```
python tools/view.py light                    how much sky each map sees
```

## What it puts to the test

Four formats, and the chains of references that bind them, all at once:

    .pac  -> grid of sections                format_pac.md
    DSBF  -> nodes, meshes, chunks, vertices format_dsb.md
    chunk -> material -> texture             the index at +0x00 and the four stages
    TPKG  -> DXT pixels                      format_tpk.md

It is a strict oracle precisely because it is visual: a mistake does not
produce a slightly crooked drawing, it produces torn geometry, or the right
textures on the wrong faces. The first dungeon (`d_1_1_1`, section 9) comes
out at the first attempt, with the tiled floor, the walls, the crates and the
water in the right place; `field_16` is recognisably the game's overworld,
with the voxel grass, the dirt paths and the paved road.

## The verification pass

A good-looking render is an anecdote. `sweep` is the measurement: it loads
**everything** that could be drawn and checks every texture reference.

```
627 of 627 files, 5,297 sections, 23,439 chunks
54,176,753 vertices, 30,909,108 triangles, in 14s
chunks without UV: 312, without texture: 312, meshes reached through skin: 77
texture references: 1,905, unresolved: 2
```

(The time depends on the disk cache: ~14 s warm, ~40 s cold.)

The 54,176,753 vertices are **all** the geometry the disc declares: the static
census of `dsb.py verify` counts 54,176,741, and the 12 of difference are a
mesh that two nodes instance twice. Nothing is lost on the way.

The two unresolved references are production leftovers, not holes:
`FireballColGrnColorFile` is not a file name, and `SouthPeak_Logo.ifl` is a
3ds Max *Image File List* — the format in which Max lists the frames of an
animated texture. They show what tools the assets were made with.

## Three things learnt by looking

**Vertex colour is baked light.** In the first dungeon it is a moss green
(119, 143, 83) with the inner edges taken to black: ambient occlusion and an
ambient tint baked into the geometry. That explains why the textures are grey
and the scene is not. It is also an **independent confirmation of the channel
order**: if it were ARGB the alpha would vary and the blue would always be
255, and the opposite is what is observed — the last byte is constant at 255.
It is RGBA.

One consequence follows for the host: dynamic light must not multiply a
second time what is already baked in.

*Written here in session 3 and applied in session 13, and that delay is worth
keeping in mind: the consequence was right, and all the while the viewer went
on multiplying.* Once it was measured rather than inferred, the baked light
split in two. In the overworld it is **per-vertex occlusion** (42% variation
within a single face, 241 levels); in the dungeons it is **two levels** and
nothing more, which is to say it is not a light. Hence the rule the renderer
now applies: light whatever does not carry light of its own, and light it
with the light the disc declares. All of it is in [`renderer.md`](renderer.md);
the command is `python tools/view.py light`.

**The maps have a lid.** A dungeon seen from above is a flat slab: the
geometry includes the ceiling. In the game it is the camera cut that hides it,
not missing data.

**The bottleneck is not the reading.** Decoding the vertices with numpy
straight from the vertex buffer — the same declaration as `dsb.py`, turned
into a `dtype` instead of `struct` formats — brings the whole disc down to 14
seconds. The version that builds a dictionary per vertex is handy for
inspecting and useless for loading.

## Skinning, solved by accident

Counting the drawable vertices, 50,043 of 54 million were missing: 0.09%.
Looking for the reason opened the `skin` record, which had been in the queue.

The 77 unreachable meshes are **all** in `Opening.ps3.dsb`, and there are
exactly as many of them as that file has `skin`s. A node can hook a `skin`
instead of a mesh, and the `skin` names the mesh at +0x20. The rest of the
record — the bone array, the inverse bind pose, the matrix convention — is
documented in [`format_dsb.md`](format_dsb.md) §skin.

Two things fell together:

- **semantic 9**, the mysterious `ubyte4` that appeared only in this file, is
  the **bone index**: its values lie in `0 .. n_bones-1`. It had been in the
  queue in its own right, and it solved itself once the `skin` record was
  open;
- the skinning is **rigid**: there is an index but no weight, one bone per
  vertex.

And there is a trap worth describing, because it is the kind of mistake that
goes unnoticed. Drawing the parts with the *node* transform gives a
plausible-looking 3D village with a few pieces out of place: it looks like a
detail to tidy up. With the bone matrices, on the other hand, the scene
**flattens** — and the instinctive reaction is to think you got it wrong. The
determinant said otherwise: the node chain passes through `oka_s-node` (Y
scale 0.04) and through a node called `Dummy_2D_pos-node`. The opening screen
is a **2D backdrop seen from above**, and looked at along the right axis, there
is the village, with its paths, the fence and the trees.

The "almost right" result was the more misleading of the two.

## The post-processing — `tools/post.py`

The description Silicon Studio gives of its own middleware in this game
(RECON §6.7) names four effects, and they become four passes:

> *"Applied for **vignetting** and **color modification** to give a toy camera
> feel, and realistic **defocusing** effects that create the feeling of a
> miniature world. Also contributes to sparkling **glare** effects for light
> sources or water."*

    scene  -> colour + depth FBO
    prep   -> half resolution; the bright pass in alpha
    blur   -> separable Gaussian, two rounds: narrow for the defocus,
              wide for the glare
    comp   -> defocus by circle of confusion, additive glare,
              vignetting, color modification

The parameters are not invented: the Lua drives them, and they can be
counted. Over the **202 calls** on the disc:

| call | observed range |
|---|---|
| `SetParamDepthofField(a, b, c)` | `a` 0.37–3.02 (median 0.79); `b` 0.20–1.50 (median 0.70); `c` always 0 |
| `SetDofApaerture(x, 0)` | 0.70 in 14 cases of 20, then 1.2 / 1.3 / 1.5 |
| `createFairyGlareEffect(38.27, 2.68, -23.2)` | **a position in the world**, not parameters: the glare is placed at a point |

`BackupDof()` and `RestoreDof()` appear 526 and 612 times: every event saves
the current DOF, imposes its own, and puts the old one back at the end. Focus
is per scene.

What we do not know is **the unit**: 0.79 cannot be a world distance, since a
map is hundreds of units wide. They are normalised values or multipliers of a
base that lives in the EBOOT — a question for Phase 3. Here the focus follows
the camera target (which is the Lua's `switchDofPointGaze()`), and the width
of the sharp band is a fraction of the scene radius, so the tilt-shift stays
consistent from one map to the next.

A setting found by looking: with the bright-pass threshold at 0.72, the floor
of a dungeon glowed, which is to say everything did. But the vendor says
*"for light sources or water"* — glare is rare, not a veil. At 0.88 it goes
back to being what that describes.

The result is that `field_16` stops looking like a 3D model and starts
looking like a scale model. That is exactly what the *defocus* is there for.

## The water, which the `.pac` does not contain

A frame of the overworld had large black areas, and they looked like missing
geometry. They were the sea. The map does not contain it — none of the 11
textures of `Field_16` is water — because the engine draws it, and its
texture lives outside every map package: **`data/shaders/water_col.dds`**,
together with `Sun.dds`. These are the disc's two loose `.dds` files, and
sitting in `shaders/` is the statement that they belong to no map and to no
character.

`water_col.dds` is 128×128, **uncompressed** (32 bits, `ARGB` masks on a
little-endian word, so `BGRA` byte by byte), and draws a midnight-blue grid of
**16 squares a side**. Sixteen squares are the sixteen dots of a cell, so the
texture is laid down **one copy per cell** and the grid lines itself up over
the whole sheet of water, with no repeat needed.

The other two things it needs come from the logic grid and the collision, and
are in [`walk.md`](walk.md):

- **where**: the cells whose only surface is the backdrop laid under the map
  (`Columns.water()`), 40,964 across the whole disc — and the grid confirms
  them by another route, with region tag `119`;
- **at what height**: it is declared nowhere, but the world pins it from both
  sides. The backdrop lies **exactly two cells** below the shore in 52.9% of
  cases, and the shore is at 0.00 in 50%, so there is a single multiple of a
  cell in between. Each sheet of water takes its own: start from the shores
  and propagate the **minimum** into the water, so that the mountain lake of
  `Field_16` stays at +11.2 while the sea is at −2.0.

```
python tools/view.py <map>.pac.gz            the water draws itself
python tools/view.py <map>.pac.gz --no-water as it was before
```

And the measurement of what is left, which `view.py layout` now prints:

```
map cells covered by the geometry:     436,043/480,731 = 90.7%
  of which water, now drawn:                40,964 cells
  still black in a frame:                    8,503 cells = 1.8% of the map
```

The remaining black is the other half of the old "water and void" item: cells
inside the map with no geometry **and** no backdrop, that is, real void. They
are 1.8%, and they are no longer an area but holes.

## What it does not do

It is a verification renderer, not the game's renderer. The rest of
[`renderer.md`](renderer.md) is missing: normal maps, environment maps, rim
light, shadows. The lighting is no longer just an aid to reading the shapes
(session 13), but the **point lights** are still left out: the disc has
`setPointLight` and `pointLightOff`, and the dungeons — the maps that do not
carry light of their own — are full of torches, 859 cells.

A note in passing, picked up while looking for the water:
`data/shaders/graphics.ps3.tpk` contains `ice_03`, `snow_01`, `sun_01` and
**`ref_01`, which is a CUBEMAP** — that is, exactly the environment map this
list gives as missing.
