# Remitente de Deck Library en un Keycloak compartido

Keycloak 26.3.4 configura SMTP por realm. Este proveedor cambia el remitente solo cuando el contexto corresponde al realm `master` y al cliente `deck-library`. Los demás clientes y realms conservan su configuración original. El SMTP, la autenticación y TLS siguen a cargo del proveedor predeterminado de Keycloak; no se incluyen credenciales.

Para Deck Library se configura **Deck Library <decklibrary@jokerlan.xyz>** en From, Reply-To y envelope sender. La dirección debe existir como buzón o alias autorizado de la cuenta SMTP. Con Docker Mailserver puede agregarse un alias al buzón existente:

```sh
docker exec mailserver setup alias add decklibrary@example.org auth@example.org
```

Usar las direcciones reales del despliegue. El alias debe estar activo antes de habilitar el proveedor. No requiere reiniciar el servidor de correo.

## Compilar y comprobar

Se necesita un JDK con soporte de Java 21 y los jars de la misma versión del servidor. Copiarlos desde `/opt/keycloak/lib/lib/main` del contenedor a una carpeta privada de compilación. El script no descarga dependencias ni recibe contraseñas:

```sh
python3 community/keycloak-mail/build.py \
  --keycloak-lib /ruta/privada/keycloak-libs \
  --output /ruta/despliegue/deck-library-mail.jar
```

Antes de crear el jar se ejecutan 16 comprobaciones: selección por realm y cliente, conservación de credenciales/TLS, direcciones de respuesta y ausencia de modificaciones a la configuración original. El jar excluye las clases de prueba.

## Instalar

Montar el jar en `/opt/keycloak/providers/deck-library-mail.jar:ro` y agregar a los argumentos existentes de inicio:

```text
--spi-email-sender--provider=deck-library
```

Opcionalmente se pueden reemplazar los valores por defecto:

```text
--spi-email-sender--deck-library--realm=master
--spi-email-sender--deck-library--client=deck-library
--spi-email-sender--deck-library--from=decklibrary@example.org
--spi-email-sender--deck-library--display-name=Deck Library
```

Conservar los otros argumentos y volúmenes del despliegue. Probar primero el arranque en un contenedor aislado de la misma imagen. Después recrear solo Keycloak y comprobar un correo de registro de Deck Library y otro de un cliente distinto. No modificar el remitente global del realm.

Este SPI de Keycloak es interno: mantener fijada la versión de la imagen probada (26.3.4) y recompilar/comprobar el proveedor antes de actualizar Keycloak. Para revertir, quitar la selección del proveedor y su montaje, y recrear el contenedor. El SMTP del realm permanece intacto.
