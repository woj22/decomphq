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

/* called once a frame on the game thread (from the cave's frame hook) */
void dlsmgr_frame(void)
{
    frameNo++;
    int type = -1;
    u8 *scr = top_screen(&type);
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
    int isPause = scr && type == 6;
    if (isPause != pauseOpen) {
        pauseOpen = isPause;
        if (isPause) {
            u8 *m = match_data();
            /* 9 | home goals << 8 | away goals << 16 */
            event(9 | m[0x9f14] << 8 | m[0x9f15] << 16);
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

void Java_com_dlsmgr_Native_pauseAction(void *env, void *cls, int id)
{
    pendingAction = id;
}
