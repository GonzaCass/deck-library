# Servicio comunitario de Deck Library

API opcional en Python, SQLite y Gunicorn. Se consulta sin cuenta; publicar y enviar feedback requiere GitHub. No necesita las bases de datos de otros servicios. No recibe ROMs, mods, ejecutables ni archivos completos del emulador.

## Preparación

Desde la raíz del repositorio:

```sh
cp community/.env.example community/.env
# Completar GITHUB_CLIENT_ID y los parámetros de Traefik en community/.env.
docker compose --env-file community/.env -f community/compose.yaml config
docker compose --env-file community/.env -f community/compose.yaml up -d --build
```

La red externa debe existir. Las etiquetas usan `websecure` y el resolver configurado; no abren un puerto del host ni requieren cambiar la configuración de Traefik. El volumen `community-data` guarda SQLite. La imagen se ejecuta sin root y sin acceso al socket Docker.

Para preparar la imagen sin publicar el servicio: `docker compose --env-file community/.env -f community/compose.yaml build`.

## Acceso mediante GitHub

Crear una OAuth App propia en https://github.com/settings/applications/new. Homepage: `https://presets.jokerlan.xyz`; callback: `https://presets.jokerlan.xyz/auth/callback` (campo obligatorio del registro, no se utiliza en Device Flow). Activar **Enable Device Flow** y **Expire user access tokens**, dejar **Allow wildcard matching** desactivado, y poner el **Client ID público** en `GITHUB_CLIENT_ID`. Este flujo no requiere Client Secret.

Deck Library muestra un código que se autoriza en `https://github.com/login/device`. El servidor consulta `/user` para verificar la identidad; no pide permisos de repositorios ni correo. El token de GitHub se usa transitoriamente y no se guarda. Se emite una sesión propia de 30 días, almacenada por hash en el servidor y en un archivo privado con permisos 0600 en la Deck. «Cerrar sesión» revoca esa sesión. Las solicitudes de autorización pendientes vencen a los 15 minutos. No registrar cuerpos ni cabeceras de autenticación en el proxy.

## Moderación y copias

Todos los aportes nuevos y las modificaciones quedan `pending`, incluidos los del propietario. Solo los `approved` aparecen en consultas públicas. Aprobar un aporte no demuestra su rendimiento; se conserva el estado de prueba declarado por el autor. El alias de autor se obtiene de GitHub y no se acepta del JSON. Cada usuario puede dejar un resultado «funcionó» o «problemas» por perfil.

```sh
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server pending
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server approve ID
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server reject ID
docker compose --env-file community/.env -f community/compose.yaml exec api python -m community.server backup /data/backup.sqlite3
```

Exportar el backup fuera del volumen y restaurarlo solo con el servicio parado. `docker compose down` conserva el volumen; no usar `down -v` si se quieren conservar los aportes. Esta primera versión no tiene panel web, administración pública ni votos de popularidad; el feedback es un reporte de prueba. La moderación y los backups se administran por consola.

«Mis aportes» consulta solo los perfiles del usuario autenticado, incluidos pendientes y rechazados.

API: `GET /v1/me/presets`, `GET /health`, `GET /v1/presets?game=ID&adapter=eden`, `POST /v1/auth/start`, `POST /v1/auth/poll`, `POST /v1/logout`, `POST /v1/presets`, `POST /v1/presets/ID/feedback`. JSON limitado a 128 KiB. El cliente descarga y valida un perfil antes de ofrecer su aplicación con vista previa y respaldo. Nada se publica automáticamente.

Fuentes del protocolo: [GitHub Device Flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow), [Traefik Docker](https://doc.traefik.io/traefik/reference/routing-configuration/other-providers/docker/).
