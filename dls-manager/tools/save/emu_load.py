#!/usr/bin/env python3
"""Run the game's own profile loader (libDLS19.so FUN_00297030) on a decoded profile under
Unicorn, to check a converted save before it goes on the phone.

Prints the stream position at each section reader and stops at the end of the read
(FUN_003472d0) or at the first fault, with a backtrace of the section readers.

Usage: python3 -I emu_load.py <libDLS19.so> <profile.dat> [--trace-comp]
"""
import struct
import sys
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_INVALID, UcError
from unicorn.arm64_const import *

sys.path.insert(0, os.path.dirname(__file__))
import dls_save as S  # noqa: E402

B = 0x40000000          # lib base
STUB = 0x10000000       # import stubs
HEAP = 0x20000000
STACK = 0x30000000
MISC = 0x38000000       # stream object, tls, magic return

SECTIONS = {
    0x297030: "profile_load", 0x0a6f78: "custom_players", 0x0adfb8: "squad", 0x0b7308: "development",
    0x0b8800: "b8800", 0x27ce1c: "season_free", 0x280898: "season_read", 0x27fa40: "season_hdr",
    0x2829a8: "divisions", 0x286f50: "competitions", 0x26ae38: "competition", 0x286718: "s+720",
    0x283db4: "s+8c8", 0x2837cc: "s+950", 0x2668fc: "s+978", 0x280258: "s+9a8", 0x28467c: "s+9c0",
    0x281ad0: "s+18a0", 0x0a9bc0: "s+1920", 0x2a2054: "p+1840", 0x2a4b6c: "p+18d4", 0x29b158: "p+8a00",
    0x2a4f80: "p+a992", 0x29b79c: "p+a994", 0x29ea1c: "p+a9cc", 0x29d784: "p+2a972", 0x293a28: "p+aa8f",
    0x2948cc: "p+aade", 0x29442c: "p+aa94", 0x294b98: "p+aaee", 0x294cc4: "p+aaf2", 0x294e40: "p+ab08",
    0x2977cc: "p+ac06", 0x29527c: "p+abaf",
}
SKIP = [0x0b291c, 0x0ae184, 0x12656c, 0x0b2c54, 0x0b3930, 0x126ce8, 0x29798c, 0x0b6a10, 0x0a1a08,
        0x277ff0, 0x2a4a0c, 0x0bfb64, 0x0b8ae8, 0x27ca4c]


def main():
    lib, prof = sys.argv[1], sys.argv[2]
    trace_comp = "--trace-comp" in sys.argv
    _, payload = S.load(prof)
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    f = open(lib, "rb")
    elf = ELFFile(f)
    top = 0
    for seg in elf.iter_segments():
        if seg["p_type"] == "PT_LOAD":
            top = max(top, seg["p_vaddr"] + seg["p_memsz"])
    top = (top + 0xFFFF) & ~0xFFFF
    uc.mem_map(B, top)
    for seg in elf.iter_segments():
        if seg["p_type"] == "PT_LOAD":
            uc.mem_write(B + seg["p_vaddr"], seg.data())
    dynsym = elf.get_section_by_name(".dynsym")
    stubs = {}
    names = {}
    for sec in elf.iter_sections():
        if not isinstance(sec, RelocationSection):
            continue
        for r in sec.iter_relocations():
            t, off = r["r_info_type"], r["r_offset"]
            add = r["r_addend"] if r.is_RELA() else 0
            if t == 1027:  # RELATIVE
                uc.mem_write(B + off, struct.pack("<Q", B + add))
                continue
            sym = dynsym.get_symbol(r["r_info_sym"])
            if sym["st_shndx"] != "SHN_UNDEF" and sym["st_value"]:
                val = B + sym["st_value"] + add
            else:
                if sym.name not in stubs:
                    stubs[sym.name] = STUB + 4 * len(stubs)
                    names[stubs[sym.name]] = sym.name
                val = stubs[sym.name]
            uc.mem_write(B + off, struct.pack("<Q", val))
    uc.mem_map(STUB, 0x100000)
    uc.mem_write(STUB, b"\xc0\x03\x5f\xd6" * (0x100000 // 4))  # ret
    uc.mem_map(HEAP, 0x4000000)
    uc.mem_map(STACK, 0x100000)
    uc.mem_map(MISC, 0x10000)
    uc.reg_write(UC_ARM64_REG_TPIDR_EL0, MISC + 0x8000)
    uc.reg_write(UC_ARM64_REG_SP, STACK + 0xF0000)
    # cpacr: enable fp/simd
    uc.reg_write(UC_ARM64_REG_CPACR_EL1, 0x300000)

    heap = [HEAP]

    def alloc(n):
        p = heap[0]
        heap[0] = (heap[0] + n + 15) & ~15
        uc.mem_write(p, b"\0" * n)
        return p

    # stream object: [0] reader obj; +8 hash; +0x10 xor; +0x14/16 adler; +0x18 version; +0x1c write flag
    STR = MISC + 0x100
    RDR = MISC + 0x200
    VT = MISC + 0x300
    READ = MISC + 0x400
    END = MISC + 0x500
    uc.mem_write(READ, b"\xc0\x03\x5f\xd6")
    uc.mem_write(END, b"\x00\x00\x00\x14")  # b . (stop hook)
    uc.mem_write(VT, struct.pack("<8Q", *[READ] * 8))
    uc.mem_write(RDR, struct.pack("<Q", VT))
    hdr = bytearray(0x28)
    struct.pack_into("<QQQ", hdr, 0, RDR, 0xbadf00dedeadbeef, 0xa45e37bddeadbeef)  # FUN_00347eac seeds
    uc.mem_write(STR, bytes(hdr))
    pos = [0]
    stack = []
    log = []
    reads = []
    done = [False]

    def on_read(uc_, addr, size, ud):
        buf, n = uc.reg_read(UC_ARM64_REG_X1), uc.reg_read(UC_ARM64_REG_X2)
        chunk = payload[pos[0]:pos[0] + n]
        uc.mem_write(buf, chunk + b"\0" * (n - len(chunk)))
        if os.environ.get("RLOG"):
            reads.append((pos[0], n, uc.reg_read(UC_ARM64_REG_LR) - B, bytes(chunk)))
        pos[0] += n
        uc.reg_write(UC_ARM64_REG_X0, len(chunk))
    uc.hook_add(UC_HOOK_CODE, on_read, begin=READ, end=READ)

    def ret0(uc_, addr, size, ud):
        uc.reg_write(UC_ARM64_REG_X0, 0)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

    def on_alloc(uc_, addr, size, ud):
        n = uc.reg_read(UC_ARM64_REG_X0)
        if n > 0x1000000:
            n = 16
        uc.reg_write(UC_ARM64_REG_X0, alloc(n + 16) + 8)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    for a in (0x346b68, 0x346b60):
        uc.hook_add(UC_HOOK_CODE, on_alloc, begin=B + a, end=B + a)
    for a in SKIP + [0x34649c]:
        uc.hook_add(UC_HOOK_CODE, ret0, begin=B + a, end=B + a)

    def on_open(uc_, addr, size, ud):
        uc.reg_write(UC_ARM64_REG_X0, STR)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE, on_open, begin=B + 0x347154, end=B + 0x347154)

    def on_finish(uc_, addr, size, ud):
        log.append(("END", pos[0]))
        st = bytes(uc.mem_read(STR, 0x20))
        h, x, a1, a2 = struct.unpack_from("<QIHH", st, 8)
        want = (x << 32) | (a1 << 16) | a2
        got = struct.unpack_from("<Q", payload, pos[0])[0] if pos[0] + 8 <= len(payload) else None
        log.append(("checksum " + ("OK" if got in (want, h) else f"BAD file {got} want {want:x}"), pos[0]))
        done[0] = True
        uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE, on_finish, begin=B + 0x3472d0, end=B + 0x3472d0)

    def on_stub(uc_, addr, size, ud):
        nm = names.get(addr, "?")
        x0, x1, x2 = (uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2))
        if nm in ("malloc", "calloc", "_Znwm", "_Znam", "operator new"):
            uc.reg_write(UC_ARM64_REG_X0, alloc(max(1, x0 * (x1 if nm == "calloc" else 1))))
        elif nm in ("memcpy", "memmove"):
            uc.mem_write(x0, bytes(uc.mem_read(x1, x2)))
        elif nm in ("__strlcpy_chk", "strlcpy", "strncpy", "__strncpy_chk", "strcpy", "__strcpy_chk"):
            n = x2 if nm != "strcpy" and nm != "__strcpy_chk" else 4096
            src = bytes(uc.mem_read(x1, n))
            src = src.split(b"\0", 1)[0][:max(0, n - 1)]
            uc.mem_write(x0, src + b"\0" * (n - len(src)))
            uc.reg_write(UC_ARM64_REG_X0, len(src))
        elif nm == "strlen":
            src = bytes(uc.mem_read(x0, 4096))
            uc.reg_write(UC_ARM64_REG_X0, src.index(b"\0"))
        elif nm == "memset":
            uc.mem_write(x0, bytes([x1 & 0xFF]) * x2)
        elif nm == "__stack_chk_fail":
            raise SystemExit("stack check failed")
        else:
            uc.reg_write(UC_ARM64_REG_X0, 0)
    uc.hook_add(UC_HOOK_CODE, on_stub, begin=STUB, end=STUB + 0x100000)

    def on_sec(uc_, addr, size, ud):
        nm = SECTIONS[addr - B]
        log.append((nm, pos[0]))
        if trace_comp or nm != "competition":
            pass
    for a in SECTIONS:
        uc.hook_add(UC_HOOK_CODE, on_sec, begin=B + a, end=B + a)

    # fake team table with the Dream FC entry (0x102) for the squad reader
    tbl = alloc(0x108)
    uc.mem_write(tbl, struct.pack("<I", 0x102))
    db = alloc(0x80)
    uc.mem_write(db + 0x20, struct.pack("<Q", tbl))
    uc.mem_write(db + 0x28, struct.pack("<I", 1))
    uc.mem_write(B + 0x569380, struct.pack("<Q", db))
    # the opener reads the version word through the stream (it counts in the checksum)
    uc.reg_write(UC_ARM64_REG_X0, STR)
    uc.reg_write(UC_ARM64_REG_X1, STR + 0x18)
    uc.reg_write(UC_ARM64_REG_X2, 0xFFFFFFFF)
    uc.reg_write(UC_ARM64_REG_LR, END)
    uc.emu_start(B + 0x0abab4, END)
    # --comp-squad-from <save>: read the competitions with that save's squad (the squad they
    # were written with); everything else sees the file's own squad.
    if "--comp-squad-from" in sys.argv:
        _, bp = S.load(sys.argv[sys.argv.index("--comp-squad-from") + 1])
        n = bp[0x20]
        o = 0x21 + n * 0xAE  # squad section: u32 258, u32 count, 32 x u32 info, 32 x u32 ids
        cnt = struct.unpack_from("<I", bp, o + 4)[0]
        ids = bp[o + 8 + 128:o + 8 + 256]
        oldt = alloc(0x108)
        uc.mem_write(oldt, struct.pack("<II", 0x102, cnt) + bp[o + 8:o + 8 + 128] + ids)
        lc = [False]

        def l_on(u, a, s_, d):
            lc[0] = True

        def l_off(u, a, s_, d):
            lc[0] = False

        def l_lookup(u, a, s_, d):
            if lc[0] and not done[0] and uc.reg_read(UC_ARM64_REG_X0) & 0xFFFFFFFF == 0x102:
                uc.reg_write(UC_ARM64_REG_X0, oldt)
                uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
        uc.hook_add(UC_HOOK_CODE, l_on, begin=B + 0x286f50, end=B + 0x286f50)
        uc.hook_add(UC_HOOK_CODE, l_off, begin=B + 0x286718, end=B + 0x286718)
        uc.hook_add(UC_HOOK_CODE, l_lookup, begin=B + 0x0ae0f0, end=B + 0x0ae0f0)
    prof_obj = struct.unpack("<Q", uc.mem_read(B + 0x54cc30, 8))[0]
    uc.reg_write(UC_ARM64_REG_X0, prof_obj)
    uc.reg_write(UC_ARM64_REG_X1, MISC + 0x600)
    uc.reg_write(UC_ARM64_REG_X2, 0)
    uc.reg_write(UC_ARM64_REG_LR, END)
    err = None
    try:
        uc.emu_start(B + 0x297030, END, count=200_000_000)
    except UcError as e:
        err = e
    for nm, p in log:
        if nm == "competition" and not trace_comp:
            print(f"  competition @0x{p:x}  bytes {payload[p:p+12].hex()}")
        else:
            print(f"{nm:16s} @0x{p:x}")
    pc = uc.reg_read(UC_ARM64_REG_PC)
    print(f"pc lib+0x{pc - B:x} lr 0x{uc.reg_read(UC_ARM64_REG_LR):x}")
    if err:
        print(f"FAULT {err} at lib+0x{pc - B:x}  x0..x2", [hex(uc.reg_read(r)) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)])
    if os.environ.get("RLOG"):
        with open(os.environ["RLOG"], "w") as fo:
            for r in reads:
                fo.write(f"{r[0]:x} {r[1]} {r[2]:x} {r[3].hex()}\n")
    print(f"stream pos 0x{pos[0]:x} of 0x{len(payload):x}; error flag {uc.mem_read(STR + 0x1e, 1)[0]}")
    if err or not done[0]:
        sys.exit(1)
    if not any(nm == "checksum OK" for nm, _ in log) and "--comp-squad-from" not in sys.argv:
        sys.exit(2)
    if "--division" in sys.argv:
        # the player's division index in the loaded season (FUN_00283470)
        STOP2 = MISC + 0x1800
        uc.mem_write(STOP2, b"\x00\x00\x00\x14")
        uc.reg_write(UC_ARM64_REG_X0, prof_obj + 0x20)
        uc.reg_write(UC_ARM64_REG_LR, STOP2)
        uc.reg_write(UC_ARM64_REG_SP, STACK + 0xF0000)
        uc.emu_start(B + 0x283470, STOP2)
        print("division index", uc.reg_read(UC_ARM64_REG_X0) & 0xFFFFFFFF)
    if "--rewrite" in sys.argv:
        out_path = sys.argv[sys.argv.index("--rewrite") + 1]
        rewrite(uc, payload, prof_obj, alloc, out_path, prof)


def rewrite(uc, payload, prof_obj, alloc, out_path, prof):
    """Write the loaded profile back out with the game's own writer (FUN_00291f74). Competition
    player stats are written as if no player were in the user's squad, so the result loads
    with any squad."""
    WS = MISC + 0x1000
    WR = MISC + 0x1100
    WVT = MISC + 0x1200
    WRITE = MISC + 0x1300
    STOP = MISC + 0x1400
    uc.mem_write(WRITE, b"\xc0\x03\x5f\xd6")
    uc.mem_write(STOP, b"\x00\x00\x00\x14")
    uc.mem_write(WVT, struct.pack("<8Q", *[WRITE] * 8))
    uc.mem_write(WR, struct.pack("<Q", WVT))
    h = bytearray(0x28)
    struct.pack_into("<QQQ", h, 0, WR, 0xbadf00dedeadbeef, 0xa45e37bddeadbeef)
    struct.pack_into("<I", h, 0x18, struct.unpack_from("<I", payload, 0)[0])
    h[0x1c] = 1
    uc.mem_write(WS, bytes(h))
    out = bytearray()
    in_comp = [False]

    def on_write(uc_, a, sz, ud):
        buf, n = uc.reg_read(UC_ARM64_REG_X1), uc.reg_read(UC_ARM64_REG_X2)
        out.extend(uc.mem_read(buf, n))
        uc.reg_write(UC_ARM64_REG_X0, n)
    uc.hook_add(UC_HOOK_CODE, on_write, begin=WRITE, end=WRITE)

    def jump_ret(val):
        uc.reg_write(UC_ARM64_REG_X0, val)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE, lambda u, a, s_, d: jump_ret(0), begin=B + 0x347864, end=B + 0x347864)
    uc.hook_add(UC_HOOK_CODE, lambda u, a, s_, d: jump_ret(WS), begin=B + 0x34731c, end=B + 0x34731c)
    ts = struct.unpack_from("<Q", payload, 0x18)[0]
    uc.hook_add(UC_HOOK_CODE, lambda u, a, s_, d: jump_ret(ts), begin=B + 0x348b54, end=B + 0x348b54)
    uc.hook_add(UC_HOOK_CODE, lambda u, a, s_, d: jump_ret(0), begin=B + 0x29553c, end=B + 0x29553c)

    def fin(u, a, s_, d):
        st = bytes(uc.mem_read(WS, 0x20))
        x, a1, a2 = struct.unpack_from("<IHH", st, 0x10)
        out.extend(struct.pack("<Q", (x << 32) | (a1 << 16) | a2))
        uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE, fin, begin=B + 0x347394, end=B + 0x347394)

    def comp_on(u, a, s_, d):
        in_comp[0] = True
    def comp_off(u, a, s_, d):
        in_comp[0] = False
    uc.hook_add(UC_HOOK_CODE, comp_on, begin=B + 0x286f50, end=B + 0x286f50)
    uc.hook_add(UC_HOOK_CODE, comp_off, begin=B + 0x286718, end=B + 0x286718)
    empty = alloc(0x108)
    uc.mem_write(empty, struct.pack("<II", 0x102, 0))

    def squad_lookup(u, a, s_, d):
        if in_comp[0] and uc.reg_read(UC_ARM64_REG_X0) & 0xFFFFFFFF == 0x102:
            jump_ret(empty)
    if "--keep-squad" not in sys.argv:
        uc.hook_add(UC_HOOK_CODE, squad_lookup, begin=B + 0x0ae0f0, end=B + 0x0ae0f0)
    # guards in the writer
    uc.mem_write(B + 0x685034, b"\0")
    uc.mem_write(B + 0x685024, b"\1")
    for g in (0x54cff0, 0x54c6f0):
        t = struct.unpack("<Q", uc.mem_read(B + g, 8))[0]
        uc.mem_write(t, b"\1")
    uc.reg_write(UC_ARM64_REG_SP, STACK + 0xF0000)
    uc.reg_write(UC_ARM64_REG_X0, WS)
    uc.reg_write(UC_ARM64_REG_X1, WS + 0x18)
    uc.reg_write(UC_ARM64_REG_X2, 0xFFFFFFFF)
    uc.reg_write(UC_ARM64_REG_LR, STOP)
    uc.emu_start(B + 0x0abab4, STOP)
    uc.reg_write(UC_ARM64_REG_X0, prof_obj)
    uc.reg_write(UC_ARM64_REG_X1, 0)
    uc.reg_write(UC_ARM64_REG_LR, STOP)
    uc.emu_start(B + 0x291f74, STOP, count=200_000_000)
    print(f"rewritten payload {len(out)} bytes (was {len(payload)})")
    hdr, _ = S.load(prof)
    S.dump(out_path, bytes(out))


if __name__ == "__main__":
    main()
