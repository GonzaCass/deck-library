# Condiciones para la versión 1.0

Estado al publicar la 0.20.0. «Hecho» significa comprobado y registrado en [VALIDATION.md](VALIDATION.md); «Pendiente» indica quién puede cerrarlo.

| Condición | Estado |
| --- | --- |
| Instalar un port del catálogo, verlo en la biblioteca y desinstalarlo sin perder archivos | Hecho: prueba con diez ports reales y con OpenRA (tres juegos); desinstalar mueve la carpeta a una papelera recuperable |
| Releases con varios juegos | Hecho para OpenRA. Otros proyectos con varios AppImage por juego se agregan con una línea en `port_recipes.py` |
| Instalación limpia y actualización desde una versión antigua conservando la biblioteca | Hecho: 0.10.1 → 0.20.0 y una instalación nueva, en un HOME temporal, con la app abierta después |
| Confianza en el catálogo | Hecho: etiqueta Revisado / Sin revisar y confirmación única para ports sin revisar |
| Pruebas automáticas, CI y revisión de datos personales en cada paquete | Hecho |
| Documentación completa en inglés y en español, sin mezclar idiomas | Hecho: README en dos secciones y prueba que lo comprueba |
| Navegación con mando físico en modo Juego (palancas, gatillos, teclado en pantalla) | **Pendiente, requiere la Deck en modo Juego:** solo se probó con mando virtual y en modo Escritorio |
| Jugar de punta a punta un port instalado desde el catálogo (audio, mando, FPS) | **Pendiente, requiere la Deck con GPU:** las pruebas llegaron hasta que el juego arranca |
| Interfaz en inglés | **Decisión pendiente:** la interfaz está solo en español; la 1.0 puede documentarlo como alcance o esperar a una traducción |

Cuando las dos pruebas con la Deck estén hechas, la 1.0 consiste en cambiar `__version__` a `1.0.0`, registrar el resultado en VALIDATION.md y publicar.
