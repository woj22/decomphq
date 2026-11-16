"""Rename a Bedrock world (levelname.txt + level.dat LevelName) so it imports as a separate world."""
import struct, sys
import amulet_nbt
world, name = sys.argv[1], sys.argv[2]
open(f'{world}/levelname.txt', 'w').write(name)
raw = open(f'{world}/level.dat', 'rb').read()
nbt = amulet_nbt.load(raw[8:], little_endian=True)
nbt.compound['LevelName'] = amulet_nbt.StringTag(name)
data = nbt.save_to(compressed=False, little_endian=True)   # Bedrock level.dat is uncompressed
open(f'{world}/level.dat', 'wb').write(raw[:4] + struct.pack('<I', len(data)) + data)
print('renamed to', name)
