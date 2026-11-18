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
static int pendingAction;      /* button id for the pause screen, 0 = none */

/* called once a frame on the game thread (from the cave's frame hook) */
void dlsmgr_frame(void)
{
    int type = -1;
    u8 *scr = top_screen(&type);
    int isPause = scr && type == 6;
    if (isPause != pauseOpen) {
        pauseOpen = isPause;
        if (isPause) {
            u8 *m = match_data();
            int side = m[0x9f0c];
            /* 9 | home goals << 8 | away goals << 16 | player's side << 24 */
            event(9 | m[0x9f14] << 8 | m[0x9f15] << 16 | side << 24);
        } else {
            pendingAction = 0;
            event(10);
        }
    }
    if (isPause && pendingAction) {
        u8 *widget = *(u8 **)(scr + 0x140);
        if (widget) {
            if (pendingAction == 7) {
                /* quit: what the confirmation's "yes" runs (FUN_0014aff8(1)), then resume so the
                   match screen ends the match */
                FN(0x14aff8, int (*)(int))(1);
                *(int *)(widget + 0x150) = 8;
            } else {
                *(int *)(widget + 0x150) = pendingAction;
            }
        }
        pendingAction = 0;
    }
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
    *(void **)(PAGE + 0xff8) = (void *)dlsmgr_frame;   /* the cave calls this each frame */
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
