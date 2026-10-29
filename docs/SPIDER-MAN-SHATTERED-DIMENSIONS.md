# Spider-Man: Shattered Dimensions en Steam Deck

**Estado: audio, voces y controles confirmados por el usuario.** La experiencia de juego corresponde a una instalación observada el 1 de octubre de 2026. Deck Library ofrece ahora **Aplicar arreglo** en la ficha del juego para reproducir la preparación de audio en el prefijo propio de cada instalación; esto no agrega una nueva prueba de jugabilidad.

## Aplicarlo desde Deck Library

Agregar el `Game.exe` de Windows de 32 bits a Steam, seleccionar **Proton 10.0** en Propiedades → Compatibilidad e iniciarlo una vez para crear el prefijo. Luego abrir la ficha del juego en Deck Library y elegir **Aplicar arreglo**. No hace falta una cuenta comunitaria, descargar el ZIP ni copiar comandos.

El botón verifica el ejecutable, el acceso y su prefijo, prepara Protontricks si hace falta e instala únicamente los componentes pendientes `d3dx9_43` y `xact`. Copia `d3dx9_43.dll` desde el prefijo local cuando no hay una copia junto al juego. **Conservar idioma actual** es la opción predeterminada y no importa cambios de idioma en el registro. Cambiarlo a español es opcional desde **Opciones y requisitos del arreglo**. Los archivos de voz del idioma elegido deben formar parte de la instalación del juego.

Antes de modificarlo guarda los registros de Wine y los archivos locales afectados en una carpeta privada de respaldos y muestra su ruta en los detalles. Este respaldo no es una copia completa del prefijo: las dependencias de DirectX instaladas permanecen en él. Conserva las partidas, el acceso, el mando y la versión de Proton seleccionada en Steam. No cambia la compatibilidad de Steam mientras el cliente está abierto. Si el juego está abierto, falta un prefijo único o está seleccionado otro Proton, explica el requisito antes de modificarlo. Repetir el arreglo reutiliza las dependencias instaladas y conserva una DLL local existente.

Herramienta: [Protontricks](https://github.com/Matoking/protontricks); componentes: [catálogo oficial de Winetricks](https://github.com/Winetricks/winetricks/blob/master/files/verbs/all.txt). No se distribuyen DLL ni archivos del juego.

## Configuracion comprobada

- Juego de Windows agregado a Steam como acceso externo. Steam apunta directamente a `Game.exe`, con la carpeta del juego como directorio de inicio. Asi encuentra `Data` y otros recursos.
- Herramienta de compatibilidad seleccionada: **Proton 10.0** (`proton_10` en Steam; el prefijo informa `10.1000-105`).
- El prefijo está en `steamapps/compatdata/<AppID del acceso>/pfx`. El ID de un juego externo es local, **no un identificador universal**; Deck Library localiza el prefijo del acceso propio.
- Las opciones de lanzamiento del acceso estan vacias. La carpeta del juego contiene `steam_appid.txt.disabled`, nombre que indica que ese archivo se aparto. No crear un `steam_appid.txt` con el ID local.
- El juego se inicia desde Steam, conservando el contexto de Steam Input. En el registro del prefijo, `xinput1_3` tiene prioridad `native,builtin`. El usuario confirma que los controles de la Deck responden. Esta guia no documenta una asignacion de botones individuales.

## Audio y voces

El prefijo contiene DLL de DirectX de **XAudio2, XACT y X3DAudio**. Hay archivos de estas familias en `drive_c/windows/system32` y `drive_c/windows/syswow64`; para este ejecutable de 32 bits interesan especialmente los de `syswow64`. En `pfx/user.reg`, bajo `Software\Wine\DllOverrides`, las familias `xaudio2_0` a `xaudio2_7`, `xactengine2_0` a `xactengine3_7` y `x3daudio1_0` a `x3daudio1_7` usan `native,builtin`. `d3dx9_43` usa `native`, y tambien hay una copia de `d3dx9_43.dll` junto a `Game.exe`.

Este es el estado final observado, no un registro paso a paso de la instalacion. No es posible atribuir con certeza el arreglo de voces a una DLL individual. Para reproducirlo, instalar las dependencias legacy de DirectX/XACT **en el prefijo creado por el acceso de ese juego**, revisar los overrides en `winecfg` y probar audio general y dialogos por separado. Antes de modificar el prefijo, respaldarlo: puede incluir partidas y configuraciones.

El archivo `pfx/winetricks.log` de esta instalacion registra exactamente `d3dx9_43` y `xact`. El paquete de preparacion usa esos dos componentes mediante Protontricks en el prefijo local de cada persona; no incluye DLL ni archivos del juego.

## Idioma en el registro

En `HKEY_CURRENT_USER\Software\Activision\Spider-Man (TM) SD\Settings\Game`, la instalacion que funciona tiene cuatro valores de tipo cadena: `AudioLanguage=ESN`, `Language=ESN`, `Locale=ESN` y `TextLanguage=ESN`. El ZIP incluye `Idioma-Espanol.reg` con solo esos valores y el instalador lo importa mediante Protontricks en el prefijo del acceso detectado. Antes guarda una copia de `user.reg` en el propio prefijo. La configuracion regional general del prefijo sigue en `en-US`; no es necesario cambiarla para reproducir el estado observado. Las voces en espanol requieren que la instalacion del juego contenga los archivos correspondientes.

## Pasos para otra Deck

1. Instalar una copia propia y completa del juego. Agregar `Game.exe` como juego externo en Steam y poner su carpeta como directorio de inicio.
2. En **Propiedades > Compatibilidad**, seleccionar Proton 10.0 e iniciar una vez para crear el prefijo.
3. En ese prefijo instalar las dependencias legacy de DirectX/XACT que falten y comprobar DLL y overrides de XAudio2, XACT, X3DAudio y `d3dx9_43`. Las rutas de esta Deck no se copian literalmente a otra.
4. Lanzar desde Steam. Comprobar efectos, voces en una escena con dialogos y controles en juego. Si el mando no responde, revisar el layout de Steam Input asignado a ese acceso.

Los archivos de juego y las DLL de terceros no se incluyen en Deck Library. La comprobación funcional corresponde a la instalación registrada. El arreglo automático es una receta propia de la app; los perfiles comunitarios de instrucciones no ejecutan comandos ni instalan dependencias. El layout de Steam Input se conserva y no se infiere del prefijo.
