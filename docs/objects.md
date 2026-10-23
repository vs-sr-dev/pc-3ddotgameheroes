# Map objects, and the symbol table — `tools/nodes.py`

*Session 12.* The TODO asked how the twenty-one gimmicks of `Object/gimmick/`
are **hooked up**: a jar does not load `EN_ENEMY_NN`, so the rule by which
session 11 had linked the enemies to their models does not reach it, and the
question was what route it takes.

It takes no rule, because **there is a table**, and it is in the clear in
`all.lua.eu` — the fifth session running in which that file held what we were
looking for:

```lua
package_manager.gPackageManager:addNodeListElement(
    package_manager.TFI_EVENT_OBJECT,  package_manager.DFI_EVENT_OBJECT,
    package_manager.MPD_M_OBJ_127_a,   "m_obj_127_01" );
```

Four arguments: the texture package, the scene package, **the native constant
by which the code names the piece**, and **the name of the node**. There are
**1,279** lines, under `../lua/packageManager/`, and they cover everything the
game loads — the player, the enemies, the bosses, the NPCs, the objects, the
weapons, the terrain.

So the mapping between the name a script speaks and the node inside a `.dsb`
is no longer an inference of ours: it is declared data.

```
python tools/nodes.py census                 the table, and what it confirms
python tools/nodes.py props                  map objects, by id
python tools/nodes.py enum MPD_M_OBJ_127_a   where a symbol lives
```

## How well it holds

```
declared nodes                               1,279
  that really exist in a .dsb                1,267    99.1%
constants passed to AddNode by the scripts     394
  declared in the table                        387    98.2%
```

The twelve declared nodes that do not exist are leftovers (`m_obj_27`,
`m_obj_30`, `m_obj_32`, `m_obj_35`, `m_obj_42`, and three pieces of the
dragon); the seven undeclared constants are their mirror image, among them
`MPD_E_TORCH`, which `Object/Torch` asks for and which is no longer in the
table — the torch is now loaded by number.

And the **ten commented-out lines** all name things that cannot be drawn: nine
a node that exists in no `.dsb`, the tenth the grouping node for the grass,
which has no mesh. That it is exactly those is the counter-proof that the
table was maintained.

## What it confirms: three sessions of inference, and where they went wrong

The table is an oracle on a chain the project had built by itself, and it
confirms almost all of it:

```
EN_ENEMY_NN -> c_enm_NN      135 entries of 136
NP_NPC_NN   -> c_npc_NN      112 entries of 116
```

The five exceptions are not scattered, and one explains itself — in the file,
under the line that replaces it:

```lua
  addNodeListElement( ..., EN_ENEMY_24_08, "c_enm_11_08" );
--addNodeListElement( ..., EN_ENEMY_24_08, "c_enm_24_08" );
```

`c_enm_24_08` does not exist, and the blue Slime's projectile takes the blue
Spider's. The authors left the original commented out right beside it.

The other four are **two swapped numbers** — `NP_NPC_19` is `c_npc_26` and
`NP_NPC_26` is `c_npc_19` — and that is exactly the pair session 8 had pointed
to as the weak spot of its own directory: *"the exceptions **all** fall on
`c_npc_19`…`c_npc_26`"*. The disc says where the discrepancy was and confirms
everything else.

### And the directory of inhabitants, by another road

The 263 files of `../lua/Object/npc/` are one per inhabitant, named
`n<NN><archetype><identifier>`, and each loads its own node. Passing them
through the table **reads** the archetype→model directory that session 4 had
inferred from the names of the 237 dialogue scripts:

```
comparable archetypes     22
  agreeing                20
  corrected                2
```

And the two that change are worth more than the twenty that hold:

- **`princessbug` is `c_npc_26`**, not `c_npc_19` — that is the swap above.
  Seen, the difference is one of colour: `c_npc_19`, `c_npc_26` and `c_npc_27`
  are **three winged figures**, red, blue and green, and indeed the files are
  named `N19PrincessBug`, `N26PrincessBugB`, `N27PrincessBugC`.
- **`goblinred` is `c_enm_12`**, that is, an **enemy** model. This is not a
  number off by a slot, it is a change of family: the friendly red goblins of
  the village reuse the red goblin you fight, and that is why there is no
  `N26GoblinRed` under `Object/` — it was not needed. `view.py char
  c_enm_12` draws a red creature with a blue tunic and white tusks.

No inference made *within* the `c_npc` family alone could have got there: the
directory was looking for a `c_npc_NN` and found one. It was wrong while
staying plausible, which is how well-made inferences go wrong.

*Hence a note on method: the number in the name of a **dialogue** script and
the number of the **model** are two numberings, not one. They match twenty
times out of twenty-two, which is why they looked like the same thing.*

## Map objects: the cell declares the model

The scripts of `Object/gimmick/` and `Object/MessageBoard/` load
`MPD_M_OBJ_*`, which the table sends to `m_obj_*` inside
`map/map_model/map_object.ps3.dsb` — plus `Torch.ps3.dsb` for 99, which has a
file of its own like the bosses. And the cell already knows it:

> **the cell identifier is `4000 + the model number`**

It is not a reading of one case: three families of scripts that know nothing
of each other bear it out, with three different numbers, and **51 cells of
51** with not one disagreeing.

| cell class | id | model | scripts |
|---|---:|---|---|
| `Signboard00`…`Signboard33` | 4041 | `m_obj_41` | 34 files |
| `Stonemark00`…`Stonemark11` | 4067 | `m_obj_67` | 12 files |
| `Well01`, `Well02`, `Well03` | 4063 | `m_obj_63` | 3 files |

From there the whole 4xxx band can be read, which until yesterday was just a
number:

```
4127   272 cells   m_obj_127    Grass, the grass you cut
4111     6 cells   m_obj_111    BossMarker, the boss's gravestone
4116..21 1 cell    m_obj_116..121  the six orb altars
4062     2 cells   m_obj_62     SwordPedestal
4099   859 cells   m_obj_99     the torch, from its own library
4060 1,022 cells   m_obj_60     the chest
```

Over the whole disc: **11,924 object cells, 7,695 with a model (64.5%)**.

### The proof by structure, which is stronger than the count

The six altars and the six gravestones are not just anywhere:

```
D_1_2  Grass Temple    4111          D_1_3  Grass Temple    4116  (7,4)
D_2_2  Forest Temple   4111          D_2_3  Forest Temple   4117  (8,4)
D_3_2  Desert Temple   4111          D_3_3  Desert Temple   4118  (8,4)
D_4_2  Aqua Temple     4111          D_4_3  Aqua Temple     4119  (8,4)
D_5_2  Flame Temple    4111          D_5_3  Flame Temple    4120  (8,4)
D_6_2  Wind Temple     4111          D_6_3  Wind Temple     4121  (8,4)
```

One gravestone per boss room, one altar in the room after it, always in the
same cell. And the order of the altars is the order of the temples, which can
be read in the scripts' guards: `item_yelloworb`, `item_greenorb`,
`item_grayorb`, `item_blueorb`, `item_redorb`, `item_whiteorb`. **Six of six,
in the right temple, in the right order.**

*And in session 13, of the right colour too*, which is the proof that was
missing here — the orb's **material**, read from the index at `+0x00` of its
chunk:

| altar | the script's item | material | colour | the walkthrough |
|---|---|---|---|---|
| 4116 | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

Six of six with the walkthrough's names. And the two internal names that do
not describe a colour — `gray` and `white` — are exactly the two that the
model contradicts: the name the game shows the player wins over the one the
authors wrote down for themselves.

The material has to be **looked at**, not inferred from the number:
`m_obj_118_b` uses `orb_121` and `m_obj_121_b` uses `orb_118`, an **exact
swap** among four that match. It is the second swapped pair this disc has made
us find, after `NP_NPC_19` ↔ `NP_NPC_26`.

The gravestones are seven scripts for six cells, and the seventh says so
itself: in `BossMarker07` the guard is commented out and in place of the event
there is `Print("ぼひょー")`. It is a leftover, and it signs itself.

`SwordPedestal` is in two maps, and one is called `//Sword Room`. The
walkthrough: *"retrieve the Ancient Sword from the pedestal"*.

### And absence reads like presence

Identifiers **4100** (the `Warp`s and the observers) and **4101** (`Exit`,
`destructionWall`, `WarpDoor`) are among the few that do *not* have an
`m_obj`. It is not a hole in the table: there is nothing to draw — the same
thing [`walk.md`](walk.md) had measured from the geometry side, without being
able to explain it.

And it shows better than that. Of the 4,229 cells without a model, **3,843
(91%) are in `4100`…`4105`**, six numbers in a row; and `m_obj_100`…`m_obj_107`
is **the longest gap in the library's whole numbering**, eight numbers, where
all the others are one to five wide and scattered. The disc reserved a block
of the object numbering for the objects that have no object.

> *Corollary of* `walk.md`: "when a declared object is not found in any of the
> files that describe the world, it is not a reading defect — it is the
> declaration that that world is built at runtime". Now that declaration has
> an address too.

## The other two bands

```
3000 + NN  ->  d_hmw_NN     28 numbers of 28
1000 + NN  ->  ?            38 numbers, from 1 to 51
```

`d_hmw` are the *"Dungeon配置物"*, and the authors' comment calls them exactly
that — dungeon **placement objects**. The 28 numbers the cells use are exactly
the 28 that `d_haichi.ps3.dsb` carries, not one more or one less; the only
declared one the cells do not use is `d_hmw_03`, which is also the only one
with sub-variants.

The 1000 band is the overworld's equivalent — 85% of its 8,053 cells are in a
`field_*` — and **it does not close the same way**. The reason can be seen,
and it is the useful thing to leave written down: where the dungeon has
**one** family (`d_hmw`), the overworld has **two** (`f_hmw` and `f_ntr`, that
is, artefacts and nature), and a single number cannot say which of the two.
The field is narrowed to two declared lists, of 21 and 14 numbers; what is
missing is the rule by which the disc lines them up.

*Tried and fallen: that the number is the ordinal in the package's list. In
the dungeon it would give 1…28, and instead the numbers go up to 36 with
gaps, that is, they are names. If they are names there, in the overworld they
cannot be ordinals.*

### The dungeon count adds up from three files

It is worth writing down, because it is the yardstick for measuring the
overworld:

```
objects declared by d_haichi.ps3.dsb              28
DFI_DUNGEON_OBJECT entries in the symbol table    28
numbers used by the 3xxx band                     28
```

The last doubt closes too: `d_hmw_03`, which was written here as *"the only
declared one the cells do not use"*, **is not missing — it is in another
file**. The family is split between `d_haichi` (the 28) and `d_chikei`, which
carries it alone, and it is also the only one with sub-variants. It was not a
leftover: it was elsewhere.

For the overworld the same two counts agree with each other — `f_haichi`
declares **40** objects and `DFI_FIELD_OBJECT` has **40** entries — but the
third does not: the cells use 38 numbers that go up to **51**.

### And there are not two families: the table names them all

The field had been described as narrowed to `f_hmw` and `f_ntr`. There are
more, and the symbol table gives the full name behind the abbreviation — the
constant is in rōmaji where the node is in three letters:

| abbreviation | constant | entries | what it is |
|---|---|---:|---|
| `d_kbe` | `MPD_D_KABE` | 145 | 壁, the wall |
| `d_dns` | `MPD_D_DANSA` | 28 | 段差, the step |
| `d_yka` | `MPD_D_YUKA` | 14 | 床, the floor |
| `d_hsr` | `MPD_D_HASIRA` | 8 | 柱, the column |
| `d_skr` | `MPD_D_SIKIRI` | 7 | 仕切り, the partition |
| `f_gke` | `MPD_F_CLIF` | 62 | 崖, the cliff |
| `f_jmn` | `MPD_F_CHIKEI` | 46 | 地面/地形, the terrain |
| `d_hmw`, `f_hmw` | `MPD_D_HMW`, `MPD_F_HMW` | 33, 28 | not expanded |
| `f_ntr` | `MPD_F_NTR` | 17 | not expanded |

Seven abbreviations of nine can be read, and the two that remain are exactly
those of the open bands. *(`NTR` for "nature" and `HMW` for the artefacts are
the reading this document already used; one holds up on the English, the
other remains a conjecture — whereas the other seven are no longer
conjectures.)*

And `MPD_F_CLIF_N_M` → `f_gke_NN_MM` sits beside `MPD_F_CHIKEI_N_M` →
`f_jmn_NN_MM` with **the same first number**, `{1, 3, 5, 6, 8}`: the first
number is the *terrain type* and the second the piece. Cliff and ground are
declared in pairs.

### The 1xxx band: three things it is not

Measured, so the next person does not repeat them:

- **it is not `1000 +` the number of a node.** All the disc's families tried:
  the best coverage of the 38 numbers is **71%** (`m_obj` and `c_enm`), and
  none reaches 51;
- **it is not an index local to the map.** The same numbers recur on different
  maps — 42 in five `D_21`/`D_22` maps, 21 in eight — and each map uses **very
  few**, median 4, with dozens of cells each. It is a global identifier, like
  4xxx;
- **it is not the edge of a screen.** The 1xxx cells that fall on the edge of
  their own screen are **29%**, against the 21% chance would give.

What does show, and it is the real clue: the cells of the same number **draw
figures**. In `D_24_3` number 21 makes the **frame of the map**, one cell thick
along all four sides; in `D_23_1` it makes a continuous column the full height;
in `field_16` numbers 41, 42 and 43 stand in **regular rows** two or three
cells apart. A number that marks a perimeter is not one object per cell: it
looks more like an **outline**, and the families the disc keeps for outlines
now have a name — 崖 the cliff, 段差 the step, 壁 the wall.

### And the band splits in two, measured against the terrain

If a number is the outline of a ledge, it has to be **where the terrain makes
a step**. Measured on the collision — the cell's maximum height against that
of its four neighbours, a jump of more than half a cell:

```
number   cells   with a step beside it
     1   1,154        86%
     4     195        85%
    43     293        80%
    44     152        80%
     6     668        72%
    21   1,016        52%
    41   1,655        46%
     5     691        41%
                            mean over map cells          33%
    26     290        20%
    42   1,362        14%
```

It is not one result, it is two groups: some sit on a step **three times more
often than chance** and some less than half as often. A number at 86% and one
at 14% cannot be the same kind of thing, and the boundary falls where one
expects it to — between what follows the shape of the terrain (the cliffs, the
steps) and what simply stands on it.

This is the point to start again from, and now the question is more precise
than *"what is the rule"*: **they are two bands in one**, and it pays to
separate them first and then look for two rules.

## How they are drawn — `walk.Walk.populate_props`, `view.Charlib`

A map object enters the entity registry like everything else, and the drawer
did not need a new road: only the library in which to look up the node
changes, and the names are enough to say which one, because they are unique
across the four in `map/map_model/`.

Two choices worth declaring:

- **which node**, when a model has more than one. The **first `AddNode` of
  the script** is taken, which is the pose in which the object appears:
  `Grass` loads the grass first and then the cut, and whoever enters the room
  sees the grass. On a tie, the lower name — `_a` before `_b`.
- **no poses**. A jar does not walk: the pose the entity asks for is ignored.

```
python tools/view.py play d_60_3 --cell 11,13     the well, with its signboard
python tools/view.py play field_91 --cell 27,44   the courtyard's columns
python tools/view.py play d_1_1_1 --cell 39,18 --skip 6   the jars and the door
python tools/view.py play <map> --no-props        without them, for comparison
python tools/view.py char m_obj_116_a,m_obj_116_b,m_obj_63,m_obj_60,m_obj_111
```

The well in `D_60_3` is the recognisability check: the cell says `Well01`,
identifier 4063 says `m_obj_63`, and what appears is **a stone well with a
wooden frame**, with the signboard the neighbouring cell declares beside it.
In the castle courtyard **columns and braziers lined up in mirror image** on
the two sides appear, which is what *配置物* means. And in the Grass Temple
room where session 8 had put two Scorpions and one Soldier Bones there are now
also **two jars and the red door**.

Lined up with `view.py char`, the models are recognised one by one — and one
closes a circle on its own:

```
m_obj_116_a   a stone altar
m_obj_116_b   a yellow orb
m_obj_63      a well
m_obj_60      a jar
m_obj_111     a stepped monument
m_obj_127_01  a tuft of green grass
```

**`m_obj_116_b` is a yellow orb**, and it is the second node that `OrbAltar01`
loads — the one that `OrbAltar01InitializeActor` switches off with
`SetNodeVisible(1, false)` *"if you have already taken the yellow orb"*
(`EventFlag.item_yelloworb`). The code says what to hide and the model is
yellow: two files that know nothing of each other, the same orb.

`m_obj_60` is **a jar**, and it is the most numerous object on the disc:
**1,022 cells**, more than any other. That it is the three-colour `Jar` is
shown a little further down, and the proof is the same one that takes apart
the hypothesis about `AddColor`.

## `AddColor` is not a tint to apply — the hypothesis that fell

The objects come out **dark**, and the obvious explanation was that
`GrassInitialize` calls `AddColor(0.25, 1.0, 0.25)` and we do not execute it.
It is false, and it is worth having written down because it was the first
item of the following TODO.

The first doubt is in the code: `12GoblinRed` calls `AddColor` **four times in
a row and the first two are identical**, which rules out both "one per node"
(it loads four, all different) and "one per colour of the model" (they would
be distinct).

The proof is a comparison that costs nothing. For each declared colour, the
nearest hue is looked for **among those the vertices of its model already
carry**, and the gap in **angle** is measured — that is, the colour short of
its brightness, which in the vertices is baked light:

```
python tools/nodes.py colors

132 colours declared by 42 files, against their own model's palette
  angle gap   median 0.5 degrees   under 5 degrees 94%
  model brightness over the declared   median 1.50
```

**Half a degree median over 132 values.** The colours that `AddColor` declares
*are* those of the model, not a tint to lay over it: applying them would
change the hue of nothing, and the darkness comes from our lighting, not from
a missing call.

What they are really for is still to be seen, but the hypothesis with the best
clue is that they are the **little cubes the thing shatters into**: 44 of the
52 files that call `AddColor` also call `SetAmount(n)`, and **the 8 that do
not are exactly the eight bosses** — which do not burst into cubes, they have
a death scene of their own.

### And it closes the question of the jar

Because the same measurement, applied to `Jar.lua` against `m_obj_60`, gives
three hits of three in a model that has seven hues:

```
declared  0.74 0.55 0.31  ->  0.593 0.442 0.245    0.3 degrees
declared  0.63 0.44 0.28  ->  0.304 0.213 0.135    0.1 degrees
declared  0.44 0.30 0.28  ->  0.373 0.254 0.238    0.1 degrees
```

**`m_obj_60` is the `Jar`**, and cell identifier 4060 is the jar: 1,022 cells,
the most numerous object on the disc. The question the TODO opened with —
*"a jar does not load `EN_ENEMY_NN`"* — closes here, and not in the way it was
put: the jar loads nothing because it has no script. The C++ instantiates it,
and of its own the disc declares the cell (`4000 + 60`) and the palette.

*And it is consistent that `Jar` is one of the **two** gimmicks of twenty-one
without a script — the other is `lava_fountain`, eleven parameters with the
authors' comments ("if you make too many the game stops"). Two files of data
only, for the two things the engine makes by itself.*

## What is missing

The darkness, which now we know where to look for: not in `AddColor` but in
the **lighting model**, which [`renderer.md`](renderer.md) has always declared
missing. The vertices carry a baked light ~1.5× brighter than the declared
colour, and we multiply it by a Lambertian of our own that snuffs it out.

And the 1xxx band remains open, the only one of the four cell numberings still
unsolved — see above.
