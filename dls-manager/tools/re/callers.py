import sys,struct
d=open(sys.argv[1],'rb').read()
TS,TE=0x8b4e0,0x8b4e0+0x3126b0
F=[int(x,16) for x in sys.argv[2:]]
for off in range(TS,TE,4):
    ins=struct.unpack_from('<I',d,off)[0]
    if ins>>26 in (0x25,0x05):
        imm=ins&0x3ffffff
        if imm&(1<<25): imm-=1<<26
        t=off+imm*4
        if t in F: print(hex(t),'<-',hex(off),'bl' if ins>>26==0x25 else 'b')
