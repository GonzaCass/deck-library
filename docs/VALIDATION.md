# Validación — 2026-10-01

## Notas del lanzamiento local de DMC3 Crimson

La instalación existente de Crimson 0.5a se lanzó mediante Steam Desktop con un wrapper directo de DMC3 y una DLL de la API de Steam compatible y aislada. La inspección de los módulos del proceso y la pantalla de bienvenida visible de Crimson confirmaron el arranque. La DLL original de la API de Steam de la colección se conservó. La jugabilidad, los FPS sostenidos y el Modo Juego siguen sin probarse tras este cambio. Esto se documenta en [DMC3-CRIMSON.md](DMC3-CRIMSON.md); no se añadió ningún instalador automático de Crimson a Deck Library.

Deck Library 0.3.3 se validó en Steam Deck OLED / SteamOS con Python 3.11+ y GTK 3. Los artefactos públicos excluyen bibliotecas personales, datos de cuentas, ROM, claves, mods y capturas de pantalla de juegos.

## Receta de GTA IV en 0.3.3

Se superaron 51 pruebas automatizadas, incluidas cinco pruebas nuevas de GTA IV: aplicación y restauración completas con conservación de los ajustes gráficos y de FPS, cambio únicamente de la preferencia de VSync en el archivo binario de ajustes, eliminación y restauración de archivos de mods exclusivos de versiones más nuevas, reversión tras un fallo de escritura inyectado, rechazo por hash, versión, ocupado o enlace simbólico, protección frente a conflictos tras un cambio de ajustes, y descubrimiento en microSD sin añadir un acceso directo de Steam duplicado.

Una comprobación rápida del diálogo GTK ejercitó los botones Aplicar/Restaurar y los mensajes de finalización asíncronos con operaciones simuladas y un almacén temporal. El juego no se abrió ni se modificó durante el desarrollo de la aplicación. La detección de la instalación y del prefijo de Steam encontró la instalación local real de GTA IV. El informe de jugabilidad satisfactorio corresponde a la prueba anterior del usuario con FusionFix 4.0.5, no a una nueva medición de FPS. Véase [GTAIV.md](GTAIV.md).

## Comprobaciones automatizadas

46 pruebas cubren los ciclos completos y la conservación del formato binario de Steam, las copias de seguridad, las escrituras concurrentes y el rechazo con Steam en ejecución; el descubrimiento y las identidades estables de accesos directos; los ID de instancia de Prism; la validación de ajustes preestablecidos, la compatibilidad, las copias de seguridad y la restauración protegida; las exportaciones portables y los comentarios; la verificación de hash y límites de NSP; la seguridad de los archivos de mods; la cancelación de procesos de compilación propios; y la coincidencia de proveedores de ilustraciones, la validación de HTTPS/imágenes, los metadatos de origen de la caché privada y el comportamiento de respaldo. Las pruebas usan directorios temporales. Los módulos de Python se compilan correctamente.

## Interfaz e instalación

El asistente de primera ejecución rediseñado se ejercitó en sus cuatro pasos con una biblioteca aislada: detección asíncrona, selección, preferencias de proveedores, finalización persistida y traspaso a la biblioteca. Las vistas de retrato/lista, los controles de selección, los detalles de juego y los ajustes se abrieron a 1200×740. Estas comprobaciones de interfaz no realizaron cambios en Steam ni lanzamientos de juegos. Se conservaron los ajustes existentes del lanzador y de los juegos.

Las descargas en vivo desde Wikipedia tuvieron éxito para Mario Kart Wii, Mario Kart 8 y Smash. También se comprobaron la búsqueda y la descarga de ilustraciones de Wii en Libretro. El comportamiento de SteamGridDB está cubierto con respuestas simuladas y pruebas de respaldo; el acceso autenticado en vivo queda pendiente de que el usuario aporte una clave de API. Wikipedia puede devolver ilustraciones representativas en lugar de una carátula específica de la edición. Las capturas de pantalla públicas contienen únicamente juegos ficticios y diseños de relleno originales.

El descubrimiento encontró 19 entradas, incluidas cuatro instancias de Prism. Las carátulas son la vista predeterminada, con una alternativa de lista y selección local de ilustraciones. Los diálogos de instalaciones, contenido, ajustes preestablecidos, distribución de Minecraft y preparación de Wii se abrieron dentro de las dimensiones de la pantalla de la Deck. La captura de pantalla pública usa entradas ficticias. La instalación conserva los datos privados de la biblioteca e instala los ajustes preestablecidos y la documentación incluidos.

## Comprobaciones de lanzamiento

| Juego | Resultado | Modo Juego |
| --- | --- | --- |
| Mario Kart Wii / WiiCompiled existente | El usuario confirmó imagen nítida y jugabilidad excelente; instalación existente conservada | El usuario confirmó que funciona |
| Mario Kart 8 Deluxe / Eden, CTGP Deluxe | El acceso directo real de Steam Desktop alcanzó el título de CTGP tras la actualización 3.0.3 y el registro de DLC | Pendiente de prueba por el usuario |
| Instalación nueva con el asistente de WiiCompiled | Configuración oficial PAL completada, parche de controles recompilado, ajuste preestablecido nítido aplicado; el lanzamiento gestionado alcanzó el título | Pendiente de prueba por el usuario |

Las comprobaciones automatizadas de lanzamiento duraron unos 15 segundos y son comprobaciones de arranque, no mediciones de FPS sostenidos. El asistente nuevo usó un KDE SDK 6.11 ya instalado; la instalación de dependencias en una Deck nueva sigue sin probarse.

El directorio de contenido NAND de MK8 estaba vacío: las actualizaciones eran visibles únicamente mediante el análisis asíncrono de la lista de juegos de Eden. Un lanzamiento directo por CLI podía iniciarse antes de que dicho análisis poblara el contenido de actualización, mientras que seleccionar el juego en Eden funcionaba. El registro de las NCA de actualización y DLC verificadas por hash del usuario en la NAND configurada permitió que el lanzamiento directo desde Steam Desktop alcanzara CTGP. Se conservaron los archivos originales, las partidas guardadas y los mods. El Modo Juego sigue sin verificarse.

Los lanzamientos gestionados de Eden suprimen el diálogo del actualizador del AppImage incluido mediante su indicador de entorno compatible DISABLE_AUTO_UPDATES. La configuración de Wii existente se mantiene en Vulkan 1.5x; el asistente nuevo aplica el ajuste preestablecido correspondiente y el parche de controles Escape/F12 únicamente a su propia instalación.

## Compartición y límites

Los ajustes preestablecidos son JSON de solo datos con listas de permitidos explícitas de adaptadores. Se admiten importaciones, exportaciones, comentarios locales y un catálogo de GitHub por HTTPS configurado manualmente. No se implementa ningún servidor, base de datos, publicación ni carga automática. Las distribuciones de mando son recomendaciones con un enlace a los controles de Steam, no asignaciones instaladas automáticamente. Las versiones base/de actualización de Switch se muestran cuando son identificables; las versiones desconocidas requieren comprobación en Eden. Las claves y el firmware los aporta el usuario mediante el emulador. Las demás integraciones de emuladores, todas las instancias de Minecraft y cada ajuste preestablecido de juego propuesto no se han probado en jugabilidad. Los ajustes preestablecidos propuestos se etiquetan en consecuencia; no se ofrece ninguna garantía universal de FPS.

## Comprobaciones de interfaz de 0.3.2

El descubrimiento durante la incorporación se inicia sin juegos seleccionados. Completarlo sin marcar ningún juego abre la biblioteca fuera del modo de selección. La selección explícita sigue disponible. El recorrido de la interfaz comprobó ambos estados. Las acciones de juego usan colores distintos y etiquetas explícitas. Se eliminaron los eslóganes decorativos, se revisaron las etiquetas en español y se corrigió la puntuación de las preguntas.

## Integración con Steam de 0.3.2

Se superan 46 pruebas automatizadas, incluidas la conservación de los ID, opciones, etiquetas e indicadores de control de accesos directos importados, la vinculación de una instancia de Prism existente sin duplicación, las copias de seguridad de reemplazo de cuadrículas y el rechazo con Steam en ejecución, las asignaciones repetidas de Steam Input y el descubrimiento de Quiver personalizado/nuevo. La inspección local de Steam encontró el perfil Omnicraft Neptune con 29 asignaciones; su lectura no modificó su configset. El diálogo de ajustes preestablecidos y las herramientas existentes se probaron rápidamente en tamaños compatibles con la Deck. Las escrituras de ilustraciones de Steam y las ediciones de accesos directos en vivo se probaron contra fixtures temporales de VDF/cuadrícula; las escrituras reales en la cuenta se aplazan hasta cerrar Steam.

## 0.3.4 Project-2099

Se superaron 55 pruebas del núcleo. Las comprobaciones nuevas cubren el rechazo de ISO/ZIP de PS3 antes de descargas o escrituras en el destino, las comprobaciones previas de volumen de Xbox, la conservación/exportación/restauración del TOML raíz incluidas claves anidadas no relacionadas, y el descubrimiento únicamente de instalaciones completas. La imagen de PS3 suministrada fue rechazada por el instalador oficial Beta 4.1 bajo Proton 11.0. Ninguna instalación del juego ni medición de FPS tuvo éxito con esa fuente; el reemplazo para Xbox 360 está pendiente.

## Project-2099 — 2026-10-02

Se superaron 56 pruebas del núcleo, incluidas las comprobaciones de metadatos de 7z nativo/ISO único y el rechazo de PS3 antes de las descargas. El diálogo del instalador GTK se construyó con las acciones de instalación simuladas. El 7z de Xbox 360 se extrajo con verificación CRC; el Beta 4.1 oficial identificó usa-europe-retail-r2, verificó 293 archivos de origen y completó ambos árboles de idioma con español seleccionado. El `--verify-install` del runtime instalado devolvió 0 bajo Proton 11.0. El ajuste preestablecido de 720p/60 está aplicado, pero sigue siendo una propuesta: no se ha realizado ninguna validación de FPS en jugabilidad ni del Modo Juego. El 7z original se conservó y se eliminó la extracción temporal de ISO/carga útil.

## 0.4.0

Se superan 90 pruebas del núcleo. Cobertura nueva: plantillas de mando (ID de aplicación con y sin signo, conservación de las elecciones existentes, reemplazo forzado con copia de seguridad, rechazo mientras Steam se ejecuta, limpieza al eliminar), eliminación de accesos directos (renumeración, copia de seguridad, ilustraciones apartadas, ejecución en cola), depuración de enlaces obsoletos de Steam, comprobaciones de actualización (comparación de versiones, `version.txt` de Quiver, caché, fallos parciales), autoactualización verificada (discrepancia de suma de verificación, rutas inseguras, suma de verificación ausente, HTTP sin cifrar rechazado) y el adaptador de DuckStation (detección de número de serie, perfiles manuales, parcheo de INI con conservación de líneas comprobado contra el `settings.ini` real, aplicación/restauración). Las páginas GTK se renderizaron con un directorio de datos temporal y el diálogo de ajustes por juego leyó los valores globales reales de DuckStation.

Sin verificar en una sesión de Steam en vivo: la eliminación y las escrituras de distribución de mando contra la cuenta real (Steam estaba abierto durante el desarrollo), el comportamiento del DualSense en Edge of Time tras asignar la distribución, la autoactualización contra una versión publicada, y la lectura por DuckStation del archivo generado por juego.

### Comprobaciones de catálogo y publicación

Se superan 114 pruebas del núcleo. El lector de catálogo se ejecutó contra las listas en vivo de Quiver (229 ports, entradas mal formadas descartadas); el selector de recursos se comprobó contra versiones en vivo de 40 de ellos (las versiones solo para Windows se rechazan, los binarios de Linux sin empaquetar se aceptan); una instalación real de Banjo Recompiled v1.0.2 verificó su SHA-256 publicado, se extrajo, identificó el ejecutable y apareció en el análisis de la biblioteca. El límite anónimo de velocidad de GitHub se alcanzó durante las pruebas y ahora produce un mensaje claro.

### 0.4.1

Se superan 148 pruebas del núcleo. La lista de GithubLauncher (`SirDiabo/GHLAppList`, lanzador con licencia MIT; el repositorio de la lista no declara licencia, por lo que se lee en tiempo de ejecución y no se redistribuye) se fusiona con la de Quiver en 255 ports; la página de catálogo se renderizó contra la red en vivo con iconos de las listas y carátulas de PlayStation encontradas mediante Libretro. Esa ejecución detectó un conflicto de nombres entre el auxiliar del catálogo y las `entries` de la biblioteca. Se inspeccionaron ambos repositorios de Spider-Man PSX: cada uno publica un kit de configuración para Linux x64; Spider-Man requiere SLUS-00875 y una BIOS de Europa, y Spider-Man 2 requiere SLUS-01378 (USA) y una BIOS SCPH-1001. No se instalaron ni compilaron aquí: esta Deck no tiene CMake, Ninja ni compilador.

### 0.4.2 - ports que se compilan en la Deck

Se superan 164 pruebas del núcleo. En esta Steam Deck (SteamOS, sin compilador, `/usr/include` vacío) el Flatpak de KDE SDK 6.11 proporcionó CMake 4.4, Ninja, GCC 15, Python 3.13 y cabeceras de SDL3/Vulkan/X11/Wayland/ALSA. Dentro de él, el kit de Spider-Man PSX (v0.1.1) se configuró con SDL3 obtenido desde el código fuente y compiló los 580 pasos de compilación hasta obtener un ejecutable setup-host funcional. El kit de Spider-Man 2 (v0.1.0) se instaló desde su versión publicada con el SHA-256 publicado verificado, se inició mediante el comando wrapper que genera Deck Library, abrió la ventana de su lanzador y abrió el mando de Steam Deck. El sandbox de flatpak no tiene red salvo que se indique `--share=network` y monta únicamente la carpeta personal, circunstancias ambas que el wrapper contempla.

Sin verificar: la generación y compilación de un juego a partir de un disco. Ambos kits requieren un volcado USA (SLUS-00875, SLUS-01378 Rev 1) y la biblioteca local solo contiene copias de España y Europa, por lo que no se ejecutaron la comprobación de disco, la generación de código ni la jugabilidad, y no se afirma nada sobre el rendimiento.

### 0.4.3

Se superan 178 pruebas del núcleo. En esta Deck, las tarjetas de los kits encontraron `scph5502.bin` (SHA-256 1faaa18f...) y `scph1001.bin` (71af94d1...) en la carpeta de BIOS de EmuDeck, que son exactamente los hashes que exigen los kits de Spider-Man y Spider-Man 2. La biblioteca de PlayStation contiene `Spider-Man (Spain)` y `Spider-Man 2 - Enter - Electro (Europe)`; los kits fijan los ejecutables USA y los hashes de Redump (SLUS-00875, SLUS-01378 Rev 1), por lo que esos discos se notifican como de región incorrecta. El verify-disc propio del kit calcula el hash del contenedor CHD, por lo que no puede identificar un CHD; la conclusión sobre la región se basa en los nombres de las versiones y en las identidades fijadas.

### 0.4.4 - kits de Spider-Man PSX generados y compilados en la Deck

Se superan 192 pruebas del núcleo. Con discos USA aportados por el usuario (SLUS-00875: tamaño, MD5, SHA-1 y CRC32 iguales a la identidad Redump fijada del kit; SLUS-01378: tamaño, MD5 y SHA-1 iguales a la identidad Rev 1 fijada) y los archivos de BIOS encontrados por hash en la carpeta de EmuDeck, ambos kits ejecutaron su propia verificación de disco, generaron el juego recompilado y el código C de la BIOS, y compilaron el runtime dentro del Flatpak de KDE SDK 6.11 (unos 6 minutos para Spider-Man, 648 pasos de compilación). Ambos juegos compilados se iniciaron dentro del sandbox en la Steam Deck: Spider-Man mostró su primera escena 3D con el lanzador indicando 'Disc verified, SLUS-00875, NTSC-U'; Spider-Man 2 arrancó directamente (`--no-launcher`) hasta su intro e indicó SLUS-01378. El lanzador del kit adopta la BIOS en la primera ejecución y la almacena en `build/bios.cfg`; Deck Library inicia un kit compilado con su lanzador hasta que ese archivo existe y directamente a partir de entonces.

Sin verificar: jugabilidad, tasa de fotogramas y audio (la sesión de prueba no disponía de un dispositivo de audio utilizable), el lanzamiento en Modo Juego desde Steam, y la advertencia del kit de que el código generado de la BIOS SCPH-1001 puede no coincidir con la huella actual del emisor (el juego arrancó igualmente).

### 0.5.0 - OpenPete, CTR Turbocharged, configuración automática y limpieza de la biblioteca

Se superan 233 pruebas del núcleo. Con ejecución exclusiva mediante las funciones propias de la aplicación en esta Deck (tras eliminar instalaciones manuales de prueba anteriores): CTR Turbocharged se descargó desde ctr.cmzi.uk (tamaño comprobado) y su disco NTSC-U (SCUS-94426, BIN MODE2/2352 sin procesar, encontrado por número de serie) se copió como `ctr-u.bin`; OpenPete v0.4.2 se descargó desde dl.openpete.com con el SHA-256 publicado coincidente, se descomprimió y su módulo se precompiló a partir del disco SCUS-94228 dentro del SDK; ambos kits de Spider-Man se reinstalaron desde sus versiones y pasaron de nuevo por verify-disc, generación y recompilación (ejecutables con tamaño en bytes idéntico al de la primera compilación). El comando de lanzamiento propio de cada entrada inició entonces su juego: ambos kits y OpenPete renderizaron escenas de juego, y CTR alcanzó su aviso de fuente de primera ejecución. La sesión es un escritorio remoto con renderizado por software y sin dispositivo de audio, por lo que las tasas de fotogramas (OpenPete mostró 4-6 FPS) y el sonido no dicen nada sobre el hardware de la Deck.

Detectado y corregido durante la ejecución: la detención de una precompilación dejaba en ejecución el juego en sandbox (ahora se detiene todo el grupo de procesos); entradas duplicadas en la biblioteca para un lanzador de configuración y su juego compilado (una entrada por port del catálogo); un acceso directo de Steam importado listado junto a la instancia de Minecraft a la que pertenece.

Sin verificar: jugabilidad, audio, lanzamientos en Modo Juego, CTR más allá de sus avisos de primera ejecución, y el rendimiento de OpenPete en la pantalla propia de la Deck. El aviso de fuente de CTR no pudo cerrarse mediante un clic automatizado, por lo que sigue siendo un paso manual.

### 0.5.2 - instalador y cachés compiladas

Los archivos de versión almacenan cada archivo con una hora de modificación igual a cero. Python reutiliza una caché compilada cuando la hora y el tamaño del código fuente coinciden, de modo que, tras actualizaciones que solo cambiaron el número de versión (de igual longitud), la aplicación instalada siguió ejecutando el código en caché de 0.4.0 mientras su código fuente indicaba 0.5.1. El instalador ahora copia los archivos con la hora actual, elimina las carpetas `__pycache__` antiguas y reemplaza el archivo de icono del tema para que las cachés de iconos del escritorio lo detecten; una prueba de regresión instala dos versiones de igual longitud con mtime cero y comprueba cuál se ejecuta (falla con el instalador anterior). Esa misma propiedad hizo que un `rsync` basado en hora y tamaño omitiera un archivo modificado al copiar una versión al repositorio; las copias deben usar `--checksum`.

### 0.5.3 - mando en los kits de recompilación

Los kits de Spider-Man ignoraban el mando al iniciarse directamente. En el runtime, el Jugador 1 usa por defecto el teclado (`player_device[0] = "keyboard"` en las compilaciones de versión) y solo el lanzador propio del kit asigna un mando; Deck Library inicia un kit compilado con `--no-launcher`. No apareció ninguna línea `opened controller for slot` en ningún registro de ejecuciones anteriores. Establecer el `[controller] p1_device = "auto"` propio del kit en `game.toml` (copias del proyecto y de `build/`) hace que el runtime imprima `opened controller for slot: Steam Deck Controller` al iniciarse en el sandbox y `...: #SettingsController_SteamController` al iniciarse desde Steam, en ambos kits. `ports.configure` ahora lo establece, y `ports.maintain` repara los kits instalados por versiones anteriores en cada análisis de la biblioteca (nunca sobrescribe un `p1_device` ya establecido).

Descartado durante el proceso: las plantillas de Steam Input (idénticas a las de los ports que funcionan), el controlador SDL HIDAPI (desactivado bajo Steam tanto en los kits como en OpenPete) y el sandbox (OpenPete funciona en él). No fue posible inyectar pulsaciones de botones, por lo que la comprobación consiste en que el runtime abre el mando, no en una sesión jugada.

### 0.5.4 - rendimiento de los kits de recompilación

Medido en esta Deck con el juego en ejecución sin ventana ni audio (`PSX_HEADLESS=1 SDL_VIDEODRIVER=dummy PSX_HOST_MUTE=1`, que no se ajusta al tiempo real) como fotogramas del invitado alcanzados en instantes fijos de reloj real. En Spider-Man 1, la introducción en vídeo (de unos 10 a 35 s) avanzó a 45,8 fotogramas/s, por debajo de los 59,94 necesarios, lo que equivale a escenas cinemáticas lentas con audio entrecortado. `perf` situó el 20,7 % de la CPU en `spu_get_global_state`: el planificador de eventos de SPU por muestra (`psx_spu_sample_event_cycles_to_next` y `psx_spu_sample_event_service`) solicitaba el estado completo de la SPU (copias de registros y un bucle sobre las 24 voces) cuando solo lee `ctrl`. Un parche local de comportamiento idéntico lee ese registro directamente (las ediciones solo se aplican si el texto original coincide exactamente, con copias de seguridad `.orig`); la misma sección avanzó entonces a 57,1 fotogramas/s (+25 %) y el perfil quedó plano. El modo por muestra se dejó activado, dado que el runtime documenta que es necesario para los motores de audio dirigidos por IRQ y para la sincronización de cinemáticas.

Spider-Man 2 tenía `overlay_cache = true` pero ningún `overlay_autocompile_cmd`, por lo que el runtime seleccionaba el nivel de toolchain incluido, no disponible, e interpretaba cada overlay de código que cargaba (0 despachos de overlays nativos y 26 089 interpretados en 70 s). Con el comando apuntando a `compile_overlays.py --compiler gcc` (python3 y gcc existen dentro del SDK) los overlays se capturaron, se compilaron en unos 2 s y se cargaron: 14 151 nativos y 10 075 interpretados en el mismo tiempo, mejorando a medida que se visita más del juego.

Probado y descartado: el PGO del kit (`[pgo] enabled`). El entrenamiento se ejecutó pero no escribió ningún perfil (su CMake no implementa PGO para gcc), por lo que el resultado se recompiló sin él. Sin verificar: la calidad audible del sonido y el ritmo real de fotogramas en la pantalla propia de la Deck en Modo Juego.

### 0.5.5

El runtime de Spider-Man 2 es más reciente y su planificador de eventos por muestra ya no solicita el estado completo de la SPU, por lo que el parche local de SPU informa `not-needed` en lugar de un fallo (su kit conserva el ajuste del compilador de overlays, que era la causa de su lentitud).

### 0.6.0 - ports de Zelda

Ejecutado únicamente mediante las funciones propias de la aplicación en esta Deck. Minish Cap: Picori v0.9.5 descargado con su resumen publicado verificado, la ROM de Europa (SHA-1 cff199b3...) encontrada por hash y copiada, y el binario informa `ROM detected`. A Link to the Past: la ROM USA suministrada con cabecera de copiadora se reconoció tras retirarla (SHA-1 6d4f10a8...), Pillow/PyYAML se instalaron localmente, se compiló en el SDK en menos de un minuto con `zelda3_assets.dat` extraído, y el juego abrió su ventana. Wind Waker HD: el AppImage coincidió con el SHA256SUMS de la versión; la imagen `.wux` más las claves leídas de `keys.txt` pasaron por la configuración del port (extracción, traducción a C, compilación con su zig descargado) y el juego compilado se inició e informó ventanas `Vulkan` para el juego y la pantalla del GamePad.

Detectado y corregido durante el proceso: `pick_asset` trataba "Wind" en `WindWakerHD-...` como Windows y rechazaba la compilación para Linux; la anulación del ejecutable de un port compilado desde el código fuente se perdía al limpiar por segunda vez su entrada de catálogo; SDL dentro del SDK elige JACK primero y aborta salvo que se establezca `SDL_AUDIODRIVER`.

Sin verificar: cualquier fotograma en pantalla. Esta sesión es un escritorio remoto sin DRI3 ni audio, por lo que Vulkan no puede presentar (Mesa así lo indica) y SDL no puede abrir un dispositivo de audio; Picori recurrió a su renderizador OpenGL y los otros dos se comprobaron únicamente hasta la creación de la ventana. La jugabilidad, el rendimiento, el audio, los lanzamientos en Modo Juego y el comportamiento de la ventana del GamePad en la pantalla propia de la Deck siguen sin probarse. Wind Waker HD abre una segunda ventana para el GamePad de Wii U.

### 0.6.0 - interfaz, ajustes máximos y BotW

La interfaz pasó de barra lateral a pestañas superiores con filtros de tipo como botones; se abrió con la biblioteca real a 1200×740 y se comprobó el diseño. El ícono pasó a una consola portátil con una estantería de cajas de juego (no es el logotipo oficial de Valve). `deckmax.apply` modificó de verdad DuckStation, Dolphin, Azahar y Eden con respaldo, y una segunda ejecución informó «ya aplicado»; no se verificó el efecto en juego. Breath of the Wild: la actualización 1.9.0 y los 2 DLC se registraron en la NAND de Eden con `install_nsp` (hash verificado), sin arrancar el juego. A Link Between Worlds (Europa, con español) se detecta desde `~/Emulation/roms/n3ds`; el idioma del sistema 3DS se elige en Azahar, no se pudo fijar desde el archivo de configuración.

### 0.6.1 - idioma, pantallas y mods

Aplicado y comprobado en archivos reales: `config` del 3DS de Azahar (bloque de idioma 0xA0002 pasó de 1 a 5, con respaldo, y una segunda ejecución informó «ya aplicado»), `qt-config.ini` de Azahar (diseño de pantalla única, atajos F9/F10, 3×), archivo propio de Breath of the Wild en Eden (idioma 14, 1× con FSR), `config.json` de Picori (escala 5×, idioma 4, pantalla completa; el binario arrancó sin quejas) y `build/mods/state.toml` de ambos kits de Spider-Man (el runtime informó «4x load acceleration», lo que confirma que el estado se lee). Steam: el acceso de A Link Between Worlds quedó con la plantilla `controller_neptune_deck_library_screens.vdf` (L4 = F9, R4 = F10) y el de Wind Waker HD se regeneró con sus variables.

Descartado: la interpolación de cuadros de los kits de Spider-Man («propiedad de un mod», que no se distribuye en esta versión) y el widescreen (requiere sitios específicos por juego que Spider-Man no declara). Sin verificar: velocidad real, nitidez y sonido de cualquiera de estos juegos, y que Steam Input aplique F9/F10 en modo Juego; esta sesión remota no tiene DRI3 ni audio, y Wind Waker HD no puede dibujar aquí (Vulkan sin presentación). La resolución y los filtros elegidos son razonamiento sobre la pantalla de 1280×800, no mediciones.

### 0.6.2 - español en A Link to the Past, mod de pantalla en Spider-Man, 60 FPS de BotW

Parche UPS «F01h» aplicado con `apply_ups` sobre la ROM USA: las tres sumas CRC32 coincidieron y el resultado tiene SHA-1 `461FCBD7…`, el que el port espera. Con `--extract-dialogue` y `--languages=es` se regeneró `zelda3_assets.dat` (de 683 888 a 721 284 bytes), el archivo `dialogue_es.txt` contiene los textos en español y el juego abrió con `Language = es`; la pantalla de menú sigue en inglés (gráficos de la ROM). No se leyó un diálogo en pantalla.

Los dos kits de Spider-Man se recompilaron con el paquete `psx.deck.display`; al arrancar, el runtime informó «display-refresh presentation-only temporal blending», «fixed display aspect 16:10» y «widescreen 16:10 (engages at game entry)». No se vio una escena de juego, de modo que el aspecto del widescreen en partida y la fluidez de la interpolación no están verificados. Se probó el framework más reciente en una copia del kit: no es compatible tal cual (su generador estaciona la BIOS como SCPH1001, con otro hash que la SCPH-5552 que exige este kit, y descargó 2,5 GB de herramientas y modificó `.bashrc`, cambios que se revirtieron); la copia se eliminó.

Breath of the Wild: el parche `60fps_1.9.0.pchtxt` (hash de compilación CD57B23FA4BBAD65…) se copió a la carpeta de mods de Eden; Eden no se abrió con él, de modo que no se comprobó que se aplique. No se encontró forma de pasar a 90 FPS: el parche solo fija el intervalo de vsync en 1 y Eden emula una pantalla de 60 Hz.

### 0.6.3 - arte de Steam

Se inspeccionó la carpeta `grid` real tras el trabajo con el plugin SteamGridDB de Decky: cinco archivos por acceso (`<id>p`, `<id>`, `<id>_hero`, `<id>_logo`, `<id>_icon`) y un `<id>.json` con la posición del logotipo; `steamart` usa exactamente ese diseño. Los tests cubren detección de espacios existentes, escritura con copia de seguridad, rechazo con Steam abierto y de archivos que no son imágenes, filtrado de resultados adultos o de humor, y la cola que espera a que Steam se cierre. El diálogo se abrió con la biblioteca real y datos de proveedor simulados (sin clave ni acceso a SteamGridDB desde aquí): las cinco pestañas, las miniaturas y el resumen por espacio se mostraron correctamente. Sin verificar: búsquedas reales contra la API y el resultado en la biblioteca de Steam.

### 0.6.4 - arte de Steam en lote

`complete_missing` se probó con proveedor simulado: llena solo los espacios vacíos, omite los accesos de la tienda de Steam, informa «completo» cuando no falta nada y un juego que falla (error de red) no detiene a los demás. El botón aparece en Ajustes. Sin verificar contra la API real de SteamGridDB (no hay clave propia en esta Deck). El plugin SteamGridDB de Decky se revisó solo para saber cómo accede a la API: usa una clave embebida con una advertencia de su autor contra su uso en otros proyectos, por lo que Deck Library no la utiliza.

### 0.6.5 - arte de Steam con la API real

Con una clave propia de SteamGridDB se consultó la API real: la búsqueda de «The Legend of Zelda: A Link Between Worlds» devolvió el juego y cada espacio dio imágenes de las medidas que usa Steam (600×900, 460×215, 1920×620, logotipo y 512×512). El lote recorrió los 23 accesos: 18 estaban completos, Breath of the Wild recibió portada horizontal, fondo, logotipo e ícono (escritos en la carpeta `grid` con Steam cerrado y reabierto) y las instancias de Minecraft se omiten a propósito porque SteamGridDB las resuelve todas al juego genérico. Se corrigió que una imagen no válida (por ejemplo un GIF) abortara todos los espacios de un juego: ahora pasa al siguiente candidato, y se acepta ICO solo para el ícono. No se vio el resultado dentro de la biblioteca de Steam.

### 0.7.0 - diseño, movimiento, ajustes detectados y actualización de WiiCompiled

Se consultaron los repositorios base de interfaz (ui-ux-pro-max-skill: 79 estilos buscables, 192 paletas, guías de movimiento y de accesibilidad; awesome-design-md) y se aplicaron sus reglas: transiciones de 150–300 ms, aparición escalonada, foco visible, objetivos táctiles, ocho píxeles de separación, respeto a «reducir movimiento» y sin degradado violeta ni controles excesivamente redondeados. La interfaz se abrió con la biblioteca real y se capturó la biblioteca, Ajustes y el diálogo de ajustes de Breath of the Wild, que mostró los valores leídos de `custom/01007EF00011E000.ini`. El movimiento (fundidos y deslizamiento) no se pudo evaluar en vídeo: solo se comprobó que no produce errores y que el aviso aparece.

WiiCompiled: la instalación gestionada por Quiver se detecta con su ejecutor Flatpak, la versión nueva v0.2.34 se informa una sola vez (se evitó el aviso duplicado de Quiver) y los tests cubren el rechazo por suma distinta, la instalación con el comando `install --game` y la restauración del setup anterior cuando falla. La actualización real no se ejecutó sobre la instalación existente (reconstruye el juego y necesita unos 20 GB libres): sigue sin comprobarse de punta a punta.

### 0.8.0 - rediseño y actualización real de WiiCompiled

Rediseño completo de la interfaz (paleta grafito y brasa, tipografía Noto Sans, controles de 4 px, filtros como pestañas, tarjetas con título debajo). Se capturaron la biblioteca, la ficha de un juego y Ajustes con la biblioteca real; el movimiento no se evaluó en vídeo. Se corrigió que una carátula pudiera apuntar al arte de otro acceso de Steam (A Link Between Worlds mostraba la de Spider-Man PS1): ahora cada entrada usa el retrato que Steam ya guarda para su propio acceso.

Actualización de Mario Kart Wii ejecutada de verdad sobre la instalación existente, con 52 GB libres: v0.2.33 → v0.2.34. Tres hallazgos: (1) el primer intento falló porque se reemplazó entero el argumento `--command=` y Flatpak recibió una ruta como ID de aplicación (el respaldo restauró el setup y la versión anteriores); (2) el segundo falló porque el runtime de Wheel Wizard no tiene archivos de desarrollo de glibc: la reinstalación debe correr en el SDK de KDE con la misma carpeta de datos, como el asistente de instalación; (3) el tercero compiló 118 objetivos, el setup nuevo coincide con el tamaño publicado, `version.txt` pasó a v0.2.34, el ejecutable se reconstruyó y `check-products` informa el producto base como actual. No se pudo abrir el juego para jugar (esta sesión no tiene GPU que dibuje); queda una copia del ejecutable y del setup anteriores en `~/.cache/wii-backup`.

### 0.8.1 - sin Quiver para actualizar

El botón «Abrir Quiver para actualizar» aparecía siempre que la tarjeta de ports tenía una actualización pendiente, incluida la de WiiCompiled que ya se actualiza desde la app. Se eliminó: los ports detectados en la carpeta de Quiver ahora ofrecen «Instalar la nueva versión aquí» (usa el instalador de Deck Library con el último release de GitHub). En esta Deck el único port administrado por Quiver es Mario Kart Wii, de modo que ese camino genérico se comprobó solo con pruebas automáticas.

### 0.8.2 - carátulas tomadas de Steam

Cada juego con acceso en Steam usa como carátula el retrato que Steam ya guarda para ese acceso (por ejemplo el elegido con el plugin SteamGridDB de Decky); si Steam no tiene uno, se conserva la carátula anterior. Aplicado a la biblioteca real: 16 carátulas pasaron a ser las de Steam. Se vuelve a aplicar en cada búsqueda de juegos.
