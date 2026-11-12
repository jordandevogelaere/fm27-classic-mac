#!/bin/zsh
# Usage: tools/apply.sh <folder-of-bundles>
#   tools/apply.sh packages/fm24-test                                   apply a built skin
#   tools/apply.sh backups/27.0.1.2494769-steam26385295/aa/StandaloneOSX  restore originals (only files a skin touches)
set -e
cd "$(dirname "$0")/.."
GAME="$HOME/Library/Application Support/Steam/steamapps/common/Football Manager 27/fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX"
SRC="${1:?give a folder of .bundle files}"
if pgrep -f "Football Manager 27/fm.app" >/dev/null; then echo "Quit FM27 first."; exit 1; fi
# when restoring, only copy back the bundles that skins in packages/ replace
if [[ "$SRC" == backups/* ]]; then
  names=(${(u)$(ls packages/*/*.bundle | xargs -n1 basename)})
else
  names=($(ls "$SRC"/*.bundle | xargs -n1 basename))
fi
for n in $names; do
  cp "$SRC/$n" "$GAME/$n" && cmp -s "$SRC/$n" "$GAME/$n" && echo "copied $n"
done
