# Spider-Man: Shattered Dimensions en Steam Deck

**Estado: el usuario confirma que el juego funciona con audio, voces y controles integrados.** Esta guia registra la configuracion local observada el 1 de octubre de 2026. Deck Library todavia no tiene un adaptador de Windows/Proton para aplicarla automaticamente.

## Configuracion comprobada

- Juego de Windows agregado a Steam como acceso externo. Steam apunta directamente a `Game.exe`, con la carpeta del juego como directorio de inicio. Asi encuentra `Data` y otros recursos.
- Herramienta de compatibilidad seleccionada: **Proton 10.0** (`proton_10` en Steam; el prefijo informa `10.1000-105`).
- El acceso de esta Deck tiene ID `3027748755`, con su prefijo en `steamapps/compatdata/3027748755/pfx`. Es un ID local de juego externo, **no un identificador universal**; en otra Deck hay que localizar el prefijo del acceso propio.
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

Los archivos de juego y las DLL de terceros no se incluyen en Deck Library. La comprobacion funcional corresponde a esta instalacion; el procedimiento necesita una segunda prueba antes de ofrecerse como arreglo automatico.

## Para convertirlo en preset aplicable

El esquema v1 solo acepta adaptadores `eden`, `wiicompiled`, `dolphin` y `prism`. Un JSON con `adapter: proton` seria rechazado. La aplicacion necesitaria un adaptador nuevo que encuentre el acceso y prefijo locales, compruebe Proton y las dependencias, muestre los cambios, respalde lo que vaya a modificar y permita restaurarlo. El layout de Steam Input requiere una exportacion y revision aparte; no se puede inferir de este prefijo.
