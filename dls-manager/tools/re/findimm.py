import sys
from capstone import *
d=open(sys.argv[1],'rb').read()
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.skipdata=True
pats=sys.argv[2:]
for i in md.disasm(d[TS:TE],TS):
    s=i.op_str
    if any(p in s for p in pats) and i.mnemonic in('mov','movz','movk','cmp','add','sub','orr','cmn'): print(hex(i.address),i.mnemonic,s)
