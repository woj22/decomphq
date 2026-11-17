import sys,struct
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
f=open(sys.argv[1],'rb'); e=ELFFile(f)
rel={}
for s in e.iter_sections():
    if isinstance(s,RelocationSection):
        for r in s.iter_relocations():
            if r['r_info_type']==1027: rel[r['r_offset']]=r['r_addend']
import pickle; pickle.dump(rel,open(sys.argv[2],'wb')); print(len(rel))
