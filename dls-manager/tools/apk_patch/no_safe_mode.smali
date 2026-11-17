    # --- added: DLS Manager never opens Safe Mode ---
    # Injected at the top of FTTBootManager.ShouldEnterSafeMode()Z (smali/com/firsttouchgames/ftt/
    # FTTBootManager.smali, classes.dex), right after ".locals 7". The game normally opens its
    # Safe Mode screen after crashed starts; the menus' start screen replaces it (export save etc.).
    const/4 v0, 0x0
    return v0
    # --- end added ---
