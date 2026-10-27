# Presets portables — esquema v1

Los perfiles son datos JSON. Los ajustes automáticos nunca contienen scripts, destinos de archivos, ROMs, claves ni un INI/TOML completo. Las instrucciones manuales pueden incluir comandos como texto informativo, que la app no ejecuta. La app determina el destino usando la instalación local y un adaptador explícito.

El esquema validable está en [preset.schema.json](../presets/preset.schema.json). El catálogo inicial está en [catalog.json](../presets/catalog.json). El registro de opciones aceptadas por cada adaptador está en `deck_library/presets.py`.

```json
{
  "schema_version": 1,
  "id": "wiicompiled-rmcp01-sharp",
  "name": "Mario Kart Wii — nitidez 1.5×",
  "game": {"id": "RMCP01", "name": "Mario Kart Wii", "platform": "WiiCompiled"},
  "adapter": {"id": "wiicompiled", "versions": ["0.2.33"]},
  "hardware": ["steam-deck-oled", "steam-deck-lcd"],
  "objective": "Nitidez y estabilidad",
  "author": "Deck Library",
  "license": "MIT",
  "tested": {"status": "user-confirmed", "date": "2026-10-01"},
  "settings": {"video": {"resolution_multiplier": 1.5, "disable_copy_filter": true}},
  "notes": "La confirmación corresponde a la Deck OLED probada.",
  "sources": []
}
```

## Identidad y compatibilidad

- Switch: Title ID base, sin la terminación de actualización/DLC. Se identifica por nombre de archivo, ticket del NSP o metadata conocida; puede completarse manualmente.
- Wii/GameCube: ID del disco (por ejemplo RMCP01).
- Minecraft Java: `minecraft-java`; la instancia se resuelve localmente y nunca se publica su ruta.
- Otros ports: un identificador público del proyecto, con un adaptador implementado antes de permitir cambios automáticos.

Versiones declaradas y hardware se muestran para evaluar compatibilidad. Si la versión instalada se conoce y no coincide, la app rechaza aplicar el preset. La versión de Eden puede no detectarse automáticamente en todos los AppImages: hay que contrastarla con la versión declarada. Los perfiles disponibles para ambos modelos de Deck no significan que todos fueron probados en ambos.

Los estados son `proposal` (para probar), `boot-tested` (arranque comprobado) y `user-confirmed` (confirmación reportada). Son declaraciones del autor; el servicio comunitario agrega revisión, votos y comentarios. Ningún preset promete FPS universales.

## Opciones de Switch para juegos sin perfil

Desde 0.10.2, **Ajustes recomendados** usa primero los perfiles específicos incluidos, importados o descargados. Si no hay ninguno para un juego de Switch/Eden con Title ID válido, ofrece tres propuestas. Si falta el ID, indica completarlo en **Editar juego**. Los ajustes actuales siguen visibles; tener un INI personalizado no impide ofrecer estas opciones.

| Opción | Precisión GPU | Shaders asíncronos | Presentación asíncrona |
| --- | --- | --- | --- |
| Equilibrado | Normal | Desactivados | Desactivada |
| Rendimiento | Normal | Activados | Activada |
| Compatibilidad | Alta | Desactivados | Desactivada |

Todas usan Vulkan, resolución 1× (`resolution_setup=3`), modo portátil, CPU automática, varios núcleos, velocidad normal, caché de shaders y emulación de GPU asíncrona. Los cinco presets existentes aportan los valores comunes; Smash, Mario Kart 8 y Mario Party Superstars aportan las opciones asíncronas de Rendimiento, y Super Mario Party/Jamboree las opciones conservadoras. No se copian requisitos de CTGP ni estados de prueba. La comparación en el juego determina cuál funciona mejor; los nombres no implican FPS medidos.

Las plantillas [Equilibrado](../presets/eden-switch-default.json), [Rendimiento](../presets/eden-switch-performance.json) y [Compatibilidad](../presets/eden-switch-compatibility.json) también se incluyen en el catálogo. Sus identidades `switch-default`, `switch-performance` y `switch-compatibility` no son comodines aplicables: `recommended()` genera copias con el Title ID real e IDs estables por juego. La compatibilidad sigue exigiendo coincidencia exacta de juego y adaptador. Consultar recomendaciones no escribe perfiles en el almacén.

**Aplicar y probar** muestra la vista previa y, tras confirmarla, usa el adaptador habitual con respaldo y abre el juego mediante el mismo lanzamiento que **Jugar**. Con Eden abierto se rechaza aplicar o restaurar: cerrar el juego/emulador antes de probar otra opción. Si falla la apertura, el perfil permanece aplicado y puede restaurarse. No hay restauración automática al cerrar el juego; **Restaurar anterior** recupera la configuración anterior a la última aplicación.

**Marcar como mejor** guarda el ID del perfil para ese juego en `preferred-presets/<id-local>.json`, dentro del almacén privado. La mejor opción se identifica en la lista y se selecciona al reabrir el diálogo. Se puede cambiar la elección. No aplica el perfil, no modifica el catálogo ni su estado de validación y no envía datos. Si cambia la identidad del juego, la preferencia anterior se ignora.

Las tres propuestas declaran Eden 0.2.1 y hardware Deck LCD/OLED. Una versión instalada conocida que no coincida sigue bloqueando la aplicación; si no se detecta, se muestra la versión declarada para su contraste. NAND, partidas, rutas, controles, idioma, mods y ajustes ajenos al perfil se conservan. Rendimiento y Gaming Mode requieren pruebas por título.

## Adaptadores

- `eden`: modifica el INI personalizado del juego. Marca las opciones como explícitas y sin heredar el valor global. Resolución `3` equivale a 1× en Eden 0.2.1. No modifica NAND, rutas, controles, velocidad superior a 100%, updates ni mods.
- `wiicompiled`: modifica únicamente opciones permitidas de video/audio del TOML local. El perfil confirmado usa Vulkan, 1.5×, copy filter desactivado y ninguna interpolación. El parche F12 de salida es código compilado, no un valor del preset.
- `dolphin`: opciones permitidas en el INI específico del juego; incluye exportación/importación y aplicación, sin un preset integrado validado de rendimiento.
- `prism`: memoria y ventana de la instancia. No exporta JavaPath, credenciales, cuentas, comandos de la instancia, mods ni mundos.

`layout` es una recomendación de Steam Input con plantilla, bindings legibles y notas. **No cambia automáticamente el layout de Steam**. El botón abre sus controles para seleccionar/adaptar la plantilla; los mods que añaden gamepad pueden requerir otro layout.

## Aplicar y compartir

En la ficha de un juego, **Ajustes recomendados** permite ver cambios, aplicar, restaurar, importar JSON y exportar opciones actuales. Se guarda el archivo original privadamente. Si el programa está abierto se rechaza modificar su configuración. Restaurar también se rechaza si otro programa cambió el archivo después, para conservar esos cambios; el backup sigue disponible.

**Exportar mis ajustes** pide un alias público y crea una propuesta con licencia MIT. Revisar las opciones y completar versiones/notas antes de recomendarlo. La app filtra claves y no incluye rutas, pero cualquier nota escrita manualmente debe revisarse antes de publicar.

**Dar feedback** guarda un JSON de resultado y permite exportarlo. No envía nada automáticamente a GitHub o a un servidor.

Para un catálogo común sin servidor: cada amigo puede apuntar **Catálogo GitHub** a la URL HTTPS raw de `presets/catalog.json`. La app descarga y valida el catálogo antes de guardar los perfiles localmente. Los aportes se comparten como JSON y se revisan mediante un commit/pull request del repositorio. No se incluye una credencial de escritura ni se suben aportes desde la app.

## Pruebas

Probar preservación de opciones ajenas al preset, rechazo de claves desconocidas/rutas/comandos, compatibilidad por juego/versión, programa abierto, rollback y feedback sin datos privados. Al recomendar un perfil, registrar el escenario probado (menú/partida), actualización, mod y modelo de Deck.

## Capturar, editar y compartir (0.19.7)

Abrir un juego → **Comunidad → Compartir mis ajustes**. **Leer configuración del juego** captura las opciones reconocidas, incluidos los valores globales heredados. **Leer otro archivo de configuración** permite elegir un INI o TOML; solo importa las claves permitidas para ese adaptador. No copia el archivo completo.

Se pueden editar los valores JSON, escribir instrucciones, registrar resultados de prueba y declarar Linux nativo, Proton o Steam, su versión y opciones de lanzamiento. **Revisar mis ajustes** muestra el contenido antes de compartirlo. **Guardar localmente** funciona sin cuenta. **Publicar perfil** requiere iniciar sesión; el servicio asigna el autor autenticado y lo hace visible a los demás. Un servidor propio puede activar revisión previa con `COMMUNITY_REVIEW_REQUIRED=true`; en ese caso figura como pendiente hasta su aprobación. **Mis aportes** muestra los perfiles propios para ese juego y adaptador. Publicar no concede una marca de verificado.

| Programa | Lectura | Aplicación |
| --- | --- | --- |
| Eden | Global + personalizado del juego | INI del juego, con respaldo |
| DuckStation | Global + archivo del serial | INI del juego, con respaldo |
| Dolphin | GFX global + GameSettings | GameSettings, con respaldo |
| PCSX2 | Global + archivo serial/CRC identificado | Solo archivo por juego identificado; nunca el global |
| Azahar / Citra | Global + personalizado del Title ID | INI del juego, con respaldo |
| PPSSPP | Global + archivo del ID de PSP | INI del juego, con respaldo |
| mGBA | Opciones gráficas globales reconocidas | Referencia manual; no modifica el global |
| WiiCompiled / Project 2099 antiguo | TOML conocido del adaptador | Opciones permitidas, con respaldo |
| Project 2099 Beta 5 y demás ports / juegos de PC | Guía manual; GTA IV puede leer opciones conocidas de FusionFix/DXVK | Pasos manuales; no ejecuta comandos |

Los archivos se buscan en instalaciones nativas y Flatpak conocidas. Una instalación personalizada puede usar `emulator_config_dir` en sus metadatos o el selector de archivo. La aplicación de PCSX2 exige una configuración existente inequívoca o serial + CRC explícitos. Un serial, Title ID o versión desconocidos se deben completar antes de aplicar. No se exportan rutas, cuentas, controles ni claves de los archivos leídos.

`instructions` admite hasta 12.000 caracteres. `runtime` declara `kind` (`native`, `proton`, `steam`), `version` y `launch_options`. Ambos son texto informativo: importar, descargar o aplicar un perfil **no ejecuta comandos ni cambia Proton**. Una guía sin ajustes automáticos muestra **Ver instrucciones** y mantiene deshabilitado Aplicar. Revisar los textos escritos manualmente antes de publicarlos.

Los juegos sin identificador público usan una identidad derivada del repositorio del port o del nombre y plataforma. Renombrarlos puede cambiar esa identidad; un ID público explícito es preferible. Los perfiles de Project 2099 Beta 4.1 no se aplican al motor distinto de Beta 5. Las referencias documentadas de DMC3 Crimson y Shattered Dimensions no instalan automáticamente esos fixes.

Fuentes de los formatos revisados: [PCSX2](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/VMManager.cpp), [Azahar](https://github.com/azahar-emu/azahar/blob/master/src/citra_qt/configuration/config.cpp), [mGBA](https://github.com/mgba-emu/mgba/blob/master/src/core/config.c), [PPSSPP](https://github.com/hrydgard/ppsspp/blob/master/Core/Config.cpp).


## Naruto: Rise of a Ninja y Proton por juego (1.2.8)

El adaptador `narutorise` identifica el proyecto `jorjbarbosa/naruto-rise-recomp` y el juego `555307E5`. Lee `narutorise.version` y modifica exclusivamente las opciones gráficas permitidas del TOML junto al ejecutable. Incluye vista previa, respaldo, restauración, importación y captura. Idioma, mandos, mods, rutas, partidas y cachés permanecen fuera del perfil.

- **Equilibrado:** configuración probada por un usuario en Steam Deck con la versión 0.3.0-beta y Proton 11.0, aproximadamente 45–60 FPS variables. Vulkan nativo, 720p internos, FXAA, CAS, MSAA desactivado y filtrado 16×. Solo esta opción declara `user-confirmed`; no certifica ambos modelos de Deck ni una tasa sostenida.
- **Rendimiento:** propuesta a 720p, sin FXAA, VSync desactivado y filtrado 8×. Puede mostrar más dientes de sierra y no garantiza mejorar FPS si el límite está en la CPU.
- **Calidad:** propuesta a 1080p internos, FXAA y objetivo de 30 FPS. Sin prueba de jugabilidad o rendimiento.

Fuentes: [configuración](https://github.com/jorjbarbosa/naruto-rise-recomp/blob/main/docs/configuration.md) y [renderizador](https://github.com/jorjbarbosa/naruto-rise-recomp/blob/main/docs/renderers.md). Se conserva la caché: compilar pipelines nuevos puede provocar pausas. El renderizador nativo usa interpolación para presentar más cuadros que la lógica original; el objetivo de FPS no mide la velocidad real alcanzada.

La ficha de los ports Windows administrados por Deck Library, Project-2099 y ejecutables Windows directos muestra **Proton**, con **Automática** y las versiones instaladas, incluidas GE-Proton y las bibliotecas de Steam en otros discos. Guardar la selección no descarga herramientas ni requiere volver a agregar el acceso. Si se elimina la versión elegida, se informa el error al iniciar: no se cambia silenciosamente a otra.

El acceso de Steam de Deck Library abre un lanzador Linux estable que consulta la preferencia de ese juego al iniciarse. Por eso **no se debe forzar Proton sobre ese lanzador desde Steam**. El AppID y las carátulas no cambian y no se genera una operación pendiente de Steam. Los ports portables mantienen el mismo prefijo y sus datos al probar otra versión; Project-2099 conserva su gestión existente de prefijos y su opción automática usa Proton 9 para el motor reeot cuando está disponible. La selección se rechaza si el juego o su lanzador están abiertos.

Los accesos externos administrados por Steam conservan la selección de **Propiedades → Compatibilidad**; no se convierten en lanzadores propios ni se modifica su compatibilidad desde este selector. Otros gestores, como Lutris, siguen controlando sus propios entornos.

`runtime.version` en un perfil es una referencia de la prueba declarada. Aplicar gráficos no cambia automáticamente la versión elegida en el selector. Para compartir perfiles `narutorise` con un servidor comunitario propio, ese servidor también necesita el registro de adaptadores de 1.2.8 o posterior.
