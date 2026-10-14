# Prototipos de Resolviendo Kos

Este repositorio publica los prototipos privados que el sistema de captación arma para cada negocio.
Se sirve con GitHub Pages en https://demos.resolviendokos.com (rama main, carpeta raíz).

## Reglas
- Cada prototipo va en su propia carpeta: `<slug-del-negocio>-<4 caracteres al azar>/index.html` (ej. `inmobiliaria-ronchi-x7k2`). Todo en un solo archivo HTML autocontenido (CSS y JS adentro; imágenes como data: o desde la web pública del negocio).
- Cada página lleva `<meta name="robots" content="noindex,nofollow">` y un aviso visible "Prototipo de demostración preparado para {negocio}".
- Nunca listar los prototipos en el index.html de la raíz. No tocar CNAME, robots.txt ni .nojekyll.
- URL final del prototipo: `https://demos.resolviendokos.com/<carpeta>/`.
- Commits chicos, uno por prototipo: `Prototipo: {negocio} ({rubro})`.
