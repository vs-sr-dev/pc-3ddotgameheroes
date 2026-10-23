# The extractor — `tools/iso.py`

Phase 1a. Its job is to make `extract/` **reproducible**: 3.1 GB that until now
existed only as local state that could not be rebuilt, and that BYOA policy
keeps out of the repository. Now they are a function of the disc.

```
python tools/iso.py index                 rewrites tools/iso_index.tsv
python tools/iso.py sets                  what is declared, with the totals
python tools/iso.py manifest              computes tools/manifest.tsv (sha256)
python tools/iso.py extract [set ...]     extracts into extract/
python tools/iso.py verify [set ...]      compares extract/ with the manifest
python tools/iso.py magic '<glob>' [n]    first bytes of the matching files
```

On the reference disc: **2,799 files, 3.3 GB**; the manifest declares
**2,793 of them, 3.1 GB**, computed in 26 seconds.

## UDF, not ISO9660

The disc carries both filesystems and they are not equivalent: ISO9660 names
are **truncated to 31 characters** and upper-cased, so `d_1_1_1.ps3.pac.gz`
becomes `D_1_1_1_PS3_PAC.GZ`. This is not cosmetic. In this game names are
data: a material refers to its texture *by file name*, a grid cell is encoded
in a mesh's name, and the destinations in `MAP_ALIGNMENT` are map names.
Extraction goes through UDF.

The check showed it straight away: the `.pac.gz` files already on disk came
out as **missing**, because they had been extracted with 7-Zip at some point
and carried the truncated names.

### Why a hand-written reader

`pycdlib` is installed and rejects this disc:

```
PyCdlibInvalidISO: UDF File Set Tag identifier not 256
```

In its way it is right. PS3 Blu-rays use UDF 2.50 with a **metadata
partition**: the second partition map of the Logical Volume Descriptor,
identified by `*UDF Metadata Partition`. The inodes do not live in the
physical partition but inside a metadata *file* (type 250) laid over it; the
extents of that file **are** the blocks of the logical partition where the
File Set Descriptor and every directory live. A reader that ignores that level
of indirection goes looking where it expects an FSD (tag 256) and finds a File
Entry (tag 261) — exactly the error above.

The full chain of descriptors is in the docstring of `tools/iso.py`. It is
about 150 lines of Python, and it removes an external dependency from the very
bottom of the stack.

A note in the method's favour: the file always declares where the next thing
is. There was nothing to guess, only to follow — the same property that solved
`DSBF`.

## The manifest is the disc's fingerprint

`tools/manifest.tsv` is `path · size · sha256` for every declared file. It is
the **fingerprint of the supported disc**, not game content, so it belongs in
the repository (devilutionX and Ship of Harkinian do the same). It makes three
things possible that were not before:

- recognising that a disc is the right one, before extracting;
- checking `extract/` without rereading the ISO (`verify`, ~30 s with
  `--deep`);
- noticing an extraction made with the wrong tool.

The reference disc is **3D Dot Game Heroes (Europe), BLES-00875**: `TITLE_ID`
in `PS3_GAME/PARAM.SFO`, version 01.01, `APP_VER` 01.00. (Until session 14
this page and the manifest's header said BLES-00860, which is no id this disc
carries.)

## The sets

`extract` with no arguments extracts everything; the list of sets *is* the
definition of what "a complete `extract/`" means.

| set | files | bytes | contents |
|---|---:|---:|---|
| `script` | 618 | 5.3 MB | the `.lua.eu` files, the game's source |
| `texture` | 763 | 623.3 MB | TPKG |
| `model` | 460 | 176.7 MB | DSBF |
| `map` | 167 | 441.5 MB | `.pac.gz`, + derived: gunzip into `extract/pac/` |
| `collision` | 171 | 5.4 MB | DPK |
| `align` | 170 | 34.0 MB | the logical grid and the world graph |
| `voxel` | 93 | 5.6 MB | EDT/SAV, the character editor |
| `shader` | 4 | 1.2 MB | Cg packages (the symbol table is what is needed) |
| `image` | 11 | 1.0 MB | loose PNG and DDS |
| `audio` | 326 | 638.3 MB | WAV |
| `movie` | 5 | 1.2 GB | Bink |
| `boot` | 2 | 21.6 MB | `EBOOT.BIN`, `PARAM.SFO` (Phase 3) |
| `font` | 1 | 1.3 kB | `Font.bin`, metrics of the interface font |
| `devtool` | 2 | 24.0 kB | Windows executables left on the disc |

**Derived** steps are part of the manifest: without them `extract/` is not
complete. For now there is only one, decompressing the `.pac.gz` files into
`extract/pac/`, because the rest of the chain reads the `.pac` in the clear.

Left out on purpose: `PS3UPDAT.PUP` (the firmware, 256 MB), `TROPHY.TRP`,
`LICDIR/LIC.DAT`, `PS3LOGO.DAT`, `PS3_DISC.SFB` — platform infrastructure —
and `IconData/Thumbs.db`, a Windows thumbnail cache that ended up on the master
by accident.

## Two finds nobody was looking for

The declared inventory turned up things nobody was looking for, because until
then there was no list of *everything*:

- **`data/MakeLuaDump.exe`** (9.5 kB) and
  **`data/edt/addition/AdditionEditCharMessage.exe`** (14.5 kB): two of the
  developers' Windows utilities, left on the pressed disc. They are tiny x86
  PEs and, going by the name, one of them exists precisely to *dump the Lua
  tables* — that is, it does the job of `tools/lua_tables.py`. They are worth a
  look: they cost little and could confirm the semantics.
- **`Font.bin`** (1.3 kB): too small to hold glyphs, so it is metrics or a
  character map, with the font's textures kept separately in
  `UserInterface/Font`. It will be needed for the "first dialogue" milestone.
