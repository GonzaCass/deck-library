# Ajustes de la comunidad

Deck Library combina el catálogo local/GitHub con un servicio opcional de cuentas propias, perfiles, estrellas y comentarios. La biblioteca local funciona sin cuenta y sin servicio.

## Usar y compartir

1. Abrir un juego y elegir **Comunidad** para consultar perfiles y comentarios.
2. Para valorar o publicar: **Mi cuenta → Crear cuenta / Iniciar sesión**. Los formularios de Keycloak aparecen dentro de Deck Library con su propio diseño; la app no lee la contraseña. El servicio público requiere verificar el correo y confirmar **Conectar** para vincular la sesión. El nombre de usuario es público; el correo no debe usarse como alias. También se puede abrir **Cuenta** desde la barra superior. No hace falta una cuenta de GitHub.
3. **Compartir mis ajustes** toma las opciones permitidas del juego. Completar nombre, objetivo y descripción; pulsar **Revisar mis ajustes** para ver el contenido; **Publicar perfil** lo hace visible para quienes usan el mismo juego y programa. Si se edita el borrador, hay que revisarlo de nuevo. **Mis aportes** muestra el estado. Un servicio propio puede habilitar moderación previa.
4. Elegir un perfil publicado y **Usar este perfil** lo importa. La ficha permite revisar diferencias y aplicarlo con respaldo.

Cada cuenta tiene una valoración editable de 1 a 5 estrellas y un comentario por perfil. El promedio se calcula con votos reales; no se mezclan con los reportes de prueba antiguos sin estrellas. Los perfiles incluidos conservan su estado de propuesta y empiezan sin votos. Una valoración no garantiza el mismo rendimiento en otra instalación.

## Formato y privacidad

Se usa el JSON portable de [PRESETS.md](PRESETS.md): ID del juego, adaptador/versiones, hardware, objetivo, autor/licencia, estado de prueba y claves permitidas. No incluye rutas de ROMs, cuentas, claves, archivos del emulador ni comandos que se ejecuten automáticamente. Las instrucciones y opciones de lanzamiento se comparten como texto para revisar. El servidor valida el mismo esquema y asigna el autor desde la sesión. Las consultas automáticas de estrellas envían solo el ID público del juego y su adaptador; se pueden desactivar desde las opciones de Actualizaciones. Nada se publica automáticamente.

La exportación/importación de un archivo JSON sigue disponible desde Más opciones, y los catálogos raw de GitHub no necesitan permisos de escritura. No incluir ROMs, firmware, DLC, texturas extraídas ni mods ajenos sin una licencia que permita compartirlos.

La instalación y moderación del servicio se documentan en [community/README.md](../community/README.md). No tiene panel web público de administración.

## Uso desde un juego (1.4.4)

En la parte superior de Perfiles están **Crear mis ajustes**, **Buscar en la comunidad** e **Importar archivo**. **Valorar este perfil** abre directamente la selección de 1 a 5 estrellas y el comentario opcional. Se necesita una cuenta; una persona puede modificar su valoración, pero no valorar su propio perfil. Los perfiles incluidos también se pueden valorar. Un perfil solo local debe publicarse para recibir valoraciones.

**Aplicar ajustes** guarda la configuración sin abrir el juego; **Aplicar y jugar** hace ambas cosas en un paso. Cuando ya coincide con lo guardado, la segunda acción pasa a **Jugar**. La alternativa **Compatibilidad** de Eden aumenta la precisión gráfica y puede reducir los FPS; no equivale a una verificación de jugabilidad. La etiqueta **Verificado en Deck** conserva el requisito de coincidencia exacta de repositorio y versión; la versión se consulta por separado en las condiciones de la prueba.
