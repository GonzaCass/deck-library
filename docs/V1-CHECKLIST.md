# Condiciones para la versión 1.0

Estado al publicar la 1.0.0. «Hecho» significa comprobado y registrado en [VALIDATION.md](VALIDATION.md).

| Condición | Estado |
| --- | --- |
| Instalar un port del catálogo, verlo en la biblioteca y desinstalarlo sin perder archivos | Hecho: prueba con diez ports reales y con OpenRA (tres juegos); desinstalar mueve la carpeta a una papelera recuperable |
| Releases con varios juegos | Hecho para OpenRA. Otros proyectos con varios AppImage por juego se agregan con una línea en `port_recipes.py` |
| Instalación limpia y actualización desde una versión antigua conservando la biblioteca | Hecho: 0.10.1 → 0.20.0 y una instalación nueva, en un HOME temporal, con la app abierta después |
| Confianza en el catálogo | Hecho: etiqueta Revisado / Sin revisar y confirmación única para ports sin revisar |
| Pruebas automáticas, CI y revisión de datos personales en cada paquete | Hecho |
| Documentación completa en inglés y en español, sin mezclar idiomas | Hecho: README en dos secciones y prueba que lo comprueba |
| Interfaz en inglés | Hecho: catálogo de más de 1 500 textos, selector en **Ajustes → Carátulas y apariencia** y prueba que exige traducción para cada texto nuevo |
| Navegación con mando físico en modo Juego (palancas, gatillos, teclado en pantalla) | **Omitido por decisión para la 1.0:** solo se probó con mando virtual y en modo Escritorio; queda como primera tarea de la 1.1 |
| Jugar de punta a punta un port instalado desde el catálogo (audio, mando, FPS) | **Omitido por decisión para la 1.0:** las pruebas llegaron hasta que el juego arranca; queda para la 1.1 |

La 1.0 declara estas dos pruebas como no realizadas. Quien las haga en una Deck con modo Juego puede registrar el resultado en VALIDATION.md.
