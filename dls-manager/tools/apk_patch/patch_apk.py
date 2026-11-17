#!/usr/bin/env python3
"""Rebuild the DLS19 v6.15 APK with our native patches and a replacement classes2.dex.

Usage: python3 -I patch_apk.py <original.apk> <out-unsigned.apk> <classes2.dex> [assets/path=local_file ...]

Extra "assets/...=file" arguments replace those APK entries (e.g. rebuilt database files
from tools/db/build_all.py: assets/data/db/players.dat=out/players.dat), or add them if
the APK does not have them yet (team badges assets/data/fe/teams/t<slot>.png).

classes2.dex comes from apktool-rebuilding smali_classes2 after injecting
obb_restore_fix.smali at the top of com/savegame/SavesRestoring.DoSmth.
Every patch checks the original instruction first, so a different build fails loudly.
Then zipalign + sign (we use uber-apk-signer with the public AOSP testkey, which is the
key the source APK was signed with, so it installs over it).
"""
import sys,struct,zipfile,shutil
src,out=sys.argv[1],sys.argv[2]
replace=dict(a.split('=',1) for a in sys.argv[4:])
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
 # team badges: skip the generated-logo table (CustomLogoInfo) so assets/data/fe/teams/t<id>.png is used
 0x166ae0:(0xb4000180,0x1400000c),
 # Imported kit/badge table (0xa74dc): the game only looked for DOCS:<id>_home.png etc. (and
 # DOCS:t<id>.png badges) for the Dream Team (258), and only after a URL import. Check the
 # files for every team instead, so kits/badges dropped in the documents folder are used.
 0xa75c8:(0x54000b61,0xd503201f),   # b.ne <not dream team> -> nop
 0xa7638:(0x710022df,0x1400000a),   # skip the "URL set in profile" check -> file check at 0xa7660
 # Team badges: the game draws badges from mask templates and caches them as
 # DOCS:teamlogo_<id>.png / teamlogo_<id>_thumb.png, but only trusts its own 64-entry cache
 # list. Hook the cache check (0x201a58): if the file exists in DOCS, use it; otherwise run
 # the original code. New code lives in the unused tail of the executable segment's last
 # page (0x525200, assembled from tools/apk_patch/logo_cave.s); the LOAD header is grown
 # to cover it.
 0x60:(0x005251c8,0x00525270), 0x68:(0x005251c8,0x00525270),   # PT_LOAD[0] p_filesz, p_memsz
 0x201a58:(0xd100c3ff,0x140c8dea),   # sub sp,sp,#0x30 -> b 0x525200
 0x525200:(0x0,0xd10483ff), 0x525204:(0x0,0xa9117bfd), 0x525208:(0x0,0xa91053f3), 0x52520c:(0x0,0x2a0003f3),
 0x525210:(0x0,0x2a0103f4), 0x525214:(0x0,0xf0fff603), 0x525218:(0x0,0x913f7063), 0x52521c:(0x0,0xd1006c69),
 0x525220:(0x0,0x7200029f), 0x525224:(0x0,0x9a831123), 0x525228:(0x0,0x2a1303e4), 0x52522c:(0x0,0x910003e0),
 0x525230:(0x0,0x52802001), 0x525234:(0x0,0x52802002), 0x525238:(0x0,0x97ee0980), 0x52523c:(0x0,0x910003e0),
 0x525240:(0x0,0x97f87219), 0x525244:(0x0,0x2a0003e8), 0x525248:(0x0,0x2a1303e0), 0x52524c:(0x0,0x2a1403e1),
 0x525250:(0x0,0xa95053f3), 0x525254:(0x0,0xa9517bfd), 0x525258:(0x0,0x910483ff), 0x52525c:(0x0,0x37000068),
 0x525260:(0x0,0xd100c3ff), 0x525264:(0x0,0x17f371fe), 0x525268:(0x0,0x52800020), 0x52526c:(0x0,0xd65f03c0),
}
for off,(orig,repl) in patches.items():
    cur=struct.unpack_from('<I',lib,off)[0]
    assert cur==orig,(hex(off),hex(cur))
    lib[off:off+4]=struct.pack('<I',repl)
zo=zipfile.ZipFile(out,'w')
for info in z.infolist():
    if info.filename.startswith('META-INF/') and info.filename.split('/')[-1].upper().endswith(('.SF','.RSA','.DSA','.EC','MANIFEST.MF')): continue
    data=bytes(lib) if info.filename=='lib/arm64-v8a/libDLS19.so' else (open(sys.argv[3],'rb').read() if info.filename=='classes2.dex' else (open(replace.pop(info.filename),'rb').read() if info.filename in replace else z.read(info.filename)))
    ni=zipfile.ZipInfo(info.filename,info.date_time); ni.compress_type=info.compress_type; ni.external_attr=info.external_attr
    zo.writestr(ni,data)
# entries not in the original APK (e.g. new team badges assets/data/fe/teams/t<slot>.png) are added
for name, path in sorted(replace.items()):
    if not (name.startswith('assets/') or name == 'classes3.dex'):
        sys.exit('refusing to add entry: ' + name)
    ni=zipfile.ZipInfo(name,(2025,1,25,10,47,0)); ni.compress_type=zipfile.ZIP_STORED if name.endswith(('.png','.ttf')) else zipfile.ZIP_DEFLATED
    zo.writestr(ni,open(path,'rb').read())
zo.close()
print('ok')
