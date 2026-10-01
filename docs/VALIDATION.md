# Validation — 2026-10-01

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
