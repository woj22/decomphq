    # --- added: show the DLS Manager menus (com.dlsmgr.Overlay in classes3.dex) on top of the game ---
    :dlsmgr_menu_start
    invoke-static {p0}, Lcom/dlsmgr/Overlay;->attach(Landroid/content/Context;)V
    :dlsmgr_menu_end
    .catchall {:dlsmgr_menu_start .. :dlsmgr_menu_end} :dlsmgr_menu_done
    :dlsmgr_menu_done
    # --- end added ---

