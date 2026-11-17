import struct
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
PAGE = 0x7c3000
NDB2 = 0x525310        # NativeDialogButton hook v2 (replaces the one at 0x5252e0)
FIX = 0x525360         # wrapper around FUN_002648f8 (user's next fixture)
FIX_ORIG = 0x5253c0    # first instruction of FUN_002648f8, then back into it
ndb = f"""
lsr w16, w2, #16
mov w17, #0x5a5e
cmp w16, w17
b.ne orig
adrp x16, {PAGE:#x}
and w17, w2, #0xffff
tst w17, #0xc000
b.ne setov
cmp w17, #3
b.eq clr
strb w2, [x16, #0xf00]
ret
setov:
strh w17, [x16, #0xf04]
ret
clr:
strh wzr, [x16, #0xf04]
ret
orig:
str x19, [sp, #-0x20]!
b 0x2b9150
"""
fix = f"""
stp x29, x30, [sp, #-0x30]!
mov x29, sp
stp x1, x2, [sp, #0x10]
str x19, [sp, #0x20]
bl {FIX_ORIG:#x}
mov w19, w0
adrp x16, {PAGE:#x}
ldrh w17, [x16, #0xf04]
cbz w17, done
ldp x1, x2, [sp, #0x10]
and w9, w17, #0x3ff
mov w10, #0x102
tst w17, #0x4000
b.eq away
str w10, [x1]
str w9, [x2]
b done
away:
str w9, [x1]
str w10, [x2]
done:
mov w0, w19
ldr x19, [sp, #0x20]
ldp x29, x30, [sp], #0x30
ret
"""
orig = """
sub sp, sp, #0x60
b 0x2648fc
"""
ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
words = {}
for base, src in ((NDB2, ndb), (FIX, fix), (FIX_ORIG, orig)):
    code = bytes(ks.asm(src, base)[0])
    for i in md.disasm(code, base): print(hex(i.address), i.mnemonic, i.op_str)
    print("end", hex(base + len(code))); print()
    for k in range(len(code) // 4): words[base + 4 * k] = struct.unpack_from("<I", code, 4 * k)[0]
for site, tgt in ((0x2b914c, NDB2), (0x2648f8, FIX)):
    words[site] = struct.unpack("<I", bytes(ks.asm(f"b {tgt:#x}", site)[0]))[0]
    print(hex(site), "-> b", hex(tgt), hex(words[site]))
open("match_hooks.words", "w").write(repr(words))
