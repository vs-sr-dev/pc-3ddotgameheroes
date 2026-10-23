# The host — `tools/host.py`, `tools/font.py`

The milestone [`STRATEGY.md`](STRATEGY.md) set was: *load a map, run a real
event script and show its message window on screen*. It has been reached.

```
python tools/view.py extract/pac/field_16.ps3.pac \
    --event extract/.../Event/Devil/Devil.lua.eu --skip 14
```

On screen: the map from the `.pac`, the textures from the `TPKG`, the YEBIS
post-processing, and over them the box with `Ｌｅｅ：　ＴｈーＴｈａｔ　ｉｓ　ｔｈｅ
　Ｄａｒｋ　Ｋｉｎｇ　Ｏｎｙｘ！？` drawn in the game's own font, while an
original Lua script runs on a real Lua VM and decides *when* to show it.

No part of that line is ours: the text is in the Lua source, the glyphs in the
`TPKG` atlas, the widths in the `Font.lua.eu` descriptor, the timing in the
script's `Wait` calls.

## What actually runs

```
python tools/host.py coverage extract/.../data/Event

377 of 378 scripts run, 377 reached the end, 0 failed
128 distinct methods, 6,634 calls
43 implemented of 128 used, covering 5,814 of 6,634 calls (87%)
```

The entity registry — `SetNpcDirection`, `CreateNpc`, `Pause`… — is in
[`entities.md`](entities.md), and it is what took coverage from 63% to 87%.

The scripts run **verbatim**: the `.lua.eu` file as it is on the disc, handed
to `lupa` (Lua 5.5). Not a translation, not a subset.

Getting them that far takes two things that are not obvious.

**The shared libraries.** The scripts call functions such as `seafterboss()`
or `setnpccamerac()` that are not host methods: they are ordinary Lua, defined
in `Event/eventfunction.lua.eu` and `Event/eventflag.lua.eu`, and the game's
package manager loads them first. Without them, one event in two dies on its
first line.

**The stubs have to be callable.** A permissive table that does not answer
`__call` makes every function we do not know yet fail. With a `__call` that
returns `nil`, the event carries on and the gap is logged instead of killing
the script.

## The scheduler

An event script always has the same rhythm:

```lua
Event:Wait(0.9);
coroutine.yield();
```

It asks the host for something and yields; the host resumes it when the
request has been met. So the scheduler **interprets nothing**. It only needs
to know when to resume, and three conditions cover the whole event corpus: a
time elapsed (`Wait`), a player input (`WaitContinue`), the end of a sequence
(`WaitScene`).

An implementation note that costs half an hour to anyone who does not know
it: the coroutine's thread **must not cross the boundary** between Lua and
Python. Handed to Python and back, it returns as a function, and
`coroutine.resume` refuses it. The scheduler therefore keeps the thread in a
Lua variable and talks to it through two functions, `__start` and `__step`.

## The native globals

**No** script on the disc defines `EventClass` or `soundList`: the PS3's C++
code supplied them. Here `EventClass.Event` is the host object, and everything
else becomes a permissive table that remembers its own name:

```
soundList.SoundID.SE_quake   ->   "soundList.SoundID.SE_quake"
```

We do not know the numeric value — it is in the EBOOT, Phase 3 — but the name
is enough to run the script and to log *what* was asked for. That is the
difference between a host that stops and a host that measures.

In the same way, every unimplemented method is **counted instead of
failing**. That is the criterion of Phase 5: a script that runs without
calling unknown methods is a finished subsystem.

## The shopping list

Measured, not estimated: the methods the events actually call, in order.

| calls | method | |
|---:|---|---|
| 875 | `Print` | ✅ |
| 472 | `WaitContinue` | ✅ |
| 417 | `CloseMessage` | ✅ |
| 385 | `GetEventFlag` | ✅ |
| 292 | `BackupCamera` | ✅ |
| 290 | `RestoreCamera` | ✅ |
| 258 | `Wait` | ✅ |
| 213 | `SetParamDepthofField` | ✅ |
| 201 | `BackupDof` | ✅ |
| 197 | `RestoreDof` | ✅ |
| 185 | `Pause` | |
| 184 | `Play` | |

**Status: 22 methods implemented of 128 used (and 497 that exist), covering
63% of all calls.** The first ten are all done, and 12 of the first twenty.
The tail is very long and not urgent: 20 methods make 76% of the calls, 30
make 85%.

The group after dialogue was not the one you would expect: **camera** (over
700 calls) and **focus** (another 600). By volume, an event in this game is
almost all framing, which is why those were the two subsystems to do first.

The next group now is **entities**: `Pause` / `Play` (369 calls between them,
the world freezing during a scene), `SetPlayerDirection` / `SetNpcDirection`
(330), `LockPlayer` / `UnlockPlayer` (266). All of them ask for the same thing
that is still missing: a world with characters in it.

### Two wrong measurements, and why

This number was measured wrong twice before it came out right. That is worth
recording, because both mistakes are easy to repeat.

**A failure counted as a success.** The first `coverage` said "376 reached the
end". But a Lua error ended the coroutine, and an ended coroutine was exactly
the criterion I was counting completions by. With `done` separated from
`failed`, the real result was 89 of 378, with 288 scripts dead on a missing
function — which is what led to finding the shared libraries.

**An unimplemented method inflates its own count.** In the same measurement
`Select` and `GetSelect` came out third and fourth, with over a thousand calls
each, and looked like the next priority. They were an artefact: a script that
repeats the choice until it gets a valid answer spins forever if `Select` does
not answer, and every spin counts. Implemented, their real numbers are **56
and 54 calls, twenty-fifth and twenty-sixth place**.

The lesson: a measurement of how an API is used is skewed by exactly the
pieces you have not built yet. It has to be redone after every
implementation, not once.

## The font — `tools/font.py`

`UserInterface/Font/Font.lua.eu` is not a data file dressed up as Lua: it is
Lua, and the same VM loads it. It declares everything — atlas, character
table, size, spacing, and the per-character width table.

- **Atlas**: `Font_eng.ps3.tpk`, 512×2048, 32×32 cells.
- **`Font.bin`**: 688 UTF-16BE code points, one per glyph, in atlas order. It
  starts with the hiragana in あいうえお order, then the katakana, then 387
  kanji and 87 full-width Latin. It has no header: the size divided by two
  gives the number of glyphs, and that is the only reading that leaves no
  stray bytes.
- **Widths**: the font is **proportional** although it has a fixed grid — the
  cell is always 32, the advance is not (`Ｉ` 10, `Ｍ` 18, `ｉ` 6).

In-game text is written full-width (`Ｓｎａｐｓｈｏｔ
　ｆａｉｌｅｄ．`), as RECON §6.4 had already found. A detail you only find by
trying: the atlas has **no hyphen** `－`. The game writes hyphens with `ー`,
the katakana length mark. You can see it in `ＴｈーＴｈａｔ`, which at first
sight looks like an encoding error and is in fact how they wrote it.

## Choices, and the UI descriptors

`Event:Select()` **takes no arguments** in any of the disc's 298 calls, and
`GetSelect()` is compared with 0 in 288 places and with 1 in 9, never with
anything else: it is a fixed yes/no. The two labels are in no event script —
they were native C++ strings — but they are declared, identically, in the
**16 UI descriptors** that have a choice of their own, and that is where we
take them from.

Those descriptors are the "137 declarative UI descriptors" found in Phase 1c,
and seen up close they are a complete interface specification:

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

Three things follow from it:

- the coordinates are in a **1280×720 virtual screen** (`X=640` is the
  centre): the interface is resolution-independent by construction, which
  makes life simpler for a PC port;
- `Cancel = {Enable, Index}` says which option the cancel button picks, so the
  input behaviour is declared too, not written in the code;
- `Animation` declares four clips with a start and a duration — open, hold,
  close, cursor — which are intervals inside the animation of the 3D model
  named by `ScenePackageName`.

The choice window **is a 3D model**, not a drawing: `SelectA/B/C` are `.dsb`
files with their `.tpk`, and the textures hold the frame and the cursor tip as
two separate drawings on the same image. The viewer uses the real frame,
cropped at the first empty column.

## Camera and focus, driven by the script

The signatures are documented nowhere, but the data gives them away, with
some unintended help from the authors. `eventfunction.lua.eu` has two helpers
commented `家NPCカメラ右から` ("NPC camera from the right") and `左から`
("from the left"), and between the two **only the sign of the third
argument** changes:

```lua
Event:SetCameraAtBody(6.12, 19.61,  47.93, n);   -- from the right
Event:SetCameraAtBody(6.12, 19.61, -47.93, n);   -- from the left
Event:SetParamDepthofField(0.73, 0.60, 0.0);
```

So the third is an **azimuth in degrees**. That leaves `6.12` and `19.61`:
distance and elevation — and the elevations across the whole disc lie between
19 and 30 degrees, as you would expect of a camera looking down from above.
The three-argument form of `SetCamera` has the same
`(distance, elevation, azimuth)` structure.

One hypothesis is still to be confirmed in Phase 3: in the six-argument form
the first argument is `0.10` in 170 calls of 170 and has the shape of a
transition time, while the last three are world coordinates, that is, the
point being framed.

The DOF goes straight into the [`post.py`](render.md) chain, and that closes
the YEBIS specification: *the parameters come from the Lua*. `BackupDof` /
`RestoreDof` are a stack, and every event uses it to leave the scene as it
found it.

The unit of the second argument is still unknown, but tying it to the **focus
distance** rather than to the scene radius is the reading that holds in both
use cases: on a close-up at 6 metres, `0.60` gives a sharp band 3.6 metres
deep; on a panorama it widens by itself, as a real lens does.

## Mixed encodings in the corpus

On the first pass 13 scripts of 378 failed to decode. They are not corrupt:
they are in **Shift-JIS**, while all the others are UTF-8. Their content is
developers' comments — `--ボスを倒した場合`, "when the boss is defeated".
Trying the two encodings in order is enough, because UTF-8 fails cleanly on
the bytes 0x80–0x9F.

## What it does not do

- *(Closed in session 7: the dialogue box is now the game's own —
  `UserInterface/Message`, in the two sizes the disc declares, with the text
  where the descriptor puts it. It was not in `data/Balloon`, which is the
  `CHECK`/`TALK`/`OPEN` sign over a character's head: its sizes in world
  units say so, and so do the 352 calls to `CreateBalloon(ActorType)`, which
  create it for an **actor**. See [`ui.md`](ui.md).)*
- Event flags and money exist but live only in memory, with no saving.
- The registry names 99 characters and places **40**: the others are already
  on the map, and the logic grid that declares them has not been read yet —
  see [`entities.md`](entities.md).
- The UI descriptors now **run** — [`ui.md`](ui.md), `tools/ui.py`: 119
  screens composed with their scene, the text where the descriptor puts it
  and the cursor where it says. What is left is the animation, that is, the
  motion between the closed pose and the open one.
- The `/vn` `/vh` `/vl` markup is recognised and stored as a "tone", but
  produces no sound — it is still the hypothesis of RECON §6.4.
