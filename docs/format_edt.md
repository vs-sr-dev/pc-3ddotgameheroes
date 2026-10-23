# The EDT format — the editor's voxel characters

**Status: solved.** The walk lands **exactly on the last byte in 90 files out
of 90**, over 260,860 voxels. Parser: [`tools/edt.py`](../tools/edt.py).

This is the format in which the game describes a character drawn dot by dot —
the thing the game is named after. Reading it means the hero the player made
can be shown instead of a stand-in model.

```
python tools/edt.py info  <file.edt>        header, poses, voxels
python tools/edt.py sheet <dir> out.png     the contact sheet of all 90
python tools/edt.py check                   the internal checks (6 properties)
```

Everything is big-endian, and there is **no alignment**: it is a byte stream,
so a string of odd length shifts everything after it by one. That is why
`angel.edt` has its body at `0x36` and `default_01.edt` at `0x30`.

## The file

| | field |
|---|---|
| `'EDTFILE1.9'` + 2 zero bytes | magic, 12 bytes |
| `u32 len` + `len` bytes | **author**, UTF-8 (`プレイヤー`) |
| `u32` | flag, 0 or 1 |
| `u32 len` + `len` bytes | **character name** (`勇者の子孫`) |
| `float[14]` | editor parameters, all small integers (0–10) |
| `u32` | **number of parts**, which is 6 in all 90 files |

and then, for each part:

| | field |
|---|---|
| `u32` | number of voxels |
| `voxel[]` | 20 bytes each |
| `float[6]` | the part's tail |

The tail comes **after** every part, the last one included: that is what makes
the count land on the byte. Finding it was the only thing the first walk got
wrong — it stopped 24 bytes short of the end, and 24 is exactly six floats.

## The voxel

Twenty bytes: a `u32` position and a `float[4]`.

```
position    0x00 XX YY ZZ    the first byte is always zero, and the three
                             after it all lie between 0 and 15
float[0..2] RGB colour in 0..1
float[3]    0 to 6, seven integer values: the finish
```

**Sixteen to a side is not an arbitrary number.** It is the grid of
`data/shaders/water_col.dds`, which has 16 squares to a side because one cell
of the world is sixteen dots (session 5). An editor character therefore lives
in a **16×16×16 cube per part**, that is, one cell — and one cell is also the
height of a character, measured by another route in session 4. Three files
that know nothing of each other, one unit.

## The six parts are six poses

The counts say so on their own: in `angel.edt` they are 261, 256, 246, 240,
263 and 267 voxels. Six numbers that close are not six pieces of a body — a
head and an arm do not have the same volume. They are the same character six
times.

Two measurements confirm it:

- between the first part and the other five, **60.4%** of the voxels sit in
  the same position;
- the six bounding boxes all overlap, and occupy the same volume.

This is the same thing [`entities.md`](entities.md) had already read from
another direction: the characters of this game **have no skeleton**, and the
children of a node are whole frames. There they were 2 to 6; here they are
always six — because the editor always makes six, and the game uses as many as
it needs.

## Forward is minimum Z

The first contact sheet came out **facing away**, and it was the person
looking at it, with no idea what to expect, who said so. It was not a reading
error: taking the maximum Z gives the backs of the heads — no eyes, only
hair — and taking the minimum brings the faces out.

So the editor's characters are authored **facing −Z**, which is exactly the
convention [`entities.md`](entities.md) had already inferred in another
session, looking at the game's meshes with `view.py char c_npc_05 --azim 180`.
Two different files, written for different purposes, the same convention.

It can also be measured without looking, which makes it a property rather than
an impression: in `black_smith.edt` the front plane carries **9** voxels and
the back one **40**. A face is hollowed out — eyes, mouth — and the back of a
head is solid.

## The check that counts

The contact sheet: 90 characters, drawn by taking the frontmost voxel of each
column. It is not a render — it is a way of looking at the data — and it is
enough to recognise every one of them: knights, wizards, Father Christmas, a
king with a crown, dragons, skeletons with red eyes, a bear, a pumpkin. And
the four presets that can be checked by eye match their own file names:
`angel` has the halo and the wings, `dragon` the horns, `black_smith` the
white beard and the apron, `boxer` the gloves.

## What is left

- **The 14 header parameters**: integers between 0 and 10, varying from
  character to character. They have the shape of the attributes the editor
  declares, but no oracle ties them to anything yet.
- **The tail of six floats** per part.
- **The finish** (0–6): seven values, and what they select is unknown.
- **The `.SAV` files**: these are something else. No magic; they start
  straight away with the same `u32 len + UTF-8` pair, and `test.SAV` carries
  `edt/preset/pumpkin.edt` — so a save **refers** to a preset by path instead
  of embedding it. Three files, ~210 kB each.
