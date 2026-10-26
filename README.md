<h1 align="center">Deck Library</h1>

<p align="center">
  <img src="assets/steam/banner.png" alt="Deck Library" width="720">
</p>

<p align="center">Ports, emulated games and Minecraft instances. One library for Steam Deck.</p>

<p align="center">
  <a href="https://github.com/GonzaCass/deck-library/releases/latest"><img src="https://img.shields.io/github/v/release/GonzaCass/deck-library?style=flat-square&amp;color=7764d8" alt="Latest release"></a>
  <a href="https://github.com/GonzaCass/deck-library/actions/workflows/test.yml"><img src="https://github.com/GonzaCass/deck-library/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-4b9f82?style=flat-square" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://github.com/GonzaCass/deck-library/releases/latest"><strong>Download</strong></a> ·
  <a href="LEEME.md">Español</a> ·
  <a href="docs/README.md">Documentation</a> ·
  <a href="https://github.com/GonzaCass/deck-library/issues">Report an issue</a>
</p>

## 🎮 One place for your games

- **Library:** discover EmuDeck games, installed ports and Prism Launcher instances, with portrait covers and platform filters.
- **Ports:** browse, install and update supported projects. Check original-file requirements and choose missing files during setup.
- **Game settings:** compare compact profiles, expand their details and apply changes with a backup.
- **Community:** share per-game settings, ratings and comments from the app.
- **Steam:** add individual games or Deck Library itself, with artwork and controller navigation in Gaming Mode.

![Library with fictional demo games](assets/screenshot.png)

<details>
<summary>See the game settings view</summary>

![Game settings with fictional demo artwork](assets/screenshot-game.png)

</details>

## 🚀 Install

1. Switch the Deck to **Desktop Mode** and download the archive from [the latest release](https://github.com/GonzaCass/deck-library/releases/latest).
2. Extract it, open the folder and double-click **Instalar.sh**. Choose **Run**.
3. Complete the setup assistant and review the detected games.

If the file opens as text, run `python3 install.py --desktop` in that folder. Requires Python 3.11+ and GTK 3/PyGObject. No sudo or pip installation is needed on the validated Steam Deck setup.

## 🕹️ Use it from Steam

1. In Desktop Mode, open Deck Library and click **Add to Steam** beside the top tabs.
2. If Steam is open, changes stay in the pending banner. Exit Steam once to save them.
3. Return to **Gaming Mode**, find **Deck Library** in Steam and press **Play**.

To add a game instead, open its cover and choose **Add to Steam**. Each game can then launch directly from Steam.

**Controls:** left stick/D-pad to move · right stick to scroll · **A** select · **B** back · **LB/RB** tabs · **X** search keyboard. Touch and trackpad remain available.

## 🔄 Already installed?

Open Deck Library in **Desktop Mode → Updates → Check for updates**. Automatic app updates are enabled by default in Desktop Mode; reopen the app after installation. Re-running the latest installer is also supported and keeps the library, profiles and settings.

The app and desktop icon update with the installation. Previous official Steam artwork is refreshed automatically; custom images and pending manual choices stay intact. Steam changes are saved when Steam closes, with backups.

<details>
<summary>Original files, compatibility and accounts</summary>

Ports may require a specific ROM, disc revision, BIOS or extracted game files. The app detects supported originals or asks for their location. It does not include game files.

The compatibility percentage is a metadata-based index, not measured gameplay performance. **Port catalog → Compatibility guide** explains the colors and calculation.

An account is needed to publish or rate community settings. The local library and local profiles can be used without signing in. Some projects still require manual preparation; [requirements and supported routes](docs/PORTS.md) describe those cases.

</details>

## 📖 More

[Documentation](docs/README.md) · [Promo images](https://github.com/GonzaCass/deck-library/tree/main/promo) · [Ports and requirements](docs/PORTS.md) · [Profiles](docs/PRESETS.md) · [Release notes](docs/CHANGELOG.md) · [Validation](docs/VALIDATION.md)

Found a problem? [Open an issue](https://github.com/GonzaCass/deck-library/issues) with the app version, game/port name and diagnostic details. Do not include tokens, keys or game files.

[MIT license](LICENSE). Independent project; not affiliated with Valve or the emulator and port projects it integrates.
