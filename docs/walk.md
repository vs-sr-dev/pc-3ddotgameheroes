# Walking the world

**Status: the game loop exists.** You stand on a map, walk from cell to cell,
cross a passage and arrive in the other map at the point the disc declares,
and talk to the inhabitants, who answer with their own dialogue.
Module: [`tools/walk.py`](../tools/walk.py) — rules and checks, no screen.
Command: `python tools/view.py play <map>`.

```
python tools/view.py play field_91          the castle courtyard, 33 inhabitants
python tools/view.py play d_1_1_1           the first dungeon
python tools/view.py walkabout              the measurement, over every map
python tools/walk.py                        the internal checks (50 properties)
```

Arrows or WASD to walk, space to talk to whoever is in front of you, `K`
removes and restores the ceiling, the mouse orbits, `ESC` quits.

This is the first thing in the project that is **played** rather than looked
at, and it is also the strictest integration test there is: it lines up the
composition of the screens, the logic grid, the passage graph, the NPC
directory, the entity registry and the Lua VM. If a single reference is wrong
the result is not a wrong picture — you walk into a wall, or come out in the
wrong map.

Almost every piece was already there; the missing link was the loop. The only
new format is the collision, [`MAPCOLLISION/*.DPK`](format_dpk.md), and it came
later — once walking made it obvious that approximating it was not enough.

## The rule: one cell at a time

A cell is `1.6` wide, which is also the height of a character. The step is
discrete and moves over time (`entity.Entity.move_to`), and turning **is not**
walking: if you are facing elsewhere, the first command only turns you. That
is how grid games behave, and it is also the only way to talk to someone
beside you without stepping onto them.

The command is relative to the viewer: "forward" is where the camera points,
not a fixed direction in the world. With the map rotated, the opposite is
disorienting.

## The wall

Cells outside the map (`0xFFFFFFFF` in the logic grid) are a wall, but a
**coarse** one: that grid marks rectangular regions, not corridors.

The real wall is given by `MAPCOLLISION/*.DPK` — see
[`format_dpk.md`](format_dpk.md) — one triangle mesh per map, in the same frame
of reference as the `.pac`, which is exactly what the game stops the player
with. Where it is missing (the event stages, the opening scene) the code falls
back on the drawn geometry, which is an approximation and does not hide it.

From mesh to answers: each cell holds a **column** of slices a quarter of a
cell thick, and for each slice the highest height found in it. The triangles
are seeded with points one slice apart, because in a collision mesh the
triangles are large — a floor of twenty cells is two triangles — and their
vertices alone would leave every cell in between empty.

Where the column starts and how many slices it has is **declared by the
mesh**, and that is not an allocation detail: see
[“The bottom and the sky”](#the-bottom-and-the-sky).

That gives the only two questions needed:

- **can you pass?** the column is free at body height, from +0.3 to +1.3
  above the feet;
- **where does the foot land?** the highest surface within one step of the
  feet — which is also how you climb a staircase without knowing it is a
  staircase, and how you do not climb a cliff.

A ledge higher than a step cannot be climbed **and cannot be descended**:
that is what stops you walking off the edge of a roof.

### The step is one cell high, and that is not a tuning

It was the only invented number in the whole system — I had written 0.6, "a
knee" — and it was wrong by a factor of nearly three. Two independent oracles
say so.

**The first: ledges are quantised.** Between neighbouring walkable cells the
height difference is an exact multiple of 1.6.

```
  0.00  (0 cells)     85.3%
  1.60  (1 cell)       8.6%
  3.20  (2 cells)      3.3%
  4.80  (3 cells)      0.2%
```

There is almost nothing in between. The world is built in steps as high as a
character, like everything else in this game.

**The second: the inhabitants saturate.** An inhabitant the map declares is a
place the game *must* let the player reach, or nobody could talk to them. How
many are reached as the threshold varies:

```
step  0.6:  206/264        step  2.5:  256/264
step  0.9:  208/264        step  3.3:  256/264
step  1.7:  255/264        step  4.9:  256/264
```

One cell buys 49 inhabitants; everything beyond it buys one. There was no
parameter to tune, there was a quantum to recognise.

### A cell has up to four floors

The gallery above the hall, the bridge over the moat, the roof over the house.
Keeping one level per cell turns a place you have already been into an
impassable ledge, and the walker's state is not "the cell" but **the cell and
the level**: someone on the gallery and someone below are in the same place
and do not meet.

### The mistake this part cost

The first version counted all the vertices together, and the map broke into
islands: from any point almost nothing was reachable, and it looked like a
threshold problem.

It was not. **A solid block has vertices only on its faces.** The floor of a
dungeon 1.6 high therefore offers two — the top face at 1.6 and the bottom face
at 0.0 — and the lower one, seen from the vertices alone, looks like a
perfectly walkable floor with a metre and a half of free air above it. In
other words you were walking inside the rock, on a level that does not exist,
cut off from everything.

What says which of the two faces is a floor is the **normal**: you stand on
what faces up. So the heights are collected into two tables — the upward-facing
surfaces for the floor, everything for the obstacle, because to bump into
something the normal does not matter.

*A corollary to keep: geometry declares surfaces, not volumes. Inferring the
solid from the vertices only works if you look at which way they face.*

## The bottom and the sky

The column was anchored at zero and 64 slices high, that is 25.6 units, and
both were assumed rather than measured. Both were wrong:

- **zero is not the bottom of the world.** 69 collision files out of 171 go
  below it, down to −4.35. Worse: the floor of a dungeon sits at `−0.000002` —
  the residue of a `float32` passed through a barycentric sum — and a slice
  anchored at zero loses it **entirely**. In `d_1_2` the 114 points that fell
  in the entrance cell were all 114 thrown away, and the arrival cell of the
  game's first passage came out as not walkable.
- **25.6 units is not the sky.** `FIELD_07` is a mountain and reaches 51.2:
  its summit was being cut off.

Base and height are now declared by the mesh (`walk.span()`), with one slice
of margin on each side.

### The backdrop

With the levels below zero restored, the measurement got **worse**: from 63%
to 41% of cells. The reason is that under every overworld map there is a
single flat quad spread from edge to edge — in `FIELD_22` it is literally
**two triangles** for 10,368 cells, on a map that has 16,384 — at −3.2 or
thereabouts. It faces up, so it is a floor in every respect; it just has
metres of rock above it. And being the lowest level, it is the one the map
starts from: `field_30` dropped to 84 cells walked out of 10,219.

What separates the backdrop from a real floor is a count, not a threshold.
There are **163,878** two-level cells, and in only **758** of them is the lower
one not the map's minimum height. So the gallery above the hall exists — and
it is 0.16% of the world; all the rest of the overlap is this backdrop.

`Columns.bury()` removes it from the floors where there is ground above.
Recognising it takes three things together, because in a dungeon the minimum
height **is** the floor and removing it would empty the map: it is **flat**
(all within one slice), it is **extensive** (at least a third of the cells
that have a floor), and it has **ground above** (in at least a quarter of the
cells it covers). The third is what separates it from the floor of `d_1_2`,
which also covers 69% of its map but has nothing above it.

### Water, which falls out of this

The cells where the backdrop is the **only** level are not ground: they are
the sea, the moat, the gorge between two plateaus. `Columns.water()` gives
them, and there are **40,964** of them across the whole disc.

And here the disc confirms itself, by a route that has nothing to do with it:
the logic grid assigns those cells a region identifier, and it is **119** — a
single value across the whole disc, not one per group of maps as had been
hypothesised.

```
88.4% of water cells carry tag 119
85.1% of cells tagged 119 are water      (the tag is one cell wider)
```

Map by map, where the tag is present it carries 98–100% of them. So **water
is known without opening the collision file**, which is what the renderer
needs in order to know where to draw it.

Not to be confused with the **void** — the cells with no collision at all,
55,477 — which is something else and which the tag does not declare: those
are the difference between the rectangular region and the real map.

## Passages, used rather than counted

That a departure cell declares a map, a gate and a direction, and that the
destination contains the cell that declares that gate as its own, was already
established — see [`format_mapdat.md`](format_mapdat.md), 508 departures out
of 517.

```
Warp        D_1_2;-gfrom_d_1;-right      D_1_1_1, cell (55,11)
Exit        -gfrom_d_1                   D_1_2,   cell (12,17)
```

What changes is that the number stops being a statistic about the graph and
becomes the way you change map. Mind the **two forms** of the gate, because
the second is the bulk of the internal passages:

- **by name** (`from_d_1`, `dungeon1`, `tf11_2`) — the arrival is an `Exit`
  cell with the same `-g`;
- **by number** (`-g11;-o101;`) — the arrival is the cell that carries that
  pair as its *own* identity. These are the staircases, and the two cells name
  each other: `A` declares that it leads to `B`'s identity, and `B` to `A`'s.

Reading only the first form resolves **46%** instead of 98%. The symptom is
the same one that had already given the graph away once: a number far too low
for a world you can cross.

Not to be confused: `arrivals` — every cell that declares a `-g` — contains
hundreds of observers and gimmicks, and is not a place to start from. A map's
entry point is its **`Exit`** class cells, which are the places where the game
itself makes someone appear. Starting from any first `-g` made the game begin
**on top of a wall**, with two reachable cells in all.

## The inhabitants

The cells whose class is the bare identifier (`a1_010`) are the NPC spots:
264 cells, 236 identifiers. The event scripts named 37 of them.

The others are named by **their own** script. The 243 files
`npcevent_n<NN><archetype><id>` are one per inhabitant and declare the model
(`n05` → `c_npc_05`) and the archetype in the file name, and the dialogue in
the body; 151 of them also name themselves in full inside
(`setnpccamerac("OldMana1_300")`), which is where the exact spelling of the
name comes from — `Blacksmith` or `BlackSmith` cannot be guessed.

Putting the two halves back together populates a map by itself: **225
identifiers out of 236 (95%)** with name, face and line. And the name is the
one the scripts would use, so an event that later names that NPC finds
**this** one, already in place, instead of materialising another one with no
position.

Six more archetypes gained their declared model:
`WiseMan1` → `c_npc_01`, `WiseMan2`…`WiseMan6` → `c_npc_20`…`c_npc_24`.

## Map objects are actors, not pieces of the map

The logic grid declares **1,518 cells in 112 classes** besides the passages
and the inhabitants (`Grid.objects`):

```
Exit             397    observer  163    destructionWall  46    WarpDoor  29
Warp             240    Observer  149    up               30    PitFall   21
SwitchObserver    80    EnemyObserver 65    BlackHole       7    Barricade  7
```

The question that matters to the walker is where they live: in the `.pac`
that is drawn, in the `.DPK` that stops you, or in neither. Measured cell by
cell, with the height of the drawn geometry and with the collision column:

| class | geometry above the floor | stops the body |
|---|---:|---:|
| `destructionWall` (45) | 0% | 0% |
| `BlackHole` (7) | 0% | 0% |
| `WarpDoor` (29) | 3% | 0% |
| `PitFall` (21) | 19% | 14% |
| `observer` / `Observer` / `*Observer` (457) | 65–70% | 65–70% |

**The breakable wall exists in neither file.** Its cell is smooth floor: it is
neither drawn nor does it stop you. The same goes for the black hole and the
door. The engine instantiates them from these cells as actors — the taxonomy
is the `ActorType` enum extracted from the Lua, which has precisely
`AT_DESTRUCTION_WALL`, `AT_DOOR`, `AT_WOOD_DOOR`, `AT_GIMM_GROUND_SWITCH`,
`AT_PUSH_OBJECT` among its 33 members.

Two consequences, and both must be kept:

- **the measurement walks through breakable walls.** 45 walls and 7
  barricades are invisible to the walker, so `walkabout` is an upper bound. It
  is a tight bound — 52 cells — but it has to be said, because I tried the
  opposite temptation (opening them and seeing how much world is gained) and
  it gives **zero extra cells across all 78 maps**: they were already open.
- **observers are not floor triggers.** Two out of three sit inside the
  solid, and indeed only 31–41% of their cells are walkable. They are position
  markers for the code, not pressure plates, and their `-g<number>` is an
  identifier that lives in the scripts, not in the map.

*Corollary: when a declared object is not found in any of the files that
describe the world, it is not a reading defect — it is the declaration that
that world is built at runtime.*

## Who lives in a cell: the field nobody read — `mapdat.actor()`

The cell record has six numeric fields before the two strings, and five had
been marked `?` for five sessions. The fifth, at **+0x10**, is the **actor**:
0 where there is nobody, and elsewhere an identifier *global to the game*, not
an index local to the map.

What says it is global is its constancy: `4100` is the observers in all 170
grids, and not by our convention but because the value is **constant per cell
class in 175 cases out of 195** (89.7%). The twenty exceptions are not noise:
they are the cells whose "class" is really the name of a destination map
(`D_7_1_2`, `Field_50`), which are not objects.

The partition of the numbering is declared by **three files that do not know
each other**:

| range | who | how we know |
|---|---|---:|
| 4000–4999 | map objects | constant per class, 175/195 |
| 5002–5082 | enemies | the `EnemyView` album, **45 of 46** |
| 5047+`NN` | NPCs, with `c_npc_NN` | 226 cells of 240, **94.2%** |

The densest 4xxx values can be read directly, because each one appears *only*
with its own classes: **4100** the observers and the `Warp`s (706 cells),
**4101** the solid things — `Exit`, `destructionWall`, `WarpDoor`, `PitFall`,
`BlackHole`, `WoodDoor` (503) — and **4115** the event triggers (168).

The NPC rule deserves a line of its own because it is **one more oracle on a
conclusion already reached**: that archetype `n05` was `c_npc_05` had been
inferred in session 4 from the names of the 237 `npcevent_n<NN>...` scripts,
an entirely different source. Here twenty consecutive values repeat it on
their own — 5049→`c_npc_02`, 5050→`c_npc_03`, … 5072→`c_npc_25` — and the few
exceptions **all** fall on the high models (`c_npc_19`…`c_npc_26`), which are
exactly the ones that inference resolved worst. The disagreement points at the
weak spot of our directory, not of the disc.

> **Session 12: the weak spot was `NP_NPC_19` ↔ `NP_NPC_26`, swapped.**
> `all.lua.eu` declares it, and the sentence above was right about where to
> look. See [`objects.md`](objects.md).

### Session 12: `4000 + NN` is the model — `Grid.props`, `nodes.props()`

The 4xxx band is not an opaque numbering: **the identifier is 4000 plus the
number of the model `m_obj_NN`**, that is the piece inside
`map/map_model/map_object.ps3.dsb` that the gimmick's script loads. 51 cells
out of 51 confirm it, across three families of scripts that do not know each
other — the 34 `Signboard`s (4041 / `m_obj_41`), the 12 `Stonemark`s (4067 /
`m_obj_67`), the three `Well`s (4063 / `m_obj_63`) — with zero disagreeing.

And the 3xxx band is `3000 + NN` → `d_hmw_NN`, the "Dungeon配置物" of the
authors' comment: the 28 numbers the cells use are exactly the 28 that
`d_haichi.ps3.dsb` carries.

So **7,695 object cells out of 11,924 (64.5%) have a model and are drawn**,
and the rest are not a gap: 3,843 of the 4,229 are in `4100`…`4105`, which is
the block of the numbering where models do not exist — that is, precisely the
markers the previous paragraph measured as absent from both the geometry and
the collision.

Still unattributed are the 8,053 values of the 1xxx band, which is the
overworld's equivalent of the 3xxx and does not close the same way because
there the model families are two (`f_hmw` and `f_ntr`) instead of one.

## The enemies are on the disc, cell by cell — `Grid.enemies`

The TODO took it as settled that the disc only said *where the species live*
— the album has a `LivingId` field — and that putting them on the map was the
code's job: "all that is left to the code is how many it puts in each room
and by what rule". That is not so. The grid places **10,196 enemies**, one per
cell, with the species in the +0x10 field.

And every enemy cell carries a **placement set**, `-sA` … `-sH`, a string
never seen before in any of the project's documents. The letters are two
triples and not a sequence — `A,B,C` and `F,G,H`, with `D` and `E` that do not
exist:

```
A 1807   B 1824   C 1804        F 1456   G 1654   H 1557        Z 94
```

**A, B, C are three alternative layouts of the same population.** Three
measurements that fail in different ways say so:

- the three letters carry **the same species in 58 maps out of 59** (98.3%);
- they are equally numerous across the whole disc (1807 / 1824 / 1804, a 1%
  spread), and in the Grass Temple they are so species by species: 13 Soldier
  Bones, 10 Scorpion, 15 Bat, 22 Red Slime, three times identical;
- their cells cover the **same area**: the box of one letter is 88% of that of
  all three, above 80% in 51 maps out of 59, and below 40% in none. So they
  are not squads guarding different zones.

> **One measurement too many, removed in session 10.** This also said "their
> cells never overlap", and it looked like the strongest proof of the three.
> It proves nothing: `mapdat.cells` walks `for i in range(w*h)`, that is
> **one cell, one record**, and each record carries a single actor and a
> single letter. Two letters in the same cell cannot exist *in the format*. It
> was a tautology dressed up as a measurement. The other two hold, and the
> reading does not change — but the count of evidence does.

**F, G, H are the same three for FROM Mode**, the difficulty unlocked by
finishing the game — and the letter says so, `F` stands for FROM. Here the
parallel breaks, and it is right that it should: in `FIELD_16` there are
36/47/45 cells against 19/19/19 and seven species against four, while in the
Grass Temple they are fewer but harder (Clay Golem and Ropus in place of Red
Slime and Bat).

### The confirmation came from outside

This reading was tested against a [GameFAQs
walkthrough](walkthrough/) — a source written for playing, not for reading
bytes, and which therefore gets things wrong in a way all its own. Four
matches, none sought:

- on the alternative sets: *"If the enemy positions are annoying, you can
  leave the room and come back and see if they respawn in a more favorable
  location."* That is `A`/`B`/`C` described from the other side of the screen.
- on FROM Mode: *"tough enemies appear all over the world map in hordes"*, and
  *"Enemy information does not apply to From mode, where all kinds of crazy
  enemies spawn all over the place — even enemies that are normally restricted
  to dungeons."* Which is exactly the profile of `F`/`G`/`H`: more cells in the
  overworld, and dungeon species where they should not be.
- on two enemies in particular: *"Crystal Slimes and Blue Dragons spawn
  rarely... It may be that they can actually spawn anywhere."* In our album
  **5075 Crystal Slime** and **5076 Blue Dragon** are the **only two of the 46
  with `LivingId = -1`**, that is with no declared habitat. The field that
  sets them apart in the data is the same one that sets them apart in the
  game.
- on the bosses, one by one: Eelagon/Grass, Queen Bee/Forest, Giga
  Golem/Desert, Kraken/Aqua, Dragon/Flame, Dark Knight/Wind, Fuelle and Onyx in
  the tower. Our album gives `DUNGEON_GRASS`, `DUNGEON_FOREST`,
  `DUNGEON_SANDS`, `DUNGEON_WATER`, `DUNGEON_FIRE`, `DUNGEON_EARO`,
  `DUNGEON_MAGIC` — **eight out of eight**, and with them the last doubt about
  `EARO` falls: it is *aero*, the wind.

And the way the bosses stand out in the data, without knowing they are
bosses: they have **2 cells on 1 map and no `-s`**, against the hundreds of
cells on dozens of maps of the common enemies. A boss needs no alternative
placements because it stays in a single room.

And the most specific sentence in that source — *"even enemies that are
normally restricted to dungeons"* — can be measured, because the album gives
each species its habitat and the grid says which map it is on:

```
A,B,C in the overworld:  2,195 enemies,    12 of dungeon species =  0.5%   3 species
F,G,H in the overworld:  3,902 enemies, 1,356 of dungeon species = 34.8%  17 species
```

Seventy times as many. With a gap like that nothing else is needed to say
what the two triples are, and it is the check that `walk.py` holds in place.

### And they add, they do not replace — measured by contradiction

It was the last thing the disc seemed not to say, and it was given as an
arithmetic inference. It can be measured, by negating the other hypothesis:

```
maps declaring A,B,C and F,G,H     50
maps declaring only A,B,C           9      the most populous is d_5_1_2, 45 enemies
maps declaring only F,G,H           0
```

If `F,G,H` **replaced** `A,B,C`, those nine maps would be left without a
single enemy in precisely the difficulty the walkthrough describes as *"tough
enemies appear all over the world map in hordes"*. Among them is a dungeon
floor with 45 enemies, which would become an empty stroll.

The opposite direction says it too: `|F| < |A|` in 29 maps out of 59, and in
the Grass Temple you would go from 60 enemies to 13. Replacing would make FROM
Mode *emptier*, which is the opposite of what it is.

So **they add**, and it is no longer an inference.

### Putting them in the world — `Walk.populate_enemies()`, `view.py play --spawn`

The renderer did not need a new line: an entity with model `c_enm_01` looks
for the node `c_enm_01_01`, which is exactly what the album declares in
`NodeStrings`. The only translation is to strip the pose from that name — the
album names a **frame**, the world needs the root — and that is the
confirmation, from a third file, of session 4's "the children of a node are
whole poses". The nine bosses have a file each and only need qualifying with
their folder.

```
python tools/view.py play d_1_1_1 --cell 39,18             two Scorpions, one Soldier Bones
python tools/view.py play d_1_1_1 --cell 39,18 --spawn C   the same, in other places
python tools/view.py play field_16 --spawn F               the overworld in FROM Mode
python tools/view.py play <map> --spawn -                  no enemies
```

The second command is the visual proof of the three placements: same room,
same player, same three species, completely different positions.

The entity's name is built from the cell (`@enemy_39_18`), because the data
declares the **species** and not the individual: no script ever names an
enemy, and giving it a fake name resembling the real ones would invite
looking for it in the scripts.

And a validation that came for free: **96% of the enemies have floor under
them**, and what says so is the `.DPK`, which is a different file and knows
nothing of this grid. The 4% that do not are set down at height zero instead
of vanishing, and why remains unknown — the obvious hypothesis, "they are the
flyers", could be measured and is **false** (see below).

## How they animate, and the twelve enemies written in Lua

The game implements its enemies in C++, but the disc carries **twelve written
out in full**: they are the actors of the Block Defence minigame, which reuses
the real game's models — and reuses them by number, not by copy. `MGBee`
loads `EN_ENEMY_06_04_a`, which is exactly the `NodeStrings` the album gives
`Killer Bee`.

The link is made on the model number and checked on the **names**, which
neither file takes from the other: `MGSkelton` lands on *Soldier Bones*,
`MGWood` on *Evil Tree*, `MGHagureSlime` on *Crystal Slime*, `MGGoblinRed` on
*Goble*. **Twelve out of twelve.**

From there three things can be read that would otherwise have had to be
invented:

- **the frame period**, `local StepWait`, which is `0.3` in all twelve. Ours
  was 0.25 and came from no data: it fell out of an `int(walk * 4) % 2`
  written to give two steps a second;
- **the poses of the cycle, which are not the same for everyone.**
  `02_a`/`02_b` is the common case but not the rule: the rabbit alternates
  `01` and `03`, the ghost `01` and `06`, the bee `04_a` and `04_b`, the
  shadow rests on `06`. It is a defect of ours that this file uncovered —
  **12 `c_enm` models out of 37** have no `02_a` at all, four walk with `04`
  and eight have no pair, so a third of the enemies stood still because we
  were looking for a pose that does not exist;
- **who flies**: `Type` is `0:陸` or `1:空`, and the flyers are Ghost, Killer
  Bee and Shadow.

And a rule that holds over **all 22** of the minigame's actors, without
exception: *if the model has two paired poses `_a`/`_b`, the engine runs the
cycle; otherwise the actor alternates them by hand with `SetNode`.* Which is
the cross-check, from a file written for a minigame, of the "`_a` and `_b` are
the two steps" inferred in session 4 from the geometry alone.

The two sources complement each other well: where the minigame is silent, the
model itself declares the cycle — and for *Cloudon*, which the minigame does
not have, it says `04_a`/`04_b`, the same shape as the bee.

What **cannot** be read is how they move around the world: in the minigame
they walk towards the tower with a native `BlockDefenceMove()`, which is
precisely that minigame's rule. Patrolling remains undeclared, and is left so
rather than invented.

### The flying hypothesis, measured and fallen

Having `Type` for twelve species makes it possible to test the natural
explanation of the cells without floor. It does not hold:

```
ground:   1,499 cells,  60 without floor = 4.0%
flying:     177 cells,   4 without floor = 2.3%
```

If anything the direction is the opposite, and the two numbers are too close
to say anything. Species by species it is clearer still: *Killer Bee*, which
flies, is on the floor in **100%** of cases, while the ones that miss it most
are *Clay Golem* (17%) and *Black Knight* (10%), which walk.

### The right place to split the question is the overworld

Looked for in the species, the cause was not there. It is in the **place**:

```
in the overworld:   0 of 6,097 enemies without floor =  0.0%
in the dungeons:  546 of 4,099                       = 13.3%
```

Zero out of six thousand. In the overworld the disc puts every single enemy on
a walkable cell, and that is not luck: it is the proof that the placement
*knows* where the ground is. The phenomenon belongs entirely and only to the
dungeons — and map objects do the same, standing without floor in 32% of cases
in the dungeons and 0.2% in the overworld.

**And it is not a one-cell offset between the grid and the collision**, which
was the next hypothesis and the most worrying one, because it would have been
our fault. The signal that suggested it is strong: the floor is **never** to
the right or below, and when the neighbour with floor is a single one it is
up and to the left 44 times out of 44. But shifting *all* the enemies by one
cell repairs nothing:

```
where the disc puts them    86.7% on walkable cells
shifted by (-1,-1)          87.6%          the best of the 24 shifts
shifted by (+1,+1)          69.5%
```

Nine tenths of a point is noise; a real offset would bring it to 99%. And in
the overworld there is no room for improvement, because it is already at 100%.

What remains is a strict rule: **nobody overflows by more than one cell**. All
546 cells without floor have one to three neighbours that do — never zero,
never more than three — and in 497 cases out of 546 those neighbours are all
at the same height. The placement is laid out on the room's rectangle and
spills one cell into the wall; in the overworld there is no wall to spill
into.

Hence the practical consequence, which used to be an `else 0.0`: an enemy
without floor is set down at the height of the floor **next to it**
(`Columns.ground_near`), not at zero.

### Where you are — `mapdat.locations()`, `Atlas.where()`

`MapParameter.lua.eu` had never been opened in eight sessions, and it was
reached for an unrelated reason: the TODO said to look there for patrolling
before inventing it. Patrolling is not there — nor anywhere else, because the
Lua API has `PlayEnemy`, `PauseEnemy` and `visibleEnemy`, that is freezing and
showing, never moving. But the file declares **211 maps** with the place's
name in English and the music track:

```lua
Identifier=map_manager.MS_FIELD_1, Location="Mt. Sabre",
Bgm=soundList.SoundID.BGM_field05, Volume=1.0
```

The identifier attaches to the file name without tricks —
`MS_DUNGEON_1_1_1` is `d_1_1_1` — and covers **168 of our 170 grids**; the two
left over are `field_99` and `field_test`, that is test maps. There are 55
distinct locations over 168 maps, and that is exactly what makes the name
information: crossing `field_6` and `field_7` means staying in "Klovis".

A name that makes you laugh and confirms the game is full of jokes: `field_3`
is **"Nialliv Valley"**, that is *Villain* backwards.

And a free confirmation of something that cost us three sessions: `d_1_1_1`
is called **"Grass Temple"** and `d_6_1_3` **"Wind Temple"**. That
`DUNGEON_EARO` was *aero*, the wind, had been inferred from `Item.lua.eu`,
confirmed by the walkthrough via Dark Knight, and is now written in English in
a fourth file.

### `LivingId` is the family, not the home

Having the temple's name and the real placement together makes it possible to
test a reading the documents took for granted — "which enemy belongs to which
dungeon is known". The count:

```
enemies placed in the temples: 1,988
whose LivingId names the temple they stand in: 936 = 47.1%
```

With seven habitats chance would give 14%, so the correlation is strong and
real; but 47% is not a rule, and the Flame Temple is full of `DUNGEON_WATER`.
`LivingId` classifies the enemy, it does not place it — and as long as the
placement could not be read, it was the best substitute available.

**The Dark Tower has no habitat of its own: it goes through all of them**, and
in an order that is not random. The prevailing habitat floor by floor is

```
d_7_1_1 GRASS   d_7_1_2 GRASS   d_7_1_3 SANDS
d_7_1_4 WATER   d_7_1_5 WATER   d_7_1_6 EARO
```

that is 1, 1, 3, 4, 4, 6 in the order in which the game has you visit the
temples: a **non-decreasing** sequence. The final tower retraces the journey.

### Two values the album does not declare

Of the 37 species placed, **35 are drawn**. The two that are not are the two
identifiers the album does not list, and they differ from each other:

- **5024**, 168 cells, with sets `A`…`H` like any enemy — but the album skips
  exactly that number (…5023, 5025…). And its cells stand in **continuous
  rows**, `(51,65) (52,65) (53,65)…` with the letters cycling, which is not how
  the others stand;
- **5080**, 94 cells, the only one with `-sZ`, and its class is a **number**
  (`0`, `1`, `4`). The positions fall on a regular grid.

Neither is a misread enemy: they are two different things that share the
range, and need to be looked at separately.

### 5024 is the falling boulder

The album does not declare it but **its own numbering predicts it**. In the
stretch 5018–5026 the offset between identifier and model number is constant:

```
5018 → c_enm_02   5021 → c_enm_05   5023 → c_enm_07   5025 → c_enm_09
5019 → c_enm_03   5022 → c_enm_06   [5024 missing]    5026 → c_enm_10
5020 → c_enm_04
```

Eight declared entries, offset 5016 in all eight, and **5024 is the only gap
in the stretch**. The model that follows from it, `c_enm_08`, really exists
among the 39 `c_enm` of `c_obj_all` — and it is a lumpy ochre mass with no
poses: a rock.

The placement says the rest, and it is three things that agree:

- it is on **six maps only, all of them high ground** — Mt. Sabre, Sukaboko
  Highlands, Klovis (two screens), Vatara Highlands (two). No dungeon, no
  plain;
- it stands **in rows** and up high, 5 to 28 cells above zero;
- and the ground in front of it **falls away**, in one direction only:

```
towards the bottom of the screen:  falls 50%   flat 48%   rises  2%
towards the top:                   rises 22%   flat 76%   falls  2%
left and right:                    falls 12%   flat ~82%
```

Behind it the ground rises, in front it drops. And the walkthrough, which
knows nothing of this, describes Sukaboko Highlands like this: *"You will come
to a screen with Centauses and **falling rocks**."*

So 5024 is the boulder that rolls down the cliff: an enemy actor in every
respect — it has the six placement sets, so it respawns like the others —
which the album does not list because **it is not a monster to be
registered**.

### 5080 is Togetoge, and its class is the direction it moves in

The previous reading said "it is not a creature, it is a figure, and class `4`
draws the four corners of a screen". The geometry was right and the
conclusion was not: 5080 **is** an actor, and to know it you only had to open
the file that writes it. It is in `all.lua.eu`, folder `../lua/Object/`, and
it is called `69Togetoge.lua` — トゲトゲ, *"spikes"*. Its header comment
declares the table we were looking for:

```
0 : 縦移動                  vertical
1 : 横移動                  horizontal
2 : 縦移動（突撃タイプ）      vertical, charging
3 : 横移動（突撃タイプ）      horizontal, charging
```

and `Togetoge4Update` calls `TogetogeDashUpdate(Object,2)`, that is 縦横: it
stays still until the player lines up with it, then charges — along **both**
axes. The classes the grids use are `0`, `1` and `4`.

**The geometry becomes the cross-check**, and it has the right shape to be
one, because it is a rule the placement cannot break without breaking the
game: two spikes moving up and down cannot share a column, two moving
sideways cannot share a row — they would collide at the first step. Those
that stay still in the corners necessarily share them.

```
class 0 (vertical)      all columns distinct         4 groups out of  4
class 1 (horizontal)    all rows distinct            5 groups out of  5
class 4 (charging)      2 columns and 2 rows        11 groups out of 11
```

Eleven groups of four, always at (1,1) (14,1) (1,10) (14,10) inside the 16×12
screen: the charging spikes guard the corners of the room and cross it when
you line up with them. That is why the boss maps have **zero** of them and why
inside each rectangle there is an observer and 10 to 16 enemies: it is a trap
room, not a figure.

The model is there, and it closes the count:
`Object:AddNode(package_manager.EN_ENEMY_39_01)` is `c_enm_39_01`, that is
**the last** of the 39 `c_enm`. The enemy rule would have given `c_enm_64` and
the NPC one `c_npc_33`, and neither exists: it was the rule that did not apply
there, not the model that was missing.

And the album is right not to list it. `69Togetoge` does not call
`setBookRegistInfo`, that is **it does not register in the bestiary** — and
neither does `08RockFall.lua`, which loads `EN_ENEMY_08` and is 5024's
boulder. The album's 46 are the 46 that get a bestiary entry; a boulder and a
trap live in the same numbering because they are `AT_ENEMY` in every respect,
but they are not monsters to be registered. See `entity.LUA_ACTORS`.

*The file name also gives the cheapest confirmation this project has had:
session 10 had inferred that 5024 was the boulder falling from the gap in a
constant-offset stretch and from the ground falling away in front of it. The
file is called `08Rock**Fall**`.*

The walkthrough, which knows nothing of bytes, validates both the rooms and
the rule of engagement: the *"spike puzzle"*s it lists fall in Aqua Temple,
Wind Temple, Dark Tower and the cave west of the tower — and they are the only
maps with `5080` of class 0 or 1. And where it explains *"if you don't move at
all upon entering a room, you are not technically "in" it yet, and thus traps
won't activate"*, the code says the same thing in one line:
`if( not Object:IsPlayerArea() ) then return; end`.

## Walking sets off events — `Grid.triggers`

64 cells name not an object but an **event**, and the TODO had them as
unresolved: "only 3 names out of 25 find their file; the other 22 have no
script called that".

It was the search that was wrong, not the data. They are not files, they are
**functions** — and they live in one file per element, in a folder named after
what it contains: `gimmick_grass4` lives inside
`Event/gimmickevent/gimmick_grass.lua.eu` together with the other six
`gimmick_grass`. Looked up as global functions, **25 out of 25** resolve, and
the check runs by itself in `walk.py`.

The content confirms they are position triggers: it opens with a guard
`if Event:GetEventFlag(167)==1 then return end`, that is once only, then
`LockPlayer`, the fairy who appears and explains the switch, `UnlockPlayer`.
They can already be run by the Phase 4 host without adding a method.

Of the 25, five are in the **same** file and are the four directions plus the
centre: `mainevent_herodream` `n`, `s`, `e`, `w` and `2`.

## What the objects do: the file that parametrises them

`GameParamData/gimmickParam.lua.eu` — 174 lines, in the clear, with the
authors' comments in Japanese — declares the behaviour of fifteen gimmicks,
and the names match the cell classes: `WarpDoor` and `BlackHole` literally,
`Hole` for the `PitFall`, `stone_monument` for the `Stonemark`s.

```
ShotArrowWall  offset, shot_size 0.4, reload_time 1.0, speed 18.0
WallSwitch     offset_x 1.0, offset_y 1.4, offset_z 1.0
TargetSwitch   collision_size 0.6, clamp_value 0.4   -- when the arrow sticks in
WarpDoor       castle_open_time 1.5, house_open_time 0.5, dark_open_time 1.5
Hole           detection_range 0.5, fall_time 1.0, gravity 18.0, pop_count 1
QuickSand      detection_range 1.3, speed 4.5
BlackHole      damage 4, vacuum_range 6.4, first_wait_time 1.0
poison         damage 8, and six colour numbers
stone_monument "Magic might help...", "Parallax revealed a hint!"
```

The walkthrough validates these too, and one **word for word**: the
`stone_monument` slate is the one Parallax is cast on — *"it can only be used
where there is a surface such as the big slate... Using the spell will reveal
the writing on the slate"* — and our twelve `Stonemark00`…`Stonemark11` stand
one or two per temple, in the same rooms where the guide says to cast it. So
too `ShotArrowWall` (*"two contraptions on the north wall... traps that will
shoot arrows at you"*), `WallSwitch` (*"hitting the wall switch with your
Boomerang"*), `QuickSand`, and the `destructionWall` (*"the cracked wall to
the west... can be bombed"*).

What this file does **not** contain is the logic, which stays in the code. But
we know its shape, because the disc carries 34 specimens of it written in Lua:
the actors of the Block Defence minigame (`data/MiniGame/*.lua.eu`) have all
four callbacks of the engine's actor contract —

```lua
function MGBombRockInitialize(Object)   Object:SetType(actor_manager.AT_DESTRUCTION_WALL) ...
function MGBombRockUpdate(Object)
function MGBombRockCheckMove(Object, Type)       -> MR_BLOCK | MR_NONE
function MGBombRockCheckCollision(Object, Type)  -> if AT_BOMB: CreateEffect, ResetMapGridData, Destroy
```

— that is the wall the bomb opens, written out in full, only in the minigame
instead of the world. `MR_BLOCK` and `MR_NONE` appear nowhere else on the
disc: the real map objects are implemented in C++, and these are the cast that
says with which functions.

## What they really declare: the room — `Grid.rooms`, `room_of()`

It remained to understand *what those cells say*. The shape of the string
splits them into two families, and the split is clean:

| | cells | form |
|---|---:|---|
| `SwitchObserver`, `EnemyObserver` | 80, 65 | `-gN;` alone |
| `destructionWall`, `WarpDoor` | 46, 29 | `-gN;-oN;` with **the two numbers equal** |
| `PitFall`, `BlackHole` | 21, 7 | `-gN;-oM;` with **the two numbers different** |

Where the two numbers are equal, the pair turns up again on a cell of
**another map**: `WarpDoor` 29 out of 29, `destructionWall` 43 out of 46.
Those are passages, and that is why `walkabout` already walked through them.

### The TODO's hypothesis was wrong

"The `PitFall` has a `-g`/`-o` pair like the passages, so falling is
probably *arriving* somewhere." Tested, it does not hold: a `PitFall`'s pair
turns up elsewhere **2 times out of 21**, and a `BlackHole`'s 3 out of 7. Not
even when searching for the `-g` alone or the `-o` alone, which do recur but
on twenty cells at a time — that is, they do not resolve, they collect.

### The number is `(floor)(room)`, and two other files say so

The dark tower's seven black holes are one per floor and carry `-g12`,
`-g212`, `-g37`, `-g410`, `-g514`, `-g63`, `-g712`: first digit 1, 2, 3, 4, 5,
6, 7 in floor order. They seemed to name the seven temples — the tower opening
onto the six dungeons would have been a nice reading, and it is false: none
of those pairs exists in the dungeon the digit names, 0 out of 7. The digit is
**the floor the cell is on**.

Which can be measured, against two external oracles:

```
2,484 numeric gates of 2,490:   the first digit is the floor given by
                                the **file name** (99.8%)
  404 rooms of 413:             the rooms derived this way are the ones
                                the `dungeonMapNN_MM` descriptors draw
                                as `room_on_NN` (21 floors of 21)
```

Fourteen floors out of twenty-one match **exactly**. And the two oracles do
not know each other: one is a string in a file name, the other is an
interface screen written to draw a minimap.

So the `-g` is not an address: it is `(floor)(room)`, local to the map, and
the object cells declare **which room they belong to** — not what they do. The
behaviour really is in the code; but the rooms are now a real structure, and
it is exactly the one the dungeon map colours one cell at a time
(`view.py play <map> --map`, or `M` while walking).

### Where a room starts and ends, the disc does not say

Knowing *which* room you are in would make the map a real minimap, and it
cannot be done: the marked cells are sparse placeholders, not regions. Three
roads tried, three results:

- **the room is a screen**: the box of the marked cells fits in 16×12 in
  95.4% of cases, but only 305 rooms out of 416 fall in an aligned block.
  Rooms are *about* one screen in size, and they are not the screen;
- **the cell's region tag is the room**: no. In `d_1_1_1` all 23 rooms carry
  the same tag `2001` — the tag is the **dungeon**;
- **the nearest marker**: the rooms' boxes do not overlap (1.3% of pairs),
  but they cover 12% of the map, and on the cells inside exactly one box the
  nearest marker gets it right **75.7%** of the time. By this project's
  standards that is noise with a preference, not a rule.

Put together, this says something coherent: the observers are the **entry
triggers** the engine uses to record which room you are in — which is why
they are sparse, and why two out of three sit inside the solid instead of on
the floor. The region is of no use to anyone except us.

## Talking

Pressing space looks at who is in the cell in front and starts their
`npcevent_*` on the Lua host, verbatim. The host is the same as ever; the only
new thing is `Host.begin()`, which restarts a conversation from scratch
without reloading the world — pages, waits and coroutines start clean,
otherwise the second line would arrive already finished.

The world is **the same object** for the host and for the walker: if the
registry belonged to one or the other, an event would move a different
character from the one on screen. While the event is talking, the camera is
its own (`SetCameraAtBody`); as soon as it ends, the game's framing comes
back, not that of the last line.

## The ceiling

This game's dungeons have ceilings: from above they are a slab, and nobody
walking inside can be seen. The fragment shader discards everything above a
height, and that height follows the player (`--roof`, by default 2.4 units
above the feet; `K` removes it, `--no-roof` turns it off).

It is not an effect: without it, `play` in a dungeon shows a floor seen from
below.

## The measurement

A frame with a character in the middle of a map is an anecdote.
`view.py walkabout` is the number: for each map it loads the collision, starts
from the entry point the data declares and looks at where you can get on foot.

```
167 maps walked in 58s
overall      167 maps, entrance walkable in 167
             cells reached on foot      242,818/363,009 = 67%   (water 40,964 apart)
             inhabitants reached            256/264     = 97%
             passages reached               369/512    , with a standable arrival 365
dungeons     127 maps    cells 68%   inhabitants  95%   passages 179/301
overworld     40 maps    cells 66%   inhabitants  99%   passages 186/211
```

A map is walked **from all its doors**, not from one. That is not a
convenience: `field_14` has six `Exit` cells, and the first opens onto a ledge
of 16 cells under a cliff while the other five open onto the 3,213 that are
the map. Taking only one measures the door instead of the map.

How to read them:

- **the entrance is walkable in 167 maps out of 167.** The point where the
  game makes the player appear is, in every map on the disc, a place where you
  can stand. That was not obvious: it depends on the composition of the
  screens, the scale, the origin of the grid and the reading of the surfaces,
  all together.
- **365 passages out of 369 lead to a cell where you can stand**, which is
  99%. The four left over are not a wrong arrival: they are passages whose
  destination map does not exist on the disc.
- **cells at 67% are not a 33% failure.** The denominator counts every cell
  you *could* stand on, house roofs and wall tops included, which indeed are
  not reached and must not be. Water, on the other hand, is removed and
  counted apart, because it is neither ground nor roof.
- **inhabitants at 97% are the real measure**, because an unreachable
  inhabitant is a piece of the game you do not see, whereas an unreachable
  cell is often a roof.

### Where this number comes from

It is worth keeping track of, because the road to it corrected a conclusion
already written down twice:

| | cells | inhabitants | passages | standable |
|---|---:|---:|---:|---:|
| render geometry, step 0.6 | 18% | 65% | 194 | |
| real collision (`.DPK`), step 0.6 | 25% | 78% | 202 | |
| real collision, step **one cell** | 63% | 96% | 303 | 281 |
| measured column, backdrop buried, all doors | **67%** | **97%** | **369** | **365** |

And the gap between dungeons and overworld — 26% against 13% of cells, 76%
against 51% of inhabitants — **has gone**: they are now 63% and 63%, and the
overworld does better than the dungeons on inhabitants (99% against 94%).

This refutes what was written here yesterday, namely that the overworld had
two distinct causes and that the first was missing geometry. There was one
cause, and it was the invented threshold. The 90.7% coverage of
`view.py layout` remains an open question, but it was **not** this.

## What is missing

- **The behaviour of map objects.** Where they are and what they are is now
  known (see above); what they *do* — the bomb that opens the wall, the switch,
  the fall into the trap — is game logic, and it comes later.
- **The enemies.** `c_enm_NN` exists and is drawn, but no cell declares them
  the way it declares the NPCs: the code creates them, on its
  `EnemyObserver`s.
- **Drawing the water.** Where it is is now known — tag 119, and the mask from
  the collision — but the surface is drawn by the engine and not by the
  `.pac`, so it is renderer work. It is the reason a frame of the overworld has
  large black areas.
- **The maps that remain hard to walk.** `d_60_2` (3%), `d_60_14` (8%),
  `d_80_1` (11%): few and contained, and now that the entrance is no longer
  suspect they are worth looking at one by one.
- **The sword and the shield**, which are separate nodes in the model.
