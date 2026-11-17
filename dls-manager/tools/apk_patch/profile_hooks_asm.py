import struct, sys
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
FLAG_PAGE, FLAG_OFF = 0x7c3000, 0xf00
FRAME = 0x525280
NDB = 0x5252e0
frame = f"""
adrp x16, {FLAG_PAGE:#x}
ldrb w17, [x16, #{FLAG_OFF:#x}]
cbz w17, go
stp x29, x30, [sp, #-0x20]!
mov x29, sp
str x0, [sp, #0x10]
strb wzr, [x16, #{FLAG_OFF:#x}]
adrp x8, 0x54c000
ldr x8, [x8, #0xc30]
cmp w17, #1
b.ne rel
mov x0, x8
mov w1, #1
bl 0x291f74
b fin
rel:
mov x0, x8
add x1, sp, #0x18
strb wzr, [x1]
mov x2, xzr
bl 0x297030
fin:
ldr x0, [sp, #0x10]
ldp x29, x30, [sp], #0x20
go:
b 0x263db8
"""
ndb = f"""
lsr w16, w2, #16
mov w17, #0x5a5e
cmp w16, w17
b.ne orig
adrp x16, {FLAG_PAGE:#x}
strb w2, [x16, #{FLAG_OFF:#x}]
ret
orig:
str x19, [sp, #-0x20]!
b 0x2b9150
"""
ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
words = {}
for base, src in ((FRAME, frame), (NDB, ndb)):
    code = bytes(ks.asm(src, base)[0])
    for i in md.disasm(code, base): print(hex(i.address), i.mnemonic, i.op_str)
    for k in range(len(code) // 4): words[base + 4 * k] = struct.unpack_from("<I", code, 4 * k)[0]
    print()
    end = base + len(code)
    print("end", hex(end))
for site, tgt, kind in ((0x2b8808, FRAME, "bl"), (0x2b914c, NDB, "b")):
    w = struct.unpack("<I", bytes(ks.asm(f"{kind} {tgt:#x}", site)[0]))[0]
    words[site] = w
    print(hex(site), kind, hex(tgt), hex(w))
open("profile_hooks.words", "w").write(repr(words))
