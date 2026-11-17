// Badge-file check hooked from 0x201a58, placed at 0x525200 in libDLS19.so (arm64).
// If DOCS:teamlogo_<id>.png (or _thumb when w1&1) exists, report it as cached;
// otherwise run the original function (its first instruction, then back to 0x201a5c).
sub sp, sp, #0x120
stp x29, x30, [sp, #0x110]
stp x19, x20, [sp, #0x100]
mov w19, w0
mov w20, w1
adrp x3, 0x3e8000
add x3, x3, #0xfdc
sub x9, x3, #0x1b
tst w20, #1
csel x3, x9, x3, ne
mov w4, w19
mov x0, sp
mov w1, #0x100
mov w2, #0x100
bl 0xa7838
mov x0, sp
bl 0x341aa4
mov w8, w0
mov w0, w19
mov w1, w20
ldp x19, x20, [sp, #0x100]
ldp x29, x30, [sp, #0x110]
add sp, sp, #0x120
tbnz w8, #0, have
sub sp, sp, #0x30
b 0x201a5c
have:
mov w0, #1
ret
