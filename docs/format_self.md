# `SELF` — the EBOOT, and how it opens

*Read by [`self.py`](../tools/self.py). Session 14.*

`PS3_GAME/USRDIR/EBOOT.BIN` is the game's only executable: 22,601,208 bytes,
no PRX beside it. For thirteen sessions it was the one file on the disc this
project did not open, by design (see [`STRATEGY.md`](STRATEGY.md)). Since the
pivot to static recompilation it is the recompiler's input, and
[ps3kit](../ps3kit) does not decrypt: its input is the ELF inside.

`self.py` is the sister project's tool (PC-ROA, session 30), brought here as
`iso.py` once went the other way. It needs nothing but Python and a key file;
the container, the chain of keys and the AES are documented there, in
PC-ROA's `docs/format_self.md`, and are not repeated here. This page is what
they give on this disc.

```
python tools/self.py header  extract/PS3_GAME/USRDIR/EBOOT.BIN
python tools/self.py check   extract/PS3_GAME/USRDIR/EBOOT.BIN
python tools/self.py meta    extract/PS3_GAME/USRDIR/EBOOT.BIN <keys>
python tools/self.py decrypt extract/PS3_GAME/USRDIR/EBOOT.BIN <keys> build/eboot.elf
```

## In the clear, before any key

```
  SCE     version 0x2  key_revision 0x0001  header_type 1
          metadata 0x410  header_len 0x980  data_len 0x158d478
  APPINFO auth id 0x1010000001000003  vendor 0x1000002  self_type 4 (APP)
  ELF     64-bit big-endian  machine 21  entry 0xfef3f8  8 segments
```

`key_revision 0x0001` and `self_type APP` pick the key set, as
[`RECON.md`](RECON.md) §4 said in session 1. `data_len` 0x158D478 is the
ELF's size, and with the 0x980 bytes of header and a signature it is the
whole file. Two segments carry everything: **16,564,704 bytes at `0x10000`**
(code and read-only data) and **6,006,656 bytes at `0xFE0000`** (data, which
grows to 30,494,200 in memory).

`check` holds on every point: the five FIPS-197 vectors, the header ending
where the first payload begins (`0x980`), every payload inside the file, and
the largest payload at a byte entropy of **8.000** against 1.911 for the
header. The segments are encrypted, not merely packed.

## The metadata

```
  the metadata decrypted: 7 sections, 52 keys, opt header 48
  section  kind        offset       size  enc  zlib  key iv  prog
    phdr   program 0       0x980  16564704  yes    no    6  7     0
    phdr   program 1    0xfd0980   6006656  yes    no   14 15     1
```

The metadata's padding came out zero, which is how `self.py` knows the key
set is right. Neither segment is compressed.

## What comes out

```
extract/PS3_GAME/USRDIR/EBOOT.BIN -> build/eboot.elf
  22587264 bytes, 8 segments, entry 0xfef3f8
    segment  0       0x10000   16564704 bytes  entropy 6.506
    segment  1      0xfe0000    6006656 bytes  entropy 5.981
  it is an ELF: b'\x7fELF', machine 21
  and it is PowerPC: mflr r0 14456, mtlr r0 18122, blr 23486, nop 47964
     4141176 words
```

44 seconds of pure Python. The prologue test that settled PC-ROA's ELF reads
differently here, and the difference is not a fault: `mflr r0` and `mtlr r0`
differ by 3,666 against ROA's 482, and segment 0's entropy is 6.5 against
5.9. Segment 0 is not all PowerPC. The PPU code ends at `0xA799CC`; after it
come 3.78 MB of Lua source and the 26 SPU programs, and SPU code is neither
`mflr` nor `mtlr`. What the ELF holds is in [`eboot.md`](eboot.md).

## The keys are not here

`erk` and `riv` have the standing the ISO has: not game content, not
derivable from the disc, not this repository's to hand on. `self.py` takes
the path of a key file in either of two formats anyone doing this already
has (scetool's `data/keys`, RPCS3's `key_vault.cpp`); `keys/` and `*.keys`
are ignored, and the decrypted ELF lives in `build/`, which is ignored too.
