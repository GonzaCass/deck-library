# Console UI preview / Vista previa de la interfaz

The home screen features a game from the local library, ordered by last played,
with a shelf of up to 16 games and direct play and favorite actions. The full library
uses covers with integrated titles. Four primary tabs keep navigation short;
the **…** menu contains validated games, updates, tools, account, help and the
Deck Library Steam shortcut action. Settings and game pages share the new theme.

Settings and Tools keep each action beside its description in a selectable row.
Display, language and text size appear first in Appearance; the optional cover
provider settings remain in a disclosure. Buttons, game tabs, forms, menus and
profile cards share neutral surfaces and moderate corner radii, with a contrasting
primary action. Narrow game headers place the title above the actions.

Close the installed app, extract the preview archive and run `sh Probar-UI.sh` in that folder from Desktop
Mode. This opens the extracted code without running the installer. To test in
Gaming Mode, add **Probar-UI.sh** as a separate non-Steam shortcut and set its
launch options to `--gaming`. The preview uses the existing local library and
settings. Changes made through the preview, such as favorites, are saved.
Automatic app and port installation is disabled for that preview session; this
does not change the saved update preferences. Close the preview and open the
installed app to return to the regular version. No upgrade is required.

Controls: A opens a focused game or activates a button; Y toggles the featured
game's favorite on Home; X opens library search; Start opens the featured game's
details; LB/RB cycles local sections inside a game or port, and the four primary
tabs elsewhere. B returns from a game to the same
cover. The **…** menu is reachable with the D-pad, touch or trackpad.

Artwork and play history come from the local library. Missing covers use a
patterned fallback. Library membership does not certify that a game is configured,
boots or runs at a particular frame rate. Physical Steam Deck input, installation
and gameplay require separate device validation.

## Español

El inicio muestra un juego de la biblioteca local, ordenada por último jugado,
con una fila horizontal de hasta 16 juegos y acciones para jugar y marcar favoritos.
La biblioteca integra los títulos en las carátulas. La barra tiene cuatro
pestañas principales; el menú **…** reúne verificados, actualizaciones,
herramientas, cuenta, ayuda y la acción para agregar Deck Library a Steam.
Los ajustes y las fichas de juego comparten el nuevo tema.

Ajustes y Herramientas reúnen cada acción con su descripción en una fila
seleccionable. Apariencia muestra primero pantalla, idioma y tamaño del texto;
el proveedor de carátulas queda en una sección desplegable. Botones, pestañas
de juego, formularios, menús y perfiles comparten superficies neutras y controles
con esquinas moderadas, con una acción principal de mayor contraste. En ventanas angostas,
el título del juego aparece sobre las acciones.

Cerrar la app instalada, extraer el archivo de prueba y ejecutar `sh Probar-UI.sh` desde esa carpeta en
Modo escritorio. Se abre el código extraído sin ejecutar el instalador. Para
probar en Gaming Mode, agregar **Probar-UI.sh** como un acceso directo separado
de un juego ajeno a Steam, con `--gaming` en las opciones de lanzamiento.
La prueba usa la biblioteca y los ajustes existentes. Los cambios realizados,
como los favoritos, se guardan. La instalación automática de actualizaciones
de la app y los ports queda desactivada durante esa sesión; las preferencias
guardadas de actualización se conservan. Para volver a la versión habitual,
cerrar la prueba y abrir la app instalada. No requiere actualizar la instalación.

Controles: A abre la ficha del juego enfocado o activa un botón; Y cambia el
favorito del juego destacado en Inicio; X abre la búsqueda; Start abre la ficha
del destacado; LB/RB recorre las secciones de la ficha o las pestañas principales
fuera de ella. B vuelve desde la
ficha a la misma carátula. El menú **…** se puede usar con cruceta, pantalla
táctil o trackpad.

Las imágenes y el historial provienen de la biblioteca local. Sin carátula se
muestra un fondo con diagonales. Estar en la biblioteca no certifica preparación,
arranque ni FPS. Los controles físicos de Steam Deck, la instalación y el juego
requieren validación por separado en el dispositivo.

## Validation / Validación

The initial home-preview GTK checks covered 165 cases: 164 passed and the SDL2 virtual joystick case
was skipped because SDL2 was unavailable. Checks ran in batches under virtual
X11, with a test-only image-loader workaround that is excluded from the archive.
Visual review covered 1280×800 and 840×640, including English, the light theme
and the largest interface text size. The extracted archive rendered the home,
menu, library and game pages with fictional data. Shell launchers, file modes,
archive contents and the SHA-256 checksum were checked.

The initial general suite discovered 1,153 tests: 982 passed, 169 were skipped and two
existing ROM-location checks failed. Those same failures were reproduced on
the unchanged base revision `60a32a2`. Installation on Steam Deck, physical
controller input and gameplay have not been validated by these checks.

La primera revisión del inicio cubrió 165 casos de GTK: 164 aprobados y uno omitido porque SDL2
no estaba disponible para el mando virtual. Se ejecutaron por grupos bajo X11
virtual, con una adaptación de prueba para el cargador de imágenes que no se
incluye en el archivo. La revisión visual cubrió 1280×800 y 840×640, incluidos
inglés, tema claro y el mayor tamaño de texto. El archivo extraído permitió
renderizar inicio, menú, biblioteca y ficha con datos ficticios. Se comprobaron
los lanzadores, los permisos, el contenido del archivo y su suma SHA-256.

La suite general inicial detectó 1.153 pruebas: 982 aprobadas, 169 omitidas y dos fallos
existentes de ubicación de ROMs. Los mismos fallos se reprodujeron en la revisión
base sin cambios `60a32a2`. Estas pruebas no validan instalación en Steam Deck,
controles físicos ni juego.

The subsequent interface consistency review covered 167 GTK cases: 166 passed
and the SDL2 virtual joystick case was skipped. The compact workspace and
profile checks were repeated after layout adjustments. The seven theme checks
passed; translation coverage reported no missing strings. All main pages and
the Appearance form were rendered at 1280×800 and at 840×640 with English,
the light theme and the largest text size. Device validation remains pending.

La revisión posterior de coherencia visual cubrió 167 casos de GTK: 166 aprobados
y el caso del mando virtual omitido por falta de SDL2. Se repitieron las pruebas
de ventanas compactas y perfiles después de ajustar el espacio. Las siete
pruebas de tema pasaron y no se detectaron traducciones faltantes. Se renderizaron
las pantallas principales y Apariencia en 1280×800 y en 840×640 con inglés,
tema claro y texto al máximo. La validación en el dispositivo sigue pendiente.

The rectangular-control revision reduces buttons to small corner radii and
uses underlined primary navigation. Eight focused GTK checks and all seven
theme checks passed. The main pages were rendered again at both viewport sizes.

La revisión de controles rectangulares reduce las esquinas de los botones y usa
subrayado en la navegación principal. Pasaron ocho pruebas específicas de GTK
y las siete pruebas de tema. Se volvieron a renderizar las pantallas principales
en ambos tamaños de ventana.

## Interactive sample library / Biblioteca de muestra interactiva

From the project folder on a GTK 3 desktop, run
`python3 tools/preview_console.py --interactive --real-games --download-artwork`.
The optional real-game fixtures contain 12 known titles across PC, Switch,
PlayStation 2 and Wii. Only public cover images and backgrounds are downloaded;
the ignored local artwork cache is excluded from source releases. No original
game files are included, installed or launched. The window is marked DEMO.
Manual game options are simulated in memory and the sample library is temporary.
This is separate from `Probar-UI.sh`, which previews the actual local library.

Settings now use shorter rows and smaller gutters. Appearance keeps the same
controls with less vertical padding. Manual game settings place Save beside the
page heading and remove nested padding from numeric controls. Twelve focused
GTK checks passed, along with the seven theme checks; all main pages and the
manual settings, controls and files pages were rendered at 1280×800 and 840×640.

Desde la carpeta del proyecto, en un escritorio con GTK 3, ejecutar
`python3 tools/preview_console.py --interactive --real-games --download-artwork`.
La muestra opcional contiene 12 títulos conocidos de PC, Switch, PlayStation 2
y Wii. Solo se descargan carátulas y fondos públicos; la caché local ignorada
se excluye de los archivos de código. No se incluyen, instalan ni ejecutan
archivos originales de juegos. La ventana se identifica como DEMO. Los ajustes
manuales se simulan en memoria y la biblioteca de muestra es temporal. Este modo
es independiente de `Probar-UI.sh`, que muestra la biblioteca local existente.

Ajustes usa filas más bajas y márgenes menores. Apariencia conserva sus controles
con menos separación vertical. Los ajustes manuales ubican Guardar junto al
título y evitan el relleno duplicado de los controles numéricos. Pasaron doce
pruebas específicas de GTK y las siete pruebas de tema. Se renderizaron las
pantallas principales, los ajustes manuales, los controles y los archivos en
1280×800 y 840×640.

## Motion and compact details / Animaciones y fichas compactas

Navigation, game sections and internal workflows fade in after layout, including
Gaming Mode. Profile cards enter in sequence and disclosures expand smoothly.
Buttons use 8 px corners and panels use 10 px corners. The Animations switch in
Appearance disables these effects. Interactive sample previews now enable motion
by default; `--no-animations` disables it. Still captures keep motion disabled.

Port details keep the installation action beside the title and show original-file
requirements first. File instructions, compatibility evidence, release information,
existing installations, removal and project links remain in labelled disclosures.
Known variant status stays visible in the summary. Game profiles remain directly
selectable; community results are folded away and empty rating rows are omitted.

La navegación, las secciones del juego y los flujos internos aparecen con un
fundido después de acomodar la página, también en Gaming Mode. Los perfiles
entran en secuencia y los desplegables se expanden suavemente. Los botones usan
esquinas de 8 px y los paneles de 10 px. El control Animaciones de Apariencia
desactiva estos efectos. La muestra interactiva los activa de forma predeterminada;
`--no-animations` los desactiva. Las capturas estáticas mantienen las animaciones
desactivadas.

Las fichas de ports ubican la instalación junto al título y muestran primero los
requisitos de archivos originales. Las instrucciones, las pruebas de compatibilidad,
las versiones, las instalaciones existentes, la eliminación y los enlaces del
proyecto quedan en desplegables identificados. El estado conocido de la variante
permanece visible en el resumen. Los perfiles del juego siguen disponibles para
seleccionar; la comunidad queda plegada y se omiten las filas sin valoraciones.

Validation for this revision: the 170-case GTK suite passed 169 cases, with one
SDL2 input case skipped because SDL2 was unavailable. The seven theme checks
passed; translation checks passed 12 cases with one display-dependent case
skipped, and the missing-string scan reported zero. Pages were rendered at
1280×800 and 840×640, including port details and large English text. These are
automated UI and rendering checks, not evidence of device installation, boot,
physical controller operation or gameplay.

Validación de esta revisión: de 170 pruebas de GTK, pasaron 169 y se omitió una
de entrada SDL2 porque SDL2 no estaba disponible. Pasaron las siete pruebas de
tema y 12 de traducción; se omitió una de traducción que depende de una pantalla.
El análisis de cadenas faltantes informó cero. Se renderizaron páginas en
1280×800 y 840×640, incluidas las fichas de ports y el texto grande en inglés.
Son comprobaciones automatizadas de interfaz y renderizado; no validan instalación,
arranque, mando físico ni partidas en el dispositivo.

## Local sections and focus / Secciones y foco

Port details now use fixed Overview, Requirements, Compatibility and Manage tabs
instead of the earlier disclosures. The installation action remains beside the
title on every tab. Game pages use the same underlined tab style, with community
results in their own section. LB/RB switches local sections inside these pages;
outside them it switches primary navigation. Each port section keeps its scroll
position. Platform and runtime labels share one compact row below the game title.

Mouse and touch clicks no longer leave the keyboard focus frame on a button.
Keyboard and controller navigation restore one visible focus indicator. The
selected tab keeps its underline independently of input method. English captions
and the built-in disc-and-BIOS descriptions are fully translated.

The 173-case GTK suite passed 172 cases; one SDL2 case was skipped because SDL2
was unavailable. Theme and translation checks passed, with zero missing strings
reported by the scanner. Main pages and all port sections were rendered at
1280×800 and 840×640, including light theme and large English text. Device input,
installation, boot and gameplay remain separate validation steps.

Las fichas de ports ahora usan las subpestañas fijas Resumen, Requisitos,
Compatibilidad y Gestión en lugar de los desplegables anteriores. La acción de
instalación permanece junto al título en todas las secciones. Los juegos usan el
mismo estilo de pestañas subrayadas, con la comunidad en su propia sección.
LB/RB cambia de sección dentro de estas fichas y de pestaña principal fuera de
ellas. Cada sección del port conserva su posición de scroll. Las etiquetas de
plataforma y motor comparten una fila compacta debajo del título del juego.

Los clics de mouse y los toques ya no dejan el marco de foco de teclado sobre
los botones. La navegación con teclado o mando vuelve a mostrar un solo
indicador visible. La pestaña seleccionada conserva su subrayado con cualquier
método de entrada. Los nombres en inglés y las descripciones integradas de disco
y BIOS se traducen por completo.

De 173 pruebas de GTK, pasaron 172; se omitió una por falta de SDL2. Pasaron las
comprobaciones de tema y traducción, y el análisis informó cero cadenas faltantes.
Se renderizaron las pantallas principales y todas las secciones del port en
1280×800 y 840×640, con tema claro y texto grande en inglés. Mando físico,
instalación, arranque y partidas requieren validación independiente.

## Detail clarity / Claridad de las fichas

Game titles, platform/runtime facts and actions occupy separate rows. Play is a
compact blue primary action; Steam stays beside it, while removal and More sit
at the other end of the action row. Buttons keep their natural height instead of
stretching with neighbouring text. More uses shorter captions and a bounded,
scrollable menu; all commands remain reachable. Games without profile support
open an Overview tab. Local tabs no longer repeat their heading or back action.

Port Overview explains preparation and shows required originals, BIOS information
when applicable, file-check status and gameplay evidence. Requirements groups
the original version, file checks and preparation. Compatibility places gameplay
evidence before catalog estimates and release/package details. A missing
compatible package now has an explicit disabled-action label. Shortcut actions,
files and launch commands share labelled sections, and community actions have a
single explanatory panel. No upgrade or installation is required for this preview.

Validation: the 175-case GTK suite passed 174 cases and skipped one unavailable
SDL2 case. Six focused layout/navigation cases passed after the final layout
adjustments. Seven theme checks passed; translation checks passed 12 cases with
one display-dependent case skipped. The scanner found zero missing strings.
Native GTK captures cover the menu and all local sections at 1280×800 and
840×640, including large English text. Direct desktop automation was unavailable;
these checks do not establish physical device input, installation, boot or gameplay.

El título, los datos de plataforma y motor y las acciones del juego ocupan filas
separadas. Jugar es una acción azul compacta; Steam queda a su lado, y Eliminar y
Más se ubican en el otro extremo. Los botones conservan su altura sin estirarse
con el texto vecino. Más usa nombres breves y un menú acotado con scroll; todas
las acciones siguen accesibles. Los juegos sin perfiles abren Resumen. Las
subpestañas ya no repiten el título ni el botón de regreso.

El resumen del port explica la preparación y muestra originales necesarios,
BIOS cuando corresponde, estado de archivos y pruebas de juego. Requisitos
agrupa versión original, comprobaciones y preparación. Compatibilidad prioriza
las pruebas de juego, seguidas por estimaciones y datos del paquete. La falta de
un paquete compatible se indica en la acción desactivada. Los accesos directos,
archivos y comandos quedan en secciones identificadas, y la comunidad tiene un
solo panel explicativo. Esta prueba no requiere actualizar ni instalar la app.

Validación: de 175 pruebas de GTK, pasaron 174 y se omitió una por falta de SDL2.
Tras los últimos ajustes pasaron seis pruebas específicas de diseño y navegación.
Pasaron siete pruebas de tema y 12 de traducción; se omitió una de traducción
dependiente de una pantalla. El análisis informó cero cadenas faltantes.
Las capturas nativas de GTK cubren el menú y todas las secciones en 1280×800 y
840×640, incluido texto grande en inglés. La automatización directa del escritorio
no estuvo disponible; estas comprobaciones no validan mando físico, instalación,
arranque ni partidas.
