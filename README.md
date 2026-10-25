# Deck Library

Native Linux app that gathers ports, applications and emulated games in one library and manages their Steam shortcuts, per-game settings and controller layouts on Steam Deck. The interface is available in English and Spanish (see [Language](#language)).

**English** · [Español](#español)

![Deck Library with a fictional demo library](assets/screenshot.png)

![Game overview with fictional artwork](assets/screenshot-game.png)

## Language

The interface comes in English and Spanish. Change it under **Settings → Covers and appearance → Idioma · Language** (Automatic, Español or English) and reopen the app. An existing installation keeps its current language; a new one follows the system language. `DECK_LIBRARY_LANG=en` or `es` overrides the saved choice for one run. Every interface string has an English translation, and a test fails when a new one is added without it.

## Install

In Steam Deck Desktop Mode, extract the archive and double-click **Instalar.sh**, choosing **Run / Ejecutar**. This installs the app and opens it. Alternatively, open a terminal in the extracted folder:

```sh
python3 install.py --desktop
```

Open **Deck Library** from the applications menu or desktop shortcut. No sudo, ROM downloads, emulator installation or SteamOS filesystem changes. The app installs in `~/Applications/DeckLibrary` and keeps private data separately in `~/.local/share/deck-library`.

Requires Python 3.11+, PyGObject and GTK 3 (available on the Steam Deck used for validation). On other distributions install their `python3-gi`/GTK 3 packages. The core and its tests use only Python's standard library; no pip packages or network service needed.

## Open Deck Library directly from Steam

1. Install and open Deck Library in Desktop Mode. Finish the first-run assistant.
2. In Desktop Mode, click **Add to Steam** beside the top navigation tabs (also available under **Settings → Deck Library in Steam**).
3. If Steam is open, the app shows a persistent pending-changes banner. Finish your other changes, exit Steam once and wait for the banner to disappear. The background worker saves the shortcut and its Deck controls; no per-change restart dialog is shown.
4. Return to Gaming Mode, find **Deck Library** in Steam's library and press **Play**. The shortcut launches the native Linux app fullscreen, with `--gaming` and its navigation template.

Use the right trackpad and right trigger for pointer/click, the D-pad or stick for navigation, **A** to activate, **B** to go back and **LB/RB** to change sections (**X** opens the search keyboard with native controller input). **Steam + X** opens Steam's on-screen keyboard. Physical controller validation in Gaming Mode is still pending; automated tests cover the shortcut, template and 1280×800 interface.

### Add individual games to Steam

Open a game's cover and click the blue **Add to Steam** button. It changes to **Shortcut pending** while queued and **In Steam** after the shortcut is saved. Add several by clicking **Select**, marking covers and using the batch action. Save the queue by exiting Steam once after finishing, then reopen Steam or return to Gaming Mode. Each game gets its own shortcut and can be launched directly from Steam; opening Deck Library first is optional. The game files stay in their current locations.

For a game already in Steam, **Play** uses its existing Steam shortcut and controller identity. **More options → Files and Steam shortcut** provides editing, artwork and removal tools.

## Use

The first launch opens a four-step Spanish onboarding flow: welcome, installation/game detection, artwork provider and library handoff. Discovery runs in the background. Users can add a missing folder or configure an emulator instead of guessing where to start. Repeat onboarding from **Settings**.

The library fills the window, with top navigation, 2:3 portrait cards, platform filters and search. Open a cover for the game overview: **Play** (green), **Add to Steam** (blue), selectable settings cards and a fixed **Apply settings** action. Selecting a card only previews the profile; changes are written, with a backup, after applying. Technical differences expand under **View changes**. The persistent **Controls**, **Content** and **Advanced** tabs open dedicated task pages. Settings cards use the full width and **Community** remains available in the same tab bar. **More options** contains import/export, artwork and shortcut tools. **Select** reveals batch controls only when needed. **Port catalog** opens the downloadable port catalog directly. Use **Settings → Installations and folders** to add discovery folders.

Steam changes accumulate in a persistent banner and are saved when Steam closes. No restart prompt interrupts each change. Settings → Add Deck Library to Steam prepares a fullscreen Gaming Mode shortcut with Deck navigation controls. The library also offers portrait cards, thumbnails in list view, platform groups and a read-only conflict report. See [Deck interface](docs/DECK-INTERFACE.md) and [optional community server](community/README.md). Physical Gaming Mode validation remains a separate check.

### Artwork providers and motion

Automatic artwork uses a personal SteamGridDB API key when configured, then Libretro for supported retro systems and Wikipedia PageImages as a fallback. No account is required for the fallback providers. Only exact normalized matches or explicitly documented edition aliases are auto-selected. A game page offers online search, result selection, a source link and a local file alternative. Wikipedia images may represent a shared article rather than the exact edition's box. SteamGridDB requests static 600x900 community grids; a valid personal API key is required.

All image requests run off the GTK thread and download into private local storage. Remote responses and image sizes are bounded. Failed lookups leave readable placeholder cards. API keys, downloaded images and personal libraries are excluded from public releases and preset/feedback exports. Only game names are sent to artwork search providers. Offline use remains available with cached artwork. Game-page entrances, profile-card states, expanding change previews, task navigation, icon hover feedback and inline save confirmations have bounded animations. They respect the animation preference; no motion loop runs while the app is idle.

References: [SteamGridDB API v2](https://www.steamgriddb.com/api/v2), [Libretro thumbnail service](https://thumbnails.libretro.com/), [MediaWiki PageImages API](https://www.mediawiki.org/wiki/Extension:PageImages#API).

### Supported games and apps

- Existing Linux ports/AppImages/scripts, including Quiver's saved executable selection.
- EmuDeck launchers: Switch/Eden, Wii/GameCube/Dolphin, PS1/DuckStation, PS2/PCSX2, PSP/PPSSPP, Nintendo 3DS/Azahar and Wii U/Cemu.
- Any other emulator/app via a custom command with arguments. Paths with spaces are supported. Commands are passed as argument arrays, never evaluated by a shell.
- Existing WiiCompiled installations in WheelWizard Flatpak use the compiled game directly, not the setup tool.
- Windows games need a configured Wine/Proton launcher (for example a script from Lutris/Heroic); selecting a raw `.exe` is diagnosed rather than pretending it will work.

The automatic scanner deliberately skips updates, DLC, firmware, keys, duplicates and setup programs. It does not cover every emulator's file formats automatically. Manual/custom entries cover the rest; emulators and legal game files must already be installed. Adding an entry is not a promise of emulator compatibility.

### Mods and a game that stays loading

Switch entries have **Usar mods de Eden**. Turning it off builds an isolated configuration using the same NAND, keys, saved games and controller settings, with an empty mod directory. It doesn't remove mods or overwrite Eden's main config. This makes a base-game comparison possible when a mod fails to boot. New entries retain Eden mods by default. The local Mario Kart 8 shortcut uses CTGP again; the no-mod comparison remains available. Managed Eden launches skip AppImage self-update prompts using the bundled updater's `DISABLE_AUTO_UPDATES=1` option; opening Eden normally keeps its existing update preference. Isolated profiles copy the existing lsfg-vk configuration when present.

### Gaming Mode

Generated launchers preserve Steam Input identity and the current display/session. They strip inherited loader/runtime variables before launching native apps or Flatpak and raise a low file-descriptor limit. They never hardcode a physical DISPLAY or send a remote session to the Deck's screen. Native shortcuts disable desktop-layout injection while Steam is running the game.

This addresses common launch-environment problems; a damaged/misconfigured Flatpak graphics extension or a mod/emulator crash still needs diagnosis. Failures show an error instead of silently closing. **Use diagnostics; don't delete saved games to troubleshoot.**

## Features

### Remove Steam shortcuts

**Remove from Steam** is on each game page and in the selection bar. It deletes the shortcut from `shortcuts.vdf`, moves its grid images to `grid/.deck-library-backups`, forgets its controller layouts and renumbers the remaining shortcuts. Games, files and saves are not touched, and a timestamped backup of `shortcuts.vdf` is written first. Like additions, removals are queued while Steam is open and applied once it is closed. Shortcuts that disappear from Steam are also dropped from the library on the next scan.

### Controller layouts (DualSense and others)

Steam keeps the Steam Input layout of a non-Steam shortcut in one `configset_controller_<family>.vdf` per controller family. A shortcut that only has an entry for the Deck itself gets a desktop/browser layout when a DualSense, DualShock, Xbox or Switch Pro pad is connected, so the game sees no XInput device. New shortcuts now receive the gamepad template for every family that has none; existing choices are kept. **Controller → Assign controller layout** on a game page replaces the saved layout for that shortcut (a backup of each changed file is kept). Writes need Steam closed. This can be disabled with `fix_controllers` in `settings.json`.

### Updates

The **Updates** page checks, at most every six hours: Deck Library releases on GitHub, the preset catalog, ports installed through Quiver (`version.txt` against the latest release of their repository) and Project-2099. Everything uses HTTPS with size limits. Deck Library can install its own update: the release must include `DeckLibrary-X.Y.Z.tar.gz` and its `.sha256`; the archive is verified, extracted with path checks and installed with `install.py`. Automatic installation of Deck Library updates is on by default and can be switched off on the page; it only runs in Desktop Mode and asks for a restart. Ports installed from the catalog can also update automatically (off by default). Ports installed by Quiver are only reported; Quiver applies them. GitHub allows 60 anonymous API requests per hour; set `GITHUB_TOKEN` to raise the limit. The catalog defaults to `presets/catalog.json` in this repository.

### Port catalog

**Port catalog** merges four sources: Quiver's public lists (`tgeorgiadis/quiver-community-app-catalog`), GithubLauncher's list (`SirDiabo/GHLAppList`, which includes Rexglue/Xbox 360 and system emulators and marks AI-assisted projects), a few built-in recommendations and the user's own repositories (about 255 ports). Both launchers use the same data model, so ports installed by either one (`apps.json`, `Apps/`, `version.txt`, `selected_executable.txt`) are found in any folder under `~/ports` or `~/Applications` and checked for updates. Each entry shows its icon, or box art found by platform, plus category, source and notes; the list can be filtered by category and source.

**Add repository** accepts any GitHub address or `owner/repo`, checks its latest release for a Linux build and keeps it in `custom_ports` of `settings.json`. Extra list files can be added with `catalog_sources` (raw.githubusercontent.com URLs in Quiver's or GithubLauncher's format).

**Install** downloads the latest release asset for Linux x86_64 (AppImage, tar.gz/tar.xz/tar.bz2/tar.zst, ZIP or a bare executable), checks the SHA-256 that GitHub publishes for the asset, extracts it with path and link checks into `~/ports/<folder>` and registers the version, so the library lists it and the updates page can detect new releases. Portable Windows ZIPs and standalone executables are supported through an isolated Proton prefix per port. Setup/MSI installers and source-only projects need an explicit integration; catalog data cannot inject installation scripts. When several executables are possible none is chosen and the game can be added by hand. Updating moves the previous folder to `~/ports/.deck-library-replaced` instead of deleting it.

Originals and ports share a library card, with **ROM found** when the original file is still available. Both entries and files remain intact; **View original** opens the emulated entry and **Show separately** reverses the association. Integrated adapters let users select and validate missing ROM/disc/BIOS files. Other projects identify their own setup assistant or manual preparation. Port details offer **Install with Proton** for portable Windows packages, including x86 releases. The [reviewed projects and requirements](docs/PORTS.md#proyectos-revisados-el-21-de-octubre-de-2026) distinguish package support from gameplay validation.

The recommended Spider-Man entries (`alexbeavs-ps1-ports/spider-man-recomp`, `spider-man-2-enter-electro-recomp`) are setup kits: the user supplies a USA disc (SLUS-00875 and SLUS-01378 Rev 1) and a BIOS, and the kit generates and compiles the game on first start. SteamOS ships no compiler or headers, so these ports run inside the **KDE SDK 6.11 Flatpak** (CMake, Ninja, GCC, Python 3, SDL3/Vulkan/X11/Wayland/ALSA headers). Deck Library asks before installing it once for the user from Flathub (no root, no change to SteamOS), detects kits after installation (`CMakeLists.txt` next to `README-SETUP.txt`) and starts them through `flatpak run --devel` with network, display, audio, input devices and the home folder. A missing SDK is reported as a blocking diagnostic. Installed kits must live under the home folder, which is the only user data the sandbox mounts. Each kit card also compares its requirements with what is already on the Deck: the BIOS is searched by exact SHA-256 in the EmuDeck `bios` folder whatever the file is called, and the disc is checked by Redump-style name against the PlayStation library (a name check only; the kit's wizard verifies the exact dump hash). The kits are pinned to the USA executables, so a PAL disc cannot be used without a separate port. Once a kit has been generated and compiled (its wizard, or `psxrecomp_cli.py generate` and `rebuild` inside the SDK), the library entry points to the built game and keeps the same id.

### Automatic port setup

Everything needed to make a port playable is scripted and starts from **Set up** in the catalog (it also runs right after **Install**). Deck Library finds the disc in the library by the serial inside its `SYSTEM.CNF` (BIN, ISO or CUE; the file name does not matter) and the BIOS by exact SHA-256 in the EmuDeck folder, shows what it found and asks before doing anything:

- **Recompilation kits** (Spider-Man, Spider-Man 2): `verify-disc`, `generate` and `rebuild` of the kit's own CLI inside the KDE SDK Flatpak, then the BIOS choice is stored in `build/bios.cfg`. The entry then starts the built game.
- **OpenPete** (Spyro the Dragon, downloaded from openpete.com and checked against the SHA-256 the site publishes): the AppImage is unpacked once, its game module is pre-built from the disc inside the SDK and the entry starts it in fullscreen with `--disc`.
- **CTR Turbocharged** (ctr.cmzi.uk; the site publishes no hash, only a size, which is checked): the raw MODE2/2352 BIN is copied as `ctr-u.bin` to `~/.local/share/ctr-turbocharged/assets`. On first start the game asks for an optional font (choose *Use Luckiest Guy*) and a graphics preset.

Ports published on their own site are found by reading its page (`resolve_web`); downloads are limited to the hosts `dl.openpete.com` and `ctr.cmzi.uk`, and updates are detected by comparing the published version.

### Zelda ports

Three more built-in entries use the same **Set up** flow:

- **Minish Cap** (Project Picori, `999sian/tmc`): the GBA ROM is found by SHA-1 in `~/Emulation/roms/gba` whatever its file name (USA, Europe or Japan) and copied next to the binary as `baserom.gba`, `baserom_eu.gba` or `baserom_jp.gba`. The European ROM carries Spanish text.
- **A Link to the Past** (`snesrev/zelda3`, pinned commit, built from source): the USA 1.0 ROM is found by SHA-1 in `~/Emulation/roms/snes` (a 512-byte copier header is stripped), Pillow and PyYAML are installed into a local folder, `make` runs inside the KDE SDK and the executable starts there with `SDL_AUDIODRIVER=pulseaudio` (SDL otherwise tries JACK first inside the sandbox and gives up). The aspect ratio is set to 16:10. The game was never released in Spanish.
- **Wind Waker HD** (`ZeldaWWHDRecomp/ZeldaWWHDRecomp`, AppImage verified against the release's SHA-256): the Wii U disc (`.wux`, `.wud` or Cemu `.wua`) is taken from the library. For `.wux`/`.wud` the disc key (matched by the `[USA, WUD]`/`[EUR, WUD]` comment) and the Wii U common key come from Cemu's `keys.txt` in EmuDeck's `bios` folder, are written to private (0600) files in a temporary folder only while the port's own setup runs, and are deleted afterwards; they are never logged or stored. The USA disc includes Spanish.

**Settings → Apply maximum settings for Steam Deck** is the app's one-click maximum-quality profile. It raises DuckStation (5x, PGXP), Dolphin (3x, 16x anisotropic), Azahar (3x, large screen with the small one visible, swap on L4/R4, async shaders) and Eden (async shaders, 16x anisotropic) to what the 1280x800 screen supports, keeping a backup of every file and skipping a running emulator.

Per-game defaults: Eden's Breath of the Wild gets Latin American Spanish, 1x resolution with FSR and normal GPU accuracy; Azahar gets Spanish console language, 3x, large-screen layout (both screens visible) and an app-owned Steam Input layout where L4 sends F9 (swap screens) and R4 F10 (layout) for 3DS shortcuts; Wind Waker HD runs with `WWHD_` environment options (Spanish, 16:10, picture-in-picture GamePad, interpolation, FXAA); Picori with the European ROM uses Spanish and 5x internal scale; the PS1 kits get 4x supersampling, PGXP and the kit's own PGXP / fast-loading / CD-speed mods (the kits' runtime has no frame interpolation or widescreen).

A Link to the Past in Spanish: `deck_library.patching.apply_ups` applies the fan translation's UPS patch (all three CRC32s verified); the result is recognised by SHA-1, built with `restool.py --extract-dialogue` / `--languages=es` and selected with `Language = es`. For the PS1 kits, `psx.deck.display` is a built-in plugin package (framework plugin API: `psx_mod_set_frame_interpolation(0)` with motion-adaptive blending, `psx_mod_set_fixed_display_aspect(16, 10)`) added to the kit's `runtime.cmake` with a backup; it needs the kit to be rebuilt.

Steam artwork: the game detail page has **Steam artwork**, backed by `deck_library.steamart` (SteamGridDB API, vertical and horizontal covers, hero, logo with its position JSON, and icon, in the file layout Decky's SteamGridDB plugin writes). Existing files are kept unless a slot is explicitly replaced, replaced files are backed up, images are validated by magic bytes (PNG/JPEG/WebP, 20 MB limit) and written through the same Steam-closed queue as shortcuts. **Settings → Complete artwork for all Steam shortcuts** (`steamart.complete_missing`) fills only empty slots for every shortcut and reports per game. The app needs the user's own SteamGridDB key; the key embedded in Decky's plugin is reserved for it by its author.

UI: top navigation, portrait game cards, distinct action colours, visible focus and finite transitions (`deck_library/motion.py`: fades, staggered card entrance, slide between library and detail, toasts), all disabled by the animations switch. The per-game settings dialog starts with the emulator's current values read from its own files. `deck_library/wiiupdate.py` updates a Quiver-managed WiiCompiled in place (SHA-256 from the GitHub digest, `install --game`, rollback of the previous setup tool).

A per-game guide (requirements, what the app sets, limits, how to revert) is in [docs/PORTS.md](docs/PORTS.md) (Spanish). `ports.build_spanish_zelda3` applies a UPS translation patch found in Downloads or the SNES ROM folder when its result has the SHA-1 zelda3 expects.

None of these ports exists for A Link Between Worlds, Breath of the Wild or Skyward Sword; those stay emulated.

### Library view

The toolbar filters by platform and by **type** (ports, emulator games, Minecraft instances, Steam shortcuts, custom). Having a port installed does not hide the emulated copy of the same game; **Settings → Originals and ports** lists the ones that share a page and lets you show them separately or send the original to the trash. A catalog port keeps a single library entry with a stable id, an imported Steam shortcut that a managed entry owns is not listed twice, and Minecraft instances are matched with their shortcut by name.

### Per-game settings

**Game settings** edits the allowlisted options of an emulator for one game: resolution, anti-aliasing, texture filtering, PGXP and other fixes, FPS limit, overclock and disc speed-up for DuckStation (`gamesettings/<SERIAL>.ini`); internal resolution and EFB options for Dolphin; Eden and Prism options use the same form. Controls start from the effective value (the game file, else the emulator-wide setting), only changed options are written, and every save keeps a backup that **Restaurar anteriores** reverts. Files are patched line by line, so repeated keys, patches and cheats stay as they were. The DuckStation serial is read from `SYSTEM.CNF` in BIN/ISO/CUE images; for CHD it must be entered in the game's identifier field. DuckStation per-game patches and cheats are not editable yet.

## Steam data and backups

Only the selected Steam account is edited. Existing games, app IDs, tags, artwork and unrelated fields are preserved. Matching legacy shortcuts are updated; repeat additions do not create duplicates. A binary KeyValues parser validates the file before any writes. Each changed library gets a timestamped backup beside `shortcuts.vdf`; writes are atomic and refused while Steam is running or a concurrent edit is detected.

Queued changes and logs stay private. A user service performs deferred writes where systemd is available; outside Steam a detached worker is the fallback. If launched inside Steam and neither service nor worker can detach safely, exit Steam and run `./launch.sh sync --no-wait` from Desktop Mode to finish the saved queue.

## Local / GitHub community presets

GTA IV Complete Edition installations in Steam also expose **GTA IV fix**: a pinned FusionFix 4.0.5/DXVK recipe with SHA-256 verification, complete backups and restore. It keeps the game closed and preserves existing graphics/FPS choices. One Steam Deck OLED user confirmed the resulting experience; sustained FPS were not measured. See [the GTA IV instructions and button API](docs/GTAIV.md).

The [DMC3 Crimson Steam launch notes](docs/DMC3-CRIMSON.md) document a separate, locally boot-tested wrapper and Steam API compatibility fix. This is an integration guide; Crimson installation is not yet a button in Deck Library.

The [Spider-Man: Shattered Dimensions Steam Deck notes](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) record the user-confirmed Windows/Proton setup for audio, voices and controls. It is a guide until Deck Library supports Windows/Proton presets.

Game details expose recommended profiles, a change preview, apply/backup/restore, allowlisted export, JSON import and local feedback export. A user-provided HTTPS raw GitHub catalog can be downloaded without write credentials. An optional self-hosted SQLite service supports own accounts, real star ratings and comments. Sharing a profile is explicit and moderated. See [the portable preset format](docs/PRESETS.md).

The initial catalog includes WiiCompiled, Eden profiles for Smash, Mario Kart 8 and three Mario Party games, plus a Prism instance preset with Steam Input recommendations. Profiles explicitly distinguish proposals, boot checks and user confirmations; hardware/version matching does not imply universal FPS or compatibility.

Switch games without a bundled or imported title-specific profile offer three proposals: **Balanced**, **Performance** and **Compatibility**. They use the included profiles as references and require a Title ID; declared compatibility is Eden 0.2.1. Choose a card, expand **View changes** if needed and press **Apply settings**. This saves a backup and writes the profile without opening the game. **Play** is a separate action. **Undo** restores the configuration before the latest application. Existing title-specific profiles keep priority, and each card displays its author's declared testing status. Performance still needs validation per game.

## Discovery, covers and setup

Portrait covers are the default view; list view is available. Local Steam, Quiver, Eden and Prism images and privately downloaded provider artwork are reused. Custom local covers can be selected. Public release artwork uses fictional placeholders; downloaded game artwork is not shipped.

**Settings → Installations and folders** reads EmuDeck paths without executing its settings script, offers manual paths and emulator executable selection, and discovers Prism instances by their folder IDs. Microsoft account files are never read or shared.

**Prepare Mario Kart Wii** uses the official pinned setup 0.2.33 and an optional KDE SDK 6.11 sandbox to compile a supplied PAL RMCP01 image in its own private installation. It applies the known source-level F12 exit fix, stabilizes toolkit links, rebuilds and applies the confirmed 1.5× baseline. It needs Internet and around 20 GB of temporary space; progress and cancellation are visible. Other recompilation projects are not automatically supported by this wizard.

Switch details inventory base, updates, DLC and LayeredFS mods. User-supplied PFS0 NSPs can be hash-validated and registered in Eden's NAND without deleting the originals; ZIP mods are installed with path validation and previous-mod backups. Valid emulator keys/firmware remain the user's responsibility. Registering updates in NAND avoids relying on asynchronous library scanning for direct CLI boots. Native/default and manually chosen Eden config paths are supported; not every Flatpak/AppImage combination was integration-tested.

## Development

```sh
python3 -m unittest discover -s tests -v
./launch.sh scan                     # read-only, prints local paths; don't publish the output
./launch.sh check ENTRY_ID           # local diagnostics
./launch.sh sync --no-wait            # saves only if Steam is already closed
```

GTK is imported only for the graphical interface. Core tests don't require a display. The repository contains code, artwork and documentation only. Do not commit library files, logs, profiles, ROMs, keys, firmware or personal Steam data. Public CI checks the core on Linux.

## Status

Version **1.1.0**. Core tests cover binary Steam preservation, malformed/concurrent writes, command quoting, discovery, launch errors and mod isolation. Desktop and Gaming Mode require separate integration validation; test results are recorded in `docs/VALIDATION.md`. Source and downloadable releases: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library).

Version 1.0 covers the catalog with install and uninstall, the library, per-game settings, Steam integration and the English and Spanish interface, all covered by automated tests. **Not yet validated:** navigation with a physical gamepad in Gaming Mode and playing an installed port from start to finish; see `docs/V1-CHECKLIST.md` (in Spanish). Release history: [docs/CHANGELOG.md](docs/CHANGELOG.md) and the [published releases](https://github.com/GonzaCass/deck-library/releases).

## Project-2099

The Project-2099 adapter prepares a supplied Xbox 360 ISO (or a ZIP/7z containing one) using the pinned official Beta 4.1 installer under Proton. PS3 images are rejected before downloads. Includes a proposed 720p / 60 FPS profile, Steam shortcuts and installed-port discovery. Gameplay validation remains pending. [Spanish version](#español).

## Community accounts and update progress

**Community → My account → Create account / Sign in** opens the configured Keycloak device authorization page in the browser. The desktop app never asks for the account password. Anonymous browsing works without an account; writing requires a session. **Share my settings → Review my settings → Publish profile** exports only allowlisted values and submits the reviewed profile for moderation. Each user can leave one editable 1–5 star rating and comment per public profile. An unrated proposal is labelled **Sin valoraciones**. The server includes the packaged profiles as proposals, without inventing reviews or performance measurements.

Eden cards offer **Balanced**, **Performance** (0.75×) and **Quality** (1.5×), plus compatibility profiles. Title-specific settings keep their original values in the balanced card. These are proposals, not universal performance guarantees. Known emulator-version checks still apply.

Catalog and update rows show download progress, percentage and estimated time from measured bytes. Compilation shows its current phase without an invented completion percentage. Completed/error state stays in that port's row during the current session. Completed installs invalidate stale update notices. Tab changes reuse the existing library and catalog; native SDL2 input supplements Steam's navigation template in Gaming Mode.

## Port management

Discovery identifies installed variants before offering another installation. The library offers reversible hiding or confirmed trashing of original disc images, with shared-file checks. Downloads have inline cancellation/dismissal. The catalog combines the current Quiver API, legacy lists and an independent curated list, tracks real addition/release dates and includes a bundled factual fallback index. Sources: [Quiver API client](https://github.com/tgeorgiadis/quiver-launcher/blob/main/Services/QuiverCatalogClient.cs), [independent list](https://github.com/Sebastrion/awesome-unofficial-pc-ports).

Project-2099 updates download verified installer/payload assets from the official release, install in a temporary folder, preserve UserData and retain the complete old installation. Beta 5 changes engines; old renderer settings and mods stay in that backup. Game shortcut Proton arguments are preserved. The update button does not launch the game. Live Beta 5 gameplay validation is pending; automated tests exercise staging, backup, preservation and failure recovery using a simulated installer.

Included playtested profiles are labelled with their actual test level and take precedence over custom imports in the primary cards. Portrait artwork fills its canvas without side bands.

### Accounts inside the app

Open **Account** (the account icon in the top bar), or **Community → My account** from a game. **Sign in** and **Create account** open Deck Library’s account forms inside the app. Registration requires email verification on the public service. Password recovery is available from the sign-in form. Browsing profiles does not require an account.

Keycloak handles passwords, registration requirements and recovery. Its forms run in a separate, ephemeral WebKit process; the application receives only its own revocable community session. Sessions are checked when opening Account; expired sessions are cleared. Closing the access panel cancels polling and closes the embedded browser.

On Steam Deck the embedded view reuses an installed GNOME Flatpak runtime when available. Otherwise the app offers to install the component from Flathub, or continue in the browser. The app selects X11 when available for GTK embedding; an explicit Wayland override uses the browser fallback. In Gaming Mode, use the D-pad/stick to move, A to select, B to cancel access and **Steam + X** for the keyboard. Physical controller navigation still needs confirmation on the Deck.

### Controller navigation

The focused game has a bright border and a highlighted title/card. The left stick and D-pad navigate the actual rows and columns; A opens the game, B returns to the same card, X opens the search keyboard and LB/RB change tabs. The right stick scrolls the current view. Moving through the library keeps the focused card visible and does not check games for batch operations. Focus survives artwork refreshes.

Deck Library’s Steam Deck layout now uses native gamepad input on both sticks, with mouse control on the right trackpad. Upgrading refreshes only Deck Library’s existing template, with a backup; it does not change Steam configsets or other games’ layouts. Close and reopen Deck Library from Steam to reload its layout. A custom layout remains selected if you chose one. The physical controls still require confirmation on the Deck; automated coverage includes a real SDL virtual controller driving the GTK interface.

### Focus and button indicators

The focus marker now follows every control: Play, profiles, settings, menus and dialogs. It is restored when the game view refreshes. **B / Circle** closes the current menu or dialog, returns from a game section to its overview and then returns to the library. Button badges show both Deck and PlayStation names (**A / Cross**, **B / Circle**) with contextual actions. Secondary hints adapt to compact windows; dialogs keep Select and Back visible. The marker follows logical focus, so it does not depend on the desktop theme’s button focus style.

### Catalog metadata

The current public Quiver API supplies game titles, project names, descriptions and artwork. Catalog rows show the game title first and the port name underneath; search matches either name. Current API metadata takes priority over older lists. Portrait artwork supports larger files, falls back to project icons and exact game/platform artwork, and retries failed downloads after one hour. The catalog cache refreshes once on upgrade to load the additional metadata. Projects from independent lists may lack these fields.

### Single-window workflows

Notices, confirmations, artwork, local file selection, account, community and setup tools are pages inside the main application window. They create no secondary GTK windows and do not resize the Gaming Mode surface. Action buttons remain outside the scrolling body. Back/B/Circle returns through nested tasks and restores focus. Tasks that explicitly disable closing cannot be cancelled with Back. Existing synchronous task handlers use a GLib loop on the embedded page; rendering and background work continue. Launcher failures are recorded locally and shown inside Deck Library when it is running or next opened, without launching a system error dialog.

The header includes **Add to Steam**, using the existing pending Steam queue. The header scrolls horizontally on compact windows. Explicit actions that open Steam, emulator settings, external documentation or an external sign-in fallback still open their respective applications.

### Port details and independent game identities

Catalog cards open an internal detail page rather than starting installation. The page identifies the original game separately from the port, shows source descriptions, requirements and available release metadata, and exposes installation/update as explicit actions. Transfer controls remain outside the clickable card body.

The [independent list](https://github.com/Sebastrion/awesome-unofficial-pc-ports) stores game identities in HTML summary headings. The parser now retains them and each project description, without leaking one heading into another. Exact identities can reuse artwork and console metadata from Quiver’s public games endpoint. Platform artwork lookup also supports GBA, Nintendo 64, Super Nintendo and Xbox. Tools and unknown games are not matched by project-name guesses. The catalog cache refreshes once after upgrading.

### Charcoal styling and Deck interactions

Panels use neutral charcoal surfaces, softly rounded corners, fewer permanent borders and no decorative shadows. Primary action colors and explicit controller focus remain visible. The update badge has independent active/inactive tab styles and tested text contrast above 4.5:1.

Search fields advertise X / Square for the keyboard. GTK text entries use INHIBIT_OSK; the Steam keyboard is requested explicitly through the same keyboard URI used by SDL, from X, the search icon or A on a text field. Physical text input remains available. [GTK input hints](https://docs.gtk.org/gtk3/flags.InputHints.html), [SDL keyboard implementation](https://github.com/libsdl-org/SDL/blob/SDL2/src/video/x11/SDL_x11keyboard.c).

GTK kinetic touch scrolling is enabled, with a capture-phase drag fallback for touches exposed as mouse events by Steam. The fallback claims a gesture only after a movement threshold, so short taps remain available to buttons. Focus scrolling uses content coordinates and the full card bounds, including its caption, instead of the already-scrolled viewport coordinates.

Completed changes and errors use a larger, dismissible eight-second notice inside the main window. Transient progress remains inline. Physical validation of SteamOS keyboard hints and touch translation is still required.

Integrated profiles occupy the relevant Equilibrado/Rendimiento/Calidad slots and retain their original settings. WiiCompiled’s confirmed Quality profile remains the default selection; two lower-resolution variants are explicit untested proposals. Verification requires an exact match of the bundled game, adapter, settings and test metadata. An imported author's claim is shown separately and cannot inherit the integrated verification label.

Community profiles have a dedicated, always-expanded preview with ratings and links to details/comments. Additional local and compatibility profiles are visible in a separate section. Profile changes remain close to the three primary cards. Community browsing stacks its panes on compact displays.

## Installing, uninstalling and review

- **Several games per release:** when a project publishes one AppImage per game, the app installs all of them and each appears in the library under its own name. OpenRA uses this today (Red Alert, Tiberian Dawn and Dune 2000). Anyone who already had OpenRA with a single game sees **Install all games** in the catalog.
- **Uninstall:** each installed port has **Uninstall** in the catalog and on its page. The folder moves to `~/ports/.deck-library-removed` (saves stored inside it go with it and can be recovered from there; nothing is deleted), the game leaves the library and, if it was in Steam, its shortcut, artwork and controller layout are removed.
- **Review:** every catalog card says **Reviewed** (built-in recommendations and projects with a reviewed recipe) or **Unreviewed** (external lists). The first install of an unreviewed port asks for confirmation once.
- **Nested archives and multi-tool packages:** a ZIP that only wraps a tar.gz is opened, and when a package ships several tools the project's launcher is chosen.
- The 1.0 conditions and their status are in [docs/V1-CHECKLIST.md](docs/V1-CHECKLIST.md) (in Spanish).

## Account, updates and Steam artwork

- **Account:** while nobody is signed in, the top bar shows **Sign up or sign in** and each game page repeats the button next to "Share my settings". Once signed in, the bar shows the user name. The session is stored in `~/.local/share/deck-library/community-session.json` (mode 0600) and survives closing and reopening the app, until the user signs out or the service rejects it.
- **Community settings:** a game page shows Deck Library's three standard profiles on top, with the verified mark where it applies. The community section lists only profiles people uploaded; the profiles Deck Library already ships are not repeated there. "Other profiles" is left for ones the user imported or saved.
- **Updates:** each port shows the first lines of its notes, and **What's new** opens with the gamepad (collapsible sections now take focus and open with A, including **Update options** and the cover provider).
- **Floating labels:** with a gamepad (Gaming Mode) tooltips are turned off, because without a mouse they stayed stuck over the page that opened under the idle pointer; with a mouse, a game's full name only appears when the title is cut off.
- **Opening a game:** no banner covers the game page any more; the button says "Opening…" and the footer names the game. A game that is in Steam is opened through Steam, which may show its own "Starting game" notice while it starts.
- **Icon and Steam artwork:** Deck Library ships a new icon and its own artwork (portrait cover, banner, background and logo) for its Steam shortcut; it is applied when the shortcut is added and, in Desktop Mode, to the existing one, and it only fills empty slots: an image the user chose is never replaced. `tools/render_art.py` redraws everything.

## References

[WiiCompiled](https://github.com/patchzyy/Wiicompiled), [Eden](https://git.eden-emu.dev/eden-emu/eden), [Flatpak launch/extension implementation](https://github.com/flatpak/flatpak/blob/main/common/flatpak-run.c). This project is independent of Valve, EmuDeck, Quiver and those emulators.

---

<!-- BEGIN SPANISH: generated from LEEME.md by tools/sync_readme.py; edit LEEME.md instead -->
# Español

**[English](#deck-library)** · Español

![Interfaz con una biblioteca de ejemplo](assets/screenshot.png)

Agregar ports, aplicaciones y juegos emulados a Steam desde una sola ventana.

## Usar Deck Library directamente desde Steam

1. Instalar la app en modo Escritorio: descargar y extraer [la última versión](https://github.com/GonzaCass/deck-library/releases/latest), abrir la carpeta y ejecutar **Instalar.sh**. Completar el asistente inicial.
2. En modo Escritorio, dentro de Deck Library, pulsar **Añadir Deck Library a Steam** junto a las pestañas superiores. También está disponible desde **Ajustes → Deck Library en Steam**.
3. Si Steam está abierto, el acceso queda preparado y aparece el aviso de cambios pendientes. Terminar de agregar o editar lo necesario, cerrar Steam una vez y esperar que desaparezca el aviso. El proceso en segundo plano guarda el acceso y los controles.
4. Volver al modo Juego. Buscar **Deck Library** en la biblioteca de Steam y pulsar **Jugar**. Se abre directamente a pantalla completa, con la biblioteca, las carátulas y los ajustes.

La primera instalación se hace desde Escritorio; después se puede abrir la app desde Steam. El acceso usa la versión nativa de Linux. Para navegar: trackpad derecho y gatillo derecho para puntero/clic; cruceta o stick para moverte; **A** para activar; **B** para volver; **X** para abrir el teclado en la búsqueda. **Steam + X** abre el teclado en pantalla. La plantilla y la interfaz se comprobaron con pruebas automáticas; la navegación con el mando físico en modo Juego sigue pendiente de prueba.

### Agregar cada juego a Steam

Abrir la carátula del juego y pulsar el botón azul **Agregar a Steam**. Verás **Acceso pendiente** hasta que se guarde al cerrar Steam; después aparecerá **En Steam**. Para varios juegos, pulsar **Seleccionar**, marcar sus carátulas y usar **Agregar a Steam** en la barra inferior.

Después de guardar los accesos, cada juego se puede abrir directamente desde su propia ficha de Steam. Abrir Deck Library antes es opcional. También se puede pulsar **Jugar** dentro de Deck Library: si ese juego ya tiene acceso, la app utiliza el de Steam y su configuración de mando.

Los cambios se acumulan: basta con cerrar Steam una vez al terminar. **Ver cambios** detalla las operaciones pendientes y permite descartarlas. La app y los juegos tienen accesos separados.

![Ficha del juego con biblioteca de ejemplo](assets/screenshot-game.png)

**GTA IV:** buscar lo instalado, abrir la ficha del juego y elegir **Mejoras para GTA IV → Aplicar arreglo de GTA IV**. Instala FusionFix 4.0.5 y los ajustes de DXVK confirmados en esta Deck, con respaldo y restauración. No abre el juego. [Instructivo y detalles](docs/GTAIV.md).

**DMC3 Crimson:** el [arreglo de arranque desde Steam](docs/DMC3-CRIMSON.md) está documentado con su wrapper, compatibilidad de la DLL, respaldo y requisitos para un futuro botón. Se comprobó el arranque local; aún no hay instalador de Crimson integrado en la app.

**Spider-Man: Shattered Dimensions:** la [guía de configuración en Steam Deck](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) registra Proton, audio, voces y controles confirmados en esta instalación. Todavía no es un preset aplicable desde la app.

Guía por juego (requisitos, qué deja ajustado la app, límites y cómo revertir): [docs/PORTS.md](docs/PORTS.md).

## Ports de Zelda y ajustes máximos

El catálogo incluye tres ports nativos que se preparan con **Configurar**:

- **The Minish Cap** (Project Picori): la ROM de GBA se reconoce por SHA-1 en `~/Emulation/roms/gba`, con cualquier nombre de archivo (USA, Europa o Japón).
- **A Link to the Past** (`snesrev/zelda3`): se compila dentro del SDK de KDE a partir de la ROM USA 1.0 de `~/Emulation/roms/snes` (se quita el encabezado de copiador si lo tiene). Queda en pantalla completa, 16:10 y sin límite de sprites.
- **The Wind Waker HD** (`ZeldaWWHDRecomp`): usa la imagen de Wii U de la biblioteca. Las claves se leen de `keys.txt` de EmuDeck, se escriben en archivos temporales privados solo durante la preparación y se borran después. Nunca se muestran ni se guardan.

A Link Between Worlds, Breath of the Wild y Skyward Sword no tienen port nativo y siguen con emulador.

**Ajustes → Aplicar ajustes máximos para Steam Deck** deja DuckStation (5×, PGXP), Dolphin (3×, anisotrópico 16×), Azahar (3×, pantalla grande con la otra pequeña, F9/F10 para alternar, shaders asíncronos) y Eden (shaders asíncronos, anisotrópico 16×) en lo máximo que admite la pantalla de 1280×800. Se hace un respaldo de cada archivo y se omite el emulador que esté abierto.

### Español, pantalla y mods por juego

- **Breath of the Wild** (Eden): idioma español latinoamericano y, solo para este juego, resolución 1× con escalado FSR y precisión de GPU normal, para evitar el desenfoque de bajar 1,5× a la pantalla. El juego va fijo a 30 FPS.
- **A Link Between Worlds** (Azahar): idioma de la consola 3DS en español, resolución 3× (la pantalla superior ocupa la altura de la Deck) y **pantalla grande con la otra pequeña** (las dos visibles). En la Deck, **L4** alterna entre pantalla superior e inferior (F9) y **R4** cambia la disposición (F10), mediante un layout de Steam Input propio para los juegos de 3DS.
- **Wind Waker HD**: español, 16:10, imagen del GamePad en un recuadro dentro de la misma ventana, interpolación de cuadros (hasta la frecuencia de la pantalla), FXAA y anisotrópico. Los cambios se guardan como variables `WWHD_` del acceso.
- **Minish Cap** (Picori): español con la ROM europea, escala interna 5× (1200×800), pantalla completa y reloj de 90 FPS.
- **A Link to the Past**: el juego original no tiene versión en español. Con la traducción de aficionados «Re-Traducción F01h» (parche UPS sobre la ROM USA; el resultado tiene el SHA-1 `461FCBD7…` que el port reconoce), **Configurar** extrae los textos y deja `Language = es`. Los diálogos quedan en español; los rótulos del menú (ITEM, EQUIPMENT…) siguen en inglés porque el port no importa esos gráficos.
- **Spider-Man 1 y 2** (kits PSX): supersampling 4× y PGXP; el **60 FPS real («Smooth 60»)** queda disponible pero apagado. El motor escala su lógica por el contador de vblanks, pero su bucle principal espera un vblank extra por cuadro y topa en 30 FPS; el kit se parchea para anular esa espera y acelerar la CPU emulada (8× y 10×). En una medición, los cambios de búfer por vblank pasaron de 0,50 a ~0,96 (juego 1) y de 0,34 a ~0,9 (juego 2); las escenas que saturan la GPU emulada pueden quedar por debajo. Con el 60 real activado el juego se sintió acelerado y con los sticks incontrolables, por eso no se aplica por defecto. Los mods de carga rápida y de CD no se activan (aceleraban todo el juego). Más la interpolación de cuadros y el widescreen 16:10 experimental del mod «Steam Deck display». Requiere recompilar el kit (botón «Mejorar rendimiento»).
- **Breath of the Wild** en Eden: el parche «60 FPS (1.9.0)» de Nexus Mods se instala en la carpeta de mods del juego (exefs, hash de compilación CD57B23F…). 90 FPS no es posible con ese parche: Eden emula una pantalla de 60 Hz.

### Arte de Steam

En la ficha de un juego con acceso en Steam, **Más opciones → Archivos y acceso de Steam → Carátulas de Steam** busca en SteamGridDB (con la misma clave API de **Ajustes**) la portada vertical, la horizontal, el fondo, el logotipo y el ícono, con las mismas rutas de archivo que usa el plugin SteamGridDB de Decky. Lo que ya existe se muestra marcado y no se reemplaza salvo que se elija otra imagen; cada archivo reemplazado deja una copia en `grid/.deck-library-backups`. **Completar lo que falta** elige automáticamente la primera imagen de cada espacio vacío. Las imágenes elegidas se guardan al cerrar Steam, junto con el resto de los cambios pendientes.

**Ajustes → Completar arte de todos los accesos de Steam** hace lo mismo para toda la biblioteca de una vez: solo llena los espacios vacíos, informa por juego qué se agregó y qué no se encontró, y deja los cambios preparados para guardarse al cerrar Steam. Hace falta una clave API propia de SteamGridDB: la clave del plugin de Decky va embebida en ese plugin y su autor advierte que usarla en otros proyectos provoca el bloqueo.

### Diseño, movimiento y actualizaciones propias

- **Interfaz:** navegación superior, carátulas verticales y una ficha con Jugar en verde, Steam en azul y ajustes en violeta. Elegir una tarjeta y pulsar **Aplicar ajustes**; seleccionar no escribe cambios. **Ver cambios** despliega los detalles técnicos. Las pestañas **Controles**, **Contenido** y **Avanzados** permanecen visibles al cambiar de tarea. Importar, exportar, carátulas y archivos están en **Más opciones**.
- **Movimiento:** entrada de la ficha y de las tarjetas, transiciones entre tareas, despliegue de detalles, estados de botones y confirmaciones al guardar. Se desactiva desde **Ajustes → Carátulas y apariencia → Animaciones**.
- **Ajustes:** la vista previa compara valores del archivo del juego y distingue los perfiles pendientes de los que ya coinciden. Aplicar guarda un respaldo y **Deshacer** restaura la configuración anterior. La edición manual conserva los cambios sin guardar durante una actualización de carátulas o detección.
- **Clave de SteamGridDB:** Ajustes explica cómo conseguirla (iniciar sesión en steamgriddb.com, Perfil → Preferencias → API), permite mostrarla u ocultarla y tiene un botón **Probar clave**.
- **Mario Kart Wii (WiiCompiled):** la pestaña **Actualizaciones** ofrece **Actualizar aquí** cuando hay una versión nueva del setup oficial. Descarga el AppImage, verifica su SHA-256 con el valor que publica GitHub, vuelve a instalar el juego con la imagen PAL de la biblioteca (necesita unos 20 GB libres) y restaura el setup anterior si algo falla. No hace falta abrir Quiver.

## Instalación

1. Descargar `DeckLibrary-1.1.0.tar.gz` desde [la última versión publicada](https://github.com/GonzaCass/deck-library/releases/latest) y extraerlo en modo Escritorio.
2. Abrir la carpeta y hacer doble clic en **Instalar.sh**. Elegir **Ejecutar** cuando Dolphin pregunte.
3. Se instala la aplicación y se abre. También queda **Deck Library** en el escritorio y en el menú de aplicaciones.

Si Dolphin abre el archivo como texto, abrir una terminal en esa carpeta y ejecutar `python3 install.py --desktop`. Necesita Python 3.11+ y GTK 3/PyGObject; se verificaron en la Deck utilizada. No necesita sudo ni pip.

## Primer inicio

![Asistente inicial de Deck Library](assets/welcome.png)

Se abre un asistente de cuatro pasos: **Bienvenida → Detectar → Carátulas → Listo para Steam**. Busca EmuDeck, emuladores, ports e instancias de Prism en segundo plano. Revisar los juegos encontrados y agregar una carpeta si falta algo. Elegir el proveedor de carátulas y abrir la biblioteca. Se puede repetirlo desde **Ajustes**.

## La biblioteca

Las carátulas tienen formato vertical 2:3. Tocar una para abrir su ficha: **Jugar** y **Agregar a Steam** son las acciones principales. Debajo están las tarjetas de ajustes. **Controles**, **Contenido** y **Avanzados** abren cada tarea; **Más opciones → Archivos y acceso de Steam** muestra rutas y comandos.

Para agregar varios juegos, tocar **Seleccionar**, marcar las carátulas y usar **Agregar a Steam** en la barra inferior. Si Steam está abierto, los cambios quedan preparados hasta cerrar Steam una vez al terminar. Los accesos aparecen en **No Steam** en modo Juego.

**Catálogo de ports** abre directamente los ports disponibles para instalar. En **Ajustes → Instalaciones y carpetas** se pueden corregir las rutas de emuladores, ports, Prism y bibliotecas en microSD. Los ejecutables Windows necesitan un launcher de Wine/Proton configurado.

## Carátulas automáticas

**Automático** usa SteamGridDB si agregaste una clave personal; si no, busca carátulas en Libretro para las consolas compatibles y una imagen del juego en Wikipedia. Funciona sin crear una cuenta. Cuando una coincidencia es dudosa, se conserva una tarjeta de título para elegir la imagen. Wikipedia puede devolver arte representativo de un artículo compartido por varias ediciones, en vez de la caja exacta.

Para carátulas verticales de la comunidad, elegir **SteamGridDB** en el asistente o en **Ajustes** y agregar una [clave API personal](https://www.steamgriddb.com/profile/preferences/api). Esta integración requiere una clave válida; no se incluye una clave compartida en el paquete.

En la ficha, **Cambiar carátula** permite buscar por nombre, elegir entre los resultados o usar **Elegir imagen local**. El origen de cada descarga queda visible. Las imágenes y la clave se guardan solamente en esta Deck y no se incluyen al exportar presets o feedback. Las consultas envían el nombre del juego al proveedor. Sin conexión, los juegos y las carátulas ya guardadas siguen disponibles.

Hay transiciones entre pantallas y pasos del asistente, respuesta visual al pasar por las carátulas e indicadores durante las búsquedas. Se pueden desactivar las animaciones en **Ajustes**.

## Mods y partidas

En Switch, **Contenido** permite activar **Usar los mods instalados**. Desactivarlo prepara un perfil sin mods que conserva la ubicación de partidas, NAND y controles. No borra mods ni cambia la configuración principal. Los nuevos juegos de Switch usan los mods instalados por defecto; se pueden desactivar para comparar el arranque. Las actualizaciones y los DLC instalados siguen disponibles.

## Qué se comparte

El paquete incluye solamente la app, su código MIT, documentación y pruebas. **Cada persona aporta sus juegos y sus emuladores ya instalados.** No incluye ROMs, claves, firmware, cuentas, partidas ni mods. El asistente opcional puede preparar WiiCompiled usando una imagen propia y el setup oficial; también reconoce una instalación existente.

Steam se modifica cuando está cerrado, conservando los demás accesos. Se crea un backup junto a `shortcuts.vdf`. La app guarda su biblioteca y registros en `~/.local/share/deck-library`; no publicar esa carpeta.

## Estado de esta versión

Versión **1.1.0**. Los resultados de las pruebas están en [docs/VALIDATION.md](docs/VALIDATION.md). El funcionamiento de cada juego depende de su emulador y configuración. El instalador puede volver a ejecutarse para actualizar la app sin borrar la biblioteca.

La 1.0 incluye el catálogo con instalación y desinstalación, la biblioteca, los ajustes por juego, la integración con Steam y la interfaz en español e inglés, todo cubierto por pruebas automáticas. **Sin validar todavía:** la navegación con mando físico en modo Juego y jugar de punta a punta un port instalado; ver [docs/V1-CHECKLIST.md](docs/V1-CHECKLIST.md). El historial de versiones está en [docs/HISTORIAL.md](docs/HISTORIAL.md) y en las [versiones publicadas](https://github.com/GonzaCass/deck-library/releases).

La ficha de cada port indica cómo se preparan sus archivos: desde Deck Library, desde el asistente del propio port o manualmente. Si hay adaptador, se puede elegir la ROM, el disco o la BIOS que falten y se comprueban antes de preparar. **Instalar con Proton** permite usar paquetes Windows portables cuando corresponde. La [tabla de proyectos revisados](docs/PORTS.md#proyectos-revisados-el-21-de-octubre-de-2026) detalla los casos de God of War, inFAMOUS, Sonic, Smash, Time Crisis, Lord of the Rings y Crash; no implica que todos se hayan probado en juego.

Código y versiones descargables: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library). Para información técnica, consultar [README.md](README.md).

## Funciones de biblioteca y presets

Los juegos de Switch sin un preset específico incluido o importado ofrecen tres opciones en **Ajustes recomendados**: **Switch — Equilibrado**, **Switch — Rendimiento** y **Switch — Compatibilidad**. Toman como referencia los cinco perfiles existentes: Vulkan, modo portátil, resolución 1×, varios núcleos, velocidad al 100% y caché de shaders. Equilibrado usa precisión GPU normal sin shaders/presentación asíncronos; Rendimiento activa ambos; Compatibilidad usa precisión alta y desactiva ambos. Requieren un Title ID detectado o completado en **Editar juego** y declaran Eden 0.2.1. Son propuestas **Para probar**, sin garantía de FPS.

Elegir una tarjeta, desplegar **Ver cambios** y pulsar **Aplicar ajustes** para escribir el perfil con respaldo. El juego se abre por separado con **Jugar**. Cerrar el emulador antes de aplicar otra configuración. **Deshacer** recupera el estado anterior a la última aplicación. Los perfiles específicos tienen prioridad y cada tarjeta muestra el estado de prueba declarado por su autor.

- **Carátulas** como vista inicial; se puede cambiar a lista y elegir una imagen local. Se aprovechan imágenes existentes de Steam/Quiver/Prism cuando se encuentran; donde falta arte se muestra una tarjeta de título.
- **Ajustes → Instalaciones y carpetas** detecta EmuDeck y permite agregar carpetas de ROMs/ports, instalaciones de Quiver, Prism y WiiCompiled, y elegir programas de emuladores que no se detectaron.
- Las **instancias de Prism Launcher** aparecen individualmente para agregarlas a Steam. La ficha ofrece un layout recomendado de teclado/ratón y abre los controles de Steam; la selección del layout se hace allí.
- **Preparar Mario Kart Wii** pide una imagen PAL limpia RMCP01, usa el setup oficial 0.2.33, instala el SDK si falta, recompila y aplica la base nítida confirmada. Puede tardar varios minutos y necesita Internet y unos 20 GB temporales. Trabaja en una instalación propia, sin sobrescribir otra que ya funcione. Se puede cancelar y retomar una instalación incompleta.
- En Switch, **Base, updates y mods** muestra contenido, versión detectada por Eden y qué NSP está registrado en NAND. Permite elegir una base faltante, instalar updates/DLC propios y mods ZIP LayeredFS. Que un archivo esté disponible en una carpeta no significa que esté instalado en NAND. La versión base puede necesitar consultarse en Eden si no se identifica.
- **Ajustes recomendados** permite aplicar, respaldar, restaurar, importar/exportar JSON y guardar feedback para compartir. Hay siete perfiles iniciales con su estado de prueba. Algunos son propuestas; no todos están validados jugando.

Para compartir ajustes, usar **Más opciones → Exportar mis ajustes** y enviar el JSON; la otra persona lo carga con **Importar ajustes de un archivo**. **Comunidad** ofrece el servicio opcional de perfiles y feedback con inicio de sesión con cuenta propia. La biblioteca local funciona sin cuenta. Ver [servicio comunitario](docs/COMMUNITY-PRESETS.md).

El formato y sus límites están explicados en [docs/PRESETS.md](docs/PRESETS.md).

## Accesos existentes, carátulas y controles de Steam

**Actualizar** vuelve a buscar los ports instalados por Quiver, incluidas sus carpetas personalizadas, y los accesos **No Steam** de la cuenta activa. Si una instancia de Prism ya tiene un acceso, se vincula con él. La detección no incluye toda la biblioteca de juegos comprados en Steam.

En la ficha de un acceso existente, **Editar acceso de Steam** permite cambiar nombre, ejecutable, carpeta de inicio y opciones de lanzamiento. Se conserva su identificador, que mantiene asociados los controles, Proton y el arte. Para guardar estos cambios, Steam debe estar cerrado; la app acumula los cambios y los guarda cuando Steam se cierra.

La carátula elegida en Deck Library se copia al grid vertical de Steam al agregar o actualizar ese acceso, con copia de seguridad de la anterior. Elegir una nueva imagen no cambia Steam inmediatamente: usar **Agregar a Steam** para guardar también allí. No se generan automáticamente imágenes horizontales, fondos ni logotipos.

**Controles** muestra el perfil de Steam Input guardado localmente para la instancia de Minecraft, cuando está disponible, y abre los controles del acceso correcto. Los perfiles no descargados desde Steam Cloud o configurados en otra cuenta pueden no aparecer. No modifica las asignaciones automáticamente.

## Project-2099

El adaptador de Project-2099 prepara una ISO de Xbox 360 (o un ZIP/7z que la contenga) con el instalador oficial Beta 4.1 fijado, bajo Proton. Las imágenes de PS3 se rechazan antes de descargar. Incluye un perfil propuesto de 720p / 60 FPS, accesos directos de Steam y detección de ports instalados. La validación de juego sigue pendiente. [Guía](docs/PROJECT2099.md).

## Ports y originales

El catálogo consulta la API actual de Quiver, las listas de GithubLauncher y una lista independiente de ports. Incluye un índice propio de respaldo para poder consultarlo sin conexión. **Nuevos primero** usa la fecha real de incorporación cuando la fuente la publica; **Últimas versiones** ordena por fecha de release. Se muestra cuándo se actualizaron los datos. Una fecha desconocida no se inventa.

Un port detectado desde otra instalación aparece como instalado. Si hay otra variante del mismo juego, se identifica como alternativa y pide confirmar antes de instalarla. Las descargas permiten **Cancelar**; una tarea terminada o fallida se puede **Descartar** desde su fila. Un error de descarga no abre un diálogo que bloquee la app.

El port y su original se asocian automáticamente en una sola carátula. **ROM encontrada** indica que el archivo sigue disponible; **Revisar originales** o ese botón en la ficha permiten ver su ruta y abrir la ficha original. **Mostrar separado** revierte la asociación sin modificar archivos. **Enviar a la papelera** muestra los archivos y requiere confirmación; se bloquea si otro acceso usa alguno. Los discos originales pueden hacer falta para reconstruir un port al actualizarlo.

**Actualizaciones → Project-2099 → Actualizar** localiza la copia de Xbox 360 disponible o permite elegirla; verifica el SHA-256 del instalador y del paquete, instala en una carpeta temporal y conserva la versión anterior completa. Se preserva UserData. Beta 5 cambia de motor: los mods y ajustes gráficos antiguos quedan en el respaldo. Se mantiene el Proton elegido en el acceso del juego; el instalador utiliza su entorno de instalación. La actualización no abre el juego. También se incluye en la cola al habilitar actualizaciones automáticas de ports.

Los perfiles incluidos y probados aparecen entre los principales con **✓ Comprobado · usuario**. Una prueba de arranque se distingue con **✓ Comprobado · arranque**; no implica validación de rendimiento. Las propuestas nuevas conservan ese estado y los perfiles propios aparecen en las opciones adicionales. Las carátulas llenan el espacio vertical, recortando el excedente si tienen otra proporción.

### Iniciar sesión y registrarse

Abrir **Cuenta** con el icono de personas de la barra superior, o **Comunidad → Mi cuenta** desde un juego. **Iniciar sesión** y **Crear cuenta** abren los formularios dentro de Deck Library. Para registrarte en el servicio público es necesario verificar el correo. Desde el inicio de sesión también se puede recuperar la contraseña. Consultar perfiles no requiere una cuenta ni GitHub.

En la Steam Deck se reutiliza el componente web de GNOME si está instalado. Si falta, la app ofrece instalarlo desde Flathub o seguir en el navegador. En modo Juego: cruceta/stick para moverte, A para seleccionar, B para cancelar el acceso y **Steam + X** para escribir. La navegación física con mando queda pendiente de confirmación.

Cerrar el acceso cancela la espera y cierra su navegador interno. **Cerrar sesión** revoca el acceso comunitario. Las contraseñas las valida Keycloak; Deck Library guarda únicamente su sesión con permisos privados.

### Navegación con mando

El juego enfocado se resalta con un borde claro y el fondo de la tarjeta. **Palanca izquierda / cruceta:** recorrer juegos. **A:** abrir la ficha. **B:** volver al mismo juego. **X:** teclado en la búsqueda. **LB/RB:** cambiar pestaña. **Palanca derecha:** desplazar la vista. El foco se mantiene visible al recorrer la cuadrícula y se conserva al actualizar carátulas. Moverse por los juegos no los marca para agregarlos a Steam.

El perfil propio de Deck Library ahora usa las dos palancas como mando y conserva el ratón en el trackpad derecho. El instalador actualiza esa plantilla con respaldo; conserva los perfiles elegidos por el usuario y los controles de otros juegos. Cerrar y volver a abrir Deck Library desde Steam para recargarla. Si elegiste un perfil personalizado, seguirá seleccionado. El recorrido se comprobó con un mando virtual de SDL; falta confirmar las palancas físicas en modo Juego.

### Selector e indicadores

El resaltado también aparece en Jugar, perfiles, opciones, menús y ventanas, y se recupera al actualizar una ficha. **B / ○** cierra primero el menú o la ventana actual; dentro de un juego vuelve de los ajustes a la ficha y después a la biblioteca. **A / ✕** selecciona el control resaltado. Al pie se muestran los botones y su acción actual; las ventanas tienen sus propios indicadores de selección y regreso.

### Nombres e imágenes del catálogo

La API pública de Quiver aporta el nombre del juego, el proyecto que lo adapta, descripción e imágenes. El catálogo muestra primero el juego y debajo el nombre del port; la búsqueda admite ambos. Las carátulas se muestran en vertical. Si falla una descarga se intenta el icono del proyecto y después una portada coincidente por plataforma; los errores se vuelven a intentar después de una hora. Los proyectos de otras listas pueden tener menos información.

### Una sola ventana

Los avisos, confirmaciones, carátulas, archivos, cuenta, comunidad y herramientas se abren como páginas dentro de Deck Library. Mantienen el tamaño de la app en modo Juego. Las acciones quedan al pie y **B / ○** vuelve a la página anterior, recuperando el control seleccionado. En tareas que no se pueden interrumpir, Volver espera a que termine la operación. Los errores del lanzador también aparecen dentro de la app; si estaba cerrada, se muestran al volver a abrirla.

El botón **Añadir Deck Library a Steam** está junto a las pestañas y utiliza la misma cola de cambios de Steam. Si Steam está abierto, el acceso se guarda al cerrarlo. En ventanas compactas, la cabecera se desplaza horizontalmente y el mando lleva a la vista el botón seleccionado.

### Fichas de ports e identificación del juego

Pulsar la imagen o el texto de un port abre su ficha dentro de la app: juego original, nombre del port, descripción, plataforma, requisitos y versión cuando la fuente la informa. Instalar y actualizar son acciones separadas.

También se leen los nombres de los juegos en los encabezados de la lista independiente, y se buscan sus imágenes por coincidencia exacta con el catálogo de juegos. Por ejemplo, GSRecomp aparece como Golden Sun y Project-2099 como Spider-Man: Edge of Time. Las herramientas se mantienen como herramientas; no se les asigna un juego. Si una fuente no tiene carátula, la ficha permite reintentar sin esperar a que venza la caché del error.

### Apariencia y manejo en Steam Deck

La interfaz usa superficies carbón, bordes suavemente redondeados, menos contornos y sombras, y una línea azul para la pestaña activa. El contador de Actualizaciones tiene texto blanco sobre azul tanto con la pestaña activa como inactiva.

El buscador indica **X: teclado**. X / □, el icono de teclado o A sobre un campo de texto abren el teclado de Steam. Los campos inhiben su apertura automática al recibir el foco; se conserva el teclado físico.

Las vistas admiten desplazamiento táctil y arrastre cuando Steam presenta el toque como un ratón. Al navegar con el mando, la tarjeta completa y su título se mantienen dentro de la vista, también en la última fila.

Los cambios guardados, ajustes aplicados, actualizaciones y errores muestran un aviso grande dentro de la app durante ocho segundos, con un botón para cerrarlo. Los estados de descarga siguen mostrando el progreso en su lugar. No se crean ventanas separadas.

Los perfiles integrados se identifican como **Integrado en Deck Library**. La marca **Verificado · usuario** corresponde a ajustes confirmados jugando; **Verificado · arranque** indica una prueba limitada al inicio. Las variantes sin prueba permanecen **Sin verificar**. En Mario Kart Wii, Calidad conserva el perfil confirmado y se selecciona de forma predeterminada; Equilibrado y Rendimiento son variantes de menor resolución pendientes de prueba.

**Ajustes de la comunidad** aparece como sección propia con una vista previa de perfiles, valoraciones y acceso a comentarios. Los perfiles adicionales están en **Otros perfiles**, visibles sin desplegar un acordeón. Los perfiles locales y las pruebas del autor no heredan la verificación de los integrados.

### Instalación y actualización de ports

La ficha del catálogo muestra qué paquete se instalará. Se admiten AppImage, binarios y archivos comprimidos de Linux; también ports portables de Windows mediante Proton. Los instaladores que necesitan convertir un disco o compilar una ROM usan una integración específica. Los proyectos sin un paquete compatible lo indican al consultar sus detalles.

Project 2099 instala la última versión oficial. Beta 5 usa un motor nuevo y un acceso distinto: Deck Library los reconoce y conserva la versión anterior como respaldo. El instalador tiene su propio entorno de Proton, progreso por archivos escritos, cancelación y detección de bloqueos. Los perfiles verificados de Beta 4.1 no se aplican a Beta 5.

### Correcciones de modo Juego

El mando usa el foco de Gamescope en modo Juego, para mantener la navegación aunque GTK pierda su indicador de ventana activa. Se suspende la entrada al pasar al menú de Steam u otra app. Los cambios de pantalla del catálogo y la biblioteca son directos en sesiones de Steam, para evitar bloqueos de dibujo de GTK. Se conservan las animaciones de los controles. Project 2099 Beta 5 arranca directamente desde su acceso de Steam, sin pasar por el lanzador de Windows.

### Mando dentro de las fichas y Project 2099

Se corrigió un bloqueo del lector del mando al abrir fichas de ports y otras tareas internas. B/○ sigue leyéndose mientras la ficha está abierta. El acceso de Project 2099 ejecuta el motor desde su propia carpeta y prefiere Proton 9 para el juego si está instalado; el instalador y el lanzador oficial conservan Proton actual. Falta confirmar ambos cambios en modo Juego.

### Más fuentes de ports

PortIntegration se suma al catálogo con nombres, plataformas, repositorios y carátulas. Puede elegirse en el filtro de fuentes. Los repositorios repetidos se unifican y mantienen sus fuentes visibles. Los estados de ese sitio se muestran como declaraciones de la fuente; no son perfiles verificados ni pruebas de funcionamiento en Steam Deck. Las descargas se siguen consultando en el proyecto original.

## Instalar, desinstalar y revisión

- **Varios juegos por release:** si un proyecto publica un AppImage por juego, la app instala todos y cada uno aparece en la biblioteca con su nombre. Hoy lo usa OpenRA (Red Alert, Tiberian Dawn y Dune 2000). Quien ya tenía OpenRA con un solo juego ve **Instalar todos los juegos** en el catálogo.
- **Desinstalar:** el catálogo y la ficha de cada port instalado tienen **Desinstalar**. La carpeta se mueve a `~/ports/.deck-library-removed` (las partidas guardadas dentro van con ella y pueden recuperarse de ahí; no se borra nada), el juego sale de la biblioteca y, si estaba en Steam, se quita su acceso con su carátula y su layout de mando.
- **Revisión:** cada tarjeta del catálogo indica **Revisado** (recomendaciones propias y proyectos con receta revisada) o **Sin revisar** (listas externas). La primera instalación de un port sin revisar pide confirmación una sola vez.
- **Archivos anidados y varias herramientas:** un ZIP que solo envuelve un tar.gz se abre, y cuando un paquete trae varias herramientas se elige el lanzador del proyecto.
- Las condiciones de la 1.0 y su estado están en [docs/V1-CHECKLIST.md](docs/V1-CHECKLIST.md).

## Cuenta, actualizaciones y arte de Steam

- **Cuenta:** mientras no haya sesión, la barra superior muestra **Registrarse o iniciar sesión** y la ficha de cada juego repite el botón junto a «Compartir mis ajustes». Con sesión iniciada, la barra muestra el nombre de usuario. La sesión se guarda en `~/.local/share/deck-library/community-session.json` (permisos 0600) y se mantiene al cerrar y abrir la app, hasta que se cierra sesión o el servicio la rechaza.
- **Ajustes de la comunidad:** la ficha muestra arriba los tres perfiles estándar de Deck Library, con su marca de verificado cuando corresponde. La sección comunitaria lista solo perfiles que subió la gente; los perfiles que Deck Library ya incluye no se repiten ahí. «Otros perfiles» queda para los importados o guardados por el usuario.
- **Actualizaciones:** cada port muestra las primeras líneas de sus notas y **Novedades** se abre con el mando (las secciones plegables ahora se enfocan y se abren con A; también **Opciones de actualización** y el proveedor de carátulas).
- **Etiquetas flotantes:** con mando (modo Juego) los textos de ayuda emergentes se desactivan, porque sin ratón quedaban pegados sobre la ficha que se abría debajo del puntero; con ratón, el nombre completo de un juego solo aparece cuando el título está recortado.
- **Abrir un juego:** ya no aparece un aviso encima de la ficha; el botón dice «Abriendo…» y el pie de pantalla nombra el juego. Un juego que está en Steam se abre a través de Steam, que puede mostrar su propio aviso «Starting game» mientras arranca.
- **Icono y arte de Steam:** Deck Library trae icono nuevo y arte propio (portada vertical, banner, fondo y logotipo) para su acceso de Steam; se aplica al agregarlo y, en modo Escritorio, al acceso existente, y solo rellena los espacios vacíos: una imagen elegida por el usuario nunca se reemplaza. `tools/render_art.py` redibuja todo.

## Idioma

La interfaz está en español e inglés. Se cambia en **Ajustes → Carátulas y apariencia → Idioma · Language** (Automático, Español o English) y hay que reabrir la app. Una instalación existente conserva su idioma actual; una nueva sigue el idioma del sistema. `DECK_LIBRARY_LANG=en` o `es` anula la elección guardada durante una ejecución. Cada texto de la interfaz tiene su traducción al inglés y una prueba falla si se agrega uno sin ella.
<!-- END SPANISH -->
