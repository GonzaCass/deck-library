# Guía de ports y juegos configurados

Cada port se instala desde **Catálogo → Instalar** y se prepara con **Configurar**. La app busca los archivos necesarios sola (discos, ROMs, BIOS, claves), verifica lo que descarga y deja el acceso listo en Steam, con el layout de mando asignado. Esta guía resume qué necesita cada juego, qué deja ajustado la app y qué límites hay. Ningún archivo de juego, BIOS ni clave se incluye en Deck Library ni se sube a ningún sitio.

Los ajustes de calidad parten de la pantalla de la Deck (1280×800, hasta 90 Hz). Los juegos de 30 FPS no pasan de 30 FPS salvo que el port tenga un modo propio.

## Spider-Man y Spider-Man 2: Enter Electro (PlayStation, recompilados)

- **Hace falta:** el disco USA (SLUS-00875 y SLUS-01378) en formato BIN/ISO/CUE dentro de `~/Emulation/roms/psx`, y la BIOS europea SCPH-5502/5552 en `~/Emulation/bios` (se reconoce por su SHA-256, con cualquier nombre de archivo).
- **Configurar:** verifica el disco, genera el código del juego, lo compila dentro del SDK de KDE (varios minutos) y deja el juego en `~/ports/SpiderManPSX` y `~/ports/SpiderMan2PSX`.
- **Queda ajustado:** primer mando automático, supersampling 4×, corrección PGXP de geometría y texturas, y los mods oficiales del kit (PGXP, carga rápida y unidad de CD 2×).
- **Mejorar rendimiento** (botón de la tarjeta, solo si hay una versión nueva del parche): acelera el audio SPU y agrega el mod propio «Steam Deck display» con interpolación de cuadros a la frecuencia de la pantalla y widescreen 16:10. Requiere recompilar el kit.
- **Límites:** la interpolación solo mezcla cuadros terminados (puede dejar estela en movimientos rápidos); el widescreen es experimental y las pantallas 2D y los videos siguen en 4:3. La lógica del juego queda a su velocidad original (30 FPS).

## Crash Team Racing: Turbocharged y Spyro the Dragon (OpenPete)

- **Hace falta:** el disco USA de cada juego (SCUS-94426 y SCUS-94228) en `~/Emulation/roms/psx`.
- **Configurar:** descarga el port, copia el disco donde lo espera y deja el acceso listo.
- **Límite conocido:** Crash pregunta la primera vez por una fuente opcional («Use Luckiest Guy») y por un preset de gráficos; esa pregunta no se puede automatizar.

## The Legend of Zelda: The Minish Cap (Project Picori)

- **Hace falta:** una ROM de GBA (USA, Europa o Japón) en `~/Emulation/roms/gba`; se reconoce por SHA-1 con cualquier nombre.
- **Configurar:** copia la ROM con el nombre que espera el port. Con la ROM europea el juego queda en español.
- **Queda ajustado:** pantalla completa, escala interna 5× (1200×800, la altura de la pantalla), reloj de 90 FPS y widescreen.

## The Legend of Zelda: A Link to the Past (zelda3)

- **Hace falta:** la ROM USA 1.0 en `~/Emulation/roms/snes` (se acepta con encabezado de copiador). Para el español, además, el parche de la traducción «F01h» (archivo `.ups`, suelto o dentro de su zip) en Descargas o en la misma carpeta de ROMs.
- **Configurar:** instala Pillow y PyYAML en una carpeta local, compila dentro del SDK, extrae los recursos y, si hay un parche que dé el SHA-1 esperado, genera la ROM en español (`The Legend of Zelda - A Link to the Past (Spanish).sfc`) y deja `Language = es`.
- **Queda ajustado:** pantalla completa, 16:10, sin límite de sprites, filtro lineal desactivado y audio por PulseAudio.
- **Límite:** los diálogos salen en español, pero los rótulos del menú (ITEM, EQUIPMENT) siguen en inglés porque el port no importa esos gráficos.

## The Legend of Zelda: The Wind Waker HD (ZeldaWWHDRecomp)

- **Hace falta:** el disco de Wii U (`.wux`, `.wud` o `.wua`) en `~/Emulation/roms/wiiu/roms`. Para `.wux`/`.wud` también las claves del disco y la clave común de Wii U en el `keys.txt` de `~/Emulation/bios/sysdata`.
- **Configurar:** descarga el AppImage (verificado con el SHA-256 del release), lo desempaqueta y ejecuta el setup del port: extrae, traduce y compila (unos 10 minutos, descarga su propio compilador). Las claves se escriben en archivos privados temporales solo durante ese paso y se borran; nunca se muestran ni se guardan.
- **Queda ajustado:** español, 16:10, pantalla completa, GamePad como recuadro dentro de la misma ventana, interpolación de cuadros, FXAA y filtro anisotrópico (variables `WWHD_` del acceso).

## Juegos con emulador

- **Ajustes → Aplicar ajustes máximos para Steam Deck:** deja DuckStation (5×, PGXP), Dolphin (3×, anisotrópico 16×), Azahar (3×, pantalla única, shaders asíncronos) y Eden (shaders asíncronos, anisotrópico 16×) al máximo que admite la pantalla. Hace una copia de cada archivo y omite el emulador que esté abierto.
- **Breath of the Wild (Eden):** español latinoamericano; resolución 1× con escalado FSR y precisión de GPU normal, solo para este juego. Parches de rendimiento: **Instalar mod** en la ficha acepta el zip del parche (`exefs/*.pchtxt`), siempre que coincida con la versión del juego (la 1.9.0 usa el hash de compilación `CD57B23F…`). El juego va a 30 FPS y los 90 FPS no son posibles con el parche de 60 FPS, porque Eden emula una pantalla de 60 Hz.
- **A Link Between Worlds (Azahar):** idioma de la consola 3DS en español y una sola pantalla. En la Deck, **L4** alterna entre pantalla superior e inferior y **R4** cambia la disposición (layout de Steam Input propio, asignado al agregar el juego a Steam).

## Mario Kart Wii (WiiCompiled)

- **Instalación propia:** Agregar juegos → Preparar Mario Kart Wii (imagen PAL limpia RMCP01, unos 20 GB temporales).
- **Actualizaciones:** si WiiCompiled está administrado por Quiver, **Actualizaciones → Actualizar aquí** descarga el setup nuevo (SHA-256 verificado), reinstala el juego con la imagen de la biblioteca dentro del SDK de KDE y restaura el setup anterior si algo falla. No hace falta abrir Quiver.

## Steam

- **Accesos y mandos:** al agregar un juego se guarda el acceso con el layout de gamepad para todos los tipos de mando (Steam Deck, DualSense, DualShock, Xbox, Switch Pro, genérico). Se escribe con Steam cerrado y siempre con copia de seguridad.
- **Arte:** la carátula de la biblioteca es el retrato que Steam ya tiene para cada acceso (por ejemplo el del plugin SteamGridDB de Decky), y la ficha muestra su fondo y logotipo como banner. **Arte de Steam** (ficha) y **Completar arte de todos los accesos de Steam** (Ajustes) buscan lo que falta con una clave API propia de SteamGridDB, sin reemplazar nada existente.

## Revertir

Cada cambio de ajustes deja una copia fechada junto al archivo original (`*.deck-library-AAAAMMDD-HHMMSS.bak`, `.orig` para el código de los kits y `grid/.deck-library-backups` para el arte). Los accesos de Steam y los layouts guardan su copia en la carpeta de configuración de Steam.
