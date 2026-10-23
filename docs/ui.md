# The system screens — `tools/ui.py`

**Status: navigable.** The disc declares 136 screens. They are loaded with the
Lua VM and run: the scene in its place, the text where the descriptor puts
it, the cursor where the descriptor says — and the buttons that move it,
because those are declared too.

```
python tools/ui.py list                   the declared screens
python tools/ui.py show ClearSave out.png one screen, composed
python tools/ui.py menus Pause            the items, and what they explain
python tools/ui.py keys EnemyAlbum        the bar: which actions, on which button
python tools/ui.py drive Pause giu,giu,croce out.png    navigated
python tools/ui.py floors 5               the floors of a dungeon
python tools/ui.py clips Option           the clip table, by index
python tools/ui.py anim ClearSave a.png   the frames of the opening
python tools/ui.py map 1 1 out.png        the map of a dungeon
python tools/ui.py check                  the internal checks (29 properties)
```

This game's interface is **data, not code**. 109 Lua files under `data/`
declare save, options, pause, game over, the shop, the enemy album and the
twenty dungeon maps. It ports without being rewritten, exactly like the event
scripts.

```lua
ClearSave = {
    TexturePackageName = "UserInterface/Select/SelectA",
    ScenePackageName   = "UserInterface/Select/SelectA",
    Animation = { In={Start=0.0,Size=0.4}, Main={...}, Out={...}, Cursor={...} },
    Message = { Size=1, {X=640.0, Y=500.0, String="Ｏｋａｙ　ｔｏ　ｓａｖｅ？",
                         Align="Center"} },
    Select  = { Size=2,
                {CursorX=927.0, CursorY=525.0, X=961.0, Y=518.0, String="ＹＥＳ"},
                {CursorX=927.0, CursorY=557.0, X=961.0, Y=550.0, String="ＮＯ"} },
    Cancel  = { Enable=0, Index=1 },
};
```

They are loaded with `lupa`, not with a parser of our own, for the same reason
the font is: **they are Lua**, and the VM reads them better than anything we
would write.

## There is one virtual screen

That the descriptors' coordinates live in a 1280×720 screen was already known
— `X=640` is the centre. What makes composition possible is that **the 3D
scenes live in it too**: the median width of the 115 scenes is exactly
1280.0, and the full-page fade `Fade/Fade.ps3.dsb` — which by definition
covers the screen and nothing more — measures `x [0, 1280]`, `y [-720, 0]` to
the decimal.

From there the two conversions follow. They are a reading, not a calibration:

```
screen_x = model_x
screen_y = −model_y         the model's Y grows upwards
z                           is not depth: it is the stacking plane
                            (−90 the fade, −50 the background, 0 the front)
```

## Rectangles, not triangles

Of the **16,494 triangles** in the 115 scenes, 16,492 are flat in Z and
**16,494 of 16,494** have two sides on the axes. The interface is made of
axis-aligned rectangles, and drawing it means cutting a piece out of a texture
and pasting it: pixel-exact, with no 3D pipeline.

## Why reading them was not enough

The descriptors had been read for three sessions and never run, and trying it
shows why: **at rest the screens are closed**.

The node of every piece of `SelectA` has **scale 0** on one axis — `(0,1,1)`,
`(1,0,1)` — while the mesh under it is whole: `Confirm_02b` measures 149×99.
And the sliding screens have their pieces parked off screen: the item menu
reaches `x=2193`, nearly twice the screen's width.

What opens them is the animation, and it is the fourth thing the descriptor
declares — `Animation = {In, Main, Out, Cursor}`, four clips with a start and
a duration. The `.dsb` holds no curves: among its eight object types
(`texture`, `material`, `effect`, `light`, `camera`, `mesh`, `skin`, `node`)
there is no animation. So the engine supplies the motion, and the final pose
is the scale at 1 — which is what `view.load(unfold=True)` does.

*Corollary: data that looks empty may only be closed. The geometry was all
there; what hid it was a zero in a scale.*

## `Start` is not a time, it is an index

The clips were read as `{Start, Size}` = start and duration on a timeline.
The count says otherwise. On the 42 screens that declare `In`, `Start` is
**0 all 42 times**; `Main` is 1 all 38 times; `Out` is 2 all 42 times. A time
that never changes is not a time — it is **the position in a clip table**,
and the clip's name decides it. `Size`, on the other hand, varies
(0.4 / 0.5 / 1.0) and is the duration in seconds.

*The numbers grew in session 9, when the 17 screens that `descriptors()` had
been dropping came back in: the property did not weaken, it held over a fifth
more cases.*

The large screens make it obvious, because there the indices reach far and
stay **dense and consecutive**: `Option` runs from 0 to 38 without a gap. And
how they are distributed says what they index:

```
python tools/ui.py clips Option

[ 0] Display.WindowIn      [ 3] Display.MessageIn  [10..19] Volume.0 .. Volume.9
[ 1] Display.Window        [ 3] Message.MessageIn  [20] Sound.WindowIn
[ 2] Display.WindowOut     [ 3] Sound.MessageIn    [23] Message.WindowIn
```

The three panels **share** indices 3–9 and keep separate only their own
0–2 / 20–22 / 23–25. The message area, the button bar and the cursor are the
*same objects*, reused, and only the window changes. So the index does not
identify a moment; it identifies **the thing that moves**.

The ten indices 10–19 are the ten notches of the volume, and they are declared
in a place that is easy to miss: `Volume` is an **array**, not a dictionary
(`Volume={{Start=10,Size=1.0},...}`). A walker that only descends into
dictionaries skips them and leaves a gap of ten — exactly as many as the
scene's `Volume00…Volume09` nodes. The gap was ours, not the disc's.

## The motion: one has it, the other does not

The screens' two animations are two different problems, and they are better
not kept together as a single "the animation is missing" entry.

**The opening has both ends on the disc.** The piece is exported with its
scale at zero and the mesh under it is whole: everything from 0 to 1 is there,
and `Size` declares the duration. There is nothing to invent, and indeed
`unfold` is no longer a switch but a **factor**:

```
python tools/ui.py anim ClearSave frame.png --frames 6

t=0.000s  open   0.0%      t=0.240s  open  60.0%
t=0.080s  open  20.0%      t=0.320s  open  80.0%
t=0.160s  open  40.0%      t=0.400s  open 100.0%
```

The window opens like a television switching on, and the scene is what says
so: `Confirm_01` is made of three pieces, `a` (505×4) and `c` (505×7) with
**scale X = 0**, and the body `b` (505×99) with **scale Y = 0**. First a
horizontal line, then the body vertically. Which scale is null declares which
axis opens.

The only thing not read is the **curve**: here it interpolates linearly,
because that is the one choice that adds no invented number.

**The slide has only one end.** The sliding screens are not closed by a
scale: they are *moved*, and the disc carries only where they are parked.

```
selectmenu_eng    Window01  x [ -600,  -18]  y [ 48, 294]
                  Window03  x [ 1300, 1619]  y [ 48, 294]
                  Message   x [ 1285, 2193]  y [555, 628]
```

The count over all the scenes: **38 pieces parked off screen, 33 of them off
only in X**, so the motion is horizontal — and the Y is already the final one.
The descriptor confirms it: it places "EQUIPMENT" at y=53 inside `Window01`
(48–294), "ITEMS" at y=308 inside `Window02` (303–550) and the buttons at
y=635 inside the bar (632–666).

But **where they land in X is nowhere**: not in the scene, which only has the
parking place, and not in the descriptor, which places the content and not
the container. Interpolating between parking place and destination cannot be
done, because the destination is missing. This — and only this — is the part
worth asking the EBOOT, and it concerns **5 screens and 15 pieces**: `Item`,
`Orb`, `Option`, `NameEntry`, `GameOver`.

## The dialogue box, and the file that was not it

The dialogue box was the last piece we drew ourselves, and the TODO placed it
in `data/Balloon`. It is not there. `balloon_eng.ps3.dsb` is three quads of
**1.6 × 0.6 world units** — 1.6 is a cell, that is, a character's height —
with three materials `CHECK`, `TALK`, `OPEN`, and its textures are three
speech bubbles with the ✕ button and the tail pointing down. It is the sign
that floats above a head, not the dialogue window.

The box is in **`UserInterface/Message`**, and it is built like every window
in this game: `Message_a/b/c` (505 × 138) and `MessageBig_a/b/c` (686 × 154),
`a` and `c` thin lines with scale X at zero, the body `b` with scale Y at
zero. With them is `Advance_Cursor`, the "press to continue" arrow.

The descriptor supplies everything else and leaves nothing to invent:

```lua
Line=3,  X=421.0, Y=485.0, Space=8.0,   -- small box
         LargeX=325.0, LargeY=465.0, LargeSpace=4.0,
Speed={0.25, 0.225, ... 0.025},          -- ten typing speeds
Color={White={...}, Blue={...}},
```

The numbers fit together, and that is the check. At scale 1 the font measures
**32 px** per line, so `485 + 3×32 + 2×8 = 597`, and the body of the box ends
at **598**. One pixel of margin — which also shows that `Space` is the spacing
**between** lines and not on each one: adding it to the last line as well
overshoots by seven pixels. And that the font at scale 1 is already the right
size confirms by one more route that there is one virtual screen.

`ui.widget()` cuts a single piece out of a scene. It is needed because the
large size *contains* the small one, so they cannot be separated by cutting a
rectangle: they are filtered by node name.

## The dungeon map, and the tint the compositor ignored

The twenty dungeon maps were on the "what is missing" list as *screens with
dynamic content, which need game data that does not exist yet*. The data now
exists: the grid declares which **room** each cell belongs to (see
[`walk.md`](walk.md)), and the scene has one piece per room and per state.

```
python tools/ui.py map 1 1 out.png --seen 1,2,3,4,5,6 --here 4
```

The descriptor closes the circle by itself, because its doors **name the
fields** that in the grid are mute digits:

```lua
-- 普通扉[Door_marker_01]：対応する部屋[room_on_02⇔room_on_06]
room1=GameDataMapFlags.DUNGEON1_1_2,  room2=GameDataMapFlags.DUNGEON1_1_6,
groupId=12,  objectId=201,
```

`groupId` and `objectId` are the cell's `-g` and `-o`, and `groupId=12` stands
for floor 1, room 2 — the same `(floor)(room)` measured on the grid, spelled
out by a third file.

### The three states are a colour, not three drawings

Composing the map changed nothing: the rooms came out identical in all three
states. It was not the filter — `room_on_02`, `room_off_02` and
`room_still_02` are the **same mesh**, in the same position, with the **same
UVs**, on the same texture. What tells them apart is the material's
`diffuse`:

| state | diffuse |
|---|---:|
| `room_on` | 1.0 |
| `room_off` | 0.5 |
| `room_still` | 0.0 |

A scale, and the scale orders them: the darkest is the room not yet seen,
because 0.0 on a map means a room you cannot see. The names do not say so and
this correspondence remains ours, but it is not a hypothesis in the dark.

*The defect, though, was general, not the map's: the compositor looked only at
the texture and threw away the material's colour, on **every** screen. Now it
multiplies it in — not the alpha, because what switches a piece off here is
the colour.*

And the defect was large, because tint is how this interface declares states:

```
115 interface scenes, 49 with at least one tinted node, 1,869 nodes in all
   891 at 0.0     fully off
   864 at 0.5     half
    70 at 0.13, 42 at 0.59, and a single truly coloured node (0.0 0.24 0.5)
```

Eight hundred and ninety-one pieces that should be black were being drawn at
full light. It is the same shape as session 6's finding — *data that looks
empty may only be closed* — the other way round: here a piece that looks lit
may only be **switched off**, and what switches it off is neither the
geometry nor the alpha but a number in the material.

## The input was almost all declared

It was on "what is missing" as *"`Cancel = {Enable, Index}` says which item the
cancel button chooses, so the behaviour is declared too: what is missing is
whatever runs it"*. Looking for whatever runs it showed that the descriptor
declares much more than that line, and that only one thing is left to choose.

### An item is an item if the cursor can rest on it

The `Select` block was nineteen yes/no pairs, and it looked like all there
was. The right criterion is not the block's **name** but
`CursorX`/`CursorY`: searching that way finds **23 blocks with 60 items**,
under three names.

```
python tools/ui.py menus Title

Title.ClearMenu: 6 items, cancelling is not allowed
   1. NEW GAME      cursor (534,377)   Start a new adventure.
   2. NEW GAME+     cursor (534,407)   Begin from your cleared data.
   ...
Title.Menu: 5 items
   1. NEW GAME      cursor (534,407)   Start a new adventure.
```

`Menu` is the title menu and the pause menu — *RESUME, SAVE, LOAD, OPTIONS,
SNAPSHOT, ALBUM, BESTIARY, LOADING ART, TITLE* — and `ClearMenu` is the title
**once the game is finished**, with `NEW GAME+` added. The two lists share
the positions from 407 down: the new item is not appended at the bottom, the
menu **grows upwards**.

Each item also carries its own line of explanation, and that is the only
piece of interface that changes as the cursor moves.

### The axis is not a choice, and neither is the step

The items are stacked in a column in **23 blocks of 23**, none in a row: you
go up and down. The cursor sits 34 px left of the text and 7 px up, always the
same, and the step between two items is **32 px** — the font line with which,
in session 7, the dialogue box came to 597 against a body that ends at 598.
The same number, from a third place.

### Cancelling does not mean leaving

`Cancel = {Enable, Index}`, and **the index counts from zero**. The content
says so: all 19 screens have the same two items `YES`/`NO` and all 19 declare
`Index=1`. Counting from one, cancelling would mean agreeing on all 19;
counting from zero it is `NO` on all 19. It is the same base as `Start`,
which is 0 for the `In` clip.

So the ○ button does not close the window: **it chooses a specific item**.
And where `Enable=0` it does nothing — on `ClearSave`,
`DeleteSaveDataSelect`, `GameOverSaveSelect` and `GameOverResurrectSelect`,
the four screens where the game demands an answer instead of letting you out.

```
python tools/ui.py drive Continue cerchio out.png
  cerchio  item 2/2 'NO'  -> chose 'NO'  (cancelling)

python tools/ui.py drive ClearSave cerchio out.png
  cerchio  item 1/2 'YES'          the button does nothing
```

Two windows that look identical, and behave differently because the disc
declares it.

### The button bar declares which actions exist

At the bottom of every screen there is a continuous strip that alternates
plates and icons: in the enemy album the seven rectangles run from 673 to 1176
without a gap. The text is in the descriptor, the icons in the scene under a
`KeyAssign` node, and they pair up because each label starts **7-8 px after**
the end of an icon.

```
python tools/ui.py keys EnemyAlbum

  pageStrings     PAGE     x=  681   no icon
  moveStrings     MOVE     x=  812   grey button
  detailsStrings  INFO     x=  937   cross button
  canselStrings   CANCEL   x= 1054   circle button
```

What names the button is **the colour**, which on this hardware is the
button: the ✕ is drawn blue and the ○ red, on the disc's textures. Grey, on
the other hand, separates nothing — the directional pad and the `L1`/`R1`
shoulders are untinted — and stays a single name.

`PAGE` has no icon because it is the first in the strip: what turns pages are
the two arrows at the sides of the page, `Left_Cursor` and `Right_Cursor`,
which are nodes of their own in the scene.

Where the screen **slides**, the pairing cannot be made, and that is not a
defect: the strip is parked off screen with the rest of the scene while the
labels are already in place. These are the same 5 screens as ever.

### The cursor was not ours, and its position measures the text

It was the last piece we supplied ourselves — a hand-drawn triangle — and
there was no need: the scenes carry it, in two different ways.

- **Parked at the origin**, like everything the descriptor places: a
  `Cursor_01` of 16–17 px a side at `(0, 0)`. 7 blocks of 8 do it this way,
  and it goes where `CursorX`/`CursorY` say.
- **One per line, already placed**: the pause menu has nine markers 31 px
  tall, at the positions the descriptor declares item by item — 530 against
  529, 86 against 84. There the cursor does not move: one is switched on and
  the other eight are switched off. It is the same shape as the dungeon map,
  where the scene carries every state and the data says which.

And the cursor is the oracle for **how the text is laid out**, which had been
two numbers calibrated by eye. The font cell is 32×32, and the descriptor puts
the cursor 7 px below the text: 16 px tall inside a 32 px line, it falls
exactly in the middle. So `Y` is the **top edge** of the line and not its
centre, and the scale is **1** and not 1.4.

```
the cursor falls in the middle of the line within 6 px, over 30 items
```

It agrees with the other count, session 7's dialogue box:
`485 + 3×32 + 2×8 = 597` against a body that ends at 598. The same line
height, taken by two routes that know nothing of each other.

### What follows a screen is declared twice in 136

Looking for the link between a screen and the next — which seemed not to
exist — it turns up, but rarely: two screens write it, for three links, always
in the same form, a field at the end of the table whose key equals its value.

```lua
Pause = { ... , PauseTitleSelect = "PauseTitleSelect" };
```

They are `Pause` opening `PauseTitleSelect`, and `GameOver` opening
`GameOverSaveSelect` and `GameOverResurrectSelect`: all three the
**confirmation window** for a choice there is no going back on. Where what
follows is a question, the disc says so; where it is another screen, it does
not.

### Only one thing is ours

That from the last item you wrap to the first. With nine items in pause it is
needed, but the disc does not declare it, so it is a choice and it can be
switched off: `Screen(..., wrap=False)`.

## The page is the floor, with its sign

`setting = {pageMin, pageMax}` sits on the seven `dungeonMapNN_01` and
declares the range of what is paged through. On the dungeon maps that number
is the **floor**, and the sign says whether it is above or below: `B1` is −1,
`1F` is 0, `2F` is +1.

Two independent counts put it to the test:

```
pageMax - pageMin + 1  =  number of floor descriptors          7 dungeons of 7
the printed labels (B2, 5F) fall inside their own range          19 of 19
```

The two left out are the **single-floor** dungeons, which declare `0..0` and
`1..1` though both are `B1`: where there is nothing to page through, the
field is not maintained.

And the order of the files is not the order of the floors — dungeon 5 keeps
them as `1F`, `2F`, `B1` — so a descriptor's floor has to be read, not
counted. The first one, though, **does not declare its own**: it lists the
labels of every floor, because it draws the selector at the side. Its own
floor is found by elimination: it is the one the others have not taken.

```
python tools/ui.py floors 5

  page  -1  B1   dungeonMap05_03
  page   0  1F   dungeonMap05_01
  page   1  2F   dungeonMap05_02
```

All 21 floors of the seven dungeons get their name this way, and in the game
loop `M` opens the map and the arrows **page through the floors** instead of
walking.

## The text was there, and could not be seen

Three defects of ours, one inside the other, and the third only showed once
the first two were gone.

**The permissive tables were needed here too.** `descriptors()` did not load
`host.BOOT`, so 11 files fell silently on a native constant
(`GameDataMapFlags`, `map_manager`): **17 screens** fewer, among them the
enemy album, `Equip` and all seven dungeon maps. There are **136**, not 119.
The same fix had already been in `descriptor_file()` for a session.

**The files are UTF-8 in the data and Shift-JIS in the comments.** The authors
left their notes in their home encoding: 21 files of 618, and the bad byte
always comes right after a `--`. The old fallback — *"if UTF-8 fails, reread
everything as Shift-JIS"* — threw away the whole file because of one note,
and among those 21 is `all.lua.eu`, which by itself declares nearly every
screen. The text came back mangled: **319 of 358**. A Lua comment is ignored
up to the end of the line, so replacing the byte costs nothing.

**And then it showed how much text the disc places.** It is **432** strings,
and **85** were being drawn: only `Message` and `Select` were looked at,
while text also sits in the button bar, in place and floor names, in the
captions (`TitleText`, `Font`, `fontStrings`) and in the menu items. A string
is recognised by having a text **and** a position: the 61 blocks without
`X`/`Y` are data lists (`ItemList`, `LivingList`), names that another part of
the screen will pick up.

So the dungeon map, which used to be mute, now says "Dark Tower" and "3F" —
which is exactly what a map has to say.

*A screen can declare several strings **at the same point**: they are
alternatives the engine chooses between — the album has three at (594,64),
the count, "complete?" and "complete!". Here the first is drawn instead of
stacking them.*

*And it can declare whole alternative blocks: the title has `Menu` and
`ClearMenu`, the same menu before and after finishing the game, and the one in
charge is drawn. What is still uncovered is that a screen also has
alternative **states** not declared as such — on the title "PRESS START
BUTTON" coexists with the menu items, and what tells them apart is not the
position but the moment. Whatever knows which state is active, we have not
found yet.*

## What is missing

- **Where the 15 sliding pieces land**, on 5 screens. See above: it is the
  one end the disc does not declare.
- **The curve** of the clips: here it is linear, so as to invent nothing.
- **What a chosen item does**: `Screen` says *which* item was chosen, not what
  happens next. The link between screens is declared twice in 136 (see
  above), so for the other 134 it has to be looked for elsewhere before it is
  invented — and the only place left is the EBOOT.
- **The wrap-around** of the cursor: the only thing in here that is a choice.
- The screens with dynamic content (`Item`, `Status`) need game data that does
  not exist yet. *(The `dungeonMapXX` are no longer among them: the grid gives
  the rooms and the descriptor the floors.)*
