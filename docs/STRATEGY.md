# PC-3Ddot — strategy

*Phases 1-5 aligned to the end of session 13 (2026-08-20); the pivot below
to session 14 (2026-10-23). Detail and priorities live in
[`TODO.md`](TODO.md); this document is the frame.*

Goal: *3D Dot Game Heroes* (From Software / Silicon Studio, PS3, 2009), the
European release BLES00875, running natively on PC **as the original game**.
Distribution is BYOA: the player supplies their own disc, the repository
ships code and documentation.

Since session 14 the road there is a **static recompilation** of the game's
own executable onto a runtime that stands in for the PS3,
[ps3kit](https://github.com/vs-sr-dev/ps3kit), shared with the sister
project PC-ROA. Sessions 1-13 were a native reimplementation driven by the
disc's Lua, and everything they read stays: see
[the pivot](#the-pivot-static-recompilation-session-14).

## The road taken in session 1, and why

Decided in session 1 (2026-08-09): **a native reimplementation driven by the
Lua**. A PC engine that exposes the same scripting API and reuses the disc's
Lua scripts *verbatim*, with the EBOOT as a reference oracle, never as code
to translate. The models were Ship of Harkinian, OpenGOAL and devilutionX.

The reasons against static recompilation of the PPC64 executable, as this
document gave them for thirteen sessions:

> On Xbox 360 it works well (XenonRecomp) because the GPU is close to D3D9.
> On PS3 the RSX would need a substantial HLE layer, and the result would be
> an opaque, unmoddable binary. Here we have an advantage that road would
> throw away: 100% of the game logic is already readable source.

The next section is why they stopped holding.

## The pivot: static recompilation (session 14)

**The reimplementation had the logic for free and the engine to write, all
of it.** After thirteen sessions the game was walkable in the viewer: maps
with their inhabitants, the passages between them, dialogue, 312 of 312
enemies running their own script, menus that navigate, map objects, the
light the disc declares. What was left was the engine under the scripts:
combat ("a subsystem that does not exist"), what a menu choice leads to (2
links declared of 136), the 1xxx band of cells, the torches, and 108 of the
161 actor methods the scripts call (20.8% of the calls). Each of those is a
piece of an engine the disc does not ship as script, rewritten by hand one
function at a time, which is the same bill the sister project PC-ROA had run
up to 69,691 functions when it changed road in its session 33 (2026-10-11).
A recompilation is the original by construction, and its questions are what
the console does, which every PS3 game shares, not what this game does.

**The three reasons above, measured on this EBOOT** (the census is in
[`eboot.md`](eboot.md)):

1. **"The RSX would need a substantial HLE layer."** It exists, in ps3kit,
   and PC-ROA paid for it: a FIFO consumer, a renderer on OpenGL 4.5 that
   translates the RSX's vertex and fragment programs to GLSL, textures,
   surfaces, flips. Session 14 asked it for three things this game does and
   ROA did not — the I/O map (`cellGcmMapEaIoAddress`), reports, and inline
   image transfers through the FIFO, which is how this game puts its
   fragment programs into local memory — and the publishers' logos, From
   Software's and Silicon Studio's DAIKOKU and YEBIS, were drawn the same
   day.
2. **"The result would be an opaque, unmoddable binary."** Any recompiled
   function can be replaced by C++ written by hand. And the game logic was
   never the binary's: the scripts run on **the game's own Lua 5.1.3 VM**,
   inside the EBOOT, instead of on ours (the host of sessions 1-13 used
   Lua 5.5). One caveat, found in session 14 and still open: the EBOOT
   carries its own copy of the scripts, 1,488 sources, 112 of them different
   from the disc's `all.lua.eu`. In the first 90 seconds of a run the game
   opens no `.lua.eu` from the disc. If it runs the copy in the executable,
   modding the scripts means patching that copy, or redirecting the loader
   to the disc's; *which one it runs is a measurement still to take*.
3. **"We would throw away the advantage: 100% of the logic is readable
   source."** Nothing is thrown away; it changes role. Everything sessions
   1-13 read becomes documentation, BYOA tooling and **an oracle**: the
   walkabout measures, the 312 enemies, the menus, the light are now things
   to compare with the recompiled game running. The open questions (combat,
   what a menu choice leads to, the 1xxx band, the torches) are answered by
   the original itself.

**The census said the same.** 20,672 PPU functions, a quarter of ROA's, in
2.73 million instructions with almost no vector code (1,600 VMX
instructions); 237 imports in 25 libraries, every one named; 77 lv2 call
numbers; **638 switch tables, all resolved**. What this game has that ROA
did not is the SPUs: **26 SPU ELFs** (Bullet's collision and solver, FMOD's
mixer and its 19 effect and codec modules, Edge zlib, two water tasks) on
SPURS task sets and an lv2 SPU thread group, where ROA had only SPURS jobs.
That is what this game teaches the kit, as ROA taught it the PPU and the
system.

**What session 14 measured, running.** The recompiled game reaches its first
flip, then draws the publishers' logos at 60 frames, with FMOD's SPU mixer
running as an SPU thread group and a SPURS task (`water_task`) waiting on its
event flag. To get there the kit learned: SPU ELFs recompiled at their load
address, lv2 SPU thread groups, SPURS task sets, tasks and event flags,
`spu_printf`, two switch-table shapes, the I/O map, reports, inline
transfers, audio notifications, `/dev_flash` and `/dev_hdd1`. After the
logos the game checks for its save data, finds none, and stays on a black
screen: that is where session 15 starts. See [`TODO.md`](TODO.md).

**How the kit is shared.** The kit grew inside PC-ROA and moved to its own
repository, with its history, when this port started (session 14). It is a
submodule at `ps3kit/` here and in PC-ROA, and it stays free of both games:
what is this game's knowledge lives in this repository. The first piece of
it is [`tools/flash.py`](../tools/flash.py), a declared stand-in for the
system's MP3 decoder that FMOD reads from `/dev_flash`. Every change to the
kit is checked on PC-ROA too, which must still reach its logos, movie,
title, character creation, town and first quest at 30 frames.

**The generated C++ is the game's code, translated, and is never
committed.** It is built from the player's own disc, like everything else
here.

---

## Phase 1 — Foundations (no engine code)

All static analysis, all automatable, no dependency on the EBOOT.

- **1a. Official extractor.** ✅ **done** — `tools/iso.py`, a UDF reader of
  its own (PS3 Blu-rays use UDF 2.50's metadata partition, which `pycdlib`
  does not handle), declared sets, a manifest with `sha256`, and
  verification. `extract/` is a function of the disc. See
  [`extract.md`](extract.md).
- **1b. Signature inference.** ✅ **done** — `tools/lua_signatures.py`. 497
  methods on 8 host classes, 29,626 call sites; arity, type per position,
  use of the return value. Output: `docs/lua_signatures.md` and
  `generated/script_api.h`.
- **1c. Constant tables.** ✅ **done** — `tools/lua_tables.py`. 12 enums,
  2,216 members (`generated/script_enums.h`), and the declarative UI
  descriptors, **136 loaded and run** since session 9 (see [`ui.md`](ui.md)).
  Only `EventFlag` has its values in Lua; the other 11 enums are native, and
  their values were left to Phase 3.
- **1d. Clustering by domain.** The 497 methods grouped into subsystems to
  order the work. — *not done*, and `host.py coverage` gave what was really
  needed: not how many methods exist but how often each is called.
- **1e. The dialogue markup.** ✅ **done** — a complete census: 9 codes, no
  escapes, a closed language (RECON §6.4). `/r` `/b` `/co` `/cl` are certain;
  the `/v*` family remains a hypothesis.

## Phase 2 — Asset formats

| Format | N | Status | Notes |
|---|---|---|---|
| `TPKG` textures | 763 | ✅ **solved** | [`format_tpk.md`](format_tpk.md) — 4,033 textures, 0 errors |
| `DPK` collision | 171 | ✅ **solved** | [`format_dpk.md`](format_dpk.md) — 171 of 171 files end on their last byte, 301 meshes and 420,301 triangles, in the `.pac`'s frame of reference |
| `DSBF` scenes | 460 | ✅ **solved** | [`format_dsb.md`](format_dsb.md) — 1.61 M triangles from 460 of 460 files, materials and textures linked, skins and bind poses included |
| `.pac` maps | 167 | ✅ **solved** | [`format_pac.md`](format_pac.md) — 4,837 sections, 51.7 M vertices, the same parser; **composition** checked against the logical grid, **99.3% of solid cells** |
| `EDT` voxels | 90 | ✅ **solved** | [`format_edt.md`](format_edt.md) — 90 of 90 files end on their last byte, 260,860 voxels in a 16×16×16 cube; the six parts are six poses |
| `SAV` saves | 3 | open | no magic, but the same `u32 len + UTF-8` pairs as the `.edt`; they refer to presets **by path** |
| `MAP_ALIGNMENT` | 170 | ✅ **solved** | [`format_mapdat.md`](format_mapdat.md) — the logical grid and the world graph; field +0x10 is **the actor** |
| `spkg`/`CGB` shaders | 4 | not needed | the recompiled game loads them itself |
| Bink, WAV, DDS | 333 | standard | ffmpeg / direct |

## Phase 3 — The EBOOT

Planned as an oracle, never opened in thirteen sessions, and **opened in
session 14** as the input of the recompiler instead: [`format_self.md`](format_self.md)
(the container, with [`tools/self.py`](../tools/self.py)) and
[`eboot.md`](eboot.md) (the program). Its first readings answered two items
this phase had been keeping: the post-processing is Silicon Studio's
**YEBIS**, which the game itself shows on its logo screen beside
**DAIKOKU**, its shader pipeline; and no string in the binary names OROCHI,
so the engine hypothesis of session 1 stays a hypothesis. The engine's own
source tree is called `Block` (`c:/work/Block/Localize/program/src/...`).

The method note this phase carried still holds: several things deferred here
turned out to be on the disc in the clear (the direction values, the
archetype-to-model table, the enemy placement, the screens' input). Before
reading code, ask whether the fact is already declared, even in a file name.

## Phase 4 — Host (sessions 1-13)

The Lua host that ran the disc's scripts verbatim, now an oracle for the
recompiled game:

- the Lua VM (`lupa`, Lua 5.5): **377 of 378 event scripts run to their
  end**, with 43 methods covering 87% of the 6,634 calls. See
  [`host.md`](host.md);
- the entity registry ([`entities.md`](entities.md)), the game loop
  ([`walk.md`](walk.md)), the enemies in the map (10,196 placements, 312 of
  312 running their script, [`actor.md`](actor.md)), the system screens
  ([`ui.md`](ui.md)), the coroutine scheduler, the interface font, the
  package manager's 1,279-line symbol table and the map objects
  ([`objects.md`](objects.md)), and the viewer with the YEBIS post-processing
  rebuilt from its vendor's description ([`render.md`](render.md),
  [`renderer.md`](renderer.md)).

The milestones it reached, each one now a comparison to make against the
original running: **"the first dialogue"** (session 3), **"the scene"**
(session 4), **"the game loop"** (session 5, measured by `view.py walkabout`:
97% of inhabitants reached, 365 of 369 passages with a standable arrival).

## Phase 5 — Bring-up

Since session 14, bring-up is the recompiled game's: screen by screen, each
stop read and resolved in the kit (what the console does) or in this
repository (what this game does). The scripts are no longer a test suite for
our host; the readings of sessions 1-13 are the checks to run against the
original. The priorities are in [`TODO.md`](TODO.md), the first document to
read at the start of a session.
