# FM27 Classic Skin for Mac

A Mac port of the FM Blog Classic Skin for Football Manager 27, which brings back the FM24-style left sidebar navigation. The original skin is Windows-only; this repository holds a ready-to-install Mac version and the scripts used to build it.

**Personal use only.** The package contains the skin author's work and Sports Interactive's game files. Keep this repository private and don't share it.

## Requirements

- macOS, with the Steam version of FM27 in the default Steam location
- FM27 **27.0.1, Steam build 26577676** exactly. The installer checks this and refuses any other version.

## Install

1. Download or clone this repository.
2. Quit FM27.
3. In Terminal, go to the package folder and run the installer:
   ```bash
   cd packages/fm27-classic-mac
   ./install.sh
   ```
4. Start FM27 and choose Preferences → Interface → Skin → **FM27 Clasic** (the author's spelling).

To remove the skin and put the original game files back:

```bash
./install.sh restore
```

Full instructions and troubleshooting are in [packages/fm27-classic-mac/INSTALL.md](packages/fm27-classic-mac/INSTALL.md).

## After a game update

A Steam update overwrites some of the skin's files, so the skin breaks or partly disappears. It then has to be rebuilt for the new game version; this package will not install on it.

## What's in here

| Path | Contents |
| --- | --- |
| `packages/fm27-classic-mac/` | The install package: 14 game bundles, `catalog.bin`, the skin and graphics folders, `install.sh` and `INSTALL.md` |
| `tools/` | Scripts used to build the port (see below) |
| `skins/` | Earlier experiments: an FM24 colour palette and navigation tests |
| `CHANGELOG.md` | Step-by-step log of how the port was made, including dead ends |

One personal change is included: the FMBLOG logo in the sidebar header is hidden (last rule in the skin's `custom.uss`).

## How the port was built

The Windows skin ships as patches against the Windows game files of Steam build 26385295. The port:

1. Rebuilds the patched Windows files from the original Windows files and the installer's patches, checked against the installer's checksums.
2. Converts them to Mac bundles (`tools/winport.py`, `tools/unityfs.py`).
3. Translates the layout element IDs from Windows to Mac numbering, since the two builds number interface elements differently (`tools/port_vta.py`).
4. Re-applies the skin's style edits onto the current game version, where a game update had changed the same file (`tools/merge_styles_common.py`).
5. Adds the skin's 127 catalog entries to the Mac catalog (`tools/port_catalog.py`).

Rebuilding needs things that are not in this repository: the Windows skin installer, the original Windows game files for build 26385295, and a backup of the stock Mac game files. `tools/classic.sh` installs and restores on the Mac the port was built on.
