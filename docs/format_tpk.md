# The TPKG format — texture packages

**Status: solved.** Validated on all 763 packages on the disc: 4,033 textures,
622.9 MB of pixels, zero discrepancies. Reference parser:
[`tools/tpk.py`](../tools/tpk.py).

Every field is **big-endian**.

## Header — 0x20 bytes

| Off | Type | Field |
|---|---|---|
| 0x00 | char[4] | `'TPKG'` |
| 0x04 | char[4] | `'ps3\0'` — platform identifier |
| 0x08 | u16 | version. `4` across the whole disc |
| 0x0A | u16 | number of textures |
| 0x0C | u32 | offset of the data area |
| 0x10 | u32 | size of the data area |
| 0x14 | u32 | end of the mip table |
| 0x18 | u32[2] | zero in every package |

Invariant: `0x0C + 0x10 == file size`.

## Entries — 0x20 bytes each, from 0x20

| Off | Type | Field |
|---|---|---|
| +0x00 | u32 | **absolute** offset of the name (a NUL-terminated string) |
| +0x04 | u32 | total size of the data |
| +0x08 | u32 | offset of the data, **relative** to the data area |
| +0x0C | u32 | **pixel format**: 9 = DXT1, 10 = DXT3, 11 = DXT5 |
| +0x10 | u16 | width |
| +0x12 | u16 | height |
| +0x14 | u8 | **number of mip levels** |
| +0x15 | u8[3] | zero in every entry |
| +0x18 | u32 | unknown, varies per entry — 666 distinct values, possibly an index |
| +0x1C | u32 | Unix build timestamp, the same for every entry in a package |

## The tables at the end

1. **Names** — consecutive NUL-terminated strings, pointed at by +0x00.
2. **Mips** — starts at the end of the names, **aligned to 4 bytes**, and ends
   at the offset declared in header field 0x14. It holds one `u32` with the
   size of each level, for each texture, in entry order. The number of levels
   varies from texture to texture *even within one package*: read it from
   +0x14, do not infer it from the dimensions.
3. Zero padding up to the data area.

## What the disc holds

| Format | Textures | % |
|---|---:|---:|
| DXT3 | 3,870 | 96.0% |
| DXT1 | 116 | 2.9% |
| DXT5 | 47 | 1.2% |

Mip counts: `1:737, 5:491, 6:17, 7:20, 8:1249, 9:1244, 10:209, 11:66`.
The most common sizes: 256×256 (1,329), 128×128 (1,261), 16×16 (494),
1280×720 (361, full-screen images), 512×512 (216).

Build timestamps: 441 distinct, from **2009-04-20** to **2010-02-01**.

## Two traps

**The pixel format cannot be inferred from the size.** DXT3 and DXT5 both take
16 bytes per 4×4 block, and 16 bytes per 4×4 block is exactly 1 byte per pixel,
so it also matches an uncompressed 8-bit texture. The three readings are
numerically indistinguishable: the code has to be read from +0x0C. DXT3 was
told apart from DXT5 by decoding the alpha channel both ways and comparing (the
wrong reading gives regular horizontal bands or ragged edges).

**DXT3 dominates, at 96%.** That is unusual for a 2009 game, but it fits the
look: DXT3's explicit 4-bit alpha keeps the edges of voxel sprites sharp, where
DXT5's interpolated alpha would fray them.

## Cubemaps: one, and no flag says so

One texture out of 4,033 is a cubemap: `shaders/graphics.ps3.tpk` →
`ref_01.dds`, 256×256 DXT5, 9 mips per face. **There is no explicit flag**:
the 6 faces are consecutive, each with its own mip chain, while the table lists
the mips only once. The number of faces comes from the ratio
`size / sum(mips)`, which is 6 for this entry alone and 1 for every other.

## Conversion is a header rewrite

The payload is standard DXT, so converting to `.dds` is just a header
rewrite — no pixel transformation, no RSX swizzle.

```
python tools/tpk.py info   <file.tpk>
python tools/tpk.py survey <dir>              census and validation
python tools/tpk.py export <file.tpk> <out>   writes .dds and .png
python tools/tpk.py sheet  <file.tpk> <png>   contact sheet
```

## Scenes find their textures by name

Textures are referenced **by `.dds` name** from the string table of the
`DSBF` blocks inside the maps' `.pac` files (see RECON §5). The name is
therefore the join key between scenes and texture packages: no numeric index is
needed.
