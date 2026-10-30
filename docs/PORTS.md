# Guía de ports y juegos configurados

[Auditoría de instalaciones (751 entradas, 26/10/2026)](PORT-INSTALLATION-AUDIT.md) · [Resultados por repositorio](../catalog/installation-audit.json)

## Vincular instalaciones y recuperar carpetas (1.4.9)

**Catálogo → Instalar** permite descargar el port o **Usar instalación existente**. En la ficha del juego, **Juego y archivos → Carpetas del juego** permite elegir de nuevo la carpeta del ejecutable y acceder al asistente de archivos originales del adaptador. Los ports agregados manualmente también pueden volver a vincular su ejecutable; reinstalar desde la app requiere conocer el repositorio o tener una integración propia.

Si un port administrado se movió, se busca primero su registro en `ports`, `DeckLibrary/ports` y las carpetas configuradas. Una coincidencia única del mismo repositorio permite recuperar la ubicación. Varias coincidencias requieren elegir: el nombre del juego no acredita que sea el mismo port. Una microSD desconectada no elimina el registro ni hace que una actualización escriba en una carpeta vacía. **Reinstalar port** es una acción explícita y puede volver a descargar una copia en la carpeta principal si la anterior ya no está disponible.

Se conserva el identificador de biblioteca y de los accesos administrados por Deck Library, la portada y la preferencia de Proton. Vincular no mueve archivos. Las instalaciones externas sin registro propio de Deck Library se referencian; no se borran ni se actualizan automáticamente. Reinstalarlas crea una copia administrada y conserva la externa. Las instalaciones administradas con registro verificado pueden seguir actualizándose en su ubicación nueva, con respaldo de la anterior.

**Savage Wind:** los originales `exefs/main` + `romfs` pueden estar en cualquier carpeta seleccionada. **Usar juego ya compilado** acepta la carpeta de datos que contiene `extracted/exefs/main`, `extracted/romfs.bin` y `extracted/swgame.so` (Linux) o `swgame.dll` (Windows), y también permite seleccionar su subcarpeta `extracted`. Esa ruta se comunica al port mediante `SAVAGEWIND_DATA_ROOT`: también determina la ubicación de partidas y ajustes. Se comprueba la estructura y el sistema del módulo; el propio port comprueba su versión de compilación. No se vuelve a pedir NSP/XCI ni claves cuando esos datos ya están preparados. Si se movieron, se muestra un aviso para volver a ubicarlos, sin crear otro directorio de partidas silenciosamente. El comportamiento de las rutas procede de [`runtime/paths.c`](https://github.com/Revivedx/SavageWindRecomp/blob/860f3722225a262bda78d049bf272e084efdc839/runtime/paths.c) del port.

## Extraer la ISO y liberar espacio (1.2.6)

En **Naruto: Rise of a Ninja** y **The Broken Bond de jorjbarbosa**, elegir **Configurar → Elegir ISO de Xbox 360 → Preparar**. También se acepta una carpeta ya extraída. Funciona sobre instalaciones anteriores de Deck Library sin reinstalar el port.

La app lee XDVDFS directamente con Python, sin abrir un instalador Windows ni instalar un compilador. Reconoce XISO recortada y las particiones estándar de discos completos; comprueba el Title ID y, cuando la receta lo publica, el SHA-256 de `default.xex`. Extrae en una carpeta temporal, verifica cada archivo por SHA-256 y solo entonces instala los datos. El progreso muestra porcentaje y tiempo estimado. `$SystemUpdate`, actualización de la consola que el port no usa, queda fuera de la extracción. Los temporales de esta operación se limpian al terminar o cancelar; las copias de respaldo previas se conservan.

Al finalizar aparece **Liberar espacio**, dentro de la app. **Conservar ISO** es la salida normal. **Eliminar ISO** pide confirmación mostrando su ruta; vuelve a verificar todos los archivos extraídos, el registro completo y la identidad de la ISO antes de borrarla permanentemente. Si falta un archivo, cambió su contenido, la ISO cambió o se cancela la tarea, el original se conserva. Partidas, mods y configuración quedan fuera de esa limpieza. La misma opción está en la ficha del catálogo y en **Archivos y Steam** del juego mientras exista una ISO verificada.

Al actualizar se conserva el registro de extracción junto con los datos originales. Si la ISO sigue presente, se verifican y reutilizan los archivos; no se vuelven a extraer. Si se eliminó, se usan los datos ya instalados. La verificación comprueba la copia y la identidad del juego: no equivale a una prueba de jugabilidad ni garantiza todas las revisiones cuando el proyecto no publica un hash exacto.

Esta extracción se aplica a las recetas anteriores. **Broken Bond de Auremana666** conserva su flujo de ISO en `assets`, importada por el propio port; Deck Library no ofrece borrarla mientras siga siendo un archivo necesario de esa integración.

## Naruto y paquetes Windows (1.2.5)

The Broken Bond tiene dos integraciones: **PC Port de Auremana666** pide la ISO de Xbox 360 y la copia a `assets`; **Recomp de jorjbarbosa** acepta ISO o carpeta extraída con `default.xex` y comprueba Title ID y SHA-256. Se instala el paquete portable con Proton y se elige el lanzador correcto. Rise of a Ninja también tiene receta para su lanzador; la versión 0.3 incorpora los arreglos Vulkan para Wine/Proton publicados por su autor. Las dos variantes de Broken Bond siguen experimentales en la Deck: instalar sin error no comprueba que su renderizado funcione.

El proceso común reconoce parejas de lanzador/motor y paquetes Windows tar, ZIP, 7z, RAR o EXE portable. Busca Proton en las bibliotecas de Steam, incluida la microSD, y contempla GE-Proton instalado como alternativa. Conserva las carpetas comunes de partidas y los originales/configuración declarados por cada receta. Los archivos para otras consolas, licencias, Android y los instaladores sin integración propia se distinguen de un juego portable. Las recetas nuevas se aplican al catálogo guardado al actualizar la app.

Los ports se descargan desde **Ports → Instalar**. La ficha distingue **Preparación integrada**, **Asistente del port**, **Preparación manual** y requisitos todavía sin integrar. Cuando hay adaptador, **Configurar** detecta o permite elegir ROM, disco y BIOS, valida sus hashes o seriales y prepara el juego. Los demás conservan el asistente o las instrucciones del proyecto. Agregar el acceso a Steam es una acción separada. Esta guía resume qué necesita cada juego, qué deja ajustado la app y qué límites hay. Ningún archivo de juego, BIOS ni clave se incluye en Deck Library ni se sube a ningún sitio.

## Dante’s Inferno y Breath of the Wild — 1.1.3

- **Dante’s Inferno / Hell’s Gate:** se descarga el ZIP portable Windows y se registra `dantes_inferno.exe`, sin confundirlo con el launcher o el extractor. Usa Proton. Después de instalar, Deck Library pide una ISO/XISO de **Xbox 360** o una carpeta extraída con `default.xex`. Las carpetas compatibles ya presentes en la biblioteca o en las rutas de EmuDeck de Xbox 360 se detectan por el Title ID `454108CF`; si hay varias, hay que elegir. Las ISO se eligen explícitamente: el nombre del archivo no demuestra qué juego contienen.
- **Preparación de Dante:** una ISO se extrae con el `extract-xiso.exe` incluido en el paquete, dentro del entorno de Proton del port. Se comprueba el contenedor XDVDFS y luego el Title ID de `default.xex`. Los datos se preparan en una carpeta temporal y solo reemplazan `game` tras verificar la identidad. Se conserva el original y una copia de la carpeta anterior. Una ISO de PS3, otro título o una cancelación no dejan el port marcado como preparado. El parche `default.xexp` publicado con el port tiene prioridad sobre el del disco. Las actualizaciones conservan `game`, partidas, modo portable y configuración; usan el parche nuevo cuando viene incluido.
- **Abrir Dante:** el acceso ejecuta el motor directamente, en pantalla completa y con SDL para el mando por defecto. Lee las opciones conocidas de `dantes_inferno.toml`, incluyendo resolución, idioma y límites de FPS, sin ejecutar comandos del archivo. La base es 60 Hz con VSync; no es una medición de rendimiento ni un preset verificado en juego.
- **Breath of the Wild / Savage Wind Recomp:** la selección automática busca una publicación con **AppImage Linux x86_64**, incluso si hay un hotfix Windows posterior. No elige aarch64. El AppImage se inicia en modo extracción y ejecución, sin depender de FUSE. El primer inicio abre el asistente del propio port para elegir la carpeta de originales **extraídos** (`exefs` y `romfs`, con la actualización integrada); no se importan NSP/XCI cifrados ni se adivina la carpeta desde la biblioteca de Eden. El paquete Linux Alpha 3 comprobado presenta versiones 1.8.2 / 1.9.0 en su asistente; la documentación actual del proyecto pide 1.9.0.
- **Convertir un NSP/XCI de Switch:** **Herramientas → Convertir un juego de Switch** convierte un NSP o XCI propio en la carpeta `exefs` + `romfs` que piden Savage Wind (Breath of the Wild) y Bayonetta 2. Hace falta el `prod.keys` de la consola propia (se busca en las carpetas de Eden, yuzu, Ryujinx y similares, o se elige a mano); solo se lee en el equipo y no se copia ni se envía. La actualización se elige aparte y se aplica sobre el juego base, de modo que la carpeta resultante ya la incluye. El resultado queda en `~/DeckLibrary/switch/<Title ID>` (o en la carpeta elegida), se comprueba que exista `exefs/main` y `romfs` y solo reemplaza una conversión anterior si es de Deck Library, conservando una copia. La conversión usa nstool (o hactool como respaldo), ver más abajo. Hacen falta unos 2,1 veces el tamaño de los archivos elegidos libres: el contenido se copia para leerlo y otra vez como `exefs`/`romfs`. No admite NSZ/XCZ comprimidos ni tickets personalizados. **Herramienta:** nstool 1.9.2, incluido en el paquete Linux x86-64 de Deck Library (binario oficial sin modificar, licencia MIT y avisos de sus dependencias; suma SHA-256 verificada), porque aplica las actualizaciones recientes que `hactool` 1.4.0 no puede leer (BKTR). Si nstool no está, usa `hactool` como respaldo. **Validación:** pruebas automáticas con herramientas simuladas y contra las reales (contenedor PFS0 con su ticket); una conversión completa de un NSP real de homebrew; y una prueba manual con Breath of the Wild de Switch: el NSP base más la actualización 1.9.0 produjeron un `exefs` completo (`main`, `main.npdm`, `rtld`, `sdk`, `subsdk0`) y 41 062 archivos de `romfs` (14,5 GB) con la estructura esperada del juego (`Actor`, `Pack/Dungeon000.pack`, `Movie`, `Voice`…) y ninguno vacío. También se convirtió un XCI real de un juego antiguo (Dragon Ball FighterZ: `exefs` y `romfs` de 6,6 GB). Un XCI de un juego de 2026 falló con «no produjo exefs/main»: el `prod.keys` probado no incluía todavía las claves de su firmware (causa probable, no verificada); la app lo indica con ese mensaje. Eso es evidencia de que la extracción terminó y se ve coherente, no de que el juego funcione con el port ni de que cada archivo sea idéntico al de otra fuente. Cuando el port pide una versión mínima (Savage Wind pide la actualización 1.9.0), el asistente avisa antes de extraer si el archivo es solo la base y pide también el archivo de la actualización; al terminar ofrece borrar los restos temporales de conversiones anteriores y nunca toca los archivos originales.
- **Savage Wind con Proton:** la opción explícita selecciona el paquete Windows y su ejecutable `savagewind.exe`, aunque también tenga un configurador. En modo automático se prioriza Linux, también al actualizar. Linux guarda originales, partidas y opciones en la carpeta de datos XDG `savagewind`, fuera de la instalación del port. Es una versión alfa; la instalación y el asistente no acreditan jugabilidad completa.
- **BotW Decomp / zeldaret/botw:** es un proyecto de decompilación sin port jugable publicado. Su ficha lo explica y no permite instalarlo como si fuera un juego. El proyecto de port correspondiente en el catálogo es Savage Wind Recomp.

Fuentes: [Hell’s Gate](https://github.com/florinp93/hells-gate-recomp), [instalación de Hell’s Gate](https://github.com/florinp93/hells-gate-recomp/blob/main/launcher/README.md), [Savage Wind para Linux](https://github.com/Revivedx/SavageWindRecomp/blob/main/docs/linux.md) y [BotW Decomp](https://github.com/zeldaret/botw).

Los ajustes de calidad parten de la pantalla de la Deck (1280×800, hasta 90 Hz). Los juegos de 30 FPS no pasan de 30 FPS salvo que el port tenga un modo propio.

## Spider-Man y Spider-Man 2: Enter Electro (PlayStation, recompilados)

- **Hace falta:** el disco USA (SLUS-00875 y SLUS-01378) en formato BIN/ISO/CUE dentro de `~/Emulation/roms/psx`, y la BIOS europea SCPH-5502/5552 en `~/Emulation/bios` (se reconoce por su SHA-256, con cualquier nombre de archivo).
- **Configurar:** verifica el disco, genera el código del juego, lo compila dentro del SDK de KDE (varios minutos) y deja el juego en `~/ports/SpiderManPSX` y `~/ports/SpiderMan2PSX`.
- **Queda ajustado:** primer mando automático, supersampling 4× y corrección PGXP de geometría y texturas. Los mods de carga rápida y de CD del kit no se activan: Fast Loading acelera todo el juego mientras detecta una carga y Spider-Man lee el disco de forma continua, por lo que quedaba súper acelerado.
- **Mejorar rendimiento** (botón de la tarjeta, solo si hay una versión nueva del parche): acelera el audio SPU y agrega el mod propio «Steam Deck display» con interpolación de cuadros (mezcla lineal) a la frecuencia de la pantalla y widescreen 16:10. En modo Juego conviene fijar 60 Hz o 90 Hz en el menú de rendimiento de Steam para ese juego. Requiere recompilar el kit.
- **60 FPS reales («Smooth 60»):** el motor de estos juegos escala su lógica por el contador de vblanks (se midió: la misma variable de posición avanza igual por vblank a 30 que a ~55 cuadros por segundo), pero su bucle principal siempre espera un vblank extra antes de mostrar cada cuadro y por eso no pasa de 30 FPS aunque la máquina sobre. Deck Library parchea el runtime del kit para anular esa espera en el bucle principal (direcciones verificadas de cada juego) y acelera la CPU emulada (8× en el primero, 10× en el segundo) frente a la GPU y el video, de modo que un cuadro cabe en un vblank. Medido en tiempo del juego: Spider-Man 1 pasó de 0,50 a ~0,96 cambios de búfer por vblank en la primera misión y Spider-Man 2 de 0,34 a ~0,9 en la escena de la Bestia (más CPU emulada rinde más hasta que manda la GPU emulada); las escenas que saturan la GPU pueden quedar por debajo de 60. **Está apagado por defecto:** en la Deck el juego se sintió acelerado y los sticks resultaron incontrolables, de modo que la lógica no es del todo independiente de los cuadros. El parche queda en el kit sin efecto y se activa solo con las variables de entorno del acceso (`DECK_WAITVB_FUNC`, `DECK_WAITVB_ZERO_RA`, `DECK_CPU_OC`).
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
- **Queda ajustado:** español, 16:10, pantalla completa, pantalla del GamePad automática (aparece unos segundos cuando cambia el mapa o un menú; **Select/Menos** pasa el juego a la pantalla del GamePad), interpolación de cuadros con ritmo uniforme, FXAA y filtro anisotrópico (variables `WWHD_` del acceso). Los tirones ocasionales son compilación de shaders la primera vez que aparece cada efecto. La versión 0.2.13 del port puede **prepararlos antes de jugar**: en Catálogo, **Preparar shaders** (también se ejecuta al configurar) los compila para la GPU de la Deck; necesita una sesión que pueda dibujar con Vulkan, no un escritorio remoto sin DRI3. Lo que no cubra la preparación se compila una vez al jugar y se guarda en `~/.config/wwhd`. **True 60** (F1 → Gráficos, experimental) calcula a Link y la cámara a 60 Hz de verdad.

## Juegos con emulador

- **Ajustes → Aplicar ajustes máximos para Steam Deck:** deja DuckStation (5×, PGXP), Dolphin (3×, anisotrópico 16×), Azahar (3×, pantalla grande con la otra pequeña, shaders asíncronos) y Eden (shaders asíncronos, anisotrópico 16×) al máximo que admite la pantalla. Hace una copia de cada archivo y omite el emulador que esté abierto.
- **Breath of the Wild (Eden):** español latinoamericano; resolución 1× con escalado FSR y precisión de GPU normal, solo para este juego (en el archivo propio del juego, cada valor necesita las marcas `\\default=false` y `\\use_global=false`; con una sola de ellas Eden lo ignora). Parches de rendimiento: **Instalar mod** en la ficha acepta el zip del parche (`exefs/*.pchtxt`), siempre que coincida con la versión del juego (la 1.9.0 usa el hash de compilación `CD57B23F…`). El juego va a 30 FPS y los 90 FPS no son posibles con el parche de 60 FPS, porque Eden emula una pantalla de 60 Hz.
- **Mod de botones de DualSense:** **Instalar mod** acepta el zip «BOTW DS4 UI Mod» (reemplaza el paquete de interfaz y las fuentes). El preset de ReShade «REVO» no sirve en Eden: ReShade es solo para Windows.
- **A Link Between Worlds (Azahar):** idioma de la consola 3DS en español y pantalla grande con la otra pequeña (las dos visibles) (la disposición se guarda en la sección `[Layout]` de `qt-config.ini`). En la Deck, **L4** alterna entre pantalla superior e inferior y **R4** cambia la disposición (layout de Steam Input propio, asignado al agregar el juego a Steam).

## Mario Kart Wii (WiiCompiled)

- **Instalación propia:** Agregar juegos → Preparar Mario Kart Wii (imagen PAL limpia RMCP01, unos 20 GB temporales).
- **Actualizaciones:** si WiiCompiled está administrado por Quiver, **Actualizaciones → Actualizar aquí** descarga el setup nuevo (SHA-256 verificado), reinstala el juego con la imagen de la biblioteca dentro del SDK de KDE y restaura el setup anterior si algo falla. No hace falta abrir Quiver.

## Steam

- **Accesos y mandos:** al agregar un juego se guarda el acceso con el layout de gamepad para todos los tipos de mando (Steam Deck, DualSense, DualShock, Xbox, Switch Pro, genérico). Se escribe con Steam cerrado y siempre con copia de seguridad.
- **Arte:** la carátula de la biblioteca es el retrato que Steam ya tiene para cada acceso (por ejemplo el del plugin SteamGridDB de Decky), y la ficha muestra su fondo y logotipo como banner. **Arte de Steam** (ficha) y **Completar arte de todos los accesos de Steam** (Ajustes) buscan lo que falta con una clave API propia de SteamGridDB, sin reemplazar nada existente.

## Revertir

Cada cambio de ajustes deja una copia fechada junto al archivo original (`*.deck-library-AAAAMMDD-HHMMSS.bak`, `.orig` para el código de los kits y `grid/.deck-library-backups` para el arte). Los accesos de Steam y los layouts guardan su copia en la carpeta de configuración de Steam.

## Fuentes vigentes (0.15)

El antiguo repositorio de listas de Quiver quedó obsoleto; la app consulta también su API paginada actual (apps y release-status) y une los registros por repositorio. La fecha de incorporación al catálogo y la fecha de release son campos distintos. La lista independiente de Sebastrion aporta otros enlaces a proyectos y el índice incluido con Deck Library conserva una copia factual como respaldo. Los assets se consultan directamente en la release del proyecto al instalar. No se ejecutan scripts obtenidos de los catálogos para descubrir instalaciones.

## Paquetes e instalación automática (0.19)

La instalación identifica familias de paquetes en la publicación oficial, sin ejecutar comandos recibidos del catálogo:

| Familia | Proceso |
| --- | --- |
| AppImage o binario Linux x86_64 | Descargar, verificar, registrar y ejecutar. Se prefiere una build SteamOS cuando existe. |
| ZIP, tar.gz, tar.xz, tar.bz2 o tar.zst de Linux | Extraer con validación de rutas y enlaces; identificar el ejecutable. tar.zst requiere zstd. |
| Windows portable, ZIP o EXE x64 o x86 | Identificar un ejecutable PE; usar Proton con un entorno persistente separado por port. Se prefiere Linux si está disponible. |
| ROM/disco + extracción o compilación conocida | Usar la integración específica: WiiCompiled, Project 2099, kits de PS1, OpenPete, CTR, zelda3, Minish Cap y Wind Waker HD. |
| Setup/MSI desconocido, Flatpak empaquetado o solo código fuente | Mostrar que requiere una integración específica. No tratarlo como un juego portable ni ejecutar pasos inventados. |

En la ficha del catálogo se muestra el tipo de instalación y el archivo de la release. La elección genérica se probó también contra nombres reales publicados por Zelda64Recomp, Shipwright, sm64coopdx, 2Ship y EdgeOfTimeRecomp; eso valida la selección del paquete, no el arranque de todos esos juegos. No hay una medición de cobertura que permita afirmar que todos o la mayoría del catálogo están probados.

Al actualizar se conserva una copia completa de la carpeta anterior y se transfieren las carpetas habituales `UserData`, `saves` y `savegames` (con sus variantes de mayúsculas). Los datos guardados por el propio juego en XDG o en su entorno de Proton mantienen su ubicación. Los mods, ROMs generadas, configuraciones y carpetas con otros nombres siguen en el respaldo: cada port que necesite migrarlos requiere una regla específica. Un fallo al mover la nueva versión restaura la carpeta anterior.

Project 2099 tiene su propio proceso: el instalador usa un entorno de Proton actual separado del usado para jugar; se muestran los bytes y archivos escritos durante la instalación y se detectan cinco minutos sin actividad. Los diagnósticos de Wine se guardan en el registro y no reemplazan el estado de progreso. Se puede cancelar el instalador sin cerrar otros entornos de Wine.

## PortIntegration como fuente adicional (0.19.3)

Se consulta el catálogo factual de [SSLabs / PortIntegration](https://github.com/Samuel-SSLabs/Port-Integration), leyendo únicamente los literales JSON `PORTS_DATABASE` y `LOCAL_COVERS_MANIFEST` de su `app.js`. No se ejecuta JavaScript ni se utilizan su proxy, sus scripts de instalación o comandos indicados por la lista. Se importan nombres, repositorios, plataforma y enlaces a carátulas del manifiesto. Los nombres de ruta de las imágenes se validan y los enlaces quedan dentro del repositorio de la fuente.

Se fusiona por repositorio, ignorando mayúsculas: las identidades y categorías que ya existen conservan su precedencia; las imágenes faltantes se completan. El filtro de fuentes permite elegir **PortIntegration**. En los detalles se presenta su estado declarado, sin convertir «jugable» en verificación de Deck Library. Su fecha de edición no se usa como fecha de incorporación ni como fecha de release. La versión instalable se consulta directamente al repositorio original cuando se instala. Si la fuente falla o cambia de formato, siguen disponibles las demás listas y la caché.

Este sitio mantiene una lista propia; su [escáner](https://github.com/Samuel-SSLabs/Port-Integration/blob/main/scripts/discover-ports.js) consulta GitHub por temas y palabras clave, filtra candidatos y genera cambios mediante un workflow diario. No es un registro exhaustivo y puede incluir proyectos experimentales, herramientas o etiquetas de estado imprecisas. La presencia en cualquier catálogo no demuestra que haya un paquete compatible o que el juego funcione en la Deck.

## Asociación de originales y preparación (0.19.6)

Un original y su port se muestran en una sola ficha, conservando ambas entradas y todos los archivos. **ROM encontrada** significa que el archivo original sigue disponible; no certifica que su región, versión o formato sean compatibles con el instalador. La asociación usa identidad y plataforma cuando están disponibles y evita unir títulos ambiguos de plataformas distintas. **ROMs asociadas → Abrir ficha de la ROM** abre la ficha de la versión emulada; **Mostrar ROM en la biblioteca** deshace la agrupación. **Ocultar ROM duplicada** vuelve a agruparla con el port. El filtro Emulador permite ver los originales. Volver a la biblioteca mantiene el foco en el port asociado.

Los adaptadores integrados ofrecen un selector cuando falta una ROM, disco o BIOS. Se valida el SHA-1, SHA-256 o serial que exige el adaptador antes de guardar la selección en los datos privados. La ruta se conserva para futuras actualizaciones. Los proyectos sin adaptador muestran si usan su propio asistente o una preparación manual; elegir un archivo arbitrario no sustituye un proceso de importación desconocido.

La ficha ofrece **Instalar con Proton** cuando hay un paquete Windows portable, incluso como alternativa a Linux. Se reconocen EXE sin etiqueta de plataforma, ZIP sin esa etiqueta cuando el catálogo revisado identifica Windows, y paquetes x86 de 32 bits para Proton. Los paquetes ARM y los instaladores genéricos siguen excluidos. Los ZIP con separadores de Windows se normalizan antes de validar las rutas. Los tar de Linux admiten bibliotecas enlazadas dentro del paquete y rechazan enlaces que salgan de su carpeta, también después de quitar la carpeta envolvente.

### Proyectos revisados el 21 de octubre de 2026

Se consultaron las publicaciones y las instrucciones originales. Identificar o instalar un paquete no valida jugabilidad, rendimiento ni mandos.

| Juego y proyecto | Paquete elegido | Preparación de los originales |
| --- | --- | --- |
| [God of War III / SpartanPort](https://github.com/FelipePrado0/SpartanPort/releases) | AppImage Linux | Su asistente pide la carpeta extraída del juego de PS4. |
| [inFAMOUS Second Son](https://github.com/HayatoG/iss_pc/releases) | tar.gz Linux; ejecutable principal identificado | Su asistente usa la carpeta de PS4 CUSA00223 con update 1.07. |
| [Sonic Unleashed](https://github.com/hedge-dev/UnleashedRecomp/releases) | ZIP Windows con Proton; el bundle Flatpak necesita otra integración | Su importador prepara los datos de Xbox 360. |
| [Smash 64 / BattleShip](https://github.com/JRickey/BattleShip/releases) | AppImage Linux general, antes que la variante japonesa | Asistente del port; ROM compatible de Nintendo 64. |
| [Smash Melee](https://github.com/999sian/melee-pc/releases) | AppImage Linux x86_64 | Asistente del port; disco de GameCube. |
| [Smash Ultimate](https://github.com/Denkishi/ssbu-recomp/releases) | El release del runtime se identifica como herramienta, no como juego portable | Instalador completo del proyecto; preparación manual. |
| [Time Crisis](https://github.com/spacestate1/namco22-decompile/releases) | Su AppImage específico; no el primer AppImage del release multijuego | `timecris.zip` de MAME 0.271 o posterior, junto al ejecutable, en `roms` o en Descargas; el port valida los archivos. |
| [LOTR / Athelas](https://github.com/Shagg88/Athelas/releases) | ZIP Windows sin etiqueta de plataforma, con Proton; `Athelas.exe` | Su asistente permite seleccionar los discos o archivos de Xbox para Two Towers y Return of the King, o la carpeta del juego de PC. |
| [The Two Towers Recompiled](https://github.com/Gumpolas/TooTawersRecomp/releases) | tar.gz Linux; se identifica `TwoTowers.sh` | Su lanzador pide una ISO/XISO USA de Xbox: usa zenity y, como alternativa, un terminal con `twotowers-setup`. |
| [Crash Bandicoot Launcher](https://github.com/Matteo842/CrashBandicoot-Launcher/releases) | Binario Linux | Asistente propio; CHD o CUE y BIN. |
| [Crash Warped Recompiled](https://github.com/alexbeavs-ps1-ports/crash-bandicoot-3-warped-recomp/releases) | ZIP Linux | Asistente del kit, disco y BIOS; compilación dentro del SDK de KDE. |
| [CTR Native](https://github.com/CTR-tools/ctr-native/releases) | ZIP Windows x86 con Proton | Adaptador integrado: BIN crudo del disco SCUS-94426 en `assets/ctr-u.bin`. |

## Instalación y preparación: revisión 0.19.8

La selección cubre AppImage, ejecutables Linux, paquetes tar/ZIP y Windows portable con Proton. Los ZIP sin etiqueta de sistema ya no se rechazan por su nombre: se inspeccionan sus ejecutables antes de elegir Linux o Proton. Los paquetes 7z/RAR se leen mediante 7-Zip instalado localmente; sus miembros se validan y se escriben como archivos normales, sin ejecutar instrucciones del catálogo. Instalar un paquete no acredita que el juego sea jugable ni garantiza FPS.

| Proyecto revisado | Ruta ofrecida |
| --- | --- |
| [Bayonetta 2 / B2recomp](https://github.com/K0NL/B2recomp/releases/tag/linux-test-5) | Constructor Linux de prueba, preferido al ZIP Windows. Selector de carpeta con `exefs/main` y `romfs` de v1.2. El Python incluido ejecuta `scripts/setup.py --dump … --jobs …`, con hasta cuatro trabajos y salida de progreso. La versión del dump la valida el constructor. No acepta NSP/XCI cifrados. Tras generar `build-linux/game_native`, el acceso inicia `scripts/play.sh`. |
| [BLACK XBERecomp](https://github.com/TGP482/BLACK-XBERecomp/releases/tag/V2) | `BLACK.exe` con Proton. Deck Library permite elegir una ISO/XISO o una carpeta extraída y prepara `assets`, conservando el original. El port comprueba su versión y compila al iniciarse. |
| [Black Definitive HD](https://github.com/euspring1/BlackDefinitiveHDPC/releases/tag/V1.3) | `black.exe` con Proton. Selector de carpeta extraída; verifica el SHA-256 NTSC-U publicado de `default.xbe` y copia los originales junto al port, sin reemplazar archivos distintos. |
| [BLACK PC](https://github.com/Spark198rus/black-pc) | Paquete Windows de 32 bits con Proton; preparación manual según su distribución `game` / `port`. |
| [BLACK 2006 Recomp](https://github.com/portingpete/Black-2006-Recomp) | Constructor con dependencias de compilación específicas, todavía sin automatización de ese entorno. La ficha muestra requisitos antes de ofrecer una instalación de juego. |
| [LittleBigPlanet 3](https://github.com/TheNIKITO/LittleBigPlanet-3---PC) | El proyecto consultado no publica un paquete listo y documenta limitaciones de arranque. Se muestra como código fuente con requisitos, sin prometer una instalación jugable. |

Bayonetta 2 conserva configuración, caché y partidas al actualizar. El juego generado se reconstruye con la nueva fuente, en vez de presentar un ejecutable viejo como actualizado. La compilación integrada puede cancelarse; solo se marca lista al encontrar el ejecutable final. Si faltan originales, la biblioteca muestra **Preparar** en lugar de **Jugar**. Los instaladores de formatos no integrados, paquetes sin ejecutable y proyectos con dependencias especiales siguen necesitando un adaptador; la app debe mostrarlo sin llamar a todo «incompatible».

## Eliminación de ports

El botón rojo **Eliminar**, en la cabecera del juego, ofrece dos opciones. **Solo de la biblioteca** oculta el juego sin tocar archivos, partidas ni su acceso de Steam; se recupera en **Herramientas → Juegos ocultos** y no reaparece al volver a detectar juegos. **Juego y datos** muestra las rutas que se van a borrar y pide una segunda confirmación. Las partidas y configuraciones dentro de esas rutas también se eliminan; los originales y otros datos externos se conservan.

Para ports administrados por Deck Library se incluyen la instalación, el entorno privado de Proton, las copias anteriores identificadas y los registros y respaldos propios del juego. La acción **Eliminar completamente** sigue disponible en la ficha del catálogo. También se admite eliminar una carpeta exclusiva de port dentro de las rutas configuradas, una instancia verificada de Prism Launcher o los archivos de una ROM local. Los datos compartidos del emulador, NAND y partidas fuera de las rutas indicadas se conservan. Las instalaciones sin una carpeta verificable y los formatos que requieren varios archivos, como listas M3U, se gestionan desde su lanzador; siempre se pueden quitar solo de la biblioteca.

La eliminación se bloquea si el juego está abierto, si cambió la instalación o si una ruta apunta fuera de las carpetas administradas. El acceso directo, sus imágenes y controles se quitan de Steam al cerrar el cliente. **Desinstalar** conserva su comportamiento anterior: mueve la instalación a una carpeta recuperable.

## Broken Bond en Steam Deck

La versión 2.5 del [port de Auremana](https://github.com/Auremana666/Naruto-The-Broken-Bond-PC-Port#steam-deck) incorpora correcciones de carga de shaders bajo Proton. Al preparar una instalación nueva, Deck Library aplica una base de 720p, objetivo de 60 FPS, MSAA desactivado y mando SDL, con respaldo de la configuración. Acepta una ISO de Xbox 360 o una carpeta extraída con `default.xex`; la copia extraída permite reutilizar datos ya preparados sin reconstruir una ISO. Los cambios personales posteriores se conservan al actualizar.

Las instalaciones del recomp original de jorjbarbosa ofrecen **Corregir pantalla negra** al abrir la ficha. La reparación descarga el port compatible, conserva las partidas y mantiene el identificador de la biblioteca, el acceso directo de Steam, la carátula y los controles. Si falla el cambio de carpeta, recupera la instalación y los registros anteriores. Requiere Proton 11 instalado y el juego cerrado. La configuración anterior queda respaldada, y la ficha permite restablecer el ajuste recomendado.

Se comprobó imagen y navegación en una Steam Deck OLED; una prueba de uso confirmó controles y fluidez. También se observaron pausas en cinemáticas: no se consideran resueltas ni se atribuyen únicamente a la primera ejecución. La lista `pipeline-guard.txt` se conserva al actualizar para evitar repetir shaders que provocaron cierres; omitirlos puede dejar efectos sin dibujar. El objetivo de 60 FPS no representa una medición sostenida de rendimiento.

## Selección y limpieza de ISO

El selector de ISO comienza filtrado por `*.iso`, sin distinguir mayúsculas, y conserva las carpetas visibles para navegar. **Todos los archivos** permite cambiar el filtro. Conservar o eliminar una ISO después de prepararla cierra la pantalla de limpieza y vuelve a Biblioteca con la navegación habilitada; las siguientes actualizaciones automáticas esperan hasta completar esa decisión.

El lanzador reintenta hasta seis veces los cierres con código 3 solo si el port dejó registrado un shader nuevo en `pipeline-guard-pending.txt`. Si el registro no cambia, no es válido o corresponde a otro error, informa el fallo. Ambos registros de shaders se conservan al actualizar. La pantalla inicial adicional del port se desactiva en el ajuste recomendado para acelerar el acceso al juego.


## Variantes y pruebas de juego (1.3.5)

El catálogo separa **Integración revisada** (se revisó la instalación), el porcentaje orientativo y la **prueba de juego**. Solo el repositorio y la versión exactos de `catalog/validated-games.json` reciben la marca verde de juego verificado. Otra versión, una versión sin identificar y otro fork conservan estados distintos; no se hereda una prueba por el título, por ser más nuevo, por instalarse correctamente o por verificar el SHA-256. Las condiciones y limitaciones de la prueba siguen siendo parte del resultado: la marca no certifica todos los ajustes, versiones de Proton ni recorridos del juego, y no es una certificación de Valve.

**Comparar variantes** aparece dentro de la ficha del port. Si hay una prueba de otro repositorio, **Ver variante probada** abre ese proyecto. La ficha identifica las variantes instaladas y sus versiones. Las instalaciones administradas de Broken Bond pueden usar **Cambiar a la variante probada**, con la reparación existente y sus respaldos; las instalaciones externas no se migran automáticamente. Instalar otra variante genérica conserva la anterior y no transfiere partidas automáticamente.

`catalog/port-variants.json` agrupa explícitamente Broken Bond, las cuatro variantes de BLACK y las dos de CTR. También se agrupan proyectos con el mismo `game_title` explícito y la misma plataforma original conocida. No se agrupa solo por parecido de nombres ni se consultan forks remotos en cada tarjeta. Si ninguna variante tiene pruebas de gameplay, todas siguen sin validar y no se elige una ganadora por la puntuación del catálogo.

Las incidencias conocidas del registro incluyen sus versiones observadas: el aviso de pantalla negra del recomp anterior de Broken Bond se limita a `0.1.0-beta` bajo Proton 11; no se atribuye automáticamente a versiones futuras. Esas instalaciones se pueden cancelar antes de descargar. La variante de Auremana probada es `2.5`; conserva las pausas en cinemáticas y las limitaciones de shaders documentadas.

La detección de Quiver lee el repositorio del registro `apps.json` por `folderName` y la versión de `version.txt`. Conserva el ejecutable elegido y la identidad de la biblioteca. Sin esos datos no se supone el repositorio a partir del nombre de una carpeta: una coincidencia por nombre se presenta como una instalación sin identificar, sin concederle la marca de la variante mostrada en el catálogo.

### Archivos de Switch durante la instalación (1.4.4)

Savage Wind y Bayonetta 2 abren directamente el formulario de archivos cuando faltan originales. **Usar carpeta ya extraída** acepta la carpeta con `exefs/main` y `romfs` (o cualquiera de esas subcarpetas); no pide claves. La otra opción convierte un XCI/NSP propio, con actualización separada si hace falta, usando el conversor incluido. No hay un paso de preparar la herramienta.

La carpeta se guarda como entrada del port. Bayonetta 2 continúa con su constructor. Savage Wind recibe la carpeta en su constructor de primer inicio mediante la interfaz `SAVAGEWIND_LAUNCHER_SETUP` del proyecto; el propio port verifica versión y compila. La estructura de carpetas por sí sola no confirma el juego ni su revisión. Después de generarse los datos y la biblioteca del juego, Deck Library no vuelve a forzar el asistente. La integración no incluye ROMs, claves ni firmware.
