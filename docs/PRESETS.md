# Presets portables — esquema v1

Los perfiles son datos JSON. Nunca contienen comandos, scripts, destinos de archivos, ROMs, claves ni un INI/TOML completo. La app determina el destino usando la instalación local y un adaptador explícito.

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

Los estados son `proposal` (para probar), `boot-tested` (arranque comprobado) y `user-confirmed` (confirmación reportada). Son declaraciones del autor; esta versión local no dispone de verificación central, votos ni moderación. Ningún preset promete FPS universales.

## Adaptadores

- `eden`: modifica el INI personalizado del juego. Marca las opciones como explícitas y sin heredar el valor global. Resolución `3` equivale a 1× en Eden 0.2.1. No modifica NAND, rutas, controles, velocidad superior a 100%, updates ni mods.
- `wiicompiled`: modifica únicamente opciones permitidas de video/audio del TOML local. El perfil confirmado usa Vulkan, 1.5×, copy filter desactivado y ninguna interpolación. El parche F12 de salida es código compilado, no un valor del preset.
- `dolphin`: opciones permitidas en el INI específico del juego; incluye exportación/importación y aplicación, sin un preset integrado validado de rendimiento.
- `prism`: memoria y ventana de la instancia. No exporta JavaPath, credenciales, cuentas, comandos de la instancia, mods ni mundos.

`layout` es una recomendación de Steam Input con plantilla, bindings legibles y notas. **No cambia automáticamente el layout de Steam**. El botón abre sus controles para seleccionar/adaptar la plantilla; los mods que añaden gamepad pueden requerir otro layout.

## Aplicar y compartir

En la ficha de un juego, **Ajustes recomendados** permite ver cambios, aplicar, restaurar, importar JSON y exportar opciones actuales. Se guarda el archivo original privadamente. Si el programa está abierto se rechaza modificar su configuración. Restaurar también se rechaza si otro programa cambió el archivo después, para conservar esos cambios; el backup sigue disponible.

**Exportar mis ajustes** pide un alias público y crea una propuesta con licencia MIT. Revisá las opciones y completá versiones/notas antes de recomendarlo. La app filtra claves y no incluye rutas, pero cualquier nota escrita manualmente debe revisarse antes de publicar.

**Dar feedback** guarda un JSON de resultado y permite exportarlo. No envía nada automáticamente a GitHub o a un servidor.

Para un catálogo común sin servidor: cada amigo puede apuntar **Catálogo GitHub** a la URL HTTPS raw de `presets/catalog.json`. La app descarga y valida el catálogo antes de guardar los perfiles localmente. Los aportes se comparten como JSON y se revisan mediante un commit/pull request del repositorio. No se incluye una credencial de escritura ni se suben aportes desde la app.

## Pruebas

Probar preservación de opciones ajenas al preset, rechazo de claves desconocidas/rutas/comandos, compatibilidad por juego/versión, programa abierto, rollback y feedback sin datos privados. Al recomendar un perfil, registrar el escenario probado (menú/partida), actualización, mod y modelo de Deck.
