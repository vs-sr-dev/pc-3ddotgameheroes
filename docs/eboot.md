# The EBOOT, opened as a program

*Session 14. [`format_self.md`](format_self.md) is the container and how it
decrypts; this is the program that comes out of it, measured with
[ps3kit](../ps3kit) before anything was recompiled. These are the numbers
the pivot in [`STRATEGY.md`](STRATEGY.md) rests on.*

PC-ROA's session 33 took a first census of this executable, outside this
project, from an ELF that was not kept. Every number below was taken again
here, from `build/eboot.elf` as [`self.py`](../tools/self.py) writes it:

```
python -m ps3kit.elf build/eboot.elf --imports --opd
python -m ps3kit.ppu build/eboot.elf --mix
python -m ps3kit.recomp build/eboot.elf --out build/recomp --spu-module-bias 0x15670 --spu-module-bias 0x18990
```

## The shape

```
entry descriptor 00FEF3F8
  r-x  00010000    16564704 bytes    16564704 in memory
  rw-  00FE0000     6006656 bytes    30494200 in memory
TLS (0x1079F40, 4, 500)
descriptors 25166, functions 20672
```

**20,672 functions with a descriptor**, as session 33 counted, and 3,095
more that only a `bl` reaches: 23,767 units for the recompiler. That is
**a quarter of PC-ROA's 76,648**, from an executable of about the same size
(22.6 MB against 19.8 MB), because segment 0 is not all code. The PPU code
runs from `0x10200` to `0xA799CC`, 10.5 MB; what follows it in the same
segment is read-only data, and two things in that data are this game's own
(below): 3.78 MB of Lua source and the SPU programs.

`ps3kit.elf` finds no process-parameter block by the name it looks for; the
runtime reads the same parameters from the `.sys_proc_param` segment and
reports them at boot (SDK `0x00300001`, primary thread priority 1001, stack
`0x10000`, malloc page `0x100000`).

## The PPU code

```
2729458 instructions, 179 operations
  stw 575356   addi 303495   lwz 291515   ld 213505   b 203775 ...
```

- **2.73 million instructions**, as ROA's 2.69 million: the two games have
  the same amount of PPU code in a third of the functions.
- **Floating point is the game's arithmetic**: 222,133 FPU instructions,
  8% of the code (`lfs` 61,992, `stfs` 53,183, `fmuls` 14,423).
- **The vector unit is almost unused**: 1,600 VMX instructions of 38 kinds,
  most of them `stvx`/`lvx` (copies). Three kinds were new to the kit
  (`vpkswss`, `vmulesh`, `vmulosh`, 24 instructions) and were added.
- 58 `lwarx` and 4 `ldarx`, 448 `sc`, no `dcbz`.
- **638 switch tables, all resolved.** 616 have the compiler's optimised
  shape; **22 are unoptimised code**, which loads the entry with `lwz` from
  a sum instead of `lwzx`. Eleven of the optimised ones put their bound
  check in a block reached by a branch, after a return. Both cases are now
  in the kit (below). Every table here sits in the code, right after its
  `bctr`: the 9,093 words that decode as illegal instructions inside the
  units are those tables' entries, which are never executed.

## The system interface

```
imports: 25 libraries, 237 functions, 237 named
```

**237 imports, every one named** from the kit's `nids.txt`. Against
PC-ROA's 306, 125 are shared and **112 are new**, in ten libraries ROA
never imported: `cellJpgEnc`, `cellPngEnc`, `cellPhotoUtility`,
`cellPhotoImportUtil`, `cellPhotoDecodeUtil`, `cellScreenShotUtility`
(this game has a photo mode), `cellMic`, `cellSysutilAvconfExt` (a
microphone), `cellGameExec`, `cellSaveData`. Of the new ones, the weight
is SPURS: **27 `cellSpurs` functions** — task sets, tasks, event flags,
queues, lock-free queues, a barrier — where ROA used only job queues.

When the census was taken, 88 of the 237 had an implementation in the kit
and 149 would answer as stubs:

| library | stubbed | of |
|---|---|---|
| cellSpurs | 32 | 32 |
| sys_net | 14 | 14 |
| cellSysutil | 12 | 24 |
| sceNpTrophy | 10 | 10 |
| sysPrxForUser | 10 | 27 |
| cellGcmSys | 9 | 31 |
| cellMic, cellJpgEnc, cellPngEnc | 8, 7, 7 | all |
| sys_fs | 5 | 19 |
| cellSysmodule, cellPhotoUtility, cellSysutilAvconfExt | 4 each | all |
| cellResc, cellGame, cellScreenShotUtility, cellPhotoDecodeUtil, cellAudio, cellNetCtl | 3 each | |
| five more | 1 each | |

The network (`sys_net`, `cellNetCtl`), the trophies, the microphone and the
photo and screenshot utilities can answer "unavailable"; SPURS, the SPU
system calls and the rest of cellGcm cannot.

**lv2 system calls**: 448 `sc` sites over **77 call numbers** (8 sites whose
number is not set within twelve instructions). 57 were in the kit. The 20
that were not are the read-write lock (120-127), `sys_time_get_timebase_frequency`
(147), the **SPU thread group** calls (156, 169-193, 251-252), memory
containers (324-325), `sys_tty_read` (402) and seven file-system calls
(810-834).

## The SPUs

**26 SPU ELFs**, embedded in segment 0 between `0xF56E80` and `0xFDC000`,
every one carrying its own `.note.spu_name`. No SPURS job binary (`JOBCRT`)
at all, which is the opposite of ROA, whose only SPU code was jobs.

| what | ELF | loads at | code | runs as |
|---|---|---|---|---|
| `water_task.spu.elf` | `00F56E80` | `0x3000` | 5,584 B | a SPURS task |
| `waver_task.spu.elf` | `00F58A80` | `0x3000` | 2,464 B | a SPURS task |
| `edgezlib_inflate_task` | `00F59A00` | `0x3000` | 35,696 B | a SPURS task (Edge zlib) |
| `PS3_SPURS_BulletCD_spu_release` | `00F63100` | `0x3000` | 173,792 B | a SPURS task (Bullet collision) |
| `PS3_SPURS_BulletSolver_spu_release` | `00F8E780` | `0x3000` | 29,696 B | a SPURS task (Bullet solver) |
| `fmodex_spu.elf` | `00F96580` | `0x80` | 66,880 B | FMOD Ex's mixer, *inferred* an SPU thread |
| `fmodex` (NeuralTHX build) | `00FA8100` | `0x80` | 38,544 B | the same, another build |
| 2 FMOD codecs, 17 FMOD effects | `00FB2780`... | vaddr + `0x15670`, + `0x18990` | | modules FMOD's mixer loads |

The 19 modules carry relocation sections (`.rela.text` and others), but
**every one of them is empty**: the code is position-independent, and FMOD's
mixer copies a module into local store as it is, with only its `.fixup` words
(data) patched. Where it goes was read off session 15's run: the PCM stream of
the title music loaded `fmod_codec_raw` (its two segments, `0x2DC0` bytes)
at LS `0x156F0`, its address `0x80` plus `0x15670`, and entered it at
`0x15888`, its entry `0x218` plus the same. Session 16's first cutscene
after the prologue loaded `fmod_dsp_sfxreverb` elsewhere, at LS `0x18A10`
(bias `0x18990`), alongside the codec: the mixer froze, and the runtime,
which now looks for the bytes at the target in every module's image, named
the module and its base. The recompiler translates all 19 at both biases
(`--spu-module-bias 0x15670 --spu-module-bias 0x18990`); another placement
will be reported the same way, its bias read off the report.
That a task links at `0x3000` is the taskset policy module's layout; the
"runs as" column is *inferred* from that and from the names, until the run
confirms it.

Where they are started from:

- SPURS, at `0x473000` (a system layer: a SPURS instance, a taskset, a
  task with an exit code, an event flag), `0x5CF000` (a second instance and
  taskset, an event flag a PPU thread waits on), `0x69C000` (a lock-free
  queue and a task: *inferred* Edge zlib's inflate queue, by
  `zlib_inflate_queue.cpp` in the asserts), and `0x955000` (a queue, a
  barrier, tasks: *inferred* Bullet's);
- SPU thread groups, by system call, at `0x8CF000`-`0x8D1000`, with four
  `sys_spu_image_import` calls; `sys_spu_thread_read_ls`/`write_ls` at
  `0x97E000`, and event ports at `0x971000`.

## The middleware, by its own strings

- **Lua 5.1.3**: `$Lua: Lua 5.1.3 Copyright (C) 1994-2008 Lua.org, PUC-Rio $`.
  The scripting host of sessions 1-13 ran the disc's scripts on Lua 5.5
  (`lupa`); the game's own VM is 5.1.3.
- **FMOD Ex** (`c:/anthill_builds/fmod4/...`, FMOD 4), with its SPU mixer.
- **Bink** (`binkliba`, "Bink IO Thread", "Bink_textures in gcmtextures").
- **Bullet**, multithreaded on SPURS (`BulletMultiThreaded/SpuNarrowPhaseCollisionTask`).
- **Edge zlib** (`edgezlib_inflate_queue.cpp`).
- Dinkumware's C library (`/home/kanee/svnwork/ps3-svn/.../dinkum-pu/`).
- `../src/ppfx.cpp`, `../src/GPU/GPUPostEffect.cpp`, `GPUDepthOfField.cpp`,
  `GPUGlareDef.cpp`, `TinyEffect/TinyEffect.cpp`: the post-processing. The
  name YEBIS is not in the binary's strings, but **the game shows it**: its
  third logo screen is Silicon Studio's DAIKOKU ("Advanced Shader Pipeline")
  and YEBIS ("Pithy Post Effect"), which settles the identification
  [`RECON.md`](RECON.md) §6.7 made from the outside.
- The engine's own sources: `c:/work/Block/Localize/program/src/system/spursManager.cpp`,
  in an assert. The engine's tree is called **Block**.
- No string names OROCHI, Silicon Studio or FromSoftware. The engine
  hypothesis of session 1 is neither confirmed nor refuted by the strings.
- FMOD reads one file of the system's: `/dev_flash/sys/external/flashMP3.pic`,
  the MP3 decoder for the SPUs, from the console's flash. It is not on the
  game's disc (the firmware update the disc carries, `PS3UPDAT.PUP` 3.15,
  has it, encrypted). Without it FMOD's output does not come up. See
  [`tools/flash.py`](../tools/flash.py).

## The game's scripts are in the executable too

The EBOOT carries **3,781,246 bytes of Lua source**, in one block at
`0xA7C967`, right after the code: **1,488 sources**, each between
`-- Start <name>.lua.eu` and `-- End`, the same shape as the disc's
`all.lua.eu` (3,754,095 bytes, 1,487 sources). Compared source by source,
with line endings set aside:

```
the same in both                1,375
different                         112
only in the EBOOT                   1   UserInterface/Skip/Skip.lua.eu
only on the disc                    0
```

The differences are small and look like two builds of the same tree: the
disc's `Event/eventfunction.lua.eu` has a debug `print(map_id, group_id,
object_id)` in `WoodFlameEvent` that the EBOOT's lacks, and
`GeneralGameData/HDDInstallList.lua.eu` declares another install size.

Which copy the game runs is a question for the run, and it matters: the
pivot's argument that the scripts stay moddable (STRATEGY, reason 2) is
simplest if the game reads them from the disc. The first measurement points
the other way: in the first 90 seconds of a run, through the logos, the
save-data check and 1,481 file opens (sounds, interface, icons, shaders),
**no `.lua.eu` is opened**. *Open*: see [`TODO.md`](TODO.md).

## Running it

```
python tools/flash.py standin build/flash
python -m ps3kit.recomp build/eboot.elf --out build/recomp
cmake -S build/recomp -B build/recomp-build -G Ninja -DCMAKE_CXX_COMPILER=clang++     -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O1
ninja -C build/recomp-build
build/recomp-build/ps3boot build/eboot.elf --bdvd extract --hdd0 build/hdd0     --hdd1 build/hdd1 --flash build/flash
```

The recompiler takes 21 seconds; the build about three and a half minutes
(Bullet's SPU task alone is 1.9 MB of C++). `extract/` needs every set,
`audio` and `movie` included, which sessions 1-13 never extracted: the game
loads its sounds while the logos play.

What session 14's runs show, in order: the first flip; the logos (ATLUS,
FROM SOFTWARE, then DAIKOKU and YEBIS) at 60 frames; FMOD's SPU mixer
started as an SPU thread group ("FMOD", `fmodex_spu.elf`) and its audio port
fed; the `Water` SPURS instance with its `water_task` waiting on its event
flag; the HDD free-space check passed; the save data looked for
(`BLES00875SYSTEM`, `BLES00875GAME-DATA`) and not found; then a black screen,
with the main loop running. That is where session 15 started.

Session 15 (see [`TODO.md`](TODO.md)): the black screen was the boot
sequence waiting for its trophies to install; with `sceNpTrophy` in the kit,
the game writes its system save, checks its game data, and reaches the
**title screen**: the logo over `TitleMovie_Omote_eu.bik`, with FMOD
playing the title music; left alone, it plays the **demo play**,
`PlayDemoMovieUS.bik` with its own sound on a second audio port, and comes
back, for as long as it is left. Both are Bink movies, decoded by the
game's own Bink on the PPU into three planes the renderer combines: what
the frames show is recorded play. Played on, Start leads to character
creation, the intro and NOW LOADING, and the first map waits for Edge zlib
behind a SPURS lock-free queue. The extract needs the `trophy` set
(`python tools/iso.py extract trophy`).

Session 16: with the PPU's side of SPURS lock-free queues and queues in the
kit, Edge zlib's inflate task decompresses the map (`Field_18.ps3.pac.gz`)
and Bullet's narrow-phase tasks compute the hits; the game **plays in the
field**: walking, enemies, hits, map transitions, at 28-31 frames once the
renderer keeps the vertex arrays it has been sent. Past the title the run is
played by hand (the name entry needs the cursor moved to END). See
[`TODO.md`](TODO.md).
