# TODO

*Read this first at the start of a session. The frame is in
[`STRATEGY.md`](STRATEGY.md), the executable in [`eboot.md`](eboot.md), the
disc survey in [`RECON.md`](RECON.md).*

---

# Next session

**Session 14 changed road and reached the logos.** The project is now a
static recompilation of the game's own executable on
[ps3kit](https://github.com/vs-sr-dev/ps3kit), which left PC-ROA for its own
repository the same day and is a submodule here. The recompiled game reaches
its first flip and draws its four logo screens at 60 frames (ATLUS, FROM
SOFTWARE, DAIKOKU and YEBIS), with FMOD's SPU mixer running as an lv2 SPU
thread group and a SPURS task waiting on its event flag. Then it checks for
its save data, finds none, and stays on a black screen with its main loop
running.

Where it stands:

- **Decryption**: [`tools/self.py`](../tools/self.py), ported from PC-ROA;
  [`format_self.md`](format_self.md).
- **Census**: [`eboot.md`](eboot.md). 20,672 functions, 237 imports all
  named, 638 switch tables all resolved, 26 SPU ELFs.
- **The kit, for this game**: SPU ELFs recompiled at their load address,
  lv2 SPU thread groups, SPURS task sets, tasks and event flags on a kernel
  of the runtime's own, `spu_printf`, the RSX's I/O map, reports and inline
  transfers, audio notifications, `/dev_flash`, `/dev_hdd1`. Checked on
  PC-ROA and pushed (`ps3kit` 9408baf).
- **This repository's own knowledge so far**: `tools/flash.py`, a declared
  stand-in for the system's MP3 decoder, which FMOD reads from
  `/dev_flash` and which the disc does not carry.

The commands are at the end of [`eboot.md`](eboot.md).

### 1. The black screen after the save-data check.

After `cellSaveDataListAutoLoad` for `BLES00875SYSTEM` and
`BLES00875GAME-DATA` (both answered "no data": the game's callback says so),
the game draws 8 draws a frame on black, opens no file, calls no stub, and
its main thread spends nearly all its time in the frame-pacing sleep of
`0x2A438`. Nothing waits on a lock (the kit now names any lightweight-mutex
wait over five seconds). Pressing Start or cross changes nothing.

Leads, cheapest first: the game's TTY (stdout) for its own messages; the
calls `0x473E8C` (`cellSysCacheMount`, now implemented, not reached yet),
`cellGameDataCheck` and `cellGameCreateGameData` (0x525340, 0x52CD08: the
HDD install the free-space check was about, 871 MB, which the disc's
`HDDInstallList.lua.eu` lists); the second SPURS instance at `0x5CF000`,
whose PPU thread waits on an event flag; and the state machine around
`0x2A438`, read off the recompiled game with `gdb_trace.py`.

### 2. Which copy of the scripts the game runs.

The EBOOT carries 1,488 Lua sources, 112 different from the disc's
`all.lua.eu` (see [`eboot.md`](eboot.md)). In 90 seconds of boot no
`.lua.eu` is opened. Find the loader (the `-- Start` / `-- End` markers, or
the Lua 5.1.3 `lua_load` it calls) and see where its chunks come from. The
answer decides how the scripts are modded.

### 3. SPURS queues, lock-free queues and the barrier.

They answer `CELL_OK` and do nothing (the kit's README says so). Edge zlib's
inflate queue (`0x69C000`) and Bullet (`0x955000`) need them. RPCS3 has no
implementation to read (it runs the firmware's library); the layouts are in
the SPU side of the protocol, which is the tasks' own code
(`edgezlib_inflate_task`, the two Bullet tasks), and RPCS3 notes that
`CellSpursLFQueue` is a `CellSyncLFQueue`. Read the task's side, then write
the PPU's, as the event flags were done in session 14.

### 4. FMOD: the real decoder and the 19 modules.

- `flashMP3.pic` is in the firmware update on the disc (`PS3UPDAT.PUP`,
  3.15), in an encrypted package. Reading it would replace the stand-in with
  the player's own file; until then MP3 decoding is absent, which this disc
  does not use (it has no MP3).
- FMOD's 2 codecs and 17 effects are relocatable SPU modules its mixer
  loads where it chooses. When it first does, the address can be read off
  the run (`PS3KIT_SPU_DMA=1`) and the modules recompiled for it.

### 5. A glitch in the game's own text.

The free-space message drew its number with the digits overlapping
("8 7 1 M|6 9s2 0e2ded"). The text is the game's (`Font.bin` and the font
textures), drawn by its code: a draw or a texture state the renderer gets
wrong. Look at it when a screen with text comes back.

### 6. Shader programs compiled at first sight.

Shared with PC-ROA, where it is item 2 of its TODO: the kit compiles a
program's GLSL when a draw first uses it, and a scene's first second can
spend 400 ms on it. PC-ROA's play check of session 14 measured it again:
171 of 182 seconds at 30 frames, every drop at a scene load. A program cache
on disk belongs in the kit.

### 7. The tools still speak Italian.

The documents are in English since session 14; the Python tools' docstrings,
comments and messages are not, and several documents quote their output
(already in English). `tools/api_domains.py` writes `api_domains.md` and
would bring the Italian back if run.

### Alongside, every session.

- **Every kit change checked on PC-ROA**, which must keep reaching its logos,
  movie, title, character creation, town and first quest at 30 frames.
- **The kit stays free of both games.** What is this game's knowledge lives
  here (`tools/`, and a port layer when one is needed).
- **Every invention declared**: the kit's in its README's known
  approximations, this repository's at its site and here.
- **Nothing generated is committed.** `build/` holds the ELF and the C++.
- **Read others' work, write our own.** RPCS3's sources are read for what
  the system does, never copied.

## The readings of sessions 1-13, as checks on the original

What used to be work to do is now a measurement to take on the recompiled
game, or a question it answers by itself:

- **`walkabout`**: 97% of inhabitants reached, 365 of 369 passages with a
  standable arrival ([`walk.md`](walk.md)). Walk the same maps in the game.
- **The enemies**: 312 of 312 running their own script, 10,196 placements,
  the patrols and the pose cycles ([`actor.md`](actor.md),
  [`entities.md`](entities.md)). Compare a room's enemies with the viewer's.
- **The menus**: 136 descriptors, 23 blocks and 60 items, and what a choice
  leads to, which the disc declares twice in 136 ([`ui.md`](ui.md)). The
  game now answers the second part itself.
- **The 1xxx band of cells**: two bands, by elimination; the forms, a
  contour ([`objects.md`](objects.md)). Look at what stands on those cells.
- **The torches**: 859 cells of `m_obj_99`, no emission in the material, no
  `light` record; the `effect` records (type 4, 1,792) never decoded. See
  how the game lights them.
- **The light**: baked into the vertices, the sky's direction, the
  overworld against indoors ([`renderer.md`](renderer.md)). Compare frames.
- **`+0x08` of the grid**: a byte pair, `b1 >= b0` in 482,180 cells of
  482,180, with `+0x0C = 1 << b0`.
- **Combat**: never written; the original has it.
- **The `SAV` saves**, the gimmicks of `Object/gimmick/`, the 41
  non-conversational event scripts (1 of 378 did not reach its end), the
  developer utilities on the disc (`MakeLuaDump.exe`), the unnamed material
  fields and the `skin` record's minor fields: questions the running game
  can answer when they matter.

## Deferred, with reasons

- **The disc-key layer.** The ISO is already decrypted (3k3y form); the
  disc-key decryption stays a teaching module for a physical disc.
- **Phase 1d** (clustering the 497 methods by domain): `host.py coverage`
  gave what was needed, and the recompiled game makes it moot.

## Open, unowned

**Inconsistencies the English rewrite found** in the documents of sessions
1-13, reported by the rewriters and left as they were written, to be
settled when someone next works in each document:

- `ui.md`: twenty dungeon maps against 21 floors; 319 of 358 strings
  mangled against 432 placed; 38 pieces parked off screen against 15 that
  slide; the cursor check's 30 items against 60.
- `walk.md`: `destructionWall` 46 against 45; `npcevent` 243 against 237;
  the walkabout block's 68% / 66% against the prose's 63% / 63%; "96% of the
  enemies have floor" against 546 of 10,196 without (5.4%); a stale "no
  cell declares the enemies"; Block Defence's 12, 22 and 34 actors; rooms
  404 of 413 against 305 of 416; nine bosses against eight.
- `objects.md`: `4060` labelled the chest and later proved the jar; twelve
  missing nodes, eight listed; the altars "in the same cell" but `D_1_3` at
  (7,4); 263 against 266 NPC files; the `AddColor`/`SetAmount` file counts;
  the overworld lists of 21 and 14 against `f_hmw` 28 and `f_ntr` 17.
- `actor.md`: "What is missing" stale after session 13 (98 methods, 27.3%,
  `AddAnimation` listed); `Troupe` still loading 869 sources, not 1,486;
  "ten enemies" against seven models.
- `entities.md`: 14,099 object cells against `objects.md`'s 11,924; the
  family table sums to 178 of 184 roots.
- `format_pac.md`: "until session 3" against "until session 4"; 91.2% in no
  measurement; the "still to clarify" 25.6/112 already explained; 40 overworld
  maps against 39 at 16×16; water and void 104,864 against `format_mapdat.md`'s
  96,441.
- `format_dpk.md`: 30.9 million triangles is the whole disc, models
  included, not the maps alone.
- `format_dsb.md`: the "common header" is 16 bytes in one place and 112 in
  another.
- `format_edt.md`: the 0x36 / 0x30 example of odd-length strings does not add
  up.
- `RECON.md`: "those 501 methods" against 497; `BackupDof` 526 against 524
  calls; 12 enums and 2,216 members against a table of 11 summing to 2,201;
  `SoundID` defined in Lua and native; 2,639 string literals against 2,747
  full-width strings; the font "fixed-width" against `host.md`'s proportional.
- `renderer.md`: the `ubyte4` still "unknown", while `render.md` names it the
  bone index.
- The log below: the session numbers some sections sit under (water drawing
  and the system screens under session 3); `SetPlayerPosition` unsolved and
  solved in session 4; the Field_16 sea at −2.0, not a multiple of 1.6.

---

# Log

## Session 14 - 2026-10-23

**The pivot, the kit's own repository, the docs in English, and the logos.**

The day began with the brief's plan: rethink the strategy on this EBOOT's
numbers, as PC-ROA had done in its session 33, and act on it.

**The repositories.** PC-ROA was brought level with GitHub (a rebase over
the remote's README fix, then a push). `ps3kit/` was split out of it with
its history (`git subtree split --prefix=ps3kit`, 15 commits) into
[vs-sr-dev/ps3kit](https://github.com/vs-sr-dev/ps3kit), with a licence and
line-ending rules of its own, and came back as a submodule in PC-ROA and
here. This project became a git repository: a first commit keeps sessions
1-13 as they stood, in Italian.

**The documents in English.** Every format and subsystem document was
rewritten in English (seven writers in parallel, each given the same brief:
rewrite, keep every fact, mark what is inferred). They reported 50-odd
inconsistencies in the originals, listed above under *Open*. The disc's
title id was wrong in the manifest's header and `extract.md`: BLES-00860, an
id the disc does not carry; PARAM.SFO says BLES00875.

**The EBOOT, decrypted and counted.** `self.py` came over from PC-ROA, minus
ROA's own `names` command, and decrypted the SELF in 44 seconds with
`key_revision 0x0001`'s APP keys ([`format_self.md`](format_self.md)). The
census confirmed session 33's numbers (20,672 functions, 26 SPU programs) and
added the rest ([`eboot.md`](eboot.md)): 237 imports all named, 112 of them
new to the kit; 77 lv2 call numbers; almost no vector code; **3.78 MB of the
game's Lua inside the executable**, 112 sources of 1,488 different from the
disc's; Lua 5.1.3, FMOD Ex, Bink, Bullet, Edge zlib; the engine's source tree
called `Block`.

**The recompiler, on a second game.** Eleven switch tables did not resolve:
their bound check sits in a block reached by a branch, after a return, and
the search for it crossed into other code. Following the branch back to its
source fixed all eleven, and corrected ten tables that had resolved with a
wrong bound. Then 22 more from unoptimised code, which loads the entry with
`lwz` from a sum instead of `lwzx`. 638 of 638; PC-ROA's 379 tables and
76,652 entries came out identical before and after.

**The SPUs.** The recompiler now finds SPU ELFs by their header and
translates each at its load address: five SPURS tasks at `0x3000`, FMOD's two
mixers at `0x80`, and lists the 19 relocatable FMOD modules it cannot place.
Bullet's 43,448-instruction task kept clang busy for more than ten minutes
with a dispatch case per instruction; with cases only where an indirect
branch can land (588) the whole build takes three and a half minutes. The
runtime gained lv2 SPU thread groups (`sputhread.cpp`) and a SPURS kernel of
its own (`spurs.cpp`): task sets, tasks on host threads, the task syscalls
through `0xA70`, exit codes, event flags in the system's layout, and
`spu_printf`. The water task told us twice what was wrong, through its own
`spu_printf`: `cellSpursEventFlagWait failed : 80410911` (the task had no
argument: `_cellSpursTaskAttributeInitialize`'s signature, which RPCS3 does
not know, was read off the call site instead), then `: 8041090f` (a task
that blocks checks its context save area and LS pattern; the task info now
holds them as the system's library writes them). Then it waited, as it
should.

**From the first flip to the logos**, each stop read and resolved: the
primary thread's priority was reported as 0 (a kit bug: the game wants
`prio - 1` for SPURS and exited cleanly when it was negative); the I/O map
(`cellGcmMapEaIoAddress` at offset `0x0E000000`, where libgcm keeps
main-memory reports); `sys_time_get_timebase_frequency`; the system
parameters; the fragment programs, which the game puts into local memory
with inline image transfers through the FIFO (NV308A into NV3062): with them
the first draw went through, and the logos appeared. Then FMOD: the sound
availability query, the MP3 decoder read from `/dev_flash` (a stand-in,
`tools/flash.py`), the audio notifications, and its SPU mixer started as a
thread group; the free space on the HDD (the game asked for 871 MB, and drew
its own message when it had none); the system cache. EISCONN and ENOTCONN had
had ESTAT's and EALIGN's values in the kit since ROA.

**The kit, checked on PC-ROA.** Rebuilt on the kit of this session, PC-ROA
reached its logos, movie and title unattended, and the user played it
through character creation, the town and the first quest: 171 of 182
seconds at 30 frames, every drop at a scene load (shader compilation, as in
its session 37). Then the kit was pushed and PC-ROA's submodule moved to it.

**And where it stops.** After the save-data check, a black screen with the
main loop running: item 1.

## Session 13 - 2026-08-20

Four TODO items, taken in order: the lighting, the 1xxx band, `AddColor`,
`AddAnimation`. Three closed. The 1xxx band did not, but three roads into it
are now shut and the question has been put better.

The TODO asked for the lighting and said where it belonged: in `renderer.md`,
not in the Lua host. It was right about the place and wrong about the
diagnosis. "The baked light is ~1.5× brighter than the declared colour and we
turn it off" takes for granted that our light and the data's are the same
thing on two scales. They are not: ours had **a direction the data does not
have**. All of it is in [`renderer.md`](renderer.md).

### The right question was: does the disc declare the light?

Twice no, and that is the useful part:

```
`light` records in the 167 map .pac         0
`light` records on the whole disc         400   one per file
  named `ambient-environment-light`       399
  40-degree cone, decay +inf          400/400
```

Forty degrees and infinite decay are the exporter's defaults. The colour
confirms it by contradiction: 336 are white and 62 the same beige, and the 62
make no sense as a set from the game — eight bosses, seven dungeon interface
maps, `NameEntry`, `Option`. It is the working environment of whoever did the
export. And `MapParameter`, which declares the place and the music track of
211 maps, says nothing about light.

### But it is baked into the vertices, and in a world of cubes there are six normals

So the data is read again, grouping the vertex colours by face. On
`field_16`: up 0.969, the four sides 0.695–0.709, down 0.494.

**The four sides agree within 1%.** That is not Lambertian, which would have
a light side and a dark side. It is a **vertical** ambient light: the sky.
Across the 40 overworld maps the spread between the sides has a median of
2.8%.

**And the direction flips.** Indoors the same measurement gives the opposite:

```
                up/sides   down/sides   spread between the sides
overworld  40     1.415       0.661            2.8%
indoors   126     0.822       1.000            0.1%
```

Where there is a ceiling the upward face is the **darkest**, and the downward
one comes back level with the sides, because below there is no longer a sky
to stand out against. A number that behaves like that is light.

### And the places put themselves in order — the validation

The up/sides ratio read per location, with the names `MapParameter`
declares: at the top Dash Circuit (1.52), Lake Garland, Nuntra Desert,
Gilgamesh Beach, Brilord Plains; at the bottom, **below the seven temples
(0.814–0.822), the caves** — Sacred Cave 0.78, Fairy's Cave and Rat Hole
0.75, Mountain Path and Fairy Spring 0.68.

Beaches, plains and desert at the top, caves at the bottom, temples in the
middle. The measurement orders the game's places the way someone walking
through them would, and none of those names went into the calculation. The
only two `field_*` maps that behave as indoors are `field_50` and `field_91`,
and `field_91` is **the castle courtyard**.

### Who carries it and who does not, decided by two measurements that do not know each other

The rule is not "maps yes, characters no". The vertex colour is light where
it **varies within one face direction** — that is, where occlusion has been
baked vertex by vertex, which the sky alone does not explain:

```
overworld   spread within the sides  42%     241 distinct levels
indoors                               3%       8 levels
```

The dungeons carry **two** (`d_1_1_1`: a moss green and black), and two levels
are not a light: there the geometry goes back among what the renderer lights,
or the walls become a single mass. The 30% threshold is not set by eye. The
second measurement, *"is the upward face brighter than the sides?"*, which
knows nothing of the first, cuts the maps in the same place: **165 of 167**,
and the two left over sit right against the boundary.

And there is a category that could not carry it **by construction**: a jar
instanced 1,022 times cannot hold in its vertices the light of 1,022 places.
Indeed `c_obj_all` has its six faces within **5%** of each other. There the
vertex colour is the tint, and it is the same thing `nodes.py colors` had
measured from the other end in session 12.

### What is left gets ambient plus sun, with the disc's numbers

- `Event:SetSunLightAngle(5.65,62.59); -- yaw, pitch` — **the comment is the
  authors'**. 16 calls, 8 distinct values, and every pitch lies between 57.75
  and 86 degrees: the sun in this game is always high. Median 73.5.
- `SetParallelLight(0.15,0.15,0.15, 0.08,0.08,0.08)` — two triples, the first
  always the brighter: diffuse and ambient. `amb/(amb+dif)` is 0.29, 0.35 and
  0.43, median **0.35** — which is, incidentally, exactly the coefficient the
  old formula had guessed.

The ambient is not flat: it follows the vertical profile that *that* map
shows in its own vertices, so whoever walks in a cave gets the cave's light.
One thing stays ours, and it is declared: the yaws, unlike the pitches, are
scattered from −180 to 31 — they belong to the scene, not the world — and one
of them is taken.

### What you see

What has gone is the horizontal direction the data does not have. The
Lambertian came from `(0.4 0.8 0.45)`, an azimuth of 42 degrees, and it dimmed
to 0.35 the two sides facing away from it — on top of a colour that was
already the light of the place. On `field_16`:

```
                   mean luminance   below 0.15   median
before                   0.195          47.9%      0.160
after                    0.295           5.9%      0.281
```

Half the screen was below 0.15, and the trees facing north and west were
black. In the dungeons, where the renderer now supplies the light, the floor
is brighter than the walls again and the room's plan can be read.

```
python tools/view.py light
```

### And what glows by itself: `emission`, a field the renderer was not using

Looking for the torches turned up the opposite: the torches are **not**
declared sources, and something else is. `emission` is filled in on **277 of
1,792 materials**.

**The edge case says how to read it.** The 166 in the `CharEditor` palette
are `1, 1, 1`: an interface panel receives no light, it shows at full colour.
So emission is not an addend, which would saturate them to white, but a
**floor**: `light = max(illumination, emission)`. With this reading the
interface case comes out on its own and nothing saturates.

The rest are exactly the things that glow in a game. The **21 magic blades**
(`MR_i_mwp_NN_light`, `_light` in 21 cases of 21) have a **white** diffuse and
all their colour in the emission, one by one — 06 fire red, 12 light blue, 15
green, 22 magenta. And then the projectiles: `tamaa`, 玉, emission 0.30, and
the boss's 0.60.

### The six orbs, and the disc's second swapped pair

The five emissives in the map library are the altars' orbs, and their colour
closes a loop from session 12, which had established the order from the item
names without being able to see it:

| altar | map | the script's item | material | colour | the walkthrough |
|---|---|---|---|---|---|
| 4116 | `D_1_3` | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `D_2_3` | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `D_3_3` | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `D_4_3` | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `D_5_3` | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `D_6_3` | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

**Six of six** with the names the walkthrough uses, and this is the third
time that source, written for playing, has validated a reading made on the
bytes. The two internal names that do not describe a colour, `gray` and
`white`, are exactly the two the model contradicts: those orbs are orange and
purple. *The name the game shows beats the one the authors wrote down for
themselves.*

And the material has to be **looked at**, not inferred from the number:
`m_obj_118_b` uses `orb_121` and `m_obj_121_b` uses `orb_118`, an exact swap
among four that match. Inferring it from the number would have given two
wrong colours, and it would have been the same shape of mistake as
`NP_NPC_19` ↔ `NP_NPC_26`. That also explains the last oddity, which follows
the material and not the place: `orb_121` is **the only one of the six with
no emission**, so the orb that does not glow is the third temple's.

### `AddAnimation`: the pose cycle is no longer inferred, it is read

It was "the most-requested missing method", 916 calls in 192 modules. It now
runs, and together with `InitializeAnimation` it takes coverage from 71.8% to
**79.2%**: two methods, seven points.

`AddAnimation(i, wait)` adds **node `i`** to the cycle for `wait` seconds.
That the first argument indexes the `AddNode` calls is the only reading the
corpus allows: **in 314 files of 314** the highest index is less than the
number of nodes added, without one exception. The trap is that it **is not in
`Initialize`** but in `Update`, at the change of state.

Of 25 enemies that declare a cycle, **15 say exactly `02_a`/`02_b`** — the
rule session 4 had inferred from the geometry — and ten correct it. Goblins
walk in **four beats** (`02_a, 01, 02_b, 01`), the Killer Bee flaps its wings
with `04_a`/`04_b`, and `c_enm_23`/`24`, which are among the eight models
with no `_a`/`_b` pair at all, have their own `02, 01`. The step timing stops
being a number of ours too: from 0.12 to 0.25 seconds, declared one by one.
In `d_1_1_1`, **59 enemies of 60** take their cycle from their own file. All
of it is in [`actor.md`](actor.md).

### `AddColor` is the fragments, and the authors say so

The item had been in the TODO for two sessions with the right hypothesis and
no proof. The proof is a comment, and it had never been read because it is in
Shift-JIS inside a UTF-8 file:

```lua
Object:SetAmount( 4 );                  -- 壊れた時の破片の量
Object:AddColor( 0.38, 0.26, 0.00 );    -- 破片の色
```

*The amount of fragments when it breaks*, and *the colour of the fragments*.
The data holds the reading without exception — `AddColor` is **always at
most `SetAmount`, 71 files of 71** — and `SetAmount` is 4 in 52 files of 78.

That **explains** session 12's measurement instead of leaving it as an
oddity: *"the 132 declared colours are already those of their own model's
vertices, to half a degree of hue"*. Of course they are: the fragments of a
thing have the colour of the thing. And the argument with which that session
had ruled out "one per node" falls. That `12GoblinRed` declares the same
colour twice rules nothing out, because in a palette of four fragments a
repeated colour **weighs double**.

The eight bosses do not call `SetAmount` because they break **in parts**:
`B01Snake` has `AddColor` for the 頭 (head), `AddBodyColor` for the 体 (body)
and `AddTailColor` for the 尻尾 (tail), three colours each. All of it is in
[`actor.md`](actor.md).

*There is nothing to implement until there is destruction: this item closes
as a reading.*

### The 1xxx band did not close, but three roads are closed

It is the only item of this session that stays open, and it sits at the top
of the TODO with what was measured: it is not a node number, not a local
index, not the edge of a screen. What was gained is **the shape** (the cells
draw frames and rows) and its split into two groups against the collision:
86% of the cells sit right against a step in one, 14% in the other.

And three things that fell out along the way, each worth having on its own:

- **`d_hmw_03` is not missing.** [`objects.md`](objects.md) had it as "the
  only declared one the cells do not use": it is in `d_chikei` instead of
  `d_haichi`. The family is split across two files, and it was not a
  leftover.
- **The dungeon count agrees across three files**: `d_haichi` declares 28
  objects, `DFI_DUNGEON_OBJECT` has 28 entries, the 3xxx band uses 28
  numbers. For the overworld the first two agree with each other (40 and 40)
  and the third does not — which is exactly where the problem lies.
- **The abbreviations can be read**, because the symbol table names them in
  rōmaji where the node has three letters: `d_kbe` is `MPD_D_KABE`, 壁 the
  wall (145 entries, the largest family on the disc); `d_dns` is 段差 the
  ledge; `d_hsr` 柱 the column; `d_skr` 仕切り the partition; `d_yka` 床 the
  floor; `f_gke` is `MPD_F_CLIF`, 崖 the cliff; `f_jmn` the ground. **Seven of
  nine**, and the two that stay abbreviations are exactly those of the open
  bands.

## Session 12

The TODO asked for **the hook-up** of the twenty-one gimmicks, because a jar
does not load `EN_ENEMY_NN`. It goes through no rule: there is a table, and
this is the fifth session in a row in which what was needed was on the disc,
in the clear, in a file we had not opened. All of it is in
[`objects.md`](objects.md), `tools/nodes.py`.

### The disc declares its own symbols, 1,279 rows

```lua
addNodeListElement( TFI_EVENT_OBJECT, DFI_EVENT_OBJECT,
                    MPD_M_OBJ_127_a,  "m_obj_127_01" );
```

The texture package, the scene package, **the native constant with which the
code names the piece**, and **the node's name**. So the bridge between the
name a script utters and the node inside a `.dsb` is no longer an inference
of ours.

```
declared nodes                           1,279
  that really exist in a .dsb            1,267    99.1%
constants passed to AddNode                394
  declared in the table                    387    98.2%
```

And the **six commented-out rows** all name models that no longer exist on
the finished disc: the table was maintained.

### And it confirms three sessions of inferences — except two entries, which were ours

```
EN_ENEMY_NN -> c_enm_NN     135 of 136
NP_NPC_NN   -> c_npc_NN     112 of 116
```

The four entries off the pattern are **two swapped numbers**, `NP_NPC_19` ↔
`NP_NPC_26`, and that is exactly the pair session 8 had pointed to as the weak
spot of its own mapping: *"the exceptions all fall on
`c_npc_19`…`c_npc_26`"*. It was right about where to look.

Going through the 263 files of `Object/npc/` re-reads the archetype→model
mapping that session 4 had inferred from the names of the 237 dialogue
scripts: **20 archetypes of 22 agree, 2 are corrected**. And the second
correction is the one that counts:

- **`princessbug` is `c_npc_26`**, which is the swap above. Seen, the
  difference is one of colour: `c_npc_19`, `26` and `27` are three winged
  figures, red, blue and green — `N19PrincessBug`, `N26PrincessBugB`,
  `N27PrincessBugC`.
- **`goblinred` is `c_enm_12`**, that is an **enemy** model. The village's
  friendly red goblins reuse the red goblin you fight, and that is why there
  is no `N26GoblinRed` under `Object/`: it was not needed.

The second is not an off-by-one, it is a change of family. No inference made
*inside* `c_npc` alone could have reached it, because it was looking for a
`c_npc_NN` and found one. *The number in the name of a **dialogue** script and
the number of the **model** are two numberings, not one. They agree twenty
times out of twenty-two, and that is why they looked like the same one.*

### The cell declares the model: `4000 + NN`

The gimmick scripts load `MPD_M_OBJ_*`, the table sends those to `m_obj_*`,
and the cell's identifier is **4000 plus that number**. It is not a reading
of one case: three families that do not know each other hold it up, **51
cells of 51**, zero disagreeing — 34 `Signboard` (4041 / `m_obj_41`), 12
`Stonemark` (4067 / `m_obj_67`), 3 `Well` (4063 / `m_obj_63`).

From there the whole band, which until now was a number, can be read: **4127
is the grass you cut** (272 cells), 4111 the bosses' gravestones, 4116–4121
the six orb altars, 4062 the sword's pedestal, 4099 the 859 torches, 4060 the
1,022 chests. And the 3xxx band is `3000 + NN` → `d_hmw_NN`, the
"Dungeon配置物" of the authors' comment, **28 numbers of 28**.

**The proof by structure, which is stronger than the count.** The six altars
and the six gravestones are not placed at random: one gravestone per boss
room, one altar in the room after it, always at the same cell (7–8, 4), and
the order of the altars is that of the temples — `item_yelloworb`,
`greenorb`, `grayorb`, `blueorb`, `redorb`, `whiteorb`. Six of six, in the
right temple, in the right order. The gravestones are seven scripts for six
cells, and the seventh signs itself: in `BossMarker07` the guard is commented
out and in place of the event there is `Print("ぼひょー")`.

**And absence reads like presence.** Of the 4,229 cells with no model,
**3,843 (91%) are in 4100…4105**, six numbers in a row; and
`m_obj_100`…`m_obj_107` is **the longest gap in the library's whole
numbering**, while the others are one to five wide and scattered. 4100 is the
`Warp`s and the observers, 4101 `Exit`, `destructionWall`, `WarpDoor` —
exactly the classes session 8 had measured as absent from both the geometry
and the collision. The disc has reserved a block of the numbering for
whatever has no object.

### And they can be seen — `walk.populate_props`, `view.Charlib`

7,695 object cells of 11,924 (**64.5%**) have a model and are drawn. The
drawing needed no new path: only the library in which to look for the node
changes, and the names are enough to say which.

The check is one of recognisability, as for the enemies in session 8:

- in `d_60_3` the cell says `Well01`, the identifier says `m_obj_63`, and **a
  stone well with a wooden frame** appears, with the signboard beside it that
  the neighbouring cell declares;
- in the castle courtyard **columns and braziers in mirror image** appear on
  the two sides — which is what *配置物* means;
- in the Grass Temple room where session 8 had put two Scorpions and one
  Soldier Bones there are now also **two jars and the red door**.

And lined up with `view.py char`, one of them closes a loop by itself:
**`m_obj_116_b` is a yellow orb**, and it is the node `OrbAltar01` hides with
`SetNodeVisible(1, false)` *"if you have already taken the yellow orb"*. The
code says what to hide and the model is yellow, from two files that do not
know each other.

### And the jar, which was the question this started from

The jar is **`m_obj_60`, identifier 4060, 1,022 cells — the most numerous
object on the disc**. What says it is the jar is `Jar.lua`, which is a table
of three colours and nothing else: the three fall on three of the **seven**
tints of `m_obj_60` within **0.1–0.3 degrees** each. The jar loads nothing
because it has no script: the C++ instantiates it, and the disc itself
declares only the cell and the palette.

*A hypothesis that fell along the way, and it has to be stated because it was
the first item of this TODO.* Objects come out dark and it looked as if
`AddColor` were missing. It is false. The first doubt is in the code:
`12GoblinRed` calls `AddColor` four times in a row **and the first two are
identical**, which rules out both "one per node" and "one per model colour".
The proof is the measurement above, extended to the whole corpus: **132
colours declared by 42 files, median hue difference 0.5 degrees, 94% under 5
degrees** against their own model's palette. `AddColor` *declares* the
colours the model already has; applying them would change the tint of
nothing. The darkness is our lighting.

```
python tools/nodes.py colors
```

### A corrected count: `all.lua.eu` is 1,486 sources, not 869

869 is the count of the `../lua/` sources alone, which is one tree of
twenty-nine; the other twenty-eight are the data files (`Event/`,
`MiniGame/`, `UserInterface/`) in the same stream. Looking for a source's
boundary only among the `../lua/` ones made seven of them swallow the 185
that follow them — `Object/DropItemList` was taking in the minigame's hundred
files. None of the seven is an enemy file, so session 11's measurements do
not change; the count does, and with it the idea of how much of the disc that
file contains.

*Fallen out along the way, and worth it because it was one more source nobody
had read:* `DropItemList` is an array of 38 rows, and the comment on row `N`
names enemy `NN` — **37 of 38**. The one miss is the authors' typo
(`34Succubus2` where the file is `35Succubus2`), not a shift, because 36 goes
back to `36HagureSlime`. It is the fourth independent confirmation of the
number→enemy table. `08Rock` is the only empty entry: a boulder drops
nothing. And after the 38 there are **two keys by name**, `['Grass']` and
`['Guard']`: the grass you cut drops coins, and it is the same `Grass` as the
272 cells above.

## Session 11

The two small loose ends that were left, taken seriously — and looking for
the first one opened a file that calls the item at the top of this TODO back
into question.

### 5080 is Togetoge, and the class is the direction it moves in

Session 10 had read the geometry well and concluded badly: *"it is not a
creature, it is a figure"*. It is an actor, and the file that writes it says
so — `../lua/Object/69Togetoge.lua`, トゲトゲ, "spikes". The comment at its
head **is the table we were looking for**:

```
0 : 縦移動                vertical
1 : 横移動                horizontal
2 : 縦移動（突撃タイプ）    vertical, charging
3 : 横移動（突撃タイプ）    horizontal, charging
```

and class `4` is `TogetogeDashUpdate(Object,2)`, that is 縦横: still until
you line up with it, then it charges along both axes.

The geometry then becomes a cross-check, and of the right kind. It is a rule
the placement cannot break without breaking the game, because two spikes on
the same lane would collide at the first step:

```
class 0 (vertical)      all columns distinct      4 groups of  4
class 1 (horizontal)    all rows distinct         5 groups of  5
class 4 (charging)      2 columns and 2 rows     11 groups of 11
```

The model exists, and it is `EN_ENEMY_39_01` = `c_enm_39_01`, **the last** of
the 39: it was the rule `5080 → c_enm_64` that did not hold there, not the
model that was missing. And the album is right not to list it, because
`69Togetoge` does not call `setBookRegistInfo`: the album's 46 are the 46
that **register themselves in the bestiary**. Nor does `08RockFall.lua`,
which loads `EN_ENEMY_08` and whose name confirms 5024's falling boulder for
the third time.

The walkthrough validates twice without knowing it. The *"spike puzzles"* it
lists are in Aqua Temple, Wind Temple, Dark Tower and the cave west of the
tower — **the only maps with 5080 of class 0 or 1**. And where it warns that
*"if you don't move at all upon entering a room… traps won't activate"*, the
code says `if( not Object:IsPlayerArea() ) then return; end`.

A hypothesis that fell along the way, worth recording because it was the most
natural one: that the four corner cells were the **four switches** of the
timed puzzles. The walkthrough counts dozens of those in every temple, Grass
included — and Grass has no 5080 at all.

### `+0x08` is not a number, it is a pair — and the old reading was a sample

`n·257` and `2ⁿ` worked because the two bytes coincide in **92.3%** of cases.
Across the whole disc that reading breaks 33,000 times. What admits no
exception is something else:

```
high bytes zero       482,180 of 482,180
b1 >= b0              482,180 of 482,180
+0x0C with two bits   never
```

So it is a **range**, and `+0x0C` carries only its lower end. What it
measures stays open, but the field is much narrower than it was: the values
go from 0 to 31, per map they number 2-3 in the dungeons and up to 7 in the
overworld — the profile of a **height** — and the measured floor agrees with
`b0` in 84.1% of the dungeons and 68.2% of the overworld. Strong, and below
the threshold at which this project calls a test an oracle.

The best clue is the exception. The **272** cells in which `+0x0C` has more
than one bit are all in `field_7`, have `b0 = b1 = 31` and the mask
`0x7FFFFFFF`. Thirty-one is the most a 32-bit mask can carry, and field_7 is
the highest map on the disc — the one that in session 6 forced us to measure
the height of the column instead of assuming it. It is a saturation.

The per-map ceiling that `map_param.lua` declares (`field07=20`) does **not**
bound `b1`: it holds in 8 maps of 35. That road is closed.

### And the file that opened everything: the enemies are written in Lua

`all.lua.eu` is not one file: it is the **concatenation of 869 sources**, with
the folder tree left in the comments (`-- Start ../lua/Object/06Bee.lua`).
Inside are 128 `Object/` files, 266 `Object/npc/`, 21 `Object/gimmick/`.

```
enemies that call setBookRegistInfo      46      as many as the album declares
of which with the full Update            46
of which with motion (phases, speed, direction, pursuit)   37
the remaining 9: the 8 bosses plus Guardian, which have only Initialize in Lua
```

That is, **the item at the top of this TODO has to be rewritten**. "Patrolling
is not declared in the clear anywhere" was true of the minigame's twelve
files and false of the game: `06Bee.lua` declares `MoveArea = 10.0` with the
comment *出現位置からの行動可能範囲* — the range of action from the spawn
point — and uses it in `IsActorMoveArea`. The common enemies' motion can be
read.

*Why we had not seen it: patrolling had been looked for in `MapParameter`, in
`GameParamData` and in the API, never here. And `all.lua.eu` is one of the 21
files with Shift-JIS comments that until session 9 made almost everything in
them unreadable.*

### And the enemies move — [`actor.md`](actor.md), `tools/actor.py`

It did not stay a reading: it runs. `Troupe` loads the VM once (869 sources
in a tenth of a second), each placed enemy receives the object the Lua calls
`Object`, and every frame its `Update` is run.

```
36 methods implemented of 134 requested = 72.7% of calls
312 actors of 312 placed enemies find their own behaviour
  0 scripts crashed      0 left the walkable area while moving
261 of 312 move on their own, in five seconds, on five maps
```

The 12% that stand on a cell with no floor **were already there at the
start** — they belong to session 10's 546 — and those that start on the floor
never leave it. The 51 that stay still are not a defect: among them are all
the Togetoge, which the first line of their `Update` freezes until the player
enters the room.

**The proof that closes the loop with this morning's loose end.** The class of
5080 had been read as the axis of movement, from the file's comment plus the
geometry of the placement. Running the scripts measures the same thing from
the other end:

```
Togetoge class 1 (horizontal)   displacement  X 2.3   Z 0.0
Togetoge class 0 (vertical)     displacement  X 0.0   Z 29.2
```

Three method decisions are in [`actor.md`](actor.md), and one is worth
recalling here: **in Lua `0` is true**, so answering zero to an unimplemented
predicate would give an enemy that always believes it can see the player — a
behaviour of our own invention. What gives the right answer is the original
code's naming convention (`Is…` a predicate, `Get…` a number, the rest a
command), which is regular across all 55 files.

`python tools/view.py play d_1_1_1 --cell 39,18 --skip 6` photographs the room
after six seconds of life: the scorpions have turned and moved, the skeleton
has walked. `--still` leaves them still.

### And the inhabitants wander about

Same folder, same hook-up: **33 NPC files**, and `OldManUpdate` is all the
villages' wandering — a random direction, one cell per second, a radius of
four cells, and again.

```
the castle courtyard: 33 inhabitants, 32 with their own script, 22 wander
0 errors   0 left the floor
```

**Ten files have no `Update` at all** — the King, the six sages, the
legendary hero, his ghost, the Medal King — and among the 55 enemies it is
never missing. The disc declares standing still by an absence, and the
category is the right one: whoever waits at the end of a temple does not go
for a stroll. But staying put is not being motionless: `KingInitialize`
alternates the two poses of the step every half second, which is why
`AddAnimation` is called even by those who do not move.

Fallen out along the way, a hook-up worth having: models 02–08 write
`NP_NPC05_01` and the others `NP_NPC_09_01`, two conventions on the same disc,
but **the file's number and the node's coincide 33 times of 33** — the third
independent confirmation of session 4's archetype→model table.

And one thing that **nobody declares**, to be marked as ours: an
inhabitant's initial facing. It is not in the scripts (none of the ten still
ones calls `SetDirection`) and it is not in the grid (the cells that name an
NPC carry not a single flag). `facing = 1` is a choice made by
`walk.populate`.

But **the placement implies it**, and that can be measured: those who do not
move always stand higher up the grid than the door you come in by — **11
cases of 11** indoors, with the King of Dotnia at y=11, the door at y=36 and
six courtiers lined up in between. You walk towards them, so looking down the
grid means looking at whoever arrives. It is the convention one expects from
a game of this kind, but here it is not taken from the genre: it is measured.
It stays an inference — the data says where they stand, not where they
look — but it is an inference with an oracle. *(The one exception is a sage
out in the open overworld, where "the nearest door" is not the entrance to a
hall and the question does not arise.)*

## Session 10

The three loose ends session 8 had isolated, all three closed — and a premise
that was holding them up, removed.

### "They never overlap" was a tautology

Of the three measurements that said *"A, B, C are three arrangements of the
same population"*, the most convincing was that their cells never overlap.
It proves nothing: `mapdat.cells` walks `for i in range(w*h)`, that is **one
cell, one record**, and each record carries one actor and one letter only.
Two letters in the same cell **cannot exist in the format**.

The reading does not change — the other two measurements hold — but the tally
of evidence does, and that is why it is worth checking the premise before the
result.

### `F,G,H` add to the others, and it is measured by contradiction

It was the last thing written down as an arithmetic inference. Counting the
maps is enough:

```
with A,B,C and F,G,H     50
with only A,B,C           9      the most populated is d_5_1_2, 45 enemies
with only F,G,H           0
```

If `F,G,H` replaced the others, those nine maps would be left **without a
single enemy** in the difficulty the walkthrough calls *"hordes"* — among
them a dungeon floor with 45. And `|F| < |A|` in 29 maps of 59: the Grass
Temple would go from 60 enemies to 13, so FROM Mode would be *emptier*. They
add.

### The 4% with no floor: the question had to be split by place, not by species

After the flight hypothesis had fallen on the species, the answer lay in the
place:

```
in the overworld:      0 of 6,097  =  0.0%
in the dungeons:     546 of 4,099  = 13.3%
```

**Zero of six thousand.** In the overworld the disc puts every single enemy
on a walkable cell, which says the placement knows where the ground is. The
phenomenon belongs entirely and only to the dungeons, and the map objects
share it (32% against 0.2%).

The next hypothesis was the most uncomfortable one — a **one-cell offset
between the grid and the collision**, that is, our fault — and the signal that
suggested it is strong: the floor is never to the right or below, and where
there is a single neighbour with floor it is up and to the left **44 times of
44**. It was measured and it does not hold: shifting *all* the enemies by one
cell takes the dungeons from 86.7% to 87.6% of walkable cells, and a real
offset would take them to 99%.

What remains is a strict rule, and it is the answer: **nobody spills over by
more than one cell**. All 546 have from one to three neighbours with floor,
never zero and never more than three, and in 497 cases of 546 those
neighbours are at the same height. The placement is drawn on the room's
rectangle and overflows by one cell into the wall; in the overworld there is
no wall to overflow into. Hence `Columns.ground_near`: an enemy with no floor
settles on the one next to it, not at zero.

### 5024 is the falling boulder — and the album's numbering says so

In the stretch 5018–5026 the offset between identifier and model number is
constant (5016) in **all eight** declared entries, and 5024 is the stretch's
only gap. Hence `c_enm_08`, which really does exist among the 39 models and is
a lumpy ochre mass with no poses.

The placement agrees from three sides: six maps only and **all of them high
ground** (Mt. Sabre, Sukaboko Highlands, Klovis, Vatara Highlands); cells in
rows, from 5 to 28 cells up; and the ground **slopes down ahead in 50% of the
cases and in no other direction**, with the rise behind. The walkthrough, on
Sukaboko Highlands: *"a screen with Centauses and **falling rocks**"*.

It has the six placement sets like every enemy — so it comes back — and the
album does not list it because a boulder is not a monster to register.

### 5080 is not a creature: it is a figure

Neither `c_enm_64` nor `c_npc_33` exists, and the record's last field is
**1** where enemies have 0 and NPCs 6. Its class is not a name but a digit,
and the digit picks a shape. Class `4`:

```
11 figures, 4 vertices each, 44 cells
the corners always at (1,1) (14,1) (1,10) (14,10) inside the 16×12 screen
```

The four corners of a screen, pulled in by one cell — one per temple plus
five in the Dark Tower, none in the Grass. They are not boss rooms, and the
contradiction says so: the boss maps have **zero**. Inside each figure there
is instead **exactly one observer**, 11 of 11, and from 10 to 16 enemies.

Classes `0` and `1` draw other figures — a diagonal of five cells, three
times — and remain open. But the range above 5000 does not hold only
creatures, and that was the point.

## Session 9

The item that had been stuck for three sessions, closed — and wider than it
was written. The TODO said "`Cancel = {Enable, Index}` says which item the
cancel button chooses, so the behaviour is declared too: what is missing is
something to run it". Looking for what runs it showed that **almost
everything** is declared, and that what was missing were three readings of
ours.

### An item is an item if the cursor can rest on it — [`ui.md`](ui.md), `ui.menus()`

The criterion is not the block's **name** but `CursorX`/`CursorY`. Searching
that way finds **23 blocks with 60 items**, under three names. `Select` is the
19 yes/no prompts already known, but `Menu` is the title menu and the pause
menu — *RESUME, SAVE, LOAD, OPTIONS, SNAPSHOT, ALBUM, BESTIARY, LOADING ART,
TITLE* — and `ClearMenu` is the title **once the game is finished**, with
`NEW GAME+` added.

The two title lists share their positions from 407 down: the new item is not
added at the bottom, the menu **grows upwards**. And every item carries its
own line of explanation, which is the only piece of interface that changes as
the cursor moves.

The axis is not a choice: the items are stacked in a column in **23 blocks of
23**, zero in a row. The cursor sits 34 px to the left and 7 up, always the
same, and the pitch between two items is **32 px** — the font row with which
in session 7 the dialogue box came out at 597 against a body that ends at
598. The same number from a third place.

### Cancelling does not mean leaving, and the index counts from zero

All 19 screens with `Cancel` have the same two items `YES`/`NO`, and all 19
declare `Index=1`. Counting from one, cancelling would mean agreeing **in all
19**; counting from zero it is `NO` in all 19. It is the same base as
`Start`, which is 0 for the `In` clip: two fields, the same convention.

So ○ does not close the window, it **chooses one particular item**. And where
`Enable=0` it does nothing — `ClearSave`, `DeleteSaveDataSelect`,
`GameOverSaveSelect`, `GameOverResurrectSelect`, the four screens in which
the game insists on an answer. Two windows that look identical behave
differently because the disc declares it:

```
python tools/ui.py drive Continue cerchio out.png
  cerchio  item 2/2 'NO'  -> chosen 'NO'  (cancelling)

python tools/ui.py drive ClearSave cerchio out.png
  cerchio  item 1/2 'YES'          the button does nothing
```

Of this whole part **only one thing stays ours**, and it is switched off:
that from the last item you go round to the first (`Screen(...,
wrap=False)`).

### The button bar declares which actions there are — `ui.keybar()`

The labels are in the descriptor, the icons in the scene under a `KeyAssign`
node, and they pair up because every label begins **7-8 px after** the end of
an icon; the strip is continuous, and in the album the seven rectangles run
from 673 to 1176 without a gap. What names the button is **the colour**,
which on this hardware *is* the button: the ✕ is drawn blue and the ○ red.
Grey, on the other hand, separates nothing — the d-pad and the shoulder
buttons have no tint — and it stays a single name.

Two things the count says that are worth keeping. `PAGE` has no icon because
paging is done by the arrows at the sides of the page, which are nodes of
their own in the scene. And where the screen **scrolls** the pairing cannot be
done, because the strip is parked off-screen while the labels are already in
place. Those are the same 5 screens as always.

### The page is the floor, with its sign — `ui.pages()`, `ui.dungeon_floors()`

`setting = {pageMin, pageMax}` was a field nobody had looked at. On the
dungeon maps that number is the floor, and the sign says which way: `B1` is
−1, `1F` is 0. Two independent counts:

```
pageMax - pageMin + 1  =  number of floor descriptors      7 dungeons of 7
the printed labels (B2, 5F) fall in their own range         19 of 19
```

The two left out are the **single-floor** dungeons, which declare `0..0` and
`1..1` although both are `B1`: where there is nothing to page through, the
field is not maintained.

The order of the files is not the order of the floors — dungeon 5 keeps them
as `1F`, `2F`, `B1` — and the first descriptor **does not declare its own**
floor, because it lists every label in order to draw the selector. Its floor
is obtained by difference: it is the one the others have not taken, and that
holds in all five multi-floor dungeons. All **21 floors** now have their
name, and in `play` the map pages with the arrows.

### The text was there and could not be seen: three defects, one inside the other

**The permissive tables were needed in `descriptors()` too.** 11 files were
failing silently on a native constant: **17 screens** missing, among them the
enemy album and all seven dungeon maps. There are 136 screens, not 119. The
fix had already been written in `descriptor_file()` a session earlier.

**The files are UTF-8 in the data and Shift-JIS in the comments.** The
authors left their notes in their home encoding — 21 files of 618, and the
bad byte always comes right after a `--`. The fallback "if UTF-8 fails,
re-read everything as Shift-JIS" threw away the whole file because of one
note, and among those 21 is `all.lua.eu`, which on its own declares almost
all the screens: the labels came back garbled, **319 of 358**.

**And then it became visible how many labels the disc places.** There are
**432**, and **85** were being drawn, because we looked inside `Message` and
`Select` and nowhere else. A label is recognised by having a text **and** a
place: the 61 blocks without `X`/`Y` are data lists, names that another part
of the screen will go and fetch.

Hence the dungeon map, which was mute, now says "Dark Tower" and "3F".

*The defect has the same shape as the two discoveries before it — in session
6 data that looked empty was only closed, in session 7 a piece that looked on
was only off — but this time the cause was **entirely ours**: the disc said
things, and we were reading the file wrongly.*

### The cursor was not ours, and where it sits measures the text

It was the last piece we drew by hand, and the scene carries it in two ways:
**parked at the origin** in 7 blocks of 8 (a 16 px `Cursor_01`, to be put
where `CursorX` says), and **one per row, already placed** in the pause menu,
nine markers at the positions the descriptor declares item by item — 530
against 529, 86 against 84. In the second case the other eight have to be
switched off, which is the same shape as the dungeon map.

And the cursor gives the oracle for **two numbers of ours that had been tuned
by eye**. The font cell is 32×32, and the descriptor puts the cursor 7 px
below the label: 16 high inside a row of 32, it lands in the middle. So `Y`
is the **top** edge of the row and the font scale is **1**, not 1.4. The
cursor lands in the middle of the row to within 6 px on 30 items, and it
matches session 7's sum for the dialogue box (`485 + 3×32 + 2×8 = 597`
against a body that ends at 598): the same row height by two roads that do not
know each other.

### A screen's follow-up is declared in two cases of 136

Looking for it before declaring it absent: `Pause` opens `PauseTitleSelect`,
and `GameOver` opens `GameOverSaveSelect` and `GameOverResurrectSelect` — a
field at the end of the table whose key is the same as its value. All three
are the **confirmation window** for a choice that cannot be taken back. Where
the follow-up is a question, the disc says so; where it is another screen, it
does not.

## Session 8

The first item of the previous TODO, closed — and with it three censuses the
project had kept apart, because it turned out that **a single field** holds
them together. Then, for the first time, a validation against an external
source.

### The field at +0x10 is the actor — [`walk.md`](walk.md), `mapdat.actor()`

The cell record has six numeric fields, and five had been marked `?` for five
sessions. The fifth is **who lives there**, in a numbering global to the game,
and three files that do not know each other share it out: map objects below
5000 (constant per class, **175 of 195**), the enemies the `EnemyView` album
declares (**45 of 46** are found placed), and the NPCs at **5047 + NN**, where
`NN` is the index of `c_npc_NN` (**226 cells of 240**, 94.2%).

The last is the best of the three, because it is one oracle *more* on a
conclusion already drawn. Session 4 had inferred that `n05` is `c_npc_05` from
the names of the 237 `npcevent_` scripts; here twenty consecutive values say
it again on their own. The exceptions fall **all** on `c_npc_19`…`c_npc_26`,
which are exactly the models that inference resolved worst: the disagreement
points at the weak spot in our directory, not in the disc.

The 8,781 values below 4000 remain unattributed.

A second field fell along the way: +0x08 and +0x0C are the **same number in
two encodings**, `257·n` and `2ⁿ`, with not one pair off the pattern.

### The enemies are on the disc, and the six letters are two triples

"All that is left to the code is how many it puts in each room and by what
rule" was written here, and it was wrong: the grid places **10,196 enemies**,
one per cell. And every cell carries a **set**, `-sA`…`-sH`, a string no
document of the project had ever seen.

**A, B and C are three alternative arrangements of the same population**, and
three measures that fail in different ways say so: the same species in **58
maps of 59**; equal numbers across the whole disc (1,807/1,824/1,804); and
cells that **never** overlap while covering the same area (88%, above 80% in
51 maps of 59, below 40% in none — so they are not squads). In the Grass
Temple the identity holds species by species: 13 Soldier Bones, 10 Scorpion,
15 Bat, 22 Red Slime, three times over.

**F, G and H are the same three for FROM Mode** — and the letter says so: `F`
stands for FROM. There the parallel breaks, as it should: in `FIELD_16`,
36/47/45 against 19/19/19, seven species against four.

### And the enemies are in the game — `view.py play --spawn`

`Walk.populate_enemies()` puts them on the map, and the drawing code needed
not one line: an entity with model `c_enm_01` looks for the node
`c_enm_01_01`, which is exactly what the album declares in `NodeStrings`. The
only translation is to strip the pose from that name, because the album names
a **frame** and the world needs the root — which is itself a confirmation,
from a third file, of session 4's "the children of a node are whole poses".

The check is one of recognisability, and it passed three times:

- in the grass temple, at cell (39,18), **two Scorpion and a Soldier Bones**
  appear — two red scorpions and a skeleton with a sword, which is exactly
  what the surrounding cells declare;
- **switching `--spawn` from A to C**, at the same spot, there are again two
  Scorpion and a Soldier Bones (plus two Red Slime), **in entirely different
  places**. The hypothesis of three placements can be looked at instead of
  read;
- in `field_16` with `--spawn F` the green overworld fills with Spidel and
  Goble.

And a measure the render suggested, worth more than the render, because it
puts the walkthrough's most specific sentence to the test — *"even enemies
that are normally restricted to dungeons"*:

```
A,B,C in the overworld:  2,195 enemies,    12 of dungeon species =  0.5%
F,G,H in the overworld:  3,902 enemies, 1,356 of dungeon species = 34.8%
```

Seventy times as many, and 17 species against 3. That is not a statistical
preference: it is the difficulty, declared in the data.

### The twelve enemies written in Lua — `entity.enemy_motion()`

The game implements its enemies in C++, but the disc carries twelve of them in
full. The actors of the Block Defence minigame reuse the real models **by
number**: `MGBee` loads `EN_ENEMY_06_04_a`, which is the `NodeStrings` of
`Killer Bee`. The link is checked on the **names**, which neither file takes
from the other — `MGSkelton`→*Soldier Bones*, `MGWood`→*Evil Tree*,
`MGHagureSlime`→*Crystal Slime*: **twelve of twelve**.

Three numbers that would have had to be invented can now be read: the
**period** of a frame (`StepWait`, 0.3 in all twelve — ours was 0.25 and came
from no data), **the poses of the cycle**, and **who flies**.

The poses exposed a defect of ours. `Entity.pose()` always returned
`02_a`/`02_b`, but **12 `c_enm` models of 37** have no `02_a` at all — four
walk with `04` and eight have no pair. A third of the enemies stood still
because we were asking for a pose that does not exist. Now the minigame
declares the cycle where it has one, and the model itself does otherwise.

And a rule that holds for **all 22** actors, with zero exceptions: *if the
model has two paired poses `_a`/`_b` the engine runs the cycle, otherwise the
actor alternates them by hand.* It is the counter-check, from a file written
for a minigame, of the "`_a` and `_b` are the two steps" inferred in session 4
from the geometry alone.

**A hypothesis that fell, and it counts because only now could it be
measured.** Having `Type` (ground/air) might have explained the 4% of placed
enemies with no floor under them. It does not: fliers 2.3%, ground 4.0% — if
anything the direction is the opposite. The one that misses the floor most
often is Clay Golem (17%), which walks, while Killer Bee is over the ground in
100% of cases. It stays open.

**Patrolling**, on the other hand, cannot be read: in the minigame the enemies
walk towards the tower with a native `BlockDefenceMove()`, which is that
minigame's rule. Left unimplemented rather than invented.

### There is no patrolling, and looking for it gave the places their names

`MapParameter.lua.eu` was the last place to look before inventing how enemies
move, and it contains nothing about movement. Nor does the API, which has
`PlayEnemy`, `PauseEnemy`, `visibleEnemy`: freeze and show, never move.
**Patrolling is not declared in the clear anywhere**, and it stays
unimplemented rather than invented.

But that file declares **211 maps with the place name and the music track**,
and it matches **168 of our 170** (the two left are `field_99` and
`field_test`). 55 locations for 168 maps, so a place spans several screens:
crossing `field_6` and `field_7` is staying in "Klovis". `play` now says where
you are. And `field_3` is called **"Nialliv Valley"**, which is *Villain*
backwards.

A confirmation at no cost: `d_1_1_1` is **"Grass Temple"** and `d_6_1_3`
**"Wind Temple"**, so `DUNGEON_EARO` = wind is now said by a **fourth** file,
in English.

### `LivingId` is the family, not the home — a reading of ours, corrected

With the temple's name and the real placement together, a sentence the
documents had taken for granted could be put to the test. 1,988 enemies are
placed in the temples, and their `LivingId` names the temple they are in
**47.1%** of the time. With seven habitats chance would give 14%, so the
correlation is strong; but it is not a rule, and the Flame Temple is full of
`DUNGEON_WATER`. The habitat classifies the enemy, it does not place it — it
was the best proxy while the placement could not be read.

And a reading that comes out of it: **the Dark Tower has no habitat of its
own, it passes through all of them**. Floor by floor the prevailing habitat
goes GRASS, GRASS, SANDS, WATER, WATER, EARO, that is 1, 1, 3, 4, 4, 6 in the
order in which the game has you visit the temples. A non-decreasing sequence:
the final tower retraces the journey.

### External validation, which is what is new in method

A [walkthrough](walkthrough/) — written for playing, not for reading bytes,
and so with errors entirely its own — confirmed four things we had inferred
from the bytes alone, and none of them had been looked for:

- *"If the enemy positions are annoying, you can leave the room and come back
  and see if they respawn in a more favorable location"* → the sets
  `A`/`B`/`C`;
- *"all kinds of crazy enemies spawn all over the place — even enemies that
  are normally restricted to dungeons"* → the profile of `F`/`G`/`H`;
- *"Crystal Slimes and Blue Dragons spawn rarely… they can actually spawn
  anywhere"* → **5075** and **5076** are the **only two of the 46** with
  `LivingId = -1`, that is with no habitat. The field that sets them apart in
  the data is the one that sets them apart in the game;
- the eight bosses with their temples, **eight of eight** against the album's
  habitats — and with them goes the last doubt about `EARO`, which is *aero*.

And a reading the data already gave without knowing it: bosses can be told
apart because they have **2 cells on 1 map and no `-s`**. A boss has no
alternative placements because it lives in a single room.

### The 25 event names were functions, not files — `Grid.triggers`

"Only 3 names of 25 find their file", the TODO said. It was the search that
was wrong: `gimmick_grass4` is a **function** inside `gimmick_grass.lua.eu`,
together with the other six `gimmick_grass`. Searched for that way, **25 of
25** resolve.

They are position triggers, and the body confirms it: the guard
`if GetEventFlag(167)==1 then return end`, `LockPlayer`, the fairy explaining
the switch, `UnlockPlayer`. They run on the Phase 4 host without adding a
method. Five of the 25 are in the same file and are the four directions plus
the centre: `mainevent_herodream` `n`, `s`, `e`, `w`, `2`.

### What the objects do: parameterised in the clear, implemented in C++

`GameParamData/gimmickParam.lua.eu` declares fifteen gimmicks with their
parameters and the authors' comments — `Hole` with `gravity 18.0` and
`pop_count 1`, `BlackHole` with `vacuum_range 6.4`, `TargetSwitch` with the
clamp value "for when the arrow sticks in", `stone_monument` with its two
messages. The walkthrough validates these too, one of them word for word: the
`stone_monument` tablet is the Parallax one, and our twelve `Stonemark` are in
the rooms where the guide says to cast it.

The **logic** stays in the code, but we know its shape. The disc carries 34
actors written in Lua for the Block Defence minigame, with all four callbacks
of the contract (`Initialize`, `Update`, `CheckMove`, `CheckCollision`), and
among them is `75MGBombRock` — the wall a bomb opens, written out in full.
`MR_BLOCK` and `MR_NONE` appear nowhere else on the disc.

## Session 7

The item at the top of the previous TODO, closed — but not as it was written.
The question was "either the motion is rebuilt by interpolating between the
parking position and the final position, or it is the first thing to ask the
EBOOT", and the answer is that these were **two different animations** put
into one item: one has both ends on the disc, the other has only one.

### `Start` is not a time, it is an index — [`ui.md`](ui.md), `ui.py clips`

The four clips had been read as a start and a duration on a timeline. The
count says otherwise: on the 36 screens that declare `In`, `Start` is **0 all
36 times**; `Main` is 1 all 33 times; `Out` is 2 all 36 times. A time that
never changes is not a time — it is a position in a table of clips, and the
name decides it. `Size`, by contrast, varies, and it is the duration in
seconds.

The big screens confirm it, and they also say what it indexes. In `Option` the
indices run from 0 to 38, densely, and the three panels `Display`, `Sound`,
`Message` **share** the block 3–9 and keep apart only their own 0–2, 20–22,
23–25. So the message area, the button bar and the cursor are the same
objects, reused: the index does not identify a moment, it identifies **the
thing that moves**.

The ten indices 10–19 looked like a gap and were a reading defect of ours:
`Volume` is an **array**, not a dictionary, and a walk that descends only into
dictionaries skips it. They are the ten notches of the volume control, and the
scene has exactly ten nodes `Volume00…Volume09`.

### Opening can be rebuilt, because the disc has both ends

The piece is exported at scale zero and the mesh under it is whole, so
everything from 0 to 1 is there; `Size` declares the duration. `unfold` is no
longer a switch but a **factor**, and `ui.py anim` produces the frames.

The window opens like a television switching on, and the scene says so:
`Confirm_01` is three pieces, `a` (505×4) and `c` (505×7) with **scale X = 0**
and the body `b` (505×99) with **scale Y = 0** — first a horizontal line, then
the body vertically. Which axis opens is declared by which scale is zero. The
one thing not read is the curve, and here it is linear so as not to add an
invented number.

### Sliding, by contrast, has only one end, and it is 15 pieces

The sliding screens are not closed by a scale: they are **moved**. Only the
parking position is on the disc — `Window01` at `x=-600`, `Window03` at
`x=1300`, `Message` at `x=1285`.

The motion is horizontal, and that is measured: **38 pieces parked off
screen, 33 off only in X**. The Y is already the final one, and the descriptor
confirms it by another route — it puts "EQUIPMENT" at y=53 inside `Window01`
(48–294), "ITEMS" at y=308 inside `Window02` (303–550), the buttons at y=635
inside the bar (632–666).

But **where they land in X is written nowhere**: not in the scene, which has
only the parking position, and not in the descriptor, which places the content
and not the container. Interpolating between parking and final position is not
possible, because the final position is missing. This, and only this, is the
part to ask the EBOOT, and it concerns **5 screens and 15 pieces**: `Item`,
`Orb`, `Option`, `NameEntry`, `GameOver`.

### The dialogue box, and the file that was not it — [`ui.md`](ui.md)

It was the last piece we still drew ourselves, and the TODO put it in
`data/Balloon`. It is not there. `balloon_eng.ps3.dsb` is three quads of
**1.6 × 0.6 world units** — 1.6 is the cell — with materials `CHECK`, `TALK`,
`OPEN`, and the textures are three speech bubbles with the ✕ button and the
tail pointing down. It is the sign that floats above a head. The same shape of
error as `Priest.ps3.dsb`: a convincing name, and a measurement that refutes
it.

The box is in **`UserInterface/Message`**, with the same three-piece structure
as every window — `Message_a/b/c` (505 × 138) and `MessageBig_a/b/c`
(686 × 154) — plus `Advance_Cursor`, the "press to continue" arrow. The
descriptor supplies the rest: `Line=3`, the text origin (`X`/`Y` and
`LargeX`/`LargeY`), the line spacing, the colours and **ten typing speeds**.

The numbers fit together, and that is the check: the font at scale 1 is 32 px
a line, so `485 + 3×32 + 2×8 = 597`, and the body ends at **598**. It also
shows that `Space` is the spacing *between* lines and not after each one —
adding it after the last line overshoots by seven pixels. `view.py` now picks,
of the two sizes, the one the text fits in, and puts it where the disc says.

### And the signs became the "you can talk here" cue

Found by mistake, the object turned out to be what the game loop was missing:
`play` had no way to show the player where to press. Now the `TALK` sign sits
above the head of whoever is in front of you, and **only if they have
something to say** — it is an invitation to press, not a decoration.

It costs nothing because it hooks into `EntityGroup`, which reads the matrix at
draw time: one geometry in the batch, a dummy entity that every frame takes the
place of whoever is in front of you, and a null matrix to switch it off. The
camera gives the angle, because a sign is always read face on.

### The body of the small box is transparent, and that is right

In the render the world shows through the dialogue box, and it looked like a
compositing defect. The alpha says otherwise: the body of the **small** box
has a mean alpha of 19, so it is empty, while the **large** one is at 214,
solid black. A dialogue with an inhabitant is two thin strips and the text
over the world; the opaque panel is the other size. *Before correcting a
transparency, measure it: here it was the data.*

### The enemies, and the album that declares them all — [`entities.md`](entities.md)

The TODO said to look at the parameters of the `EnemyObserver` cells before
concluding that the EBOOT is needed. Those cells carry no enemies: 65 cells
with a `-gNNN` and nothing else, that is **a room number**, and the five
numeric fields are the same as any `observer`'s.

The census is elsewhere, and in the clear. The **enemy album**
(`UserInterface/EnemyView`) is a descriptor like the others, and it declares
**46 enemies** with identifier (5002–5082), model, English name, habitat and
drops. The models resolve **46 of 46**: 37 are nodes inside
`Character/c_obj_all.ps3.dsb` — the same shape as the NPCs — and the 9 bosses
have a file each. `view.py char c_enm_01` draws a purple rabbit with red
horns: ツノウサギ in the comment, `Killer Rabbit` in the descriptor.

The fifteen habitats are `FIELD_*` and `DUNGEON_*` by element, and the seven
dungeon ones match one to one the seven temples of `Item.lua.eu`
(`DUNGEON_EARO` is *aero*, wind). So **which enemy belongs to which dungeon is
known without the EBOOT**; all that is left to the code is how many it puts in
each room and by what rule.

*(Corrected in session 8: it is not left to the code. The grid places the
enemies cell by cell, 10,196 in all, with the species in field +0x10 and the
set in `-sA`…`-sH`. See above.)*

The first attempt failed, and it is worth saying so: without the **permissive
tables** the descriptor does not run, because it names native constants
(`LIVING`, `GameDataFlags`, `item`) that no script defines — and the table
appears not to be there. `ui.descriptor_file` now loads `host.BOOT`, which
already had that solution.

### Map objects declare their room — [`walk.md`](walk.md), `Grid.rooms`

The shape of the string splits the cells into two families: `-gN;` alone
(`SwitchObserver` 80, `EnemyObserver` 65) and `-gN;-oM;` as a pair. And within
the pairs, where the two numbers are **equal** the cell turns up again on
another map — `WarpDoor` 29 of 29, `destructionWall` 43 of 46 — so those are
passages, and that is why `walkabout` already went through them.

**The hypothesis written here was wrong.** "The `PitFall` has a pair like the
passages, so falling is arriving": tested, its pair turns up again 2 times in
21, and the `BlackHole`'s 3 in 7. Neither the `-g` alone nor the `-o` alone
resolves them: each falls on twenty cells at a time, so they collect instead
of addressing.

**The number is `(floor)(room)`**, and two files that do not know each other
say so. The first digit is the floor written in the **file name** (2,484 gates
of 2,490, 99.8%), and the rooms that come out are the ones the
`dungeonMapNN_MM` descriptors draw as `room_on_NN` — **404 of 413**, with 14
floors of 21 exact.

A nice reading that fell along the way: the dark tower's seven black holes are
one per floor, and the first digit of their gates goes 1, 2, 3, 4, 5, 6, 7.
They looked like the seven temples, and a tower that opens onto the dungeons
would have been an elegant explanation. None of those pairs exists in the
dungeon the digit names: **0 of 7**. The digit was the floor the cell is on.

### The dungeon map can be drawn — [`ui.md`](ui.md), `ui.py map`

It was under "what is missing", as a screen with dynamic content waiting for
save data that does not exist. The data came from the item above: the grid
declares the room of every cell, and the scene has one piece per room and per
state. `ui.py map 1 1 out.png --seen 1,2,3 --here 4` draws the floor with the
rooms seen lit, the current one brighter and the rest black.

And the descriptor confirms the reading of the rooms from a third file, by
naming the fields that are mute digits in the grid: the doors declare
`groupId` and `objectId`, which are the `-g` and the `-o`, with `groupId=12`
for floor 1, room 2.

**The three states are not three drawings: they are a colour.** `room_on_02`,
`room_off_02` and `room_still_02` have the same mesh, the same position, the
same UVs and the same texture, and what tells them apart is the material's
`diffuse` — 1.0 / 0.5 / 0.0. The defect this uncovered is general: the
compositor looked only at the texture and threw away the material colour on
**every** screen. Now it multiplies by it — and the defect was a big one,
because tint is how this interface declares states: **49 scenes of 115** have
tinted nodes, 1,869 in all, of which **891 at 0.0** (fully off) and 864 at
0.5. Eight hundred and ninety-one pieces that should be black were being drawn
at full light.

### The map enters the game, and three roads that lead nowhere

`view.py play <map> --map`, or `M` while walking: the map of the floor you are
on, over the scene. In the wind temple the floor selector on the left lights
the third slot of five, which is the right floor — and it does so by itself,
because it is in the descriptor's scene.

What **cannot** be done is to say which room you are in, and not out of
laziness:

- "the room is a screen" — the box around the marked cells fits in 16×12 in
  95.4% of cases, but only 305 rooms of 416 fall in an aligned block;
- "the region tag is the room" — no: in `d_1_1_1` all 23 rooms carry the same
  tag `2001`, which is the **dungeon**;
- "the nearest marker" — the boxes do not overlap (1.3%) but cover 12% of the
  map, and where the answer is certain the nearest marker gets it right
  **75.7%** of the time: noise with a preference.

The picture that emerges is coherent, though, and that is a result: the
observers are the **entry triggers** by which the engine records which room
you are in — which is why they are sparse, and why two in three sit inside the
solid rather than on the floor. The region is of use to nobody but us, so it
is not declared.

### The `EDT` format, the heart of the game's identity — [`format_edt.md`](format_edt.md)

`EDTFILE1.9`, the characters drawn dot by dot. Solved with the same oracle as
ever: **90 files of 90 end exactly on the last byte**, for 260,860 voxels. All
big-endian and **unaligned** — a byte stream, where one odd-length string
shifts everything after it by one.

A voxel is 20 bytes: a packed position, plus RGB, plus a finish (0–6). And the
three bytes of the position are **all between 0 and 15**, that is a cube of
**16×16×16** — which is the grid of `water_col.dds`, sixteen dots per cell,
found in session 5 for quite another reason. Three files that do not know each
other, the same unit.

**The six parts are six poses.** The counts of `angel.edt` — 261, 256, 246,
240, 263, 267 — are too close to be six pieces of one body, and the measure
closes it: **60.4%** of the voxels are in the same position between the first
part and the other five. It is session 4's "characters have no skeleton, the
children of a node are whole frames", seen from the other side.

The check is the contact sheet: 90 recognisable characters — knights, mages,
Santa Claus, a king with a crown, dragons, skeletons, a bear, a pumpkin — and
the presets come back under their own file names, `angel` with a halo and
wings, `black_smith` with a white beard and an apron, `boxer` with gloves.

**And the first contact sheet came out from behind**, which was noticed by the
person looking at it without knowing what to expect. It was not a defect:
taking the maximum Z gives the backs of the heads, taking the minimum gives
the faces — so the editor's characters are authored **facing −Z**, the same
convention `entities.md` had inferred in another session from the game's
meshes. Two files written for different purposes, the same choice. And it can
be measured without looking: in `black_smith.edt` the front plane carries 9
voxels and the back one 40, because a face is hollow and the back of a head is
solid.

Only one thing did the first pass get wrong, and it corrected itself: it
stopped 24 bytes short of the end. Twenty-four is exactly six floats — the
part's tail, which is there after the last part too.

### A hypothesis that fell, worth keeping

The `_PIVOT` nodes seemed to declare the anchor the growth starts from, and
the test "for every piece at scale zero, the mesh has an edge at exactly 0 on
the zeroed axis" gives **87.3%** — which seems a lot until you measure the
control on pieces at full scale, which gives **76%**. It is not an oracle, it
is noise with a preference. And the exceptions say why: `NEW-node` in
`EnemyAlbum` measures `[-61.5, +61.5]`, so it is **centred** on the origin and
grows from the centre. The anchor is not the edge, it is wherever the origin
falls — which is just how a scale works, not a discovery.

## Session 6

Both items at the top of the previous TODO, closed — and the first opened the
second, which had not been planned to come this way.

### The 22 passages without a standable arrival: none was a wrong reading

They were 19 arrivals that were not walkable, plus 3 passages whose
destination does not exist on the disc. The right question turned out to be
the first one asked: **is there a collision triangle above that cell?** Yes,
in all 19, and in several cases one that faces up, too. So the collision was
there, and what missed it was our reading, in **three** different ways — all
three of them numbers assumed instead of measured:

- **the column was anchored at zero.** 69 collision files of 171 go below it,
  and the floor of `d_1_2` is at `−0.000002`: a barely negative zero, the
  residue of a `float32` passed through a barycentric sum. The 114 points that
  fell in the entry cell of the game's first passage were thrown away, all 114
  of them.
- **the column was 25.6 units tall.** `FIELD_07` is a mountain and reaches
  51.2: the summit was cut off.
- **the seeding had a cap of 96 subdivisions**, which looked like the prudent
  choice. In `FIELD_07` 2,238 triangles of 6,747 exceed 38.4 units — the
  longest side measures 190 — and for them the step became 2.0, wider than a
  cell: it left whole cells uncovered. Without the cap it costs 27% more points
  across the whole disc and leaves no holes.

Now the mesh declares base and height, and the passages reached with a
standable arrival are **365 of 369**: the four that remain have a destination
map absent from the disc.

### The backdrop, and why putting the right levels back made everything worse

With the levels below zero put back, the measure dropped from 63% to 41%.
Under every overworld map there is a single flat quadrilateral spread from
side to side — in `FIELD_22` it is **two triangles** for 10,368 cells of
16,384 — at −3.2. It faces up, so it is a floor in every respect; only it has
metres of rock on top of it, and being the lowest it is the one the map
starts from. `field_30` dropped to 84 cells walked of 10,219.

What separates it from a real floor is a count, not a threshold: there are
**163,878** two-level cells, and in only **758** of them is the lower one not
the map's minimum height. The gallery above the hall exists and is 0.16% of
the world; all the rest of the overlap is this backdrop.

Two plausible hypotheses fell before getting there, and they are worth
keeping: `LEVELS = 4` had nothing to do with it (four levels cover 100.00% of
the cells), and the criterion "there is something else above the backdrop"
runs from 30% to 83% with no break, which is noise with a preference.

### Water, and the tag that declares it

The cells where the backdrop is the **only** level are not land: they are the
sea, the moat, the gorge between two plateaus. There are **40,964** of them,
and at that point the TODO's second item solves itself, because there is now
something to test the region tag against:

```
88.4% of water cells carry tag 119
85.1% of cells with tag 119 are water      (the tag is one cell wider)
```

Map by map, wherever `119` appears, 98–100% of the water carries it. And it is
a value **unique across the whole disc**. Session 5's hypothesis, that it
changed by group of maps, came from confusing **water** with **void** — the
cells with no collision at all, 55,477 of them, which are the gap between the
declared rectangular region and the real map, and which the tag indeed does
not declare (among them `119` is 10%).

So water is known without opening the collision file, which is what the
renderer needed in order to know where to draw it.

### A map is entered by all its doors

`field_14` has six `Exit` cells: the first opens onto a shelf of 16 cells
under a cliff, the other five onto the 3,213 that are the map. The measure
tried one and wrote 0%. That is not calibration: taking a single door measures
the door instead of the map.

And the complete picture, worth keeping apart because four different causes
had been merged into a single number:

| | cells | inhabitants | passages | standable |
|---|---:|---:|---:|---:|
| rendering geometry, step 0.6 | 18% | 65% | 194 | |
| `.DPK` collision, step 0.6 | 25% | 78% | 202 | |
| `.DPK` collision, one-cell step | 63% | 96% | 303 | 281 |
| measured column, buried backdrop, all doors | **67%** | **97%** | **369** | **365** |

### Stepping down is one cell, and it is not a choice

The rule was symmetric — one step up, one step down — so as not to walk off
roofs, and the symmetry had never been tested. The same oracle as for the step
says it is right: letting the walk descend further, the inhabitants reached
stay at **257 for any descent**, from one cell to no limit at all. Descending
further buys only cells (+3.6%), that is roofs and cornices.

So the maps that stay poorly walkable — `d_60_2`, `d_80_1`, `field_90` — have
real islands, not a wrong threshold. Three of them, incidentally, **have no
passage pointing at them**: they are entered by script
(`Event:SetMap("Field_90","-gtf3_1")`), and the door the script names is the
very one the walk already starts from.

### Map objects are actors — [`walk.md`](walk.md), `Grid.objects`

The grid declares **1,518 cells in 112 classes** besides passages and
inhabitants: `observer` 163, `Observer` 149, `SwitchObserver` 80,
`EnemyObserver` 65, `destructionWall` 46, `up` 30, `WarpDoor` 29, `PitFall`
21, `BlackHole` 7, `Barricade` 7.

The useful question was where they live, and the answer is **nowhere**: the
breakable wall is 0% drawn and 0% solid, and so are the black hole and the
door. Their cell is smooth floor. The engine instantiates them as actors — the
taxonomy is the `ActorType` enum already extracted from the Lua, with
`AT_DESTRUCTION_WALL`, `AT_DOOR`, `AT_GIMM_GROUND_SWITCH` among its 33
members.

Two consequences follow, and they belong together. The game loop **walks
through** the 45 breakable walls, so `walkabout` is an upper bound, however
tight — and trying to open them gives zero extra cells, because they were
already open. And the observers **are not floor triggers**: two in three are
inside the solid, and only 31–41% of their cells are walkable.

A small side thread: 64 cells name a script (`mainevent_*`, `gimmick_*`), but
only 3 names find their file — `mainevent_deserttemple1` is in
`mainevent_201_deserttemple1.lua.eu`, that is the number is not in the cell's
name. The other 22 names have no script called that.

*(Corrected in session 8: all 25 resolve. They are not files but **functions**
inside one file per element.)*

## Session 5

Both items at the top of the previous TODO, closed. And then two things that
were not planned, which walking itself asked for: the collision format, and
the discovery that the only invented number in the system was wrong.

### Walking in the world — [`walk.md`](walk.md), `tools/walk.py`

`view.py play <map>` — arrows to walk, space to talk, `K` for the ceiling.
One cell at a time, and turning is not walking.

- **The wall.** Each cell keeps a column of 64 slices a quarter of a cell
  thick, with the highest height found in each, and up to four distinct
  **levels** — the gallery above the hall is a place, not a step. You pass if
  the column is free between +0.3 and +1.3 above your feet; the foot lands on
  the highest surface within a step, which is also how you climb a staircase
  without knowing it is a staircase.
- **You stand only on what faces up.** This is the mistake this part cost: a
  solid block has vertices *only on its faces*, so a floor 1.6 high offers
  two, and the underside looks like a floor with a metre and a half of free
  air above it. You walked inside the rock and the map broke into islands.
  What separates the two is the vertex **normal**.
- **Passages, used rather than counted.** A gate has two forms and both are
  needed: by name (`-gfrom_d_1`, matched on an `Exit` cell) and by number
  (`-g11;-o101;`, matched on the *identity* of the arrival cell, which is how
  staircases are built). With the first form alone 46% resolve instead of 98%.
- **The entry point is an `Exit` cell**, not any cell with a `-g`: those are
  in the hundreds — observers, gimmicks — and starting from the first one made
  the game begin **on top of a wall**.
- **The ceiling is removed above the player's head**, because this game's
  dungeons have a roof and from above they are a slab.

And the measure, which is what stays:

```
python tools/view.py walkabout

167 maps walked in 62s, standable entry in 167 of 167
cells reached on foot     221,227/352,278 = 63%
inhabitants reached           254/264     = 96%   (dungeons 94%, overworld 99%)
passages reached              303/512,  with a standable arrival 281
```

63% of cells is not a 37% failure: the denominator also counts roofs and the
tops of walls, which are not meant to be reached. The number that counts is
the inhabitants'.

### The black areas of a frame are water, and the disc declares it

Looking at the overworld still: the large black areas were neither a render
defect nor missing geometry — they are **water and void**. The cells under
those areas have neither geometry nor collision, and `MAP_ALIGNMENT` sets them
apart by giving them a region identifier all their own (496 cells with tag
`119` in `Field_16`, and no other cell of that map carries it).

That closes an item open for two sessions: **the 9% that `layout` left
uncovered was the denominator**. Counting only the cells the game considers
solid, the map composition covers **99.6%** instead of 90.7%; the other
104,864 cells, 22%, are sea and moats. `view.py layout` now prints both
numbers.

*(Corrected in session 6: 99.3% and 96,062 cells, because the denominator of
solid cells was itself truncated below zero. And "sea and moats" were two
different things put together — see above.)*

Water still has to be **drawn**, though: the `.pac` does not contain it, and
none of its 11 textures is water. The engine draws it, and that is renderer
work.

### `MAPCOLLISION/*.DPK`, the real wall — [`format_dpk.md`](format_dpk.md)

It was not planned for this session: walking asked for it, when the measure
said that approximating collision with the drawn vertices was not enough.
Solved at the first attempt, with the same oracle as `MAP_ALIGNMENT`: a table
of meshes, each one vertices and triangles, and walking it ends **exactly** on
the last byte in **171 files of 171** (301 meshes, 420,301 triangles). The
same frame of reference as the `.pac`, nothing to convert.

The one field you would not guess is the count, which is of **floats** rather
than vertices. And there is a typo on the pressed disc: `DANGEON_8_2.DPK`.

### A step is one cell, and it was not calibration

The only invented number in the whole system — "a knee", 0.6 — was wrong by
nearly a factor of three. Two independent oracles say **1.6**:

- the height differences between neighbouring walkable cells are exact
  multiples of 1.6 (85.3% at zero, 8.6% at 1.60, 3.3% at 3.20, almost nothing
  in between);
- the **inhabitants reached** saturate there: 206/264 at 0.6, **255** at 1.7,
  256 at 2.5 and at 4.9. One cell buys 49, everything beyond it one.

The overall gain, worth keeping apart because two different causes had been
merged:

| | cells | inhabitants | passages |
|---|---:|---:|---:|
| rendering geometry, step 0.6 | 18% | 65% | 194 |
| `.DPK` collision, step 0.6 | 25% | 78% | 202 |
| `.DPK` collision, one-cell step | **63%** | **96%** | **303** |

And the overworld/dungeon gap **has gone**: 63% and 63% of cells, with the
overworld at 99% of inhabitants against the dungeons' 94%. What a few hours
earlier had been written as "two causes, the first being missing geometry" had
a single cause, and it was the invented threshold.

### The 199 NPC places without a name — [`walk.md`](walk.md), `entity.npc_directory()`

The map declares 236 identifiers, and the event scripts named 37 of them. The
others are named by **their own** script: the 243
`npcevent_n<NN><archetype><id>` carry the model and the archetype in the file
name, and the dialogue in the body.

- **225 identifiers of 236 (95%)** now have a name, a face and a line, and the
  name is the one the scripts would use — so an event that later names that
  NPC finds *this one*, already in place.
- The **capitalisation** is not given by the file name (`Blacksmith` or
  `BlackSmith`?): it is given by the 151 scripts that spell out their own name
  inside.
- Six more archetypes with a declared model: `WiseMan1` → `c_npc_01`,
  `WiseMan2`…`WiseMan6` → `c_npc_20`…`c_npc_24`. They had ended up among the
  "extras with no `npcevent`" because the census looked at the names used by
  the **event scripts**, and the six wise men speak almost only through their
  own.

## Session 4

Three items, all three at the top of the previous TODO, and **none of them
needed the EBOOT**, as had been written there.

### Map NPCs and the model table — [`entities.md`](entities.md)

The two items at the top of the previous TODO, both closed, and **neither of
the two needed the EBOOT**, as had been written.

- The **positions**: among the cells of the logical grid there are 271 whose
  class is nothing but an NPC's identifier (`a1_010`, `b8_010`), with no
  parameters. The name the script uses is archetype plus identifier, so the
  tail of the name is the key — the same shape of match as the gate name for
  passages. **72 names of 99 placed**, up from 40.
- The **models**: the 237 scripts under `Event/npcevent_*` are named
  `npcevent_n<NN><archetype><id>`, and that number is the index of
  `c_npc_NN`. A perfect bijection — zero indices with two archetypes, zero
  archetypes with two indices — and checked by eye on six unmistakable models:
  Spelunker in dungarees, the king's crown, the hen, the dog. **66 names of 99
  with the model the disc declares**, up from zero.

The first clue came by chance: drawn, `c_npc_05` looked like an old man, and
`n05` is `oldman`.

### Map composition — [`format_pac.md`](format_pac.md)

`view.py screens()` + `layout`. The knot that kept two working pieces apart,
and with it a **correction**: until yesterday the sections of a `.pac` were
believed to be *cullings* already in place, and they were all drawn on top of
one another.

They are **screens to be composed**. Section `(c, r)` goes in its place in a
grid whose pitch is declared by the `MAP_ALIGNMENT` of the same name: the
ratio between the logical grid and the container's grid is always an integer
— 16 × 12 cells per screen in the dungeons, 16 × 16 in the overworld.

```
python tools/view.py layout

167 maps checked, map cells covered    436,043/480,731 = 90.7%
                  geometry off the map  14,192/625,861 =  2.3%

on the 82 multi-screen maps:  composed 90.3%   stacked 3.9%
```

The oracle is external to the format: `MAP_ALIGNMENT` says cell by cell where
there is map, and it is another file, with another purpose, in the only other
endianness on the disc.

Everything else follows from this:

- **a logical cell is 1.6**, which is a character's height: the logical grid,
  the screen grid, the models and the script arguments are the same unit;
- the scripts speak in a frame with its **origin at a corner** (X positive to
  the right, Z negative downwards), and `to_local()` brings it onto the
  `.pac`'s centred one;
- `SetPlayerPosition(cx, cy, floor)` really places the player, and with them
  the NPCs that spawn relative to the player;
- the six-argument signature of `SetCamera` **was wrong**: it read a distance
  where the elevation is, and there is no distance at all. A sign said so —
  the second argument goes down to −17.72.

Now `view.py <map> --event <script>` is the game's own scene: the whole map,
the characters where the script puts them, the framing the script chooses.
And admitting a fractional screen pitch — `d_20_9` has 3 screens for 38 cells
— takes the check from 163 maps to **167 of 167**, 13,000 more cells covered
without increasing the geometry off the map.

### Entities — [`entities.md`](entities.md), `tools/entity.py`

The first item of the previous TODO, closed. The world has characters in it:
position, direction, pose, movement over time. Twenty-two more methods on the
host.

```
43 methods implemented of 128 used, covering 5,814 calls of 6,634 (87%)
                                            (it was 22 methods and 63%)
```

- The **four directions** are `0:+Z 1:−Z 2:−X 3:+X`, an enumeration in paired
  axes that nobody would have guessed — 2 and 3 are opposite each other, not
  consecutive. Two independent oracles that agree decided it: whoever turns
  and then walks walks forward (75% on the largest cell), and Pizzaro and Rosy
  talk to each other from −1.6 and +1.6 in `mapevent_f80`.
- **A cell is 1.6, and a character is one cell tall**: the arguments of
  `CreateNpc` are multiples of 1.6, and the 31 NPC models measure exactly 1.60
  with their origin at the feet. Two files that do not know each other, the
  same scale.
- **Characters have no skeleton**: the children of a node are whole frames
  spaced 2.0 apart (162 of 200), not parts. The game animates by swapping the
  mesh, like a sprite game — and `SetNpcNode(name, 0..3)`, which picks a child
  by ordinal, confirms it by an independent route. This is also why skinning
  appears in only one file on the whole disc.
- **`MoveNpc` does not block**: at equal speed and wait the distances covered
  are 1.6 — 3.2 — 4.8, so the wait that follows times nothing.
- Two new modes of the viewer: `view.py char <model>`, to look a character in
  the face with its poses in a row, and `view.py event <script>`, to run an
  event **on an empty stage, with no map**. The second came from a real
  obstacle: this game's maps are full and have ceilings, the NPCs ended up
  inside a wall, and you could not see whether the registry worked.

Two things the data refuted along the way, worth remembering because both
were plausible:

- "a newly created NPC faces the player" gives **55%**, that is noise with a
  preference, and proposes a wrong mapping as the best candidate;
- `Event/Priest/Priest.ps3.dsb` exists and is named like a `CreateNpc` name,
  but it measures 0.96 × 0.64 and uses `cliff_01.dds`: it is the event's
  *scenery*, not the priest. The coincidence of names would have passed for a
  successful resolution had the numbers not been looked at.

And one thing that stays **declared unsolved**, rather than guessed: where in
the world a `SetPlayerPosition` cell falls. X is at ~1.6 units per cell over
31 events, Z changes by a factor of ten — because every map has its own
origin. So the registry notes the cell and moves nobody, and of the corpus's
99 names it places 40 (those of `CreateNpc`, which are offsets from the
player) and draws only those.

## Session 3

Both items at the top of the previous TODO, closed.

**Phase 1a, the official extractor** — [`extract.md`](extract.md),
`tools/iso.py`. `extract/` is no longer local state: it is a function of the
disc, with a manifest and hashes. 2,799 files indexed, 2,793 declared for
3.1 GB, `sha256` of all of them in 26 seconds, full verification in 30.

- It reads via **UDF**, not ISO9660: ISO9660 names are truncated to 31
  characters, and in this game names *are data* (a material refers to its
  texture by file name). Verification proved it at once, by flagging as
  missing 167 `.pac.gz` that locally carried 7-Zip's truncated name.
- The UDF reader is hand-written because `pycdlib` refuses the disc: PS3
  Blu-rays use UDF 2.50 with a **metadata partition**, and the inodes live
  inside a file that overlays the physical partition. ~150 lines, no
  dependencies.
- The **manifest** (`tools/manifest.tsv`, `path · size · sha256`) is the
  fingerprint of the supported disc: hashes, not content, so it belongs in the
  repository.
- Two finds in the inventory: `MakeLuaDump.exe` and
  `AdditionEditCharMessage.exe`, the developers' Windows utilities left on the
  pressed disc, and `Font.bin`.

**The first render** — [`render.md`](render.md), `tools/view.py`. A map
loaded, composed and drawn textured in OpenGL 3.3. `d_1_1_1` comes out at the
first attempt; `field_16` is recognisably the game's overworld.

And the measurement, not the anecdote: `view.py sweep` loads **everything**
drawable on the disc — 627 files, 5,297 sections, **54,176,753 vertices**,
30.9 M triangles in **14 seconds** — and resolves 1,903 texture references of
1,905. The two missing are production leftovers (`SouthPeak_Logo.ifl` is a
3ds Max *Image File List*: it says what tools the assets were made with).

Three things learned by looking:

- **per-vertex colour is baked light** — moss green with the edges going to
  black — which confirms by an independent route that the channel order is
  RGBA, and warns the host not to multiply twice what is already baked;
- the maps **include the ceiling**: a dungeon from above is a slab;
- decoding vertices with numpy instead of a dictionary per vertex is the
  difference between 14 seconds and unusable.

**Skinning, solved.** 50,043 vertices of 54 million were missing — 0.09% — and
it was not a counting error: they were the 77 meshes of `Opening.ps3.dsb` that
no node references directly. A node can reference a **`skin`**, which names
the mesh at +0x20 and carries an array of bones (node index + **inverse bind
pose**) at +0x60. See [`format_dsb.md`](format_dsb.md) §skin.

Two more items of the previous TODO fell with it: vertex **semantic 9** is the
**bone index**, and skinning is **rigid** — there is an index but no weight. A
clean oracle decided the matrix convention: `world(bone) @ Mᵀ` comes out
identical for every bone of a skin, so it is the bind pose; the other three
combinations do not.

And a trap to remember. With the *node* transform the opening scene looks like
a 3D village with a few pieces out of place, that is "almost right". With the
bone matrices it **flattens**, and looks like a mistake. It is not: the chain
passes through `oka_s-node` (Y scale 0.04) and `Dummy_2D_pos-node` — the
opening is a **2D backdrop seen from above**. The almost-right result was the
more deceptive of the two.

**YEBIS post-processing** — `tools/post.py`, documented in
[`render.md`](render.md). The four effects the vendor names are four passes:
defocus by circle of confusion, additive glare from the bright pass,
vignetting, colour modification. The parameters come from the **202 DOF
calls** counted in the scripts (`SetParamDepthofField`: first argument
0.37–3.02, second 0.20–1.50, third always 0; `SetDofApaerture` is at 0.70 in
14 cases of 20). The unit of those numbers remains unknown: they are not world
distances, and the answer is in the EBOOT.

A find in passing: `createFairyGlareEffect(38.27, 2.68, -23.2)` takes no
effect parameters, it takes a **position in the world**.

With the chain on, `field_16` stops looking like a 3D model and starts looking
like a diorama.

**The first dialogue** — [`host.md`](host.md), `tools/host.py` +
`tools/font.py`. The milestone that validates the project's thesis: a map from
the `.pac`, the script `Devil.lua.eu` run **verbatim** on a Lua VM (`lupa`,
Lua 5.5), a coroutine scheduler, and the line on screen in the game's font.

```
377 event scripts of 378 run, 377 reach the end, 0 errors
128 distinct methods, 6,634 calls — 20 methods make 76% of the calls
```

Getting there takes two things that are not obvious: **loading the shared
libraries** (`Event/eventfunction.lua.eu` defines the Lua functions the events
call, and the package manager loads them first), and **callable stubs**,
because a permissive table that does not answer `__call` kills the script at
the first unknown function.

**22 methods implemented of 128 used, covering 63% of the calls** — all of the
top ten, 12 of the top twenty. Besides dialogue and choices there are now
**camera** and **focus**, which the measurement pointed to as the real bulk of
an event: `SetCameraAtBody(distance, elevation°, azimuth°, target)` frames the
shot, `SetParamDepthofField` and `SetDofApaerture` drive the YEBIS chain, and
the two stacks `BackupCamera`/`RestoreCamera` and `BackupDof`/`RestoreDof`
leave the scene as it was.

The authors gave the signatures away without meaning to: two helpers in
`eventfunction.lua.eu` are commented "NPC camera from the right" and "from the
left", and between the two **only the sign of the third argument** changes. So
the third is an azimuth, and the first two are distance and elevation.

Three suspension conditions are enough for the whole corpus: `Wait`,
`WaitContinue`, `WaitScene`. The native globals (`EventClass`, `soundList`)
are defined by no script — the C++ supplied them — and here they become
permissive tables that remember their own name: `soundList.SoundID.SE_quake`
evaluates to its own string, which is enough to run and to record what is
needed.

Two finds in passing: the corpus has **mixed encodings** (13 scripts in
Shift-JIS among 365 in UTF-8), and the font atlas **has no hyphen** — the game
writes `ＴｈーＴｈａｔ` with the katakana prolonged-sound mark.

### Water is drawn — [`render.md`](render.md), `view.py water_parts()`

The texture was there, and where it made sense for it to be:
**`data/shaders/water_col.dds`**, one of only two loose `.dds` on the disc,
together with `Sun.dds`. Sitting in `shaders/` rather than in a map package is
the declaration that it belongs to no map: the engine draws it.

It is 128×128, uncompressed, a midnight-blue lattice of **16 squares per
side** — the sixteen dots of a cell, so one copy is laid per cell and the
lattice lines up by itself.

The height is declared nowhere, but the world pins it from both sides: the
backdrop is exactly two cells below the shore (52.9%) and the shore is at 0.00
(50%), so in between there is **only one multiple of a cell**. Each body of
water takes its own by propagating the minimum from its shores, so in
`Field_16` the mountain lake stays at +11.2 while the sea is at −2.0.

```
map cells covered by geometry: 436,043/480,731 = 90.7%
  of which water, now drawn:            40,964 cells
  still black in a frame:                8,503 cells = 1.8% of the map
```

`Field_16` is an island in the sea and `Field_31` an archipelago; before, they
were islands in nothing. The black that remains is real void — cells with no
geometry *and* no backdrop — and it is no longer an area but holes.

A find in passing in the same folder: `graphics.ps3.tpk` contains `ref_01`,
which is a **CUBEMAP** — the environment map that `renderer.md` lists as
missing.

### The system screens are composed — [`ui.md`](ui.md), `tools/ui.py`

The 137 UI descriptors had been read for three sessions and never run. Now
**119 screens** are composed: the scene in its place, the text where the
descriptor puts it, the cursor where it says.

Two measurements made it possible to compose rather than rasterise:

- **there is only one virtual screen.** That the descriptors spoke in
  1280×720 was known; that the **3D scenes** lived there too was not. The
  full-page fade measures `x [0, 1280]`, `y [-720, 0]` to the decimal, and Z
  is not depth but the overlay plane (−90 the fade, 0 the front).
- **the interface is made of rectangles**: of the 16,494 triangles of the 115
  scenes, 16,492 are flat in Z and **16,494 of 16,494** have two sides on the
  axes.

And the reason nobody had run them in three sessions: **at rest they are
closed**. The node of every piece of `SelectA` has scale **0** on one axis
while the mesh under it is whole (149×99), and the sliding screens park their
pieces off screen — the items menu reaches `x=2193`. What opens them is the
`Animation` the descriptor declares; the `.dsb` has no curves, so the engine
supplies the motion and the final pose is scale 1
(`view.load(unfold=True)`).

---

## Method that has worked

It bears repeating, because it solved five formats in a row: **use the
constraints the format itself provides as the test**, instead of guessing.

- `TPKG`: DXT3 against DXT5 was decided by looking at the alpha channel
  decoded both ways. The wrong interpretation produces regular horizontal
  bands.
- `DSBF` vertex: the sum of the declared sizes must give *exactly* the
  stride, which the chunk declares by another route (`vb_size / n_vert`). Two
  independent fields that must agree: 8,707 of 8,707.
- `DSBF` positions: they must **fill** the record's bounding box, not merely
  fit inside it. And the composed scene must fill the header's, which tests
  the hierarchy, the quaternions and the scales in one go.
- `MAP_ALIGNMENT`: in a format of **variable-length records**, walking the
  file to the end is the best oracle there is. If the layout is right you
  finish *exactly* on the last byte after the expected number of records. 170
  files of 170.
- **UDF**: the descriptor chain always says where the next thing is. There
  was nothing to guess, only to follow — and whoever guesses stops at the File
  Set Descriptor, as `pycdlib` does.

Corollaries, paid for in the field:

- When a test gives **0% under every interpretation**, it usually does not
  mean "wrong hypothesis" but "you are reading the data in the wrong place".
- When a reference does not resolve and the "unknown" values are **small and
  ordered**, it is not a hash: it is an index. That holds for the node
  hierarchy, and it holds for the mesh index inside the `skin` record.
- When the data has a **property expected a priori** — a map graph can be
  walked in both directions — that property measures the quality of the
  extraction.
- **A residue of 0.09% is information, not noise.** The 50,043 vertices that
  were missing from the count were not a counting error: they were the whole
  skinning subsystem, which opened only because the total did not add up.
  Making the numbers balance *exactly* is what makes the rest visible.
- **Before deferring to the EBOOT, look at the file names.** The archetype →
  model table was at the top of the TODO as "the first thing to ask Ghidra".
  It was in the names of the 237 scripts `npcevent_n<NN><archetype><id>`: in
  the clear, in a directory already extracted. It is a corollary of a rule
  the project already has, *look for the field that declares the layout*. A
  file name is a field too.
- **When a conclusion is already written in the documents, the test still has
  to be run again.** That the sections of a `.pac` were already positioned was
  documented, argued from three observations and confirmed by the image. It
  was false, 23 times over. The three observations were all *true*; what was
  wrong was the inference from the fact to the cause. 79% of vertices
  identical between neighbouring sections is what you get when a dungeon is
  built from repeated blocks and each screen is drawn around its own origin.
- **The good test comes from a file that has nothing to do with it.** The
  composition of the maps could not be checked inside the `.pac`: any reading
  is self-consistent there. `MAP_ALIGNMENT` decided it — another file, with
  another purpose, written in the only other endianness on the disc, which
  declares for reasons of its own where there is map and where there is not.
- **A sign is an oracle.** The six-argument signature of `SetCamera` fell on
  a detail: the second argument is −17.72 in one call, and a negative
  distance does not exist. Nothing more was needed to know that reading was
  wrong, and that an elevation belonged in its place.
- **Two weak oracles that agree are worth more than one strong one.** The
  four directions were decided where a mechanical statistic (who turns and
  then walks) met a hand reading of a dialogue. Alone, the first gave 75% on
  one cell and nothing on the others, and the second was an anecdote.
  Together they leave no way out, because they are wrong in different ways.
- **An oracle at 55% is not "almost right", it is noise with a preference.**
  "The NPC faces the player" looked like an obvious premise, and it
  confidently proposed a wrong mapping. The threshold is not "better than
  chance": it is "sharp enough that it cannot be anything else".
- **A name coincidence is not a resolution.** `Event/Priest/Priest.ps3.dsb`
  exists, is named like an NPC, and is not that NPC. What said so was not the
  name but the measurement: 0.64 high where a character is 1.60.
- **The "almost right" result is the most dangerous one.** Skinned meshes
  drawn with the node's transform gave a plausible 3D village with a few
  pieces out of place — an error that would have been filed as a detail. The
  correct reading flattens the scene, and it *looks* wrong. It was not the eye
  that decided but the determinant of the matrix, which led back to two nodes
  in the chain called `oka_s` (Y scale 0.04) and `Dummy_2D_pos`. When an image
  convinces and the numbers do not, the numbers are right.

- **A leftover that is an exact multiple of a known structure says where the
  error is.** The first walk of the `EDT` stopped 24 bytes before the end, and
  24 is exactly six floats, that is the tail of a part. There was no need to
  search: recognising the number was enough. *When the count does not add up,
  look at how much it is off by before looking at where.*
- **What only we need is not declared.** Where a room begins and ends is not
  on the disc, and three independent roads confirm it (the screen at 95% but
  not aligned, the tag that turns out to be the dungeon, the nearest marker at
  75.7%). It is not missing data: the engine has no use for the region,
  because to register entering a room a **trigger** is enough — and that is
  why the observers are sparse and two in three sit inside the solid instead
  of on the floor. *Before searching long for a piece of data, ask whether the
  game needed it.*
- **When two things that should differ come out identical, the field that
  tells them apart is one you are not reading.** The three rooms
  `room_on_02`, `room_off_02` and `room_still_02` came out identical pixel for
  pixel, and it looked like a broken filter. The filter worked: the three have
  the same mesh, the same position, the same UVs and the same texture, and
  what tells them apart is the material's `diffuse` — 1.0 / 0.5 / 0.0. *A
  difference of exactly zero is not a bug in the comparison: it is the
  statement that you are looking in the wrong place.* It is the twin of the
  session 6 corollary — data that looks empty may only be closed — taken the
  other way round: a piece that looks on may only be switched off.
- **A beautiful pattern needs checking more than an ugly one.** The seven
  black holes of the dark tower, one per floor, with the first digit of the
  passage running 1-2-3-4-5-6-7: it seemed obvious that they named the seven
  temples, and it is what *a designer would have done*. Zero of seven. It was
  the number of the floor the cell is on — the boring explanation, which was
  then measured at 99.8% over 2,490 cells. *When a reading is elegant and
  tells the game's story well, that is exactly where to ask for the bill.*
- **A recognisable result can be recognisable and wrong.** The first contact
  sheet of the `EDT`s showed ninety characters, every one identifiable, and
  the check seemed to have passed: they all had **their backs to the camera**.
  The one who saw it was someone looking without knowing what to expect, and
  the defect was a choice never made — which of the two Zs is the front.
  *That something is recognisable says the chain holds, not that every
  convention inside it is the right one; and conventions nobody chose do not
  give an error, they give a mirrored result.* The fix then yielded a
  measurable property (9 voxels in front against 40 behind) and a third
  confirmation of "authored facing −Z".
- **Someone who does not know what they should see is an independent
  oracle.** The model `c_enm_01_01` was shown to someone who knew neither its
  name nor the state of the chain that draws it, and the first word was
  "rabbit". The descriptor calls it `Killer Rabbit` and the Japanese comment
  ツノウサギ, horned rabbit. It counts because it **is wrong in a different
  way** from the numerical checks: those say the bytes add up, this says the
  thing *means* what it should. And it counts because it was blind. Looking
  at the same image already knowing the answer, you see a rabbit in anything,
  which is exactly how the "almost right" skinning render had passed for
  good. *When a long chain produces something recognisable, have it
  recognised by someone who does not know what to expect.*
- **A name coincidence is not a resolution, even when it is ours.**
  `data/Balloon` was in the TODO as "the original of the dialogue box", and
  it is the `CHECK`/`TALK`/`OPEN` sign that floats above a head: 1.6 × 0.6
  **world units**, not pixels. It is the same error as `Priest.ps3.dsb`, but
  made by us and then written into the documents, where it waited for three
  sessions. Looking at the unit of measure was enough to refute it. *The
  TODO's items are not verified results: they have to be tested like
  everything else.*
- **A field that never varies is not the field its name says.** `Start` was
  read as the start of the clip on the timeline, and it is 0 in all 36 `In`, 1
  in all 33 `Main`, 2 in all 36 `Out`. A time determined by the name is not a
  time: it is an index. *The first thing to ask of a numeric field is how much
  it varies; if it is constant per class, the name is lying.*
- **Two missing ends are not the same problem as one.** "The animation is
  missing" was a single item and it held two things. The opening, for which
  the disc has the closed pose (scale 0), the open one (the whole mesh) and
  the duration — so it can be rebuilt without inventing anything; and the
  scrolling, for which it has only the parked position. Interpolating needs
  two ends, and separating them shrinks the question for the EBOOT from "the
  screens' animation" to "where 15 pieces land in 5 screens".
- **A hole in the data can be a hole in the walker.** `Option`'s indices
  jumped from 9 to 20, and it looked as if the disc did not declare ten clips.
  It did: `Volume` is an **array** instead of a dictionary, and a walker that
  only descends into dictionaries skips it. That the hole was exactly as wide
  as the scene's ten `Volume00…Volume09` nodes was the clue, and it was
  visible before the cause was found. *A hole of suspiciously meaningful size
  should be looked for in your own reader before the data.*
- **A control has to be measured together with the oracle, not after it.**
  "The pivot puts the growth edge on the origin" gave 87.3%, which looks like
  a result. The same test giving 76% on the full-scale pieces says it is not.
  Without the control it would have gone into the documents as a reading of
  the format, and it was nothing but the way a scale works.
- **Data that looks empty may only be closed.** The system screens composed
  black, and it looked like a defect in reading the textures or the UVs. The
  geometry was all there: what hid it was a **zero in a scale**, and the rest
  pose of an interface is the closed pose. Before looking for what is missing,
  check whether what is there has zero volume.
- **Where a file is *not* is as much information as what it contains.** The
  water texture is in no map package and no character package: it sits loose
  in `data/shaders/`, together with the sun. That folder says "the engine
  draws this", the same thing the `destructionWall` absent from the `.pac` and
  the backdrop absent from the drawing were saying. It is worth looking at
  *where* things are before asking what they contain.
- **If a declared thing is in none of the files that describe the world, it
  is not a reading defect.** The `destructionWall` is not in the `.pac` and
  not in the `.DPK`: 0% and 0%. Looking harder would have been wasted, because
  the absence *was* the information. The engine builds that wall at runtime,
  and indeed the Lua has `AT_DESTRUCTION_WALL` among its 33 actor types. It is
  the same form of reasoning that had already given the skinning, but in
  reverse: there a residue of 0.09% was a subsystem, here a clean zero is a
  statement of architecture.
- **An experiment that gives zero should be reported all the same.** Opening
  every breakable wall gains **not one cell** over 78 maps, and knowing that
  the world behind them was already reachable is worth as much as a gain: it
  says the 33% not reached lies elsewhere.
- **A rule made symmetric out of caution has to be tested like the others.**
  Climbing and descending one cell was a single choice, made so as not to
  walk down off roofs. Tested on its own, descent saturates at once: 257
  inhabitants with a limit of one cell and with no limit at all. The caution
  was right, but now it is a result.
- **A cautious limit is an invented number like any other.** The cap of 96
  subdivisions in the seeding had been set so as not to blow up memory, and
  it looked like the careful choice. On a third of `FIELD_07`'s triangles it
  made the sampling step wider than a cell — exactly the damage the seeding
  was there to prevent. Removing it costs 27%. *A cap set out of caution has
  to be measured against the thing it must guarantee, not against the fear
  that suggested it.*
- **Fixing a wrong reading can make the measurement worse, and that does not
  mean the fix was wrong.** Putting the levels below zero back took the cells
  reached from 63% to 41%. The first instinct — go back — would have restored
  the number and kept the defect. What had happened is that the recovered
  level was the **backdrop**, and finding that out then gave the water mask
  for free. *A right correction can uncover a second defect the first one was
  hiding; the measurement goes down because it is now looking at one more
  true thing.*
- **Before choosing between two explanations, count.** "The backdrop has
  ground above it" looked like the obvious way to recognise it: it ranges from
  30% to 83% with no break, so it is not a criterion. The count that does
  decide is a different and banal one — there are 163,878 two-level cells,
  and in only 758 of them is the lower level not the minimum height — and it
  also says something about the world: the gallery above the hall exists, and
  it is 0.16% of the game.
- **A single entrance measures the entrance, not the map.** `field_14` has
  six doors, and the first opens onto a 16-cell shelf below a cliff. When the
  data declares several access points, trying one and reporting the
  percentage is a measurement error dressed up as a result — and it shows,
  because the distribution has a tail of maps at 0-3% instead of tapering
  smoothly.
- **Two neighbouring names for two different things lead to false
  conclusions.** "Water and void" was a single item, and from it came the idea
  that the region tag changed by group of maps. Separate them — water is where
  the backdrop is the only surface, void is where there is no collision at
  all — and water has a single tag across the whole disc (`119`, 88%) while
  void has none, because it is not something anyone declares.
- **An invented number survives until someone tests it.** Of the whole
  walking system, only one value did not come from the data: the step, "a
  knee", 0.6. And it was the only wrong one, by almost a factor of three. It
  produced a symptom that looked like something else entirely (maps broken
  into islands, and the overworld much worse than the dungeons) and a
  plausible, false diagnosis ("geometry is missing"). When a measurement is
  low, the first suspect is the parameter that has no source.
- **The quantum before the calibration.** The step did not need calibrating,
  it needed recognising: ledges are exact multiples of one cell, and between
  1.7 and 2.5 not a single number changes. If a threshold has a flat interval
  as wide as the quantisation step, that threshold is not a choice.
- **A second oracle that saturates is worth more than a distribution.** That
  ledges are multiples of 1.6 says how the world is built, not what the
  player can climb. What decided it was an oracle of a different nature: the
  **inhabitants** the map declares are places the game must be able to reach,
  and their count saturates at exactly one cell.
- **Geometry declares surfaces, not volumes.** Inferring the solid from the
  vertices works only by looking at which way they face: a solid block has
  vertices only on its faces, and the underside of a floor looks like a floor
  with free air above it. Count both and you walk inside the rock, and the
  symptom — maps broken into islands — looks like a threshold problem. It was
  not: it was a normal.
- **A list of "the ones that do not have it" ages with the census that
  produced it.** The six `WiseMan` were on the list of extras with no declared
  model because that census started from the names used by the *event*
  scripts, and the sages speak almost only through their own. When the source
  changes, the list of what is missing has to be redone, not inherited.
- **Before choosing a starting point, look at what class it is.** `arrivals`
  held every cell with a `-g` — hundreds of observers and gimmicks — and
  starting from the first one began the game on top of a wall, with two
  reachable cells. The entry point has a name in the data: `Exit`.
- **A host that measures is worth more than a host that stops.** Every
  unimplemented method is counted instead of raising an error, and every
  missing native global becomes a table that remembers its own name. So the
  order of implementation does not have to be guessed: it is read.
- **But the measurement has to be redone after every implementation.** It was
  wrong twice running, in two different ways. First: a Lua error ended the
  coroutine, and an ended coroutine was the criterion by which I counted
  completions, so errors counted as successes and "376 of 378" was really 89.
  Second: `Select` came out third with a thousand calls, because a script that
  repeats the choice until it gets an answer spins idle if `Select` never
  answers, and every spin counts; implemented, it makes 56 calls and comes
  twenty-fifth. **The measurement of an API's use is distorted by precisely
  the pieces you have not built yet.**

- **Looking for something and not finding it is a result, if you looked in
  every place.** Enemy patrolling is not in `MapParameter`, not in
  `GameParamData`, and the Lua API for enemies has only `PlayEnemy`,
  `PauseEnemy`, `visibleEnemy` — freeze and show, never move. Put that way,
  "it is not there" stops being a surrender and becomes the reason the next
  move is a **decision** (invent it, and declare it) rather than a search.
- **The file opened for the wrong reason pays off all the same.**
  `MapParameter` was opened to look for the enemies' motion, which is not
  there, and it declares the names of 211 maps — data the game loop had been
  waiting for for eight sessions without anyone looking for it, because nobody
  knew they wanted it.
- **A stand-in has to be measured again when the real data arrives.**
  `LivingId` was "where an enemy lives" until the placement could be read.
  Now it can, and the comparison gives 47%: the habitat is a classification,
  not a location. *The stand-in does not become false when the data arrives:
  it turns out it was not the same thing, and whatever had been inferred from
  it has to be rewritten.*
- **A game's secondary mode can be the only place where the main mode is
  written in the clear.** The world's enemies are C++, but twelve of them also
  exist as Lua actors in the minigame, with their poses, their period and
  their type of motion. It is not a copy: they reuse the models **by number**,
  and the names confirm it twelve times of twelve. *When the main piece is
  compiled, look for a secondary piece that reuses it — the side mode, the
  editor, the minigame, the tutorial.*
- **A constant of ours survives until a file names it.** The period of the
  walk cycle was 0.25 because it came out of an `int(walk * 4) % 2` written to
  get two steps a second: nobody had chosen it, and nobody had questioned it.
  The disc declares it twelve times and it is 0.3. It is the twin of session
  5's step, but more insidious, because 0.25 produced **no** symptom.
- **A generalisation from the common case is exposed by counting the
  cases.** `02_a`/`02_b` was "everyone's" walk cycle, because all 31 NPCs have
  it. Among the 37 enemies **twelve do not** — four use `04`, eight have no
  pairs — and for that third the code asked for a pose that does not exist,
  without an error: it fell back to the first frame and the enemy stood still.
  *Before writing down a constant taken from the case in front of you, count
  over which population you saw it.*
- **A hypothesis becomes refutable only when the data that measures it
  arrives, and then it has to be measured at once.** "The enemies with no
  floor are the flying ones" had been written as the motivation for an
  implementation choice, and it seemed obvious. The minigame brought the
  `Type` field, and the count says 2.3% against 4.0% — if anything, the
  opposite. *A plausible motivation written in a comment is an unverified
  hypothesis dressed up as an explanation.*
- **An external source is wrong in a way all its own, and that is why it is
  worth having.** A walkthrough is written for playing, not for reading
  bytes: it knows nothing of our fields and cannot agree with us to be
  polite. Four readings inferred from the bytes alone turned up in it without
  being looked for — the placement sets, FROM Mode's profile, the two enemies
  with no habitat, the eight bosses with their temples. It is the same form of
  proof as session 7's "rabbit" — someone who does not know what they should
  see is an independent oracle — but on a scale a single image does not reach.
  *When a reading concerns what the player experiences, there is already a
  literature describing it from the other side of the screen.*
- **An "unknown" field can be the field that holds everything else
  together.** The cell's +0x10 had been marked `?` for five sessions while
  three censuses — map objects, enemies, NPCs — were kept apart because they
  looked like three problems. They were one numbering. *Before opening a new
  front, count how many fields already read are still without a name: a `?`
  in a structure that is walked end to end is not a hole, it is work not
  done.*
- **A name that does not find its file may be a function.** "22 names of 25
  have no script of that name" was in the TODO as a negative result, and the
  search was looking for files. `gimmick_grass4` is a function inside
  `gimmick_grass.lua.eu`, and searched for as functions they resolve 25 of 25.
  It is the twin of the corollary "a file name is a field too": *so is a
  function name, and the level at which a piece of data names something has
  to be chosen, not assumed.*
- **Two subsets of equal size that never touch are the same set.** `A`, `B`,
  `C` have the same species, almost the same counts, and zero cells in common
  across the whole disc. Each of those facts alone can be explained in many
  ways; together they leave one. And the measurement that settles it is the
  *geometric* one: if they were squads their boxes would be small and
  separate, and instead they are 88% the same box.
- **The irregular case should be kept, not normalised.** `F`, `G`, `H` break
  the parallel of `A`, `B`, `C` — more cells, more species, different counts
  — and the temptation was to read them as a second, identical triple. The
  break is what identifies them: that asymmetry *is* the description of FROM
  Mode.

And the most general moral: before inferring a layout, **look for the field
that declares it**. That holds for scripts too: `Font.lua.eu` declares the
whole font, and the VM reads it better than any parser of ours.

## Environment

- `extract/` is rebuilt with `python tools/iso.py extract` and checked with
  `verify --deep`. Since session 14 **every set is extracted**, `audio` (326
  WAV) and `movie` (5 Bink) included: the recompiled game loads its sounds
  while the logos play. It is kept out of git under the BYOA policy; the
  manifest is not.
- The recompiled game: `build/eboot.elf` (from `tools/self.py`, with a key
  file kept outside the repository: here PC-ROA's copy of RPCS3's
  `key_vault.cpp`), `build/recomp` (the generated C++), `build/recomp-build`
  (CMake + Ninja + clang 22 from MSYS2's `mingw64`, which must be on `PATH`
  for the build and for SDL3 at run time), `build/flash`, `build/hdd0`,
  `build/hdd1`. All of `build/` is ignored.
- `ps3kit/` is a submodule (`git submodule update --init` after a clone).
  Under gdb, pass `-ex "handle SIGSEGV nostop noprint pass"` before
  `-x ps3kit/gdb_trace.py`: the kit's write tracking faults on purpose.
- A leftover to clean up: `data/map/pac_data` still holds the 167 `*_PAC.GZ`
  with the truncated names from the old 7-Zip extraction, 441 MB of nothing.
  The correct `.pac.gz` files are beside them.
- 7-Zip exits with **code 2** and `Headers Error` on this ISO. It is benign:
  it is the region table at the end. But it extracts with the ISO9660 names,
  so use `iso.py`.
- Available: Python 3.14 with Pillow, numpy, **pyglet** (OpenGL 3.3) and
  **lupa** (the Lua 5.5 VM, installed in session 3 — it is Phase 4's
  dependency), plus 7-Zip, ffmpeg, ImageMagick.
- Tools: `iso.py` extraction, `tpk.py` textures, `dsb.py` scenes, `mapdat.py`
  the world graph, `dpk.py` collision, `view.py` + `post.py` rendering,
  `font.py` fonts, `edt.py` voxel characters, `host.py` the Lua VM and
  scheduler, `entity.py` the entity registry, `walk.py` the game loop.
- `docs/walkthrough/` is a GameFAQs guide saved locally (7 pages, 325 kB of
  text extracted into `walkthrough.txt`). It serves as an **external
  oracle**: it describes from the other side of the screen the same things we
  infer from the bytes. It is not in git; it is third-party material.
- The checks that run by themselves: `python tools/entity.py` (49 properties,
  with the bestiary and the actor identifiers),
  `python tools/walk.py` (31 properties, on all 170 grids, with the placed
  enemies and the event triggers),
  `python tools/view.py sweep ../extract` (54,176,753 vertices, 1,903 textures
  of 1,905), `python tools/view.py layout` (99.3% of the solid cells, 1.8%
  still black),
  `python tools/view.py walkabout` (167 maps walked on foot, 97% of the
  inhabitants reached, 365 passages of 369 with a standable arrival),
  `python tools/dpk.py check` (171 files of 171),
  `python tools/edt.py check` (6 properties, 90 files, 260,860 voxels),
  `python tools/ui.py check` (14 properties, 119 screens),
  `python tools/host.py coverage ../extract/PS3_GAME/USRDIR/data/Event` (87%).
- `docs/lua_signatures.*` and `docs/lua_tables.*` are in `.gitignore`: they
  hold the game's dialogue and tables. The tools regenerate them in a few
  seconds.
