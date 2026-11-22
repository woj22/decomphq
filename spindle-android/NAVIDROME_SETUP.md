# Running Navidrome on an Android phone for Spindle

Spindle streams from a Navidrome server. These steps run Navidrome on a spare Android phone that holds your music, and reach it from anywhere through Tailscale.

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

## 2. Tailscale on both phones

1. Install **Tailscale** from the Play Store on the server phone and on the phone running Spindle. Sign in to the same account on both.
2. In the Tailscale app on either phone, find the server phone's name, for example `music-phone`. With MagicDNS (on by default) its full name is `music-phone.<your-tailnet>.ts.net`. The full name is shown in the Tailscale admin console under Machines.
3. In Spindle, sign in with:
   - Server address: `http://music-phone.<your-tailnet>.ts.net:4533`
   - Your Navidrome username and password

Spindle allows plain `http` only for addresses ending in `.ts.net`. Tailscale encrypts that traffic end to end, so it's safe. Any other address has to use `https`.

Android allows one VPN at a time. If another VPN app is on, Tailscale can't connect, and Spindle will show your saved library offline.

## How Spindle keeps in sync

- **Library:** the first sign-in loads every song's details. After that, each sync compares albums with the last sync and downloads only the ones that changed. It runs when the app opens (at most every 15 minutes), when the connection comes back, and from Settings → Refresh library. Settings → Rebuild reads everything again.
- **Likes and playlists:** saved on the server as Navidrome favourites and playlists. Changes made offline wait on the phone and are sent at the next connection. If you change the same playlist on two devices while offline, the last one to sync wins.
- **Listening history:** each song counts as played once you've heard half of it (or 4 minutes). Plays while offline are sent later with the time they happened.
- **Streaming cache** (default 2 GB, adjustable in Settings): recently played songs. The oldest are removed when it's full.
- **Downloads:** albums, playlists, Liked songs or single songs you choose to keep. They're stored separately and never removed to make room for the cache. They're removed only when you turn the download off, remove the song from a downloaded playlist, or the song is deleted from the server.
