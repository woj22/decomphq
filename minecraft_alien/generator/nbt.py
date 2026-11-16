"""Minimal little-endian NBT writer (Minecraft Bedrock), enough for .mcstructure files."""
import struct

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BARR, STRING, LIST, COMPOUND = range(11)


class Byte(int):
    """Marks a value to be written as TAG_Byte (booleans in block states)."""


def _tag_of(v):
    if isinstance(v, Byte) or isinstance(v, bool):
        return BYTE
    if isinstance(v, int):
        return INT
    if isinstance(v, float):
        return FLOAT
    if isinstance(v, str):
        return STRING
    if isinstance(v, dict):
        return COMPOUND
    if isinstance(v, (list, tuple, IntList)):
        return LIST
    raise TypeError(type(v))


class IntList:
    """A TAG_List of TAG_Int backed by a compact array (block_indices can hold millions of entries)."""

    def __init__(self, arr):
        self.arr = arr


def _str(s):
    b = s.encode('utf-8')
    return struct.pack('<H', len(b)) + b


def _payload(v, out, list_type=None):
    t = _tag_of(v)
    if t == BYTE:
        out.append(struct.pack('<b', int(v)))
    elif t == INT:
        out.append(struct.pack('<i', v))
    elif t == FLOAT:
        out.append(struct.pack('<f', v))
    elif t == STRING:
        out.append(_str(v))
    elif t == COMPOUND:
        for k, x in v.items():
            out.append(struct.pack('<b', _tag_of(x)))
            out.append(_str(k))
            _payload(x, out)
        out.append(b'\x00')
    elif isinstance(v, IntList):
        import numpy as np
        a = np.asarray(v.arr, dtype='<i4')
        out.append(struct.pack('<bi', INT, len(a)))
        out.append(a.tobytes())
    else:   # list
        if len(v) == 0:
            out.append(struct.pack('<bi', list_type if list_type is not None else COMPOUND, 0))
            return
        et = _tag_of(v[0])
        out.append(struct.pack('<bi', et, len(v)))
        for x in v:
            _payload(x, out)


def dumps(root):
    out = [struct.pack('<b', COMPOUND), _str('')]
    _payload(root, out)
    return b''.join(out)
