import sys,struct
d=open(sys.argv[1],'rb').read()
F=int(sys.argv[2],16); want=int(sys.argv[3],16)
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins>>26==0x25:  # BL
        imm=ins&0x3ffffff
        if imm&(1<<25): imm-=1<<26
        if off+imm*4==F:
            for k in range(1,6):
                p=struct.unpack_from('<I',d,off-4*k)[0]
                # movz w0,#imm
                if p&0xffe0001f==0x52800000:
                    v=(p>>5)&0xffff
                    if v==want: print(hex(off))
                    break
