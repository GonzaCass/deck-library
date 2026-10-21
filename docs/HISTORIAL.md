# Historial de cambios

Descripciones de cómo era la app en cada etapa hasta la 0.14; parte de ellas fue reemplazada por versiones posteriores. Lo vigente está en [LEEME.md](../LEEME.md) y [README.md](../README.md), y cada versión publicada tiene sus notas en [GitHub](https://github.com/GonzaCass/deck-library/releases).

## 0.4.0

- **Quitar de Steam:** en la ficha de cada juego y en la barra de selección. No toca juegos ni partidas; guarda un respaldo de la lista de accesos.
- **Mando:** los accesos nuevos reciben el layout de gamepad de Steam para DualSense, DualShock, Xbox y Switch Pro. Para un acceso existente, usar **Mando → Asignar layout** con Steam cerrado.
- **Actualizaciones:** página propia con avisos de Deck Library, ajustes recomendados y ports. La instalación automática de Deck Library se activa en esa página.
- **Ajustes del juego:** resolución, FPS, correcciones y rendimiento por juego (DuckStation, Dolphin, Eden y Prism), con respaldo y restauración.
- **Catálogo de ports:** reúne las listas de Quiver y GithubLauncher, recomendados (Spider-Man 1 y 2 de PSX) y repositorios propios, con íconos o portadas, categorías y filtros. Instala desde GitHub con verificación de integridad y avisa cuando hay una versión nueva. Los ports instalados con Quiver o GithubLauncher también se detectan.
- **Actualización automática:** Deck Library avisa cuando hay una versión nueva y se actualiza sola en modo Escritorio; se desactiva en la página Actualizaciones.
- **Ports que compilan en la Deck (por ejemplo Spider-Man 1 y 2 de PSX):** se ejecutan dentro del SDK de KDE de Flatpak, que Deck Library instala una vez con confirmación. No hace falta root ni tocar SteamOS. Hay que aportar el disco USA y la BIOS que pide cada kit.
- **Configuración automática de ports:** el botón **Configurar** del catálogo busca el disco en la biblioteca (por el serial interno) y la BIOS (por hash), y prepara Spider-Man 1 y 2, Spyro (OpenPete) y Crash Team Racing Turbocharged.
- **Biblioteca sin duplicados:** nuevo filtro por tipo (ports, emulador, instancias de Minecraft…) y la opción **Preferir ports**, que oculta la versión por emulador de un juego que ya tiene port.

## 0.11

Interfaz adaptada a la pantalla de la Deck, lista con carátulas, vista por plataforma y aviso fijo de cambios pendientes de Steam. «Configurar juego» reúne las acciones de ajustes. «Conflictos» muestra las rutas coincidentes. Desde Ajustes se puede agregar Deck Library a Steam para abrirla en modo Juego. La comunidad opcional usa cuentas propias mediante Keycloak y un servicio con SQLite. Ver [interfaz](docs/DECK-INTERFACE.md) y [servicio comunitario](community/README.md).


## 0.12

Nueva estructura de la ventana: biblioteca a ancho completo y navegación superior. Cada juego tiene pestañas **Perfiles**, **Opciones**, **Controles**, **Archivos** y, en Switch, **Contenido**. Aplicar y guardar quedan visibles mientras se desplazan las opciones. Los cambios de Steam muestran cada operación por nombre y se pueden descartar. «Preferir ports» se retiró: se muestran tanto el port como la copia emulada. Los scripts de EmuDeck no se cuentan como instalaciones adicionales. Las actualizaciones muestran las notas que publicó el autor para esa versión.


## 0.13

La ficha del juego se reemplazó por una vista con carátula, acción principal y tarjetas de ajustes. Se retiró la navegación por pestañas del juego. Aplicar y Deshacer permanecen visibles; los cambios y sus errores aparecen en la ficha. Las herramientas secundarias se agrupan por tarea y la selección de perfiles no aplica cambios automáticamente. La cabecera se compacta en ventanas bajas, el foco empieza en Jugar y Escape vuelve primero al juego. Se conserva la integración con Steam, EmuDeck, Quiver, Prism y los perfiles comunitarios.

## 0.14

- **Catálogo de ports** reemplaza Explorar; abre el catálogo sin pasos intermedios.
- Cada port muestra su descarga, porcentaje y tiempo estimado en su propia fila. Durante la compilación se indica la fase; no se estima un porcentaje sin datos.
- Los ajustes de Eden se presentan como **Equilibrado**, **Rendimiento** y **Calidad**, con iconos y valoraciones reales. Los perfiles sin votos lo indican.
- **Comunidad → Mi cuenta** permite crear una cuenta o iniciar sesión (integrado en la app desde 0.16). No necesitás GitHub. Para compartir: **Compartir mis ajustes → Revisar mis ajustes → Publicar perfil**. El aporte queda pendiente de revisión. Las estrellas y los comentarios requieren sesión.
- En modo Juego: cruceta o stick para navegar, A para activar, B para volver y LB/RB para cambiar de sección. Trackpad derecho y R2 conservan puntero/clic. **Steam + X** abre el teclado. El soporte nativo de mandos usa SDL2, incluido en SteamOS.
- Se conserva la biblioteca al cambiar de pestaña para evitar reconstruir todas las carátulas.
