# Servicio comunitario de Deck Library

API opcional en Python, SQLite y Gunicorn. Se consulta sin cuenta; publicar y valorar requiere una cuenta propia mediante Keycloak. No necesita las bases de datos de otros servicios. No recibe ROMs, mods, ejecutables ni archivos completos del emulador.

## Preparación

Desde la raíz del repositorio:

```sh
cp community/.env.example community/.env
# Completar OIDC_ISSUER, OIDC_CLIENT_ID y los parámetros de Traefik.
docker compose --env-file community/.env -f community/compose.yaml config
docker compose --env-file community/.env -f community/compose.yaml up -d --build
```

La red externa debe existir. Si la API está detrás de Traefik, configurar `COMMUNITY_TRUST_PROXY_CIDRS` con el CIDR de su red privada o la IP del proxy con máscara `/32`. Solo esas conexiones pueden aportar `X-Real-IP` para separar los límites por cliente; con el valor vacío se ignoran las cabeceras reenviadas. No incluir redes públicas de usuarios. Las etiquetas usan `websecure` y el resolver configurado; no abren un puerto del host ni requieren cambiar la configuración de Traefik. El volumen `community-data` guarda SQLite. La imagen se ejecuta sin root y sin acceso al socket Docker.

Para preparar la imagen sin publicar el servicio: `docker compose --env-file community/.env -f community/compose.yaml build`.

## Cuenta propia mediante Keycloak

Configurar `OIDC_ISSUER=https://auth.example.org/realms/REALM` y `OIDC_CLIENT_ID=deck-library`. Importar `keycloak-client.json` en el realm elegido: cliente público, Device Authorization habilitado, sin Client Secret, sin password grant ni service accounts y sin acceso a todos los scopes. Habilitar registro de usuarios en el realm si se quiere ofrecer Crear cuenta. El ejemplo usa el dominio público del servicio; para otro despliegue se reemplazan los valores en `.env`.

La app integra los formularios en un proceso WebKit aislado y consulta automáticamente hasta completar la autorización. El navegador externo queda como alternativa explícita si no está disponible el componente integrado. Las contraseñas quedan en Keycloak. El servidor verifica `userinfo`, descarta el token del proveedor y emite una sesión propia de 30 días. El cliente guarda esa sesión con permisos 0600; Cerrar sesión la revoca. No registrar cuerpos ni cabeceras de autenticación.

El esquema SQLite se migra sin perder sesiones ni reportes. Hacer un backup antes de actualizar. La base y `.env` quedan fuera de Git y del paquete.

## Compatibilidad con clientes antiguos mediante GitHub

Crear una OAuth App propia en https://github.com/settings/applications/new. Homepage: `https://presets.jokerlan.xyz`; callback: `https://presets.jokerlan.xyz/auth/callback` (campo obligatorio del registro, no se utiliza en Device Flow). Activar **Enable Device Flow** y **Expire user access tokens**, dejar **Allow wildcard matching** desactivado, y poner el **Client ID público** en `GITHUB_CLIENT_ID`. Este flujo no requiere Client Secret.

Deck Library muestra un código que se autoriza en `https://github.com/login/device`. El servidor consulta `/user` para verificar la identidad; no pide permisos de repositorios ni correo. El token de GitHub se usa transitoriamente y no se guarda. Se emite una sesión propia de 30 días, almacenada por hash en el servidor y en un archivo privado con permisos 0600 en la Deck. «Cerrar sesión» revoca esa sesión. Las solicitudes de autorización pendientes vencen a los 15 minutos. No registrar cuerpos ni cabeceras de autenticación en el proxy.

## Moderación y copias

Desde 1.3.0, los aportes válidos de cuentas autenticadas se publican de inmediato (`approved`). Para revisar cada aporte antes de hacerlo público, configurar `COMMUNITY_REVIEW_REQUIRED=true` al desplegar: los nuevos y sus modificaciones quedan `pending`, incluidos los del propietario. Solo los `approved` aparecen en consultas públicas. Publicar o aprobar no demuestra rendimiento ni agrega el juego a Juegos validados; se conserva la prueba declarada por el autor. El alias de autor se obtiene de la identidad autenticada y no se acepta del JSON. Cada usuario puede dejar una valoración de 1 a 5 estrellas y un comentario editable por perfil. Se conservan los reportes antiguos.

```sh
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server pending
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server approve ID
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server reject ID
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server backup /data/backup.sqlite3
```

Exportar el backup fuera del volumen y restaurarlo solo con el servicio parado. `docker compose down` conserva el volumen; no usar `down -v` si se quieren conservar los aportes. Esta primera versión no tiene panel web, administración pública; las valoraciones se muestran en la aplicación. La moderación y los backups se administran por consola.

«Mis aportes» consulta solo los perfiles del usuario autenticado, incluidos pendientes y rechazados.

API: `GET /v1/me`, `GET /v1/auth/providers`, `GET /v1/presets/ID/feedback`, `GET /v1/me/presets`, `GET /health`, `GET /v1/presets?game=ID&adapter=eden`, `POST /v1/auth/start`, `POST /v1/auth/poll`, `POST /v1/logout`, `POST /v1/presets`, `POST /v1/presets/ID/feedback`, `POST /v1/bug-reports`. JSON limitado a 128 KiB. El cliente descarga y valida un perfil antes de ofrecer su aplicación con vista previa y respaldo. Nada se publica automáticamente.

Fuentes del protocolo: [GitHub Device Flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow), [Traefik Docker](https://doc.traefik.io/traefik/reference/routing-configuration/other-providers/docker/).

## Tema de acceso integrado

`keycloak-theme/deck-library` contiene el tema de acceso, que hereda las plantillas y validaciones de `keycloak.v2` (probado con Keycloak 26.3.4). Copiar o montar esa carpeta en `/opt/keycloak/themes/deck-library:ro` del contenedor de Keycloak. Por ejemplo, desde la carpeta de despliegue de Keycloak:

```yaml
volumes:
  - /ruta/deck-library/community/keycloak-theme/deck-library:/opt/keycloak/themes/deck-library:ro
```

Conservar los otros volúmenes existentes. Recrear solo el contenedor de Keycloak para activar el montaje. El cliente importable selecciona el tema mediante `attributes.login_theme=deck-library`; para un cliente ya existente, elegir **Login theme → deck-library** en sus ajustes. No cambiar el tema global del realm ni el de otros clientes. El tema ofrece textos de Deck Library en español incluso si el realm no tiene internacionalización habilitada. No modificar las políticas de verificación de correo, doble factor ni contraseña para integrar la interfaz.

La vista usa memoria temporal para cookies y almacenamiento, deniega permisos y ventanas emergentes y limita la navegación al origen HTTPS del proveedor. El servidor no incorpora un endpoint de contraseñas ni permisos administrativos. `GET /v1/me` valida la sesión propia; un 401 elimina la sesión local vencida.

## Remitente específico de Deck Library

Si el realm también tiene otros clientes, no cambiar su remitente SMTP global para poner el nombre de Deck Library. El proveedor opcional [keycloak-mail](keycloak-mail/README.md) aplica un remitente específico solo al cliente configurado y conserva el transporte SMTP existente. Incluye código fuente, pruebas y compilación contra la versión instalada de Keycloak.

## Diagnósticos privados (1.3.0)

**Ayuda → Reportar un problema** permite revisar un reporte, exportar un ZIP, abrir un issue de GitHub o enviarlo expresamente al servicio. No se envía automáticamente ni se necesita una cuenta. El servidor valida tamaño y formato, vuelve a ocultar credenciales y datos personales conocidos y limita los envíos. La redacción automática no sustituye la revisión del contenido por quien lo comparte.

`POST /v1/bug-reports` devuelve un identificador de recepción. El reporte se guarda en la tabla privada `bug_reports` del volumen SQLite y no tiene una ruta pública de descarga. Solo el administrador con acceso al volumen puede consultarlo por su ID; conviene eliminarlo una vez resuelto el incidente. GitHub recibe únicamente el texto que la persona decide publicar y los adjuntos que añade al issue. El servidor no crea issues en su nombre.
