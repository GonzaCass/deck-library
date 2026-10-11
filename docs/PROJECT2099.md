# Project-2099 en Steam Deck

**Agregar juegos → Preparar Project-2099** instala Spider-Man: Edge of Time desde una ISO propia de Xbox 360, o un ZIP/7z con una sola ISO. No acepta la versión PS3. La comprobación de cabecera detecta ese caso antes de descargar componentes; el instalador oficial comprueba además la revisión, tamaños y hashes de los archivos del juego.

Instalá Proton 11.0 desde las Herramientas de Steam. Elegí el archivo y una carpeta de destino vacía. El asistente exige 18 GB libres para los datos temporales, más el tamaño descomprimido de la ISO cuando se selecciona ZIP/7z. Los 7z requieren `7z` o `7zz`. Deck Library descarga el instalador y payload oficiales **v2.0.0-beta.4.1**, verifica SHA-256, los ejecuta mediante Proton en un entorno propio y selecciona español. No cambia la ISO original ni instala sobre una carpeta ocupada. Los registros quedan en la carpeta privada de Deck Library, dentro de `downloads/project2099/install.log`.

Al terminar, el juego aparece en la biblioteca. Usá **Agregar a Steam** desde su ficha; con Steam abierto, el guardado queda pendiente hasta cerrarlo. El acceso ejecuta el juego directamente, sin volver a mostrar el launcher de Windows. Los ports ya preparados se detectan en `~/ports` y las carpetas de ports configuradas cuando contienen `SpiderManEOT.exe`, `rexruntime.dll` y su TOML.

## Perfil inicial

El preset **Project 2099 — Steam Deck 720p / 60 FPS** usa salida 1280×720, renderizado interno 1×, DirectX 12 mediante VKD3D, objetivo/límite de 60 FPS, anisotropía 8×, caché y compilación asíncrona originales, mando XInput y modo teclado/ratón desactivado. Conserva Native AA del paquete oficial; no instala DLSS, ReShade ni generación de cuadros. Resolución interna superior a nativa y Vulkan no son rutas recomendadas por el proyecto en esta beta.

Es un perfil **propuesto**, pendiente de prueba de juego en Steam Deck. No se midieron FPS ni se garantiza que alcance 60 en todas las escenas. En Steam Input, elegí la plantilla **Gamepad**. Para probar 60 FPS en OLED, usá 60 Hz; 90 Hz puede producir una cadencia desigual a 60 FPS. No se modifica el refresco global de la Deck.

**Ajustes recomendados** permite ver cambios, aplicar, respaldar, restaurar y compartir el JSON. El adaptador solo modifica una lista de opciones gráficas/de mando; conserva idioma, rutas, partidas y el resto del TOML.

## Estado local

La primera imagen recibida el 1 de octubre de 2026 era PS3 (`PS3VOLUME`) y fue rechazada por el instalador. Se eliminó a pedido del usuario, junto con la copia temporal. La copia Xbox 360 recibida en 7z el 2 de octubre fue extraída con integridad comprobada e instalada correctamente. El instalador reconoció `usa-europe-retail-r2`, verificó 293 archivos de origen y completó ambos árboles de idioma; español quedó seleccionado. `SpiderManEOT.exe --verify-install` terminó con código 0 bajo Proton 11.0. Se conservó el 7z y se eliminaron la ISO y los datos temporales. La prueba jugando en modo Juego y los FPS siguen pendientes.

Fuentes: [instalación oficial](https://github.com/GenryTheFox0/Project-2099/blob/main/INSTALL_ES.md), [requisitos y limitaciones del renderer](https://github.com/GenryTheFox0/Project-2099), [release fijado](https://github.com/GenryTheFox0/Project-2099/releases/tag/v2.0.0-beta.4.1).

## Comparación de rendimiento y acentos — 2026-10-02

El usuario confirmó arranque y aproximadamente 30 FPS con salida 1080p / Native AA, y letras acentuadas desplazadas en menús. No es un benchmark sostenido ni una validación en modo Juego.

Se agregó **Project 2099 — salida 1080p / FSR espacial** como propuesta: mantiene salida 1920×1080 y objetivo de 60 FPS, sustituye `present_effect=fsr3` por `fsr` y desactiva `eot_pc_raster_glyphs` y `eot_pc_prompt_labels` para comparar los textos de consola originales. Esto puede reducir el coste y artefactos temporales; no garantiza mejora ni corrige necesariamente las métricas de las letras acentuadas. FSR espacial no equivale a Native AA temporal: puede aumentar el aliasing. El renderizado interno sigue siendo nativo 720p.

No se encontró un mod de iconos PlayStation verificado para este port/beta; conserva los símbolos Xbox. El cambio de glifos no cambia el idioma ni altera los paquetes del juego. El preset tiene respaldo y puede revertirse desde la ficha. Hay que probarlo en la misma escena para comparar FPS, letras y nitidez.

El usuario probó el perfil FSR espacial y reportó rendimiento igual o ligeramente peor. Se descartó como mejora y se volvió a FSR3 / Native AA, manteniendo salida 1080p y los glifos originales para comparar los acentos por separado. No se declaró validado el arreglo de acentos ni una mejora de FPS. El feedback queda también registrado localmente en Deck Library.

El usuario reportó unos 30 FPS más estables al volver a Native AA en 1080p. A su pedido se cambió la salida a 1280×720, manteniendo Native AA, glifos originales y objetivo de 60 FPS; se reabrió el juego para comparar. Rendimiento de este último cambio pendiente.

El usuario no percibió mejora al cambiar la salida de 1080p a 720p. La inspección X11 mostró que fullscreen seguía creando una ventana 1280×800; una muestra de GPU indicó 100 % de ocupación. Se probó fullscreen=false con tamaño configurado 1280×720 y Native AA. La ventana real quedó 1272×720 por los bordes del escritorio. Se reabrió y activó el juego; la comparación de FPS queda pendiente. Estas dimensiones de ventana no demuestran por sí solas la resolución interna 3D.

La prueba en ventana también fue percibida como unos 30 FPS, con buena imagen. Se activó `show_fps_counter=true` para obtener una lectura numérica, sin cambiar el renderer ni el antialiasing, y se volvió a abrir el juego.

El contador mostró 30–45 FPS según el usuario; las estimaciones anteriores de 30 FPS no eran mediciones. Se preparó una comparación con Proton 10.0-4b, manteniendo ventana 720p, Native AA, glifos originales y contador. Usa un prefix separado del de Proton 11, sin tocar los archivos de juego ni UserData. El juego abrió bajo Proton 10; comparación de rendimiento pendiente.

Proton 10 superó la pantalla negra inicial y el usuario reportó 39–45 FPS más estables. A pedido del usuario se activó fullscreen manteniendo Native AA y contador. Se guardó el acceso pendiente con Steam cerrado y se reabrió el juego mediante `steam://rungameid`; se verificó la ventana `steam_app_3581851636` en 1280×800 y AllowDesktopConfig=0 para evitar la inyección del layout de Escritorio. Prueba de FPS/teclado en esta modalidad pendiente.

El usuario confirmó 40–45 FPS y algunos 47 con Proton 10 fullscreen desde Steam. Se respaldó esa referencia y se probó `VKD3D_CONFIG=single_queue` como única variación, sin cambiar gráficos ni partidas. La opción está presente en d3d12core.dll del Proton 10 instalado y documentada por VKD3D-Proton. Su efecto es evitar colas de compute/transfer asíncronas; no garantiza mejora. Resultado de la comparación pendiente.

El usuario reportó 40–50 FPS con single_queue, sin mejora sustancial percibida. Se inició una comparación con Proton Experimental 11.0-20260924, retirando single_queue y manteniendo gráficos/contador/fullscreen. Usa un entorno propio; el entorno y referencia de Proton 10 se conservaron. Arranque desde Steam y ventana fullscreen verificados; rendimiento pendiente de feedback.

Experimental no mejoró el rendimiento según el usuario. Se inició una comparación con Proton 9.0-4f (instalado bajo el nombre Proton 9.0 (Beta)), con entorno separado y los mismos ajustes gráficos. La alternativa RPCS3 figura como Playable en la lista oficial para BLES01291/BLUS30760; esa clasificación no acredita rendimiento en Steam Deck. La ISO PS3 anterior se eliminó a pedido del usuario, por lo que esa comparación requiere aportar de nuevo su copia PS3.

El usuario confirmó unos 50 FPS y mayor fluidez con Proton 9.0-4f. Se guardó una referencia local completa de comando y TOML. Se prueba single_queue con Proton 9 como única variación; la resolución, Native AA, fullscreen y partidas se conservan. Resultado pendiente de comparación en la misma escena.

El usuario corrigió la lectura del ensayo single_queue a 40–50 FPS; no se acredita una mejora. Se retira esa opción y se prepara Proton 8.0 como comparación aislada, conservando el entorno y referencia de Proton 9. Rendimiento pendiente.

Proton 8.0-5d se instaló desde Steam y falló al arrancar: KERNEL32.dll.CopyFile2 no implementada, salida 1. No hubo prueba de FPS. Se descartó esta versión y se restauró Proton 9 sin single_queue, conservando gráficos y partidas.

Steam en modo Juego había elegido controller_neptune_webbrowser.vdf y registraba mapping uses xinput: false. Con Steam cerrado se respaldó configset_controller_neptune.vdf y se fijó controller_neptune_gamepad_joystick.vdf para este acceso (nombre normalizado y AppID firmado/sin signo), sin editar otros perfiles. Se desactivó show_fps_counter y input_auto_device_switching, manteniendo XInput, mnk_mode=false y fullscreen. Se conservaron los gráficos ajustados por el usuario (FSR3 Performance y objetivo 75). No se abrió el juego; validación del mando después del reinicio pendiente. La demora de arranque reportada no tiene causa confirmada; no se borraron cachés.
