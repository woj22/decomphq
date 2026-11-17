# Added to com/firsttouchgames/ftt/FTTMainActivity.smali: the native exhibition code
# (tools/apk_patch/exhibition.c, java_event) calls this from the game thread the way the game
# calls CheckImmersive; it forwards to the menus (1 = match on screen, 2 = full time).
.method public static DlsmgrEvent(I)V
    .locals 0

    invoke-static {p0}, Lcom/dlsmgr/Overlay;->nativeEvent(I)V

    return-void
.end method
