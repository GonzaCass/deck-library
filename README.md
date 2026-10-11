# Deck Library

Native Linux app that gathers ports, applications and emulated games in one library and manages their Steam shortcuts, per-game settings and controller layouts on Steam Deck. The interface is in Spanish.

[Guía en español para instalar y compartir](LEEME.md)

![Deck Library with a fictional demo library](assets/screenshot.png)

## Install

In Steam Deck Desktop Mode, extract the archive and double-click **Instalar.sh**, choosing **Run / Ejecutar**. This installs the app and opens it. Alternatively, open a terminal in the extracted folder:

```sh
python3 install.py --desktop
```

Open **Deck Library** from the applications menu or desktop shortcut. No sudo, ROM downloads, emulator installation or SteamOS filesystem changes. The app installs in `~/Applications/DeckLibrary` and keeps private data separately in `~/.local/share/deck-library`.

Requires Python 3.11+, PyGObject and GTK 3 (available on the Steam Deck used for validation). On other distributions install their `python3-gi`/GTK 3 packages. The core and its tests use only Python's standard library; no pip packages or network service needed.

## Use

The first launch opens a four-step Spanish onboarding flow: welcome, installation/game detection, artwork provider and library handoff. Discovery runs in the background. Users can add a missing folder or configure an emulator instead of guessing where to start. Repeat onboarding from **Ajustes**.

The default library uses 2:3 portrait cards, platform filters and search. Click a card for a focused game page with **Jugar** and **Agregar a Steam**. Presets, Switch content and Minecraft controls appear as contextual actions; paths and commands are under advanced options. **Seleccionar** reveals batch controls only when needed. **Agregar juegos** offers discovery, manual addition and the Wii preparation wizard.

If Steam is open, the user can restart it after closing any running game, or save later after exiting Steam. Existing shortcut preservation and deferred writes are unchanged. Desktop/Gaming Mode launch verification remains separate.

### Artwork providers and motion

Automatic artwork uses a personal SteamGridDB API key when configured, then Libretro for supported retro systems and Wikipedia PageImages as a fallback. No account is required for the fallback providers. Only exact normalized matches or explicitly documented edition aliases are auto-selected. A game page offers online search, result selection, a source link and a local file alternative. Wikipedia images may represent a shared article rather than the exact edition's box. SteamGridDB requests static 600x900 community grids; a valid personal API key is required.

All image requests run off the GTK thread and download into private local storage. Remote responses and image sizes are bounded. Failed lookups leave readable placeholder cards. API keys, downloaded images and personal libraries are excluded from public releases and preset/feedback exports. Only game names are sent to artwork search providers. Offline use remains available with cached artwork. Transitions between pages and onboarding steps, card hover feedback and loading spinners can be disabled through the animation preference.

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

The recommended Spider-Man entries (`alexbeavs-ps1-ports/spider-man-recomp`, `spider-man-2-enter-electro-recomp`) are setup kits: the user supplies a USA disc (SLUS-00875 and SLUS-01378 Rev 1) and a BIOS, and the kit generates and compiles the game on first start. SteamOS ships no compiler or headers, so these ports run inside the **KDE SDK 6.11 Flatpak** (CMake, Ninja, GCC, Python 3, SDL3/Vulkan/X11/Wayland/ALSA headers). Deck Library asks before installing it once for the user from Flathub (no root, no change to SteamOS), detects kits after installation (`CMakeLists.txt` next to `README-SETUP.txt`) and starts them through `flatpak run --devel` with network, display, audio, input devices and the home folder. A missing SDK is reported as a blocking diagnostic. Installed kits must live under the home folder, which is the only user data the sandbox mounts. Each kit card also compares its requirements with what is already on the Deck: the BIOS is searched by exact SHA-256 in the EmuDeck `bios` folder whatever the file is called, and the disc is checked by Redump-style name against the PlayStation library (a name check only; the kit's wizard verifies the exact dump hash). The kits are pinned to the USA executables, so a PAL disc cannot be used without a separate port.

### Per-game settings

**Ajustes del juego** edits the allowlisted options of an emulator for one game: resolution, anti-aliasing, texture filtering, PGXP and other fixes, FPS limit, overclock and disc speed-up for DuckStation (`gamesettings/<SERIAL>.ini`); internal resolution and EFB options for Dolphin; Eden and Prism options use the same form. Controls start from the effective value (the game file, else the emulator-wide setting), only changed options are written, and every save keeps a backup that **Restaurar anteriores** reverts. Files are patched line by line, so repeated keys, patches and cheats stay as they were. The DuckStation serial is read from `SYSTEM.CNF` in BIN/ISO/CUE images; for CHD it must be entered in the game's identifier field. DuckStation per-game patches and cheats are not editable yet.

## Steam data and backups

Only the selected Steam account is edited. Existing games, app IDs, tags, artwork and unrelated fields are preserved. Matching legacy shortcuts are updated; repeat additions do not create duplicates. A binary KeyValues parser validates the file before any writes. Each changed library gets a timestamped backup beside `shortcuts.vdf`; writes are atomic and refused while Steam is running or a concurrent edit is detected.

Queued changes and logs stay private. A user service performs deferred writes where systemd is available; outside Steam a detached worker is the fallback. If launched inside Steam and neither service nor worker can detach safely, exit Steam and run `./launch.sh sync --no-wait` from Desktop Mode to finish the saved queue.

## Local / GitHub community presets

GTA IV Complete Edition installations in Steam also expose **Arreglo de GTA IV**: a pinned FusionFix 4.0.5/DXVK recipe with SHA-256 verification, complete backups and restore. It keeps the game closed and preserves existing graphics/FPS choices. One Steam Deck OLED user confirmed the resulting experience; sustained FPS were not measured. See [the GTA IV instructions and button API](docs/GTAIV.md).

The [DMC3 Crimson Steam launch notes](docs/DMC3-CRIMSON.md) document a separate, locally boot-tested wrapper and Steam API compatibility fix. This is an integration guide; Crimson installation is not yet a button in Deck Library.

The [Spider-Man: Shattered Dimensions Steam Deck notes](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) record the user-confirmed Windows/Proton setup for audio, voices and controls. It is a guide until Deck Library supports Windows/Proton presets.

Game details expose recommended profiles, a change preview, apply/backup/restore, allowlisted export, JSON import and local feedback export. A user-provided HTTPS raw GitHub catalog can be downloaded without write credentials. No server, database or automatic upload is deployed. See [the portable preset format](docs/PRESETS.md).

The initial catalog includes WiiCompiled, Eden profiles for Smash, Mario Kart 8 and three Mario Party games, plus a Prism instance preset with Steam Input recommendations. Profiles explicitly distinguish proposals, boot checks and user confirmations; hardware/version matching does not imply universal FPS or compatibility.

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

Version **0.4.0**, early release. Core tests cover binary Steam preservation, malformed/concurrent writes, command quoting, discovery, launch errors and mod isolation. Desktop and Gaming Mode require separate integration validation; test results are recorded in `docs/VALIDATION.md`. Source and downloadable releases: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library).

## Referencias

[WiiCompiled](https://github.com/patchzyy/Wiicompiled), [Eden](https://git.eden-emu.dev/eden-emu/eden), [Flatpak launch/extension implementation](https://github.com/flatpak/flatpak/blob/main/common/flatpak-run.c). This project is independent of Valve, EmuDeck, Quiver and those emulators.

## Project-2099

**Agregar juegos → Preparar Project-2099** prepares a supplied Xbox 360 ISO (or a ZIP/7z containing one) using the pinned official Beta 4.1 installer under Proton. PS3 images are rejected before downloads. Includes a proposed 720p / 60 FPS profile, Steam shortcuts and installed-port discovery. Gameplay validation remains pending. [Guía en español](docs/PROJECT2099.md).
