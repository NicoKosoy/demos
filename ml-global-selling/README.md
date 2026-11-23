# Analizador ML Global Selling

Herramienta local para decidir **qué productos vender por Mercado Libre Global Selling** (México, Brasil, Chile, Colombia y Argentina) comprándoselos a proveedores que despachan por unidad.

- **Base de datos** de proveedores y productos (SQLite, queda en tu computadora).
- **Mensajes listos** (email en inglés o español, y WhatsApp) para preguntarle a cada proveedor la demora de despacho y sus condiciones. Registra lo que respondió y te avisa a quién hacerle seguimiento.
- **Margen por país**: comisión, cargo fijo, envío internacional, cobro y reserva para reclamos. También muestra cuánto paga el comprador con impuestos de importación, para compararlo con la competencia local.
- **Días de disponibilidad** a declarar en cada publicación, calculados con la demora real del proveedor.
- **Puntaje y veredicto** por producto y país: Publicar, Confirmar demora, Revisar, No conviene o Pierde plata. Se exporta a Excel.
- **Precios de la competencia**: por la API de Mercado Libre (con tu app) o cargados a mano desde el link del listado.

## Antes de empezar: lo que hay que saber

- **Global Selling exige una empresa en EE.UU. (o China/Hong Kong)**. Desde Argentina, lo habitual es una LLC con EIN y cuenta bancaria en EE.UU. o Payoneer. Los pagos llegan en USD.
- **Publicás en USD** y Mercado Libre convierte a la moneda de cada país.
- **"Comprarle directo al proveedor" funciona si él despacha unidades sueltas con la etiqueta de ML.** Si no lo hace, necesitás un prep center o 3PL (Miami/Texas) que reciba y reetiquete. La herramienta calcula las dos rutas.
- **Cada día de disponibilidad declarado te baja exposición.** Apuntá a proveedores que despachen en 1-2 días hábiles.
- **Brasil es el país más difícil**: el comprador paga ~45 % o más de impuestos de importación, así que te cuesta competir contra vendedores locales. México y Colombia suelen dar mejor.
- **Empezá por productos livianos, de valor alto por gramo y sin homologación**: cables, hubs, repuestos, impresión 3D, almacenamiento. Evitá cargadores, power banks e inalámbricos hasta tener experiencia.

## Instalación en Windows

1. Descargá esta carpeta. En GitHub, abrí la rama `claude/wizardly-mccarthy-02vt1p`, tocá **Code → Download ZIP**, descomprimí y entrá a `ml-global-selling`.
2. Instalá **Python 3.11 o más nuevo** desde https://www.python.org/downloads/ y tildá **"Add python.exe to PATH"**.
3. Doble clic en **`instalar.bat`**. Se hace una sola vez y tarda un par de minutos.
4. Doble clic en **`iniciar.bat`**. Se abre el navegador en http://localhost:8501.

Para ver cómo funciona sin cargar nada, tocá **"Cargar datos de ejemplo"** en Oportunidades. Los precios de ejemplo son inventados y se borran desde la barra lateral.

En Mac o Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run app.py`

## Flujo de trabajo

1. **Configuración → General**: cargá tu empresa y firma (salen en los mensajes), el margen objetivo y la ganancia mínima por venta.
2. **Configuración → Países**: tocá "Actualizar tipos de cambio" y reemplazá comisiones y costos de envío por los de tu Seller Center (ver tabla de abajo).
3. **Proveedores**: cargá cada uno con email o WhatsApp.
4. **Productos**: cargá costo, peso y medidas de la caja, o importá el catálogo del proveedor en CSV (hay planilla modelo).
5. **Proveedores → "Preguntarle la demora"**: elegí los productos, abrí el mensaje en tu email o WhatsApp, envialo y marcá "Ya lo envié".
6. Cuando responda, usá **"Anotar lo que respondió"** y cargá los días hábiles. Desde ese momento el análisis usa esa demora.
7. **Precios de mercado**: para cada producto y país, traé los precios por API o mirá el listado y cargá el más barato, el del medio y el más caro.
8. **Oportunidades**: ordenado por puntaje. En "Detalle" está la cuenta completa por país, con los días a declarar y la entrega estimada. Guardá los que vas a subir como borrador de publicación.

## Cómo hace las cuentas

- **Ganancia por venta** = precio − comisión − cargo fijo − envío internacional a tu cargo − cobro/retiro − reserva para reclamos − (costo + envío hasta el despacho + etiquetado).
- **Precio elegido**, en este orden:
  - el que fijaste vos;
  - si no fijaste ninguno y hay precios de competencia, el más alto con el que el comprador paga (con envío e impuestos) un 3 % menos que la mediana local;
  - si tampoco hay competencia cargada, el mínimo que deja tu margen objetivo.
- **Peso facturable** = el mayor entre el peso real y el volumétrico (largo × ancho × alto / 5000).
- **Días a declarar**:
  - si el proveedor despacha con etiqueta ML: su preparación + 1 día de colchón;
  - si pasa por tu 3PL: preparación + tránsito al 3PL + 1 día de proceso + colchón.
  - Si el total no supera los días que ML da por defecto, no hace falta declarar nada.
- **Puntaje** (0-100):

  | Factor | Puntos |
  |---|---|
  | Margen | 35 |
  | Precio frente a la competencia | 25 |
  | Ganancia en USD | 15 |
  | Valor por kilo | 10 |
  | Demora de entrega | 10 |
  | Riesgo regulatorio | 5 |

  Un producto de riesgo alto resta 20 puntos. Si la demora del proveedor no está confirmada, el veredicto queda en "Confirmar demora" aunque los números den.

## Valores a verificar antes de vender

La configuración trae **valores estimados para arrancar**. No son oficiales: Mercado Libre bloquea la lectura automática de sus tarifas y las fuentes públicas no coinciden. Todo se edita en Configuración.

| Dato | Valor que trae | Dónde verificarlo |
|---|---|---|
| Comisión por país y rubro | 16,5 % a 17,5 % | Seller Center → Tarifas (varía por categoría) |
| Cargo fijo en ventas baratas | USD 1 por debajo de USD 12 | Seller Center → Tarifas |
| Envío internacional a tu cargo | tabla por peso, USD 4,5 a 60 | Seller Center → costo de envío de cada publicación |
| Días que ML da para despachar sin declarar | 2 | Tus condiciones de envío |
| Impuestos del comprador | MX 0/17 %, BR ~45 %, CL 19 %, CO 0 % hasta USD 200, AR 21 % | SAT, Receita, SII, DIAN y ARCA (cambian seguido) |
| Costo de cobro/retiro | 1,5 % | Tu banco o Payoneer |

## Conectar la API de Mercado Libre (opcional, recomendado)

Desde 2025, la búsqueda de precios por API pide un token. Sin token, la herramienta igual sugiere la categoría de cada producto y te da el link del listado para cargar los precios a mano.

1. Entrá a https://developers.mercadolibre.com.ar/devcenter con tu usuario y creá una aplicación.
2. Como *Redirect URI* poné una dirección https, por ejemplo `https://www.google.com`.
3. En **Configuración → API de Mercado Libre**:
   - pegá el Client ID, el Client Secret y la Redirect URI;
   - tocá **Autorizar**, aceptá y copiá la dirección a la que te lleva (contiene `code=TG-...`);
   - pegala en la herramienta y tocá **Conectar**.
4. El token se renueva solo. Las credenciales quedan en `datos/`, que no se sube a GitHub.

Si tu aplicación no tiene permiso para búsquedas, la herramienta te lo avisa y podés seguir cargando los precios a mano.

## Tus datos

- Todo queda en la carpeta `datos/` (base, ajustes y token). Está excluida de git.
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
- `mlglobal/`: las cuentas. Margen en `margen.py`, demora en `demora.py`, puntaje en `puntaje.py`; además la base, los mensajes y la API de ML.
- `config/`: los valores de fábrica por país, los rubros con su riesgo y las ideas de productos.
- `tests/`: las pruebas de las cuentas y de cada sección de la app.
