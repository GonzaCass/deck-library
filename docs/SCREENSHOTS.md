# Screenshots — 1.5.0

Captured from Deck Library at 1280×800 with a temporary library, fictional games,
original vector covers and sample update metadata. The DEMO label identifies the
fixtures; the images do not represent gameplay validation or a personal library.

## English

[Home](../assets/screenshots/en/home.png) · [Library](../assets/screenshots/en/library.png) · [Game profiles](../assets/screenshots/en/game.png) · [Updates](../assets/screenshots/en/updates.png) · [Settings](../assets/screenshots/en/settings.png) · [Menu](../assets/screenshots/en/menu.png)

## Español

Capturas de la app a 1280×800 con una biblioteca temporal, juegos ficticios,
carátulas vectoriales originales y datos de actualización de ejemplo. La etiqueta
DEMO identifica esos datos; las imágenes no representan pruebas de juego ni una
biblioteca personal.

[Inicio](../assets/screenshots/es/home.png) · [Biblioteca](../assets/screenshots/es/library.png) · [Perfiles](../assets/screenshots/es/game.png) · [Actualizaciones](../assets/screenshots/es/updates.png) · [Ajustes](../assets/screenshots/es/settings.png) · [Menú](../assets/screenshots/es/menu.png)

## Reproduce

From the repository, with Python, GTK 3/PyGObject and a disposable X11 display:

```sh
xvfb-run -a -s "-screen 0 1280x800x24" python3 tools/preview_console.py dist/screens-en --all-pages --language en
xvfb-run -a -s "-screen 0 1280x800x24" python3 tools/preview_console.py dist/screens-es --all-pages --language es
```

The preview uses a temporary store, mocks installation and launching, and makes no
community requests. The default fixtures need no network or game files. The six
main screens per language are selected from this larger capture set.
