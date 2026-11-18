/*
 * libdlsmgr.so - DLS Manager's own native code, loaded next to libDLS19.so.
 *
 * Built without the NDK (tools/apk_patch/build_native.py): no libc is linked; libc
 * functions are reached through libDLS19's own PLT and game functions by their offsets
 * from the library's load address, which Java passes to Native.init(). The code cave in
 * libDLS19 (exhibition.c) calls dlsmgr_frame() once a frame through the pointer this
 * library stores at PAGE+0xff8, so new behaviour doesn't need cave space.
 *
 * Pause menu (screen 6, constructor FUN_00148fbc, update FUN_0014a578): DLS asks its button
 * widget (screen+0x140) which button was pressed (widget+0x150, FUN_00101a90) and runs that
 * action: 8 resume, 7 quit (asks), 1 team management, 3 replay, 4 settings. Our menus draw
 * the pause menu; the chosen action is written into that field so DLS's own code runs it.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;

typedef void *JNIEnv_;          /* JNIEnv* = pointer to the function table pointer */
typedef void **JavaVM_;

static u64 base;                /* libDLS19.so load address */
static JavaVM_ *vm;
static void *overlayClass;      /* global ref: com.dlsmgr.Overlay */
static void *eventMethod;       /* Overlay.nativeEvent(int) */

#define PAGE ((u8 *)(base + 0x7c3000))
#define FN(off, type) ((type)(base + (off)))

/* game functions */
#define screen_mgr()        FN(0x123a68, void *(*)(void))()
#define match_data()        (*(u8 **)(base + 0x54d950))

/* libc through libDLS19's PLT */
#define c_fopen(p, m)    FN(0x8ad40, void *(*)(const char *, const char *))(p, m)
#define c_fprintf        FN(0x8a610, int (*)(void *, const char *, ...))
#define c_fclose(f)      FN(0x8b390, int (*)(void *))(f)
#define LOG_FILE "/storage/emulated/0/Android/data/com.firsttouchgames.dls3/files/dlsmgr_log_native.txt"

static void nlog(const char *fmt, int a, int b, int c)
{
    void *f = c_fopen(LOG_FILE, "a");
    if (f) {
        c_fprintf(f, fmt, a, b, c);
        c_fclose(f);
    }
}

/* JNI by table index (see jni.h) */
#define JFN(env, idx, type) ((type)((*(void ***)(env))[idx]))

static void *get_env(void)
{
    void *env = 0;
    if (!vm)
        return 0;
    /* JavaVM->GetEnv(vm, &env, JNI_VERSION_1_6) : invoke interface slot 6 */
    ((int (*)(JavaVM_ *, void **, int))((*vm)[6]))(vm, &env, 0x10006);
    return env;
}

static void event(int code)
{
    void *env = get_env();
    if (!env || !overlayClass || !eventMethod)
        return;
    u64 arg = (u64)(u32)code;   /* jvalue */
    JFN(env, 143, void (*)(void *, void *, void *, u64 *))(env, overlayClass, eventMethod, &arg);  /* CallStaticVoidMethodA */
    JFN(env, 17, void (*)(void *))(env);  /* ExceptionClear */
}

/* the top screen object and its type (+0x134), or 0 */
static u8 *top_screen(int *type)
{
    u8 *mgr = screen_mgr();
    int n = *(int *)(mgr + 0x48);
    if (n < 1 || n > 24)
        return 0;
    u8 *s = *(u8 **)(mgr + 0x50 + (n - 1) * 8);
    if (s && type)
        *type = *(int *)(s + 0x134);
    return s;
}

static int pauseOpen;
static int pendingPause;       /* our pause button was tapped */
static u32 lastHud = 0xffffffff;
static int lastAdded = -1;
static int halfNo, lastLeft;
static int pendingAction;      /* pause menu choice, 0 = none */
static int lastTop = -2, lastDepth = -1, lastCut = -1;
static unsigned frameNo;

/* resume the match from the pause screen, as its own Resume path does (FUN_0014a578) */
static void pause_resume(void)
{
    FN(0x18ff7c, void (*)(void))();
    FN(0x16ac90, void (*)(int))(1);
    FN(0x2a90dc, void (*)(void))();
}

static int match_in_stack(void)
{
    u8 *mgr = screen_mgr();
    int n = *(int *)(mgr + 0x48);
    for (int i = 0; i < n && i < 24; i++) {
        u8 *s = *(u8 **)(mgr + 0x50 + i * 8);
        if (s && *(int *)(s + 0x134) == 0)
            return 1;
    }
    return 0;
}

static void roster_poll(void);

/* ---- substitutions and tactics (our pause menu's panel)
 *
 * The user's team: M + M[0x9ab0] * 0x1028 + 0x3848; its sheet FUN_0018b940(team). The sheet's
 * player list (sheet+0x140; count FUN_001dade0, id i FUN_001d985c) holds the XI in formation
 * slot order, then the bench; +0x184 formation, +0x185 mentality (0-100). A swap goes through
 * DLS's own FUN_001dd330(sheet, idA, idB, 0, -1, -1), as its team screen (FUN_000f69b8) does:
 * it checks the substitution (0 ok, 4 none left, 3 already off / sent off, 1-2 goalkeeper,
 * 9 unknown player), swaps the live players and re-applies the sheet; then FUN_0018ae9c(team).
 * Changes are queued from Java and run on the game thread in dlsmgr_frame. */
static u8 *user_team(void)
{
    u8 *m = match_data();
    return m + (m[0x9ab0] & 1) * 0x1028 + 0x3848;
}

#define team_sheet(t)   FN(0x18b940, u8 *(*)(void *))(t)
#define list_count(l)   FN(0x1dade0, int (*)(void *))(l)
#define list_id(l, i)   FN(0x1d985c, u32 (*)(void *, int))(l, i)
#define team_player(t, id) FN(0x18aad0, u8 *(*)(void *, u32))(t, id)
#define subs_left(t)    FN(0x18abd4, int (*)(void *, int))(t, 1)

static volatile int opKind;      /* 0 none, 1 swap, 2 tactics; set by Java, run by the frame */
static int opA, opB;
static volatile int opResult = -1;

static void run_op(void)
{
    int k = opKind;
    if (!k)
        return;
    u8 *team = user_team();
    u8 *sheet = team_sheet(team);
    int r = 9;
    if (sheet) {
        if (k == 1) {
            r = FN(0x1dd330, int (*)(void *, u32, u32, int, int, int))(sheet, (u32)opA, (u32)opB, 0, -1, -1);
            if (r == 0)
                FN(0x18ae9c, void (*)(void *))(team);
        } else {
            if (opA >= 0 && opA < 12)
                sheet[0x184] = (u8)opA;
            if (opB >= 0 && opB <= 100)
                sheet[0x185] = (u8)opB;
            FN(0x1dc6bc, void (*)(void *))(sheet);
            r = 0;
        }
    }
    nlog("sheet op %d -> %d (a %d)\n", k, r, opA);
    opResult = r;
    opKind = 0;
    event(17 | (r & 0xff) << 8);
}

/* ---- live match stats
 *
 * Team stats: 25 ints a side at *(base+0x54da40) (= 0x5a1864, cleared each match by
 * FUN_00192404), as DLS's match stats screen reads them (FUN_00142c64, table 0x3c0c30):
 * [0] possession counter, [2] shots, [3] on target, [4]/[5] passes / completed, [14] yellow
 * cards, [15] red, [16] fouls, [17] offsides, [23] corners.
 * Players: 0x7cc-byte records at 0x5a1d8c + side*0xf980 (count M[side*0x1028+0x3990]); +0 id,
 * then counters by event type (FUN_00192810: +4*(type+1)): +0x28 saves (9), +0x44 assists
 * (0x10), +0x4c touches (0x12), +0x50 yellow (0x13), +0x54 red (0x14); goals +0x2c, own goals
 * +0x40 (FUN_00193e2c), with an event list (+0x5c8 count, 8 bytes each from +0x5cc: minute,
 * goal, own goal, flag M[0xa958], red).
 * Polled every frame: an increase becomes an event with the match minute. */
#define TEAMSTATS() (*(int **)(base + 0x54da40))
#define PREC(side, i) ((u8 *)(base + 0x5a1d8c + (side) * 0xf980 + (i) * 0x7cc))

static int tstats[50];
static int pstat[2][32][8];   /* id, goals, own goals, assists, yellow, red, saves, touches */
static int pcount[2];
static int evs[96][5];        /* type (1 goal, 2 own goal, 3 assist, 4 yellow, 5 red), side, id, minute, extra */
static int evN;
static int statsLive;
static const int POFF[7] = {0x2c, 0x40, 0x44, 0x50, 0x54, 0x28, 0x4c};

static void stats_reset(void)
{
    evN = 0;
    for (int s = 0; s < 2; s++) {
        pcount[s] = 0;
        for (int i = 0; i < 32; i++)
            for (int k = 0; k < 8; k++)
                pstat[s][i][k] = 0;
    }
    for (int i = 0; i < 50; i++)
        tstats[i] = 0;
}

static void stats_poll(void)
{
    u8 *m = match_data();
    int *ts = TEAMSTATS();
    if (ts)
        for (int i = 0; i < 50; i++)
            tstats[i] = ts[i];
    int minute = *(int *)(m + 0xa704);
    for (int s = 0; s < 2; s++) {
        int n = m[s * 0x1028 + 0x3990];
        if (n > 32) n = 32;
        pcount[s] = n;
        for (int i = 0; i < n; i++) {
            u8 *r = PREC(s, i);
            int *ps = pstat[s][i];
            int id = *(int *)r;
            if (ps[0] != id) {          /* new record: take it as it is */
                ps[0] = id;
                for (int k = 0; k < 7; k++)
                    ps[k + 1] = *(int *)(r + POFF[k]);
                continue;
            }
            for (int k = 0; k < 7; k++) {
                int v = *(int *)(r + POFF[k]);
                if (k < 5 && v > ps[k + 1] && v - ps[k + 1] < 4) {
                    for (int j = ps[k + 1]; j < v && evN < 96; j++) {
                        int extra = 0;
                        if (k < 2) {         /* goal: its entry in the player's event list */
                            int c = *(int *)(r + 0x5c8);
                            if (c > 0 && c < 100)
                                extra = r[0x5cc + (c - 1) * 8 + 6] | *(int *)(m + 0x9e34) << 8;
                        }
                        int *e = evs[evN++];
                        e[0] = k + 1; e[1] = s; e[2] = id; e[3] = minute; e[4] = extra;
                        nlog("stat event %d side %d id %d", k + 1, s, id);
                        nlog(" min %d extra %x%d\n", minute, extra, 0);
                    }
                }
                ps[k + 1] = v;
            }
        }
    }
}

/* called once a frame on the game thread (from the cave's frame hook) */
void dlsmgr_frame(void)
{
    frameNo++;
    /* Kick-off with the previous match's screen still in the stack (it stays under the hub
       after full time): clear the history first and wait until that screen is destroyed -
       its clean-up (FUN_0013f954 -> FUN_001d6a1c) frees the team sheets, so it must run
       before the new match is set up. The cave's kick-off (request 4 at PAGE+0xf00) is held
       back meanwhile (PAGE+0xf03). */
    if (PAGE[0xf00] == 4 && match_in_stack()) {
        PAGE[0xf00] = 0;
        PAGE[0xf03] = 1;
        FN(0x16acb4, void (*)(int, void *))(0, 0);
        FN(0x169f44, void (*)(int, int, int, int, int, int))(5, 0, 0, 0, 1, 0);
        nlog("kick-off waits for the old match screen%d%d%d\n", 0, 0, 0);
        return;
    }
    if (PAGE[0xf03] && !match_in_stack()) {
        PAGE[0xf03] = 0;
        PAGE[0xf00] = 4;     /* the cave kicks off right after this returns */
        nlog("old match screen gone, kicking off%d%d%d\n", 0, 0, 0);
    }
    int inMatch = match_in_stack();
    if (inMatch && !statsLive) {
        stats_reset();
        nlog("match stats reset%d%d%d\n", 0, 0, 0);
    }
    statsLive = inMatch;
    int type = -1;
    u8 *scr = top_screen(&type);
    /* only while the match (or its pause screen) is on top: after full time DLS may clear
       the counters while the match screen still sits under the menus */
    if (inMatch && scr && (type == 0 || type == 6))
        stats_poll();
    if (!inMatch || (scr && type != 0))
        roster_poll();          /* never while a match is being played */
    if (inMatch)
        run_op();
    else
        opKind = 0;
    u8 *mgr = screen_mgr();
    int depth = *(int *)(mgr + 0x48);
    if (type != lastTop || depth != lastDepth) {
        nlog("frame %d: top screen %d, depth %d\n", (int)frameNo, type, depth);
        lastTop = type;
        lastDepth = depth;
    }
    /* cutscenes (build-up, replays...): FUN_001b38a8 = cutscene type while one plays */
    int active = (FN(0x1b3910, u64 (*)(int))(1) & 1) || FN(0x1b3670, int (*)(void))() > 0;
    int cut = active ? FN(0x1b38a8, int (*)(void))() : -1;
    if (cut != lastCut) {
        lastCut = cut;
        event(11 | (cut & 0xff) << 8 | active << 16);
    }
    /* our scoreboard: score and clock while the match screen is on top (event 14 on change).
       Clock: match minute at M+0xa704 and its seconds at M+0xa708 (to be confirmed by the
       raw values logged below). */
    if (scr && type == 0) {
        u8 *m = match_data();
        u32 hg = m[0x9f14] & 31, ag = m[0x9f15] & 31;
        /* clock, as DLS's: M+0xa700 counts down the half's match seconds (half length M+0xa708
           x 60; a whole match takes about 6 real minutes), M+0xa704 is the
           match minute (tells the halves apart), M+0xa714 the added minutes, played once
           M+0xa700 has run out (where DLS widens its clock for the red tab). */
        int half = *(int *)(m + 0xa708), left = *(int *)(m + 0xa700), minute = *(int *)(m + 0xa704);
        if (halfNo > 3) halfNo = 3;
        if (half <= 0 || half > 90)
            half = 45;
        int frames = half * 60;
        /* which period: counted here, not from the minute (it passes 45 in first-half added
           time). A new period starts when the frame counter jumps back up to (near) full. */
        if (minute <= 1 && left > frames - 120)
            halfNo = 0;                       /* kick-off */
        else if (left > lastLeft + 300)
            halfNo++;
        lastLeft = left;
        int total = halfNo * frames + (frames - left);
        if (total < 0) total = 0;
        u32 secs = (u32)total;     /* M+0xa700 counts match seconds (2700 a half) */
        u32 mn = secs / 60, sc = secs % 60;
        if (mn > 255) mn = 255;
        int added = (*(int *)(m + 0xa714) > 0 && left < 1) ? *(int *)(m + 0xa714) : 0;
        if (added != lastAdded) {
            lastAdded = added;
            event(16 | (added & 0xff) << 8);   /* added-time tab on / off */
        }
        u32 hud = 14 | hg << 8 | ag << 13 | sc << 18 | mn << 24;
        if (hud != lastHud) {
            lastHud = hud;
            event((int)hud);
        }
        if (frameNo % 600 == 0)
            nlog("clock? a700 %d a704 %d a708 %d\n", *(int *)(m + 0xa700), *(int *)(m + 0xa704), *(int *)(m + 0xa708));
        if (pendingPause) {
            pendingPause = 0;
            FN(0x18fdf0, void (*)(long, int))(-1, 0);   /* what DLS's pause button calls */
        }
    }
    int isPause = scr && type == 6;
    if (isPause != (pauseOpen != 0)) {
        pauseOpen = isPause;
        if (isPause) {
            u8 *m = match_data();
            int st = *(int *)(m + 0x9e3c);
            nlog("pause screen: 9e34 %d 9e3c %d", *(int *)(m + 0x9e34), st, 0);
            nlog(" 9e6c %d a704 %d%d\n", *(int *)(m + 0x9e6c), *(int *)(m + 0xa704), 0);
            if (st == 10) {
                /* the match is over (the state DLS's pause screen treats specially): skip DLS's
                   full-time menu and leave the match straight away, so our full-time handler
                   brings the menus up with the result */
                pendingAction = 8;
                pauseOpen = 2;     /* not ours to show */
                event(15);
            } else {
                /* 9 | home goals << 8 | away goals << 16 */
                event(9 | m[0x9f14] << 8 | m[0x9f15] << 16);
            }
        } else {
            pendingAction = 0;
            event(10);
        }
    }
    if (isPause && pendingAction) {
        int a = pendingAction;
        pendingAction = 0;
        nlog("pause action %d%d%d\n", a, 0, 0);
        if (a == 8) {
            pause_resume();
        } else if (a == 7) {
            /* quit: what the confirmation's "yes" runs (FUN_0014aff8(1)), then back to the
               match screen, which ends the match */
            FN(0x14aff8, int (*)(int))(1);
            pause_resume();
        } else if (a == 1) {
            /* team management (screen 4), as the pause screen's button does */
            u8 *m = match_data();
            FN(0x15ab7c, void (*)(void *))(m + m[0x9ab0] * 0x1028 + 0x3848);
            FN(0x169f44, void (*)(int, int, int, int, int, int))(4, 1, 0, 0, 1, 0);
        }
    }
}

/*
 * Draw the screen stack (called by the cave's render gate instead of FUN_001693e8) without
 * DLS's pause / half-time screen on top: our menus replace it. Nothing is drawn unless the
 * match screen is in the stack (DLS's front end is cut out).
 */
void dlsmgr_render(void)
{
    u8 *mgr = screen_mgr();
    int n = *(int *)(mgr + 0x48);
    int match = -1;
    for (int i = 0; i < n && i < 24; i++) {
        u8 *s = *(u8 **)(mgr + 0x50 + i * 8);
        if (s && *(int *)(s + 0x134) == 0) {
            match = i;
            break;
        }
    }
    if (match < 0)
        return;
    int draw = n;
    u8 *top = *(u8 **)(mgr + 0x50 + (n - 1) * 8);
    if (top && *(int *)(top + 0x134) == 6)
        draw = n - 1;              /* hide the pause screen */
    *(int *)(mgr + 0x48) = draw;
    FN(0x1693e8, void (*)(void))();
    *(int *)(mgr + 0x48) = n;
}

/* ---- squads: transfers and loans made in the menus
 *
 * DLS keeps each team's squad in a 0x108-byte record (team manager DAT_00569380; records at
 * +0x20 / count +0x28, or +0x38 / +0x58; FUN_000ae0f0(team id) finds the one in use): +0 team
 * id, +4 player count, +8 + i*4: shirt number (u8) and flags (u16 at +0xa: starting XI,
 * captain, set-piece takers), +0x88 + i*4: player ids (u32, up to 32). A match builds its
 * teams from these (FUN_000b2298), so editing them moves players between DLS teams. Players
 * who stay keep their entry; new ones get a blank one, then DLS's own repair (FUN_000adadc)
 * gives shirt numbers and flags. Queued from Java, written on the game thread. */
#define RQ_MAX 96
static int rqTeam[RQ_MAX], rqN[RQ_MAX], rqIds[RQ_MAX][32];
static volatile int rqHead, rqTail;

static void roster_write(u8 *rec, const int *ids, int n)
{
    u32 oldEnt[32], oldId[32];
    int on = *(int *)(rec + 4);
    if (on < 0 || on > 32) on = 0;
    for (int i = 0; i < on; i++) { oldEnt[i] = *(u32 *)(rec + 8 + i * 4); oldId[i] = *(u32 *)(rec + 0x88 + i * 4); }
    for (int i = 0; i < n; i++) {
        u32 ent = 0;
        for (int j = 0; j < on; j++)
            if (oldId[j] == (u32)ids[i]) { ent = oldEnt[j]; break; }
        *(u32 *)(rec + 8 + i * 4) = ent;
        *(u32 *)(rec + 0x88 + i * 4) = (u32)ids[i];
    }
    for (int i = n; i < 32; i++) { *(u32 *)(rec + 8 + i * 4) = 0; *(u32 *)(rec + 0x88 + i * 4) = 0; }
    *(int *)(rec + 4) = n;
    FN(0xadadc, void (*)(void *))(rec);
}

/* both record tables can hold the team; update it wherever it is */
static int roster_apply(int team, const int *ids, int n)
{
    u8 *mgr = *(u8 **)(base + 0x569380);
    int hits = 0;
    if (!mgr || n < 11) return 0;
    for (int t = 0; t < 2; t++) {
        u8 *arr = *(u8 **)(mgr + (t ? 0x38 : 0x20));
        int cnt = *(int *)(mgr + (t ? 0x58 : 0x28));
        if (!arr || cnt <= 0 || cnt > 4000) continue;
        for (int i = 0; i < cnt; i++) {
            u8 *rec = arr + i * 0x108;
            if (*(int *)rec == team) { roster_write(rec, ids, n); hits++; break; }
        }
    }
    return hits;
}

static void roster_poll(void)
{
    while (rqTail != rqHead) {
        int k = rqTail % RQ_MAX;
        int h = roster_apply(rqTeam[k], rqIds[k], rqN[k]);
        nlog("squad of team %d set (%d players, %d records)\n", rqTeam[k], rqN[k], h);
        rqTail++;
    }
}

/* ---- notifications: DLS's banners are replaced by the menus' tile (top right)
 *
 * FUN_00261c1c(banner, decision) shows the referee's decisions: 0 offside, 1 half / full time,
 * 2 advantage, 3 corner, 4 goal kick, 5 throw-in, 6 penalty, 7 free kick. The cave sends it
 * here instead (PAGE+0xfe8), so DLS's banner never shows: event 18 | decision << 8 |
 * full time << 16.
 * FUN_0025b218(panel, kind) shows player news: 0 red card, 1 yellow, 2 injury, 3 goal, 4 own
 * goal, 5 hat-trick (kinds 0-5 come here via PAGE+0xfe0; 6+ stay DLS's): event 19 | kind << 8 |
 * side << 12 | user side << 13 | player id << 16, the player found as DLS's panel does. */
void dlsmgr_ref_note(void *banner, int decision)
{
    if (decision < 0 || decision > 15)
        return;
    nlog("referee %d (half %d)%d\n", decision, halfNo, 0);
    event(18 | decision << 8 | (decision == 1 && halfNo >= 1) << 16);
}

void dlsmgr_player_note(void *panel, int kind)
{
    u8 *m = match_data();
    int side, idx;
    switch (kind) {
    case 0: case 1: side = m[0x9f90]; idx = m[0x9f91]; break;
    case 2: side = 1 - m[0x9f90]; idx = m[0x9f92]; break;
    case 3: case 5: side = m[0x9ee9]; idx = *(u16 *)(m + 0x9eea); break;
    case 4: side = 1 - m[0x9ee9]; idx = *(u16 *)(m + 0x9eea); break;
    default: return;
    }
    side &= 1;
    u8 *pl = *(u8 **)(m + side * 0x1028 + 0x4858);
    u32 id = (pl && idx >= 0 && idx < 32) ? *(u16 *)(pl + idx * 0xb0) : 0;
    nlog("player note %d side %d id %d\n", kind, side, (int)id);
    event(19 | kind << 8 | side << 12 | (m[0x9ab0] & 1) << 13 | (int)(id << 16));
}

/* ---- JNI: com.dlsmgr.Native */

int JNI_OnLoad(JavaVM_ *javaVm, void *reserved)
{
    vm = javaVm;
    return 0x10006;
}

void Java_com_dlsmgr_Native_init(void *env, void *cls, u64 libBase, void *overlay)
{
    base = libBase;
    overlayClass = JFN(env, 21, void *(*)(void *, void *))(env, overlay);     /* NewGlobalRef */
    eventMethod = JFN(env, 113, void *(*)(void *, void *, const char *, const char *))(env, overlayClass, "nativeEvent", "(I)V");
    JFN(env, 17, void (*)(void *))(env);
    *(void **)(PAGE + 0xff0) = (void *)dlsmgr_render;  /* the cave's render gate calls this */
    *(void **)(PAGE + 0xff8) = (void *)dlsmgr_frame;   /* the cave calls this each frame */
    *(void **)(PAGE + 0xfe8) = (void *)dlsmgr_ref_note;     /* referee decision banner */
    *(void **)(PAGE + 0xfe0) = (void *)dlsmgr_player_note;  /* goal / card / injury banner */
    nlog("native library ready%d%d%d\n", 0, 0, 0);
}

/* Is libDLS19.so loaded at this address? (its "DOCS:profile.dat" string sits at +0x3ee100) */
int Java_com_dlsmgr_Native_probe(void *env, void *cls, u64 start)
{
    static const char want[] = "DOCS:profile.dat";
    const char *p = (const char *)(start + 0x3ee100);
    for (int i = 0; i < 16; i++)
        if (p[i] != want[i])
            return 0;
    return 1;
}

void Java_com_dlsmgr_Native_pause(void *env, void *cls)
{
    pendingPause = 1;
}

void Java_com_dlsmgr_Native_pauseAction(void *env, void *cls, int id)
{
    pendingAction = id;
}

/* Live sheet of the user's team: [side, formation, mentality, subs left, count,
   then per player: id, flags (0xac) | injury (0xaa) << 8 | 0xab << 16 ] */
void *Java_com_dlsmgr_Native_getSheet(void *env, void *cls)
{
    int out[5 + 64];
    int n = 0;
    if (base && match_in_stack()) {
        u8 *m = match_data();
        u8 *team = user_team();
        u8 *sheet = team_sheet(team);
        if (sheet) {
            int c = list_count(sheet + 0x140);
            if (c > 32) c = 32;
            out[0] = m[0x9ab0] & 1;
            out[1] = sheet[0x184];
            out[2] = sheet[0x185];
            out[3] = subs_left(team);
            out[4] = c;
            n = 5;
            for (int i = 0; i < c; i++) {
                u32 id = list_id(sheet + 0x140, i);
                u8 *p = team_player(team, id);
                out[n++] = (int)id;
                out[n++] = p ? (p[0xac] | p[0xaa] << 8 | p[0xab] << 16) : 0;
            }
        }
    }
    void *arr = JFN(env, 179, void *(*)(void *, int))(env, n);                       /* NewIntArray */
    if (arr && n)
        JFN(env, 211, void (*)(void *, void *, int, int, const int *))(env, arr, 0, n, out);  /* SetIntArrayRegion */
    return arr;
}

/* Queue a change for the game thread: kind 1 swap players a <-> b, kind 2 formation a,
   mentality b. The outcome comes back as event 17 | result << 8. */
int Java_com_dlsmgr_Native_sheetOp(void *env, void *cls, int kind, int a, int b)
{
    if (opKind)
        return 0;
    opA = a;
    opB = b;
    opResult = -1;
    opKind = kind;
    return 1;
}

/* Match stats so far: [0..49] team stats (home, away), [50] user side, [51] event count,
   events (type, side, id, minute, extra) x5, then per side: count, players x8 */
void *Java_com_dlsmgr_Native_stats(void *env, void *cls)
{
    static int out[52 + 96 * 5 + 2 * (1 + 32 * 8)];
    int n = 0;
    for (int i = 0; i < 50; i++)
        out[n++] = tstats[i];
    out[n++] = base ? (match_data()[0x9ab0] & 1) : 0;
    out[n++] = evN;
    for (int i = 0; i < evN; i++)
        for (int k = 0; k < 5; k++)
            out[n++] = evs[i][k];
    for (int s = 0; s < 2; s++) {
        out[n++] = pcount[s];
        for (int i = 0; i < pcount[s]; i++)
            for (int k = 0; k < 8; k++)
                out[n++] = pstat[s][i][k];
    }
    void *arr = JFN(env, 179, void *(*)(void *, int))(env, n);
    if (arr)
        JFN(env, 211, void (*)(void *, void *, int, int, const int *))(env, arr, 0, n, out);
    return arr;
}

/* Queue a team's new squad (DLS player ids, 11-32) for the game thread; 0 if the queue is full. */
int Java_com_dlsmgr_Native_setRoster(void *env, void *cls, int team, void *arr)
{
    int n = JFN(env, 171, int (*)(void *, void *))(env, arr);    /* GetArrayLength */
    if (n < 11 || n > 32 || rqHead - rqTail >= RQ_MAX) return 0;
    int k = rqHead % RQ_MAX;
    JFN(env, 203, void (*)(void *, void *, int, int, int *))(env, arr, 0, n, rqIds[k]);  /* GetIntArrayRegion */
    rqTeam[k] = team;
    rqN[k] = n;
    rqHead++;
    return 1;
}
