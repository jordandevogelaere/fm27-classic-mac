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
