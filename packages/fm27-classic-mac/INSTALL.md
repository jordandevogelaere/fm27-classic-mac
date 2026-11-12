# FM27 Classic Skin for Mac: installing on another Mac

This is a Mac port of the FM Blog Classic Skin, made for personal use only. Please don't share it.

## Before you start

- **Mac only.** On a Windows PC, use the author's original Windows installer instead.
- **Exact game version.** The skin fits only FM27 27.0.1, Steam build 26577676. The script checks this and refuses to install on any other version.
- **Steam version of FM27**, installed in the default Steam location.

## Install

1. Copy this whole folder (`fm27-classic-mac`, about 145 MB) to the other Mac, for example with a USB stick or AirDrop.
2. Quit FM27 if it is open.
3. Open the Terminal app, type `cd ` (with a space), drag the folder onto the Terminal window, and press Enter.
4. Run:
   ```bash
   ./install.sh
   ```
5. Start FM27 and choose Preferences → Interface → Skin → **FM27 Clasic** (the author's spelling).

If the script says it could not write into the game, open System Settings → Privacy & Security → App Management, allow Terminal, and run it again.

## Remove

```bash
./install.sh restore
```

This puts the original game files back from the `backup-stock` folder the installer made, and removes the skin and graphics folders. If that backup is missing, use Steam instead: right-click the game → Properties → Installed Files → Verify integrity of game files.

## After a game update

A Steam update replaces some of these files, and the skin stops working or partly disappears. The skin then has to be rebuilt for the new version; this package will refuse to install on it.

## What the script does

- Checks that all 15 game files are the originals of build 26577676 (checksums in `stock.sha256`).
- Copies those originals to `backup-stock` next to the script.
- Copies 14 bundles and `catalog.bin` into the game.
- Copies the skin to `~/Library/Application Support/Sports Interactive/Football Manager 27/skins` and two graphics packs to `.../graphics`.

## The script (`install.sh`)

```zsh
#!/bin/zsh
# FM27 Classic Skin, Mac port. Personal use only.
#   ./install.sh            install the skin
#   ./install.sh restore    put the original game files back and remove the skin
set -e
cd "$(dirname "$0")"
AA="$HOME/Library/Application Support/Steam/steamapps/common/Football Manager 27/fm.app/Contents/Resources/Data/StreamingAssets/aa"
USERDIR="$HOME/Library/Application Support/Sports Interactive/Football Manager 27"
BACKUP="backup-stock"
USERITEMS=("skins/FM27 Clasic" "graphics/FM Blog Classic FM27 Continents" "graphics/FM Blog Classic FM27 Flags and Trophies")
src() { [[ "$1" == catalog.bin ]] && echo "catalog.bin" || echo "${1:t}"; }

[[ -d "$AA" ]] || { echo "FM27 not found at: $AA"; exit 1; }
if pgrep -f "Football Manager 27/fm.app" >/dev/null; then echo "Quit FM27 first."; exit 1; fi

if [[ "$1" == restore ]]; then
  [[ -d "$BACKUP" ]] || { echo "No backup found. Use Steam: Properties > Installed Files > Verify integrity of game files."; exit 1; }
  while read -r hash f; do cp "$BACKUP/$f" "$AA/$f"; echo "restored $f"; done < stock.sha256
  for u in $USERITEMS; do rm -rf "$USERDIR/$u"; echo "removed $u"; done
  echo "Done. The game is back to its original files."
  exit 0
fi

# 1. every game file must be the original of build 26577676, or already this skin
while read -r hash f; do
  have=$(shasum -a 256 "$AA/$f" | cut -d' ' -f1)
  if [[ "$have" != "$hash" ]] && ! cmp -s "$AA/$f" "$(src $f)"; then
    echo "Not installing: $f is not from FM27 27.0.1 (Steam build 26577676)."
    echo "This skin only fits that exact game version."
    exit 1
  fi
done < stock.sha256

# 2. back up the originals once, next to this script
while read -r hash f; do
  if [[ ! -f "$BACKUP/$f" ]]; then
    have=$(shasum -a 256 "$AA/$f" | cut -d' ' -f1)
    [[ "$have" == "$hash" ]] && { mkdir -p "$BACKUP/${f:h}"; cp "$AA/$f" "$BACKUP/$f"; }
  fi
done < stock.sha256

# 3. copy the skin in
while read -r hash f; do
  cp "$(src $f)" "$AA/$f" || { echo "Could not write into the game. Allow your terminal under System Settings > Privacy & Security > App Management, then run this again."; exit 1; }
  echo "installed $f"
done < stock.sha256
for u in $USERITEMS; do
  mkdir -p "$USERDIR/${u:h}"; rm -rf "$USERDIR/$u"; cp -R "user/$u" "$USERDIR/$u"; echo "installed $u"
done
echo "Done. Start FM27, then choose: Preferences > Interface > Skin > FM27 Clasic."
```
