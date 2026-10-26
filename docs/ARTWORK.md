# Deck Library artwork

The supplied `deck_library_png_pack.zip` provides the app and Steam artwork from version 1.2.2. Selected PNGs are copied without resizing, recoloring or editing their pixels. The dark icon, HD portrait and hero with a built-in logo remain alternatives in the original pack.

| Use | Pack file | App resource |
| --- | --- | --- |
| Window, desktop and Steam icon | `01_icono_app_degradado_512x512.png` | `assets/icon.png`, `assets/steam/icon.png` |
| App header | `03_isotipo_transparente_512x512.png` | `assets/brand.png` |
| Steam logo | `04_logo_transparente_steam_1712x452.png` | `assets/steam/logo.png` |
| Steam portrait | `05_portada_vertical_600x900.png` | `assets/steam/portrait.png` |
| Steam horizontal capsule | `07_portada_horizontal_920x430.png` | `assets/steam/banner.png` |
| Steam hero background | `08_banner_hero_limpio_1920x620.png` | `assets/steam/hero.png` |

The desktop's existing `assets/icon.svg` is a wrapper embedding the original main PNG. This preserves theme lookup and existing desktop shortcuts. Steam uses the clean hero and a separate transparent logo, so text is not duplicated.

To import the pack again, run from a source checkout:

```sh
python3 tools/import_art.py /path/to/deck_library_png_pack.zip
```

The importer checks the selected PNG names and dimensions before copying any files. `tools/render_art.py` is retained as an alias for this importer and no longer redraws the previous icon. No ZIP is required to install or run a release.

Adding Deck Library to Steam fills empty artwork slots. From 1.2.3, the installer and the Desktop Mode app also refresh previous official artwork, recognized by exact SHA-256 hashes from the released artwork history in `assets/steam/previous-defaults.json`. Current images, custom images and pending manual choices are preserved. An absent or invalid history never authorizes replacement. Only managed Deck Library shortcuts are migrated; their launch commands and controls stay untouched. Explicitly selected replacements use the normal artwork queue: they are written with Steam closed and previous files are backed up in the account's `grid/.deck-library-backups` directory. Desktop icon files refresh during installation; an already running app needs reopening to reload its window and header icons.

## Español

La tabla indica qué imagen del pack se usa en cada lugar. Los PNG se conservan sin cambios. El icono principal se aplica a la ventana, el menú de aplicaciones y Steam; el isotipo transparente aparece en la cabecera. Steam combina el fondo limpio y el logotipo transparente separado.

El instalador actualiza el icono del escritorio. Los reemplazos de arte elegidos para Steam se guardan cuando Steam está cerrado, con respaldo de los archivos anteriores. Desde 1.2.3, instalar una actualización o abrir la app en Escritorio también renueva el arte oficial antiguo, reconocido por su SHA-256. Se conservan las imágenes personalizadas y las elecciones manuales pendientes. Solo se cambia el arte de los accesos de Deck Library administrados por la app, con respaldo; no se alteran comandos ni controles.
