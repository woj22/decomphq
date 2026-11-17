import sys,struct
from capstone import *
d=open(sys.argv[1],'rb').read(); F=int(sys.argv[2],16)
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins>>26 in (0x25,0x05):
        imm=ins&0x3ffffff
        if imm&(1<<25): imm-=1<<26
        if off+imm*4==F:
            pre=[i for i in md.disasm(d[off-24:off],off-24) if 'w1,' in i.op_str]
            print(hex(off), pre[-1].op_str if pre else '?')
