#!/usr/bin/env python3
"""Build the exhibition-match cave (exhibition.c + the FUN_00273170 entry hook) for patch_apk.py.

Compiles exhibition.c for arm64 with clang, links it at CAVE with ld.lld (game functions and
globals are absolute symbols = their library offsets, so every call/load is pc-relative), and
writes exhibition_words.py: {offset: (original word, new word)} plus the new end of the cave.

Usage: python3 -I exhibition_build.py <libDLS19.so (unpatched)>
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CAVE = 0x5253d0
LIMIT = 0x5260a8          # file offset of the RW segment: the cave must end before it
HOOK = 0x273170           # FUN_00273170 entry: stp x28, x27, [sp, #-0x60]!
SYMS = {
    "PTR_profile": 0x54cc30, "PTR_match": 0x54d950, "PTR_state": 0x54ccc8, "PTR_compinfo": 0x54d928,
    "PTR_compdef": 0x54c4f8, "PAGE": 0x7c3000, "time_plt": 0x8a310, "memcpy_plt": 0x8a4c0,
    "memcpy": 0x8a4c0, "fopen_plt": 0x8ad40, "fprintf_plt": 0x8a610, "fclose_plt": 0x8b390, "FUN_002b9150": 0x2b9150, "FUN_0013f9d8": 0x13f9d8, "memset": 0x8a820, "FUN_00273174": 0x273174, "PROFILE_FRAME": 0x525280,
}
FUNCS = ["002a25f8", "001d8354", "000a4a00", "001d8b34", "0027dc84", "0027eabc", "0027eac4", "00283470",
         "002b5760", "000b35c8", "001d72a0", "001d69f4", "001d6ba8", "00273a9c", "002b70e8", "002b70dc",
         "0027e3fc", "0027e304", "002b6fb0", "00348f2c", "000b5d70", "000acf28", "00227cb8", "001d83ec",
         "001d8ef8", "001d8384", "001d6ed8", "00169f44", "001d728c", "001d72ec", "001d73c4", "0022a548", "0016ac60", "001dc0b8", "001dcdc4", "001d95e0", "001dbd50", "001db894", "000ae0f0", "001dc1d8", "0034da64", "0034db84", "000a45f0", "001693e8", "0016a134", "0027d3d0", "001ed0e4", "002b2318", "0026357c", "0016acb4", "001d8908", "001d8928"]
HOOK_S = """
.text
.global exhibition_hook
exhibition_hook:
    adrp x16, PAGE
    ldrh w17, [x16, #0xf04]
    cbz w17, 1f
    mov w9, #0x102
    cmp w0, w9
    b.eq exhibition_start
    cmp w1, w9
    b.eq exhibition_start
1:  stp x28, x27, [sp, #-0x60]!
    b FUN_00273174

.global frame_wrap
frame_wrap:
    stp x29, x30, [sp, #-0x30]!
    mov x29, sp
    stp x0, x1, [sp, #0x10]
    stp x2, x3, [sp, #0x20]
    bl exhibition_poll
    ldp x0, x1, [sp, #0x10]
    ldp x2, x3, [sp, #0x20]
    ldp x29, x30, [sp], #0x30
    b PROFILE_FRAME

.global ndb_hook
ndb_hook:
    lsr w16, w2, #16
    mov w17, #0x5a5e
    cmp w16, w17
    b.eq ndb_ours
    str x19, [sp, #-0x20]!
    b FUN_002b9150

.global match_screen_hook
match_screen_hook:
    adrp x16, PAGE
    str x0, [x16, #0xf28]
    str d8, [sp, #-0x30]!
    b FUN_0013f9d8
"""
RENDER = 0x1692a8         # FUN_001691d4: bl FUN_001693e8 (draw the screen stack)
MSCREEN = 0x13f9d4        # FUN_0013f9d4 (match screen update): str d8, [sp, #-0x30]!
NDB = 0x2b914c            # FTTJNI.NativeDialogButton: str x19, [sp, #-0x20]!
FRAME = 0x2b8808          # step(): bl FUN_00263db8, patched to bl 0x525280 (profile_hooks_asm.py)


def main():
    lib = open(sys.argv[1], "rb").read()
    t = tempfile.mkdtemp()
    open(os.path.join(t, "hook.S"), "w").write(HOOK_S)
    flags = ["--target=aarch64-linux-android21", "-O2", "-ffreestanding", "-fno-builtin", "-fno-pic",
             "-fno-pie", "-fno-stack-protector", "-fno-jump-tables", "-mgeneral-regs-only" if False else "-O2",
             "-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-c"]
    subprocess.run(["clang"] + flags + [os.path.join(HERE, "exhibition.c"), "-o", os.path.join(t, "ex.o")], check=True)
    subprocess.run(["clang", "--target=aarch64-linux-android21", "-c", os.path.join(t, "hook.S"),
                    "-o", os.path.join(t, "hook.o")], check=True)
    ld = ["SECTIONS { . = %#x; .text : { *(.text.hook) *(.text*) *(.rodata*) } /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) } }" % CAVE]
    for k, v in SYMS.items():
        ld.append("%s = %#x;" % (k, v))
    for f in FUNCS:
        ld.append("FUN_%s = 0x%s;" % (f, f))
    open(os.path.join(t, "ld.x"), "w").write("\n".join(ld))
    subprocess.run(["ld.lld", "-T", os.path.join(t, "ld.x"), "--no-relax", "-o", os.path.join(t, "ex.elf"),
                    os.path.join(t, "hook.o"), os.path.join(t, "ex.o")], check=True)
    subprocess.run(["llvm-objcopy", "-O", "binary", "--only-section=.text", os.path.join(t, "ex.elf"),
                    os.path.join(t, "ex.bin")], check=True)
    nm = subprocess.run(["llvm-nm", os.path.join(t, "ex.elf")], capture_output=True, text=True).stdout
    sym = {l.split()[2]: int(l.split()[0], 16) for l in nm.splitlines() if len(l.split()) == 3}
    code = open(os.path.join(t, "ex.bin"), "rb").read()
    code += b"\0" * (-len(code) % 4)
    end = CAVE + len(code)
    assert end <= LIMIT, hex(end)
    assert sym["exhibition_hook"] == CAVE, sym
    words = {}
    for i in range(0, len(code), 4):
        old = struct.unpack_from("<I", lib, CAVE + i)[0]
        assert old == 0, "cave not empty at %#x" % (CAVE + i)
        words[CAVE + i] = (0, struct.unpack_from("<I", code, i)[0])
    old = struct.unpack_from("<I", lib, HOOK)[0]
    assert old == 0xa9ba6ffc, hex(old)
    words[HOOK] = (old, 0x14000000 | (((CAVE - HOOK) >> 2) & 0x3ffffff))
    old = struct.unpack_from("<I", lib, FRAME)[0]
    assert old == 0x97fead6c, hex(old)
    words[FRAME] = (old, 0x94000000 | (((sym["frame_wrap"] - FRAME) >> 2) & 0x3ffffff))
    old = struct.unpack_from("<I", lib, NDB)[0]
    assert old == 0xf81e0ff3, hex(old)
    words[NDB] = (old, 0x14000000 | (((sym["ndb_hook"] - NDB) >> 2) & 0x3ffffff))
    old = struct.unpack_from("<I", lib, RENDER)[0]
    assert old == 0x94000050, hex(old)
    words[RENDER] = (old, 0x94000000 | (((sym["render_screens_gate"] - RENDER) >> 2) & 0x3ffffff))
    old = struct.unpack_from("<I", lib, MSCREEN)[0]
    assert old == 0xfc1d0fe8, hex(old)
    words[MSCREEN] = (old, 0x14000000 | (((sym["match_screen_hook"] - MSCREEN) >> 2) & 0x3ffffff))
    with open(os.path.join(HERE, "exhibition_words.py"), "w") as f:
        f.write("# generated by exhibition_build.py from exhibition.c - do not edit\n")
        f.write("END = %#x\n" % end)
        f.write("WORDS = {\n")
        for k in sorted(words):
            f.write(" %#x: (%#010x, %#010x),\n" % (k, words[k][0], words[k][1]))
        f.write("}\n")
    subprocess.run(["llvm-objdump", "-d", "--no-show-raw-insn", os.path.join(t, "ex.elf")],
                   stdout=open(os.path.join(t, "ex.dis"), "w"))
    print("cave %#x-%#x (%d bytes), start %#x, full time %#x; disassembly %s" % (
        CAVE, end, len(code), sym.get("exhibition_start", 0), sym.get("exhibition_fulltime", 0),
        os.path.join(t, "ex.dis")))


if __name__ == "__main__":
    main()
