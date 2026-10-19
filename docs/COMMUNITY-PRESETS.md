# Ajustes de la comunidad

Estado 0.11: catálogo local/GitHub, importación y exportación, servicio opcional SQLite con acceso GitHub, aportes moderados y feedback por usuario. El servidor necesita su OAuth Client ID antes de habilitar la publicación. No hay votos de popularidad ni panel web. La app no sube configuraciones automáticamente. Ver [instalación del servicio](../community/README.md). Las secciones siguientes conservan el diseño a largo plazo; no todas describen funciones ya implementadas.

## Experiencia

En la ficha de cada juego: **Ajustes de la comunidad**. Se muestran perfiles compatibles con ese juego, emulador y modelo de Deck. Cada ficha indica autor, fecha, versiones probadas, objetivo (nitidez, estabilidad o batería), cambios y fuente. FPS medidos por el autor se identifican como reportes, no garantías.

Acciones: **Ver cambios**, **Aplicar**, **Restaurar ajuste anterior**, **Publicar mi ajuste** y **Reportar**. Antes de aplicar se muestra la comparación y se crea un backup local. Si el juego está abierto se espera a su cierre; no se toca un archivo que el emulador pueda sobrescribir al salir.

Consultar y aplicar no requiere cuenta. Publicar y votar requiere autenticación. Un aporte nuevo comienza pendiente de revisión; no recibe automáticamente una etiqueta de recomendado. Los perfiles probados localmente son una categoría distinta de los recomendados por la comunidad.

## Alojamiento recomendado

Para publicar desde la misma app, votos y moderación: una API HTTPS pequeña en el servidor del proyecto y SQLite con backups. No requiere PostgreSQL para el volumen inicial. GitHub conserva el código, los perfiles revisados exportados y sus fuentes. El cliente no lleva una credencial compartida de escritura.

Alternativa sin servidor: catálogo JSON versionado en GitHub y aportes mediante pull requests con la cuenta de cada usuario. Descargar/aplicar puede seguir siendo de un clic; enviar aportes requiere autenticación y revisión en GitHub. No se debe conceder a todos los usuarios acceso directo de escritura al repositorio principal.

## Datos portables

No utilizar el ID local de Deck Library como identidad pública: contiene rutas y cambia entre máquinas. Switch puede usar el title ID; Wii, el game ID; ports, un identificador público del proyecto y su versión. No identificar un juego por una ruta personal o solo por su nombre traducido.

Cada perfil contiene: versión de esquema; ID y nombre público de juego; plataforma y emulador; versión del emulador y actualización del juego; hardware LCD/OLED; versiones de SteamOS probadas; autor; objetivo; ajustes; notas; fuentes; mods requeridos por nombre y versión; fecha y revisión. Los mods no se adjuntan. Un perfil de controles también necesita su propio adaptador y formato; no equivale a un preset gráfico.

El primer adaptador propuesto es Eden: opciones gráficas/CPU por juego. Después, WiiCompiled y Dolphin mediante adaptadores separados. No asumir que claves de INI tienen el mismo significado entre emuladores o versiones.

Solo exportar claves permitidas de un registro de ajustes conocido. Nunca subir el INI completo: puede incluir rutas, usuarios, controles, partidas o datos privados. Nunca ejecutar comandos/scripts de un perfil ni aceptar rutas arbitrarias de destino. La versión del adaptador determina las claves, tipos y rangos válidos.

## Servicio

Entidades iniciales: usuarios, juegos, revisiones de perfiles, resultados reportados, votos únicos por usuario y reportes de moderación. Un perfil publicado es inmutable; una edición crea otra revisión, permitiendo volver atrás.

API propuesta: buscar perfiles por compatibilidad, obtener una revisión, enviar un aporte autenticado, votar y reportar. Límite de tamaño y frecuencia; validación del mismo esquema en servidor y cliente; revisiones pendientes antes de entrar al catálogo recomendado. El cliente usa caché local para consultar y aplicar perfiles ya descargados sin conexión.

## Contenido y GitHub

Compartir ajustes originales (valores de resolución, filtros y opciones del emulador) es distinto de redistribuir juegos o recursos protegidos. Cada aporte declara su licencia y fuentes. No incluir ROMs, claves, firmware, DLC, texturas extraídas, ejecutables ni mods de terceros sin licencia compatible.

Esto no constituye una garantía legal para cualquier contenido: GitHub exige respetar propiedad intelectual y privacidad. Referencias: https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies y https://docs.github.com/en/rest/repos/contents.

## Para conectar un servicio real

Faltan dominio/URL HTTPS, forma de despliegue (por ejemplo Docker) y mecanismo de autenticación. No se ha desplegado un servicio, creado una base de datos externa ni publicado contenido en una cuenta de GitHub.
