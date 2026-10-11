# Deck Library — guía para Steam Deck

![Interfaz con una biblioteca de ejemplo](assets/screenshot.png)

Agregá ports, aplicaciones y juegos emulados a Steam desde una sola ventana.

**GTA IV:** buscar lo instalado, abrir la ficha del juego y elegir **Ver arreglo → Aplicar arreglo de GTA IV**. Instala FusionFix 4.0.5 y los ajustes de DXVK confirmados en esta Deck, con respaldo y restauración. No abre el juego. [Instructivo y detalles](docs/GTAIV.md).

**DMC3 Crimson:** el [arreglo de arranque desde Steam](docs/DMC3-CRIMSON.md) está documentado con su wrapper, compatibilidad de la DLL, respaldo y requisitos para un futuro botón. Se comprobó el arranque local; aún no hay instalador de Crimson integrado en la app.

**Spider-Man: Shattered Dimensions:** la [guía de configuración en Steam Deck](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) registra Proton, audio, voces y controles confirmados en esta instalación. Todavía no es un preset aplicable desde la app.

## Ports de Zelda y ajustes máximos

El catálogo incluye tres ports nativos que se preparan con **Configurar**:

- **The Minish Cap** (Project Picori): la ROM de GBA se reconoce por SHA-1 en `~/Emulation/roms/gba`, con cualquier nombre de archivo (USA, Europa o Japón).
- **A Link to the Past** (`snesrev/zelda3`): se compila dentro del SDK de KDE a partir de la ROM USA 1.0 de `~/Emulation/roms/snes` (se quita el encabezado de copiador si lo tiene). Queda en pantalla completa, 16:10 y sin límite de sprites.
- **The Wind Waker HD** (`ZeldaWWHDRecomp`): usa la imagen de Wii U de la biblioteca. Las claves se leen de `keys.txt` de EmuDeck, se escriben en archivos temporales privados solo durante la preparación y se borran después. Nunca se muestran ni se guardan.

A Link Between Worlds, Breath of the Wild y Skyward Sword no tienen port nativo y siguen con emulador.

**Ajustes → Aplicar ajustes máximos para Steam Deck** deja DuckStation (5×, PGXP), Dolphin (3×, anisotrópico 16×), Azahar (3×, pantalla única con F9/F10 para alternar, shaders asíncronos) y Eden (shaders asíncronos, anisotrópico 16×) en lo máximo que admite la pantalla de 1280×800. Se hace un respaldo de cada archivo y se omite el emulador que esté abierto.

### Español, pantalla y mods por juego

- **Breath of the Wild** (Eden): idioma español latinoamericano y, solo para este juego, resolución 1× con escalado FSR y precisión de GPU normal, para evitar el desenfoque de bajar 1,5× a la pantalla. El juego va fijo a 30 FPS.
- **A Link Between Worlds** (Azahar): idioma de la consola 3DS en español, resolución 3× (la pantalla superior ocupa la altura de la Deck) y **una sola pantalla**. En la Deck, **L4** alterna entre pantalla superior e inferior (F9) y **R4** cambia la disposición (F10), mediante un layout de Steam Input propio para los juegos de 3DS.
- **Wind Waker HD**: español, 16:10, imagen del GamePad en un recuadro dentro de la misma ventana, interpolación de cuadros (hasta la frecuencia de la pantalla), FXAA y anisotrópico. Los cambios se guardan como variables `WWHD_` del acceso.
- **Minish Cap** (Picori): español con la ROM europea, escala interna 5× (1200×800), pantalla completa y reloj de 90 FPS.
- **A Link to the Past**: el juego original no tiene versión en español. Con la traducción de aficionados «Re-Traducción F01h» (parche UPS sobre la ROM USA; el resultado tiene el SHA-1 `461FCBD7…` que el port reconoce), **Configurar** extrae los textos y deja `Language = es`. Los diálogos quedan en español; los rótulos del menú (ITEM, EQUIPMENT…) siguen en inglés porque el port no importa esos gráficos.
- **Spider-Man 1 y 2** (kits PSX): supersampling 4×, PGXP y los mods oficiales del kit (PGXP, carga rápida, CD 2×), más un mod propio de Deck Library con **interpolación de cuadros a la frecuencia de la pantalla** (solo presentación: mezcla cuadros terminados, la lógica y el audio siguen a la velocidad original; el movimiento rápido puede dejar estela) y **widescreen 16:10** (experimental: las pantallas 2D y los videos siguen en 4:3). Usa la interfaz de plugins del propio framework; requiere recompilar el kit (botón «Mejorar rendimiento»).
- **Breath of the Wild** en Eden: el parche «60 FPS (1.9.0)» de Nexus Mods se instala en la carpeta de mods del juego (exefs, hash de compilación CD57B23F…). 90 FPS no es posible con ese parche: Eden emula una pantalla de 60 Hz.

### Arte de Steam

En la ficha de un juego con acceso en Steam, **Arte de Steam** busca en SteamGridDB (con la misma clave API de **Ajustes**) la portada vertical, la horizontal, el fondo, el logotipo y el ícono, con las mismas rutas de archivo que usa el plugin SteamGridDB de Decky. Lo que ya existe se muestra marcado y no se reemplaza salvo que se elija otra imagen; cada archivo reemplazado deja una copia en `grid/.deck-library-backups`. **Completar lo que falta** elige automáticamente la primera imagen de cada espacio vacío. Las imágenes elegidas se guardan al cerrar Steam, junto con el resto de los cambios pendientes.

**Ajustes → Completar arte de todos los accesos de Steam** hace lo mismo para toda la biblioteca de una vez: solo llena los espacios vacíos, informa por juego qué se agregó y qué no se encontró, y ofrece reiniciar Steam para guardar. Hace falta una clave API propia de SteamGridDB: la clave del plugin de Decky va embebida en ese plugin y su autor advierte que usarla en otros proyectos provoca el bloqueo.

### Diseño, movimiento y actualizaciones propias

- **Interfaz:** barra lateral con íconos, tarjetas de juego con el nombre y la plataforma sobre un degradado, marca de «ya en Steam», controles más planos y un único color de acento. Foco visible en todos los controles (para usar el mando con Steam Input) y objetivos táctiles de al menos 36 px.
- **Movimiento:** transiciones de 150–300 ms con salida suave, aparición escalonada de las tarjetas al abrir la biblioteca o cambiar de filtro, deslizamiento entre la biblioteca y la ficha de un juego, y avisos breves al guardar cambios. **Ajustes → Animaciones y transiciones** lo desactiva por completo.
- **Ajustes detectados:** el diálogo de ajustes de cada juego empieza con **Ajustes actuales**, leídos del archivo propio del emulador (con fecha de modificación) o de los valores globales si el juego no tiene uno, antes de los perfiles recomendados del catálogo.
- **Clave de SteamGridDB:** Ajustes explica cómo conseguirla (iniciar sesión en steamgriddb.com, Perfil → Preferencias → API), permite mostrarla u ocultarla y tiene un botón **Probar clave**.
- **Mario Kart Wii (WiiCompiled):** la pestaña **Actualizaciones** ofrece **Actualizar aquí** cuando hay una versión nueva del setup oficial. Descarga el AppImage, verifica su SHA-256 con el valor que publica GitHub, vuelve a instalar el juego con la imagen PAL de la biblioteca (necesita unos 20 GB libres) y restaura el setup anterior si algo falla. No hace falta abrir Quiver.

## Instalación

1. Copiar y extraer `DeckLibrary-0.4.0.tar.gz` en modo Escritorio.
2. Abrir la carpeta y hacer doble clic en **Instalar.sh**. Elegir **Ejecutar** cuando Dolphin pregunte.
3. Se instala la aplicación y se abre. También queda **Deck Library** en el escritorio y en el menú de aplicaciones.

Si Dolphin abre el archivo como texto, abrir una terminal en esa carpeta y ejecutar `python3 install.py --desktop`. Necesita Python 3.11+ y GTK 3/PyGObject; se verificaron en la Deck utilizada. No necesita sudo ni pip.

## Primer inicio

![Asistente inicial de Deck Library](assets/welcome.png)

Se abre un asistente de cuatro pasos: **Bienvenida → Detectar → Carátulas → Listo para Steam**. Busca EmuDeck, emuladores, ports e instancias de Prism en segundo plano. Revisar los juegos encontrados y agregar una carpeta si falta algo. Elegir el proveedor de carátulas y abrir la biblioteca. Se puede repetirlo desde **Ajustes**.

## Tu biblioteca

Las carátulas tienen formato vertical 2:3. Tocá una para abrir su ficha: **Jugar** y **Agregar a Steam** son las acciones principales. Debajo están los presets, el contenido de Switch y los controles de Minecraft cuando corresponden. Rutas, comandos y el interruptor de mods quedan en **Opciones avanzadas**.

Para agregar varios juegos, tocar **Seleccionar**, marcar las carátulas y usar **Agregar a Steam** en la barra inferior. Si Steam está abierto, elegir **Reiniciar Steam y guardar** después de cerrar el juego en uso. Los accesos aparecen en **No Steam** en modo Juego.

**Agregar juegos** ofrece tres caminos: buscar lo instalado, elegir una ROM/app o preparar Mario Kart Wii. En **Ajustes → Instalaciones y carpetas** se pueden corregir las rutas de emuladores, ports, Prism y bibliotecas en microSD. Los ejecutables Windows necesitan un launcher de Wine/Proton configurado.

## Carátulas automáticas

**Automático** usa SteamGridDB si agregaste una clave personal; si no, busca carátulas en Libretro para las consolas compatibles y una imagen del juego en Wikipedia. Funciona sin crear una cuenta. Cuando una coincidencia es dudosa, se conserva una tarjeta de título para que elijas la imagen. Wikipedia puede devolver arte representativo de un artículo compartido por varias ediciones, en vez de la caja exacta.

Para carátulas verticales de la comunidad, elegir **SteamGridDB** en el asistente o en **Ajustes** y agregar una [clave API personal](https://www.steamgriddb.com/profile/preferences/api). Esta integración requiere una clave válida; no se incluye una clave compartida en el paquete.

En la ficha, **Cambiar carátula** permite buscar por nombre, elegir entre los resultados o usar **Elegir imagen local**. El origen de cada descarga queda visible. Las imágenes y la clave se guardan solamente en esta Deck y no se incluyen al exportar presets o feedback. Las consultas envían el nombre del juego al proveedor. Sin conexión, los juegos y las carátulas ya guardadas siguen disponibles.

Hay transiciones entre pantallas y pasos del asistente, respuesta visual al pasar por las carátulas e indicadores durante las búsquedas. Se pueden desactivar las animaciones en **Ajustes**.

## Mods y partidas

En Switch, **Opciones avanzadas** permite activar **Usar mods instalados en Eden**. Desactivarlo prepara un perfil sin mods que conserva la ubicación de partidas, NAND y controles. No borra mods ni cambia la configuración principal. Los nuevos juegos de Switch usan los mods instalados por defecto; se pueden desactivar para comparar el arranque. Las actualizaciones y los DLC instalados siguen disponibles.

## Qué se comparte

El paquete incluye solamente la app, su código MIT, documentación y pruebas. **Cada persona aporta sus juegos y sus emuladores ya instalados.** No incluye ROMs, claves, firmware, cuentas, partidas ni mods. El asistente opcional puede preparar WiiCompiled usando una imagen propia y el setup oficial; también reconoce una instalación existente.

Steam se modifica cuando está cerrado, conservando los demás accesos. Se crea un backup junto a `shortcuts.vdf`. La app guarda su biblioteca y registros en `~/.local/share/deck-library`; no publiques esa carpeta.

## Estado de esta versión

Versión **0.7.0**. Los resultados de las pruebas están en [docs/VALIDATION.md](docs/VALIDATION.md). El funcionamiento de cada juego depende de su emulador y configuración. El instalador puede volver a ejecutarse para actualizar la app sin borrar la biblioteca.

Código y versiones descargables: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library). Para información técnica, consultar [README.md](README.md).

## Funciones de biblioteca y presets

- **Carátulas** como vista inicial; se puede cambiar a lista y elegir una imagen local. Se aprovechan imágenes existentes de Steam/Quiver/Prism cuando se encuentran; donde falta arte se muestra una tarjeta de título.
- **Ajustes → Instalaciones y carpetas** detecta EmuDeck y permite agregar carpetas de ROMs/ports, instalaciones de Quiver, Prism y WiiCompiled, y elegir programas de emuladores que no se detectaron.
- Las **instancias de Prism Launcher** aparecen individualmente para agregarlas a Steam. La ficha ofrece un layout recomendado de teclado/ratón y abre los controles de Steam; la selección del layout se hace allí.
- **Preparar Mario Kart Wii** pide una imagen PAL limpia RMCP01, usa el setup oficial 0.2.33, instala el SDK si falta, recompila y aplica la base nítida confirmada. Puede tardar varios minutos y necesita Internet y unos 20 GB temporales. Trabaja en una instalación propia, sin sobrescribir otra que ya funcione. Se puede cancelar y retomar una instalación incompleta.
- En Switch, **Base, updates y mods** muestra contenido, versión detectada por Eden y qué NSP está registrado en NAND. Permite elegir una base faltante, instalar updates/DLC propios y mods ZIP LayeredFS. Que un archivo esté disponible en una carpeta no significa que esté instalado en NAND. La versión base puede necesitar consultarse en Eden si no se identifica.
- **Ajustes recomendados** permite aplicar, respaldar, restaurar, importar/exportar JSON y guardar feedback para compartir. Hay siete perfiles iniciales con su estado de prueba. Algunos son propuestas; no todos están validados jugando.

Para probar presets con otra persona: compartir este paquete; esa persona abre el juego, elige **Ajustes recomendados**, aplica el perfil y usa **Exportar comentarios**. Puede enviar el JSON de comentarios y, si cambió algo, exportar sus ajustes. También se puede apuntar al mismo catálogo JSON de GitHub. Todavía no hay cuentas, sitio, base de datos ni subida automática de aportes.

El formato y sus límites están explicados en [docs/PRESETS.md](docs/PRESETS.md).

## Accesos existentes, carátulas y controles de Steam

**Actualizar** vuelve a buscar los ports instalados por Quiver, incluidas sus carpetas personalizadas, y los accesos **No Steam** de la cuenta activa. Si una instancia de Prism ya tiene un acceso, se vincula con él. La detección no incluye toda la biblioteca de juegos comprados en Steam.

En la ficha de un acceso existente, **Editar acceso de Steam** permite cambiar nombre, ejecutable, carpeta de inicio y opciones de lanzamiento. Se conserva su identificador, que mantiene asociados los controles, Proton y el arte. Para guardar estos cambios, Steam debe estar cerrado; la app ofrece guardar más tarde o reiniciarlo desde Escritorio.

La carátula elegida en Deck Library se copia al grid vertical de Steam al agregar o actualizar ese acceso, con copia de seguridad de la anterior. Elegir una nueva imagen no cambia Steam inmediatamente: usar **Agregar a Steam** para guardar también allí. No se generan automáticamente imágenes horizontales, fondos ni logotipos.

**Controles** muestra el perfil de Steam Input guardado localmente para la instancia de Minecraft, cuando está disponible, y abre los controles del acceso correcto. Los perfiles no descargados desde Steam Cloud o configurados en otra cuenta pueden no aparecer. No modifica las asignaciones automáticamente.

## Project-2099

**Agregar juegos → Preparar Project-2099** prepara una ISO de Xbox 360 (o un ZIP/7z que la contenga) con el instalador oficial Beta 4.1 fijado, bajo Proton. Las imágenes de PS3 se rechazan antes de descargar. Incluye un perfil propuesto de 720p / 60 FPS, accesos directos de Steam y detección de ports instalados. La validación de juego sigue pendiente. [Guía](docs/PROJECT2099.md).

## Novedades de la 0.4.0

- **Quitar de Steam:** en la ficha de cada juego y en la barra de selección. No toca juegos ni partidas; guarda un respaldo de la lista de accesos.
- **Mando:** los accesos nuevos reciben el layout de gamepad de Steam para DualSense, DualShock, Xbox y Switch Pro. Para un acceso existente, usar **Mando → Asignar layout** con Steam cerrado.
- **Actualizaciones:** página propia con avisos de Deck Library, ajustes recomendados y ports. La instalación automática de Deck Library se activa en esa página.
- **Ajustes del juego:** resolución, FPS, correcciones y rendimiento por juego (DuckStation, Dolphin, Eden y Prism), con respaldo y restauración.
- **Catálogo de ports:** reúne las listas de Quiver y GithubLauncher, recomendados (Spider-Man 1 y 2 de PSX) y repositorios propios, con íconos o portadas, categorías y filtros. Instala desde GitHub con verificación de integridad y avisa cuando hay una versión nueva. Los ports instalados con Quiver o GithubLauncher también se detectan.
- **Actualización automática:** Deck Library avisa cuando hay una versión nueva y se actualiza sola en modo Escritorio; se desactiva en la página Actualizaciones.
- **Ports que compilan en la Deck (por ejemplo Spider-Man 1 y 2 de PSX):** se ejecutan dentro del SDK de KDE de Flatpak, que Deck Library instala una vez con confirmación. No hace falta root ni tocar SteamOS. Hay que aportar el disco USA y la BIOS que pide cada kit.
- **Configuración automática de ports:** el botón **Configurar** del catálogo busca el disco en la biblioteca (por el serial interno) y la BIOS (por hash), y prepara Spider-Man 1 y 2, Spyro (OpenPete) y Crash Team Racing Turbocharged.
- **Biblioteca sin duplicados:** nuevo filtro por tipo (ports, emulador, instancias de Minecraft…) y la opción **Preferir ports**, que oculta la versión por emulador de un juego que ya tiene port.
