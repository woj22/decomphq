    # --- added: unpack DLS Manager files (custom kit textures) into the game's documents folder ---
    # DOCS: on this build is Context.getExternalFilesDir(null) (FTTFileManager.getFilesDir).
    # The game checks DOCS:/t<team id>_<version>_custom.png for every team in a match
    # (version defaults to 6150 when CustomData.dat has no entry for the team).
    # Runs on every launch; the zip is small. Any failure is ignored.
    :dlsmgr_ext_start
    const/4 v0, 0x0
    invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v0
    if-eqz v0, :dlsmgr_ext_end
    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    const-string v2, "dlsmgr_ext.zip"
    invoke-virtual {v1, v2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v1
    invoke-virtual {v0}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    move-result-object v2
    invoke-static {v1, v2}, Lcom/savegame/SavesRestoring;->unZipIt(Ljava/io/InputStream;Ljava/lang/String;)V
    :dlsmgr_ext_end
    .catchall {:dlsmgr_ext_start .. :dlsmgr_ext_end} :dlsmgr_ext_done
    :dlsmgr_ext_done
    # --- end added ---

