# Deck Library

Native Linux app that gathers ports, applications and emulated games in one library and manages their Steam shortcuts, per-game settings and controller layouts on Steam Deck. The interface is in Spanish.

[Spanish guide: installing and sharing](LEEME.md)

![Deck Library with a fictional demo library](assets/screenshot.png)

![Game overview with fictional artwork](assets/screenshot-game.png)

## Install

In Steam Deck Desktop Mode, extract the archive and double-click **Instalar.sh**, choosing **Run / Ejecutar**. This installs the app and opens it. Alternatively, open a terminal in the extracted folder:

```sh
python3 install.py --desktop
```

Open **Deck Library** from the applications menu or desktop shortcut. No sudo, ROM downloads, emulator installation or SteamOS filesystem changes. The app installs in `~/Applications/DeckLibrary` and keeps private data separately in `~/.local/share/deck-library`.

Requires Python 3.11+, PyGObject and GTK 3 (available on the Steam Deck used for validation). On other distributions install their `python3-gi`/GTK 3 packages. The core and its tests use only Python's standard library; no pip packages or network service needed.

## Open Deck Library directly from Steam

1. Install and open Deck Library in Desktop Mode. Finish the first-run assistant.
2. Open **Ajustes → Deck Library en Steam → Agregar a Steam**.
3. If Steam is open, the app shows a persistent pending-changes banner. Finish your other changes, exit Steam once and wait for the banner to disappear. The background worker saves the shortcut and its Deck controls; no per-change restart dialog is shown.
4. Return to Gaming Mode, find **Deck Library** in Steam's library and press **Play**. The shortcut launches the native Linux app fullscreen, with `--gaming` and its navigation template.

Use the right trackpad and right trigger for pointer/click, the D-pad or stick for navigation, **A** to activate, **B** to go back and **LB/RB** to change sections (**X** focuses search with native controller input). **Steam + X** opens Steam's on-screen keyboard. Physical controller validation in Gaming Mode is still pending; automated tests cover the shortcut, template and 1280×800 interface.

### Add individual games to Steam

Open a game's cover and click the blue **Agregar a Steam** button. It changes to **Acceso pendiente** while queued and **En Steam** after the shortcut is saved. Add several by clicking **Seleccionar**, marking covers and using the batch action. Save the queue by exiting Steam once after finishing, then reopen Steam or return to Gaming Mode. Each game gets its own shortcut and can be launched directly from Steam; opening Deck Library first is optional. The game files stay in their current locations.

For a game already in Steam, **Jugar** uses its existing Steam shortcut and controller identity. **Más opciones → Archivos y acceso de Steam** provides editing, artwork and removal tools.

## Use

The first launch opens a four-step Spanish onboarding flow: welcome, installation/game detection, artwork provider and library handoff. Discovery runs in the background. Users can add a missing folder or configure an emulator instead of guessing where to start. Repeat onboarding from **Ajustes**.

The library fills the window, with top navigation, 2:3 portrait cards, platform filters and search. Open a cover for the game overview: **Jugar** (green), **Agregar a Steam** (blue), selectable settings cards and a fixed **Aplicar ajustes** action. Selecting a card only previews the profile; changes are written, with a backup, after applying. Technical differences expand under **Ver cambios**. **Controles**, **Contenido** and **Ajustes manuales** open dedicated task pages with a return button. **Más opciones** contains import/export, artwork and shortcut tools. **Seleccionar** reveals batch controls only when needed. **Catálogo de ports** opens the downloadable port catalog directly. Use **Ajustes → Instalaciones y carpetas** to add discovery folders.

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

## 0.4.0

### Remove Steam shortcuts

**Quitar de Steam** is on each game page and in the selection bar. It deletes the shortcut from `shortcuts.vdf`, moves its grid images to `grid/.deck-library-backups`, forgets its controller layouts and renumbers the remaining shortcuts. Games, files and saves are not touched, and a timestamped backup of `shortcuts.vdf` is written first. Like additions, removals are queued while Steam is open and applied once it is closed. Shortcuts that disappear from Steam are also dropped from the library on the next scan.

### Controller layouts (DualSense and others)

Steam keeps the Steam Input layout of a non-Steam shortcut in one `configset_controller_<family>.vdf` per controller family. A shortcut that only has an entry for the Deck itself gets a desktop/browser layout when a DualSense, DualShock, Xbox or Switch Pro pad is connected, so the game sees no XInput device. New shortcuts now receive the gamepad template for every family that has none; existing choices are kept. **Mando → Asignar layout** on a game page replaces the saved layout for that shortcut (a backup of each changed file is kept). Writes need Steam closed. This can be disabled with `fix_controllers` in `settings.json`.

### Updates

The **Actualizaciones** page checks, at most every six hours: Deck Library releases on GitHub, the preset catalog, ports installed through Quiver (`version.txt` against the latest release of their repository) and Project-2099. Everything uses HTTPS with size limits. Deck Library can install its own update: the release must include `DeckLibrary-X.Y.Z.tar.gz` and its `.sha256`; the archive is verified, extracted with path checks and installed with `install.py`. Automatic installation of Deck Library updates is on by default and can be switched off on the page; it only runs in Desktop Mode and asks for a restart. Ports installed from the catalog can also update automatically (off by default). Ports installed by Quiver are only reported; Quiver applies them. GitHub allows 60 anonymous API requests per hour; set `GITHUB_TOKEN` to raise the limit. The catalog defaults to `presets/catalog.json` in this repository.

### Port catalog

**Catálogo de ports** merges four sources: Quiver's public lists (`tgeorgiadis/quiver-community-app-catalog`), GithubLauncher's list (`SirDiabo/GHLAppList`, which includes Rexglue/Xbox 360 and system emulators and marks AI-assisted projects), a few built-in recommendations and the user's own repositories (about 255 ports). Both launchers use the same data model, so ports installed by either one (`apps.json`, `Apps/`, `version.txt`, `selected_executable.txt`) are found in any folder under `~/ports` or `~/Applications` and checked for updates. Each entry shows its icon, or box art found by platform, plus category, source and notes; the list can be filtered by category and source.

**Agregar repositorio** accepts any GitHub address or `owner/repo`, checks its latest release for a Linux build and keeps it in `custom_ports` of `settings.json`. Extra list files can be added with `catalog_sources` (raw.githubusercontent.com URLs in Quiver's or GithubLauncher's format).

**Instalar** downloads the latest release asset for Linux x86_64 (AppImage, tar.gz/tar.xz, zip or a bare executable), checks the SHA-256 that GitHub publishes for the asset, extracts it with path and link checks into `~/ports/<folder>` and registers the version, so the library lists it and the updates page can detect new releases. Releases that only ship Windows builds are refused with a message. When several executables are possible none is chosen and the game can be added by hand. Updating moves the previous folder to `~/ports/.deck-library-replaced` instead of deleting it.

The recommended Spider-Man entries (`alexbeavs-ps1-ports/spider-man-recomp`, `spider-man-2-enter-electro-recomp`) are setup kits: the user supplies a USA disc (SLUS-00875 and SLUS-01378 Rev 1) and a BIOS, and the kit generates and compiles the game on first start. SteamOS ships no compiler or headers, so these ports run inside the **KDE SDK 6.11 Flatpak** (CMake, Ninja, GCC, Python 3, SDL3/Vulkan/X11/Wayland/ALSA headers). Deck Library asks before installing it once for the user from Flathub (no root, no change to SteamOS), detects kits after installation (`CMakeLists.txt` next to `README-SETUP.txt`) and starts them through `flatpak run --devel` with network, display, audio, input devices and the home folder. A missing SDK is reported as a blocking diagnostic. Installed kits must live under the home folder, which is the only user data the sandbox mounts. Each kit card also compares its requirements with what is already on the Deck: the BIOS is searched by exact SHA-256 in the EmuDeck `bios` folder whatever the file is called, and the disc is checked by Redump-style name against the PlayStation library (a name check only; the kit's wizard verifies the exact dump hash). The kits are pinned to the USA executables, so a PAL disc cannot be used without a separate port. Once a kit has been generated and compiled (its wizard, or `psxrecomp_cli.py generate` and `rebuild` inside the SDK), the library entry points to the built game and keeps the same id.

### Automatic port setup

Everything needed to make a port playable is scripted and starts from **Configurar** in the catalog (it also runs right after **Instalar**). Deck Library finds the disc in the library by the serial inside its `SYSTEM.CNF` (BIN, ISO or CUE; the file name does not matter) and the BIOS by exact SHA-256 in the EmuDeck folder, shows what it found and asks before doing anything:

- **Recompilation kits** (Spider-Man, Spider-Man 2): `verify-disc`, `generate` and `rebuild` of the kit's own CLI inside the KDE SDK Flatpak, then the BIOS choice is stored in `build/bios.cfg`. The entry then starts the built game.
- **OpenPete** (Spyro the Dragon, downloaded from openpete.com and checked against the SHA-256 the site publishes): the AppImage is unpacked once, its game module is pre-built from the disc inside the SDK and the entry starts it in fullscreen with `--disc`.
- **CTR Turbocharged** (ctr.cmzi.uk; the site publishes no hash, only a size, which is checked): the raw MODE2/2352 BIN is copied as `ctr-u.bin` to `~/.local/share/ctr-turbocharged/assets`. On first start the game asks for an optional font (choose *Use Luckiest Guy*) and a graphics preset.

Ports published on their own site are found by reading its page (`resolve_web`); downloads are limited to the hosts `dl.openpete.com` and `ctr.cmzi.uk`, and updates are detected by comparing the published version.

### Zelda ports

Three more built-in entries use the same **Configurar** flow:

- **Minish Cap** (Project Picori, `999sian/tmc`): the GBA ROM is found by SHA-1 in `~/Emulation/roms/gba` whatever its file name (USA, Europe or Japan) and copied next to the binary as `baserom.gba`, `baserom_eu.gba` or `baserom_jp.gba`. The European ROM carries Spanish text.
- **A Link to the Past** (`snesrev/zelda3`, pinned commit, built from source): the USA 1.0 ROM is found by SHA-1 in `~/Emulation/roms/snes` (a 512-byte copier header is stripped), Pillow and PyYAML are installed into a local folder, `make` runs inside the KDE SDK and the executable starts there with `SDL_AUDIODRIVER=pulseaudio` (SDL otherwise tries JACK first inside the sandbox and gives up). The aspect ratio is set to 16:10. The game was never released in Spanish.
- **Wind Waker HD** (`ZeldaWWHDRecomp/ZeldaWWHDRecomp`, AppImage verified against the release's SHA-256): the Wii U disc (`.wux`, `.wud` or Cemu `.wua`) is taken from the library. For `.wux`/`.wud` the disc key (matched by the `[USA, WUD]`/`[EUR, WUD]` comment) and the Wii U common key come from Cemu's `keys.txt` in EmuDeck's `bios` folder, are written to private (0600) files in a temporary folder only while the port's own setup runs, and are deleted afterwards; they are never logged or stored. The USA disc includes Spanish.

**Settings → Apply maximum settings for Steam Deck** is the app's one-click maximum-quality profile. It raises DuckStation (5x, PGXP), Dolphin (3x, 16x anisotropic), Azahar (3x, large screen with the small one visible, swap on L4/R4, async shaders) and Eden (async shaders, 16x anisotropic) to what the 1280x800 screen supports, keeping a backup of every file and skipping a running emulator.

Per-game defaults: Eden's Breath of the Wild gets Latin American Spanish, 1x resolution with FSR and normal GPU accuracy; Azahar gets Spanish console language, 3x, large-screen layout (both screens visible) and an app-owned Steam Input layout where L4 sends F9 (swap screens) and R4 F10 (layout) for 3DS shortcuts; Wind Waker HD runs with `WWHD_` environment options (Spanish, 16:10, picture-in-picture GamePad, interpolation, FXAA); Picori with the European ROM uses Spanish and 5x internal scale; the PS1 kits get 4x supersampling, PGXP and the kit's own PGXP / fast-loading / CD-speed mods (the kits' runtime has no frame interpolation or widescreen).

A Link to the Past in Spanish: `deck_library.patching.apply_ups` applies the fan translation's UPS patch (all three CRC32s verified); the result is recognised by SHA-1, built with `restool.py --extract-dialogue` / `--languages=es` and selected with `Language = es`. For the PS1 kits, `psx.deck.display` is a built-in plugin package (framework plugin API: `psx_mod_set_frame_interpolation(0)` with motion-adaptive blending, `psx_mod_set_fixed_display_aspect(16, 10)`) added to the kit's `runtime.cmake` with a backup; it needs the kit to be rebuilt.

Steam artwork: the game detail page has **Arte de Steam**, backed by `deck_library.steamart` (SteamGridDB API, vertical and horizontal covers, hero, logo with its position JSON, and icon, in the file layout Decky's SteamGridDB plugin writes). Existing files are kept unless a slot is explicitly replaced, replaced files are backed up, images are validated by magic bytes (PNG/JPEG/WebP, 20 MB limit) and written through the same Steam-closed queue as shortcuts. **Settings → Completar arte de todos los accesos de Steam** (`steamart.complete_missing`) fills only empty slots for every shortcut and reports per game. The app needs the user's own SteamGridDB key; the key embedded in Decky's plugin is reserved for it by its author.

UI: top navigation, portrait game cards, distinct action colours, visible focus and finite transitions (`deck_library/motion.py`: fades, staggered card entrance, slide between library and detail, toasts), all disabled by the animations switch. The per-game settings dialog starts with the emulator's current values read from its own files. `deck_library/wiiupdate.py` updates a Quiver-managed WiiCompiled in place (SHA-256 from the GitHub digest, `install --game`, rollback of the previous setup tool).

A per-game guide (requirements, what the app sets, limits, how to revert) is in [docs/PORTS.md](docs/PORTS.md) (Spanish). `ports.build_spanish_zelda3` applies a UPS translation patch found in Downloads or the SNES ROM folder when its result has the SHA-1 zelda3 expects.

None of these ports exists for A Link Between Worlds, Breath of the Wild or Skyward Sword; those stay emulated.

### Library view

The toolbar filters by platform and by **type** (ports, emulator games, Minecraft instances, Steam shortcuts, custom). **Preferir ports** (on by default) hides the emulator version of a game that already has a port, by title without edition tags; nothing is deleted. A catalog port keeps a single library entry with a stable id, an imported Steam shortcut that a managed entry owns is not listed twice, and Minecraft instances are matched with their shortcut by name.

### Per-game settings

**Ajustes del juego** edits the allowlisted options of an emulator for one game: resolution, anti-aliasing, texture filtering, PGXP and other fixes, FPS limit, overclock and disc speed-up for DuckStation (`gamesettings/<SERIAL>.ini`); internal resolution and EFB options for Dolphin; Eden and Prism options use the same form. Controls start from the effective value (the game file, else the emulator-wide setting), only changed options are written, and every save keeps a backup that **Restaurar anteriores** reverts. Files are patched line by line, so repeated keys, patches and cheats stay as they were. The DuckStation serial is read from `SYSTEM.CNF` in BIN/ISO/CUE images; for CHD it must be entered in the game's identifier field. DuckStation per-game patches and cheats are not editable yet.

## Steam data and backups

Only the selected Steam account is edited. Existing games, app IDs, tags, artwork and unrelated fields are preserved. Matching legacy shortcuts are updated; repeat additions do not create duplicates. A binary KeyValues parser validates the file before any writes. Each changed library gets a timestamped backup beside `shortcuts.vdf`; writes are atomic and refused while Steam is running or a concurrent edit is detected.

Queued changes and logs stay private. A user service performs deferred writes where systemd is available; outside Steam a detached worker is the fallback. If launched inside Steam and neither service nor worker can detach safely, exit Steam and run `./launch.sh sync --no-wait` from Desktop Mode to finish the saved queue.

## Local / GitHub community presets

GTA IV Complete Edition installations in Steam also expose **Arreglo de GTA IV**: a pinned FusionFix 4.0.5/DXVK recipe with SHA-256 verification, complete backups and restore. It keeps the game closed and preserves existing graphics/FPS choices. One Steam Deck OLED user confirmed the resulting experience; sustained FPS were not measured. See [the GTA IV instructions and button API](docs/GTAIV.md).

The [DMC3 Crimson Steam launch notes](docs/DMC3-CRIMSON.md) document a separate, locally boot-tested wrapper and Steam API compatibility fix. This is an integration guide; Crimson installation is not yet a button in Deck Library.

The [Spider-Man: Shattered Dimensions Steam Deck notes](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) record the user-confirmed Windows/Proton setup for audio, voices and controls. It is a guide until Deck Library supports Windows/Proton presets.

Game details expose recommended profiles, a change preview, apply/backup/restore, allowlisted export, JSON import and local feedback export. A user-provided HTTPS raw GitHub catalog can be downloaded without write credentials. An optional self-hosted SQLite service supports own accounts, real star ratings and comments. Sharing a profile is explicit and moderated. See [the portable preset format](docs/PRESETS.md).

The initial catalog includes WiiCompiled, Eden profiles for Smash, Mario Kart 8 and three Mario Party games, plus a Prism instance preset with Steam Input recommendations. Profiles explicitly distinguish proposals, boot checks and user confirmations; hardware/version matching does not imply universal FPS or compatibility.

Switch games without a bundled or imported title-specific profile offer three proposals: **Equilibrado**, **Rendimiento** and **Compatibilidad**. They use the included profiles as references and require a Title ID; declared compatibility is Eden 0.2.1. Choose a card, expand **Ver cambios** if needed and press **Aplicar ajustes**. This saves a backup and writes the profile without opening the game. **Jugar** is a separate action. **Deshacer** restores the configuration before the latest application. Existing title-specific profiles keep priority, and each card displays its author's declared testing status. Performance still needs validation per game.

## Discovery, covers and setup

Portrait covers are the default view; list view is available. Local Steam, Quiver, Eden and Prism images and privately downloaded provider artwork are reused. Custom local covers can be selected. Public release artwork uses fictional placeholders; downloaded game artwork is not shipped.

**Ajustes → Instalaciones y carpetas** reads EmuDeck paths without executing its settings script, offers manual paths and emulator executable selection, and discovers Prism instances by their folder IDs. Microsoft account files are never read or shared.

**Preparar Mario Kart Wii** uses the official pinned setup 0.2.33 and an optional KDE SDK 6.11 sandbox to compile a supplied PAL RMCP01 image in its own private installation. It applies the known source-level F12 exit fix, stabilizes toolkit links, rebuilds and applies the confirmed 1.5× baseline. It needs Internet and around 20 GB of temporary space; progress and cancellation are visible. Other recompilation projects are not automatically supported by this wizard.

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

Version **0.16.0**. Core tests cover binary Steam preservation, malformed/concurrent writes, command quoting, discovery, launch errors and mod isolation. Desktop and Gaming Mode require separate integration validation; test results are recorded in `docs/VALIDATION.md`. Source and downloadable releases: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library).

## Referencias

[WiiCompiled](https://github.com/patchzyy/Wiicompiled), [Eden](https://git.eden-emu.dev/eden-emu/eden), [Flatpak launch/extension implementation](https://github.com/flatpak/flatpak/blob/main/common/flatpak-run.c). This project is independent of Valve, EmuDeck, Quiver and those emulators.

## Project-2099

The Project-2099 adapter prepares a supplied Xbox 360 ISO (or a ZIP/7z containing one) using the pinned official Beta 4.1 installer under Proton. PS3 images are rejected before downloads. Includes a proposed 720p / 60 FPS profile, Steam shortcuts and installed-port discovery. Gameplay validation remains pending. [Guía en español](docs/PROJECT2099.md).

## Community accounts and update progress (0.14)

**Comunidad → Mi cuenta → Crear cuenta / Iniciar sesión** opens the configured Keycloak device authorization page in the browser. The desktop app never asks for the account password. Anonymous browsing works without an account; writing requires a session. **Compartir mis ajustes → Revisar mis ajustes → Publicar perfil** exports only allowlisted values and submits the reviewed profile for moderation. Each user can leave one editable 1–5 star rating and comment per public profile. An unrated proposal is labelled **Sin valoraciones**. The server includes the packaged profiles as proposals, without inventing reviews or performance measurements.

Eden cards offer **Equilibrado**, **Rendimiento** (0.75×) and **Calidad** (1.5×), plus compatibility profiles. Title-specific settings keep their original values in the balanced card. These are proposals, not universal performance guarantees. Known emulator-version checks still apply.

Catalog and update rows show download progress, percentage and estimated time from measured bytes. Compilation shows its current phase without an invented completion percentage. Completed/error state stays in that port's row during the current session. Completed installs invalidate stale update notices. Tab changes reuse the existing library and catalog; native SDL2 input supplements Steam's navigation template in Gaming Mode.

## Port management (0.15)

Discovery identifies installed variants before offering another installation. The library offers reversible hiding or confirmed trashing of original disc images, with shared-file checks. Downloads have inline cancellation/dismissal. The catalog combines the current Quiver API, legacy lists and an independent curated list, tracks real addition/release dates and includes a bundled factual fallback index. Sources: [Quiver API client](https://github.com/tgeorgiadis/quiver-launcher/blob/main/Services/QuiverCatalogClient.cs), [independent list](https://github.com/Sebastrion/awesome-unofficial-pc-ports).

Project-2099 updates download verified installer/payload assets from the official release, install in a temporary folder, preserve UserData and retain the complete old installation. Beta 5 changes engines; old renderer settings and mods stay in that backup. Game shortcut Proton arguments are preserved. The update button does not launch the game. Live Beta 5 gameplay validation is pending; automated tests exercise staging, backup, preservation and failure recovery using a simulated installer.

Included playtested profiles are labelled with their actual test level and take precedence over custom imports in the primary cards. Portrait artwork fills its canvas without side bands.

### Accounts inside the app

Open **Account** (the account icon in the top bar), or **Community → My account** from a game. **Sign in** and **Create account** open Deck Library’s account forms inside the app. Registration requires email verification on the public service. Password recovery is available from the sign-in form. Browsing profiles does not require an account.

Keycloak handles passwords, registration requirements and recovery. Its forms run in a separate, ephemeral WebKit process; the application receives only its own revocable community session. Sessions are checked when opening Account; expired sessions are cleared. Closing the access panel cancels polling and closes the embedded browser.

On Steam Deck the embedded view reuses an installed GNOME Flatpak runtime when available. Otherwise the app offers to install the component from Flathub, or continue in the browser. The app selects X11 when available for GTK embedding; an explicit Wayland override uses the browser fallback. In Gaming Mode, use the D-pad/stick to move, A to select, B to cancel access and **Steam + X** for the keyboard. Physical controller navigation still needs confirmation on the Deck.
