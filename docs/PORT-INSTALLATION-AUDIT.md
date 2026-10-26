# Port installation audit · Auditoría de instalaciones

Snapshot: **2026-10-26 · Deck Library 1.2.5 · 751 catalog entries**.

This checks release metadata and package selection, not gameplay. The catalog also includes tools, launchers and projects for other devices. A Windows package plus Proton is not proof that a game works on Steam Deck. Only the three Naruto packages listed below were downloaded and installed in isolated test directories during this audit. No original game files were available for a gameplay test.

| Release classification | Entries | Meaning |
| --- | ---: | --- |
| Native | 403 | A supported Linux package is published. |
| Proton | 238 | A portable Windows package can use the managed Proton workflow. |
| Inspect archive | 22 | An unlabelled archive must be inspected for ELF/PE executables before choosing a runtime. |
| Specialized | 4 | A dedicated installer, website download or source-build integration applies. |
| No compatible package | 50 | Current assets are for other platforms, installers, patches or unsupported package types. |
| No release | 22 | No published release was found. |
| Unavailable | 11 | GitHub did not expose the repository/releases to the audit session. |
| Manual build | 1 | The reviewed release is a build tool, not a ready-to-run game. |

Full public metadata: [installation-audit.json](../catalog/installation-audit.json). Each entry records its repository, selected tag, assets, runtime and original-data preparation mode. These results are dated; new upstream releases can change them.

Original-data preparation is a separate check: 16 entries have an integrated preparation flow, 11 have a reviewed upstream wizard and 4 have reviewed manual instructions. The other 720 have no reviewed original-data contract in Deck Library; some are tools or games that need no ROM. Their package being downloadable does not mean Deck Library can already import their original files automatically. For those that require game data, follow the port's own wizard or guide until a specific recipe is reviewed.

## Naruto

| Project | Audited release | Integration | Remaining limit |
| --- | --- | --- | --- |
| [The Broken Bond · Auremana666](https://github.com/Auremana666/Naruto-The-Broken-Bond-PC-Port/releases/tag/v2.0) | v2.0 | Proton; choose your Xbox 360 ISO inside Deck Library; copy it to `assets`; preserve `hdd` and `naruto.toml` on update. | The port imports and validates the ISO on launch. [Steam Deck graphics/crash reports remain open](https://github.com/Auremana666/Naruto-The-Broken-Bond-PC-Port/issues/6). |
| [The Broken Bond · jorjbarbosa](https://github.com/jorjbarbosa/broken-bond-recomp/releases/tag/v0.1.0-beta) | v0.1.0-beta | Proton; launch `broken_bond_launcher.exe`; match extracted originals by Title ID and exact SHA-256, then copy to `game`; preserve `user` and `broken_bond.toml`. | The portable ZIP lacks the Windows installer's ISO importer. Choose an extracted folder. Current renderer: Direct3D 12; Deck gameplay unverified. |
| [Rise of a Ninja · jorjbarbosa](https://github.com/jorjbarbosa/naruto-rise-recomp/releases/tag/v0.3.0-beta) | v0.3.0-beta | Proton; launch `narutorise_launcher.exe`; match extracted originals by Title ID; preserve originals, saves, mods and settings. | The author added Vulkan/Wine fixes in 0.3. Earlier builds can show a black screen. Full gameplay not tested here. |

The two Broken Bond integrations are explicitly experimental. Their metadata score is capped at 50 so that reviewing the installation cannot promote them to high gameplay compatibility. v2.0 is the newer published Broken Bond package in this snapshot; release version numbers from different projects do not measure which one performs better.

## Shared fixes

- Recognize a matching launcher/engine pair, selecting its launcher. Unrelated executables remain ambiguous and require a specific integration.
- Support portable Windows tar archives as well as ZIP, 7z, RAR and standalone EXE; recognize MSVC, MinGW, W32 and W64 labels.
- Exclude console, Android, Apple mobile, web and license/notice archives from Proton package selection. Enforce a reviewed asset prefix for Windows too.
- Find installed Proton builds on Steam library drives, including microSD, and use an installed GE-Proton as a fallback. No system Wine installation is needed.
- Keep a persistent Proton prefix per managed port. Updates preserve common `hdd`/`user` save folders and each reviewed port's declared originals and configuration.
- Reapply updated local recipes to cached catalogs immediately after an app upgrade.
- Preparation asks only for a supported input type. Extracted Xbox 360 folders are auto-detected by identity; ambiguous matches require a choice. ISO containers are never auto-identified by filename.

## Pending integrations

The 50 entries without a compatible portable asset are not all failed Linux ports: many only publish Android, macOS, iOS or console builds. Others need a reviewed installer flow, including `xmd-recompiled`, `DimensionsRecomp`, Ace Combat 04, NFL Head Coach 09, FNCReborn and inFAMOUSreborn. Tekken3Recompiled publishes an Easy Setup kit; generic portable installation must not treat that builder as the finished game. Some releases only contain patches or license archives. A missing GitHub repository is also not a Proton compatibility result.

New integrations should declare their executable, original-data contract, runtime and files to preserve, then validate an actual published package and update/rollback behavior. A source-only project needs a build integration; Proton cannot turn its source archive into a game.

## Repeat the audit

From a checkout, with Python 3.11 or later:

```sh
python3 tools/audit_ports.py --refresh --output /tmp/deck-library-port-audit.json
```

With an existing GitHub CLI login, avoiding the small anonymous API quota:

```sh
python3 tools/audit_ports.py --refresh --github-cli --output /tmp/deck-library-port-audit.json
```

For a saved catalog, use `--catalog catalog/ports.json` instead of `--refresh`. This still queries published releases; it never installs or launches them. The output contains public project metadata only, and no tokens or local library/settings paths.

## Resumen en español

Se analizaron 751 entradas: **403 con paquete Linux, 238 con paquete Windows portable para Proton y 22 archivos que requieren inspección**. El resto usa una integración específica, requiere compilación, publica para otro dispositivo o no tiene un release accesible. Esto mide el proceso de instalación, no los FPS ni la posibilidad de completar un juego.

Las dos variantes de The Broken Bond y Rise of a Ninja se instalaron desde sus paquetes reales, verificando SHA-256 y el ejecutable elegido. Se probaron con datos sintéticos la selección del original, la identificación por Title ID/revisión, la conservación de partidas/configuración y la reutilización de una ISO ya copiada después de actualizar. Sin las copias originales, no se comprobó una partida. Las incidencias de renderizado de Broken Bond siguen siendo una limitación del port; agregar Proton no las garantiza resueltas.
