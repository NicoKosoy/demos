# Prototipos de Resolviendo Kos

Este repositorio publica los prototipos privados que el sistema de captación arma para cada negocio.
Se sirve con GitHub Pages en https://demos.resolviendokos.com (rama main, carpeta raíz).

## Reglas
- Cada prototipo va en su propia carpeta: `<slug-del-negocio>-<4 caracteres al azar>/index.html` (ej. `inmobiliaria-ronchi-x7k2`). Todo en un solo archivo HTML autocontenido (CSS y JS adentro; imágenes como data: o desde la web pública del negocio).
- Cada página lleva `<meta name="robots" content="noindex,nofollow">` y un aviso visible "Prototipo de demostración preparado para {negocio}" (ver "Firma del prototipo": va chico, como firma, no como advertencia).
- Cada página lleva, justo antes de `</body>`, el registro de visitas: `<script defer src="https://visitas.resolviendokos.com/v/t.js" data-negocio="{negocio}"></script>` (con el nombre real del negocio en `data-negocio`). Es la única excepción a "todo en un solo archivo". Si abrís un prototipo para revisarlo, agregá `?yo=1` a la URL para que tu visita no cuente.
- Nunca listar los prototipos en el index.html de la raíz. No tocar CNAME, robots.txt ni .nojekyll.
- URL final del prototipo: `https://demos.resolviendokos.com/<carpeta>/`.
- Commits chicos, uno por prototipo: `Prototipo: {negocio} ({rubro})`.

## Qué tiene que tener cada prototipo (obligatorio desde nov 2026)
El que decide la compra es el dueño. Tiene que verlo 20 segundos y pensar "esto lo hicieron para mí, hoy, y me resuelve laburo".

1. **Firma del prototipo, chica y arriba.** Una sola línea discreta (no una franja de color gritona): "Prototipo preparado para {negocio} · {día mes año}" y, si existe, su calificación real de Google ("4,8 ★ en Google · 312 reseñas"). Al pie: "Prototipo de demostración preparado para {negocio} por Resolviendo Kos · No es la web oficial". Si se cita una reseña, tiene que ser real, textual, corta y con su fecha; nunca inventada.
2. **"Precio de ejemplo" al lado de cada precio**, en letra chica. No alcanza con decirlo una vez arriba.
3. **El mensaje final a la vista.** Una burbuja con estilo de chat de WhatsApp que se va escribiendo en vivo mientras el cliente elige (fecha, personas o carga, total, seña, nombre) y muestra el texto exacto que le llegaría al dueño. El botón final abre WhatsApp con ese mismo texto.
4. **"Ver como dueño".** Un botón o pestaña que muestra el lado del dueño: consultas que entraron (con el formato de la burbuja), agenda o cupos de la semana, señas cobradas y lo que se ahorra frente al intermediario. Todo marcado "Panel de ejemplo". Más una sección corta "Para vos, {nombre del dueño o del negocio}" con 3 o 4 bullets concretos: menos mensajes repetidos, agenda con cupos, seña que entra antes de confirmar, sin comisión por reserva.
5. **Fotos reales** del negocio sacadas de su web, Facebook o Instagram (URL pública, hotlink), con `onerror` que las reemplace por una ilustración. Nunca fotos de stock. Si no hay fotos, diseño sin recuadros vacíos.
6. **Bullets, no párrafos.** Reglas, condiciones, qué incluye y cómo funciona van en listas o tablas cortas. Ningún párrafo de más de 2 líneas en esas secciones.
7. **Diferenciación.** Ninguna página repite la tipografía display, la estructura ni la paleta de otra. Nada de look genérico de IA (degradés violetas, emojis como íconos, grillas de 3 tarjetas iguales, "Bienvenidos a…").
