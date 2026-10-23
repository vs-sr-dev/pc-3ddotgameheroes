# Enemies, run by the disc's own scripts — `tools/actor.py`

*Session 11.* The companion of [`host.md`](host.md) for a second domain: there
the events, here the actors. The thesis is the same, and this time it is
harder to believe before seeing it — **the movement of 3D Dot Game Heroes'
enemies is written in Lua, on the disc, and it can be run**.

## What the TODO said for three sessions

> Patrolling is not declared in the clear anywhere, and it stays unimplemented
> rather than invented.

That was true of the places it had been looked for — `MapParameter`,
`GameParamData`, the Lua API, the twelve actors of the Block Defence minigame
— and false of the disc. The movement is in `all.lua.eu`, which **is not a
file**: it is the concatenation of **1,486 sources**, with the folder tree
left in the comments.

> *Corrected in session 12: they had been given as 869, which is the count of
> `../lua/` alone. Below it there are twenty-eight more trees — `Event/`,
> `MiniGame/`, `UserInterface/` — that is, almost all the disc's data files,
> in the same stream. Looking for a source's boundary only among the
> `../lua/` ones makes seven of them swallow the 185 that follow them; none of
> the seven is an enemy file, so the measurements below do not change, but the
> count does.*

```
-- Start ../lua/Object/06Bee.lua.eu
```

Under `../lua/Object/` there are 55 enemy files, 266 NPC files, 21 gimmick
files and 100 object files. Forty-six call `setBookRegistInfo`, that is, they
register themselves in the bestiary, and that is **exactly the number of
entries in the album**; 37 carry their behaviour in full, and the 9 that
remain are the eight bosses plus Guardian, which have only their
initialisation in Lua.

*Why it had not been seen: the search had been made in three places and not
in the fourth, which is the largest file on the disc — and until session 9
that file came back mangled, because it is one of the 21 with comments in
Shift-JIS.*

## What an enemy looks like

Two global functions, an explicit state machine, the phase in a field of the
actor and the timers in numbered slots:

```lua
function BeeUpdate(Object)
    if(Object:GetPhase()==0 and Object:IsTimeZero()) then
        Object:SetPhase(1);
        CommonRandomDirection(Object,WallDistance);
        if( Object:IsActorMoveArea( MoveArea ) ) then
            Object:SetDirectionToInit();
        end
    end
```

and `MoveArea` is a `local` of the file, with the authors' comment:

```lua
local MoveArea = 10.0;   -- 出現位置からの行動可能範囲
```

*the range of action from the spawn point*. **That is the patrol**: it wanders
at random, and when it leaves the range it heads back towards the point where
it was born. There was nothing to invent.

## What the module does

`Troupe` loads the VM once — 3.7 MB and 869 sources in a tenth of a second —
and gives every enemy placed by `walk.populate_enemies` its own `Actor`, which
is the object the Lua receives as `Object`. Every frame it calls its
`Update`.

```
53 methods implemented of 161 requested,  covering 4,225/5,335 calls = 79.2%
```

*(The count grew in session 12 with the correction of the source boundary,
and in session 13 with `AddAnimation` and `InitializeAnimation` — two methods
only, seven points, because they are the most requested in the corpus.)*

They are the ones for phase, time, movement and perception, written against
the grid and the columns the project already has: an enemy has no collision
of its own in the data, so it stops at walls by going through the same code
as the player. All the others **are counted instead of failing**, which is
`host.py`'s criterion and the way to measure how much is missing without
inventing.

### Three decisions worth getting right

**In Lua `0` is true.** Only `nil` and `false` are false, so answering zero to
an unimplemented predicate would mean every `if Object:IsSomething()` takes
the affirmative branch: an enemy that always believes it sees the player and
has a wall in front of it. That would be behaviour invented by us. What gives
the right answer is the naming convention of the **original code**, regular
across all 55 files: `Is…` is a predicate and answers "no", `Get…` answers
zero, and the rest is a command and returns an object that can be asked for
further methods — because the scripts chain,
`local club = Object:SetChildObject(…); club:setVisible(false)`.

**`GetPosition` must return a live reference.** The scripts assign into the
value it returns:

```lua
Object:GetPosition().y = Object:GetFloor()*1.6 + 4.0*1.6;
```

and that `1.6` is `entity.TILE`, the side of a cell — the world's scale
confirmed by yet another file.

**The closures must be memoised.** A single enemy asks for `GetPhase` a dozen
times a frame: creating a new one each time means handing the Lua tens of
thousands of temporary Python objects a second that nobody keeps alive, and
the symptom — actors that fall over after a hundred frames or so, never alone,
never at the same point — did not resemble the cause at all.

## The measurements

Five maps, five seconds of life each, in [`walk.py`](../tools/walk.py):

```
312 actors of 312 placed enemies find their own behaviour
  0 scripts crashed
  0 enemies that left walkable ground by moving
261 of 312 move by themselves
```

The 12% standing on a cell with no floor were there **from the start**: they
are the 546 that session 10 measured overhanging by one cell into the wall.
Whoever starts on the floor never leaves it.

And the 51 that do not move are not a defect: they are waiting for reasons of
their own, and among them are all the Togetoge, which the first line of their
`Update` freezes until the player enters the room —
`if( not Object:IsPlayerArea() ) then return; end`.

## The proof that closes the circle

Session 11 had read the class of the 5080 cells as the **axis of movement**,
and had inferred it from the file's comment plus the geometry of the
placement. Running the scripts, the same thing is measured from the other end:

```
Togetoge class 1 (horizontal)     displacement  X 2.3   Z 0.0
Togetoge class 0 (vertical)       displacement  X 0.0   Z 29.2
```

A static reading of the data and a dynamic reading of the code that confirm
each other, and neither knows of the other.

## And the inhabitants, which are the same thing

In the same folder there are **33 NPC files**, `N01WiseMan1` …
`N31Spelunker`, and the hook is again the node they load — with a wrinkle
worth noting, because it shows two hands on the same disc: models 02–08 write
`NP_NPC05_01`, model 01 and all those from 09 up write `NP_NPC_09_01`. The
number, though, is never wrong: **the number in the file name and that of the
node coincide 33 times out of 33**, which is the third independent
confirmation of the archetype→model table inferred in session 4 from the
names of the 237 `npcevent_` scripts.

> **Session 12.** The sentence holds, and it has to be read narrowly: what
> coincides is the number of the *file* with that of the *constant*
> `NP_NPC_NN`. From constant to **model** there is one more step, and the node
> table declares it — where two entries are swapped, `NP_NPC_19` ↔
> `NP_NPC_26`. See [`objects.md`](objects.md).

`OldManUpdate` is the villages' wandering, in full:

```lua
Object:SetRandomDirection();
Object:SetSpeed(1.6);      -- one cell a second
Object:SetDistance(6.4);   -- four cells, then start again
```

```
the castle courtyard: 33 inhabitants, 32 with their own script, 22 wander
0 errors   0 left the floor
```

**Ten files have no `Update` at all**, and it is not a gap: they are
`N10King`, the six wise men, `N28LegendHeroGhost`, `N29MedalKing`,
`N30LegendHero`. The disc declares stillness by an absence, and the category
is exactly the right one — a king on his throne and a wise man at the back of
a temple wait, they do not stroll. Not one of the 55 enemy files lacks it.

Still but not frozen, though: `KingInitialize` loads the two poses of the step
and alternates them every half second with `AddAnimation(0,0.5)`,
`AddAnimation(1,0.5)`. That is why `AddAnimation` is called even by those that
do not move.

**One thing nobody declares**, and it has to be said: the initial direction.
It is not in the scripts — none of the ten still ones calls `SetDirection` or
`setAngle` — and it is not in the grid, where the cells that name an NPC carry
not a single flag. The `facing = 1` we put them down with remains **a choice
of ours**.

But it is not a blind choice, and the difference matters: **the placement
implies it**. Those who do not move always stand higher up than the door one
comes in by —

```
still characters indoors: 11,  with the nearest door further down: 11
d_20_1  the King at y=11, the door at y=36, six courtiers lined up between
```

— so one walks towards them, and facing down the grid means facing whoever
arrives. It is the convention anyone who has played a game of this kind
expects (you enter the throne room from the south and the king faces south),
and here it is not borrowed from the genre: it is measured on the placement,
11 cases of 11. It remains an inference — the data says where they stand, not
where they look — but it is an inference with an oracle, which is not the same
thing as a habit.

The only exception on the disc is a wise man in the open overworld
(`field_8`), where "the nearest door" is not the entrance to a hall and the
question does not arise.

## What is missing

The 98 unimplemented methods are 27.3% of the calls, and they are almost all
outside movement: animation (`AddAnimation`, `InitializeAnimation`), colour
(`AddColor` — see below: they are **the fragments**, and without destruction
there is nothing to implement), sound (`PlaySE`), effects (`CreateEffect`,
`createWarpEffect`), combat (`IsHitGuardPlayer`, `GetPlayerHP`, `Throw`) and
registration in the bestiary. Combat in particular is a subsystem the project
does not have yet, not a hole in this one.

Movement is uncovered in only two places, and they are declared here because
they cannot be read: the flag of `Move(false)` — 17 calls, always `false`,
its meaning declared nowhere — and the curve of `Fly`, where the scripts pass
a gravity that here becomes a linear approach to the flying height.

## The pose cycle is declared — `AddAnimation`

It was "the most requested method that is missing": **916 calls in 192
modules**. It now runs, and together with `InitializeAnimation` it takes the
coverage from 71.8% to **79.2%** of the calls — two methods, seven points,
because they are the most requested of all.

`AddAnimation(i, wait)` adds **node `i`** to the cycle, shown for `wait`
seconds. That the first argument is an index in `AddNode` order is not a
choice of reading, it is the only one the corpus allows:

```
files where the highest AddAnimation index is < the number of AddNode   314/314
```

Zero exceptions. And the second argument is a wait, as the name the scripts
give it says — `AnimationWait`, `DashAnimationWait`, `patapataSpeed`
(パタパタ, the flapping of wings). It is `0.5` in 702 calls of 916.

**It is not in the `Initialize`**, and that is the trap to fall into: it is in
the `Update`, at the change of state. `06Bee` redoes its own `1, 2` every time
it goes from still to flying, so the cycle has to be carried back into the
entity after every frame. And since only 63 modules of 192 call
`InitializeAnimation`, the list would grow forever: what is kept is the
**period**, which is indistinguishable to the eye and does not grow.

### It confirms what was inferred, and corrects ten enemies

Of 25 enemies that declare a cycle, **15 say exactly `02_a`/`02_b`**, that is,
the rule inferred in session 4 from the geometry of the nodes alone. The other
ten do not, and they are the cases the project could not have guessed:

| model | rest | cycle | step |
|---|---|---|---|
| `c_enm_06` | `01` | `04_a`, `04_b` | 0.15 s |
| `c_enm_12`, `13` | `06` | `02_a`, `01`, `02_b`, `01` | 0.22 s |
| `c_enm_23`, `24` | `01` | `02`, `01` | 0.25 s |
| `c_enm_16` | `02_a` | `02_b`, `06` | 0.25 s |
| `c_enm_35` | `01` | `01`, `06` | 0.25 s |

The goblins walk in **four beats** — step, stand, opposite step, stand — which
cannot be read from the suffixes in any way. And `c_enm_23`/`24` are among the
eight models that session 8 had counted **with no `_a`/`_b` pair at all**:
they stood still because we were looking for the cycle in the names, and
instead it is written down.

The step also stops being a number of ours: it was `0.25` (or `0.3` for the
twelve of the minigame), and now every enemy has its own, from 0.12 to 0.25.

*The 12 that declare nothing keep the earlier fallback, which is the inferred
rule: where the disc is silent, we do not change our mind.*

## `AddColor` is the fragments, and the authors say so

The question had been in the TODO for two sessions, with the right hypothesis
and no proof. The proof is a comment, in three places in the corpus:

```lua
Object:SetAmount( 4 );                  -- 壊れた時の破片の量
Object:AddColor( 0.38, 0.26, 0.00 );    -- 破片の色
```

*The number of fragments when it breaks*, and *the colour of the fragments*.
They are in Shift-JIS inside a UTF-8 file, like the 21 notes that until
session 9 made almost everything `all.lua.eu` contained unreadable — and
indeed here they had stayed silent.

**The data bears the reading out without exception**: `AddColor` is **always
at most `SetAmount`**, 71 files of 71. No more colours are declared than
fragments. And `SetAmount` is **4 in 52 files of 78**: a thing that breaks
into four pieces.

This explains, instead of leaving it an oddity, session 12's measurement —
*"the 132 declared colours are already those of their own model's vertices,
to within half a degree of hue"*. Of course they are: **the fragments of a
thing have the colour of the thing.** That measurement did not say `AddColor`
is useless; it said its colours come from there.

And the argument by which session 12 had ruled out the "one per node"
hypothesis falls too: `12GoblinRed` declaring the same colour twice rules out
nothing, because in a palette of four fragments a repeated colour is simply
**a colour that weighs double**.

### The bosses do not break, and their colours are per part

The eight bosses do not call `SetAmount`, and that is why the TODO had set them
apart. `B01Snake` shows what they do instead:

```lua
Boss:AddColor     (0.62, 0.63, 0.43);   -- 頭      the head
Boss:AddBodyColor (0.62, 0.63, 0.43);   -- 体      the body
Boss:AddTailColor (0.62, 0.63, 0.43);   -- 尻尾    the tail
```

Three parallel methods for the three parts of a snake, three colours each. And
that these too are fragments is said by `B02BeeChild`, which uses the same
`Boss:AddColor` with the comment `-- 破片の色`: the boss breaks **by parts**,
and each part has its own palette.
