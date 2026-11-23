# Analizador ML Global Selling

Herramienta local para decidir **qué productos comprar en EE.UU. (Amazon, eBay, Walmart o mayoristas) y vender por Mercado Libre Global Selling** en México, Brasil, Chile, Colombia y Argentina.

- **Buscar ofertas** de USD 50 a 500, solo nuevas:
  - eBay: los resultados aparecen en la herramienta y se agregan con un clic (API gratis);
  - Amazon y Walmart: links con el filtro ya puesto y carga manual.
- **Margen por país** con todo descontado:
  - sales tax de la compra, prep center y almacenaje en Texas;
  - comisión, cargo fijo y envío internacional;
  - publicidad, costo de cobro y reserva para reclamos.

  Muestra cuánto pagaría el comprador con impuestos de importación y lo compara con la competencia local.
- **Días de disponibilidad** a declarar en cada publicación y entrega estimada, según la logística que elijas.
- **Margen de hoy** para cada publicación: cuando entra un pedido, actualizás el precio de compra y ves si todavía conviene.
- **Puntaje y veredicto** por producto y país: Publicar, Confirmar demora, Revisar, No conviene, Pierde plata o No permitido. Se exporta a Excel.
- **Base de proveedores** con mensajes listos para pedir demoras y condiciones a mayoristas.

## Antes de empezar: lo que hay que saber

**Requisitos de Mercado Libre**
- **Global Selling exige una empresa en EE.UU. (o China/Hong Kong).** Desde Argentina, lo habitual es una LLC con EIN y cuenta en EE.UU. o Payoneer. Publicás y cobrás en USD.
- **Solo productos nuevos.** Las publicaciones de Global Selling tienen que ser "nuevo" y los países de destino restringen la importación de usados. Los reacondicionados no están claros: confirmalo con Mercado Libre.

**El depósito de Texas**
- Mercado Libre tiene un centro de fulfillment para vendedores de EE.UU. en la zona de **San Antonio** (algunas fuentes lo ubican en China Grove, al lado).
- **No hay una dirección pública para mandar paquetes.** Se trabaja con stock enviado antes de vender: se coordina con el equipo de Global Selling y la dirección y la cita salen del envío de inventario que armás en tu cuenta.
- **Amazon, eBay o Walmart no pueden mandar directo al depósito.** Cada unidad tiene que llegar con la etiqueta de Mercado Libre. Hace falta un **prep center** (o una dirección tuya en EE.UU.) que reciba, etiquete y despache.

**Las tres formas de trabajar** (cada producto tiene su "Logística")

| Logística | Cómo funciona | Ventaja | Contra |
|---|---|---|---|
| Compro por pedido → prep center → ML | Publicás sin stock. Cuando entra el pedido, comprás y el prep center reetiqueta y despacha | No inmovilizás plata: ideal para probar | Hay que declarar ~5 días de disponibilidad y el precio de compra puede cambiar |
| Stock en el depósito de ML en Texas | Comprás antes, el prep center manda en bloque a Texas | Entrega rápida (México 2-3 días) y mejor posición | Capital parado y almacenaje |
| El proveedor despacha con etiqueta ML | Mayorista que acepta tu etiqueta | El más barato | Pocos mayoristas lo hacen |

**Los números**

Con los costos estimados que trae la herramienta, **el comprador tiene que pagar unas 1,8 a 2 veces lo que te sale en Amazon para no perder, y unas 2,5 veces para ganar 18 %.** Colombia es la excepción: hasta USD 200 no paga impuestos de importación (a confirmar), así que el equilibrio queda en ~1,6 veces. Brasil queda casi siempre afuera por los impuestos.

Eso significa que comprar al precio normal de Amazon rara vez da. Lo que funciona:
- productos que en Latinoamérica son escasos o muy caros: repuestos de nicho, equipos de música, impresión 3D, foto;
- ofertas y liquidaciones por debajo del precio normal;
- **no pagar sales tax** (8 % menos de costo): prep center en Oregon, Delaware, Montana o New Hampshire, o compra con certificado de reventa (Amazon Business lo acepta);
- pautar solo lo que ya vende.

**Publicidad**
- Mercado Ads funciona por ACOS: el porcentaje de la venta que se va en anuncios. La herramienta lo descuenta en cada cuenta (5 % por defecto, se cambia en Configuración).
- Para pautar en Mercado Libre suelen pedir algo de historial: reputación, días desde el alta y ventas.

## Puesta en marcha (con la LLC ya creada)

**1. Cuenta de Global Selling** (lo hacés vos, con los datos de la LLC)
- Registrate en https://global-selling.mercadolibre.com como empresa. Vas a necesitar:
  - nombre legal de la LLC, EIN y dirección en EE.UU.;
  - documento del representante;
  - el formulario fiscal que pida: W-9 o W-8, según cómo esté armada la LLC (consultalo con quien la armó).
- Para cobrar: cuenta bancaria en USD a nombre de la LLC, o Payoneer. Mantené EIN, dirección y socios iguales en todos los formularios: los bancos y Payoneer lo controlan.
- Habilitá México, Colombia, Chile y Argentina. Argentina está abierta a vendedores internacionales desde diciembre de 2024. Brasil dejalo para más adelante por los impuestos.

**2. Prep center** (recibe lo que comprás, pone la etiqueta de ML y despacha)
- Pedile que:
  - reciba paquetes de Amazon, Sweetwater y otras tiendas;
  - etiquete por unidad con la etiqueta que le mandás;
  - despache el mismo día o al siguiente.
- Costo típico: USD 1,5 a 3 por unidad. Cargá el real en Configuración.
- Si está en Oregon, Delaware, Montana o New Hampshire, no pagás sales tax al comprar (~8 % menos de costo). En ese caso poné 0 en "Sales tax de compra".

**3. Valores reales en la herramienta**
- En el Seller Center vas a ver la comisión por categoría y el costo de envío de cada publicación. Copialos en Configuración → Países.

**4. App para publicar por API**
- En el Seller Center tocá **Developers** (al pie) → DevCenter → **Crear aplicación** ([guía](https://global-selling.mercadolibre.com/devsite/create-application)).
- Configurala así:
  - Redirect URI: una dirección https (ej. `https://www.google.com`);
  - **PKCE desactivado**;
  - permisos de lectura y de publicaciones/ventas.
- Copiá el App ID y la Secret Key en Configuración → Conexiones, elegí "Global Selling (para publicar)" y tocá Autorizar.

**5. Primera publicación de prueba**
- Validá precios de la tanda, elegí 1 producto que pase el mínimo y publicalo con `python cli.py publicar ... --confirmar`.
- Si sale bien, seguí con los demás.

## Instalación en Windows

1. Descargá esta carpeta. En GitHub, abrí la rama `claude/wizardly-mccarthy-02vt1p`, tocá **Code → Download ZIP**, descomprimí y entrá a `ml-global-selling`.
2. Instalá **Python 3.11 o más nuevo** desde https://www.python.org/downloads/ y tildá **"Add python.exe to PATH"**.
3. Doble clic en **`instalar.bat`**. Se hace una sola vez y tarda un par de minutos.
4. Doble clic en **`iniciar.bat`**. Se abre el navegador en http://localhost:8501.

Para verla funcionando sin cargar nada, tocá **"Cargar datos de ejemplo"** en Oportunidades. Los precios de ejemplo son inventados y se borran desde la barra lateral.

En Mac o Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run app.py`

## Flujo de trabajo

1. **Configuración → General**: margen objetivo, ganancia mínima, sales tax de compra, publicidad, costo del prep center y su código postal.
2. **Configuración → Países**: tocá "Actualizar tipos de cambio" y reemplazá comisiones y costos de envío por los de tu Seller Center.
3. **Configuración → Conexiones**: conectá eBay (para buscar ofertas) y Mercado Libre (para traer precios de la competencia).
4. **Buscar ofertas**: buscá por palabra clave entre USD 50 y 500, tildá las que te interesan y agregalas. Las de Amazon y Walmart se cargan con el formulario de abajo.
5. **Productos**: completá peso y medidas de la caja (el envío se cobra por peso real o volumétrico, el que sea mayor).
6. **Precios de mercado**: "Traer precios por API" para todos los productos de una vez, o carga manual desde el link del listado.
7. **Oportunidades**: ranking por puntaje, con filtro por costo de compra. La columna **"Mín. que tiene que pagar el comprador"** frente a **"Competencia"** te dice rápido si hay negocio. En "Detalle" está la cuenta completa por país.
8. Publicá lo que da y guardalo como borrador en Oportunidades → Publicaciones. **Cuando entre un pedido**, actualizá el costo del producto con el precio de ese momento y mirá "Margen hoy" antes de comprar.

## Candidatos, fichas y publicación

- **Tandas de candidatos**: en `candidatos/` hay archivos `.json` con productos ya relevados (costo en EE.UU., peso, caja, riesgos). Se cargan desde Productos → "Cargar una tanda de candidatos" o con `python cli.py cargar-candidatos candidatos/tanda-01.json`.
- **Validación rápida sin API**: en Oportunidades, la columna **"Para no perder, el comprador paga"** dice el precio local por debajo del cual ese producto pierde plata en cada país. Abrí el listado de ML de ese país: si los vendedores están bastante por encima, es candidato.
- **Fichas de publicación**: Productos → "Preparar fichas de publicación" arma un Excel con:
  - título en inglés y en español;
  - categoría de Global Selling y atributos obligatorios de esa categoría (sin token);
  - precio en USD y días de disponibilidad por país;
  - peso, caja y link de compra.

  Con eso se publica a mano desde el Seller Center.
- **Publicar por API** (cuando tengas la cuenta de Global Selling conectada):
  ```
  python cli.py publicar --producto 3 --paises MX,CO,CL --imagen https://foto1 --imagen https://foto2
  ```
  - Sin `--confirmar`, solo muestra lo que mandaría, para revisarlo.
  - Con `--confirmar`, lo publica y lo registra en Publicaciones.
  - Mercado Libre no tiene ambiente de prueba: arrancá con un producto y ajustá según el error que devuelva (suele pedir atributos extra o fotos).
  - Las fotos tienen que ser propias o del fabricante con permiso, no copiadas de Amazon.

## Cómo hace las cuentas

- **Ganancia por venta** = precio − comisión − cargo fijo − envío internacional a tu cargo − publicidad − cobro/retiro − reserva para reclamos − (costo × (1 + sales tax) + envío hasta el prep center + prep + almacenaje en Texas).
- **Precio elegido**, en este orden:
  - el que fijaste vos;
  - si no fijaste ninguno y hay precios de competencia, el más alto con el que el comprador paga (con envío e impuestos) un 3 % menos que la mediana local;
  - si tampoco hay competencia cargada, el mínimo que deja tu margen objetivo.
- **Peso facturable** = el mayor entre el peso real y el volumétrico (largo × ancho × alto / 5000).
- **Días a declarar**:
  - por pedido vía prep center: lo que tarda la tienda en despachar + tránsito hasta el prep center + 1 día de proceso + 1 de colchón. Amazon, eBay y Walmart traen demoras estimadas que podés editar en Proveedores;
  - stock en Texas: 0;
  - proveedor con etiqueta ML: su preparación + colchón.
- **Puntaje** (0-100):

  | Factor | Puntos |
  |---|---|
  | Margen | 35 |
  | Precio frente a la competencia | 25 |
  | Ganancia en USD | 15 |
  | Valor por kilo | 10 |
  | Demora de entrega | 10 |
  | Riesgo regulatorio | 5 |

  Un producto de riesgo alto resta 20 puntos. Un usado queda en "No permitido".

## Valores a verificar antes de vender

La configuración trae **valores estimados para arrancar**. No son oficiales: Mercado Libre bloquea la lectura automática de sus tarifas y las fuentes públicas no coinciden. Todo se edita en Configuración.

| Dato | Valor que trae | Dónde verificarlo |
|---|---|---|
| Comisión por país y rubro | 16,5 % a 17,5 % | Seller Center → Tarifas (varía por categoría) |
| Cargo fijo en ventas baratas | USD 1 por debajo de USD 12 | Seller Center → Tarifas |
| Envío internacional a tu cargo | tabla por peso, USD 4,5 a 60 | Seller Center → costo de envío de cada publicación |
| Almacenaje en Texas | USD 0,30 por unidad y mes | El equipo de Global Selling al habilitarte el depósito |
| Entrega desde Texas | México 2-4 días; resto estimado | Tu cuenta |
| Sales tax de compra | 8,25 % (Texas) | 0 % con prep center en estado sin sales tax o certificado de reventa |
| Prep center | USD 2,50 por unidad | El prep center que elijas |
| Impuestos del comprador | MX 0/17/19 %, BR ~45 %+, CL 19 %, CO 0 % hasta USD 200, AR 21 % | SAT, Receita, SII, DIAN y ARCA (cambian seguido) |
| Publicidad (ACOS) | 5 % | Tus campañas de Mercado Ads |

## Conexiones

**eBay (gratis):**
1. Registrate en https://developer.ebay.com con tu cuenta de eBay.
2. En *Application Keys*, creá un keyset de **Production**.
3. Pegá el App ID y el Cert ID en Configuración → Conexiones.

**Mercado Libre:** desde 2025, la búsqueda de precios por API pide un token.
1. Creá una aplicación en https://developers.mercadolibre.com.ar/devcenter. Como *Redirect URI* poné una dirección https, por ejemplo `https://www.google.com`.
2. En Configuración → Conexiones:
   - pegá el Client ID, el Client Secret y la Redirect URI;
   - tocá **Autorizar**, aceptá y pegá la dirección a la que te lleva (contiene `code=TG-...`);
   - tocá **Conectar**.
3. El token se renueva solo.

Sin token, la herramienta igual sugiere la categoría y te da el link del listado para cargar los precios a mano.

**Amazon y Walmart:** no tienen una API abierta para esto. Se usan los links con filtro y la carga manual. Si más adelante querés automatizar Amazon, la opción habitual es Keepa (pago).

## Tus datos

- Todo queda en la carpeta `datos/`: base, ajustes y credenciales. Está excluida de git.
- Para hacer backup o pasar todo a otra computadora, copiá esa carpeta.

## Comandos (sin interfaz)

```
python cli.py demo                       carga ejemplos
python cli.py analizar --excel out.xlsx  ranking en consola y Excel
python cli.py fx                         actualiza tipos de cambio
python cli.py escanear --producto 3      precios de la competencia por API
python -m pytest -q tests                pruebas
```

## Archivos

- `app.py`: la interfaz.
- `cli.py`: los comandos de consola.
- `mlglobal/`: las cuentas y conexiones. Margen en `margen.py`, demora en `demora.py`, puntaje en `puntaje.py`, eBay en `ebay.py`, Mercado Libre en `mercadolibre.py`; además la base y los mensajes.
- `config/`: los valores de fábrica por país, y los rubros con su riesgo e ideas de productos.
- `tests/`: las pruebas de las cuentas y de cada sección de la app.
