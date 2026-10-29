# Interfaz y modo Juego

## Vista actual (1.4.7)

Todas las fichas usan **Ajustes**, **Controles** y **Juego y archivos**, con un único botón **Comunidad**. La cabecera mantiene Jugar, Steam, Eliminar y Más opciones. El desplegable agrupa edición avanzada, creación/importación/exportación de perfiles, valoración, restauración del perfil anterior, favoritos, carátulas y ayuda. La versión de Proton se consulta o cambia en Juego y archivos, según quién administre el acceso.

La biblioteca vuelve a detectar instalaciones en segundo plano cada 45 segundos; no repite ajustes de ports ni sustituye un formulario abierto. Las bandejas de solicitudes y los listados comunitarios abiertos se consultan cada 20 segundos, conservando borradores y evitando reconstruir resultados iguales. No hay botones de recarga manual en esas vistas. El catálogo de ports y la búsqueda de versiones de Deck Library usan una caché de 15 minutos; las versiones de ports se consultan por hora. La instalación de versiones nuevas sigue las opciones de actualización configuradas.

Shattered Dimensions ofrece un botón de preparación de audio. El idioma se conserva por defecto; cambiarlo es una opción explícita. Ver [requisitos y alcance del arreglo](SPIDER-MAN-SHATTERED-DIMENSIONS.md). Las pruebas de interfaz usan pantallas virtuales a 1280×800 y 840×640; no equivalen a una nueva sesión física de juego.

## Referencia histórica: 0.19.5

- Navegación superior: Biblioteca, Ports, Actualizaciones y Ajustes. Biblioteca a ancho completo, carátulas verticales, lista con miniaturas y agrupación por plataforma. No hay barra lateral.
- La ficha abre una vista de juego con carátula y fondo derivado de esa imagen, **Jugar** en verde y Steam en azul. **Ajustes del juego** ofrece tarjetas seleccionables con objetivo, valores legibles y estado de prueba declarado por su autor. Seleccionar no modifica archivos. **Ver cambios** despliega la lista de diferencias; **Aplicar ajustes** y **Deshacer** permanecen en una barra fija. Las pestañas Ajustes, Controles, Contenido o Archivos y Steam, y Avanzados permanecen visibles. Comunidad tiene un botón propio en esa barra.
- **Controles**, **Contenido** y **Avanzados** son tareas separadas con regreso explícito a la vista del juego. **Más opciones** agrupa importación, exportación, carátulas, archivos y diagnóstico. La edición manual habilita Guardar solo cuando hay cambios, conserva el formulario durante actualizaciones de detección/carátulas y pregunta antes de descartar ediciones sin guardar.
- Entrada de cabecera y tarjetas, navegación entre tareas, despliegue de diferencias, estados de selección y confirmaciones usan animaciones finitas. Se respeta **Ajustes → Carátulas y apariencia → Animaciones**. En pantallas de hasta 820 px de alto, la cabecera se reduce a una fila con regreso, título, Jugar, Steam y Más opciones. Los ajustes usan todo el ancho sin una columna lateral. El texto principal tiene 17 px y la información secundaria, al menos 14–15 px. Los perfiles pasan a una columna en ventanas estrechas. Al abrir una ficha el foco empieza en Jugar; Escape vuelve de la tarea al juego y luego a la biblioteca.
- Referencia de interacción inspeccionada a pedido del usuario: [SpotiFLAC de escritorio](https://github.com/spotbye/SpotiFLAC), especialmente [AlbumInfo](https://github.com/spotbye/SpotiFLAC/blob/main/frontend/src/components/AlbumInfo.tsx), [botones](https://github.com/spotbye/SpotiFLAC/blob/main/frontend/src/components/ui/button.tsx) y [dependencias del frontend](https://github.com/spotbye/SpotiFLAC/blob/main/frontend/package.json) (React, Radix UI, motion). Deck Library conserva su implementación nativa en GTK/Python, sus adaptadores y la instalación sin sudo. Los componentes e íconos de esta ficha son propios; no se incorporó el código del descargador ni sus servicios.
- El botón superior «Añadir Deck Library a Steam» aparece en modo Escritorio y se oculta al iniciar desde Steam o con `--gaming`. Los botones para agregar cada juego a Steam siguen disponibles.
- Los cambios de Steam se acumulan sin diálogo de reinicio. El aviso nombra la operación cuando solo hay una. «Ver cambios» muestra cada juego, carátula o perfil de mando y permite descartar el lote. El acceso de Deck Library preparado durante la instalación aparece con ese motivo explícito. Abrir la app no crea operaciones nuevas.
- Se retiró «Preferir ports»: tener un port ya no oculta la copia emulada.
- La revisión de biblioteca separa posibles copias de ROMs e instalaciones alternativas. Resuelve enlaces e identifica archivos por dispositivo/inodo. No cuenta scripts ni lanzadores de EmuDeck como otros emuladores y nunca ejecuta esos scripts para inspeccionarlos. No compara hashes de ROMs ni borra archivos.
- Las actualizaciones conservan el changelog del autor y lo consultan por tag si la caché anterior no lo tenía. Las imágenes remotas y el HTML de las notas no se renderizan. Cuando no hay notas disponibles, se ofrece la publicación original. [API oficial de releases](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name).
- **Ajustes → Deck Library en Steam → Agregar a Steam** crea el acceso `--gaming`, a pantalla completa, y asigna a Steam Deck una plantilla propia con gamepad nativo y trackpad para el puntero: cruceta/stick para navegar, A para activar, B para volver, LB/RB para secciones; con entrada SDL2, X abre el teclado en la búsqueda, trackpad derecho como puntero y gatillo derecho para clic. Steam + X abre el teclado de Steam. Se conserva el acceso del escritorio y los datos entre versiones.
- La integración es una app normal de Steam, no un plugin de Decky. No requiere Decky ni AppImage; usa Python/GTK de SteamOS. Aún requiere prueba física de navegación en modo Juego y de todos los diálogos con el teclado de Steam abierto.
- **Idioma y controles** detecta el idioma emulado de Eden y permite un override por juego, con respaldo. No cambia el idioma de su interfaz. Para el mapeo de mandos y otros emuladores, abre su editor original; no escribe controles arbitrarios ni presupone dispositivos iguales. Referencia: [enumeración de idiomas de Eden](https://github.com/eden-emulator/mirror/blob/master/src/common/settings_enums.h).
- Comunidad es opcional. Funciona el catálogo local/GitHub sin cuenta; el servicio añade publicación autenticada y feedback. Ver [servicio](../community/README.md).

El catálogo abre directamente. Los perfiles muestran estrellas reales y una publicación guiada; la cuenta propia usa Keycloak en el navegador. Las actualizaciones tienen una barra por port y ETA medida durante la descarga. La biblioteca y el catálogo se reutilizan al navegar. SDL2 agrega soporte nativo para mandos, repetición de direcciones y protección frente a la doble activación de Steam Input.

## Pantalla de la Deck (0.19.9)

- En pantallas de hasta 1400×900 la ventana se abre maximizada y las filas ganan densidad: la lista de la Biblioteca usa miniaturas de 36×54 (unas ocho filas visibles en 1280×800 en lugar de cuatro) y las tarjetas del catálogo bajan a unos 88 px de alto.
- El mensaje de estado inferior es transitorio: se oculta a los 7 segundos y no reserva espacio mientras está vacío (antes tapaba el final de Ajustes y de la ficha).
- El botón de cabecera pasó a «Añadir a Steam» en estilo discreto (el texto completo está en su ayuda); el botón azul principal de la pantalla queda para la acción de cada vista.
- Catálogo: el encabezado ocupa una sola fila y la lista carga de 30 en 30 con **Mostrar más** en lugar de cortar en 60. La ficha de un port muestra título, nombre del port y una línea con plataforma, sistemas y fuente; el botón de reintentar imagen solo aparece si falló.
- Los botones de sección de la ficha de juego (Controles, Archivos y Steam, Avanzados, Comunidad) comparten un estilo neutro; el color queda para **Jugar**, Steam y **Aplicar ajustes**.
- El texto de la interfaz y de los documentos usa español impersonal: se retiraron las formas con voseo («elegí», «podés», «revisá») de los mensajes, las recetas y LEEME.



## TodoJuegos y navegación superior — 1.2.0

La referencia entregada por el usuario es TodoJuegos 1.2 (React/Electron). Se trasladó su tema Negro, su jerarquía de títulos, sus superficies con borde discreto y sus tarjetas al frontend nativo GTK de Deck Library. Se conservan el motor Python, los instaladores, los presets, la cuenta comunitaria y los accesos de Steam. No se incorpora el ejecutable Windows, node_modules ni los datos de TodoJuegos.

La cabecera mantiene Inicio, Biblioteca, Ports, Actualizaciones y Ajustes en una fila superior, sin barra lateral. En ventanas estrechas se puede desplazar horizontalmente. La propia app se puede añadir a Steam desde Escritorio; esa acción permanece oculta en modo Juego. Inicio muestra contadores reales, ports instalados, espacio de la unidad personal y herramientas. En Apariencia se puede elegir abrir Resumen o Biblioteca. No se calcula un supuesto tamaño de colección a partir del espacio de la unidad.

La Biblioteca ofrece carátulas verticales, lista con miniaturas y agrupación por plataforma; conserva la vista elegida por el usuario. El Catálogo usa tarjetas en una cuadrícula adaptable, con imágenes horizontales que llenan el área disponible, nombre del juego, proyecto, sistemas y acciones. El progreso de instalación sigue en la tarjeta correspondiente; los detalles y las confirmaciones permanecen dentro de la ventana. Las fuentes Manrope y Space Grotesk se cargan solo para este proceso, desde archivos locales con sus licencias OFL; no se instalan fuentes en SteamOS.

Cada tarjeta del catálogo muestra el requisito de originales cuando está revisado: por ejemplo SLUS-00875, SLUS-01378 Rev 1, SCUS-94426, RMCP01 PAL, CUSA00223 con actualización 1.07 o una versión de Switch. El buscador incluye esa etiqueta. La ficha amplía región, formato y revisión y enlaza al proyecto. Las entradas sin requisito revisado muestran «ROM por confirmar»; un nombre parecido o un campo recibido de una lista externa no se convierte en un requisito confirmado. Un Title ID de Xbox 360 se distingue de una revisión concreta del disco.

LB/RB recorre las cinco pestañas, la palanca izquierda mueve el selector y la derecha desplaza la vista. B vuelve desde una tarea al juego y luego al origen; desde una ficha abierta en Inicio vuelve al mismo port de Inicio. X abre el teclado de forma explícita y, desde Inicio, lleva al buscador de Biblioteca. Se conservan la inhibición del teclado automático, el desplazamiento táctil y las animaciones opcionales; las transiciones de página siguen deshabilitadas en Gamescope por la limitación documentada de GTK Stack.


## Etiquetas y perfiles compactos (1.2.1)

Las etiquetas del catálogo separan por color sistemas, categoría, revisión, fecha de incorporación, requisitos de originales e instalación. La compatibilidad estimada conserva su cálculo, porcentaje y nivel; se muestra en verde, amarillo, naranja o rojo según sea alta, media, baja o muy baja. Los colores tienen texto propio y contraste comprobado. La ficha usa las mismas etiquetas. **Guía de compatibilidad** en el catálogo y **Cómo se calcula** en la ficha abren una página interna con los rangos, las bases y los ajustes exactos. Explica que el porcentaje es un índice orientativo con pesos elegidos por Deck Library; no es una probabilidad medida, una tasa de éxito ni una medición de FPS.

Las tarjetas de perfiles muestran nombre, resumen, verificación y valoración. Objetivo, procedencia, autor, versiones, notas e instrucciones aparecen en el desplegable del perfil seleccionado, junto con los cambios previstos. El desplegable empieza cerrado; los perfiles manuales mantienen sus instrucciones abiertas. Seleccionar o desplegar no aplica ajustes. El botón Aplicar sigue fijo y el control del desplegable funciona con mando.


## Inicio y biblioteca completa (1.2.4)

Las instalaciones sin una elección explícita de página inicial abren Biblioteca. La elección Resumen de Apariencia se respeta. Inicio muestra todos los ports del resumen, con carátulas verticales 2:3 y desplazamiento normal con rueda; desaparece el límite de cuatro miniaturas horizontales. El contador de ports excluye las copias del propio programa que tampoco aparecen en esa sección.

Abrir Inicio empieza arriba. Una actualización de la detección conserva su posición de desplazamiento y regresar desde una ficha conserva el port seleccionado. El inicio del mando enfoca la página visible. No se modifican ROMs, ajustes de juegos ni la vista de biblioteca elegida por el usuario.

## Versión y actualizaciones (1.2.6)

La esquina inferior derecha muestra siempre la versión que está ejecutándose. Indica si hay una actualización, si terminó de instalarse y falta volver a abrir la app, si la consulta falló o si la búsqueda automática está desactivada. Actualizaciones también muestra la versión en uso; el indicador permite reconocer una captura de una copia antigua.

La consulta de la app se entrega a la interfaz antes de esperar las consultas de ports. Tiene una caché independiente de una hora, invalidada al cambiar la versión en ejecución, y vuelve a intentar los errores tras un minuto. El catálogo de actualizaciones de ports conserva su intervalo de seis horas. La página se refresca cuando llegan resultados, aunque la consulta haya empezado automáticamente. Un fallo de red no borra una actualización previamente detectada ni se muestra como «Al día».

Si la API de GitHub falla, la app consulta la redirección pública de la última publicación del mismo repositorio. Valida el dominio y la ruta de la versión; los paquetes se siguen verificando con el archivo SHA-256 publicado. No hace falta un token de GitHub para usar esta alternativa.

Se puede instalar la actualización desde modo Juego. La app espera si hay otra instalación o un asistente activo. Después se vuelve a abrir Deck Library; en modo Juego, el botón la cierra para abrirla otra vez desde Steam. El instalador renueva el acceso existente del escritorio y el lanzador administrado de Steam para que apunten a la instalación actual, conservando el AppID, las carátulas personalizadas y los metadatos del acceso. No modifica accesos manuales desconocidos ni otras apps.

Los cambios de biblioteca pendientes en Steam son una cola separada: accesos, imágenes o controles. Por ejemplo, renovar las cinco imágenes oficiales de Deck Library puede producir cinco operaciones pendientes sin que el usuario haya editado cinco juegos. Se muestran una sola vez con su detalle y se aplican cuando Steam está cerrado. La actualización del código de la app no necesita reiniciar Steam; el cliente sí necesita cerrarse para aplicar esa cola de imágenes.

## Legibilidad y objetivos táctiles en la Deck

- El texto más pequeño de la interfaz pasó de 13 a 15 px y el secundario de 14 a 16 px. Botones, campos y desplegables miden unos 48 px de alto, y las casillas 24 px, para pantalla táctil y mando.
- **Ajustes → Carátulas y apariencia → Tamaño de la interfaz** ofrece Normal, Grande (×1,15) y Muy grande (×1,3). Escala todos los tamaños de fuente y se aplica al guardar, sin reiniciar.
- Cuenta y Ayuda usan el estilo discreto: el registro es opcional y ya no es lo más llamativo de la cabecera. Las pestañas de la ficha de juego son neutras; el color queda para Jugar, Steam y Aplicar ajustes.
- Nombres unificados: la página de inicio se llama **Inicio** en todas partes (antes «Resumen»), la pestaña de la ficha es **Perfiles** (antes «Ajustes», que también es el menú de la aplicación), **Actualizar biblioteca** reemplaza a «Buscar instalados» y **Ayuda** reemplaza a «Guía de uso».
- Un juego sin perfiles ya no reserva la barra fija «Aplicar ajustes». La carátula de relleno de una miniatura muestra una inicial en vez de texto cortado. Las etiquetas del catálogo se agrupan de a dos por fila para que entren tres tarjetas en 1280 px.

## Catálogo, biblioteca vacía y Steam pendiente

- Las tarjetas del catálogo ya no muestran el porcentaje de compatibilidad: una frase llana indica si es **Listo para instalar**, **Se instala con Proton** o **Solo código fuente**, y las etiquetas quedan en plataforma, revisión, variantes y «Nuevo». El índice y su explicación siguen en la ficha del port y en la Guía de compatibilidad. «Juegos validados» comparte fila con esa guía en lugar de ocupar una fila propia.
- La biblioteca vacía explica qué es un port y ofrece tres acciones: buscar juegos instalados, instalar un port del catálogo y elegir carpetas de juegos.
- Un juego con un acceso de Steam pendiente muestra **Pendiente en Steam** en su carátula y en su botón; la pantalla de cambios pendientes explica en una frase qué hacer según el modo.
- **Ajustes → Juegos de Switch** (y un botón en la ficha de Savage Wind y Bayonetta 2) abre la conversión de NSP/XCI a `exefs` + `romfs`; ver [PORTS.md](PORTS.md).

## Temas, favoritos, verificados y solicitudes

- **Temas Negro y Claro** (Ajustes → Carátulas y apariencia → Tema). Los colores salen del degradado del logo (azul `#4780cd` a violeta `#6152b6`); los botones principales (Jugar, Aplicar) usan ese degradado con texto blanco. Negro conserva el fondo casi negro, bueno para el panel OLED; Claro invierte superficies y etiquetas y usa un contorno oscuro en el logo. Hay pruebas de contraste (texto, acento, botones y etiquetas de colores) para ambos temas.
- **Favoritos y orden.** Cada ficha tiene **Marcar favorito**; la biblioteca se ordena por nombre, por **jugados hace poco** o con los favoritos primero. Inicio muestra **Continuar jugando** con los últimos juegos abiertos (se anotan en un archivo aparte, `played.json`, para que ningún guardado de ajustes los borre). Las carátulas indican «★ Favorito», «Necesita preparación», «En Steam» o «Pendiente en Steam».
- **Perfiles.** Cada tarjeta dice para qué está pensada («Imagen y fluidez parejas…», «Pensado para ganar fluidez…», «Pensado para una imagen más nítida…»; es la intención de los ajustes, no una medición) y marca **Recomendado** al favorito. **Aplicar y jugar** guarda el perfil con respaldo y abre el juego.
- **Verificados por Deck Library** (antes «Juegos validados»). Cada juego comprobado muestra **qué se arregló**, cómo se aplica (lo hace Deck Library, perfil incluido o guía manual) y la evidencia. Ahora incluye GTA IV y Spider-Man: Shattered Dimensions, ambos como confirmación de experiencia de usuario.
- **Pedir un juego** (en Verificados y en Ayuda): nombre, plataforma y qué falla. No se aceptan juegos, archivos ni enlaces; se intenta que funcione y, si se logra, el arreglo se publica sin incluir el juego. Solo la cuenta del propietario ve lo recibido (Ajustes → Solicitudes recibidas); ver [community/README.md](../community/README.md).
- **Etiquetas del catálogo:** plataforma, requisito de ROM, sistema y estado se muestran sobre la imagen de cada tarjeta; debajo quedan el título, la descripción y el estado de la integración.

## Herramientas, páginas sin ventanas y carpeta DeckLibrary (1.4.1)

- **Herramientas** es una pestaña nueva con las acciones que no son ajustes: **Convertir un juego de Switch** (NSP/XCI a `exefs` + `romfs`), **Extraer una ISO de Xbox o Xbox 360** (verificada, la ISO no se modifica), ROMs y ports instalados, duplicados y conflictos, agregar Deck Library a Steam (solo en Escritorio), reportar un problema y, solo con la cuenta del propietario, las solicitudes recibidas. **Ajustes** queda agrupado en General, Biblioteca y Mantenimiento.
- **Ports de Switch:** el asistente de Bayonetta 2 ofrece **Convertir un XCI o NSP** además de elegir la carpeta, y al instalar Savage Wind (Breath of the Wild) la app propone convertir el juego en ese momento.
- **Sin ventanas.** Ayuda es una página de la ventana (la pestaña queda marcada) y todas las páginas internas (reportar, convertir, extraer, pedir un juego…) muestran una **flecha arriba a la izquierda** en lugar del botón Volver. B en el mando vuelve igual.
- **Mando:** Y abre las opciones del juego (o los filtros de la biblioteca) y Menú abre los filtros.
- **Avisos y versión.** El aviso de actualizaciones tiene una ✕ para cerrarlo y reaparece solo si cambia. La versión ya no ocupa una fila: está al final de Ajustes y en Actualizaciones.
- **Verificados** muestra una carátula en cada juego (la de la biblioteca o la del catálogo si existe; si no, el cartel con su nombre).
- **Carpeta `~/DeckLibrary`** con `ports`, `roms`, `switch` e `iso`. Los ports nuevos se instalan en `~/DeckLibrary/ports`; si `~/ports` ya tiene instalaciones se sigue usando esa carpeta sin moverla. Los ROM puestos en `~/DeckLibrary/roms` se detectan además de los de EmuDeck.
