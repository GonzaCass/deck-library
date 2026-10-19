# Ajustes de la comunidad

En 0.16 conviven el catálogo local/GitHub y un servicio opcional con SQLite, cuentas propias mediante Keycloak, perfiles moderados, estrellas y comentarios. La biblioteca local funciona sin cuenta y sin servicio.

## Usar y compartir

1. Abrir un juego y elegir **Comunidad** para consultar perfiles y comentarios.
2. Para valorar o publicar: **Mi cuenta → Crear cuenta / Iniciar sesión**. Los formularios de Keycloak aparecen dentro de Deck Library con su propio diseño; la app no lee la contraseña. El servicio público requiere verificar el correo. También se puede abrir **Cuenta** desde la barra superior. No hace falta una cuenta de GitHub.
3. **Compartir mis ajustes** toma las opciones permitidas del juego. Completar nombre, objetivo y descripción; pulsar **Revisar mis ajustes** para ver el contenido; **Publicar perfil** lo envía a revisión. **Mis aportes** muestra el estado.
4. Elegir un perfil publicado y **Usar este perfil** lo importa. La ficha permite revisar diferencias y aplicarlo con respaldo.

Cada cuenta tiene una valoración editable de 1 a 5 estrellas y un comentario por perfil. El promedio se calcula con votos reales; no se mezclan con los reportes de prueba antiguos sin estrellas. Los perfiles incluidos conservan su estado de propuesta y empiezan sin votos. Una valoración no garantiza el mismo rendimiento en otra instalación.

## Formato y privacidad

Se usa el JSON portable de [PRESETS.md](PRESETS.md): ID del juego, adaptador/versiones, hardware, objetivo, autor/licencia, estado de prueba y claves permitidas. No incluye rutas de ROMs, cuentas, claves, archivos del emulador ni comandos de ejecución. El servidor valida el mismo esquema y asigna el autor desde la sesión. Las consultas automáticas de estrellas envían solo el ID público del juego y su adaptador; se pueden desactivar desde las opciones de Actualizaciones. Nada se publica automáticamente.

La exportación/importación de un archivo JSON sigue disponible desde Más opciones, y los catálogos raw de GitHub no necesitan permisos de escritura. No incluir ROMs, firmware, DLC, texturas extraídas ni mods ajenos sin una licencia que permita compartirlos.

La instalación y moderación del servicio se documentan en [community/README.md](../community/README.md). No tiene panel web público de administración.
