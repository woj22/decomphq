import sys
from capstone import *
from capstone.arm64 import *
d=open(sys.argv[1],'rb').read()
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.detail=False
import struct
tgt_lo,tgt_hi=0x39e168,0x3bb7a8
# fast manual decode of ADRP/ADD
res=[]
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins & 0x9f000000 == 0x90000000:
        rd=ins&31; immlo=(ins>>29)&3; immhi=(ins>>5)&0x7ffff
        imm=((immhi<<2)|immlo)<<12
        if imm & (1<<32): imm-= (1<<33)
        page=(off&~0xfff)+imm
        if 0x39e000<=page<=0x3bb000:
            for k in range(1,6):
                n=struct.unpack_from('<I',d,off+4*k)[0]
                if n & 0xffc00000 == 0x91000000 and ((n>>5)&31)==rd:
                    a=page+((n>>10)&0xfff)
                    if tgt_lo<=a<tgt_hi: res.append((off,a))
                    break
for o,a in res: print(hex(o),hex(a))
