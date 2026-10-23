# PC-3Ddot

Documentation and tooling towards a native PC port of **3D Dot Game Heroes**
(PS3, 2009, From Software / Silicon Studio): a static recompilation of the
game's own executable onto a runtime that stands in for the PS3,
[`ps3kit`](https://github.com/vs-sr-dev/ps3kit), built on thirteen sessions
of reading the disc.

This repository contains **no game content**. It contains a disc reader,
format documentation, the tools that produced it, and the game's side of the
recompilation. To use any of it you supply your own copy of the disc; the C++
the recompiler writes is your disc's code, translated, and is never part of
this repository.

`ps3kit/` is a submodule: clone with `git clone --recurse-submodules`, or run
`git submodule update --init` in an existing clone.

## Status

Session 14 (2026-10-23). **The game runs its own code to its logos.** The
project changed road: from a native engine hosting the disc's Lua scripts to
a static recompilation of the EBOOT, as its sister project
[pc-ragnarokodysseyace](https://github.com/vs-sr-dev/pc-ragnarokodysseyace)
had done, on the kit that project grew, which moved to its own repository the
same day. The reasons, measured on this executable, are in
[`docs/STRATEGY.md`](docs/STRATEGY.md#the-pivot-static-recompilation-session-14);
the census is in [`docs/eboot.md`](docs/eboot.md).

The recompiled game reaches its first flip and draws its four logo screens at
60 frames — ATLUS, FROM SOFTWARE, and Silicon Studio's DAIKOKU and YEBIS —
with FMOD's mixer running on an SPU thread group and a SPURS task waiting on
its event flag. Getting there taught the kit the SPUs: SPU ELFs recompiled at
their load address, lv2 SPU thread groups, SPURS task sets, tasks and event
flags. After the logos the game looks for its save data and stays on a black
screen; that is where the next session starts ([`docs/TODO.md`](docs/TODO.md)).

Sessions 1-13 (2026-08-09 to 2026-08-20). **The disc, read, and a game loop
on its own scripts.** A UDF reader; every asset format solved to the last
byte (textures, scenes, maps, collision, voxel characters, the logical grid);
the 497 methods the Lua scripts call, inferred from 29,626 call sites; and a
viewer in which the maps can be walked with their inhabitants, passages,
dialogue, menus, map objects, light, and 312 of 312 enemies running their own
script. That work is not retired: it is the oracle the recompiled game is now
checked against.

## Running the recompiled game

Python 3 (no third-party dependency for the readers), and for the build
CMake, Ninja, clang (MSYS2's `mingw64` here) and SDL3.

```
python tools/iso.py extract                       # every set, into extract/
python tools/self.py decrypt extract/PS3_GAME/USRDIR/EBOOT.BIN <key file> build/eboot.elf
python tools/flash.py standin build/flash         # a declared stand-in, see the tool
python -m ps3kit.recomp build/eboot.elf --out build/recomp
cmake -S build/recomp -B build/recomp-build -G Ninja -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O1
ninja -C build/recomp-build
build/recomp-build/ps3boot build/eboot.elf --bdvd extract --hdd0 build/hdd0 \
    --hdd1 build/hdd1 --flash build/flash
```

The key file is yours, like the disc: scetool's `data/keys` or RPCS3's
`key_vault.cpp`, with the retail APP keys of `key_revision 0x0001`. See
[`docs/format_self.md`](docs/format_self.md).

## Tools

The readers of sessions 1-13 and the tools of the recompilation, all in
`tools/`. Their messages and comments are still in Italian, which the
documents are not (see the TODO).

```
python tools/iso.py index|sets|extract|verify   the disc, by UDF, with a manifest
python tools/self.py check|header|meta|decrypt   the EBOOT
python tools/flash.py standin DIR                what the game reads from /dev_flash
python tools/tpk.py | dsb.py | mapdat.py | dpk.py | edt.py   the formats
python tools/view.py play <map>                  the viewer: walk a map
python tools/view.py walkabout                   the measure, on every map
python tools/ui.py drive|menus|keys|floors       the system screens
python tools/nodes.py census|props               the disc's symbol table
python tools/actor.py census                     the enemies' scripts
```

## BYOA

Bring Your Own Assets. Nothing extracted from the disc is redistributed here
— no textures, no models, no text, no audio, no executable. What *is*
published:

- the tools, which are original code;
- format documentation, which describes structure rather than content;
- `tools/manifest.tsv`, the fingerprint of the supported disc (path, size,
  sha256), so that a copy can be identified and verified before use;
- `generated/*.h`, method names, signatures and constant names: API
  surface, not content.

`extract/`, `build/` and everything derived from the disc stays local. See
[`.gitignore`](.gitignore), which states the policy per file type.

The reference disc is **3D Dot Game Heroes (Europe)**, BLES00875, version
01.01.

## Licence

MIT, see [`LICENSE`](LICENSE). It covers the tools and the documentation in
this repository, which is all this repository contains. It says nothing about
the disc you supply, which is not ours to licence.

## Not affiliated

*3D Dot Game Heroes* is the property of its rights holders (From Software,
Silicon Studio, and its publishers). This project is unaffiliated,
non-commercial, and distributes none of their work.
