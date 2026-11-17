import sys
from capstone import *
d=open(sys.argv[1],'rb').read()
a=int(sys.argv[2],16); n=int(sys.argv[3])
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for i in md.disasm(d[a:a+4*n],a): print(hex(i.address),i.mnemonic,i.op_str)
