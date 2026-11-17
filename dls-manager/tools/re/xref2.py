import sys,struct
from capstone import *
d=open(sys.argv[1],'rb').read()
target=int(sys.argv[2],16)
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.detail=True
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins & 0x9f000000 != 0x90000000: continue
    rd=ins&31; immlo=(ins>>29)&3; immhi=(ins>>5)&0x7ffff
    imm=((immhi<<2)|immlo)<<12
    if imm & (1<<32): imm-=(1<<33)
    page=(off&~0xfff)+imm
    if page!=target&~0xfff: continue
    for i in md.disasm(d[off+4:off+40],off+4):
        s=i.op_str
        if i.mnemonic.startswith('ldr') or i.mnemonic.startswith('str') or i.mnemonic=='add':
            regs=s.split(', ')
            name='x%d'%rd
            if ('[%s'%name) in s or (i.mnemonic=='add' and len(regs)>1 and regs[1]==name):
                if hex(target&0xfff) in s:
                    print(hex(off),hex(i.address),i.mnemonic,s)
                break
