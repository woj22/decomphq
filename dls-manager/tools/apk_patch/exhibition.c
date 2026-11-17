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
void FUN_001dc0b8(void *);
void FUN_001dcdc4(void *, int);
void FUN_001d95e0(void *, int);
void FUN_001dbd50(void *, int);
void FUN_001db894(void *, void *);
void *FUN_000ae0f0(int);
void FUN_001dc1d8(void *);

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
    /* back to the hub, as the league handler does, without touching the season or saving */
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
    FUN_001db894(sheet + 0x186, FUN_000ae0f0(team));
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
    FUN_0016ac60(1);
}
