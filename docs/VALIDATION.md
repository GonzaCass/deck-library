# Validación

## Versión 0.18.2 — 2026-10-19

Se superaron 687 pruebas, incluidas 54 de GTK. Se verifica contraste superior a 4,5:1 del contador de Actualizaciones en ambas variantes de la pestaña, su espacio y su ocultación cuando no hay actualizaciones. Se comprueban apertura del teclado únicamente por acción explícita, indicación X en el buscador e inhibición de teclado automático; captura del arrastre tras superar el umbral y conservación de toques cortos; visibilidad de la tarjeta completa y su título en la última fila; avisos grandes y descartables dentro de la ventana principal. Las solicitudes del teclado de Steam se simulan en las pruebas para no abrirlo en la Deck remota. También se verifica la integración del perfil confirmado de Mario Kart Wii en Calidad sin alterar sus ajustes, que las otras variantes no hereden su verificación, que una modificación local no conserve la marca y que comunidad/perfiles adicionales sean visibles sin desplegables y dentro de 840 píxeles.

Se revisó visualmente la ficha a 1280×760. Falta confirmar en la Deck física el teclado de SteamOS y los gestos táctiles, que pueden presentarse como eventos de ratón en modo Juego. No se ejecutaron juegos ni se cambiaron sus ajustes.

## Versión 0.18.1 — 2026-10-19

Se superaron 679 pruebas, incluidas 48 de GTK. Se verifican los encabezados de juego de la lista independiente, entidades HTML, separación de descripciones por proyecto, clasificación de herramientas, enriquecimiento de imágenes únicamente por identidad exacta y reintento manual de imágenes. En GTK se comprueba que pulsar una tarjeta abre una ficha interna sin iniciar la instalación, que la ficha identifica juego y port por separado y que se muestran imágenes descargadas.

Se descargaron imágenes reales para Golden Sun, Spider-Man: Edge of Time, Twilight Princess y otros juegos entre los primeros 24 proyectos del catálogo. Las herramientas y algunos proyectos que agrupan varios juegos pueden no tener una carátula. Se revisó visualmente la ficha de Golden Sun a 1280×760. No se instalaron ni se abrieron juegos.

## Versión 0.18.0 — 2026-10-19

Se superaron 674 pruebas, incluidas 46 de GTK. Se comprueba que los avisos, confirmaciones y carátulas no crean ventanas adicionales; páginas internas anidadas conservan el tamaño de la app; B/Círculo vuelve al nivel anterior y recupera el foco. El explorador local valida archivos y carpetas, y conserva la confirmación explícita antes de reemplazar un archivo. El cierre con B respeta los bloqueos de tareas activas. Los errores del lanzador se guardan localmente y aparecen dentro de la app, sin ejecutar kdialog. El botón de Steam usa la cola existente y la cabecera admite 840 píxeles. Cuenta y comunidad también se validan dentro de la ventana principal.

Se revisó visualmente la pantalla interna de carátulas a 1280×760. La prueba física en modo Juego queda pendiente. No se abrieron juegos ni se cambiaron sus ajustes. Las aplicaciones externas solo se abren mediante las acciones explícitas correspondientes.

## Versión 0.17.2 — 2026-10-19

Se superaron 666 pruebas, incluidas 39 de GTK. Se comprueban el nombre del juego como título del catálogo y del port como subtítulo, búsqueda por ambos nombres, descripción y diseño a 840 píxeles. Las pruebas de metadatos cubren la prioridad de la API actual sobre las listas antiguas, conservación de imágenes al normalizar el catálogo, alternativa del icono cuando falla la carátula, imágenes de más de 2 MB, reintento de errores de descarga y búsqueda de portadas por el título original.

La consulta de la API pública devolvió 464 proyectos: 460 con juegos asociados y 461 con carátula. Se comprobaron descargas reales de imágenes; los proyectos de fuentes independientes pueden no disponer de esos datos. No se instalaron ni ejecutaron juegos.

## Versión 0.17.1 — 2026-10-19

Se superaron 661 pruebas, incluidas 38 de GTK. Se verifican foco lógico visible en acciones de la ficha, perfiles, menús y ventanas; navegación entre controles de tamaños distintos; restauración del perfil enfocado al reconstruir una ficha; regreso por niveles con B/Círculo y cierre de popovers antes de salir del juego. Las leyendas muestran nombres de Deck y PlayStation y adaptan las acciones al contexto. Se comprobaron 1280×760 y 840×640 sin desbordar la ventana.

El mando virtual real de SDL también inyecta A y B: abre la ficha, mantiene marcado Jugar y vuelve al mismo juego de la biblioteca. Un test impide activar un botón Jugar de una página oculta. Se corrigió el orden de visualización inicial de Gtk.Stack para respetar la vista configurada antes del primer recorrido. No se abrieron juegos ni se modificaron configuraciones de juegos. La validación física de estas pantallas queda para el usuario.


## Versión 0.17 — 2026-10-19

Se superaron 654 pruebas, incluidas 32 de interfaz GTK.

Navegación espacial por filas/columnas, foco de carátulas y filas visible, restauración al volver de una ficha y al regenerar la biblioteca, desplazamiento con palanca derecha, umbral con histéresis y repetición sin repetir A. La integración usa un mando virtual real de SDL: se inyectan ejes, se leen a través del backend de la app y se comprueba movimiento de foco y desplazamiento GTK. No se abrieron juegos.

El perfil instalado de la biblioteca seguía basado en teclado/ratón: la palanca derecha enviaba movimiento de ratón. La nueva plantilla deriva del mando nativo de Steam, mantiene ambos joysticks y coloca el ratón exclusivamente en el trackpad derecho. Se comprobó el VDF real instalado y se prueba su generación, respaldo y conservación del original. El instalador refresca solo el archivo de plantilla propio, sin escribir configsets ni modificar perfiles personalizados. Recargar la plantilla en Steam y confirmar las palancas físicas sigue requiriendo la prueba del usuario en modo Juego.


## Remitente de correo — 2026-10-19

Se instaló un proveedor específico de correo, compilado contra Keycloak 26.3.4 y probado primero en un contenedor aislado de la misma imagen. La política superó 16 comprobaciones: selección por realm/cliente, conservación de credenciales y TLS, sobrescritura de From/Reply-To/envelope y ausencia de cambios en el mapa SMTP original. Se fijó la misma versión de imagen del despliegue para evitar actualizaciones incompatibles del SPI interno.

Una cuenta temporal se registró mediante el formulario real de Deck Library con la nueva dirección local como destinataria. El mensaje llegó como **Deck Library <decklibrary@jokerlan.xyz>**, con cabecera DKIM. Se siguió el enlace real del correo, se completó la autorización y `/v1/me` confirmó la sesión comunitaria; después se revocó. Una recuperación iniciada desde el cliente integrado account-console llegó como **Keycloak <keycloack@jokerlan.xyz>**. Se comprobó que el mapa SMTP global quedó sin cambios y se eliminaron los usuarios temporales. No se enviaron mensajes a terceros ni se publicaron perfiles.

La nueva dirección es un alias del buzón SMTP existente. Esta prueba confirma entrega y verificación en el servidor local; no mide recepción en proveedores externos. Cierra la comprobación pendiente de recepción/verificación de registro de la sección 0.16. La navegación física con mando sigue pendiente. El código, compilación y reversión están en [keycloak-mail](../community/keycloak-mail/README.md).


## Versión 0.16 — 2026-10-19

Se superaron 645 pruebas, incluidas 27 de interfaz GTK. Las nuevas pruebas cubren el origen HTTPS permitido, reutilización del componente web, ausencia de instalaciones automáticas, descarte de accesos cancelados, permisos privados de sesión, identidad autenticada, revocación y limpieza de sesiones vencidas. Se comprobaron los botones del panel, cancelación con el controlador lógico y límites de la ventana de cuenta a 840×640.

La vista WebKit se incrustó realmente en un Gtk.Socket nativo usando GNOME Platform 50 ya instalado. Cargó el formulario con el tema propio en español y se verificó el cierre del proceso al cancelar. La ventana mantuvo 840×680 durante la carga real. La recuperación abrió el formulario correspondiente con el tema propio, sin enviar solicitudes de correo. Una cuenta temporal se creó a través del formulario real de registro y llegó al paso obligatorio de verificación de correo. Para probar el inicio de sesión sin depender de un buzón, se marcó verificado únicamente ese usuario temporal mediante administración. Luego se rechazó una contraseña incorrecta, se autorizó el acceso real con contraseña correcta, `/v1/me` confirmó la identidad y cerrar sesión revocó el token. Se eliminaron las cuentas temporales. No se publicó contenido ni se alteraron cuentas existentes.

La recepción del correo de verificación y la recuperación por correo requieren una prueba con un buzón real. No se presentan como validadas por el test de registro. La navegación física con mando y el teclado de Steam en modo Juego siguen pendientes de confirmación del usuario. No se abrieron juegos. El tema se selecciona solo para el cliente deck-library y el montaje se conserva en el despliegue de Keycloak.


## Versión 0.15 — 2026-10-19

Se superaron 636 pruebas, incluidas 24 de interfaz GTK. Se comprobaron el catálogo vivo (503 repositorios combinados; 453 con fecha de incorporación de Quiver), su paginación y una fuente independiente. El índice incluido es una copia de metadatos públicos, sin juegos ni instaladores. La revisión local encontró seis parejas de original/port y detectó que CTR Turbocharged ya está instalado. Los tests cubren esas asociaciones, pistas CUE compartidas y referencias externas, ocultación, cancelación, limpieza del estado de errores, orden de fechas, perfiles propios después de los principales y carátulas sin bandas.

El actualizador de Project-2099 se ejercitó con un instalador simulado: instalación en un destino temporal, verificación de paquete, conservación de UserData, respaldo de la versión anterior y fallo sin reemplazar el juego. Se verificaron los assets oficiales de Beta 5 y la presencia del modo automático en el instalador. Se detectaron los datos Xbox 360 de la instalación local como fuente reutilizable. No se actualizó ni se abrió el juego; la instalación real completa de Beta 5 y su jugabilidad en la Deck siguen pendientes.

Los perfiles verificados identifican el nivel real de prueba: Mario Kart Wii y Smash, confirmación del usuario; Mario Kart 8, arranque comprobado y modo Juego pendiente; Project-2099, configuración actual del motor Beta 4.1 probada con Proton 9 y FPS variables. Las propuestas nuevas y la compatibilidad con Beta 5 no se presentan como comprobadas.


## Versión 0.14 — 2026-10-19

Se superaron 621 pruebas, incluidas 20 de GTK. Cubren autorización de cuenta propia con proveedor simulado, migración de SQLite conservando sesiones, estrellas reales y un voto editable por usuario, restricciones de los endpoints de autenticación, perfiles por Title ID, ETA medida, invalidación de actualizaciones completadas, repetición del mando, navegación sin reconstruir carátulas y límites de la ventana comunitaria. Las capturas públicas a 1280×800 contienen juegos e imágenes ficticios.

El servicio público respondió a health y a la lista de proveedores. La autorización real de Keycloak emitió un código de dispositivo y devolvió espera antes de la autorización del usuario. La finalización de ese acceso desde el navegador y la navegación física con mando en modo Juego requieren prueba del usuario; las pruebas automatizadas no equivalen a esas comprobaciones.

Wind Waker HD se verificó instalado en v0.3.0, con SHA-256 coincidente con el asset publicado, binario compilado y preparación de shaders finalizada. Se corrigió el metadato anterior y la caché de actualizaciones. No se volvió a lanzar el juego ni se midió su rendimiento durante esta revisión.

La auditoría del contenido de Git, el paquete nuevo y los 29 lanzamientos anteriores no encontró credenciales, rutas personales ni correos personales. La autoría de commits históricos contenía un correo personal; su sustitución por el alias y la dirección noreply de GitHub fue autorizada por el propietario. El respaldo de la historia original se conserva fuera del repositorio.



## Switch: tres propuestas y prueba directa — 0.10.2, 2026-10-17

Se superaron 572 pruebas automatizadas. Las nuevas comprobaciones cubren las tres opciones distintas para títulos sin perfil, prioridad de presets específicos incluidos/importados, resolución del Title ID, exclusión de otros adaptadores y juegos sin ID, preferencia local persistente por juego y aplicación/exportación/restauración con conservación de rutas, controles e idioma. Se mantienen el bloqueo por versión de Eden conocida y la protección del archivo global.

El diálogo GTK se ejercitó con Xvfb y un almacén temporal: selección de cada propuesta, confirmación de **Aplicar y probar**, lectura del INI resultante y tres lanzamientos mediante el método real `Window.play` y `app.py launch`, usando `/bin/true` como ejecutable de prueba. Se comprobó la salida correcta de cada proceso, **Marcar como mejor**, su selección al reabrir y **Restaurar anterior**. La captura a 880×640 permitió revisar que la lista y ambas filas de acciones quedaran visibles. Los metadatos GTK necesarios se extrajeron temporalmente; no se instalaron paquetes ni se modificó una biblioteca real.

Estas comprobaciones validan el flujo de la aplicación, no la emulación de un juego. No se lanzaron ROMs ni se midieron FPS. Las tres opciones mantienen estado `proposal`, compatibilidad declarada con Eden 0.2.1 y validación pendiente por título en Steam Deck/Gaming Mode.

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

### 0.8.3 - banner en la ficha

La ficha de un juego con acceso en Steam muestra como banner el fondo (`_hero`) y el logotipo (`_logo`) que Steam guarda para ese acceso, recortados al ancho de la página y con un degradado hacia el color de la página. Se comprobó con Breath of the Wild (arte descargado por el lote de arte): fondo y logotipo se ven y la carátula vertical también es la de Steam. Sin arte de fondo, la ficha queda como antes.

### 0.9.0 - guía por juego y traducción automática

Se agregó `docs/PORTS.md` con la guía de cada port y juego con emulador trabajados (Spider-Man 1 y 2, Crash, Spyro, Minish Cap, A Link to the Past, Wind Waker HD, Breath of the Wild, A Link Between Worlds, Mario Kart Wii, Steam) y **Configurar** de A Link to the Past genera ahora la ROM en español a partir del parche `.ups` que encuentre (suelto o en un zip de Descargas o de la carpeta de ROMs), siempre que las tres sumas CRC y el SHA-1 del resultado coincidan: los tests cubren un parche correcto, uno ajeno, uno dentro de un zip y un resultado con otro hash. No se volvió a ejecutar sobre la ROM real, que ya existe desde 0.6.2.

### 0.9.1 - correcciones tras la prueba en la Deck

Hallazgos de la prueba del usuario y su causa: (1) Breath of the Wild seguía en inglés porque en el archivo propio del juego faltaba la marca `\\default=false` de cada valor (con solo `\\use_global=false` Eden ignora el valor); además el registro de Eden confirmó que el parche de 60 FPS sí se aplicó y que el juego admite español latinoamericano (máscara de idiomas 0002FBFF incluye el 14). (2) A Link Between Worlds mostraba tres ventanas porque la disposición se había guardado en la sección `[Renderer]` en lugar de `[Layout]`; se corrigió y se migró la clave mal ubicada. (3) Spider-Man 1 iba súper acelerado por el mod Fast Loading: su propia descripción indica que acelera el juego mientras detecta una carga y este juego lee el disco sin parar; se retiró junto con CD Speed. (4) La interpolación pasó a mezcla lineal; el runtime informó «59.9 presents/s from 59.940 guest frames/s» con mezcla lineal y ya sin aceleración de carga. (5) Wind Waker HD: la pantalla del GamePad pasó a modo automático y la interpolación a ritmo uniforme; los tirones son compilación de shaders la primera vez (el port compila en Vulkan al primer uso y guarda la caché). No se pudo ver ninguno de estos juegos en pantalla desde esta sesión.

### 0.9.2 - Wind Waker HD 0.2.13 y preparación de shaders

Wind Waker HD se actualizó a v0.2.13 con las funciones de la app (descarga con suma verificada, reinstalación con las claves de keys.txt en archivos temporales que se borraron). El setup nuevo resuelve 27 147 registros de shaders desde los archivos del juego, pero la compilación para la GPU falló porque esta sesión remota no puede presentar con Vulkan (sin DRI3); además el setup guardó el resultado en `~/.config/xrdp-plasma` por la variable `XDG_CONFIG_HOME` de esta sesión, de modo que ahora el setup y la preparación usan siempre `~/.config` y `~/.local/share` reales. Se agregó el botón **Preparar shaders** (Catálogo) que reutiliza el módulo del propio port; falla con un mensaje claro cuando la sesión no puede dibujar. No se pudo compilar ningún shader aquí.

Mods de Breath of the Wild: el zip «BOTW DS4 UI Mod v2» se instaló con el instalador de mods (3 archivos en `romfs`); el preset de ReShade no es aplicable en Eden. Spider-Man: no se pudo medir la velocidad real del motor (el juego tarda más de 70 s en cargar con renderizado por software en esta sesión).

### 0.10.0 - Spider-Man a 60 FPS reales (Smooth 60)

Se compiló una variante de depuración de cada kit (con el servidor TCP de depuración) para medir y localizar el límite. Hallazgos: (1) el juego gira su bucle principal en `func_8002C174` (Spider-Man 1; `func_80031D34` en el 2) con una espera condicional de un vblank y otra **incondicional** (`0x8005E748(1)` desde `0x8002C294`) antes de mostrar cada cuadro: un mínimo de 2 vblanks por cuadro. (2) La lógica de actualización (`func_80062CE0`) calcula su paso como la diferencia del contador de vblanks, es decir, está basada en tiempo; una variable de posición avanzó 26 770 y 26 990 unidades por vblank en la versión original y en la parcheada (razón 1,01), y otra ±2 140 por vblank. (3) Un overclock de CPU por sí solo no cambia nada (0,50 cambios de búfer por vblank con 4×); anular la espera da 0,61; anulación y CPU 4×, 0,885; con 8×, 0,958 en Spider-Man 1 (primera misión). Spider-Man 2 en la escena de la Bestia: 0,34 original, 0,77 con 6×, 0,94 con 12×. Los kits reales se recompilaron con el parche y se lanzaron con el comando del propio acceso (entorno `DECK_WAITVB_FUNC`, `DECK_WAITVB_ZERO_RA`, `DECK_CPU_OC` dentro del SDK): ambos arrancaron sin errores. Esta sesión corre a menos de la velocidad real (renderizado por software), de modo que las mediciones son en tiempo del juego (vblanks), no en segundos. No se jugó una partida completa: falta comprobar que menús, videos y escenas especiales mantengan su velocidad y que no aparezcan fallos de temporización con el overclock.

### 0.10.1 - Correcciones tras la prueba en la Deck

Resultado de jugar en la Deck: Spider-Man 1 y 2 con el 60 real se sentían muy acelerados y los sticks eran incontrolables, de modo que parte de la lógica depende de los cuadros (la medición con variables de posición no lo detectó). Smooth 60 queda apagado por defecto (`SMOOTH60_DEFAULT=False`); `maintain` retira el entorno de los accesos que lo tenían. Breath of the Wild no arrancaba: el registro de Eden muestra más de 900 000 lecturas y escrituras en memoria sin asignar a los 13 s, justo después de abrir el audio, con el mod de interfaz DS4 instalado; la última ejecución que llegó a compilar pipelines (sin ese mod) no tenía errores, así que el mod se movió a `~/Emulation/storage/eden/mods-desactivados` (no se pudo comprobar el arranque aquí, sin GPU). A Link Between Worlds pasa de una sola pantalla a la disposición «pantalla grande» con la otra pequeña, para que las dos se vean sin depender de F9/F10 de Steam Input. Wind Waker HD: la pantalla del GamePad «queda a un costado» al pulsar Select; no se pudo reproducir sin una sesión con Vulkan y no se cambió nada.


### 0.11.0 — Interfaz de Deck y comunidad (2026-10-18)

Base: main 5f8d0ec (0.10.2), traída con git pull --ff-only. Pruebas completas: 591 casos correctos, incluidos cuatro GTK optativos con DECK_LIBRARY_UI_TESTS=1. Se comprobaron las vistas carátulas/lista/plataformas, miniaturas, ausencia de diálogo modal al acumular cambios de Steam y tamaño del informe de conflictos con 50 resultados asíncronos y una confirmación con 80 líneas. Capturas con biblioteca ficticia a 1280×760: biblioteca, ficha, ajustes, alta y asistente; seis diálogos mantuvieron tamaños de 660–880 × 480–640. La navegación física con Steam Input y el teclado de Steam requiere prueba del usuario en modo Juego.

Se instaló localmente 0.11.0 conservando una copia de la instalación 0.10.1. Se preparó el acceso de Deck Library con la cola segura de Steam; no se cerró Steam automáticamente. No se cambiaron juegos ni sus ajustes durante esta tarea.

Servidor opcional en jokerlan.xyz: imagen construida y probada primero con red deshabilitada, servicio independiente desplegado con red traefik-net y TLS. GET /health y GET /v1/presets respondieron por HTTPS desde la Deck; GitHub Device Flow emitió un código real y respondió pending sin autenticar a ningún usuario. El inicio de sesión completo y la publicación autenticada están cubiertos con respuestas GitHub simuladas en tests; falta la autorización real del usuario en la app. SQLite persistente en volumen propio, token de sesión por hash, aportes pendientes hasta revisión, consulta privada de aportes y un feedback por usuario/perfil. No se subió ninguna configuración personal.


### 0.12.0 — Sustitución de la estructura de interfaz

Se reemplazó la ventana anterior por navegación superior y biblioteca a ancho completo. Las acciones de biblioteca se separaron en gui_actions.py, las vistas en gui_shell.py y el editor integrado en gui_editor.py. Se retiraron el selector intermedio y los diálogos antiguos de perfiles/opciones. La captura de README usa una biblioteca ficticia con arte geométrico propio, sin rutas ni cuentas personales.

El pendiente de la Deck era el acceso de Deck Library preparado en la instalación anterior, no una operación iniciada al abrir la app. Se añadió detalle por operación y cancelación segura de la cola. La revisión real de esta Deck no reporta instalaciones alternativas de emuladores tras excluir scripts y deduplicar rutas/inodos. Se descargaron a caché las notas oficiales de las versiones que mostraba el programa para Wind Waker HD y Project-2099; no se actualizaron juegos.

Pruebas GTK: navegación y tres vistas a 1280×760, perfil aplicado desde su ficha sin selector modal, edición de opciones integrada, visibilidad de ambas versiones port/emulador, detalle nominal de pendientes, miniaturas y límites de diálogos. Las pruebas de servicio cubren el trabajador al cancelar la cola, alias AppImage/script/enlace, y changelog de la versión exacta. Falta la prueba física en modo Juego.

Resultado final 0.12.0: **601 pruebas correctas**, incluidas siete pruebas GTK optativas. No se modificaron juegos ni se actualizaron ports durante esta revisión.


### 0.13.0 — Ficha visual, tareas y ejecución desde Steam (2026-10-19)

Se inspeccionó el frontend de SpotiFLAC de escritorio (React, Radix UI y motion) como referencia de jerarquía y comportamiento. La ficha de Deck Library se implementó con componentes nativos propios: cabecera con carátula y fondo, acciones de colores, tarjetas de perfiles y barra fija de aplicación. Se retiró el selector de pestañas del juego; controles, contenido y edición manual son tareas con regreso explícito.

**611 pruebas correctas**, incluidas **17 comprobaciones GTK**. El recorrido verificado con datos aislados cubre selección sin escrituras, aplicación real a un INI temporal, creación de respaldo, restauración, rechazo con el emulador abierto, estado de reintento, diferencias de valores heredados de Eden, cambio de juego durante una aplicación diferida, botones de Steam pendientes y conservación de ediciones manuales durante refrescos. Se verificó que abrir una ficha empieza en el resumen y da foco a Jugar.

Se renderizaron biblioteca, juego, opciones y controles a **1280×800** y **840×520**. La cabecera se compacta en la ventana baja y los perfiles pasan a una columna en la estrecha; aplicar y guardar permanecen dentro de la ventana. Se comprobaron mediante reloj de cuadros la entrada de la cabecera, el despliegue de detalles, el estado final y la desactivación de animaciones. Las capturas públicas contienen juegos ficticios y arte geométrico propio.

La guía en español y el README explican cómo agregar Deck Library desde Ajustes, guardar una sola vez la cola al cerrar Steam y abrir la app desde la biblioteca en modo Juego. También distinguen los accesos individuales de cada juego. Se añadió un trabajo de CI con GTK/Xvfb para mantener estas comprobaciones. La navegación con los controles físicos y las transiciones entre la app y juegos en modo Juego quedan para prueba en la Deck; no se ejecutaron juegos ni se cambiaron sus ajustes en esta revisión.

El primer trabajo GTK de GitHub detectó que el runner de Ubuntu no tenía lector SVG de GdkPixbuf. El arranque y la cabecera pasaron a usar el PNG incluido, para que abrir la app no dependa de ese lector opcional. También se fijó el tema oscuro de los controles nativos y los menús desplegables.

## 0.19 — Paquetes comunes y actualización real de Project 2099

Se reprodujo un bloqueo real del instalador Beta 5 ejecutado con el Proton 9 elegido para jugar a Beta 4.1: repetía diagnósticos de Wine y no creaba el juego temporal. El proceso se detuvo únicamente en su entorno. El mismo instalador oficial, con el payload descargado, terminó con salida 0 bajo Proton 11 en un entorno separado. El recibo declara Project 2099 Beta 5 2026-10-13 e idioma efectivo 5 (español). Se verificó la estructura nueva, se conservaron las partidas y la instalación completa anterior, y se mantuvo el identificador del acceso de Steam. No se abrió Beta 5 ni se midió rendimiento: su prueba de juego queda pendiente.

Pruebas nuevas: selección de paquetes oficiales SteamOS/Linux frente a Windows/Flatpak/ARM, instalación y actualización simuladas de un Windows portable, entorno persistente por juego, partidas y respaldo, rechazo de ejecutables fuera del paquete, rollback del reemplazo, cancelación de procesos reales, detección de inactividad, filtrado de Wine, actividad por escrituras y migración Beta 4.1 → Beta 5 con identidad estable. Las pruebas de paquetes usan ejecutables mínimos y descargas simuladas; no acreditan compatibilidad de juego de todo el catálogo.

## 0.19.1 — Cambios de pantalla en modo Juego e inicio directo de Beta 5

Los registros de modo Juego reportan errores de GTK `alloc_needed` al dibujar durante cambios de página. Se desactivan las transiciones que capturan imágenes de Gtk.Stack en sesiones de Steam; se conservan las animaciones de botones y tarjetas y la configuración del usuario. Se evita además forzar `check_resize` del contenedor del juego. Una prueba de interfaz recorre catálogo, biblioteca, ficha, archivos y ambos niveles de Volver con animaciones habilitadas y SteamGameId; comprueba páginas dibujadas/mapeadas, ausencia de errores críticos de GTK y cambio directo de los stacks.

Los registros reales de Beta 5 muestran inicio del motor, ventana fullscreen y, en uno de los intentos, cuadros renderizados. No bastan para afirmar que el juego no se ejecuta: es posible que el lanzador WPF quede delante de la ventana del juego en Gamescope. El acceso administrado ahora inicia `Engine/Project2099.exe` directamente, pasando la carpeta instalada de datos, el idioma del recibo y el perfil default; el lanzador queda como opción explícita `--launcher`. Las pruebas cubren el comando, las rutas con espacios, el idioma y los datos ausentes. No se ejecutó el juego al hacer este cambio; la comprobación física de foco, mando y avance del juego queda pendiente.

El usuario precisó que los botones del mando dejaban de responder después del cambio de pantalla. El lector SDL suspendía toda entrega de pulsaciones cuando GTK dejaba de informar una ventana activa. Ahora consulta la propiedad oficial de Gamescope `GAMESCOPE_FOCUSED_APP` mediante X11: entrega la entrada si el compositor mantiene enfocada esta app, aunque los indicadores GTK se pierdan; la suspende al cambiar al menú de Steam u otra app. En un escritorio normal conserva la comprobación GTK. Se probaron ambos estados del compositor, ausencia de propiedad, identificación de accesos de Steam, memoria X11 liberada, pérdida de foco GTK y navegación Catálogo/Volver mediante el trabajador real con lecturas SDL simuladas. No se inspeccionó el foco de una sesión física de Gamescope durante el fallo.

Referencia del compositor: https://github.com/ValveSoftware/gamescope/issues/416 (la propiedad también se usa para filtrar entrada en Proton).

## 0.19.2 — Bloqueo reproducido del mando dentro de las fichas

El cambio de foco de 0.19.1 no resolvía el fallo reportado. La lectura SDL se ejecutaba desde un timeout de GLib que llamaba a `controller_action` sincrónicamente. Al abrir una ficha de port u otra tarea con `InlineDialog.run`, ese timeout quedaba dentro de un bucle GLib anidado y no podía volver a ejecutarse para entregar B/○. El renderizado podía continuar, pero el lector del mando quedaba suspendido. Las acciones ahora se despachan desde fuentes idle independientes; el timeout termina inmediatamente y continúa leyendo el mando dentro de las tareas. Una excepción transitoria del callback tampoco elimina permanentemente el lector: queda registrada y el timeout continúa.

La prueba de regresión usa el timeout real, abre la ficha con A y devuelve B desde la siguiente lectura simulada de SDL mientras la ficha mantiene su bucle anidado. Con despacho síncrono anterior alcanza el watchdog y falla; con el despacho independiente vuelve al catálogo sin intervención del watchdog. Se probó además el catálogo local real con 60 filas: carga de widgets en menos de un segundo y retorno a Biblioteca en el escritorio remoto. Eso no equivale a una validación física de Gaming Mode.

Project 2099 seguía cerrándose con código 3 desde el acceso de 0.19.1. La inspección local del método `StartGame` del lanzador oficial confirma que fija `WorkingDirectory` a la carpeta del motor. Deck Library usaba la carpeta superior. Se corrigió a `Engine` para el inicio directo y se conservan datos, idioma y perfil. En una prueba breve con la GPU/pantalla físicas, Proton 11 aún terminó con código 3. Con Proton 9 y la misma carpeta de motor el proceso permaneció abierto durante 35 segundos, mostró la pantalla de carga en español (captura privada) y se detuvo al terminar la prueba. El acceso directo prefiere Proton 9 si está instalado, con entorno independiente del instalador y del lanzador .NET; si falta, usa el Proton actual disponible. No se acredita llegada al menú, jugabilidad, FPS ni funcionamiento en Gamescope con esta prueba de escritorio. Se conserva la opción explícita de abrir el lanzador con Proton actual.

Se corrigió también una activación duplicada al construir pantallas: el filtro de ecos de A contaba desde antes de dibujar la ficha. Si el render tardaba más de 90 ms, un eco posterior activaba otro botón y abría una tarea no prevista. El intervalo ahora se mide desde que termina la acción. La prueba existente de navegación y activación duplicada reproducía el fallo en el escritorio remoto; se conserva como regresión.

## 0.19.3 — Revisión de Quiver y fuente PortIntegration

Se consultó la release estable oficial de Quiver: v3.5.1, publicada el 15 de octubre de 2026. La instalación local preparada de Quiver tiene fuentes v3.4.5. Se revisaron sus cambios de mando, archivos y catálogo; no se reemplazó Quiver ni se tocaron sus juegos como parte de esta revisión.

PortIntegration se inspeccionó desde su repositorio público y su sitio. Al revisarlo, `PORTS_DATABASE` contenía 231 entradas y 230 repositorios distintos, de los cuales 95 no aparecían en la caché previa de Deck Library. Su escáner usa búsquedas de GitHub y filtros; el workflow genera propuestas diariamente. Se integró la lectura de literales JSON, con validación de repositorios, límite de filas, enlaces de imágenes restringidos al manifiesto, deduplicación, precedencia de identidades existentes y filtro de fuente. Las pruebas cubren un catálogo con código JS después de los datos (no ejecutado), contenido inválido, rutas de imagen inseguras, estados y fechas no verificados, fallo de red y fusión sin duplicados.


## 0.19.4 — Catálogo desde Steam y navegación con mando

Se superaron 719 pruebas: 658 de lógica y 61 de GTK.

Se reprodujo el bloqueo al abrir el catálogo desde el acceso de Steam en una Deck física, en modo Escritorio y a pantalla completa. El registro mostró recorridos del árbol de widgets desde la comprobación de foco, repetidos por el sondeo SDL cada 25 ms. El foco que no cambia ya no vuelve a recorrer el árbol; la búsqueda de menús solo visita las páginas visibles. Una prueba con un recorrido deliberadamente lento verifica que los callbacks de carga siguen ejecutándose mientras el mando se consulta.

También se reprodujo una página mapeada con una distribución de 1×1 píxel y luego tarjetas sin distribuir tras completar la carga. El cambio de página sin transición y la carga del catálogo solicitan y procesan una nueva distribución de la ventana. La regresión comprueba la recuperación de la distribución y se mantienen las comprobaciones de ancho compacto. Se revisaron visualmente los 633 proyectos combinados de la caché local: las primeras 60 tarjetas, con imágenes y nombres, aparecen en la pantalla de 1280×800. La prueba final del mando físico y de una nueva sesión de modo Juego requiere confirmación del usuario.

La versión no cambia juegos, Proton, perfiles ni ajustes de Spider-Man. Las correcciones del servicio de escritorio remoto y de la clasificación de sesiones son mantenimiento local de esa Deck; no se incluyen en el paquete público.

## 0.19.5 — Lectura y distribución para la pantalla de la Deck

Se superaron 725 pruebas: 658 de lógica y 67 de GTK. La interfaz se comprueba a 1280×800 y en una ventana de 840×520. La cabecera del juego se compacta hasta 820 px de alto, las tareas pasan a una barra de pestañas persistente y los presets ocupan todo el ancho. El texto principal tiene 17 px; los metadatos y los indicadores de mando también aumentan. Las comprobaciones cubren las tres tarjetas principales, las acciones de la cabecera, las pestañas visibles y la última carátula completa incluso con cambios pendientes en Steam. La captura pública de la ficha utiliza un juego ficticio y datos temporales.

La prueba local se hizo abriendo el acceso desde Steam en modo Escritorio, a pantalla completa y con `--gaming`, en una Steam Deck física. Un mando virtual Linux creado con uinput envió eventos reales de botones, cruceta y ambas palancas a SDL. Se recorrieron las cuatro pestañas principales en ambos sentidos, tres ciclos de navegación, fichas de cuatro juegos y sus secciones disponibles, detalles de un port, la cuenta y las tres vistas de Comunidad. Se alcanzó el final de la biblioteca y del catálogo; A abre las fichas y B devuelve el foco. Los desplegables se recorrieron con el mando, se cambiaron las vistas Lista, Por plataforma y Carátulas y se cerró un menú con B. La vista Carátulas quedó restaurada.

Ese recorrido detectó secciones internas sin distribuir y un panel comunitario que no respondía a la palanca derecha cuando el foco estaba en las pestañas. Los cambios de las pilas internas y las cargas que reconstruyen tarjetas ahora solicitan la distribución desde la ventana. El desplazamiento prefiere el panel enfocado y luego los paneles visibles con contenido desplazable. Los desplegables normalizan su botón interno de GTK al selector que representa, para conservar la navegación y el resaltado. Hay regresiones para esos casos.

No se aplicaron presets ni se lanzaron juegos durante el recorrido. Los instrumentos privados de diagnóstico no forman parte de la instalación ni del paquete. Estas pruebas no equivalen a accionar las palancas físicas en una sesión nueva de modo Juego: esa comprobación sigue pendiente del usuario.

El botón superior para añadir la propia app a Steam se oculta al arrancar desde Steam o con `--gaming`. Se comprobó la visibilidad en ambos contextos, incluso después de `show_all()`, y que el mando no incluye la acción oculta entre los controles disponibles.

## 0.19.6 — Originales asociados y preparación de ports

Se superaron 739 pruebas: 669 de lógica y 70 de GTK. Se añaden regresiones para la agrupación de originales sin borrar entradas ni archivos, plataforma e identificadores incompatibles, títulos ambiguos, asociación reversible, carátula con badge completa al final de la biblioteca con cambios pendientes, filtros y recuperación del foco. El selector integrado comprueba un original elegido fuera de EmuDeck antes de habilitar Preparar. La alternativa explícita de Proton se comprueba dentro de la ficha y sin iniciar una instalación real en el test GTK.

La selección de paquetes se revisó contra publicaciones e instrucciones originales de los proyectos de [la tabla](PORTS.md#proyectos-revisados-el-21-de-octubre-de-2026). Se descargaron e instalaron paquetes reales en carpetas temporales, registrando un ejecutable existente, para SpartanPort, inFAMOUS Second Son, Sonic Unleashed, BattleShip, Melee, Time Crisis, Athelas, Two Towers Recompiled, Crash Warped y CTR Native. No se iniciaron los juegos ni sus asistentes y no se midieron FPS. Los paquetes temporales se eliminaron al acabar; no se reemplazaron los juegos del usuario.

Ese recorrido reprodujo tres fallos: CTR Native utiliza rutas con barras inversas en su ZIP, inFAMOUS contiene enlaces internos entre bibliotecas en su tar y Two Towers ofrece varios ejecutables que la detección genérica no podía distinguir. La extracción normaliza las rutas ZIP antes de validarlas, permite enlaces tar contenidos y los vuelve a comprobar después de aplanar el paquete. Two Towers registra el lanzador publicado `TwoTowers.sh`. Las regresiones también rechazan enlaces externos, rutas ZIP que escapan y enlaces que quedarían fuera después de aplanar, conservando la instalación anterior.

Athelas reconoce su ZIP Windows sin etiqueta de plataforma. CTR Native usa el paquete Windows x86 con Proton y tiene un adaptador para el BIN SCUS-94426; se probó la copia a su carpeta de assets con datos ficticios, sin ejecutar código descargado. Time Crisis selecciona su propio AppImage entre los de un release con varios juegos. BattleShip prefiere el paquete general frente a la variante japonesa. Las actualizaciones conservan la elección previa de Proton y las rutas privadas verificadas de los originales. El runtime de Smash Ultimate se identifica como herramienta de compilación y no se instala como un juego portable completo.

La interfaz distingue preparación integrada, asistente del port y preparación manual. La presencia de una ROM asociada solo indica que el archivo existe; la validación de versión/región corresponde al adaptador o al propio port. Las ROMs, BIOS, credenciales, datos personales y registros privados no se incluyen en la distribución.

## 0.19.7 — Captura y edición de perfiles por juego

Se añadieron pruebas de captura efectiva global + por juego para Eden, DuckStation, Dolphin, PCSX2, Azahar y PPSSPP; captura de referencia de mGBA; importación filtrada de INI; aplicación y restauración de PCSX2/Azahar; rechazo de escrituras sin identidad inequívoca; guías manuales sin ejecución; aislamiento por usuario y juego en la API; y pérdida de la verificación integrada al modificar instrucciones o entorno. El esquema JSON se contrastó con el registro de adaptadores.

La interfaz se comprobó a 1280×800 y en los tamaños reducidos de la suite GTK. Se guardó un perfil sin iniciar sesión, se editaron instrucciones y Proton, se comprobó el modo de guía manual, y se accionaron Mostrar separado / Asociar al port con persistencia y sin borrar la ROM. El botón para añadir la propia app a Steam se oculta también en Ajustes al ejecutarse desde Steam. Las filas comunitarias que llegaban por red podían quedar sin distribuir: ahora solicitan distribución al terminar la carga; una regresión comprueba dimensiones visibles de la fila.

En la pantalla física, dentro de la sesión de Escritorio, una copia privada de la biblioteca se abrió a pantalla completa. Un mando virtual Linux con eventos reales leídos por SDL recorrió las cuatro pestañas, las opciones de compartir, lectura y guardado local, B para volver, el catálogo con 60 filas y una ficha de port. Se inspeccionaron capturas privadas de Comunidad y del editor. La biblioteca mostró seis originales asociados sin duplicar su ficha. Esta prueba no equivale a mover las palancas físicas en una nueva sesión de Gamescope.

El servicio desplegado se actualizó conservando su volumen SQLite y la configuración de autenticación. Sobre HTTPS, una cuenta temporal de validación publicó una guía con versión de Proton, consultó Mis aportes, comprobó el aislamiento de pendientes, descargó el perfil tras aprobarlo y validó su identidad. Los tokens, perfiles y cuenta temporales se eliminaron al terminar. Esta comprobación ejercita la sesión de la API; no prueba un nuevo registro, el envío de correo ni una nueva autorización interactiva de Keycloak/GitHub. La sesión local estaba sin iniciar.

La captura real recuperó opciones guardadas de Eden, DuckStation, WiiCompiled, PCSX2 y Azahar. No se aplicaron perfiles a los juegos del usuario ni se ejecutaron juegos. DMC3 Crimson y Shattered Dimensions conservan sus referencias documentadas; Project 2099 Beta 5 usa guía manual y no hereda los ajustes del motor antiguo. mGBA no modifica su configuración global.

## 0.19.8 — Interfaz de Deck y fallos de instalación concretos

Se superaron 776 comprobaciones: 698 de núcleo y 78 de interfaz GTK. El recorrido de instalar y preparar comprueba el inicio del trabajador, la cancelación del constructor y el cierre del progreso. Con filtros plegados, subir desde el primer juego lleva al buscador y permite llegar a Vista y filtros tanto en carátulas como en lista.

Se verificó que el pendiente de la propia app era redundante: los campos del acceso y el contenido del lanzador ya coincidían con Steam. La reconciliación elimina solo ese caso, conserva altas/cambios reales, carátulas, controles y otras entradas, y no escribe el VDF con Steam abierto. La acción explícita para añadir la app también es idempotente.

La biblioteca pliega Vista y filtros; indica cuántos filtros siguen activos y separa Buscar instalados del catálogo. Se reduce el espacio de cabeceras, controles y páginas internas manteniendo fuentes legibles y la acción principal del juego. Comunidad usa una lista a todo el ancho y vistas separadas de perfil, comentarios y opinión; los ajustes pueden leerse sin el panel dividido anterior. B vuelve primero al perfil/lista y conserva el foco. El JSON avanzado para publicar queda plegado. Se corrigió el desplazamiento de palanca derecha que podía conservar el resaltado de una imagen fuera del viewport mientras solo quedaba visible el texto de su tarjeta.

Se descargaron paquetes reales de B2recomp Linux, BLACK XBERecomp V2 y Black Definitive HD V1.3, se verificaron sus hashes y se instalaron temporalmente con ejecutables existentes. El CLI del constructor Linux de Bayonetta 2 se ejecutó con --help y terminó con salida 0; el paquete contiene python3.13, no el enlace python3 mencionado en instrucciones anteriores. El flujo integrado de selección, comando de compilación, cancelación, comprobación del ejecutable y conservación de partidas se prueba con datos ficticios. No se compiló Bayonetta 2 desde un dump real ni se jugaron esos títulos, al no disponer de esos originales en esta revisión.

Un archivo 7z real con un ejecutable mínimo se extrajo y clasificó; las pruebas también rechazan rutas que escapan antes de escribir miembros. La lista y las fichas comunitarias se recorrieron con eventos reales de un mando virtual Linux leídos por SDL en una ventana a pantalla completa de la sesión física de Escritorio a 1280×800. Se abrió un perfil, se regresó con B, se llegó al guardado local y se recorrieron las cuatro pestañas y el catálogo con 60 filas. Las capturas de la biblioteca real son privadas. Esta prueba sigue sin equivaler a controles físicos dentro de una sesión nueva de Gamescope.

### 0.19.9 - Interfaz en la pantalla de la Deck

Se abrió la app en la pantalla real de la Deck (1280×800, escritorio) y se recorrieron Biblioteca, Catálogo, ficha de port, ficha de juego, Actualizaciones y Ajustes con capturas antes y después. Antes: cuatro filas en la Biblioteca, dos tarjetas en el Catálogo, un mensaje fijo que tapaba el final de Ajustes y una ficha de port con pares etiqueta/valor apilados que obligaba a desplazar. Después: ocho filas, cuatro tarjetas y media, mensaje transitorio y ficha de port completa sin desplazamiento. Las 776 pruebas pasan, incluidas las de interfaz sobre un display desechable (tres corridas seguidas); la maximización inicial se omite bajo esas pruebas porque cambia el tamaño de forma asíncrona.

Cobertura de instalación del catálogo (641 de 646 entradas con repositorio de GitHub, consultando el último release o el más reciente si no hay estable y aplicando la misma selección de paquetes de la app): 53,2 % con paquete de Linux, 28,1 % con paquete de Windows para Proton, 5,1 % con paquete sin etiqueta que se identifica al descargar, 2,5 % con receta revisada, 6,1 % sin paquete compatible (Android o código fuente), 5,0 % sin releases publicados o sin archivos. Esto mide si hay algo que descargar e instalar, no que cada juego arranque: no se instaló ningún port nuevo y la mayoría necesita los archivos del juego original.

### 0.19.10 - Prueba de diez ports populares y README bilingüe

Se instalaron diez ports del catálogo, elegidos entre los más valorados en GitHub, en una carpeta personal temporal con el instalador de la app (descarga, extracción, identificación del ejecutable) y se comprobó con el mismo escaneo que usa la biblioteca si cada uno aparece, además de arrancarlos diez segundos en un display remoto.

| Port | Paquete | En la biblioteca | Arranque |
| --- | --- | --- | --- |
| OpenRA | AppImage de Linux | sí (solo el AppImage de Dune 2000; el release trae tres) | abierto a los 10 s |
| OpenRCT2 | AppImage de Linux | sí | abierto a los 10 s |
| DevilutionX | AppImage de Linux | sí | abierto a los 10 s |
| Ship of Harkinian | AppImage de Linux | sí | abierto a los 10 s |
| VCMI | AppImage de Linux | sí | abierto a los 10 s |
| mGBA | AppImage de Linux | sí | abierto a los 10 s |
| Zelda 64: Recompiled | ZIP que envuelve un tar.gz | **no** antes de la corrección; sí después | termina por falta de Vulkan en esa sesión remota (sin DRI3), no por el instalador |
| OpenMW | tar.gz de Linux con muchas herramientas | **no** antes de la corrección; sí después (arranca con el lanzador) | abierto a los 10 s |
| 3D Pinball Space Cadet | ZIP de Windows (Proton) | sí | el proceso del juego aparece bajo Proton |
| Unleashed Recompiled | ZIP de Windows (Proton) | sí | no se arrancó (requiere los archivos del juego) |

Dos fallos reales: un ZIP que solo contiene un tar.gz quedaba sin extraer (el port se instalaba pero no aparecía y el aviso hablaba de «varios ejecutables»), y con varias herramientas del mismo proyecto no se elegía ninguna. Ahora se abre el archivo anidado una vez y, entre varios candidatos, se prefiere el lanzador del proyecto (también si es un script con shebang) y después el binario principal. Límites que siguen: un release con varios juegos instala solo uno (OpenRA), no se reconocen todos los formatos anidados, y que un port arranque no significa que sea jugable: no se probaron audio, mando ni FPS, y varios necesitan los archivos del juego original.

El README de GitHub pasó a tener una sección completa en inglés seguida de otra completa en español; la segunda se genera desde LEEME.md con `tools/sync_readme.py` y una prueba comprueba que coincidan y que el inglés no mezcle prosa en español.

### 0.20.0 - Candidata a 1.0

- **OpenRA con los tres juegos:** con el release real (release-20250330) se instalaron los tres AppImage en 7 s, aparecieron tres entradas distintas (Dune 2000, Red Alert y Tiberian Dawn) y cada una arrancó y cargó su contenido (`d2k-content`, `ra-content`, `cnc-content`) en una sesión remota. Una búsqueda sobre todo el catálogo encontró un solo release más con varios juegos (Serious Sam Classic), pero sus AppImage son variantes de la misma versión y no se tocó.
- **Desinstalar:** pruebas automáticas con un port instalado y una partida dentro de la carpeta: la carpeta pasa a `~/ports/.deck-library-removed`, la partida se recupera de ahí, el port deja de figurar en el registro, en la biblioteca y en el escaneo, y se rechazan las carpetas fuera de `~/ports` y Project 2099. No se probó el retiro del acceso de Steam con una cuenta real (se reutiliza la cola de eliminación existente).
- **Revisión del catálogo:** etiqueta Revisado / Sin revisar y confirmación única antes de instalar un port sin revisar, con pruebas de interfaz.
- **Instalación limpia y actualización:** el paquete 0.10.1 publicado se instaló en un HOME temporal, se creó una biblioteca de ejemplo y se instaló encima el paquete 0.20.0: la versión pasó de 0.10.1 a 0.20.0, la biblioteca y los ajustes se conservaron y la app quedó abierta 14 s sin errores; una instalación nueva en otro HOME hizo lo mismo y creó el acceso de escritorio y el del menú.
- Las pruebas automáticas y de interfaz pasan (ver el conteo en las notas de la versión). Lo que sigue sin comprobarse está en [V1-CHECKLIST.md](V1-CHECKLIST.md): navegación con mando físico en modo Juego y jugar un port de punta a punta con audio, mando y FPS.

### 1.0.0 - Interfaz en inglés

- **Cómo funciona:** el código y las claves siguen en español y la traducción se aplica en el punto donde el texto llega a un widget (etiquetas, botones, ayudas, títulos, listas desplegables, nombres accesibles, enlaces, expansores), de modo que la lógica que compara textos no cambia. El catálogo (`deck_library/i18n_en/*.json`) tiene alrededor de 1 600 textos; los que se arman con variables se traducen por patrón y los fragmentos concatenados por trozos. Los nombres de juegos, rutas y datos de catálogos externos no se tocan.
- **Cobertura:** `tools/i18n_extract.py --missing` recorre el código y los presets y una prueba exige que no quede ningún texto sin traducir (se detectó que los textos de una sola palabra sin tilde, como los nombres de pestañas, escapaban a la primera extracción y se completaron a mano). Además se recorrió la app en inglés sobre una sesión remota con registro de todo texto sin traducir que llegaba a un widget: Biblioteca, Catálogo, ficha de un port, Actualizaciones, Ajustes, apariencia, instalaciones, originales, asistente inicial y las cuatro secciones de juegos de Switch, PlayStation, Linux, Minecraft, Windows y 3DS. Lo que quedó sin traducir son nombres de juegos, plataformas, rutas y claves técnicas.
- **Idioma por defecto:** una instalación existente conserva el español; una nueva sigue el idioma del sistema; se cambia en Ajustes → Carátulas y apariencia (hay que reabrir la app) y `DECK_LIBRARY_LANG` lo fuerza. El idioma de la línea de comandos sigue la misma regla.
- **Límites:** no se revisaron en inglés las pantallas que solo aparecen al fallar una operación real (la mayoría de los errores), ni se midió el ancho de cada texto inglés en 1280×800 más allá de las pantallas recorridas; las traducciones de los textos técnicos de los emuladores son mías y no pasaron por una persona que hable inglés nativo. Las dos pruebas con la Deck en modo Juego (mando físico y un port jugado de punta a punta) se omitieron por decisión para esta versión y siguen sin hacerse; ver [V1-CHECKLIST.md](V1-CHECKLIST.md).

### 1.0.1 - Correcciones tras probar la 1.0 en modo Juego

- **Qué se probó:** la app abierta como lo hace Steam en modo Juego (pantalla completa y con un identificador de aplicación de Steam) sobre la pantalla real de la Deck, abriendo la ficha de Mario Kart 8 y pulsando Jugar; un gamescope anidado no pudo arrancar en esta sesión (Xwayland falla), de modo que el modo Juego real sigue sin probarse.
- **Cartel al abrir un juego:** al pulsar Jugar en un juego que está en Steam se ve el aviso «Starting game» del propio Steam sobre la ficha, y además Deck Library mostraba su banner «Se solicitó abrir…» arriba. Se quitó el banner de Deck Library y el botón recupera el foco al terminar; el aviso de Steam no depende de la app.
- **Actualizaciones sin detalle y sin desplazamiento:** las secciones plegables no eran enfocables con el mando, de modo que ni «Novedades» ni «Opciones de actualización» se podían abrir. Ahora se enfocan, se abren con A y su contenido entra en la navegación. Cada port muestra además las primeras líneas de sus notas sin abrir nada (se comprobó que las notas de los tres ports pendientes se descargan: 201, 4 276 y 7 793 caracteres).
- **Ajustes de la comunidad:** el servicio devolvía los perfiles de Deck Library como propuestas y la ficha los repetía; se filtran por autor y por identificador. «Otros perfiles» ya no muestra perfiles incluidos de Deck Library (el cuarto, «Compatibilidad») sino solo los del usuario.
- **Cuenta:** botón visible para registrarse o iniciar sesión (barra superior y ficha) y nombre de usuario con sesión iniciada. La sesión ya se guardaba en un archivo con permisos 0600; no se probó un inicio de sesión real porque requiere una cuenta.
- **Arte e icono:** icono nuevo y arte para Steam, dibujados con formas planas; se comprobó el aspecto de cada imagen y que solo se rellenen espacios vacíos.
- **Mario Kart 8 no carga:** en una ejecución de prueba lanzada desde Steam, Eden se cerró solo a los 4 s (volcado de memoria) con escrituras en memoria sin asignar, antes de llegar a los gráficos; es el mismo patrón que mostró Breath of the Wild con sus mods. Una ejecución en la sesión remota, con y sin el mod CTGP Deluxe, no reprodujo la caída (esa sesión no puede dibujar con Vulkan), así que la causa no está confirmada; la sospecha principal es el mod instalado en `load/`.

### 1.0.2 - Etiqueta flotante sobre la ficha

Al recorrer la lista con el mando y pulsar X para abrir un juego, el puntero inactivo quedaba sobre el título de la ficha y aparecía la ayuda emergente con el nombre completo, tapando las pestañas y los perfiles. Con mando ahora se desactivan las ayudas emergentes (`gtk-enable-tooltips`) y, con ratón, el nombre completo solo aparece cuando el título está recortado. Se probó el comportamiento con pruebas automáticas (la ayuda solo se ofrece con el texto recortado y nunca en modo mando; el ajuste global se apaga); no se reprodujo el cartel original en el modo Juego real, que sigue sin probarse en esta sesión.

### 1.0.3 - Actualización de la app

- **Aviso azul que no desaparecía:** la búsqueda de actualizaciones se guarda en caché durante 6 horas; tras actualizar y reiniciar, la oferta de la versión ya instalada seguía en esa caché y el aviso «disponible» reaparecía. La oferta se descarta al leer la caché si no es más nueva que la versión en ejecución (prueba automática añadida).
- **App bloqueada tras actualizar:** no se logró reproducir (se instaló y reinició desde la sesión remota y la app nueva abrió su ventana). Como causa probable, el instalador reemplaza archivos mientras la app en ejecución todavía importa módulos nuevos, mezclando dos versiones; ahora se importan todos los módulos antes de instalar. En la ficha de actualizaciones, tras instalar, se ofrece «Reiniciar» en lugar de volver a instalar. Pendiente de confirmar en la Deck real.
- **No comprobado:** la configuración de controles de Eden (los perfiles no tocan controles a propósito) y Mario Party Jamboree no se tocaron en esta versión.

### 1.0.4 - Modo Juego y mando de la Deck en Eden

- **Actualizar en modo Juego:** la app se reiniciaba a sí misma lanzando una copia nueva fuera de la sesión de Steam, que quedaba sin ventana utilizable. En modo Juego (también con `--gaming`) ya no se instala desde la app ni se relanza; se pide abrirla en modo Escritorio y «Reiniciar» solo cierra. Verificado con pruebas y por lectura del código; no se reprodujo el cuelgue en modo Juego real.
- **Mando de la Deck en Eden:** tras aplicar un perfil o guardar opciones de un juego de Switch se comprueba el jugador 1 de `qt-config.ini`; si no tiene mapeada la Deck (o usa otro dispositivo) se ofrece actualizarlo, con copia de seguridad y sin tocar otras claves (se recuerda si se rechazó). El bloque generado es idéntico clave por clave al de la configuración funcional de esta Deck. No se comprobó con una Deck que parta de cero.
- **Super Mario Party Jamboree:** en la pantalla real de la Deck el juego abre y llega a la introducción con la actualización 2.2.0 y sin mods; el registro muestra un aviso crítico de la applet de mando (`ControllerSupportMode=1`) que no detuvo la ejecución. No se reprodujo el fallo de otra Deck; causas sin confirmar: mando sin mapear, claves o firmware distintos.

### 1.1.0 - Compatibilidad de ports y más conflictos

- **Compatibilidad estimada en Ports:** cada port del catálogo muestra una etiqueta «Compatibilidad N% · Alta/Media/Baja/Muy baja» y, en su ficha, los motivos. Se calcula sin descargar nada, solo con los datos del catálogo: revisado por Deck Library (88), versión para Linux (72), solo Windows con Proton (50), sistemas sin declarar (40), solo Android u otros (8), solo código fuente (8), más o menos puntos según el estado que informa la fuente, la antigüedad de la última versión y si exige archivos originales. Sobre los 641 ports del catálogo actual: 87 altas, 252 medias, 201 bajas y 101 muy bajas. **Es una estimación, no una prueba de juego:** los pesos son una decisión de criterio y no se contrastaron con instalaciones reales de todo el catálogo.
- **Conflictos nuevos** en «Coincidencias e instalaciones»: dos configuraciones de Eden (AppImage y Flatpak, indicando cuál edita Deck Library), partidas de Eden en dos carpetas, otros emuladores de Switch instalados junto a Eden, jugador 1 de Eden con otro dispositivo, Eden abierto y varias copias de Deck Library. Probado con carpetas temporales; en esta Deck solo apareció la de varias copias de la app. Los demás casos no se vieron con instalaciones reales.
