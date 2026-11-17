import sys
from capstone import *
d=open(sys.argv[1],'rb').read()
lo,hi=int(sys.argv[2],16),int(sys.argv[3],16); pats=sys.argv[4:]
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.skipdata=True
for i in md.disasm(d[lo:hi],lo):
    if any(p in i.op_str for p in pats) and (i.mnemonic.startswith('st')): print(hex(i.address),i.mnemonic,i.op_str)
