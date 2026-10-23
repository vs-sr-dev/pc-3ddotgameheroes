# Entities — `tools/entity.py`

**Status: solved.** 72 of 99 names are placed, and 66 of 99 have the model the
disc declares. What remains are extras in the main events and props, which do
not go through the mechanism that map NPCs use.

This is the layer that was missing between the script and the drawing. Before
it, `SetCameraAtBody` could frame an NPC but there was no NPC to frame, and
[`view.py`](../tools/view.py) could draw a character, but as a file, not as
something that *stands somewhere*.

Twenty-two API methods were all asking for the same thing, and together they
make **1,664 calls, 25% of the corpus**. They were the largest item left.

```
python tools/view.py event extract/.../Event/mapevent/mapevent_d08_02.lua.eu --skip 40

8 entities on stage:
  <player @player (0.0, 0.0, 0.0) dir 1 c_ply_01>
  <npc PriestSP (0.0, 0.0, -9.6) dir 0 c_npc_05>
  <npc YoungWomana4_010 (1.6, 0.0, -1.6) dir 0 c_npc_27>
  ...
```

## The four directions

The scripts turn characters with an integer from 0 to 3 — `SetNpcDirection`
(242 calls), `SetPlayerDirection` (149). Which integer is which direction was
settled by **two independent oracles that agree**:

| direction | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| unit vector | +Z | −Z | −X | +X |

1. **Whoever turns and then walks, walks forward.** Of 81
   `SetXDirection(d)` … `MoveX(dx, dz, …)` pairs taken from the corpus,
   direction 0 goes towards +Z in 34 cases of 45. It is the most populated
   cell and the sharpest.
2. **Whoever talks to someone looks at them.** In `mapevent_f80` Pizzaro and
   Rosy are created at the same coordinates except for X (−1.6 and +1.6), and
   they talk to each other: he turns to 3, she to 2. So 3 is towards +X and 2
   towards −X — and the two axes left over for 0 and 1 are exactly the ones
   the mechanical oracle gives.

The enumeration is by **paired axes** (0/1 on Z, 2/3 on X), not a clockwise
rotation. Nobody would have guessed it: `2` and `3` are opposite each other,
not consecutive in a turn.

### The hypothesis that did not work

"A freshly created NPC faces the player" scores **55%**, barely above chance,
and its best candidate is `dir0 = −X`, which is wrong. It is not a rule:
`CreateNpc` puts them down already oriented, and `SetNpcDirection` turns them
*for the scene*, not towards us.

This is worth keeping in mind. An oracle at 55% is not "nearly right"; it is
noise with a preference. The mechanical one, which goes through no narrative
intent at all, reaches 75% on the largest cell and agrees with a reading made
by hand on a dialogue. Two different roads, the same answer.

### The front of the model

The one thing no data could say. The scripts decide the directions, the mesh
decides which way is the front, and the only way to know is to look at it:

```
python tools/view.py char c_npc_05 --azim 180   # the face
python tools/view.py char c_npc_05 --azim 0     # the back of the head
```

The characters are authored **facing −Z**, that is, already turned to
direction 1. Hence the angles `(180°, 0°, 90°, −90°)` in `ANGLES`.

## The world's unit of measure

A cell is **1.6**. Two measurements say so, and they meet from files that know
nothing of each other:

- the arguments of `CreateNpc` are multiples of 0.8 and mostly of 1.6
  (`1.6`, `3.2`, `4.8`, `-9.6`…);
- every character in `Character/c_obj_all.ps3.dsb` is **exactly 1.60** tall,
  with its origin at the feet — median over 31 NPC models, min 0.70, max 1.61.

**A character is one cell tall.** Everything else rests on this fact, and it
can be seen by eye on the checkered stage of `view.py event`, where one square
is one cell.

## Poses, and why there is no skeleton

The models have no rig. Under each character there are 2 to 6 child nodes,
and each one is a **whole character** 1.6 tall, spaced 2.0 apart along X in
the authoring scene — 162 spacings of 200 are exactly 2.0. They are not parts:
they are **frames**.

| suffix | 01 | 02_a | 02_b | 03 | 06, 07, 08 |
|---|---|---|---|---|---|
| occurrences | 102 | 58 | 58 | 44 | 44 |
| reading | standing | first step | second step | special pose | extra |

The game animates **by swapping the mesh**, like a sprite game. It fits the
rest of its aesthetic, and it explains why skinning — solved in session 3 —
appears in only one file on the whole disc, `Opening.ps3.dsb`.

The API confirms it, and it is the independent proof: `SetNpcNode(name, 0..3)`
picks a child by **ordinal**. `SetNpcNode("SwordPedestal", 1)` is the pedestal
with the sword, `0` the empty one. A method that chooses among a node's
children only makes sense if the children are alternatives, not parts.

The order matters, and it is **alphabetical**, not the file's: the nodes are
written as `_01`, `_02_b`, `_02_a`, `_03`, and only once they are sorted by
name does `SetNpcNode(x, 1)` become sensible.

## Movement does not block

`MoveNpc` starts a movement and the script carries on. This shows when the
wait that follows is used as a stopwatch: at the same speed (3.2) and the same
wait (0.5 s) the distances covered are 1.6 — 3.2 — 4.8. The wait measures
nothing.

So the registry integrates the motion over time, in `tick()`, and a character
can still be halfway there when the event closes.

### The signatures, given by the names

```
MoveNpc(name, dx, dz, speed [, flag])          87 calls
MoveNpcAndY(name, dx, dy, dz, speed)            5 calls
MovePlayer(dx, dz, speed)                      43 calls
```

The second one's name **declares the difference**: the first has no Y. The
speed confirms it. It stays the last argument in both and is 3.2 in 76 calls
of 87 — and it comes back as the third and last argument of `MovePlayer`, with
the same family of values (2.4 — 3.2 — 4.8 — 6.4).

That the speed is in units per second remains **unconfirmed**: nothing in the
corpus times it (see above). It is the simplest hypothesis consistent with the
data, and 3.2 gives two cells a second, which is a walking pace.

## The models

`Character/c_obj_all.ps3.dsb` is the library: 22 MB, 646 nodes, **184 roots**.

| family | c_npc | c_enm | c_ply | i_evt | i_mwp | i_nml | i_swp | i_she | i_mgc |
|---|---|---|---|---|---|---|---|---|---|
| count | 31 | 39 | 7 | 30 | 24 | 26 | 9 | 6 | 6 |

All of them on a single texture, `dot_base.dds`: they are voxels, and the
colour lives in the palette.

The 30 `i_evt` are **leaves**, with no frames. An altar does not walk.

### Which model goes with which name: the file names say

The name the script uses — `"YoungWomana4_150"` — is a **logical identifier**,
and it appears in no binary data on the disc. It looked like EBOOT material
(Phase 3). It was not: the table is in the **names of the script files**.

The 237 scripts under `Event/npcevent_*` are named
`npcevent_n<NN><archetype><id>.lua.eu` —

```
npcevent_n05oldmana7_010.lua.eu
npcevent_n11imperialguarda3_320.lua.eu
npcevent_n16chickena3_010.lua.eu
```

— and that number is **the index of the `c_npc_NN` model**.

The **bijection** says it is a table and not a coincidence: over 237 scripts,
there are zero indices with more than one archetype and zero archetypes with
more than one index.

| | | | | | |
|---|---|---|---|---|---|
| 02 merchant | 03 youngman | 04 youngwoman | 05 oldman | 06 oldwoman | 07 girl |
| 08 boy | 10 king | 11 imperialguard | 12 ladysmaid | 14 dog | 15 cat |
| 16 chicken | 19 princessbug | 25 blacksmith | 26 goblinred | 31 spelunker | |
| 01 wiseman1 | 20 wiseman2 | 21 wiseman3 | 22 wiseman4 | 23 wiseman5 | 24 wiseman6 |

> **Session 12: twenty of twenty-two, and two corrected.** The disc declares
> the table — 1,279 `addNodeListElement` lines in `all.lua.eu`, see
> [`objects.md`](objects.md) — and it confirms this whole grid except for two
> cells:
>
> - **`princessbug` is `c_npc_26`**, not `c_npc_19`: the table swaps exactly
>   those two numbers, which are also the two that session 8 had pointed to
>   as the weak spot. Seen, the difference is one of colour — `c_npc_19`, `26`
>   and `27` are three winged figures, red, blue and green, and the files are
>   named `N19PrincessBug`, `N26PrincessBugB`, `N27PrincessBugC`;
> - **`goblinred` is `c_enm_12`**, which is an *enemy* model. The friendly red
>   goblins of the village reuse the red goblin you fight, and that is why
>   there is no `N26GoblinRed` under `Object/`.
>
> The second also says why the inference could not get there: it was looking
> for a `c_npc_NN` and it found one. The number in the name of a **dialogue**
> script and the number of the **model** are two numberings, not one — they
> match twenty times out of twenty-two, which is why they looked like the
> same.

And it can be checked by eye, which here is a proof and not an impression — a
dog and a chicken cannot be mistaken for anything else:

```
python tools/view.py char c_npc_31,c_npc_12,c_npc_11,c_npc_10,c_npc_16,c_npc_14
```

gives, in order: the blue overalls and red cap of **Spelunker**, a maid, a
guard with a spear, a gold crown on an ermine mantle, a white **chicken** with
a red comb, a brown **dog**. Six of six.

The first clue came by chance, in session 4: `c_npc_05`, once drawn, looked
like an old man, and `n05` is `oldman`.

**66 names of 99** have a declared model this way. The 33 that remain are the
extras of the main events (`Princess`, `Priest`, `Landlord`,
`LegendHeroGhost`) and the props (`OrbAltar01`, `BossMarker01`): none of them
has an `npcevent`, because the code created them without going through the
map-NPC mechanism. For them there is still the stable slot by name, which is a
declared placeholder.

> **Session 5, six more archetypes.** `WiseMan1`…`WiseMan6` were in that list
> of extras, and they did not belong there: each has an `npcevent`, and so a
> declared model — `c_npc_01` and `c_npc_20`…`c_npc_24`. They had been missed
> because the first census looked at the names the **event scripts** use, and
> the six wise men speak almost only through their own.
> The full directory is now `entity.npc_directory()`: it reads the 243 files
> and returns, for each identifier, the index, the archetype, the exact name
> and the path of the dialogue. See [`walk.md`](walk.md).

#### The coincidence to watch out for

Eleven directories under `Event/` have a `<Name>.ps3.dsb`, and one is called
`Priest`, like a `CreateNpc` name. It looked like a successful resolution — a
script name landing on a file on the disc. But
`Event/Priest/Priest.ps3.dsb` measures **0.96 × 0.64 × 0.96** and uses
`cliff_01.dds`: it is the *set* of the priest's event, not the priest. A
character in this game is 1.60 tall and lives on `dot_base.dds`.

The coincidence would have passed for a proof if nobody had looked at the
numbers. The other ten (`Devil`, `Dragon`, `Golem`…) are the boss scenes.

## Placement in the world

`CreateNpc(x, y, z, name)` places the NPC **relative to the player**: the
coordinates lie between −9.6 and +16.0 and are multiples of 0.8, while
`SetPlayerPosition` uses integers up to 89. They are offsets, not points in
the world. Y is 0 in 108 calls of 115, and that is exactly what says the
second argument is the height: the five calls where it is 8.0 are the two
lovers on the balcony in `mapevent_f80`.

And the player stands where `SetPlayerPosition(cx, cy, floor)` says: **cells
of the logical grid** of the `MAP_ALIGNMENT` files, with the third argument
being the floor (0 in 48 calls of 71). A cell is `TILE`, and the origin is at a
**corner** — X positive to the right, Z **negative** downwards:

```
world = (cx · 1.6,  y,  −cy · 1.6)
```

The arguments of the scripts' absolute cameras say themselves that the origin
is at a corner: their X is always positive (8.33…130.53) and their Z always
negative (−206.36…−11.19) — one quadrant, not a neighbourhood of zero. And it
checks out: every point read this way falls inside `[0, w·1.6] × [−h·1.6, 0]`
in **17 cases of 17** among the events that the `MAP_ALIGNMENT` files can
assign to a map with the `-e` flag.

One obstacle remained, and it was the real knot: the loaded maps measured
twenty-odd units while the cameras reached x = 158. It was not a problem of
reference frame but of **composition** — the sections of a `.pac` are screens
to be laid out in a grid, and they were all being drawn stacked on top of each
other. Once that was untangled ([`format_pac.md`](format_pac.md)), the two
systems match and the conversion is a subtraction:

```python
local = world − (w·1.6/2,  0,  −h·1.6/2)      # host.to_local()
```

With no map loaded — the empty stage — the cell is just recorded: there are no
`w` and `h` to translate it with.

### The NPCs that are already on the map

Of the 99 names in the corpus only 40 go through `CreateNpc`. The others are
there before the event, and the script just names them — and no file seemed
to say where they stood.

The `MAP_ALIGNMENT` says. Among the 14,099 cells with an object there are
**271** whose class is **the identifier alone**, with no parameters and
nothing else:

```
d_20_1   cell (7, 11)   cls = "a1_010"      -> Kinga1_010
d_20_9   cell (7, 16)   cls = "b8_010"      -> WiseMan2b8_010
d_4_1_1  cell (62, 16)  cls = "b4_010"      -> PrincessBugb4_010
```

The name the script uses is **archetype plus identifier**, so the tail of the
name is the key: `OldWomana6_010` = `OldWoman` + `a6_010`. Of 50 names in the
corpus that carry an identifier, **37 find their cell** — and the cell
converts to a position with the same formula as the player's.

The final count: **72 names of 99 placed**, 40 from `CreateNpc` and 37 from
the map (with some overlap). The 27 that remain are not drawn:
`visible_entities()` shows only those with a position that someone actually
declared, and `unplaced()` lists the others. Putting them at the player's feet
would make them visible and wrong, which is worse than absent.

The parser is `mapdat.npc_spots()`; the host loads it with `Host.load_map()`,
which is also what gives it `(w, h)`.

> **Session 5: the 199 spots nobody named.** The 37 names above are the ones
> an event mentions. The other 199 spots are named by **their own**
> `npcevent_*` script, and putting the two halves back together brings the
> count to **225 identifiers of 236 (95%)** with a name, a model and a
> dialogue. From there a map populates itself, without waiting for an event to
> name anyone: `walk.Walk.populate()`. See [`walk.md`](walk.md).
>
> One thing the file names alone do not say: the **capitals**. The file name
> is all lower case, and there is no way to choose between `Blacksmith` and
> `BlackSmith`. The 151 scripts that name themselves in full inside
> (`setnpccamerac("OldMana1_300")`) say it — another declaration of the same
> fact, taken from another part of the file.

## The empty stage

```
python tools/view.py event <script.lua.eu> [--skip N] [--at x,y,z]
```

An event **with no map**, on a checkered floor of cells. It exists because the
two are different subsystems and until now they got in each other's way: a
map in this game is full, it has a ceiling too, and where there is free ground
is written nowhere. The NPCs ended up inside a wall and there was no seeing
whether the registry worked.

The floor is ours, not an asset: it gives the stage a readable scale, and one
square is `TILE`.

## How it is drawn

The map has its transforms baked into the vertices — that is what makes it
possible to draw 54 million of them. The entities do not: they move every
frame. Hence the `model` matrix in the shader, the identity for the map and
position plus rotation for a character, read from the registry **at draw
time**. Movement costs nothing: there is no buffer to rebuild.

The wrong pose and the hidden entity are switched off with a **null matrix**
instead of a branch: the triangles collapse to a point and the rasterizer
throws them away. It costs less than taking a vertex list out of the batch and
putting it back every frame.

The event camera is in command only if its target exists for us:
`SetCameraAtBody` on a placed entity, or an absolute point that falls
**inside** the loaded scene. Otherwise the whole shot is discarded. The filter
was born as a safety net against black frames; now that the reference frames
match, it is almost always the absolute point that passes, and that is the
right case.

### The signature of `SetCamera` was wrong

The six-argument form was read as `(time, distance, azimuth, x, y, z)`, with
the distance marked "a hypothesis to be confirmed". It was not one: **the
second argument goes down to −17.72**, and a negative distance does not exist.
The distributions over the 142 calls say something else —

| arg | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| range | 0.10…10.22 | −17.72…64.83 | −180…338 | 8.33…130.53 | 1.26…22.77 | −206.36…−11.19 |
| reading | time (0.10 in 140/142) | elevation | azimuth | x | y | z |

— that is, `(time, elevation, azimuth, x, y, z)`: **there is no** distance. The
signs of the last three are the same signature as the corner reference frame,
and that is what made the rest suspect.

## The methods implemented

Calls **measured** by running all 377 scripts, not counted in the source: the
two differ, and the first is the one that counts.

| method | calls | what it does |
|---|---:|---|
| `Pause` / `Play` | 185 / 184 | freezes everything: it is almost always the first line of an event |
| `SetPlayerDirection` | 183 | |
| `SetNpcDirection` | 147 | |
| `LockPlayer` / `UnlockPlayer` | 133 / 133 | stops the player, not the world |
| `PlayNpc` / `PauseNpc` | 82 / 80 | |
| `SetStatusVisible` | 79 | the HUD |
| `CreateNpc` | 57 | |
| `SetNpcVisible` | 57 | |
| `PlayEnemy` / `PauseEnemy` | 52 / 51 | |
| `setPlayerAngle` | 52 | the fine angle, in degrees |
| `SetPlayerPosition` | 46 | records the cell, see above |
| `SavePlayerAngle` / `RestorPlayerAngle` | 37 / 36 | |
| `MovePlayer` | 28 | |
| `MoveNpc` | 24 | |
| `SetNpcNode` | 16 | the pose |
| `SetPlayerVisible` | 2 | |
| `MoveNpcAndY` | 0 | |

Two readings that the static count does not give. `setPlayerAngle` appears four
times in the source of the events and makes **52** calls: it sits inside a
shared helper in `eventfunction.lua.eu`, and counting lines does not see it.
`MoveNpcAndY` is the reverse: five calls written, **zero** executed — they are
all on branches that are not taken with the starting flags.

With these, the host's coverage goes from **22 methods / 63% of calls** to
**43 methods / 87%**.

## Enemies — `entity.py bestiary()`, `enemy_models()`

The TODO had them as "created by the code, on its `EnemyObserver`s", and said
to look at those cells' parameters before concluding that the EBOOT is needed.
The cells do not in fact carry enemies: the 65 `EnemyObserver`s have a `-gNNN`
and nothing else, that is, **a room number**, and the cell's five numeric
fields (`2001`, `0`, `257`, `2`, `4100`) are the same that any `observer`
carries — properties of the cell, not of the enemy.

*(Session 8: that `4100` was the right trail read in the wrong place. It is the
**actor** field, and it is 4100 because that cell hosts an observer. The
enemies are in **other** cells, where the same field carries their album
identifier — 10,196 on the whole disc. See [`walk.md`](walk.md), the section
on actors.)*

The census does exist, though, and it is in the clear: the **enemy album**.
`UserInterface/EnemyView/EnemyView.lua.eu` is a descriptor like the others and
declares the whole table, 46 entries:

```lua
Num=5003,                              -- identifier, from 5002 to 5082
NodeStrings="c_enm_01_01",             -- the model
NameStrings="Ｋｉｌｌｅｒ　Ｒａｂｂｉｔ",
LivingId=LIVING.FIELD_GRASS,           -- where it lives
ItemId=item.Item.IL_RED_APPLE,         -- what it drops
```

**The models resolve 46 of 46**, and the way they are split says something
about the game: 37 are **nodes** inside `Character/c_obj_all.ps3.dsb` — the
same shape as the NPCs, which are nodes inside a single scene — and the 9
**bosses** have a file each (`c_bos_01_all.ps3.dsb`). The field being called
`NodeStrings` already said so: it is not a file name. `view.py char c_enm_01`
draws the first one, and it is a purple rabbit with red horns: ツノウサギ in
the Japanese comment, `Killer Rabbit` in the descriptor.

**The fifteen habitats** are `FIELD_*` and `DUNGEON_*` by element, and the
seven dungeons match one to one the seven temples that `Item.lua.eu` declares
in `WarpItem`:

| `LivingId` | temple |
|---|---|
| `DUNGEON_GRASS` | 草原の神殿, `Dungeon1` |
| `DUNGEON_FOREST` | 森の神殿, `Dungeon2` |
| `DUNGEON_SANDS` | 砂漠の神殿, `Dungeon3` |
| `DUNGEON_WATER` | 水の神殿, `Dungeon4` |
| `DUNGEON_FIRE` | 炎の神殿, `Dungeon5` |
| `DUNGEON_EARO` | 風の神殿, `Dungeon6` — *earo* is *aero*, the wind |
| `DUNGEON_MAGIC` | 闇の塔, `Dungeon7` |

So **which enemy belongs to which dungeon is known without the EBOOT**.

*(Refined in session 8, and the refinement matters: `LivingId` gives an
enemy's **family**, not where the game puts it. Now that where it puts it is
known — the grid declares it cell by cell — the two can be compared, and the
temple's English name matches the habitat of the species placed in it in only
**47.1%** of cases over 1,988 enemies. With seven habitats that is well above
chance, so the correlation is there and it is strong; but it is not a rule,
and the Flame Temple is full of `DUNGEON_WATER` enemies. Once the real data is
there, the habitat goes back to being what it is: a classification.)*

The table was then validated against an external source that knows nothing of
these files: a walkthrough assigns Eelagon to the grass temple, Queen Bee to
the forest, Giga Golem to the desert, Kraken to the water, Dragon to the fire,
Dark Knight to the wind, and puts Fuelle and Onyx in the tower. **Eight of
eight** agree with the habitats above, and with them the last doubt about
`EARO` falls.

What was said to be left to the code — *how many* it puts in each room and by
what rule — **is not left to the code**: the logical grid declares it, cell by
cell, in the field at +0x10 of the record. See [`walk.md`](walk.md), the
section on enemies. Here it is enough that two of the 46 stand out in the data
before they do in the game, **5075 Crystal Slime** and **5076 Blue Dragon**,
the only ones with `LivingId = -1`, that is, with no habitat — and they are
exactly the two that the guides describe as able to appear anywhere.

A note on method, which cost the first attempt: without the **permissive
tables** this descriptor does not run at all, because it names native
constants that no script defines (`LIVING`, `GameDataFlags`, `item`). With
bare `lua.execute` the file raises and the table seems not to be there. It is
the same obstacle as the events, and the solution was already written in
`host.BOOT`.

## Checks

`python tools/entity.py` tests 49 properties, and they are not courtesy tests:
each one is something inferred from the data, and if it stops holding, it is
the inference that is wrong. The directions opposite in pairs, the angles that
bring the model's front onto the right unit vector, the offset relative to the
player, a 4.8 move at speed 3.2 that ends in 1.5 s, the freeze that stops the
motion, the reduction of names to archetypes.
