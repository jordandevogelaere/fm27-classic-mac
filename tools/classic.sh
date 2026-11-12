#!/bin/zsh
# Install or remove the Mac port of the FM Blog Classic Skin (personal use only).
#   tools/classic.sh install   copy the 14 bundles + catalog into the game, and the skin/graphics into the user folder
#   tools/classic.sh restore   put the stock game files back and remove the skin/graphics folders
#   tools/classic.sh status    show whether game files are stock, skinned or something else
set -e
cd "$(dirname "$0")/.."
AA="$HOME/Library/Application Support/Steam/steamapps/common/Football Manager 27/fm.app/Contents/Resources/Data/StreamingAssets/aa"
USERDIR="$HOME/Library/Application Support/Sports Interactive/Football Manager 27"
PKG="packages/fm27-classic-mac"
STOCK="backups/27.0.1.2503222-steam26577676/aa"
USERITEMS=("skins/FM27 Clasic" "graphics/FM Blog Classic FM27 Continents" "graphics/FM Blog Classic FM27 Flags and Trophies")

files=(catalog.bin)
for f in $PKG/*.bundle; do files+=("StandaloneOSX/${f:t}"); done
src() { [[ "$1" == catalog.bin ]] && echo "$PKG/catalog.bin" || echo "$PKG/${1:t}"; }

state() {  # stock | skin | other
  local s=0 k=0
  for f in $files; do
    if cmp -s "$AA/$f" "$STOCK/$f"; then s=$((s+1)); elif cmp -s "$AA/$f" "$(src $f)"; then k=$((k+1)); fi
  done
  if (( s == $#files )); then echo stock; elif (( k == $#files )); then echo skin; else echo "other ($s stock, $k skin, of $#files)"; fi
}

case "$1" in
  status) echo "game files: $(state)"; for u in $USERITEMS; do [[ -e "$USERDIR/$u" ]] && echo "present: $u" || echo "absent:  $u"; done ;;
  install)
    if pgrep -f "Football Manager 27/fm.app" >/dev/null; then echo "Quit FM27 first."; exit 1; fi
    st=$(state)
    if [[ "$st" == other* ]]; then echo "Game files are neither stock build 26577676 nor this skin: $st. The game probably updated; not installing."; exit 1; fi
    for f in $files; do cp "$(src $f)" "$AA/$f"; cmp -s "$(src $f)" "$AA/$f"; echo "installed $f"; done
    for u in $USERITEMS; do mkdir -p "$USERDIR/${u:h}"; rm -rf "$USERDIR/$u"; cp -R "$PKG/user/$u" "$USERDIR/$u"; echo "installed $u"; done
    echo "Done. In FM27: Preferences > Interface > Skin > FM27 Clasic." ;;
  restore)
    if pgrep -f "Football Manager 27/fm.app" >/dev/null; then echo "Quit FM27 first."; exit 1; fi
    for f in $files; do cp "$STOCK/$f" "$AA/$f"; cmp -s "$STOCK/$f" "$AA/$f"; echo "restored $f"; done
    for u in $USERITEMS; do rm -rf "$USERDIR/$u"; echo "removed $u"; done ;;
  *) echo "usage: tools/classic.sh install|restore|status"; exit 1 ;;
esac
