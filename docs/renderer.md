# The renderer, read off the shaders

Obtained by extracting the strings from the shader packages in
`data/shaders/`: **1,200 Cg programs** (magic `CGB`) and **107 distinct
identifiers**, with an `at*` convention for vertex attributes and `g*` for
uniforms.

No reverse engineering of the bytecode: these are the symbol tables of the
compiled programs.

## Model

A **forward** renderer, with up to **4 lights** at once, and matrices and
vectors available in three spaces (model, view, world) — typical of an engine
that picks the lighting space according to the material.

## Vertex attributes (13)

```
atPosition0  atNormal0  atColor / atColur0  atTexCoord0
atTangent0   atBinormal0
atBlendIndex atBlendWeight
atWorld0 atWorld1 atWorld2 atWorld3
```

Three important cross-checks:

- `atPosition0 · atNormal0 · atColor · atTexCoord0 · atTangent0 · atBinormal0`
  are **exactly the six attributes** of the stride-76 vertex decoded in
  [`format_dsb.md`](format_dsb.md). An independent confirmation of that work.
- `atBlendIndex` + `atBlendWeight`, together with `gWorldViewMtxPalette`,
  confirm **matrix-palette skinning**. That gave rise to the prediction that
  the stride-88 vertex was the 76 bytes plus bone indices and weights:
  **refuted**. The vertex declaration, found in the DSBF format in the
  meantime, says that the 8 attributes are the usual six plus a second UV set
  and an unknown `ubyte4` — and that *no* vertex on the disc carries weights.
  So the skinning lives entirely in the 77 `skin` records.
- `atWorld0..3` is a **per-instance world matrix in the vertex stream**:
  hardware instancing.

`atColur0` is a developers' typo left in the binary, like `SetDofApaerture`
in the Lua API (RECON §6.7).

## Lighting

For each of the 4 lights: `gLightAmbient`, `gLightColor`,
`gLightAttenuation`, `gSpotLightCutoff`, plus direction and position in
model/view/world space and `gSpotLightDir` — so **directional, point and spot**
lights.

On top of that, a **rim lighting** block: `gRimSpecularLightColor0..3` and
`gRimSpecularParam`. Material: `gMaterialDiffuse`,
`gMaterialDiffuseAttenuation`, `gMaterialEmission`, `gMaterialSpecularPow`,
`gGlobalAmbientAndMateAlpha`.

## The light, and who already has it — `view.sky_profile`, `view.py light`

The uniforms above say *which* lights the pipeline accepts. Which ones are
**switched on in a map** is another question, and the answer is that the map
data has none at all:

```
`light` records (type 9) in the 167 map .pac files      0
`light` records on the whole disc                     400   one per file
  named `ambient-environment-light`                   399
  cone 0.69813 rad = 40 degrees, falloff +inf     400/400
```

Forty degrees and an infinite falloff are the exporter's starting values, and
the colour confirms it: 336 white lights and 62 of the same beige, spread
over a set that makes no sense in game terms — eight bosses, seven dungeon
interface maps, `NameEntry`, `Option`. It is the working environment of
whoever did the export, not the lighting of the scene. The header's ambient
colour (`+0x60`) is `0.8 0.8 0.8` in 399 files of 399.

### It is not needed: it is baked into the vertices, and in a world of cubes it can be read back

The normals of this geometry are **six**, so grouping the vertex colours by
face is enough. On `field_16`:

| face | vertices | luminance |
|---|---:|---:|
| up | 409,989 | 0.969 |
| south | 132,357 | 0.709 |
| west | 167,995 | 0.703 |
| north | 208,204 | 0.697 |
| east | 172,619 | 0.695 |
| down | 31,305 | 0.494 |

The **four sides agree within 1%**. That is not a Lambertian, which would have
a bright side and a dark one, but a **vertical** ambient light: the sky. Nor
is it one map's accident: over the 40 overworld maps the median spread
between the four sides is **2.8%**, and the up face is the brighter in 38 of
40.

**The proof is that the direction reverses.** Indoors the same measurement
gives the opposite, with the sides agreeing even more closely:

```
                up/sides     down/sides    spread between the sides
overworld  40      1.415         0.661            2.8%
indoors   126      0.822         1.000            0.1%
```

Where there is a ceiling, the up face is the **darkest**, and the down face
comes back to the level of the sides, because below it there is no longer a
sky to set it apart. A number that behaves like that is light.

### And the places line up by themselves

The up/sides ratio, read per location — the names are the ones
`MapParameter` declares, not ours:

```
1.52  Dash Circuit          0.82  the seven temples (0.814-0.822)
1.47  Lake Garland          0.78  Sacred Cave
1.45  Nuntra Desert         0.75  Fairy's Cave, Rat Hole, Cave
1.40  Gilgamesh Beach       0.73  Grave of the Hero
1.38  Brilord Plains        0.68  Mountain Path, Fairy Spring
```

Beaches, plains and desert at the top; at the bottom, **below the temples,
the caves**. The measurement orders the game's places the way someone walking
through them would, and none of these names went into the count.

The only two `field_*` maps that behave as indoors are `field_50` and
`field_91`, which is **the castle courtyard**.

### Who gets lit, and with what light

The rule is not "the map yes, the characters no", and it is measured twice.
Vertex colour is lighting where it **varies within a single face direction**
— that is, where there is occlusion baked vertex by vertex, which the sky
alone does not explain:

```
overworld   spread within the sides  42%     241 distinct levels
indoors                               3%       8 levels
```

The dungeons carry **only two** (`d_1_1_1`: a moss green, and black), and two
levels are not a light: there the geometry has to be lit like everything
else, or the walls become a single mass. The threshold (30%) is not set by
eye. A second measurement that knows nothing of the first, *"is the up face
brighter than the sides?"*, cuts the maps at the same place: **165 of 167**.

The **library models** cannot carry it, by construction: a vase instanced
1,022 times does not hold in its vertices the light of 1,022 places. And
indeed `c_obj_all` has its six faces within **5%** of one another — there,
vertex colour is the tint.

Whatever is left gets **ambient plus sun**, which is the form the disc
declares, with the disc's own numbers:

- `Event:SetSunLightAngle(5.65,62.59); -- yaw, pitch` — the comment is the
  authors'. 16 calls, 8 distinct values, **every pitch between 57.75 and 86
  degrees**: this game's sun is always high. Median 73.5.
- `SetParallelLight(0.15,0.15,0.15, 0.08,0.08,0.08)` — two triples, the first
  always the brighter: diffuse and ambient. The ratio `amb/(amb+dif)` is 0.29,
  0.35 and 0.43, median **0.35**.

And the ambient is not flat: it follows the vertical profile that *that* map
shows in its own vertices, so whoever walks into a cave gets the cave's
light. The one thing still ours is that the yaws, unlike the pitches, are
scattered from −180 to 31 — they belong to the scene, not to the world — and
here one of them is picked.

### What changes in a frame

What has gone is a **horizontal direction the data does not have**: the
earlier Lambertian came from `(0.4 0.8 0.45)`, that is, 42 degrees of
azimuth, and dimmed to 0.35 the two sides that had their backs to it — on top
of a colour that was already the light of the place. On `field_16`:

```
                   mean luminance   below 0.15   median
before                   0.195          47.9%      0.160
after                    0.295           5.9%      0.281
```

Half the screen was below 0.15. The trees facing north and west were black.

## What shines on its own — the `emission` field

Looking for the torches turned up the opposite: the torches are **not**
declared sources, and something else is. The `emission` field of the
`material` record had never been used by the renderer, and it is full:

```
materials with non-zero emission       277 of 1,792 = 15.5%
  the CharEditor palette               166   emission 1 on every channel
  in c_obj_all                          33   of which 21 magic blades
  the orb altars                          5
```

**The edge case says how to read it.** The 166 in `CharEditor` are the
character editor's palette, and they are `1, 1, 1`: an interface panel
receives no light, it shows at full colour. So emission is not an addend —
that would saturate them to white — but a **floor**:
`light = max(lighting, emission)`, per channel. With this reading the
interface case comes out right by itself, and nothing saturates.

And the others are exactly the things that glow in a game:

```
MR_i_mwp_06_light   emis (1.00, 0.32, 0.11)   diff white      fire-red blade
MR_i_mwp_12_light   emis (0.15, 0.64, 0.87)   diff white      sky-blue blade
MR_i_mwp_15_light   emis (0.22, 0.83, 0.18)   diff white      green blade
MR_i_mwp_22_light   emis (1.00, 0.38, 0.99)   diff white      magenta blade
MR_c_enm_10tamaa    emis 0.30                 玉, the enemy's projectile
RM_c_bos_bullet     emis 0.60                 the boss's projectile
```

The **21 magic blades** have a white diffuse and all their colour in the
emission: the blade is a source, and each blade's colour is declared one by
one. The material name ends in `_light` in 21 cases of 21.

### The six orbs, and a material swap

The five emissives in the map library are the altar orbs, and reading their
colour closes a loop opened in session 12, which had established the order of
the altars from the item names without being able to see it:

| altar | map | the script's item | material | colour | the walkthrough |
|---|---|---|---|---|---|
| 4116 | `D_1_3` | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `D_2_3` | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `D_3_3` | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `D_4_3` | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `D_5_3` | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `D_6_3` | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

**Six of six** with the names the walkthrough uses, and the two internal
names that do not name a hue — `gray` and `white` — are exactly the two the
model contradicts: the orbs are orange and purple. The name the game shows
wins over the one the authors wrote down for themselves.

Two things seen by looking at them rather than inferring them:

- `m_obj_118_b` uses the material `orb_121`, and `m_obj_121_b` uses
  `orb_118` — an **exact swap**; in the other four the number matches.
  Inferring the material from the model number would have given two wrong
  colours; what settles it is the index at `+0x00` of the chunk.
- `orb_121` is **the only one of the six with no emission**. The anomaly
  follows the material and not the place, so it ends up on the orb of the
  third temple, which is the only one of the six that does not glow.

## Shadows

Two shadow maps: `gShadowMap0_stage4`, `gShadowMap1_stage8`, with
`gShadowMapParams`, `gShadowMapPolygonOffset` and the shadow projection
matrices in the three spaces (`gModelShadowMtx0/1`, `gViewShadowMtx0/1`,
`gWorldShadowMtx0`). Two maps can mean cascades, or two separate projectors.

## Surfaces

- **Normal mapping**: `gNormalMap_stage2`, with `gNormalMapBaseAxisR` and
  `gNormalMapBaseAxisG` — the channel convention is configurable, so the
  orientation of the green channel must not be taken for granted.
- **Parallax mapping**: `gParallaxMapParams`.
- **Environment mapping**: `gCubeEnvironmentMap_stage3` or
  `gSphereEnvironmentMap_stage3`, with `gEnvironmentMapColor` and
  `gEnvironmentMapFresnel`. This is where `ref_01.dds` comes in, the game's
  only cubemap, and with it the Fresnel-weighted water reflection that YEBIS
  describes.
- **Depth of field**: `gDOFParams` — the YEBIS DOF reaches the shaders as a
  uniform, driven by the Lua (RECON §6.7).
- Miscellaneous: `gAlphaTestParams`, `gPolygonOffset`, `gTexCoordMatrix0..2`,
  `gUtilityColorTexture_stage1` / `gUtilityColorCubeTexture_stage1`.

## Texture stage assignment

| Stage | Contents |
|---:|---|
| 0 | base colour |
| 1 | utility colour (2D or cube) |
| 2 | normal map |
| 3 | environment map (cube or sphere) |
| 4 | shadow map 0 |
| 8 | shadow map 1 |

## Why it matters

This is, in effect, **the specification of the material system** the host
will have to provide: which attributes the pipeline accepts, which uniforms
drive the material, how many lights, which maps and on which stages.
Rewriting the shaders in GLSL or HLSL becomes a job of translation against a
known interface, instead of reconstruction by trial and error.

The stage assignment above later found an **independent confirmation in the
data**: the `material` records of the `DSBF` files have four texture slots,
and the slot position matches the stage. Only `*_nm` / `*_nml` files end up in
slot 2, only `forref_*` in slot 3, and slot 1 is never used — see
[`format_dsb.md`](format_dsb.md) §material. Diffuse, ambient, emission,
specular and the specular exponent are hooked up as well.

The remaining uniforms are still to be connected: the 43 shader identifiers
of the material field at +0x28, and the **numeric tags** of the `DSBF`
binding tables, which associate each `float4` with a constant register.
