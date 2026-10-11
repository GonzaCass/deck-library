# Validation — 2026-10-01

## DMC3 Crimson local launch notes

The existing Crimson 0.5a installation was launched through Steam Desktop with a direct DMC3 wrapper and an isolated compatible Steam API DLL. Process module inspection and the visible Crimson welcome confirmed boot. The collection's original Steam API DLL was preserved. Gameplay, sustained FPS and Gaming Mode remain untested after this change. This is documented in [DMC3-CRIMSON.md](DMC3-CRIMSON.md); no automatic Crimson installer was added to Deck Library.

Deck Library 0.3.3 was validated on Steam Deck OLED / SteamOS with Python 3.11+ and GTK 3. Public artifacts exclude personal libraries, account details, ROMs, keys, mods and game screenshots.

## 0.3.3 GTA IV recipe

51 automated tests passed, including five new GTA IV tests: complete apply/restore with preserved graphics/FPS settings, only the VSync preference changed in the binary settings file, removal and restoration of newer-only mod files, rollback after an injected write failure, hash/version/busy/symlink rejection, conflict protection after settings change, and microSD discovery without adding a duplicate Steam shortcut.

A GTK dialog smoke check exercised Apply/Restore buttons and asynchronous completion messages with mocked operations and a temporary store. The game was not opened or modified during application development. Steam installation/prefix detection found the real local GTA IV installation. The successful gameplay report belongs to the user's earlier FusionFix 4.0.5 test, not a new FPS benchmark. See [GTAIV.md](GTAIV.md).

## Automated checks

46 tests cover Steam binary round trips and preservation, backups, concurrent writes and Steam-running refusal; discovery and stable shortcut identities; Prism instance IDs; preset validation, compatibility, backups and guarded restoration; portable exports and feedback; NSP hash and bounds verification; mod archive safety; cancellation of owned build processes; and artwork provider matching, HTTPS/image validation, private cache origin metadata and fallback behavior. Tests use temporary directories. Python modules compile successfully.

## Interface and installation

The redesigned first-run wizard was exercised through all four steps with an isolated library: asynchronous detection, selection, provider preferences, persisted completion and library handoff. Portrait/list views, selection controls, game details and settings opened at 1200×740. No Steam changes or game launches were performed by these interface checks. Existing launcher/game settings were retained.

Live Wikipedia downloads succeeded for Mario Kart Wii, Mario Kart 8 and Smash. Libretro Wii artwork lookup and download were also checked. SteamGridDB behavior is covered with mocked responses/fallback tests; live authenticated access is pending a user's API key. Wikipedia may return representative artwork rather than an edition-specific box. Public screenshots contain fictional games and original placeholder designs only.

Discovery found 19 entries, including four Prism instances. Covers are the default view, with a list alternative and local artwork selection. The installations, content, presets, Minecraft layout and Wii preparation dialogs opened within the Deck display dimensions. The public screenshot uses fictional entries. Installation preserves private library data and installs bundled presets and documentation.

## Launch checks

| Game | Result | Gaming Mode |
| --- | --- | --- |
| Existing Mario Kart Wii / WiiCompiled | User confirmed sharp image and excellent gameplay; existing installation preserved | User confirmed working |
| Mario Kart 8 Deluxe / Eden, CTGP Deluxe | Actual Steam Desktop shortcut reached CTGP title after update 3.0.3 and DLC registration | Pending user test |
| Fresh WiiCompiled wizard installation | Official PAL setup completed, control patch rebuilt, sharp preset applied; managed launch reached title | Pending user test |

Automated launch checks lasted about 15 seconds and are boot checks, not sustained FPS benchmarks. The fresh wizard used an already installed KDE SDK 6.11; dependency installation on a new Deck remains untested.

The MK8 NAND content directory was empty: updates were visible only through Eden's asynchronous game-list scan. A direct CLI launch could start before that scan populated update content, while selecting the game in Eden worked. Registering the user's hash-verified update and DLC NCAs in the configured NAND allowed the direct Steam Desktop launch to reach CTGP. Original files, saves and mods were retained. Gaming Mode remains unverified.

Managed Eden launches suppress the bundled AppImage updater dialog using its supported DISABLE_AUTO_UPDATES environment flag. The existing Wii configuration remains at 1.5x Vulkan; the new wizard applies the corresponding preset and Escape/F12 control patch only to its own installation.

## Sharing and limits

Presets are data-only JSON with explicit adapter allowlists. Imports, exports, local feedback and a manually configured HTTPS GitHub catalog are supported. No server, database, publishing or automatic upload is implemented. Controller layouts are recommendations with a Steam controls link, not automatically installed bindings. Switch base/update versions are shown when identifiable; unknown versions require checking Eden. Keys and firmware are provided by the user through the emulator. Other emulator integrations, all Minecraft instances and every proposed game preset have not been gameplay-tested. Proposed presets are labeled accordingly; no universal FPS guarantee is made.

## 0.3.2 interface checks

Onboarding discovery starts with no selected games. Completing it without checking a game opens the library outside selection mode. Explicit selection remains available. The interface walkthrough checked both states. Game actions use distinct colors and explicit labels. Decorative slogans were removed, Spanish labels reviewed and question punctuation corrected.

## 0.3.2 Steam integration

46 automated tests pass, including preservation of imported shortcut IDs/options/tags/control flags, linking an existing Prism instance without duplication, grid replacement backups and Steam-running refusal, repeated Steam Input bindings and custom/fresh Quiver discovery. Local Steam inspection found the Omnicraft Neptune profile with 29 bindings; reading it did not modify its configset. The presets dialog and existing tools were smoke-tested at Deck-compatible sizes. Live Steam artwork writes and shortcut edits were tested against temporary VDF/grid fixtures; actual account writes are deferred until Steam is closed.

## 0.3.4 Project-2099

55 core tests passed. New checks cover PS3 ISO/ZIP rejection before downloads or destination writes, Xbox volume prechecks, preservation/export/restore of root TOML including nested unrelated keys, and discovery of complete installations only. The supplied PS3 image was rejected by the official Beta 4.1 installer under Proton 11.0. No game installation or FPS benchmark succeeded with that source; the Xbox 360 replacement is pending.

## Project-2099 — 2026-10-02

56 core tests passed, including native 7z metadata/single-ISO checks and PS3 rejection before downloads. The GTK installer dialog was constructed with installation actions mocked. The Xbox 360 7z extracted with CRC verification; official Beta 4.1 identified usa-europe-retail-r2, verified 293 source files and completed both language trees with Spanish selected. The installed runtime `--verify-install` returned 0 under Proton 11.0. The 720p/60 preset is applied but remains a proposal: no gameplay FPS or Gaming Mode validation has been performed. The original 7z was retained and temporary ISO/payload extraction removed.

## 0.4.0

90 core tests pass. New coverage: controller templates (unsigned and signed app IDs, existing choices kept, forced replacement with backup, refusal while Steam runs, cleanup on removal), shortcut removal (renumbering, backup, artwork moved aside, queued execution), pruning of stale Steam links, update checks (version comparison, Quiver `version.txt`, caching, partial failures), verified self-update (checksum mismatch, unsafe paths, missing checksum, plain HTTP refused) and the DuckStation adapter (serial detection, manual profiles, line-preserving INI patching checked against the real `settings.ini`, apply/restore). The GTK pages were rendered with a temporary data directory and the per-game settings dialog read the real DuckStation global values.

Not verified on a live Steam session: removal and controller-layout writes against the real account (Steam was open during development), DualSense behaviour in Edge of Time after the layout is assigned, the self-update against a published release, and DuckStation reading the generated per-game file.

### Catalog and publishing checks

114 core tests pass. The catalog reader was run against Quiver's live lists (229 ports, malformed entries dropped); the asset picker was checked against live releases of 40 of them (Windows-only releases are refused, bare Linux binaries are accepted); a real install of Banjo Recompiled v1.0.2 verified its published SHA-256, extracted, identified the executable and appeared in the library scan. GitHub's anonymous rate limit was reached during testing and now produces a clear message.

### 0.4.1

148 core tests pass. GithubLauncher's list (`SirDiabo/GHLAppList`, MIT launcher; the list repository declares no license, so it is read at run time and not redistributed) is merged with Quiver's into 255 ports; the catalog page was rendered against the live network with icons from the lists and PlayStation box art found through Libretro. A name clash between the catalog helper and the library's `entries` was caught by that run. Both Spider-Man PSX repositories were inspected: each publishes a Linux x64 setup kit; Spider-Man requires SLUS-00875 and a Europe BIOS, Spider-Man 2 requires SLUS-01378 (USA) and an SCPH-1001 BIOS. They were not installed or compiled here: this Deck has no CMake, Ninja or compiler.

### 0.4.2 - ports that compile on the Deck

164 core tests pass. On this Steam Deck (SteamOS, no compiler, empty `/usr/include`) the KDE SDK 6.11 Flatpak provided CMake 4.4, Ninja, GCC 15, Python 3.13 and SDL3/Vulkan/X11/Wayland/ALSA headers. Inside it, the Spider-Man PSX kit (v0.1.1) configured with SDL3 fetched from source and compiled all 580 build steps into a working setup-host executable. The Spider-Man 2 kit (v0.1.0) was installed from its release with the published SHA-256 verified, started through the wrapper command that Deck Library generates, opened its launcher window and opened the Steam Deck controller. The flatpak sandbox has no network unless `--share=network` is given and mounts only the home folder, both of which the wrapper accounts for.

Not verified: generating and compiling a game from a disc. Both kits require a USA dump (SLUS-00875, SLUS-01378 Rev 1) and the local library only holds Spain and Europe copies, so the disc check, code generation and gameplay were not run, and nothing is claimed about performance.

### 0.4.3

178 core tests pass. On this Deck the kit cards found `scph5502.bin` (SHA-256 1faaa18f...) and `scph1001.bin` (71af94d1...) in the EmuDeck BIOS folder, which are the exact hashes the Spider-Man and Spider-Man 2 kits require. The PlayStation library holds `Spider-Man (Spain)` and `Spider-Man 2 - Enter - Electro (Europe)`; the kits pin the USA executables and Redump hashes (SLUS-00875, SLUS-01378 Rev 1), so those discs are reported as the wrong region. The kit's own verify-disc hashes the CHD container, so it cannot identify a CHD; the region conclusion rests on the release names and on the pinned identities.
