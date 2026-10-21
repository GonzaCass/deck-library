# Deck Library — guía para Steam Deck

![Interfaz con una biblioteca de ejemplo](assets/screenshot.png)

Agregá ports, aplicaciones y juegos emulados a Steam desde una sola ventana.

## Usar Deck Library directamente desde Steam

1. Instalá la app en modo Escritorio: descargá y extraé [la última versión](https://github.com/GonzaCass/deck-library/releases/latest), abrí la carpeta y ejecutá **Instalar.sh**. Completá el asistente inicial.
2. Dentro de Deck Library, abrí **Ajustes → Deck Library en Steam** y pulsá **Agregar a Steam**.
3. Si Steam está abierto, el acceso queda preparado y aparece el aviso de cambios pendientes. Terminá de agregar o editar lo que necesites, cerrá Steam una vez y esperá que desaparezca el aviso. El proceso en segundo plano guarda el acceso y los controles.
4. Volvé al modo Juego. Buscá **Deck Library** en la biblioteca de Steam y pulsá **Jugar**. Se abre directamente a pantalla completa, con la biblioteca, las carátulas y los ajustes.

La primera instalación se hace desde Escritorio; después podés abrir la app desde Steam. El acceso usa la versión nativa de Linux. Para navegar: trackpad derecho y gatillo derecho para puntero/clic; cruceta o stick para moverte; **A** para activar; **B** para volver; **X** para Tab. **Steam + X** abre el teclado en pantalla. La plantilla y la interfaz se comprobaron con pruebas automáticas; la navegación con el mando físico en modo Juego sigue pendiente de prueba.

### Agregar cada juego a Steam

Abrí la carátula del juego y pulsá el botón azul **Agregar a Steam**. Verás **Acceso pendiente** hasta que se guarde al cerrar Steam; después aparecerá **En Steam**. Para varios juegos, pulsá **Seleccionar**, marcá sus carátulas y usá **Agregar a Steam** en la barra inferior.

Después de guardar los accesos, cada juego se puede abrir directamente desde su propia ficha de Steam. Abrir Deck Library antes es opcional. También podés pulsar **Jugar** dentro de Deck Library: si ese juego ya tiene acceso, la app utiliza el de Steam y su configuración de mando.

Los cambios se acumulan: basta con cerrar Steam una vez al terminar. **Ver cambios** detalla las operaciones pendientes y permite descartarlas. La app y los juegos tienen accesos separados.

![Ficha del juego con biblioteca de ejemplo](assets/screenshot-game.png)

**GTA IV:** buscar lo instalado, abrir la ficha del juego y elegir **Mejoras para GTA IV → Aplicar arreglo de GTA IV**. Instala FusionFix 4.0.5 y los ajustes de DXVK confirmados en esta Deck, con respaldo y restauración. No abre el juego. [Instructivo y detalles](docs/GTAIV.md).

**DMC3 Crimson:** el [arreglo de arranque desde Steam](docs/DMC3-CRIMSON.md) está documentado con su wrapper, compatibilidad de la DLL, respaldo y requisitos para un futuro botón. Se comprobó el arranque local; aún no hay instalador de Crimson integrado en la app.

**Spider-Man: Shattered Dimensions:** la [guía de configuración en Steam Deck](docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md) registra Proton, audio, voces y controles confirmados en esta instalación. Todavía no es un preset aplicable desde la app.

Guía por juego (requisitos, qué deja ajustado la app, límites y cómo revertir): [docs/PORTS.md](docs/PORTS.md).

## Ports de Zelda y ajustes máximos

El catálogo incluye tres ports nativos que se preparan con **Configurar**:

- **The Minish Cap** (Project Picori): la ROM de GBA se reconoce por SHA-1 en `~/Emulation/roms/gba`, con cualquier nombre de archivo (USA, Europa o Japón).
- **A Link to the Past** (`snesrev/zelda3`): se compila dentro del SDK de KDE a partir de la ROM USA 1.0 de `~/Emulation/roms/snes` (se quita el encabezado de copiador si lo tiene). Queda en pantalla completa, 16:10 y sin límite de sprites.
- **The Wind Waker HD** (`ZeldaWWHDRecomp`): usa la imagen de Wii U de la biblioteca. Las claves se leen de `keys.txt` de EmuDeck, se escriben en archivos temporales privados solo durante la preparación y se borran después. Nunca se muestran ni se guardan.

A Link Between Worlds, Breath of the Wild y Skyward Sword no tienen port nativo y siguen con emulador.

**Ajustes → Aplicar ajustes máximos para Steam Deck** deja DuckStation (5×, PGXP), Dolphin (3×, anisotrópico 16×), Azahar (3×, pantalla grande con la otra pequeña, F9/F10 para alternar, shaders asíncronos) y Eden (shaders asíncronos, anisotrópico 16×) en lo máximo que admite la pantalla de 1280×800. Se hace un respaldo de cada archivo y se omite el emulador que esté abierto.

### Español, pantalla y mods por juego

- **Breath of the Wild** (Eden): idioma español latinoamericano y, solo para este juego, resolución 1× con escalado FSR y precisión de GPU normal, para evitar el desenfoque de bajar 1,5× a la pantalla. El juego va fijo a 30 FPS.
- **A Link Between Worlds** (Azahar): idioma de la consola 3DS en español, resolución 3× (la pantalla superior ocupa la altura de la Deck) y **pantalla grande con la otra pequeña** (las dos visibles). En la Deck, **L4** alterna entre pantalla superior e inferior (F9) y **R4** cambia la disposición (F10), mediante un layout de Steam Input propio para los juegos de 3DS.
- **Wind Waker HD**: español, 16:10, imagen del GamePad en un recuadro dentro de la misma ventana, interpolación de cuadros (hasta la frecuencia de la pantalla), FXAA y anisotrópico. Los cambios se guardan como variables `WWHD_` del acceso.
- **Minish Cap** (Picori): español con la ROM europea, escala interna 5× (1200×800), pantalla completa y reloj de 90 FPS.
- **A Link to the Past**: el juego original no tiene versión en español. Con la traducción de aficionados «Re-Traducción F01h» (parche UPS sobre la ROM USA; el resultado tiene el SHA-1 `461FCBD7…` que el port reconoce), **Configurar** extrae los textos y deja `Language = es`. Los diálogos quedan en español; los rótulos del menú (ITEM, EQUIPMENT…) siguen en inglés porque el port no importa esos gráficos.
- **Spider-Man 1 y 2** (kits PSX): supersampling 4× y PGXP; el **60 FPS real («Smooth 60»)** queda disponible pero apagado. El motor escala su lógica por el contador de vblanks, pero su bucle principal espera un vblank extra por cuadro y topa en 30 FPS; el kit se parchea para anular esa espera y acelerar la CPU emulada (8× y 10×). En una medición, los cambios de búfer por vblank pasaron de 0,50 a ~0,96 (juego 1) y de 0,34 a ~0,9 (juego 2); las escenas que saturan la GPU emulada pueden quedar por debajo. Con el 60 real activado el juego se sintió acelerado y con los sticks incontrolables, por eso no se aplica por defecto. Los mods de carga rápida y de CD no se activan (aceleraban todo el juego). Más la interpolación de cuadros y el widescreen 16:10 experimental del mod «Steam Deck display». Requiere recompilar el kit (botón «Mejorar rendimiento»).
- **Breath of the Wild** en Eden: el parche «60 FPS (1.9.0)» de Nexus Mods se instala en la carpeta de mods del juego (exefs, hash de compilación CD57B23F…). 90 FPS no es posible con ese parche: Eden emula una pantalla de 60 Hz.

### Arte de Steam

En la ficha de un juego con acceso en Steam, **Más opciones → Archivos y acceso de Steam → Carátulas de Steam** busca en SteamGridDB (con la misma clave API de **Ajustes**) la portada vertical, la horizontal, el fondo, el logotipo y el ícono, con las mismas rutas de archivo que usa el plugin SteamGridDB de Decky. Lo que ya existe se muestra marcado y no se reemplaza salvo que se elija otra imagen; cada archivo reemplazado deja una copia en `grid/.deck-library-backups`. **Completar lo que falta** elige automáticamente la primera imagen de cada espacio vacío. Las imágenes elegidas se guardan al cerrar Steam, junto con el resto de los cambios pendientes.

**Ajustes → Completar arte de todos los accesos de Steam** hace lo mismo para toda la biblioteca de una vez: solo llena los espacios vacíos, informa por juego qué se agregó y qué no se encontró, y deja los cambios preparados para guardarse al cerrar Steam. Hace falta una clave API propia de SteamGridDB: la clave del plugin de Decky va embebida en ese plugin y su autor advierte que usarla en otros proyectos provoca el bloqueo.

### Diseño, movimiento y actualizaciones propias

- **Interfaz:** navegación superior, carátulas verticales y una ficha con Jugar en verde, Steam en azul y ajustes en violeta. Elegí una tarjeta y pulsá **Aplicar ajustes**; seleccionar no escribe cambios. **Ver cambios** despliega los detalles técnicos. **Controles**, **Contenido** y **Ajustes manuales** abren pantallas con un botón para volver al juego. Importar, exportar, carátulas y archivos están en **Más opciones**.
- **Movimiento:** entrada de la ficha y de las tarjetas, transiciones entre tareas, despliegue de detalles, estados de botones y confirmaciones al guardar. Se desactiva desde **Ajustes → Carátulas y apariencia → Animaciones**.
- **Ajustes:** la vista previa compara valores del archivo del juego y distingue los perfiles pendientes de los que ya coinciden. Aplicar guarda un respaldo y **Deshacer** restaura la configuración anterior. La edición manual conserva los cambios sin guardar durante una actualización de carátulas o detección.
- **Clave de SteamGridDB:** Ajustes explica cómo conseguirla (iniciar sesión en steamgriddb.com, Perfil → Preferencias → API), permite mostrarla u ocultarla y tiene un botón **Probar clave**.
- **Mario Kart Wii (WiiCompiled):** la pestaña **Actualizaciones** ofrece **Actualizar aquí** cuando hay una versión nueva del setup oficial. Descarga el AppImage, verifica su SHA-256 con el valor que publica GitHub, vuelve a instalar el juego con la imagen PAL de la biblioteca (necesita unos 20 GB libres) y restaura el setup anterior si algo falla. No hace falta abrir Quiver.

## Instalación

1. Descargar `DeckLibrary-0.19.2.tar.gz` desde [la última versión publicada](https://github.com/GonzaCass/deck-library/releases/latest) y extraerlo en modo Escritorio.
2. Abrir la carpeta y hacer doble clic en **Instalar.sh**. Elegir **Ejecutar** cuando Dolphin pregunte.
3. Se instala la aplicación y se abre. También queda **Deck Library** en el escritorio y en el menú de aplicaciones.

Si Dolphin abre el archivo como texto, abrir una terminal en esa carpeta y ejecutar `python3 install.py --desktop`. Necesita Python 3.11+ y GTK 3/PyGObject; se verificaron en la Deck utilizada. No necesita sudo ni pip.

## Primer inicio

![Asistente inicial de Deck Library](assets/welcome.png)

Se abre un asistente de cuatro pasos: **Bienvenida → Detectar → Carátulas → Listo para Steam**. Busca EmuDeck, emuladores, ports e instancias de Prism en segundo plano. Revisar los juegos encontrados y agregar una carpeta si falta algo. Elegir el proveedor de carátulas y abrir la biblioteca. Se puede repetirlo desde **Ajustes**.

## Tu biblioteca

Las carátulas tienen formato vertical 2:3. Tocá una para abrir su ficha: **Jugar** y **Agregar a Steam** son las acciones principales. Debajo están las tarjetas de ajustes. **Controles**, **Contenido** y **Ajustes manuales** abren cada tarea; **Más opciones → Archivos y acceso de Steam** muestra rutas y comandos.

Para agregar varios juegos, tocar **Seleccionar**, marcar las carátulas y usar **Agregar a Steam** en la barra inferior. Si Steam está abierto, los cambios quedan preparados hasta que lo cierres una vez al terminar. Los accesos aparecen en **No Steam** en modo Juego.

**Catálogo de ports** abre directamente los ports disponibles para instalar. En **Ajustes → Instalaciones y carpetas** se pueden corregir las rutas de emuladores, ports, Prism y bibliotecas en microSD. Los ejecutables Windows necesitan un launcher de Wine/Proton configurado.

## Carátulas automáticas

**Automático** usa SteamGridDB si agregaste una clave personal; si no, busca carátulas en Libretro para las consolas compatibles y una imagen del juego en Wikipedia. Funciona sin crear una cuenta. Cuando una coincidencia es dudosa, se conserva una tarjeta de título para que elijas la imagen. Wikipedia puede devolver arte representativo de un artículo compartido por varias ediciones, en vez de la caja exacta.

Para carátulas verticales de la comunidad, elegir **SteamGridDB** en el asistente o en **Ajustes** y agregar una [clave API personal](https://www.steamgriddb.com/profile/preferences/api). Esta integración requiere una clave válida; no se incluye una clave compartida en el paquete.

En la ficha, **Cambiar carátula** permite buscar por nombre, elegir entre los resultados o usar **Elegir imagen local**. El origen de cada descarga queda visible. Las imágenes y la clave se guardan solamente en esta Deck y no se incluyen al exportar presets o feedback. Las consultas envían el nombre del juego al proveedor. Sin conexión, los juegos y las carátulas ya guardadas siguen disponibles.

Hay transiciones entre pantallas y pasos del asistente, respuesta visual al pasar por las carátulas e indicadores durante las búsquedas. Se pueden desactivar las animaciones en **Ajustes**.

## Mods y partidas

En Switch, **Contenido** permite activar **Usar los mods instalados**. Desactivarlo prepara un perfil sin mods que conserva la ubicación de partidas, NAND y controles. No borra mods ni cambia la configuración principal. Los nuevos juegos de Switch usan los mods instalados por defecto; se pueden desactivar para comparar el arranque. Las actualizaciones y los DLC instalados siguen disponibles.

## Qué se comparte

El paquete incluye solamente la app, su código MIT, documentación y pruebas. **Cada persona aporta sus juegos y sus emuladores ya instalados.** No incluye ROMs, claves, firmware, cuentas, partidas ni mods. El asistente opcional puede preparar WiiCompiled usando una imagen propia y el setup oficial; también reconoce una instalación existente.

Steam se modifica cuando está cerrado, conservando los demás accesos. Se crea un backup junto a `shortcuts.vdf`. La app guarda su biblioteca y registros en `~/.local/share/deck-library`; no publiques esa carpeta.

## Estado de esta versión

Versión **0.19.2**. Los resultados de las pruebas están en [docs/VALIDATION.md](docs/VALIDATION.md). El funcionamiento de cada juego depende de su emulador y configuración. El instalador puede volver a ejecutarse para actualizar la app sin borrar la biblioteca.

Código y versiones descargables: [GonzaCass/deck-library](https://github.com/GonzaCass/deck-library). Para información técnica, consultar [README.md](README.md).

## Funciones de biblioteca y presets

Los juegos de Switch sin un preset específico incluido o importado ofrecen tres opciones en **Ajustes recomendados**: **Switch — Equilibrado**, **Switch — Rendimiento** y **Switch — Compatibilidad**. Toman como referencia los cinco perfiles existentes: Vulkan, modo portátil, resolución 1×, varios núcleos, velocidad al 100% y caché de shaders. Equilibrado usa precisión GPU normal sin shaders/presentación asíncronos; Rendimiento activa ambos; Compatibilidad usa precisión alta y desactiva ambos. Requieren un Title ID detectado o completado en **Editar juego** y declaran Eden 0.2.1. Son propuestas **Para probar**, sin garantía de FPS.

Elegí una tarjeta, desplegá **Ver cambios** y pulsá **Aplicar ajustes** para escribir el perfil con respaldo. El juego se abre por separado con **Jugar**. Cerrá el emulador antes de aplicar otra configuración. **Deshacer** recupera el estado anterior a la última aplicación. Los perfiles específicos tienen prioridad y cada tarjeta muestra el estado de prueba declarado por su autor.

- **Carátulas** como vista inicial; se puede cambiar a lista y elegir una imagen local. Se aprovechan imágenes existentes de Steam/Quiver/Prism cuando se encuentran; donde falta arte se muestra una tarjeta de título.
- **Ajustes → Instalaciones y carpetas** detecta EmuDeck y permite agregar carpetas de ROMs/ports, instalaciones de Quiver, Prism y WiiCompiled, y elegir programas de emuladores que no se detectaron.
- Las **instancias de Prism Launcher** aparecen individualmente para agregarlas a Steam. La ficha ofrece un layout recomendado de teclado/ratón y abre los controles de Steam; la selección del layout se hace allí.
- **Preparar Mario Kart Wii** pide una imagen PAL limpia RMCP01, usa el setup oficial 0.2.33, instala el SDK si falta, recompila y aplica la base nítida confirmada. Puede tardar varios minutos y necesita Internet y unos 20 GB temporales. Trabaja en una instalación propia, sin sobrescribir otra que ya funcione. Se puede cancelar y retomar una instalación incompleta.
- En Switch, **Base, updates y mods** muestra contenido, versión detectada por Eden y qué NSP está registrado en NAND. Permite elegir una base faltante, instalar updates/DLC propios y mods ZIP LayeredFS. Que un archivo esté disponible en una carpeta no significa que esté instalado en NAND. La versión base puede necesitar consultarse en Eden si no se identifica.
- **Ajustes recomendados** permite aplicar, respaldar, restaurar, importar/exportar JSON y guardar feedback para compartir. Hay siete perfiles iniciales con su estado de prueba. Algunos son propuestas; no todos están validados jugando.

Para compartir ajustes, usá **Más opciones → Exportar mis ajustes** y enviá el JSON; la otra persona lo carga con **Importar ajustes de un archivo**. **Comunidad** ofrece el servicio opcional de perfiles y feedback con inicio de sesión con cuenta propia. La biblioteca local funciona sin cuenta. Ver [servicio comunitario](docs/COMMUNITY-PRESETS.md).

El formato y sus límites están explicados en [docs/PRESETS.md](docs/PRESETS.md).

## Accesos existentes, carátulas y controles de Steam

**Actualizar** vuelve a buscar los ports instalados por Quiver, incluidas sus carpetas personalizadas, y los accesos **No Steam** de la cuenta activa. Si una instancia de Prism ya tiene un acceso, se vincula con él. La detección no incluye toda la biblioteca de juegos comprados en Steam.

En la ficha de un acceso existente, **Editar acceso de Steam** permite cambiar nombre, ejecutable, carpeta de inicio y opciones de lanzamiento. Se conserva su identificador, que mantiene asociados los controles, Proton y el arte. Para guardar estos cambios, Steam debe estar cerrado; la app acumula los cambios y los guarda cuando Steam se cierra.

La carátula elegida en Deck Library se copia al grid vertical de Steam al agregar o actualizar ese acceso, con copia de seguridad de la anterior. Elegir una nueva imagen no cambia Steam inmediatamente: usar **Agregar a Steam** para guardar también allí. No se generan automáticamente imágenes horizontales, fondos ni logotipos.

**Controles** muestra el perfil de Steam Input guardado localmente para la instancia de Minecraft, cuando está disponible, y abre los controles del acceso correcto. Los perfiles no descargados desde Steam Cloud o configurados en otra cuenta pueden no aparecer. No modifica las asignaciones automáticamente.

## Project-2099

El adaptador de Project-2099 prepara una ISO de Xbox 360 (o un ZIP/7z que la contenga) con el instalador oficial Beta 4.1 fijado, bajo Proton. Las imágenes de PS3 se rechazan antes de descargar. Incluye un perfil propuesto de 720p / 60 FPS, accesos directos de Steam y detección de ports instalados. La validación de juego sigue pendiente. [Guía](docs/PROJECT2099.md).

## Historial: novedades de la 0.4.0

- **Quitar de Steam:** en la ficha de cada juego y en la barra de selección. No toca juegos ni partidas; guarda un respaldo de la lista de accesos.
- **Mando:** los accesos nuevos reciben el layout de gamepad de Steam para DualSense, DualShock, Xbox y Switch Pro. Para un acceso existente, usar **Mando → Asignar layout** con Steam cerrado.
- **Actualizaciones:** página propia con avisos de Deck Library, ajustes recomendados y ports. La instalación automática de Deck Library se activa en esa página.
- **Ajustes del juego:** resolución, FPS, correcciones y rendimiento por juego (DuckStation, Dolphin, Eden y Prism), con respaldo y restauración.
- **Catálogo de ports:** reúne las listas de Quiver y GithubLauncher, recomendados (Spider-Man 1 y 2 de PSX) y repositorios propios, con íconos o portadas, categorías y filtros. Instala desde GitHub con verificación de integridad y avisa cuando hay una versión nueva. Los ports instalados con Quiver o GithubLauncher también se detectan.
- **Actualización automática:** Deck Library avisa cuando hay una versión nueva y se actualiza sola en modo Escritorio; se desactiva en la página Actualizaciones.
- **Ports que compilan en la Deck (por ejemplo Spider-Man 1 y 2 de PSX):** se ejecutan dentro del SDK de KDE de Flatpak, que Deck Library instala una vez con confirmación. No hace falta root ni tocar SteamOS. Hay que aportar el disco USA y la BIOS que pide cada kit.
- **Configuración automática de ports:** el botón **Configurar** del catálogo busca el disco en la biblioteca (por el serial interno) y la BIOS (por hash), y prepara Spider-Man 1 y 2, Spyro (OpenPete) y Crash Team Racing Turbocharged.
- **Biblioteca sin duplicados:** nuevo filtro por tipo (ports, emulador, instancias de Minecraft…) y la opción **Preferir ports**, que oculta la versión por emulador de un juego que ya tiene port.

## Historial: cambios 0.11

Interfaz adaptada a la pantalla de la Deck, lista con carátulas, vista por plataforma y aviso fijo de cambios pendientes de Steam. «Configurar juego» reúne las acciones de ajustes. «Conflictos» muestra las rutas coincidentes. Desde Ajustes se puede agregar Deck Library a Steam para abrirla en modo Juego. La comunidad opcional usa cuentas propias mediante Keycloak y un servicio con SQLite. Ver [interfaz](docs/DECK-INTERFACE.md) y [servicio comunitario](community/README.md).


## Historial: cambios 0.12

Nueva estructura de la ventana: biblioteca a ancho completo y navegación superior. Cada juego tiene pestañas **Perfiles**, **Opciones**, **Controles**, **Archivos** y, en Switch, **Contenido**. Aplicar y guardar quedan visibles mientras se desplazan las opciones. Los cambios de Steam muestran cada operación por nombre y se pueden descartar. «Preferir ports» se retiró: se muestran tanto el port como la copia emulada. Los scripts de EmuDeck no se cuentan como instalaciones adicionales. Las actualizaciones muestran las notas que publicó el autor para esa versión.


## Cambios 0.13

La ficha del juego se reemplazó por una vista con carátula, acción principal y tarjetas de ajustes. Se retiró la navegación por pestañas del juego. Aplicar y Deshacer permanecen visibles; los cambios y sus errores aparecen en la ficha. Las herramientas secundarias se agrupan por tarea y la selección de perfiles no aplica cambios automáticamente. La cabecera se compacta en ventanas bajas, el foco empieza en Jugar y Escape vuelve primero al juego. Se conserva la integración con Steam, EmuDeck, Quiver, Prism y los perfiles comunitarios.

## Novedades de 0.14

- **Catálogo de ports** reemplaza Explorar; abre el catálogo sin pasos intermedios.
- Cada port muestra su descarga, porcentaje y tiempo estimado en su propia fila. Durante la compilación se indica la fase; no se estima un porcentaje sin datos.
- Los ajustes de Eden se presentan como **Equilibrado**, **Rendimiento** y **Calidad**, con iconos y valoraciones reales. Los perfiles sin votos lo indican.
- **Comunidad → Mi cuenta** permite crear una cuenta o iniciar sesión (integrado en la app desde 0.16). No necesitás GitHub. Para compartir: **Compartir mis ajustes → Revisar mis ajustes → Publicar perfil**. El aporte queda pendiente de revisión. Las estrellas y los comentarios requieren sesión.
- En modo Juego: cruceta o stick para navegar, A para activar, B para volver y LB/RB para cambiar de sección. Trackpad derecho y R2 conservan puntero/clic. **Steam + X** abre el teclado. El soporte nativo de mandos usa SDL2, incluido en SteamOS.
- Se conserva la biblioteca al cambiar de pestaña para evitar reconstruir todas las carátulas.

## Ports y originales (0.15)

El catálogo consulta la API actual de Quiver, las listas de GithubLauncher y una lista independiente de ports. Incluye un índice propio de respaldo para poder consultarlo sin conexión. **Nuevos primero** usa la fecha real de incorporación cuando la fuente la publica; **Últimas versiones** ordena por fecha de release. Se muestra cuándo se actualizaron los datos. Una fecha desconocida no se inventa.

Un port detectado desde otra instalación aparece como instalado. Si hay otra variante del mismo juego, se identifica como alternativa y pide confirmar antes de instalarla. Las descargas permiten **Cancelar**; una tarea terminada o fallida se puede **Descartar** desde su fila. Un error de descarga no abre un diálogo que bloquee la app.

**Revisar originales**, sobre la biblioteca, o **Ajustes → Originales y ports** muestra los juegos que tienen port instalado. **Ocultar original** conserva sus archivos y tiene una acción para volver a mostrarlo. **Enviar a la papelera** muestra los archivos y requiere confirmación; se bloquea si otro acceso usa alguno. Los discos originales pueden hacer falta para reconstruir un port al actualizarlo.

**Actualizaciones → Project-2099 → Actualizar** localiza la copia de Xbox 360 disponible o permite elegirla; verifica el SHA-256 del instalador y del paquete, instala en una carpeta temporal y conserva la versión anterior completa. Se preserva UserData. Beta 5 cambia de motor: los mods y ajustes gráficos antiguos quedan en el respaldo. Se mantiene el Proton elegido en el acceso del juego; el instalador utiliza su entorno de instalación. La actualización no abre el juego. También se incluye en la cola al habilitar actualizaciones automáticas de ports.

Los perfiles incluidos y probados aparecen entre los principales con **✓ Comprobado · usuario**. Una prueba de arranque se distingue con **✓ Comprobado · arranque**; no implica validación de rendimiento. Las propuestas nuevas conservan ese estado y los perfiles propios aparecen en las opciones adicionales. Las carátulas llenan el espacio vertical, recortando el excedente si tienen otra proporción.

### Iniciar sesión y registrarse

Abrí **Cuenta** con el icono de personas de la barra superior, o **Comunidad → Mi cuenta** desde un juego. **Iniciar sesión** y **Crear cuenta** abren los formularios dentro de Deck Library. Para registrarte en el servicio público necesitás verificar tu correo. Desde el inicio de sesión también podés recuperar la contraseña. Consultar perfiles no requiere una cuenta ni GitHub.

En la Steam Deck se reutiliza el componente web de GNOME si está instalado. Si falta, la app ofrece instalarlo desde Flathub o seguir en el navegador. En modo Juego: cruceta/stick para moverte, A para seleccionar, B para cancelar el acceso y **Steam + X** para escribir. La navegación física con mando queda pendiente de confirmación.

Cerrar el acceso cancela la espera y cierra su navegador interno. **Cerrar sesión** revoca el acceso comunitario. Las contraseñas las valida Keycloak; Deck Library guarda únicamente su sesión con permisos privados.

### Navegación con mando (0.17)

El juego enfocado se resalta con un borde claro y el fondo de la tarjeta. **Palanca izquierda / cruceta:** recorrer juegos. **A:** abrir la ficha. **B:** volver al mismo juego. **X:** buscar. **LB/RB:** cambiar pestaña. **Palanca derecha:** desplazar la vista. El foco se mantiene visible al recorrer la cuadrícula y se conserva al actualizar carátulas. Moverse por los juegos no los marca para agregarlos a Steam.

El perfil propio de Deck Library ahora usa las dos palancas como mando y conserva el ratón en el trackpad derecho. El instalador actualiza esa plantilla con respaldo; conserva los perfiles elegidos por el usuario y los controles de otros juegos. Cerrá y volvé a abrir Deck Library desde Steam para recargarla. Si elegiste un perfil personalizado, seguirá seleccionado. El recorrido se comprobó con un mando virtual de SDL; falta confirmar las palancas físicas en modo Juego.

### Selector e indicadores (0.17.1)

El resaltado también aparece en Jugar, perfiles, opciones, menús y ventanas, y se recupera al actualizar una ficha. **B / ○** cierra primero el menú o la ventana actual; dentro de un juego vuelve de los ajustes a la ficha y después a la biblioteca. **A / ✕** selecciona el control resaltado. Al pie se muestran los botones y su acción actual; las ventanas tienen sus propios indicadores de selección y regreso.

### Nombres e imágenes del catálogo (0.17.2)

La API pública de Quiver aporta el nombre del juego, el proyecto que lo adapta, descripción e imágenes. El catálogo muestra primero el juego y debajo el nombre del port; la búsqueda admite ambos. Las carátulas se muestran en vertical. Si falla una descarga se intenta el icono del proyecto y después una portada coincidente por plataforma; los errores se vuelven a intentar después de una hora. Los proyectos de otras listas pueden tener menos información.

### Una sola ventana (0.18.0)

Los avisos, confirmaciones, carátulas, archivos, cuenta, comunidad y herramientas se abren como páginas dentro de Deck Library. Mantienen el tamaño de la app en modo Juego. Las acciones quedan al pie y **B / ○** vuelve a la página anterior, recuperando el control seleccionado. En tareas que no se pueden interrumpir, Volver espera a que termine la operación. Los errores del lanzador también aparecen dentro de la app; si estaba cerrada, se muestran al volver a abrirla.

El botón **Añadir Deck Library a Steam** está junto a las pestañas y utiliza la misma cola de cambios de Steam. Si Steam está abierto, el acceso se guarda al cerrarlo. En ventanas compactas, la cabecera se desplaza horizontalmente y el mando lleva a la vista el botón seleccionado.

### Fichas de ports e identificación del juego (0.18.1)

Pulsar la imagen o el texto de un port abre su ficha dentro de la app: juego original, nombre del port, descripción, plataforma, requisitos y versión cuando la fuente la informa. Instalar y actualizar son acciones separadas.

También se leen los nombres de los juegos en los encabezados de la lista independiente, y se buscan sus imágenes por coincidencia exacta con el catálogo de juegos. Por ejemplo, GSRecomp aparece como Golden Sun y Project-2099 como Spider-Man: Edge of Time. Las herramientas se mantienen como herramientas; no se les asigna un juego. Si una fuente no tiene carátula, la ficha permite reintentar sin esperar a que venza la caché del error.

### Apariencia y manejo en Steam Deck (0.18.2)

La interfaz usa superficies carbón, bordes suavemente redondeados, menos contornos y sombras, y una línea azul para la pestaña activa. El contador de Actualizaciones tiene texto blanco sobre azul tanto con la pestaña activa como inactiva.

El buscador indica **X: teclado**. X / □, el icono de teclado o A sobre un campo de texto abren el teclado de Steam. Los campos inhiben su apertura automática al recibir el foco; se conserva el teclado físico.

Las vistas admiten desplazamiento táctil y arrastre cuando Steam presenta el toque como un ratón. Al navegar con el mando, la tarjeta completa y su título se mantienen dentro de la vista, también en la última fila.

Los cambios guardados, ajustes aplicados, actualizaciones y errores muestran un aviso grande dentro de la app durante ocho segundos, con un botón para cerrarlo. Los estados de descarga siguen mostrando el progreso en su lugar. No se crean ventanas separadas.

Los perfiles integrados se identifican como **Integrado en Deck Library**. La marca **Verificado · usuario** corresponde a ajustes confirmados jugando; **Verificado · arranque** indica una prueba limitada al inicio. Las variantes sin prueba permanecen **Sin verificar**. En Mario Kart Wii, Calidad conserva el perfil confirmado y se selecciona de forma predeterminada; Equilibrado y Rendimiento son variantes de menor resolución pendientes de prueba.

**Ajustes de la comunidad** aparece como sección propia con una vista previa de perfiles, valoraciones y acceso a comentarios. Los perfiles adicionales están en **Otros perfiles**, visibles sin desplegar un acordeón. Los perfiles locales y las pruebas del autor no heredan la verificación de los integrados.

### Instalación y actualización de ports (0.19)

La ficha del catálogo muestra qué paquete se instalará. Se admiten AppImage, binarios y archivos comprimidos de Linux; también ports portables de Windows mediante Proton. Los instaladores que necesitan convertir un disco o compilar una ROM usan una integración específica. Los proyectos sin un paquete compatible lo indican al consultar sus detalles.

Project 2099 instala la última versión oficial. Beta 5 usa un motor nuevo y un acceso distinto: Deck Library los reconoce y conserva la versión anterior como respaldo. El instalador tiene su propio entorno de Proton, progreso por archivos escritos, cancelación y detección de bloqueos. Los perfiles verificados de Beta 4.1 no se aplican a Beta 5.

### Correcciones de modo Juego (0.19.1)

El mando usa el foco de Gamescope en modo Juego, para mantener la navegación aunque GTK pierda su indicador de ventana activa. Se suspende la entrada al pasar al menú de Steam u otra app. Los cambios de pantalla del catálogo y la biblioteca son directos en sesiones de Steam, para evitar bloqueos de dibujo de GTK. Se conservan las animaciones de los controles. Project 2099 Beta 5 arranca directamente desde su acceso de Steam, sin pasar por el lanzador de Windows.

### Mando dentro de las fichas y Project 2099 (0.19.2)

Se corrigió un bloqueo del lector del mando al abrir fichas de ports y otras tareas internas. B/○ sigue leyéndose mientras la ficha está abierta. El acceso de Project 2099 ejecuta el motor desde su propia carpeta y prefiere Proton 9 para el juego si está instalado; el instalador y el lanzador oficial conservan Proton actual. Falta confirmar ambos cambios en modo Juego.
