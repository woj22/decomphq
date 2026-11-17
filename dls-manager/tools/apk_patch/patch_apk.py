#!/usr/bin/env python3
"""Rebuild the DLS19 v6.15 APK with our native patches and a replacement classes2.dex.

Usage: python3 -I patch_apk.py <original.apk> <out-unsigned.apk> <classes2.dex>

classes2.dex comes from apktool-rebuilding smali_classes2 after injecting
obb_restore_fix.smali at the top of com/savegame/SavesRestoring.DoSmth.
Every patch checks the original instruction first, so a different build fails loudly.
Then zipalign + sign (we use uber-apk-signer with the public AOSP testkey, which is the
key the source APK was signed with, so it installs over it).
"""
import sys,struct,zipfile,shutil
src,out=sys.argv[1],sys.argv[2]
z=zipfile.ZipFile(src)
lib=bytearray(z.read('lib/arm64-v8a/libDLS19.so'))
MOV_W23_1=struct.pack('<I',0x52800037)
MOV_W23_1_V=0x52800037; NOP=0xd503201f
patches={
 # unlimited player-development sessions per turn
 0xf53cc:(0x531f7c17,MOV_W23_1_V), 0xf714c:(0x531f7c17,MOV_W23_1_V), 0xf7138:(0x2a1f03f7,MOV_W23_1_V),
 # create-player offer: always enable (skip per-tier cap and min-games check)
 0xba2d8:(0x5400014d,0x1400000d),
 # transfer market: always insert create-player card (skip used/enabled/per-period/countdown gates)
 # (gates removed; also re-roll created-player type on every insertion using the CPU timer)
 0xbab1c:(0xf0002568,0xd53be040),
 0xbab20:(0x9119b108,0xd2800189),
 0xbab24:(0x39400109,0x9ac9080a),
 0xbab28:(0x35ffdda9,0x9b098140),
 0xbab2c:(0x39400908,0xf0002568),
 0xbab30:(0x34ffdd68,0xb9066100),
 0xbab38:(0x910082f5,0xd503201f),
 0xbab3c:(0xaa1503e0,0xd503201f),
 0xbab40:(0x94070fe7,0xd503201f),
 0xbab44:(0x3707dcc0,0xd503201f),
 0xbab48:(0xaa1503e0,0xd503201f),
 0xbab4c:(0x94071314,0xd503201f),
 0xbab50:(0x72001c1f,0xd503201f),
 0xbab54:(0x54ffdc41,0xd503201f),
 # player development: after results popup, return dialog to 'ready' state (0) instead of 'close' (2)
 0x10ae4c:(0x52800049,0x52800009),
 # player development: skip results popup -> call its close-callback directly, continue
 0x10adc8:(0x5280b200,0x9400001b), 0x10adcc:(0x2a1f03e1,0x1400000f),
}
for off,(orig,repl) in patches.items():
    cur=struct.unpack_from('<I',lib,off)[0]
    assert cur==orig,(hex(off),hex(cur))
    lib[off:off+4]=struct.pack('<I',repl)
zo=zipfile.ZipFile(out,'w')
for info in z.infolist():
    if info.filename.startswith('META-INF/') and info.filename.split('/')[-1].upper().endswith(('.SF','.RSA','.DSA','.EC','MANIFEST.MF')): continue
    data=bytes(lib) if info.filename=='lib/arm64-v8a/libDLS19.so' else (open(sys.argv[3],'rb').read() if info.filename=='classes2.dex' else z.read(info.filename))
    ni=zipfile.ZipInfo(info.filename,info.date_time); ni.compress_type=info.compress_type; ni.external_attr=info.external_attr
    zo.writestr(ni,data)
zo.close(); print('ok')
