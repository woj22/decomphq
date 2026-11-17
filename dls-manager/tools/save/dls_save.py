#!/usr/bin/env python3
"""Read and write DLS19 save files (profile.dat, profile_cld_u.dat, ...).

Format (from libDLS19.so, writer at 0x34754c):
  16-byte header, little endian:
    u16 version   = 1
    u16 flags     = bit 0: encrypted; bits 1-3: padding bytes added to reach whole words
    u32 length    = payload length before padding
    u32 checksum  = Adler-32 (zlib.adler32) seeded 0xabc30526 over the encrypted, padded payload
    u32 raw size  = uncompressed size if the payload is zlib-compressed, else 0
  then the payload: (optionally zlib-compressed) data, zero-padded to a multiple of 4,
  XXTEA-encrypted as 32-bit words with the key below (config block at 0x7bd234).
"""
import struct
import sys
import zlib

KEY = (0x5035EE21, 0xB329A046, 0xBCDF1389, 0x08BA8AF1)
DELTA = 0x9E3779B9
M = 0xFFFFFFFF


def _mx(z, y, s, p, e, k):
    return ((((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4))) ^ ((s ^ y) + (k[(p & 3) ^ e] ^ z))) & M


def xxtea_encrypt(v, k=KEY):
    n = len(v)
    if n < 2:
        return v
    v = list(v)
    rounds = 6 + 52 // n
    s = 0
    z = v[-1]
    for _ in range(rounds):
        s = (s + DELTA) & M
        e = (s >> 2) & 3
        for p in range(n):
            y = v[(p + 1) % n]
            v[p] = (v[p] + _mx(z, y, s, p, e, k)) & M
            z = v[p]
    return v


def xxtea_decrypt(v, k=KEY):
    n = len(v)
    if n < 2:
        return v
    v = list(v)
    rounds = 6 + 52 // n
    s = (rounds * DELTA) & M
    y = v[0]
    for _ in range(rounds):
        e = (s >> 2) & 3
        for p in range(n - 1, -1, -1):
            z = v[(p - 1) % n]
            v[p] = (v[p] - _mx(z, y, s, p, e, k)) & M
            y = v[p]
        s = (s - DELTA) & M
    return v


def load(path):
    raw = open(path, "rb").read()
    ver, flags, length, csum, rawsize = struct.unpack_from("<HHIII", raw, 0)
    body = raw[16:]
    if flags & 1:
        words = struct.unpack("<%dI" % (len(body) // 4), body[: len(body) // 4 * 4])
        body = struct.pack("<%dI" % len(words), *xxtea_decrypt(words))
    body = body[:length]
    if rawsize:
        body = zlib.decompress(body)
    return {"version": ver, "flags": flags, "length": length, "checksum": csum, "rawsize": rawsize}, body


def dump(path, data, version=1):
    """Write data as an encrypted, uncompressed save file (the format profile.dat uses)."""
    pad = (-len(data)) % 4
    body = data + b"\0" * pad
    words = struct.unpack("<%dI" % (len(body) // 4), body)
    enc = struct.pack("<%dI" % len(words), *xxtea_encrypt(words))
    flags = 1 | (pad << 1)
    csum = zlib.adler32(enc, 0xABC30526) & 0xFFFFFFFF
    open(path, "wb").write(struct.pack("<HHIII", version, flags, len(data), csum, 0) + enc)


if __name__ == "__main__":
    hdr, data = load(sys.argv[1])
    print(hdr, len(data))
    if len(sys.argv) > 2:
        open(sys.argv[2], "wb").write(data)
