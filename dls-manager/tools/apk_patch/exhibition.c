/*
 * Team A vs team B: an exhibition match between the player's club (DLS team 0x102, the
 * Dream FC slot holding the club's squad) and any database team, with no DLS season involved.
 *
 * Compiled for arm64 and linked into the code cave after libDLS19.so's executable segment
 * (tools/apk_patch/exhibition_build.py); calls go straight to the game's functions by their
 * offsets (pc-relative, so the library's load address doesn't matter).
 *
 * Flow: the menus send NativeDialogButton 0x5A5E4000|team (player at home) or 0x5A5E8000|team
 * (away); the hub's next fixture shows that opponent (FUN_002648f8 wrapper). When the pre-match
 * screen starts the match, FUN_00273170 (league match start) jumps to exhibition_hook: with an
 * override set, exhibition_start() sets the match up the way FUN_00273170 does, minus every
 * season lookup and with its own full-time handler, which writes the result for the menus and
 * goes back to the hub without recording anything in the DLS season.
 *
 * Result block (unused tail of the last RW page, lib+0x7c3f10):
 *   +0 u32 sequence (bumped at full time)  +4 i32 home team  +8 i32 away team
 *   +0xc u8 home goals  +0xd u8 away goals  +0xe u8 player's side (0 home, 1 away)
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;

/* game globals: pointers stored in the library's GOT-like table */
extern u8 *PTR_profile;   /* 0x54cc30 -> profile object; season at +0x20 */
extern u8 *PTR_match;     /* 0x54d950 -> match data M */
extern u8 *PTR_state;     /* 0x54ccc8 -> game/match state */
extern u8 *PTR_compinfo;  /* 0x54d928 -> {u64, competition*} shown during the match */
extern u8 *PTR_compdef;   /* 0x54c4f8 */
extern u8 PAGE[];         /* 0x7c3000 flag page */

/* game functions */
void FUN_002a25f8(void *);
void FUN_001d8354(int);
void FUN_000a4a00(int, int);
void FUN_001d8b34(int, int, void *, void *);
int FUN_0027dc84(void *);
int FUN_0027eabc(void *);
int FUN_0027eac4(void *);
u32 FUN_00283470(void *);
int FUN_002b5760(int, int, int, int, int);
void FUN_000b35c8(void *, int, int);
void FUN_001d72a0(void *);
void FUN_001d69f4(void *);
void FUN_001d6ba8(int, void *);
int FUN_00273a9c(void);
int FUN_002b70e8(void);
void FUN_002b70dc(int);
int FUN_0027e3fc(void *);
int FUN_0027e304(void *);
int FUN_002b6fb0(int);
long time_plt(long *);
void FUN_00348f2c(long, void *, void *, void *, long, long, long, int);
void FUN_000b5d70(void *);
u8 *FUN_000acf28(int);
int FUN_00227cb8(void *);
void FUN_001d83ec(void *, void *, int, int);
void FUN_001d8ef8(int, int);
void FUN_001d8384(int, int, int, int, int, int, int);
void FUN_001d6ed8(void);
void FUN_00169f44(int, int, int, int, int, int);
void *memcpy_plt(void *, const void *, u64);
void FUN_001d728c(int);
void FUN_001d72ec(void);
void FUN_001d73c4(int, int);
void FUN_0022a548(void);
void FUN_0016ac60(int);
void FUN_001693e8(void);
int FUN_00257820(void);
int FUN_0025775c(void);
int FUN_0025d5e4(void);
extern int WEATHER;   /* DAT_005cd804: 0 clear, 1 rain, 2 snow */
extern int TIMEOFDAY; /* DAT_005cc8dc: <2 day, 2 night */
void FUN_0016a134(void);
void FUN_0027d3d0(void *);
void FUN_001ed0e4(void);
void FUN_002b2318(int, int, int);
void FUN_0026357c(void);
void FUN_0016acb4(int, void *);
void FUN_001d8908(int);
void FUN_001d8928(int);
void FUN_001dc0b8(void *);
void FUN_001dcdc4(void *, int);
void FUN_001d95e0(void *, int);
void FUN_001dbd50(void *, int);
void FUN_001db894(void *, void *);
void *FUN_000ae0f0(int);
void FUN_001dc1d8(void *);
void *fopen_plt(const char *, const char *);
int fprintf_plt(void *, const char *, ...);
int fclose_plt(void *);
long *FUN_0034da64(void);                 /* JNIEnv* for this thread */
void *FUN_0034db84(const char *);         /* game class by short name (local ref) */
void FUN_000a45f0(long *, void *, void *, ...);  /* CallStaticVoidMethod */

/*
 * Tell the menus about the match, straight from the game thread: calls the static Java method
 * FTTMainActivity.DlsmgrEvent(int) (added in smali, forwards to com.dlsmgr.Overlay.nativeEvent)
 * the way the game calls CheckImmersive. 1 = the match is on screen, 2 = full time.
 */
#define NATIVE_LOG "/storage/emulated/0/Android/data/com.firsttouchgames.dls3/files/dlsmgr_log_native.txt"

/* one line in the export's native log (Export save zips dlsmgr_log*) */
static void nlog(const char *fmt, int a, int b)
{
    void *f = fopen_plt(NATIVE_LOG, "a");
    if (f) {
        fprintf_plt(f, fmt, a, b);
        fclose_plt(f);
    }
}

static void java_event(int code)
{
    nlog("event %x (state %d)\n", code, PAGE[0xf0c]);
    long *env = FUN_0034da64();
    if (!env)
        return;
    void **fn = *(void ***)env;
    void *cls = FUN_0034db84("MainActivity");
    if (!cls)
        return;
    void *mid = ((void *(*)(long *, void *, const char *, const char *))fn[0x388 / 8])(env, cls, "DlsmgrEvent", "(I)V");
    if (mid)
        FUN_000a45f0(env, cls, mid, code);
    else
        nlog("DlsmgrEvent not found (%d)%d\n", code, 0);
    ((void (*)(long *))fn[0x88 / 8])(env);              /* ExceptionClear */
    ((void (*)(long *, void *))fn[0xb8 / 8])(env, cls);  /* DeleteLocalRef */
}

/* full-time result for the menus (app-private files dir; Java polls it) */
#define RESULT_FILE "/data/data/com.firsttouchgames.dls3/files/dlsmgr_result.txt"


#define USER 0x102

static void exhibition_fulltime(void)
{
    u8 *m = PTR_match;
    u8 *r = PAGE + 0xf10;
    *(int *)(r + 4) = *(int *)(m + 0x3848);
    *(int *)(r + 8) = *(int *)(m + 0x4870);
    r[0xc] = m[0x9f14];
    r[0xd] = m[0x9f15];
    r[0xe] = m[0x9f0c];
    *(u32 *)r = *(u32 *)r + 1;
    *(u16 *)(PAGE + 0xf04) = 0;  /* one match per request */
    PAGE[0xf0c] = 0;
    void *f = fopen_plt(RESULT_FILE, "w");
    if (f) {
        fprintf_plt(f, "%d,%d,%d,%d,%u\n", *(int *)(r + 4), *(int *)(r + 8), r[0xc], r[0xd], *(u32 *)r);
        fclose_plt(f);
    }
    java_event(2);  /* menus up now (score already in the file), before the hub is drawn */
    /* Back to the hub without touching the season or saving. The screen history is cleared
       first (FUN_0016acb4(0, 0), as DLS's kick-off does) so the finished match screen is
       destroyed now: pushed on top of it (v47-v62), it was only destroyed at the next
       kick-off, after the new match was set up, and its clean-up (FUN_0013f954 ->
       FUN_001d6a1c) freed the new match's team sheets - the second-match crash. */
    FUN_0016acb4(0, 0);
    FUN_00169f44(5, 0, 0, 0, m[0x9ef4] == 0, 0);
}

int exhibition_start2(int home, int away, void *homeSheet, void *awaySheet)
{
    u8 *prof = PTR_profile;
    u8 *season = prof + 0x20;
    u8 *m = PTR_match;
    int userHome = home == USER;
    void *lineup = season + 0x720;  /* FUN_002864e4: the player's team sheet */
    u8 date[8];
    int stadium[944];
    long now = 0, ym = 0;
    int day = 0;

    /* AI difficulty: profile +0x6100 (s16), applied to the match by FUN_002a25f8 ->
       FUN_001d8348; DLS nudges it by results and caps it per division (FUN_002a281c).
       Ours is set from the menus' setting (PAGE+0xf0f: 1 easy .. 4 very hard, x100),
       hard (300) if none was sent. The saves so far had 0, the easiest. */
    int dlv = PAGE[0xf0f];
    *(short *)(prof + 0x6100) = (short)((dlv >= 1 && dlv <= 5 ? dlv : 3) * 100);
    FUN_002a25f8(prof + 0x6100);
    FUN_001d8354(1);
    FUN_000a4a00(0, userHome ? 0 : 1);
    FUN_000a4a00(1, 2);
    FUN_000a4a00(2, 2);
    FUN_000a4a00(3, 2);
    if (!homeSheet)
        homeSheet = userHome ? lineup : 0;
    if (!awaySheet)
        awaySheet = userHome ? 0 : lineup;
    FUN_001d8b34(home, away, homeSheet, awaySheet);

    /* opponent strength, as for a league match in the player's division */
    u32 div = FUN_00283470(season);
    int lvl = div < 6 ? (int)div * 3 + 0xf : 0x32;
    int diff = FUN_002b5760(FUN_0027dc84(season), FUN_0027eabc(season), FUN_0027eac4(season), 0, lvl);
    FUN_000b35c8(m + (userHome ? 1 : 0) * 0x1028 + 0x3848, 1, diff);

    FUN_001d72a0(0);
    *(u64 *)PTR_compinfo = *(u64 *)PTR_compdef;
    *(u64 *)(PTR_compinfo + 8) = 0;
    FUN_001d69f4((void *)exhibition_fulltime);
    *(u8 **)(PTR_state + 0xfb8) = prof + 0x22800;
    /* Assists off for our matches (profile control settings, as the game's Controls screen
       sets them): +0x6145 cross assist (0 off), +0x6146 kick assist (0 off). */
    prof[0x6145] = 0;
    prof[0x6146] = 0;
    long kitinfo = (long)((u64)*(u32 *)(prof + 0x6144) << 32);
    FUN_001d6ba8(USER != *(int *)(m + 0x3848), &kitinfo);

    int weather = FUN_00273a9c();
    int seed = FUN_002b70e8();
    FUN_002b70dc(FUN_0027e3fc(season) + FUN_0027e304(season));
    int r = FUN_002b6fb0(100);
    FUN_002b70dc(seed);
    time_plt(&now);
    FUN_00348f2c(now, (u8 *)&ym + 4, &ym, &day, 0, 0, 0, 1);
    *(u16 *)date = (u16)((u64)ym >> 32);
    date[2] = (u8)ym;
    date[3] = (u8)day;
    date[4] = r > 0x55 ? 0x13 : r > 0x41 ? 0x11 : 0xf;  /* kick-off hour */
    date[5] = r > 0x55 ? 0x2d : 0;

    FUN_000b5d70(stadium);
    int crowd;
    if (userHome) {
        memcpy_plt(stadium, FUN_000acf28(0xd4) + 0x150, 0xebb);  /* the player's ground */
        crowd = FUN_00227cb8(stadium);
    } else {
        memcpy_plt(stadium, FUN_000acf28(home) + 0x150, 0xebb);
        int cap = FUN_00227cb8(stadium);
        crowd = (int)(((float)(FUN_002b6fb0(0x19) + 0x4b) / 100.0f) * (float)cap);
    }
    FUN_001d83ec(date, stadium, weather, crowd);
    FUN_001d8ef8(0, -1);
    /* match type 0 (friendly): type 3 (league) made the post-match code look both teams up in
       the DLS league table, which crashed for opponents outside it (v46) */
    FUN_001d8384(0, 0, stadium[0] != 1, 0, 0, 0, 0);
    FUN_002a25f8(prof + 0x6100);
    FUN_001d6ed8();
    return 1;
}

int exhibition_start(int home, int away)
{
    return exhibition_start2(home, away, 0, 0);
}

/*
 * Team sheets from the menus (Java writes them through /proc/self/mem before the start
 * request): PAGE+0xf40 home, PAGE+0xf84 away, each u8 valid, u8 DLS formation (0-11),
 * u8 count, u8 0, then count x u16 player ids: starting XI in the formation's slot order,
 * then substitutes and reserves. Built the way FUN_00273170 builds one for a squad list.
 */
static void *make_sheet(u8 *sheet, int team, u8 *src)
{
    if (src[0] != 1)
        return 0;
    src[0] = 0;
    FUN_001dc0b8(sheet);
    FUN_001dcdc4(sheet, team);
    int n = src[2] > 32 ? 32 : src[2];
    for (int i = 0; i < n; i++)
        FUN_001d95e0(sheet + 0x140, *(u16 *)(src + 4 + 2 * i));
    FUN_001dbd50(sheet + 0x184, src[1]);
    sheet[0x185] = 0x32;   /* mentality, as FUN_001dbd3c sets it */
    FUN_001db894(sheet + 0x186, FUN_000ae0f0(team));
    /* per-player entries (32 x 10 bytes at +0), filled the way FUN_001dcdd4 does for a
       squad: u16 id, u8 0, u16 0, u16 condition 0x927c (full fitness), u16 0. Left at 0
       (v49-v55) the engine treated every player as unfit/injured. */
    for (int i = 0; i < 32; i++) {
        u8 *e = sheet + i * 10;
        u16 id = i < n ? *(u16 *)(src + 4 + 2 * i) : 0xffde;
        u16 cond = i < n ? 0x927c : 0;
        e[0] = (u8)id; e[1] = (u8)(id >> 8);
        e[2] = 0; e[3] = 0; e[4] = 0; e[5] = 0;
        e[6] = (u8)cond; e[7] = (u8)(cond >> 8);
        e[8] = 0; e[9] = 0;
    }
    sheet[400] = 1;
    return sheet;
}

/*
 * Called every frame (wrapper at the frame-update call, see exhibition_build.py). The menus'
 * Play match sends the opponent (0x5A5E4000/0x8000|team) and then 0x5A5E0004, which the
 * NativeDialogButton hook stores at PAGE+0xf00: kick off straight away, as the pre-match
 * screen does (reset, set up, kits, then FUN_0016ac60 starts the match).
 */
void exhibition_poll(void)
{
    /* libdlsmgr.so's per-frame function (stored by Native.init), if loaded */
    void (*ext)(void) = *(void (**)(void))(PAGE + 0xff8);
    if (ext)
        ext();
    /* match screen (FUN_0013f9d4, its object recorded by match_screen_hook) finished loading:
       the match is on screen, the menus can step aside */
    if (PAGE[0xf0c] == 1) {
        u8 *scr = *(u8 **)(PAGE + 0xf28);
        if (scr && scr[0x139]) {
            PAGE[0xf0c] = 2;
            java_event(1);
        }
    }
    if (PAGE[0xf00] != 4)
        return;
    PAGE[0xf00] = 0;
    u16 ov = *(u16 *)(PAGE + 0xf04);
    if (!ov)
        return;
    int team = ov & 0x3ff;
    int home = (ov & 0x4000) ? USER : team;
    int away = (ov & 0x4000) ? team : USER;
    u64 hbuf[0x50], abuf[0x50];  /* 0x280 bytes each; a sheet is 0x1a0 */
    *(u64 *)(PAGE + 0xf28) = 0;
    PAGE[0xf0c] = 1;
    FUN_001d728c(0);
    FUN_001d72ec();
    void *hs = make_sheet((u8 *)hbuf, home, PAGE + 0xf40);
    void *as = make_sheet((u8 *)abuf, away, PAGE + 0xf84);
    exhibition_start2(home, away, hs, as);
    if (hs)
        FUN_001dc1d8(hs);
    if (as)
        FUN_001dc1d8(as);
    FUN_001d73c4(0, 1);   /* home kit, away kit */
    FUN_0022a548();
    /* Kick off as DLS's own Play does (FUN_000a54c4, called by the team screen): front-end
       tidy-up, clear the screen history, then screen 0 = the match screen (FUN_0013f87c /
       update FUN_0013f9d4). Only its in-app shop popup (FUN_0009babc) is left out.
       (v52/v53 called FUN_0016ac60, which advances the career screen sequence instead.) */
    u8 *st = PTR_state;
    FUN_0016a134();
    FUN_0027d3d0(PTR_profile + 0x20);
    FUN_001ed0e4();
    FUN_002b2318(5, 0, 0);
    FUN_0026357c();
    FUN_0016acb4(0, 0);
    if (*(int *)(st + 0x10) != 8 && PTR_profile[0x2aa3c] == 0 && *(int *)(st + 0xfac) == -1) {
        FUN_001d8908(1);
        FUN_001d8928(1);
    }
    FUN_00169f44(0, 1, 0, 0, 0, 0);
}

/*
 * FTTJNI.NativeDialogButton(int) hook (0x2b914c): values 0x5A5Exxxx are ours, anything else
 * runs the game's own handler (see exhibition_build.py). Replaces match_hooks_asm.py's version
 * with the same meanings plus a byte channel for the team sheets, since an app can't write
 * its own /proc/self/mem on every phone:
 *   0x4000|team, 0x8000|team  opponent (player at home / away)   0x0003  clear opponent
 *   0x3000|n  sheet write position n   0x2000|b  write byte b, then position + 1
 *   anything else: request byte at PAGE+0xf00 (1 save, 2 reload, 4 kick off)
 */
void ndb_ours(long env, long cls, u32 v)
{
    u32 x = v & 0xffff;
    if (x & 0xc000) {
        *(u16 *)(PAGE + 0xf04) = (u16)x;
    } else if ((x & 0xf000) == 0x3000) {
        *(u16 *)(PAGE + 0xf08) = x & 0xfff;
    } else if ((x & 0xf000) == 0x2000) {
        u32 i = *(u16 *)(PAGE + 0xf08);
        if (i < 0x88)
            PAGE[0xf40 + i] = (u8)x;
        *(u16 *)(PAGE + 0xf08) = (u16)(i + 1);
    } else if (x == 3) {
        *(u16 *)(PAGE + 0xf04) = 0;
    } else if ((x & 0xff00) == 0x0100) {
        PAGE[0xf0f] = (u8)x;          /* difficulty level 1-4 */
    } else if (x == 0x10 || x == 0x11) {
        PAGE[0xf0d] = (u8)(x & 1);  /* DLS front end hidden (0x10) / shown (0x11) */
    } else {
        PAGE[0xf00] = (u8)x;
    }
}


/*
 * The game's screen stack is drawn by FUN_001693e8, called once a frame from the render
 * function FUN_001691d4 (patched call at 0x1692a8). DLS's front end is cut out: the stack is
 * drawn only while the screen on top is the match screen (type 0, FUN_0013f87c; FUN_000f213c
 * gives the top screen's type). Every other DLS screen - hub, menus, loading, popups - is never
 * drawn, whatever state the game gets into; the frame is just cleared and the menus are the app.
 */
void *FUN_00123a68(void);

void render_screens_gate(void)
{
    void (*ext)(void) = *(void (**)(void))(PAGE + 0xff0);  /* libdlsmgr's dlsmgr_render */
    if (ext) {
        ext();
        return;
    }
    u8 *mgr = FUN_00123a68();
    int n = *(int *)(mgr + 0x48);
    for (int i = 0; i < n && i < 24; i++) {
        u8 *scr = *(u8 **)(mgr + 0x50 + i * 8);
        if (scr && *(int *)(scr + 0x134) == 0) {   /* the match screen is in the stack */
            FUN_001693e8();
            return;
        }
    }
}

/*
 * The match's HUD manager (FUN_002620f8) shows the team-intro card (overlay 0xc,
 * FUN_002577c8 / draw FUN_00257a60: both teams, weather, temperature) while the build-up
 * cutscene runs (FUN_00257820: cutscene type 3). Its check is routed here (call at 0x2624ac):
 * DLS's card never appears; instead the menus are told when the intro starts and ends and
 * play their own transparent animated intro over the cutscene.
 * Event 3 | weather << 8 | time of day << 16 = intro starts, 4 = intro over.
 */
int intro_gate(void)
{
    int on = FUN_00257820() & 1;
    if (on != PAGE[0xf0e]) {
        PAGE[0xf0e] = (u8)on;
        java_event(on ? (3 | (WEATHER & 0xff) << 8 | (TIMEOFDAY & 0xff) << 16) : 4);
    }
    return 0;
}

/* HUD overlay 0xb: DLS's "Starting XI" line-up graphic (FUN_002568e8, check FUN_0025775c,
   call at 0x262480). Never shown; the menus draw both line-ups instead (events 7 / 8). */
int lineup_gate(void)
{
    int on = FUN_0025775c() & 1;
    if (on != PAGE[0xf06]) {
        PAGE[0xf06] = (u8)on;
        java_event(on ? 7 : 8);
    }
    return 0;
}

/* HUD overlay 8: DLS's "Dream League Soccer" replay wipe (HUD_Replay_Logo.png, check
   FUN_0025d5e4, call at 0x2623fc). Never shown; the menus flash the league logo instead. */
int replay_logo_gate(void)
{
    int on = FUN_0025d5e4() & 1;
    if (on != PAGE[0xf07]) {
        PAGE[0xf07] = (u8)on;
        java_event(on ? 12 : 13);
    }
    return 0;
}
