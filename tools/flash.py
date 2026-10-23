"""
flash.py - what the game reads from the console's own flash (/dev_flash).

The recompiled game runs on ps3kit, which mounts /dev_flash from a host
directory (`ps3boot --flash DIR`). This game reads one file there, and only
through FMOD Ex: `/dev_flash/sys/external/flashMP3.pic`, the system's MP3
decoder for the SPUs. FMOD loads it while it sets its output up, and when it
cannot, the output fails (`cellMP3Decoder: Error loading MP3 codec`) and the
game retries for ever, on the publishers' logos.

The real file is part of the console's firmware, not of the game: it is in
the firmware update the disc carries (`PS3_UPDATE/PS3UPDAT.PUP`, version
3.15), encrypted, and this repository does not read it yet.

    python tools/flash.py standin build/flash

writes a STAND-IN instead: an SPU ELF header with no sections and no code.
FMOD's loader checks the magic, the machine (SPU, 23) and the section table,
and accepts it, so the output comes up. What is lost is MP3 decoding, which
this disc does not use: it carries no MP3 file (its sounds are 326 WAV files
and its movies Bink). See docs/eboot.md.
"""
import os
import struct
import sys

STANDIN = "sys/external/flashMP3.pic"


def standin_elf():
    """A 32-bit big-endian SPU ELF header: executable, no program headers,
    no sections, entry 0."""
    ident = b"\x7fELF" + bytes([1, 2, 1]) + bytes(9)
    return ident + struct.pack(">HHIIIIIHHHHHH",
                               2,      # e_type: executable
                               23,     # e_machine: SPU
                               1,      # e_version
                               0,      # e_entry
                               0,      # e_phoff
                               0,      # e_shoff
                               0,      # e_flags
                               52,     # e_ehsize
                               32, 0,  # e_phentsize, e_phnum
                               40, 0,  # e_shentsize, e_shnum
                               0)      # e_shstrndx


def main():
    a = sys.argv[1:]
    if len(a) != 2 or a[0] != "standin":
        print(__doc__)
        return 1
    path = os.path.join(a[1], STANDIN)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(standin_elf())
    print(f"{path}: a stand-in for the system's MP3 decoder ({len(standin_elf())} bytes, no code)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
