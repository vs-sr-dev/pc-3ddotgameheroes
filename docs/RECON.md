# 3D Dot Game Heroes — disc reconnaissance (Session 1)

Date: 2026-08-09/10
Source: `3D Dot Game Heroes (Europe).iso` — 3,584,425,984 B
Disc mastered: **2010-03-25**, UDF 2.50, trophy ID `NPWR01180_00`

## 1. Structure of the medium

Region table at offset 0x0: 2 regions in the clear, 1 "encrypted".

| Region | Sectors | Contents |
|---|---|---|
| 0 (plain) | 0x0 – 0x115F | ISO9660/UDF metadata |
| 1 ("enc") | 0x1160 – 0x18B49F | game data |
| 2 (plain) | 0x18B4A0 – 0x1AB4BF | `PS3_UPDATE/PS3UPDAT.PUP` (268 MB, firmware — irrelevant) |

**Region 1 is not actually encrypted** (entropy 0.09 bits/byte at its start;
under AES it would be ~8.0): the ISO is in 3k3y/decrypted form, with the
region table kept but the payload in the clear. The SELF/disc-key decryption
layer remains an optional teaching module, off the critical path.

## 2. Reading the filesystem

The **ISO9660 tree truncates names to 31 characters** (`..._lua.` → `.LU`,
`.L`, `.E`). The real names are **only in the UDF tree**. Always extract
through UDF:

```
7z x "…\3D Dot Game Heroes (Europe).iso" -o<dst> -y -r "*.lua.eu"
```

7-Zip reports `Headers Error` / `Tail Size = 65536` (the region table at the
end) and exits with code 2. This is **benign**: the extraction is correct.
Ignore the exit code.

`tools/iso.ps1` implements a native ISO9660 reader — useful for probing at
LBA/sector level, **not** for extraction (the names are truncated).

## 3. Inventory

2,792 files, 3.07 GB under `PS3_GAME/USRDIR/`. A single executable.

| Ext | N | MB | Format | Difficulty |
|---|---|---|---|---|
| `.bik` | 5 | 1193.2 | **Bink 1** (`BIKi`) | solved (ffmpeg) |
| `.wav` | 326 | 638.3 | **RIFF PCM** 44.1 kHz 16-bit mono | solved |
| `.tpk` | 763 | 623.3 | `TPKG`+`ps3` — texture package | **solved** ([doc](format_tpk.md)) |
| `.gz` | 167 | 441.5 | **gzip** → `<name>.ps3.pac` — maps | **solved** ([doc](format_pac.md)) |
| `.dsb` | 460 | 176.7 | `DSBF` — scene/model | **solved** ([doc](format_dsb.md)) |
| `.dat` | 170 | 34.0 | `MAP_ALIGNMENT` — logic grid, **little-endian** | half solved ([doc](format_pac.md)) |
| `.bin` | 2 | 21.6 | `EBOOT.BIN` + UTF-16BE font table | see §4 |
| `.dpk` | 171 | 5.4 | `MAPCOLLISION` — collision mesh | **solved** ([doc](format_dpk.md)) |
| `.edt` | 90 | 5.0 | `EDTFILE1.9` — voxel editor data | to RE |
| `.lua.eu` / `.lua` | 618 | 5.6 | **Lua source in the clear** | solved |
| `.pkg` | 2 | 1.1 | `spkg`+`ps3` — shader package | to RE |
| `.spk` | 2 | 0.1 | `CGB` — **Cg binary** (RSX) | to RE |
| `.dds` | 2 | 0.3 | standard **DirectDraw Surface** | solved |
| `.sav` | 3 | 0.6 | editor saves, big-endian | to RE |

Standard or trivial formats: **~2.3 GB of 3.07 GB (75%)**.

### Fingerprints of a Windows toolchain
- `data/MakeLuaDump.exe`, `data/EDT/Addition/AdditionEditCharMessage.exe` —
  x86 build utilities, MSVC 2008 (VC90 CRT). Small, and not part of the game.
- `data/ICONDATA/Thumbs.db` — an Explorer thumbnail cache that ended up on the
  master.
- `.dds` and Cg: an asset pipeline of PC descent.

## 4. EBOOT.BIN

`SCE\0`, 22,601,208 B. A signed SELF, `key_revision = 0x0001` (a 2010 game →
public retail keys), inner ELF 0x0158D478. Decryptable offline into a
big-endian PPC64 ELF. **The game's only executable**: no additional PRX
module, no separate SPU archive visible at filesystem level.

## 5. Contents of a `.pac` (map)  ⟵ solved, see [`format_pac.md`](format_pac.md)

`D_1_3.ps3.pac` → 963,072 B (gzip 5.0x). A wrapper around one or more `DSBF`
blocks with a **readable string table**: a scene graph with names.

```
D_1_3_00_00.ps3
dot_512_nm.dds / wall.dds / dot_floor_nm.dds / yka.dds     ← textures
d_kbe_01-fx / d_yka_01-fx                                  ← materials
OPACITY                                                    ← material parameter
md_kbe_L0_00_00-mesh / md_hsr_L1_00_00-mesh                ← meshes (with LOD L0/L1)
md_kbe_L0_00_00-node / md_yka_00_00-node                   ← hierarchy nodes
```

Textures are referenced by **`.dds` name**, which gives a direct join key
into the `TPKG` packages.

The suspicion that the `_00_00` and `L0`/`L1` suffixes were the cell and the
level of detail later proved exact, and checkable: the name encodes the cell
in 12,097 meshes of 12,097.

## 6. The scripting API surface  ⟵ the main result

618 Lua files, 5.57 MB of **source in the clear** (Japanese comments
included), all of it contained in `all.lua.eu` (see §6.1). Measured on the
bundle alone, so as not to count the same call sites twice: **497 native
methods**, **29,626 call sites**, across **8 host classes**.

> An earlier measurement gave 501 methods / 43,253 call sites. It was
> inflated: it analysed the bundle *and* the loose files together, and used
> regexes instead of a lexer. The set of methods, though, came out almost
> identical (497 against 501), which gives confidence that the result is
> stable.

| Host class | Methods | Calls | Role |
|---|---|---|---|
| `Object` | 297 | 14,999 | game entities: nodes, animations, phase/state, motion, collision |
| `Event` | 176 | 13,136 | cutscene direction: dialogue, camera, DOF, player lock, audio |
| `PackageManager` | 3 | 1,351 | resource loading (`addNodeListElement`) |
| `MapManager` | 1 | 72 | map transitions |
| `Boss` | 11 | 51 | boss logic |
| `observer`, `club`, `gimmick` | 9 | 17 | probably aliases of `Object` |

Most frequent methods: `:Print` (2,805), `:WaitContinue` (1,156),
`:GetEventFlag` (1,093), `:SetPhase` (1,291), `:AddNode` (1,281),
`:AddAnimation` (916).

Full inferred signatures: [`lua_signatures.md`](lua_signatures.md) /
[`.json`](lua_signatures.json), with a generated C++ header in
[`generated/script_api.h`](../generated/script_api.h).

**Strategic implication.** Plot, dialogue, events, NPCs, boss logic and
progression are already available as source, and they are *portable
verbatim*. They do not need reimplementing: what needs reimplementing is the
host that exposes those 501 methods. This list is in effect a
machine-generated functional specification.

### 6.1 `all.lua.eu` is the authoritative bundle

`data/all.lua.eu` (3,754,095 B, 190,695 lines) is not a debug dump but the
**concatenation of 1,486 modules** in load order, delimited by
`-- Start <path>` markers. It contains more modules than the 618 loose files:
the loose files are a subset, probably leftovers of the build. So the bundle
is both the real payload and the **manifest of the initialisation order**. It
was in all likelihood generated by `MakeLuaDump.exe`.

### 6.2 The runtime contract is very narrow

Three properties measured over the whole corpus, all of them in favour of
reimplementation:

- **No standard library.** Not one occurrence of `table.*`, `string.*`,
  `math.*`, `#`, varargs, `require`, `os.*`. The scripts are a fully
  sandboxed DSL: the only stdlib module used is `coroutine`.
  → the exact version of the Lua VM is almost irrelevant; any 5.x will do.
- **No metatables.** Zero `setmetatable`, `__index`, `loadstring`, `dofile`
  in the bundle. `Event:Method()` is not Lua OO: these are tables the host
  fills directly with native functions. The dispatch is trivial to
  implement.
- **Coroutine scripting.** `coroutine.yield` is used throughout the event and
  boss scripts. `Event:Wait()` / `:WaitContinue()` are suspension points: the
  host runs each event as a coroutine and resumes it once per frame.

Typical shape of a script (`Event/Guard/GuardAfter.lua.eu`):

```lua
function GuardAfterEvent()
    local Event = EventClass.Event;
    if (Event:GetEventFlag(EventFlag.scene_guardtomb) == 0) then
        Event:SetEventFlag(EventFlag.scene_guardtomb, 1);
        Event:StopBgm();
        Event:PlayBgm(soundList.SoundID.BGM_field02);
        return;
    end
end
```

The enums (`EventFlag.*`, `soundList.SoundID.*`) are Lua tables defined
inside the bundle: they come for free and do not need rebuilding.

### 6.3 MIXED encoding — a trap to keep in mind

The corpus mixes UTF-8 and Shift-JIS, **even within a single file**: in
`all.lua.eu` there are ~11,837 UTF-8 lines and ~1,525 pure Shift-JIS ones;
among the loose files, 514 are UTF-8 and 20 Shift-JIS. These are modules
written on different machines and in different years.

Decoding everything as UTF-8 silently corrupts the Japanese strings.
`tools/lua_lex.py::decode_lua()` decodes **line by line**, with a UTF-8 →
CP932 fallback. Splitting on `\n` is safe: in Shift-JIS the second byte of a
pair is never 0x0A.

### 6.4 The dialogue is string literals in the Lua

`Event:Print()` — the most called method — receives 2,639 string literals in
2,805 calls. **The game's text is in the Lua source**, not in an archive.

Two peculiarities:
- The English text is stored in **full-width Latin** (`ｔｈａｔ’ｓ ｎｏｔ
  ｅｎｏｕｇｈ ｍｏｎｅｙ．`), because the font is a fixed-width Japanese
  bitmap. A PC port will have to decide whether to normalise it to ASCII.
- 2,747 strings of 2,805 use full-width; **134 still contain kana/kanji** in
  the European build (untranslated strings, probably debug ones — e.g.
  `/paてきをしゅつげんさせたよ`).

**Inline markup — a complete census.** 9 codes, no control characters, no
escape sequences. The language is closed:

| Code | Occurrences | Reading | Evidence |
|---|---|---|---|
| `/r` | 2,770 | line break inside the box | always separates 2-3 lines of text |
| `/b` | 2,383 | end of block, wait for input | always at the end, followed by `/co` or `/pl` |
| `/co` | 1,435 | close the box | the dominant terminator, always after `/b` |
| `/cl` | 1,422 | clear and continue in the same window | in the middle of long messages |
| `/vn` | 857 | normal *voice* (a hypothesis) | at the start, before the speaker's name |
| `/vh` | 387 | high *voice* (a hypothesis) | likewise |
| `/vl` | 25 | low *voice* (a hypothesis) | `/vlＢｌｕｓｅｙ：…` |
| `/pl` | 33 | alternative terminator to `/co` | always after `/b` |
| `/pa` | 2 | unknown | only on 2 Japanese strings |

The `/vn` `/vh` `/vl` family comes at the head of the line, just before the
character's name: almost certainly the **tone of the text beep** (the game
has no voice acting, only Zelda-style beeps). To be confirmed in Phase 3.

### 6.5 Constant tables

Extracted by [`tools/lua_tables.py`](../tools/lua_tables.py) →
[`lua_tables.md`](lua_tables.md), with a header in
[`generated/script_enums.h`](../generated/script_enums.h). 12 enums, 2,216
members.

| Enum | Members | Refs | Origin |
|---|---|---|---|
| `PackageId` (`package_manager.*`) | 1,354 | 5,447 | native |
| `MapId` (`map_manager.*`) | 216 | 409 | native |
| `GameDataMapFlag` | 195 | 228 | native |
| `SoundID` (`soundList.SoundID.*`) | 144 | 781 | native |
| `ItemId` (`item.Item.IL_*`) | 100 | 179 | native |
| `EventFlag` | 67 def. / 61 used | 535 | **Lua, values known** (0..98) |
| `GameDataFlag` | 46 | 140 | native |
| `ActorType` (`actor_manager.AT_*`) | 33 | 6,674 | native |
| `SwordId` (`swordData.SwordData.SL_*`) | 24 | 104 | native |
| `LivingId` (`LIVING.*`) | 16 | 60 | native |
| `ObjectClassId` | 6 | 64 | native |

Only `EventFlag` is defined in Lua, and so only it comes with its values. The
other tables live in the EBOOT: we have their **full names** from the use
sites, not their values. That is not blocking — the values are free as long
as host and Lua agree on them — but they have to be reconciled with the EBOOT
before original saves can be read.

A useful convention turned up: every enum constant has an **upper-case prefix
plus underscore** (`AT_`, `IT_`, `IL_`, `SL_`, `MS_`, `BGM_`, `SE_`,
`ATTACK_`). Data fields never follow it. It is the discriminant that tells
enums apart from field accesses such as `Boss.m_info.armHp`.

### 6.6 The UI is declarative in Lua too

413 tables defined in Lua, 15,596 leaf constants, divided as follows:
**137 UI screen descriptors**, 20 integer enums, 256 data tables.

Every screen (`EnemyAlbum`, `FieldMap`, the 20 `dungeonMapXX`, `Item`,
`Status`, …) is a Lua table with `TexturePackageName`, `ScenePackageName` and
the widget layout — up to 421 keys per screen. **The whole interface layer is
data, not code**, and it references the `TPK`/scene packages by name. It
ports without being rewritten, exactly like the event scripts.

A bonus: `Boss.m_info` exposes 180 **boss balance parameters** (`armHp`,
`armAttackDistance`, `armCutDownSpeed`, `accel`, …). It is not an enum but a
struct the engine fills in: a useful list for tuning the combat.

## 7. Unknown / to be clarified

- How much use is made of the SPUs (audio? culling? skinning?) — this needs
  the ELF.
- The bodies of the `DSBF` records: mesh (vertices/indices), node (matrices,
  hierarchy), material, skin. Container and tables solved, see
  [`format_dsb.md`](format_dsb.md).
  ~~`TPKG`~~ solved, see [`format_tpk.md`](format_tpk.md).
- The editor's voxel format (`.edt` / `.sav`) — the core of the game's
  identity.
- The exact semantics of the 497 methods: the names, the inferred signatures
  and the call sites suggest a great deal, but the ambiguous cases need the
  EBOOT.
- The numeric values of the 11 native enums (§6.5).
- The semantics of the dialogue markup `/cl` `/b` `/co` `/pl` (§6.4), and
  whether there are other codes beyond the ones observed.
- A hypothesis to check: the base engine is Silicon Studio's **OROCHI**. It
  stays open: knowing that YEBIS is there (§6.7) does not decide it, because
  YEBIS is only the post-processing library and can sit inside any engine.

## 6.7 The post-processing is YEBIS

Silicon Studio is first of all a **middleware** company, not a games studio:
it sells engines and libraries to third parties. That explains the format
discipline we found — string tables with named objects, CRC32 lookups typical
of a generic resource manager, a declarative UI, and an exporter whose
version numbers appear in every file.

It also explains the `'ps3\0'` field in the `TPKG` header and the `.ps3`
suffix in the name of every file on the disc: the pipeline was
**multi-platform**, and it marked the target variant in the format itself.

**YEBIS**, their post-processing middleware, is used by 3D Dot Game Heroes
(an external source, confirmed by the API surface). The methods exposed to
Lua:

| Method | Notes |
|---|---|
| `Event:BackupDof()` / `RestoreDof()` | 524 / 612 calls — among the most used in the whole API |
| `SetDofApaerture(float, int)` | lens aperture. **The typo is in the original** and has to be reproduced: the scripts call it by that name |
| `SetParamDepthofField(float, float, float)` | |
| `SetCaptureDOF()` | |
| `switchDofPointGaze()` / `resetDofPointGaze()` | focus that follows a target |
| `createFairyGlareEffect(float, float, float)` | *glare* is a YEBIS feature |

### The vendor's description

The YEBIS showcase page on the Silicon Studio site (recovered through the
Wayback Machine) lists 3D Dot Game Heroes and describes its use like this:

> *"Applied for vignetting and color modification to give a toy camera feel,
> and realistic defocusing effects that create the feeling of a miniature
> world. Also contributes to sparkling glare effects for light sources or
> water."*

It is a specification written by the vendor, and the resources on the disc
match it:

| Element of the description | What the disc has |
|---|---|
| defocusing / *miniature world* | the whole DOF family in the API, among the game's most called methods |
| glare on *light sources* | `shaders/Sun.dds`, `useSunStoneParameter()`, `createFairyGlareEffect()` |
| glare on *water* | `shaders/water_col.dds` and `ref_01.dds` — **the game's only cubemap**, the environment map for the reflections |
| vignetting, *color modification* | no dedicated texture or LUT: it lives in the shader code (`shaders.ps3.pkg`, `SasShader.ps3.spk` in Cg binary) |

**The practical consequence, and it is not a minor one.** The *defocus* here
is not optional polish: it is **visual identity**. It is the tilt-shift
effect that makes a voxel world read as a miniature diorama — the reason the
game looks the way it does. Removing it does not mean graphics that are less
refined; it means a game that no longer looks like 3D Dot Game Heroes.

So in planning the host, the post-processing chain **must not be put off to
the polishing phase**: it belongs next to the first render.

YEBIS is proprietary and cannot be reused, but there is no need to reuse it:
we know *which* effects are needed and *with what parameters*, because the
Lua itself drives them, call by call. It is a specification of the
post-processing obtained without opening the EBOOT.

A side note, a **refuted hypothesis**: it had been conjectured that "SAS" in
`SasShader.ps3.spk` stood for *Standard Annotations and Semantics*, the
Microsoft convention for `.fx` effects. It does not: **no** `Sas.` string
appears in the shader packages, and the naming convention is entirely
in-house (`at*` for vertex attributes, `g*` for uniforms). What the acronym
stands for remains unknown.

The check did, however, yield the renderer's entire interface — 1,200 Cg
programs, 107 identifiers — documented in [`renderer.md`](renderer.md).
