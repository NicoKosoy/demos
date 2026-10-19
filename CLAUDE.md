# Prototipos de Resolviendo Kos

Este repositorio publica los prototipos privados que el sistema de captación arma para cada negocio.
Se sirve con GitHub Pages en https://demos.resolviendokos.com (rama main, carpeta raíz).

## Reglas
- Cada prototipo va en su propia carpeta: `<slug-del-negocio>-<4 caracteres al azar>/index.html` (ej. `inmobiliaria-ronchi-x7k2`). Todo en un solo archivo HTML autocontenido (CSS y JS adentro; imágenes como data: o desde la web pública del negocio).
- Cada página lleva `<meta name="robots" content="noindex,nofollow">` y un aviso visible "Prototipo de demostración preparado para {negocio}".
- Cada página lleva, justo antes de `</body>`, el registro de visitas: `<script defer src="https://visitas.resolviendokos.com/v/t.js" data-negocio="{negocio}"></script>` (con el nombre real del negocio en `data-negocio`). Es la única excepción a "todo en un solo archivo". Si abrís un prototipo para revisarlo, agregá `?yo=1` a la URL para que tu visita no cuente.
- Nunca listar los prototipos en el index.html de la raíz. No tocar CNAME, robots.txt ni .nojekyll.
- URL final del prototipo: `https://demos.resolviendokos.com/<carpeta>/`.
- Commits chicos, uno por prototipo: `Prototipo: {negocio} ({rubro})`.
