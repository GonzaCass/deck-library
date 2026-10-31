# GTA IV en Steam Deck: arreglo confirmado por usuario

En Deck Library: **Buscar juegos → Grand Theft Auto IV → Ver arreglo → Aplicar arreglo de GTA IV**. La aplicación detecta la instalación de Steam, también en microSD. Cerrar GTA IV primero. El botón descarga el paquete oficial, verifica su SHA-256, guarda un respaldo y aplica el arreglo sin abrir el juego. **Restaurar respaldo** vuelve al estado inmediatamente anterior a la última aplicación.

## Probar FusionFix 5.1.2

El selector del arreglo ofrece **4.0.5 · Perfil probado** y **5.1.2 · Nueva versión, para probar**. La segunda opción descarga el [ZIP oficial de 5.1.2](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/tag/v5.1.2), verifica el SHA-256 `138f4067a2d2f09df2df80c4378407ad7c742be0e3b99f090633d50820bb2450` y respalda cada archivo que reemplaza o quita.

FusionFix cambió el formato de las opciones del menú. Este perfil crea un CFG nuevo con valores comprobados en el código de la versión 5.1.2: Vulkan, SMAA, límite de 60 FPS, filtro de sombras Soft, niebla volumétrica y oclusión ambiental desactivadas, y botones de PS5. Conserva la resolución, el idioma configurado, las opciones INI reconocidas y Proton. No interpreta los índices del CFG anterior como si tuvieran el mismo significado. El respaldo permite recuperar las opciones anteriores.

**Restaurar respaldo** recupera la instalación anterior. Si el juego modificó sus ajustes durante la prueba, la app guarda esos archivos aparte antes de restaurar. Un binario cambiado posteriormente bloquea la restauración para no sobrescribir otros mods. No se tocan partidas.

Validación del perfil 5.1.2: instalación con checksum y verificación de los archivos, arranque desde Steam y carga de una partida en Steam Deck. No se midieron FPS ni se realizó una comparación de rendimiento durante gameplay; no reemplaza la confirmación histórica de 4.0.5.

### Quitar el tono sepia sin reinstalar

FusionFix 5.1.2 usa `ScreenFilter = 0` para el filtro predeterminado y `ScreenFilter = 1` para **OFF**, según su [enumeración en settings.ixx](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/blob/v5.1.2/source/settings.ixx). Cero no desactiva el filtro. El perfil de 5.1.2 ahora escribe el valor OFF explícitamente. La gamma de consola y la exposición son opciones distintas.

Si la versión 5.1.2 ya está instalada desde Deck Library, **Ver arreglo → Quitar filtro de color** cambia solo `MISC/ScreenFilter` y respalda el CFG. Conserva el límite de FPS, resolución, controles y el resto de los gráficos. Cerrar el juego antes de usarlo. La iluminación cálida de una zona o clima puede seguir presente: desactivar este filtro no elimina la iluminación propia del juego.

## Qué funcionó en esta Deck

El 1 de octubre de 2026 el usuario reportó «anduvo perfecto el gta iv» después de sustituir FusionFix **5.0.1 por 4.0.5**, conservando **DXVK 2.6.2**, con estos ajustes en `dxvk.conf` al lado de `GTAIV.exe`:

```ini
d3d9.maxFrameLatency = 1
d3d9.presentInterval = 1
```

El VSync del juego estaba apagado. `d3d9.cfg` tenía `[MAIN] API = 1`, y `plugins/GTAIV.EFLC.FusionFix.cfg`, `[MAIN] GraphicsAPI = 1`: se utiliza el DXVK incluido en el paquete. Los botones de Sony se seleccionan con `[MISC] Buttons = 9` (PS5). Se desactiva `CheckForUpdates` para mantener la versión de la comparación y evitar el aviso del actualizador.

**Al aplicar originalmente:** límite de 60 FPS (`FpsLimitPreset = 7`). **Al documentar después de jugar:** el usuario había seleccionado 100 FPS (`FpsLimitPreset = 9`). El botón conserva el límite y las opciones gráficas existentes; sólo en ausencia de configuración crea el límite de 60. La configuración observada también tenía SMAA, filtro de sombras Soft, profundidad de campo sólo en escenas y niebla volumétrica apagada. No se modifican automáticamente esos valores ni la resolución.

Equipo: Steam Deck OLED. Juego: **Complete Edition 1.2.0.59**, Steam App ID **12210**. Proton seleccionado durante las pruebas: **11.0**. El botón no cambia Proton, Steam Input, energía, frecuencia del panel, cachés, partidas ni versión del juego. La captura de clips estaba activa al documentar; el botón la conserva.

Esta es una **confirmación de experiencia del usuario**, sin captura de frametimes ni recorrido/tiempo registrados. No demuestra 60 o 100 FPS constantes ni compatibilidad con todos los equipos. Se cambiaron versión del mod y opciones de presentación durante la revisión: no se aisló cuál cambio produjo la mejora. Las pruebas anteriores con DXVK de Proton y sin FusionFix seguían mostrando tirones.

## Reproducir manualmente

1. Cerrar el juego. Respaldar los archivos de FusionFix, su carpeta `update`, ambos archivos de configuración del mod, `d3d9.cfg`, `dxvk.conf` si existe y `SETTINGS.CFG` del prefijo de Proton.
2. Descargar el ZIP de [FusionFix 4.0.5 oficial](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/tag/v4.0.5). SHA-256 fijado:
   `d78abf54aaf86a8193278a77bafc33dbc7767bd57d80968a8ed42edd75ba06bd`.
3. Extraer el paquete completo junto a `GTAIV.exe`; no sustituir únicamente el `.asi`. Si se viene del paquete 5.0.1, retirar sus cinco archivos adicionales enumerados abajo, después de respaldarlos. Usar el INI de 4.0.5 y migrar sólo opciones que éste reconoce.
4. Seleccionar API 1 en `d3d9.cfg` y `GraphicsAPI = 1` en el CFG de FusionFix. Añadir las dos líneas de DXVK anteriores. Apagar VSync en Gráficos del juego. Para apuntar a 60, seleccionar 60 en el límite de FusionFix. El instalador puede preparar todo con el juego cerrado.
5. Probar manejando por el tramo que antes tironeaba. Mantener el mismo perfil de energía, resolución y ajustes para comparar. No es necesario borrar cachés ni partidas.

Archivos que pertenecían al paquete 5.0.1 y no están en 4.0.5 (rutas relativas a `GTAIV`):

```text
update/TBoGT/common/data/carcols.dat
update/TBoGT/common/data/fonts.dat
update/TBoGT/pc/models/cdimages/playerped.rpf
update/TLAD/pc/models/cdimages/playerped.rpf
update/common/data/visualsettings.dat
```

Estos son overrides del mod en `update`; no se eliminan los archivos base del juego. El botón respalda también cualquier modificación local en esos destinos.

## Integración desde un botón o terminal

La implementación reutilizable está en `deck_library/gtaiv.py`. El paquete se obtiene de una URL oficial fijada en el código; no acepta URLs ni comandos de catálogos importados. Usa sólo Python estándar. No distribuye el ZIP ni archivos del juego en el release.

```python
from deck_library import gtaiv

entries = gtaiv.discover()  # instalación Steam y prefijo, sin abrir el juego
entry = entries[0]
backup = gtaiv.apply(entry.metadata['gtaiv_root'], entry.metadata['gtaiv_settings'])
# Para deshacer, con GTA IV cerrado:
gtaiv.restore(entry.metadata['gtaiv_root'])
```

Ejecutar `apply`/`restore` en un worker de la interfaz: la descarga y la copia pueden tardar. `apply` devuelve la carpeta del respaldo y lanza una excepción con motivo legible si falla. Si hay más de un prefijo, se debe elegir `SETTINGS.CFG` explícitamente.

Desde la carpeta de la aplicación:

```sh
python3 -m deck_library.gtaiv detect
python3 -m deck_library.gtaiv apply --root '/ruta/GTAIV' --settings '/ruta/Settings/SETTINGS.CFG'
python3 -m deck_library.gtaiv restore --root '/ruta/GTAIV'
```

`--archive /ruta/GTAIV.EFLC.FusionFix-v4.0.5.zip` permite usar una descarga local con el mismo SHA-256. La primera descarga requiere unos 172 MB; reservar aproximadamente 1 GB para descarga, instalación y respaldo. Los archivos privados quedan en `~/.local/share/deck-library/gtaiv/` y el ZIP cacheado en `downloads/`, fuera del código compartible.

Se valida el ejecutable 1.2.0.59 y el formato de `SETTINGS.CFG` antes de escribir. Sólo se cambia el entero VSync de ese archivo (offset 608); se preservan resolución, gráficos, audio y controles. Se rechazan destinos con enlaces simbólicos y cambios mientras se aplica; las escrituras usan reemplazo atómico por archivo. Un fallo durante la aplicación restaura los originales respaldados. No se inicia el juego en ninguna operación. La restauración rechaza sobrescribir archivos cambiados posteriormente, por ejemplo ajustes guardados por el juego; el respaldo queda disponible para recuperación manual.

## Fuentes y lo que no se aplicó

- [Post y comentarios consultados](https://www.reddit.com/r/GTAIV/comments/1pbnnn9/fusionfix_405_microstutters_with_dxvk_radeon_rx/): experiencias individuales; el comentario sobre un FusionFix viejo no identifica su versión y compartió instrucciones por mensaje privado. **4.0.5 es nuestra comparación local**, no la versión confirmada de ese comentario.
- [Release oficial 4.0.5](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/releases/tag/v4.0.5): paquete, fixes y DXVK incluido.
- [Opciones DXVK 2.6.2](https://github.com/doitsujin/dxvk/blob/v2.6.2/dxvk.conf): latencia y presentación.
- [Valores de menú de FusionFix 4.0.5](https://github.com/ThirteenAG/GTAIV.EFLC.FusionFix/blob/v4.0.5/source/settings.ixx): índices de límite de FPS y botones.

No se bajó GTA IV a 1.0.7.0 ni se instaló Reality IV. No se añadió `-availablevidmem 24576` (no corresponde a la Deck), `numBackBuffers` (ausente en DXVK 2.6.2) ni opciones de descriptor buffers de otra versión. No hay una promesa de mejora universal.
