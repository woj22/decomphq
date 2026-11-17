    # --- added: re-run OBB restore whenever the OBB is missing or incomplete ---
    invoke-virtual {p0}, Landroid/content/Context;->getObbDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "main.116.com.firsttouchgames.dls3.obb"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->length()J
    move-result-wide v2
    const-wide v4, 0x123deb04L
    cmp-long v0, v2, v4
    if-eqz v0, :obb_ok_added
    const-string v0, "savegame"
    const/4 v1, 0x0
    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v0
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v0
    const-string v1, "notfirst250125"
    invoke-interface {v0, v1}, Landroid/content/SharedPreferences$Editor;->remove(Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;
    move-result-object v0
    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->commit()Z
    :obb_ok_added
    # --- end added ---

