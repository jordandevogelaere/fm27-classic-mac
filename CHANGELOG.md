# Change log

Game: FM27 27.0.1.2503222, Steam build 26577676 (from 2026-11-12). Earlier: 27.0.1.2494769 / 26385295, 27.0.0 / 26340721.
Backup of original bundles: backups/27.0.1.2494769-steam26385295/aa (older build kept alongside)

## 0.0.1 (2026-11-10)
- fm24-test: sets --primary to red. Not built or applied yet.

## Toolchain test (2026-11-10): FM Skin Builder 0.7.1 does not work on FM27
- FM27 uses Unity 6000.3.18f1; FM26 used 6000.0.52f1. FM Skin Builder 0.7.1 (25 Sep 2026) targets FM26.
- Its CLI opens FM27 style bundles and lists variable names, but property names and selectors come back
  empty and the .uss export is 0 bytes.
- Dry run of fm24-test (3 variables to red) reported 3670 colour changes instead of 3. Not applied.
- Real FM27 variable names are in debug/scan/*/bundle_index.json (var_map), e.g. --brand-theme-primary,
  --colours-brand-accent, --layout-ui-global-background, --data-tables-background-odd.

## 0.0.2 (2026-11-10): own patcher, tools/fmpatch.py
- Uses UnityPy 1.25.4 (tools/venv). Reads FM27 stylesheets correctly; readable export in debug/uss.
- fm24-test built to packages/fm24-test: 7 definitions of 3 variables set to red, in
  ui-styles_assets_common.bundle and ui-styles_assets_default.bundle. Re-read and diffed: no other change.
- Not applied to the game yet.
- Known gap: standard properties (padding, height...) are stored as numeric ids in FM27, shown as
  -unity-id(N) in the export. Only custom variables with colour values can be patched so far.

## 0.0.3 (2026-11-10): rebuilt for 27.0.1
- Steam updated the game; 62 bundles changed, 6 of them ui-styles. New backup taken, fm24-test rebuilt from it.
- fm24-test applied to the game via tools/apply.sh (2 bundles). In-game result not checked yet.

## 0.0.4 (2026-11-10): test skin v2
- 0.0.3 loaded in game without errors, but its 3 variables have only 6-14 uses each, so no clear visible change.
- v2 sets --brand-theme-accent, --brand-theme-ui-base (red), --global-text-primary (yellow),
  --layout-modules-block-surface (dark green). Built to packages/fm24-test, not applied yet.
- v2 applied to the game. In-game result not checked yet.

## fm24 0.1.0 (2026-11-10)
- fm24-test v2 confirmed in game (yellow text on main menu): toolchain works end to end.
- New skin skins/fm24: 13 variables, neutral greys and blue accent. Colours are approximations, not sampled.
  Built to packages/fm24, not applied yet.
- fm24 0.1.0 applied to the game (replaces fm24-test). In-game result not checked yet.

## fm24 0.1.1 (2026-11-10)
- 0.1.0 seen in game: text normal, Voorkeuren button half blue (gradient), menu tiles still navy.
- Added 19 variables: remaining magenta/lilac to blue, navy "midnight" family to neutral grey. Built, not applied.

## Navigation investigation (2026-11-10)
- Top bar = VisualTreeAsset `PrimaryNavigationBar` (gameworld VTA bundle), 54px high row, class
  `tile-mockups-navigation-core-primary-hi-res`. Menu buttons = `MenuBar` > ButtonGroup.row-direction-normal
  with six `navigation-tab-portal-default` templates. `OverviewTitleBar` stacks Primary + SecondaryNavigationBar.
- No layout asset embeds OverviewTitleBar, so game code places it above the page content.
- Layout assets are readable/writable with UnityPy (tools/vta_dump.py prints an outline).
- Standard style properties are numeric ids (89 distinct), e.g. 131083 flex-direction, 131087 height,
  131105 width, 131102 position, 458752 background-color (inferred from context, not confirmed).

## nav-test (2026-11-10): first layout experiment
- tools/vtapatch.py patches layout assets from a skin's layout.json. Works around a UnityPy 1.25 write
  limitation (null managed reference). Untouched layouts re-serialise byte-identical.
- skins/nav-test: MenuBar's three ButtonGroups switched from row to column (class swap + inline
  flex-direction). Built to packages/nav-test (1 bundle, only MenuBar and its inline sheet differ). Not applied.
- nav-test applied to the game. In-game result not checked yet.
- nav-test seen in game: menu items stacked (squashed inside the 54px bar). Layout patching works.

## nav-test 2 (2026-11-10): sidebar strip experiment
- :root padding-left 200px (AlwaysAppliedStyleSheet) + MenuBar groups absolute, column, 200px wide, left -355px, top 70px.
- packages/nav-test also carries palette 0.1.1 (built on top of packages/fm24) so the bundles don't clash. Not applied.
- nav-test 2 applied to the game (3 bundles). In-game result not checked yet.
- nav-test 2 seen in game: no left strip (:root padding ignored), menu gone off-screen left. Palette 0.1.1 fine.

## nav-test 3 (2026-11-10)
- fmpatch can now append a new single-class rule. New rule `.base-layer-content { margin-left: 200px }`
  (content root of Portal/Squad/Training/Club/Recruitment/Nation screens, which sit inside `.panel`).
- MenuBar groups: left -170px, top 90px, width 200px. Built with palette 0.1.1, not applied.

## Restored (2026-11-10)
- All three patched bundles restored; game bundle folder is identical to the 27.0.1 backup. nav-test 3 was never applied.

## FM Blog Classic Skin Build 134 -> Mac port (2026-11-12)
- Windows package targets 27.0.1 / Steam build 26385295 (same as our Mac backup). It changes 14 bundles +
  catalog.bin (XOR deltas against the exact Windows originals) and installs a user skin folder
  "skins/FM27 Clasic" (USS + textures) plus two graphics packs. The USS targets elements (#FMBClassicSidebar,
  #MainNav ...) that only exist in their patched layout bundles, so both parts are needed.
- tools/unityfs.py rebuilds FM bundles byte-for-byte (LZ4HC 12). Windows originals = Mac bundle with
  platform tag 19 for 8 of 14 bundles (hash-verified). Those 8 are ported: Windows patched file
  reconstructed and hash-verified, then retagged to macOS (1 byte differs). In packages/fm27-classic-mac.
- Not reconstructable from Mac files (need the real Windows originals): ui-backgrounds_assets_,
  ui-styles_assets_common, ui-styles_assets_default, the three ui-visualtreeassets bundles, catalog.bin.
  Windows depot is 4530372 (8.7 GB). Steam shows a pending update to build 26577676 (6.8 MB, not installed).
- Licence note from FM Blog: editing/redistributing needs their written permission. Port kept for personal use.
- Steam updated to 26577676 (27.0.1.2503222). Changed: globalobjects, ui-styles_assets_common, catalog.bin, 2 scene bundles. Backup in backups/27.0.1.2503222-steam26577676.
- Port target is now 26577676. 12 of the skin's bundles are unchanged by the update. globalobjects merged
  object-by-object (update: version TextAssets; skin: GridLayoutSettings; no overlap) -> packages/fm27-classic-mac.
- ui-styles_assets_common changed in the update (SIStyles + AssetBundle object): needs a 3-way merge once the
  Windows original is available. catalog.bin also changed.
- User files (skins/FM27 Clasic, two graphics packs, 1134 files) staged in packages/fm27-classic-mac/user,
  hash-checked against the installer manifest.
- Windows manifest for build 26385295 (SteamDB, depot 4530372, seen 2026-11-10 15:59 UTC): 1558728990731412600.

## 2026-11-12 — Classic Skin Mac port complete (not yet installed)

- Windows originals for build 26385295 fetched with DepotDownloader (7 files, 52 MB) into `windows-originals/`; all match the installer's stock hashes.
- Patched Windows files rebuilt (stock XOR payload, truncated to the length in `patches.tsv`); all 7 match the installer's target hashes.
- Windows vs Mac stock objects differ only in `m_ContentHash` and per-asset element ids (constant offset per asset), so:
  - `ui-backgrounds_assets_`, `ui-styles_assets_default` and the three `ui-visualtreeassets_*` bundles are the patched Windows bundles retagged to platform 2 (objects byte-identical to the patched Windows ones).
  - Known risk: layout assets in these three bundles carry Windows element ids; template overrides that cross into the unpatched fantasydraft/init/intro layout bundles could miss.
- `ui-styles_assets_common`: skin and game update both changed `SIStyles`. `tools/merge_styles_common.py` re-applies the skin's 105 dimension edits (corner radii to 4px) and 3 image re-points onto the 26577676 Mac bundle.
- `catalog.bin`: the skin appends 127 keys (asset GUIDs) and a new key table. `tools/port_catalog.py` appends the same onto the 26577676 Mac catalog, translating offsets via a parallel walk of both stock key tables; dependencies verified to resolve to the same bundles.
- `tools/classic.sh install|restore|status` handles bundles, catalog and user files, and refuses to install if the game is neither stock 26577676 nor this skin.

## 2026-11-12 — Layout bundles rebuilt with Mac element ids

- First install: main menu lost its tile titles and icons and showed placeholder text ("Tertiary button"). Cause: the three layout bundles carried Windows element ids, so overrides coming from unpatched Mac layout bundles could not find their targets.
- `tools/port_vta.py`: objects the skin left alone now come from the Mac stock bundle; in objects the skin changed or added, ids are translated through a Windows-to-Mac map built from both stock builds (133,028 ids; fields `m_Id`, `m_ParentId`, `uxmlAssetId`, `m_ElementId`, `m_ElementIdsPath`, `m_ContentContainerId`). Ids of elements in the skin's new assets that have no stock counterpart are kept.
- Reinstalled (restore, then `tools/classic.sh install`; install refuses to overwrite an older skin build directly). Not yet checked in game.

- Personal change: FMBLOG sidebar logo hidden via a rule appended to `custom.uss` (package and installed copy).
