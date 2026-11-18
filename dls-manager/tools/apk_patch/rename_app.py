#!/usr/bin/env python3
"""Rename the app: Assistant Manager 27 (Settings, app info) / Assistant Manager (under the icon).

resources.arsc: string/app_name ("Dream League", used by the launcher activity's label) becomes
the short name. AndroidManifest.xml (binary XML): the <application> label stops pointing at
app_name and becomes the long name, a new string in the manifest's own string pool.

Both edits rebuild the string pool chunk (strings re-encoded in the pool's own UTF-8 / UTF-16
form, styles copied as they are) and fix the sizes of the chunks around it.

Usage: python3 -I rename_app.py --apk app.apk --out-dir dir [--short "..."] [--long "..."]
       writes dir/resources.arsc and dir/AndroidManifest.xml
"""
import argparse
import os
import struct
import zipfile

UTF8 = 0x100


def read_pool(b, off):
    typ, hs, size, n, ns, flags, ss, sts = struct.unpack_from("<HHIIIIII", b, off)
    assert typ == 0x0001
    offs = struct.unpack_from("<%dI" % n, b, off + hs)
    soffs = struct.unpack_from("<%dI" % ns, b, off + hs + 4 * n)
    utf8 = bool(flags & UTF8)
    base = off + ss
    strs = []
    for o in offs:
        p = base + o
        if utf8:
            def ln(p):
                v = b[p]
                if v & 0x80:
                    return ((v & 0x7f) << 8) | b[p + 1], p + 2
                return v, p + 1
            _, p = ln(p)
            m, p = ln(p)
            strs.append(b[p:p + m].decode("utf-8", "replace"))
        else:
            v = struct.unpack_from("<H", b, p)[0]
            p += 2
            if v & 0x8000:
                v = ((v & 0x7fff) << 16) | struct.unpack_from("<H", b, p)[0]
                p += 2
            strs.append(b[p:p + v * 2].decode("utf-16-le", "replace"))
    styles = b[off + sts: off + size] if ns else b""
    return {"off": off, "size": size, "hs": hs, "flags": flags, "strs": strs, "soffs": soffs, "styles": styles, "utf8": utf8}


def enc(s, utf8):
    if utf8:
        u = s.encode("utf-8")
        def ln(v):
            return bytes([v]) if v < 0x80 else bytes([0x80 | (v >> 8), v & 0xff])
        return ln(len(s)) + ln(len(u)) + u + b"\0"
    u = s.encode("utf-16-le")
    n = len(u) // 2
    head = struct.pack("<H", n) if n < 0x8000 else struct.pack("<HH", 0x8000 | (n >> 16), n & 0xffff)
    return head + u + b"\0\0"


def write_pool(P):
    data, offs = b"", []
    for s in P["strs"]:
        offs.append(len(data))
        data += enc(s, P["utf8"])
    data += b"\0" * (-len(data) % 4)
    n, ns = len(P["strs"]), len(P["soffs"])
    ss = P["hs"] + 4 * n + 4 * ns
    sts = ss + len(data) if ns else 0
    size = ss + len(data) + len(P["styles"])
    head = struct.pack("<HHIIIIII", 0x0001, P["hs"], size, n, ns, P["flags"], ss, sts)
    head += b"\0" * (P["hs"] - len(head))
    return head + struct.pack("<%dI" % n, *offs) + struct.pack("<%dI" % ns, *P["soffs"]) + data + P["styles"]


def rename_arsc(b, old, new):
    hs = struct.unpack_from("<H", b, 2)[0]
    P = read_pool(b, hs)
    hits = [i for i, s in enumerate(P["strs"]) if s == old]
    assert hits, "app name string not found"
    for i in hits:
        P["strs"][i] = new
    pool = write_pool(P)
    out = bytearray(b[:hs] + pool + b[hs + P["size"]:])
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out), len(hits)


def relabel_manifest(b, label):
    P = read_pool(b, 8)
    idx = len(P["strs"])
    P["strs"].append(label)
    pool = write_pool(P)
    out = bytearray(b[:8] + pool + b[8 + P["size"]:])
    struct.pack_into("<I", out, 4, len(out))
    strs = P["strs"]
    p = 8 + len(pool)
    done = False
    while p < len(out):
        typ, chs, size = struct.unpack_from("<HHI", out, p)
        if typ == 0x0102:
            name = struct.unpack_from("<I", out, p + 20)[0]
            ast, asz, acnt = struct.unpack_from("<HHH", out, p + 24)
            if strs[name] == "application":
                for k in range(acnt):
                    q = p + 16 + ast + k * asz
                    an = struct.unpack_from("<I", out, q + 4)[0]
                    if strs[an] == "label":
                        struct.pack_into("<I", out, q + 8, idx)           # raw value
                        struct.pack_into("<HBBI", out, q + 12, 8, 0, 0x03, idx)  # typed: string
                        done = True
                break
        p += size
    assert done, "<application android:label> not found"
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--old", default="Dream League")
    ap.add_argument("--short", default="Assistant Manager")
    ap.add_argument("--long", default="Assistant Manager 27")
    a = ap.parse_args()
    z = zipfile.ZipFile(a.apk)
    os.makedirs(a.out_dir, exist_ok=True)
    arsc, n = rename_arsc(z.read("resources.arsc"), a.old, a.short)
    open(os.path.join(a.out_dir, "resources.arsc"), "wb").write(arsc)
    man = relabel_manifest(z.read("AndroidManifest.xml"), a.long)
    open(os.path.join(a.out_dir, "AndroidManifest.xml"), "wb").write(man)
    print(f"app_name -> {a.short!r} ({n} string), application label -> {a.long!r}")


if __name__ == "__main__":
    main()
