#!/usr/bin/env python3
"""Build android/native/dlsmgr.c into libdlsmgr.so (arm64) with plain clang + lld, no NDK:
no libc or other libraries are linked (the code uses libDLS19's functions and JNI tables).

Usage: python3 -I build_native.py <out libdlsmgr.so>
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "android", "native", "dlsmgr.c")


def main():
    out = sys.argv[1]
    subprocess.run(["clang", "--target=aarch64-linux-android21", "-O2", "-fPIC", "-shared", "-nostdlib",
                    "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fvisibility=default",
                    "-Wl,-soname,libdlsmgr.so", "-Wl,--hash-style=both", "-Wl,-z,max-page-size=16384",
                    "-Wl,--no-undefined", "-o", out, SRC], check=True)
    print("built", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
