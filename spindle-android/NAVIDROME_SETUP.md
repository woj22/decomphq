# Running Navidrome on an Android phone for Spindle

Spindle streams from a Navidrome server. These steps run Navidrome on a spare Android phone that holds your music. Your main phone connects to it over your home Wi-Fi, with nothing extra installed. Away from home, your downloads and recently played songs still play.

## 1. On the server phone: Termux and Navidrome

1. Install **Termux** from F-Droid (the Google Play version is outdated and won't install current packages).
2. In Termux:
   ```sh
   pkg update && pkg upgrade
   pkg install ffmpeg        # lets Navidrome convert songs for lower-quality streaming
   termux-setup-storage      # allow Termux to read your Music folder; tap Allow
   ```
3. Install Navidrome. First try the Termux package:
   ```sh
   pkg search navidrome && pkg install navidrome
   ```
   If it isn't listed, download the `linux_arm64` release from navidrome.org (Releases page), then:
   ```sh
   mkdir -p ~/navidrome && tar -xzf navidrome_*_linux_arm64.tar.gz -C ~/navidrome
   ```
4. Create `~/navidrome/navidrome.toml`:
   ```toml
   MusicFolder = "/storage/emulated/0/Music"
   DataFolder = "/data/data/com.termux/files/home/navidrome/data"
   Address = "0.0.0.0"
   Port = 4533
   ScanSchedule = "@every 1h"
   ```
5. Start it:
   ```sh
   termux-wake-lock
   ~/navidrome/navidrome --configfile ~/navidrome/navidrome.toml
   ```
6. On the server phone, open `http://localhost:4533` in a browser and create your admin account. This is the username and password you'll enter in Spindle.

### Keep it running

- In Android settings, turn **battery optimisation off** for Termux, or Android will stop the server in the background.
- `termux-wake-lock` keeps the phone from sleeping the server. Keep the phone plugged in.
- Optional: install **Termux:Boot** from F-Droid and put the start command in `~/.termux/boot/start-navidrome` so it starts after a restart.

## 2. Connect Spindle over your home Wi-Fi

1. Find the server phone's address: on the server phone, open **Settings → About phone → Status** (or **Settings → Wi-Fi →** your network) and note the **IP address**, for example `192.168.1.20`.
2. In Spindle on your main phone, sign in with:
   - Server address: `http://192.168.1.20:4533` (your address, followed by `:4533`)
   - Your Navidrome username and password
3. Make the address permanent: in your router's settings, reserve that IP address for the server phone (often called "DHCP reservation" or "static lease"). Otherwise the router may give it a new address after a restart, and Spindle won't find it.

Both phones must be on the same Wi-Fi. Spindle allows plain `http` only for home-network addresses (192.168.x.x, 10.x.x.x, 172.16-31.x.x) and Tailscale addresses. Anything else has to use `https`.

### Optional: listening away from home

- **Tailscale:** install it on both phones and sign in to the same account, then use the server's Tailscale name instead, for example `http://music-phone.<your-tailnet>.ts.net:4533`. It runs as a VPN on your main phone, and Android allows only one VPN at a time.
- **A public https address**, for example through Cloudflare Tunnel: Spindle already accepts any `https` address. Setting it up has security and cost trade-offs, so plan it separately.

## How Spindle keeps in sync

- **Library:** the first sign-in loads every song's details. After that, each sync compares albums with the last sync and downloads only the ones that changed. It runs when the app opens (at most every 15 minutes), when the connection comes back, and from Settings → Refresh library. Settings → Rebuild reads everything again.
- **Likes and playlists:** saved on the server as Navidrome favourites and playlists. Changes made offline wait on the phone and are sent at the next connection. If you change the same playlist on two devices while offline, the last one to sync wins.
- **Listening history:** each song counts as played once you've heard half of it (or 4 minutes). Plays while offline are sent later with the time they happened.
- **Streaming cache** (default 2 GB, adjustable in Settings): recently played songs. The oldest are removed when it's full.
- **Downloads:** albums, playlists, Liked songs or single songs you choose to keep. They're stored separately and never removed to make room for the cache. They're removed only when you turn the download off, remove the song from a downloaded playlist, or the song is deleted from the server.
