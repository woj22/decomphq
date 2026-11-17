import sys,struct
from capstone import *
d=open(sys.argv[1],'rb').read(); target=int(sys.argv[2],16)
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins & 0x9f000000 != 0x90000000: continue
    rd=ins&31; immlo=(ins>>29)&3; immhi=(ins>>5)&0x7ffff
    imm=((immhi<<2)|immlo)<<12
    if imm & (1<<32): imm-=(1<<33)
    page=(off&~0xfff)+imm
    if page!=target&~0xfff: continue
    r='x%d'%rd; lo='#0x%x'%(target&0xfff)
    for i in md.disasm(d[off+4:off+4+4*80],off+4):
        if lo in i.op_str or '#0x62' in i.op_str and r in i.op_str: print(hex(off),hex(i.address),i.mnemonic,i.op_str)
