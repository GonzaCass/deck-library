# DMC3 Crimson: arreglo de arranque desde Steam

**Estado: arranque comprobado en Steam Deck OLED, modo Escritorio, el 1 de octubre de 2026.** Steam inició DMC3, cargó `Crimson.dll` y mostró «DMC3 Crimson has loaded». No se probó una misión, rendimiento sostenido ni el modo Juego después de este cambio.

Este documento registra el arreglo local y los requisitos para incorporarlo a una acción de Deck Library. **Todavía no hay un botón de instalación de Crimson en la aplicación.** El botón integrado para GTA IV es un arreglo distinto.

## Instalación revisada y causa

- Juego: Devil May Cry HD Collection de Steam, App ID **631510**.
- Mod instalado: paquete **Crimson 0.5a**.
- La preparación anterior había dejado un `dmc3.exe` compatible antiguo; no es el ejecutable más reciente de Steam. Este arreglo de arranque conserva ese ejecutable y los recursos ya instalados, sin volver a bajar el juego.
- Proton seleccionado al comprobar el arreglo: **Proton Experimental**.

Había dos puntos relevantes:

1. El acceso normal iniciaba `dmcLauncher.exe`. Su registro `logs/dinput8.txt` decía `No Match`; ese mensaje sólo significa que el cargador no encontró un ejecutable al cual inyectar Crimson en ese proceso. No demuestra por sí solo que el launcher sea la causa del cierre.
2. Al iniciar DMC3 directamente desde Steam, el cargador reconoció `dmc3.exe` y cargó Crimson, pero Proton registró el cierre real:

```text
wine: Call ... to unimplemented function steam_api64.dll.SteamAPI_Init, aborting
```

`objdump -p` confirmó que el ejecutable compatible requiere `SteamAPI_Init`, mientras que la DLL presente en la instalación actual no la exporta. No era simplemente una opción de FPS o un mod que Steam no cargaba.

## Solución aplicada

Se creó un entorno separado en:

```text
~/.local/share/dmc3-crimson/
  launch-crimson.sh
  runtime/
    dmc3.exe
    steam_api64.dll
    ... enlaces a los demás archivos y carpetas de la instalación
  respaldo-arranque-20261001-231253/
```

`runtime/dmc3.exe` es una copia del ejecutable compatible que ya estaba instalado. `runtime/steam_api64.dll` es una DLL compatible obtenida de **la instalación local de Steam de Kingdom Hearts HD 1.5+2.5 ReMIX del usuario**. No se descargó de un sitio de DLLs ni se usó un emulador de Steam API. Esto es la procedencia de esta prueba concreta, no una recomendación de instalar Kingdom Hearts ni de elegir cualquier DLL de otro juego.

Se comprobaron los siete símbolos que importaban DMC3/Crimson y el launcher compatible:

Identificación de los archivos locales comprobados (SHA-256, no enlaces de descarga):

```text
dmc3.exe         4d7962a8f1ee61a58fbab11534de62d8ceaf3e9a84aa3bd3824a15b8d3678a67
steam_api64.dll  a44e5537939ae4eebc69000589aa9b2437a667813a1657cc779198bae9b815a9
```

Imports comprobados:

```text
SteamAPI_GetHSteamPipe
SteamAPI_GetHSteamUser
SteamAPI_Init
SteamAPI_RestartAppIfNecessary
SteamAPI_Shutdown
SteamInternal_ContextInit
SteamInternal_CreateInterface
```

La misma DLL compatible **no exporta `SteamInternal_SteamAPI_Init`**, requerido por los ejecutables actuales de DMC1/DMC2. Por eso quedó únicamente en `runtime`: se restauró byte por byte la DLL original en la carpeta de la colección. Esto evita introducir esa incompatibilidad en DMC1/DMC2; no sustituye una prueba de arranque de esos juegos.

Los demás archivos y carpetas de `runtime` son enlaces a la instalación. El directorio de trabajo original de Steam se conserva. No se duplicaron partidas ni se cambiaron los ajustes de Crimson durante este arreglo.

En **Steam → Propiedades de Devil May Cry HD Collection → General → Opciones de lanzamiento**, quedó el wrapper seguido de `%command%`. En esta Deck:

```text
"$HOME/.local/share/dmc3-crimson/launch-crimson.sh" %command%
```

Para otra instalación debe usarse la ruta absoluta de su wrapper. No copiar la ruta de esta Deck literalmente.

El wrapper probado conserva todos los argumentos de Steam/Proton y reemplaza sólo el destino del launcher:

```bash
#!/bin/bash
set -e
args=("$@")
found=0
for i in "${!args[@]}"; do
    if [[ "${args[$i]}" == */dmcLauncher.exe ]]; then
        game="${XDG_DATA_HOME:-$HOME/.local/share}/dmc3-crimson/runtime/dmc3.exe"
        if [[ ! -f "$game" ]]; then
            echo "No se encuentra dmc3.exe: $game" >&2
            exit 1
        fi
        args[$i]="$game"
        found=1
    fi
done
if [[ "$found" != 1 ]]; then
    echo "No se encontro dmcLauncher.exe en el comando de Steam." >&2
    exit 1
fi
export WINEDLLOVERRIDES="dinput8=n,b"
exec "${args[@]}"
```

El acceso de la colección ahora abre **DMC3 directamente**. Conserva el comando administrado por Steam, su prefijo de Proton y su identidad para Steam Input. No fija `DISPLAY`, no ejecuta Proton por fuera de Steam y no desactiva autenticación.

## Respaldo y cómo deshacer

El respaldo local contiene las opciones anteriores en `cambios.json`, el wrapper anterior si existía, una copia de `localconfig.vdf`, la DLL original de la colección y el registro de procedencia de la DLL compatible.

Para deshacer la apertura directa, cerrar DMC3 y restaurar sólo sus opciones de lanzamiento anteriores:

```text
WINEDLLOVERRIDES=dinput8=n,b %command%
```

La DLL original ya está restaurada en la colección: no hay que reemplazarla para deshacer el wrapper. El entorno separado puede conservarse hasta terminar la comparación. **No restaurar `localconfig.vdf` entero con Steam abierto:** podría sobrescribir opciones de otros juegos. Volver a las opciones anteriores recupera el comportamiento anterior, no garantiza arreglar el launcher ni la instalación antigua.

## Comprobación y límites

En el arranque final se verificó:

- Proceso `dmc3.exe` iniciado desde `runtime` a través de Steam.
- `Crimson.dll` presente en los módulos cargados.
- `steam_api64.dll` cargada desde el entorno separado.
- Registro nuevo de Crimson, inicialización de Weapon Wheel y aviso visible de carga del mod.
- DLL original de la colección igual a su respaldo.

Antes de la prueba Steam también frenó el arranque por una sesión con Wallpaper Engine en otra PC. Ese aviso era independiente del fallo de DLL; una automatización no debería interpretarlo como un crash de Crimson ni cerrar otra sesión sin decisión del usuario.

La instalación anterior registraba además un recurso faltante, `newBaseVergilAnims_pl021_00_0.pac`. El arreglo de arranque no lo repone. Hay que probar una misión y las acciones de Vergil antes de dar por comprobada toda la instalación del mod. Tampoco se validaron los objetivos de 90 FPS ni todas las mejoras QoL durante esta revisión.

Una actualización de Steam, del ejecutable o del mod puede dejar desactualizada la copia de `runtime`. Comprobar versiones, imports y recursos nuevamente antes de regenerarla.

## Requisitos para un futuro botón de Deck Library

1. Detectar la instalación de App ID 631510 y Crimson, con el juego cerrado. Distinguir una instalación compatible de una instalación nueva: este wrapper no adapta por sí solo el ejecutable más reciente al mod.
2. Recibir una DLL compatible de procedencia verificable y comprobar los imports del ejecutable/mod. Si falta un símbolo, rechazar el cambio con el motivo. No distribuir DLLs de juegos ni ejecutables en el release de Deck Library.
3. Preparar una copia privada del ejecutable compatible, la DLL y los enlaces a los recursos. Mantener la DLL original en la colección y los datos de usuario en su ubicación original.
4. Respaldar el entorno y las opciones de lanzamiento específicas del juego antes de cambiar nada. Conservar otros argumentos/overrides que el usuario necesite; el wrapper de esta sesión reproduce únicamente el override que ya tenía esta instalación.
5. Aplicar el wrapper al comando de Steam; ofrecer restauración sólo de los archivos y opciones propios. Comprobar arranque por separado y registrar su resultado como `boot-tested`, no como confirmación de gameplay.

La guía y el wrapper son compartibles. La DLL, el ejecutable, las partidas y los respaldos personales quedan fuera del código y de los paquetes públicos.

Proyecto del mod: [DMC3 Crimson](https://github.com/berthrage/DMC3-Crimson). Los hallazgos de imports, módulos y arranque anteriores proceden de la inspección local de esta instalación.
