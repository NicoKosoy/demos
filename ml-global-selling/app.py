"""Interfaz web local. Se abre con iniciar.bat (Windows) o:  streamlit run app.py"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mlglobal import analisis, candidatos, config, db, demo, ebay, fx  # noqa: E402
from mlglobal import mercadolibre as ml  # noqa: E402
from mlglobal import plantillas, publicar  # noqa: E402

st.set_page_config(page_title="Analizador ML Global", layout="wide")


@st.cache_resource
def conexion():
    c = db.conectar()
    db.asegurar_fuentes(c)
    return c


con = conexion()
PAISES = config.paises()
GENERAL = config.general()
RUBROS = config.rubros()
NOMBRE_RUBRO = {r["id"]: r["nombre"] for r in RUBROS}
VEREDICTOS = ["Publicar", "Confirmar demora", "Revisar", "No conviene", "Pierde plata", "No permitido"]
RUTAS = {"3pl": "Compro por pedido → prep center → ML", "full": "Stock en el depósito de ML en Texas",
         "directo": "El proveedor despacha con etiqueta ML"}
FUENTES_COMPRA = {"amazon": "Amazon", "ebay": "eBay", "walmart": "Walmart", "proveedor": "Proveedor mayorista",
                  "otro": "Otra tienda"}
CONDICIONES = ["nuevo", "reacondicionado", "usado"]


def nombre_pais(c: str) -> str:
    return PAISES[c]["nombre"] if c in PAISES else c


def n(valor, defecto=0.0) -> float:
    try:
        return defecto if valor in (None, "") or pd.isna(valor) else float(valor)
    except (TypeError, ValueError):
        return defecto


def a_excel(hojas: dict[str, pd.DataFrame]) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for nombre, d in hojas.items():
            d.to_excel(w, sheet_name=nombre[:31], index=False)
    return buf.getvalue()


COLUMNAS_OPORTUNIDADES = {
    "producto": st.column_config.TextColumn("Producto", width="large"),
    "pais_nombre": "País",
    "fuente_compra": st.column_config.TextColumn("Compra en"),
    "costo_compra_usd": st.column_config.NumberColumn("Costo USD", format="$ %.2f"),
    "veredicto": "Veredicto",
    "puntaje": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%d"),
    "precio_usd": st.column_config.NumberColumn("Precio USD", format="$ %.2f"),
    "origen_precio": "Precio elegido",
    "precio_minimo_usd": st.column_config.NumberColumn("Mínimo USD", format="$ %.2f",
                                                       help="Precio más bajo que deja tu margen objetivo"),
    "ganancia_usd": st.column_config.NumberColumn("Ganancia USD", format="$ %.2f"),
    "margen_pct": st.column_config.NumberColumn("Margen", format="%.1f %%"),
    "precio_final_comprador_local": st.column_config.NumberColumn("Paga el comprador (local)", format="%.0f",
                                                                  help="Con envío e impuestos de importación"),
    "equilibrio_final_comprador_local": st.column_config.NumberColumn(
        "Para no perder, el comprador paga", format="%.0f",
        help="Si en ML se vende por debajo de esto (moneda local), perdés plata"),
    "minimo_final_comprador_local": st.column_config.NumberColumn(
        "Mín. que tiene que pagar el comprador", format="%.0f",
        help="Lo que pagaría el comprador (con impuestos) a tu precio mínimo. Comparalo con la competencia."),
    "mediana_competencia_local": st.column_config.NumberColumn("Competencia (mediana local)", format="%.0f"),
    "dif_vs_competencia_pct": st.column_config.NumberColumn("vs competencia", format="%+.0f %%"),
    "dias_a_declarar": st.column_config.NumberColumn("Días a declarar", format="%d",
                                                     help="Disponibilidad de stock a poner en la publicación"),
    "entrega_estimada": "Entrega al comprador",
    "riesgo": "Riesgo",
    "proveedor": "Proveedor",
    "alertas": st.column_config.TextColumn("Alertas", width="large"),
}


# ---------------------------------------------------------------- barra lateral
st.sidebar.title("Analizador ML Global")
pagina = st.sidebar.radio("Sección", ["Oportunidades", "Buscar ofertas", "Calculadora rápida", "Productos",
                                      "Proveedores", "Precios de mercado", "Configuración"])
estado_ml = ml.estado_token()
st.sidebar.caption("API de Mercado Libre: " + ("conectada" if estado_ml["conectado"] else "sin conectar"))
pendientes = db.seguimientos_pendientes(con)
if pendientes:
    st.sidebar.warning(f"{len(pendientes)} proveedor(es) esperando seguimiento")
if demo.hay_ejemplos(con):
    st.sidebar.info("Hay datos de EJEMPLO cargados (precios inventados).")
    if st.sidebar.button("Borrar datos de ejemplo"):
        demo.borrar_ejemplos(con)
        st.rerun()
st.sidebar.caption(f"Tus datos: {db.RUTA_DB}")


# ---------------------------------------------------------------- oportunidades
def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, int):
        return str(v)
    return "0.00" if abs(v) < 0.005 else f"{v:,.2f}"


def tabla_detalle(filas: list[dict]) -> pd.DataFrame:
    conceptos = [
        ("Precio de venta (USD)", lambda f: f["precio_usd"]),
        ("Cómo se eligió el precio", lambda f: f["origen_precio"]),
        ("Comisión ML (USD)", lambda f: -f["_detalle"]["resultado"]["comision_usd"]),
        ("Cargo fijo (USD)", lambda f: -f["_detalle"]["resultado"]["cargo_fijo_usd"]),
        ("Envío internacional a tu cargo (USD)", lambda f: -f["envio_vendedor_usd"]),
        ("Cobro / retiro (USD)", lambda f: -f["_detalle"]["resultado"]["payout_usd"]),
        ("Reserva reclamos (USD)", lambda f: -f["_detalle"]["resultado"]["reserva_usd"]),
        ("Publicidad (USD)", lambda f: -f["publicidad_usd"]),
        ("Producto con sales tax + envío + prep (USD)", lambda f: -f["costo_producto_usd"]),
        ("GANANCIA (USD)", lambda f: f["ganancia_usd"]),
        ("Margen sobre precio", lambda f: f"{f['margen_pct']:.1f} %"),
        ("ROI sobre costo", lambda f: f"{f['_detalle']['resultado']['roi_pct']:.0f} %"),
        ("Precio mínimo para tu margen (USD)", lambda f: f["precio_minimo_usd"]),
        ("…el comprador pagaría (moneda local)", lambda f: (f"{f['minimo_final_comprador_local']:,.0f} {f['moneda']}"
                                                           if f["minimo_final_comprador_local"] else "—")),
        ("Impuestos que paga el comprador (USD)", lambda f: f["_detalle"]["resultado"]["impuesto_comprador_usd"]),
        ("Paga el comprador (moneda local)", lambda f: f"{f['precio_final_comprador_local']:,.0f} {f['moneda']}"),
        ("Competencia, mediana (moneda local)", lambda f: (f"{f['mediana_competencia_local']:,.0f} {f['moneda']}"
                                                          if f["mediana_competencia_local"] else "sin dato")),
        ("Días de disponibilidad a declarar", lambda f: f["dias_a_declarar"]),
        ("Entrega estimada al comprador", lambda f: f["entrega_estimada"]),
        ("Puntaje", lambda f: f"{f['puntaje']:.0f} ({f['veredicto']})"),
    ]
    datos = {f["pais_nombre"]: [fmt(fn(f)) for _, fn in conceptos] for f in filas}
    return pd.DataFrame(datos, index=[c for c, _ in conceptos])


def pagina_oportunidades():
    st.title("Oportunidades por país")
    filas = analisis.analizar_todo(con)
    if not filas:
        st.info("Todavía no hay productos. Cargalos en **Productos** o mirá un ejemplo armado.")
        if st.button("Cargar datos de ejemplo"):
            demo.cargar_ejemplos(con)
            st.rerun()
        return
    df = pd.DataFrame(filas)
    df["fuente_compra"] = df["fuente_compra"].map(lambda f: FUENTES_COMPRA.get(f, f or ""))
    c1, c2, c3, c4 = st.columns(4)
    paises_sel = c1.multiselect("Países", list(PAISES), default=GENERAL["paises_activos"], format_func=nombre_pais)
    ver_sel = c2.multiselect("Veredicto", VEREDICTOS, placeholder="Todos")
    rub_sel = c3.multiselect("Rubro", sorted(df["rubro"].unique()), placeholder="Todos")
    min_pts = c4.slider("Puntaje mínimo", 0, 100, 0)
    tope = float(max(500.0, df["costo_compra_usd"].max()))
    cmin, cmax = st.slider("Costo de compra (USD)", 0.0, tope, (0.0, tope), step=5.0)
    vista = df[df["pais"].isin(paises_sel) & (df["puntaje"] >= min_pts)
               & df["costo_compra_usd"].between(cmin, cmax)]
    if ver_sel:
        vista = vista[vista["veredicto"].isin(ver_sel)]
    if rub_sel:
        vista = vista[vista["rubro"].isin(rub_sel)]
    vista = vista.sort_values(["puntaje", "ganancia_usd"], ascending=False)

    buenas = vista[vista["veredicto"] == "Publicar"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Producto × país", len(vista))
    m2.metric("Para publicar", len(buenas))
    m3.metric("Margen promedio (las que dan)", f"{buenas['margen_pct'].mean():.1f} %" if len(buenas) else "—")
    m4.metric("Ganancia por venta (las que dan)", f"USD {buenas['ganancia_usd'].mean():.2f}" if len(buenas) else "—")

    st.dataframe(vista[list(COLUMNAS_OPORTUNIDADES)], hide_index=True, column_config=COLUMNAS_OPORTUNIDADES)
    exportable = vista.drop(columns=["_detalle"])
    st.download_button("Descargar en Excel", a_excel({
        "Oportunidades": exportable,
        "Productos": pd.DataFrame(db.todos(con, "productos")),
        "Proveedores": pd.DataFrame(db.todos(con, "proveedores")),
    }), file_name="oportunidades_ml_global.xlsx")
    st.caption("Las cuentas usan los valores de Configuración. Los que vienen de fábrica son ESTIMADOS: "
               "reemplazalos por los de tu Seller Center antes de decidir.")

    st.subheader("Detalle de un producto")
    productos = {f["producto_id"]: f["producto"] for f in filas}
    pid = st.selectbox("Producto", list(productos), format_func=lambda i: productos[i])
    filas_prod = [f for f in filas if f["producto_id"] == pid and f["pais"] in paises_sel]
    if filas_prod:
        st.dataframe(tabla_detalle(filas_prod))
        for f in filas_prod:
            if f["alertas"]:
                st.caption(f"**{f['pais_nombre']}:** {f['alertas']}")
        with st.form("guardar_pub"):
            st.write("Guardar como publicación en borrador (para llevar control de lo que subís)")
            pais = st.selectbox("País", [f["pais"] for f in filas_prod], format_func=nombre_pais)
            if st.form_submit_button("Guardar borrador"):
                f = next(x for x in filas_prod if x["pais"] == pais)
                db.insertar(con, "publicaciones", {"producto_id": pid, "pais": pais, "precio_usd": f["precio_usd"],
                                                   "dias_disponibilidad": f["dias_a_declarar"],
                                                   "margen_pct": f["margen_pct"]})
                st.success("Guardado.")
    pubs = db.filas(con, "SELECT pu.id, pr.titulo AS producto, pu.pais, pu.precio_usd, pu.dias_disponibilidad, "
                         "pu.margen_pct, pu.estado, pu.item_id_ml, pu.fecha FROM publicaciones pu "
                         "JOIN productos pr ON pr.id = pu.producto_id ORDER BY pu.fecha DESC")
    if pubs:
        st.subheader("Publicaciones")
        st.caption("Cuando entra un pedido, actualizá el costo del producto (precio de hoy en Amazon/eBay) y mirá "
                   "'Margen hoy' antes de comprarlo.")
        ids_prod = {r["id"]: r["producto_id"] for r in db.filas(con, "SELECT id, producto_id FROM publicaciones")}
        for pub in pubs:
            hoy = analisis.margen_a_precio(con, ids_prod[pub["id"]], pub["pais"], n(pub["precio_usd"]))
            pub["margen_hoy_pct"] = hoy["margen_pct"] if hoy else None
            pub["ganancia_hoy_usd"] = hoy["ganancia_usd"] if hoy else None
        editadas = st.data_editor(pd.DataFrame(pubs), hide_index=True,
                                  disabled=["id", "producto", "fecha", "margen_hoy_pct", "ganancia_hoy_usd"],
                                  column_config={"estado": st.column_config.SelectboxColumn(
                                      "estado", options=["borrador", "publicado", "pausado", "cerrado"])},
                                  key="ed_pubs")
        if st.button("Guardar cambios de publicaciones"):
            for _, r in editadas.iterrows():
                db.actualizar(con, "publicaciones", int(r["id"]), {
                    "pais": r["pais"], "precio_usd": n(r["precio_usd"]), "estado": r["estado"],
                    "dias_disponibilidad": int(n(r["dias_disponibilidad"])), "item_id_ml": r["item_id_ml"]})
            st.success("Listo.")


# ---------------------------------------------------------------- buscar ofertas
def pagina_buscar():
    st.title("Buscar ofertas en EE.UU.")
    st.caption("Productos NUEVOS en Amazon, eBay y Walmart. Global Selling no acepta usados. Después de agregarlos, "
               "traé los precios de la competencia en 'Precios de mercado' y mirá el ranking en 'Oportunidades'.")
    c1, c2, c3 = st.columns([3, 1, 1])
    texto = c1.text_input("Qué buscar", placeholder="ej.: pedal overdrive, ssd nvme 2tb, hotend")
    pmin = c2.number_input("Desde USD", 0.0, value=float(GENERAL["costo_min_busqueda_usd"]), step=10.0)
    pmax = c3.number_input("Hasta USD", 0.0, value=float(GENERAL["costo_max_busqueda_usd"]), step=10.0)
    with st.expander("Ideas por rubro"):
        st.dataframe(pd.DataFrame([{"Rubro": r["nombre"], "Riesgo": r["riesgo"], "Ideas": r.get("ideas", ""),
                                    "Ojo": r.get("nota", "")} for r in RUBROS]), hide_index=True)
    if texto:
        cols = st.columns(3)
        for col, (tienda, url) in zip(cols, ebay.links_busqueda(texto, pmin, pmax).items()):
            col.link_button(f"Ver en {tienda} (nuevos, USD {pmin:g}-{pmax:g})", url)

    st.subheader("eBay: resultados acá mismo")
    if not ebay.configurado():
        st.info("Conectá eBay en Configuración → Conexiones (es gratis) para traer los resultados acá y "
                "agregarlos con un clic. Mientras, usá los links de arriba y el formulario de abajo.")
    else:
        c1, c2 = st.columns(2)
        orden = c1.selectbox("Orden", ["", "price"],
                             format_func={"": "Más relevantes", "price": "Más baratos primero"}.get)
        limite = c2.slider("Cantidad", 10, 200, 50, step=10)
        if st.button("Buscar en eBay", disabled=not texto):
            try:
                st.session_state["ebay_res"] = ebay.buscar(texto, pmin, pmax, True, limite, orden or None,
                                                           GENERAL.get("zip_prep_center", ""))
                st.session_state["ebay_texto"] = texto
            except ebay.ErrorEbay as e:
                st.error(str(e))
        res = st.session_state.get("ebay_res")
        if res:
            df = pd.DataFrame(res)
            df.insert(0, "agregar", False)
            editado = st.data_editor(
                df[["agregar", "imagen", "titulo", "precio_usd", "envio_usd", "feedback_pct", "feedback_cantidad",
                    "vendedor", "url"]],
                hide_index=True, key="ed_ebay",
                disabled=["imagen", "titulo", "precio_usd", "envio_usd", "feedback_pct", "feedback_cantidad",
                          "vendedor", "url"],
                column_config={"agregar": st.column_config.CheckboxColumn("Agregar"),
                               "imagen": st.column_config.ImageColumn("Foto"),
                               "titulo": st.column_config.TextColumn("Título", width="large"),
                               "precio_usd": st.column_config.NumberColumn("Precio", format="$ %.2f"),
                               "envio_usd": st.column_config.NumberColumn("Envío", format="$ %.2f"),
                               "feedback_pct": st.column_config.NumberColumn("Feedback", format="%.1f %%"),
                               "feedback_cantidad": "Opiniones", "vendedor": "Vendedor",
                               "url": st.column_config.LinkColumn("Link", display_text="abrir")})
            c1, c2, c3 = st.columns(3)
            rubro = c1.selectbox("Rubro de los elegidos", list(NOMBRE_RUBRO), format_func=NOMBRE_RUBRO.get)
            ruta = c2.selectbox("Logística", list(RUTAS), format_func=RUTAS.get, key="ruta_ebay")
            peso = c3.number_input("Peso estimado por unidad (kg)", 0.0, value=0.5, step=0.1)
            if st.button("Agregar los elegidos a Productos"):
                prov = db.proveedor_por_nombre(con, "eBay") or {}
                elegidos = editado[editado["agregar"]]
                for _, r in elegidos.iterrows():
                    db.insertar(con, "productos", {
                        "titulo": str(r["titulo"])[:200], "rubro": rubro, "fuente_compra": "ebay",
                        "proveedor_id": prov.get("id"), "costo_usd": float(r["precio_usd"]),
                        "envio_local_usd": n(r["envio_usd"]), "peso_kg": peso, "ruta": ruta, "condicion": "nuevo",
                        "prep_usd": GENERAL["prep_por_unidad_usd"] if ruta != "directo" else 0,
                        "url_proveedor": r["url"], "busqueda": st.session_state.get("ebay_texto", texto)})
                st.success(f"{len(elegidos)} producto(s) agregados. Revisá peso y medidas en Productos.")

    st.subheader("Agregar una oferta a mano")
    with st.form("oferta_manual", clear_on_submit=True):
        titulo = st.text_input("Título *")
        c1, c2, c3, c4 = st.columns(4)
        fuente = c1.selectbox("Tienda", ["amazon", "walmart", "ebay", "otro"], format_func=FUENTES_COMPRA.get)
        precio = c2.number_input("Precio (USD) *", 0.0, step=1.0)
        envio = c3.number_input("Envío hasta tu prep center (USD)", 0.0, step=1.0)
        peso = c4.number_input("Peso (kg)", 0.0, value=0.5, step=0.1)
        c1, c2, c3 = st.columns(3)
        url = c1.text_input("Link")
        rubro = c2.selectbox("Rubro", list(NOMBRE_RUBRO), format_func=NOMBRE_RUBRO.get)
        ruta = c3.selectbox("Logística", list(RUTAS), format_func=RUTAS.get)
        busqueda = st.text_input("Cómo buscarlo en Mercado Libre", value=texto or "")
        if st.form_submit_button("Agregar"):
            if not titulo or not precio:
                st.error("Faltan el título o el precio.")
            else:
                prov = db.proveedor_por_nombre(con, FUENTES_COMPRA[fuente]) or {}
                db.insertar(con, "productos", {
                    "titulo": titulo, "fuente_compra": fuente, "proveedor_id": prov.get("id"), "costo_usd": precio,
                    "envio_local_usd": envio, "peso_kg": peso, "url_proveedor": url, "rubro": rubro, "ruta": ruta,
                    "condicion": "nuevo", "busqueda": busqueda or titulo,
                    "prep_usd": GENERAL["prep_por_unidad_usd"] if ruta != "directo" else 0})
                st.success("Agregado.")


# ---------------------------------------------------------------- calculadora
def pagina_calculadora():
    st.title("Calculadora rápida")
    st.caption("Para probar un producto antes de cargarlo. Nada se guarda hasta que lo pidas.")
    c1, c2, c3, c4 = st.columns(4)
    costo = c1.number_input("Costo del proveedor (USD)", 0.0, value=10.0, step=0.5)
    envio_local = c2.number_input("Envío proveedor → despacho (USD)", 0.0, value=0.0, step=0.5)
    prep = c3.number_input("Etiquetado / 3PL por unidad (USD)", 0.0, value=0.0, step=0.5)
    peso = c4.number_input("Peso real (kg)", 0.0, value=0.2, step=0.05, format="%.3f")
    c1, c2, c3, c4 = st.columns(4)
    largo = c1.number_input("Largo caja (cm)", 0.0, value=0.0)
    ancho = c2.number_input("Ancho caja (cm)", 0.0, value=0.0)
    alto = c3.number_input("Alto caja (cm)", 0.0, value=0.0)
    rubro = c4.selectbox("Rubro", list(NOMBRE_RUBRO), format_func=NOMBRE_RUBRO.get)
    c1, c2, c3, c4 = st.columns(4)
    ruta = c1.selectbox("Logística", list(RUTAS), format_func=RUTAS.get)
    dias = c2.number_input("Días hasta que el proveedor despacha (0 = no sé)", 0.0, value=0.0, step=1.0)
    tax = c3.number_input("Sales tax de la compra (%)", 0.0, 15.0, float(GENERAL["sales_tax_compra_pct"]))
    precio = c4.number_input("Precio de venta USD (0 = calcularlo)", 0.0, value=0.0, step=1.0)
    st.write("Precio de la competencia en cada país (mediana, moneda local; 0 = no sé)")
    cols = st.columns(len(GENERAL["paises_activos"]))
    mercado = {}
    for col, codigo in zip(cols, GENERAL["paises_activos"]):
        v = col.number_input(f"{nombre_pais(codigo)} ({PAISES[codigo]['moneda']})", 0.0, value=0.0, key=f"m_{codigo}")
        if v:
            mercado[codigo] = {"precio_mediana_local": v, "fuente": "manual"}
    prod = {"id": 0, "titulo": "Prueba", "rubro": rubro, "costo_usd": costo, "envio_local_usd": envio_local,
            "prep_usd": prep, "peso_kg": peso, "largo_cm": largo, "ancho_cm": ancho, "alto_cm": alto, "ruta": ruta,
            "precio_venta_usd": precio or None, "sales_tax_pct": tax}
    prov = {"dias_preparacion": dias or None, "dias_transito_local": GENERAL["dias_transito_local_por_defecto"]}
    filas = analisis.analizar_producto(prod, prov, mercado, PAISES, GENERAL, RUBROS)
    st.dataframe(tabla_detalle(filas))
    for f in filas:
        if f["alertas"]:
            st.caption(f"**{f['pais_nombre']}:** {f['alertas']}")


# ---------------------------------------------------------------- productos
CAMPOS_NUM = ["costo_usd", "envio_local_usd", "prep_usd", "peso_kg", "largo_cm", "ancho_cm", "alto_cm",
              "precio_venta_usd"]


def form_producto(clave: str, datos: dict | None = None) -> dict | None:
    d = datos or {}
    provs = {p["id"]: p["nombre"] for p in db.todos(con, "proveedores", "nombre")}
    with st.form(clave, clear_on_submit=datos is None):
        titulo = st.text_input("Título *", d.get("titulo", ""))
        c1, c2 = st.columns([3, 1])
        titulo_en = c1.text_input("Título en inglés (Global Selling lo pide)", d.get("titulo_en") or "")
        modelo = c2.text_input("Modelo", d.get("modelo") or "")
        c1, c2, c3 = st.columns(3)
        ids_prov = [None] + list(provs)
        proveedor_id = c1.selectbox("Proveedor", ids_prov, index=ids_prov.index(d.get("proveedor_id"))
                                    if d.get("proveedor_id") in ids_prov else 0,
                                    format_func=lambda i: "— sin asignar —" if i is None else provs[i])
        ids_rub = list(NOMBRE_RUBRO)
        rubro = c2.selectbox("Rubro", ids_rub, index=ids_rub.index(d["rubro"]) if d.get("rubro") in ids_rub else 0,
                             format_func=NOMBRE_RUBRO.get)
        riesgos = ["", "bajo", "medio", "alto"]
        riesgo = c3.selectbox("Riesgo regulatorio", riesgos, index=riesgos.index(d.get("riesgo") or ""),
                              format_func=lambda r: r or "el del rubro")
        c1, c2, c3 = st.columns(3)
        fuentes = list(FUENTES_COMPRA)
        fuente = c1.selectbox("Dónde se compra", fuentes, format_func=FUENTES_COMPRA.get,
                              index=fuentes.index(d["fuente_compra"]) if d.get("fuente_compra") in fuentes else 0)
        condicion = c2.selectbox("Condición", CONDICIONES, index=CONDICIONES.index(d.get("condicion") or "nuevo"),
                                 help="Global Selling solo acepta productos nuevos")
        tax_actual = d.get("sales_tax_pct")
        tax = c3.number_input("Sales tax de compra (%) — vacío = el general", 0.0, 15.0,
                              value=None if tax_actual in (None, "") else float(tax_actual))
        c1, c2, c3 = st.columns(3)
        sku = c1.text_input("SKU / ASIN / item de eBay", d.get("sku") or "")
        marca = c2.text_input("Marca", d.get("marca") or "")
        upc = c3.text_input("UPC / EAN", d.get("upc") or "")
        c1, c2, c3, c4 = st.columns(4)
        costo = c1.number_input("Costo (USD) *", 0.0, value=n(d.get("costo_usd")), step=0.5)
        envio_local = c2.number_input("Envío a despacho (USD)", 0.0, value=n(d.get("envio_local_usd")), step=0.5)
        prep = c3.number_input("Prep / 3PL (USD)", 0.0, value=n(d.get("prep_usd")), step=0.5)
        precio = c4.number_input("Precio fijo USD (0 = automático)", 0.0, value=n(d.get("precio_venta_usd")))
        c1, c2, c3, c4 = st.columns(4)
        peso = c1.number_input("Peso (kg)", 0.0, value=n(d.get("peso_kg")), step=0.05, format="%.3f")
        largo = c2.number_input("Largo (cm)", 0.0, value=n(d.get("largo_cm")))
        ancho = c3.number_input("Ancho (cm)", 0.0, value=n(d.get("ancho_cm")))
        alto = c4.number_input("Alto (cm)", 0.0, value=n(d.get("alto_cm")))
        c1, c2 = st.columns(2)
        rutas = list(RUTAS)
        ruta = c1.selectbox("Logística", rutas, index=rutas.index(d["ruta"]) if d.get("ruta") in rutas else 0,
                            format_func=RUTAS.get)
        busqueda = c2.text_input("Palabras para buscarlo en ML", d.get("busqueda") or "")
        url = st.text_input("Link del producto en el proveedor", d.get("url_proveedor") or "")
        notas = st.text_area("Notas", d.get("notas") or "")
        activo = st.checkbox("Activo (entra en el análisis)", value=bool(d.get("activo", 1)))
        if st.form_submit_button("Guardar"):
            if not titulo.strip():
                st.error("Falta el título.")
                return None
            return {"titulo": titulo.strip(), "proveedor_id": proveedor_id, "rubro": rubro, "riesgo": riesgo or None,
                    "sku": sku, "marca": marca, "upc": upc, "costo_usd": costo, "envio_local_usd": envio_local,
                    "prep_usd": prep, "precio_venta_usd": precio or None, "peso_kg": peso, "largo_cm": largo or None,
                    "ancho_cm": ancho or None, "alto_cm": alto or None, "ruta": ruta, "busqueda": busqueda,
                    "url_proveedor": url, "notas": notas, "activo": int(activo), "fuente_compra": fuente,
                    "condicion": condicion, "sales_tax_pct": tax, "titulo_en": titulo_en, "modelo": modelo}
    return None


def pagina_productos():
    st.title("Productos")
    prods = db.filas(con, "SELECT p.id, p.titulo, p.rubro, v.nombre AS proveedor, p.costo_usd, p.peso_kg, p.ruta, "
                          "p.precio_venta_usd, p.activo FROM productos p LEFT JOIN proveedores v "
                          "ON v.id = p.proveedor_id ORDER BY p.id")
    if prods:
        df = pd.DataFrame(prods)
        df["rubro"] = df["rubro"].map(lambda r: NOMBRE_RUBRO.get(r, r))
        st.dataframe(df, hide_index=True)
    with st.expander("Agregar producto", expanded=not prods):
        nuevo = form_producto("nuevo_producto")
        if nuevo:
            db.insertar(con, "productos", nuevo)
            st.success("Producto agregado.")
            st.rerun()
    if prods:
        with st.expander("Editar o borrar un producto"):
            pid = st.selectbox("Producto", [p["id"] for p in prods],
                               format_func=lambda i: next(p["titulo"] for p in prods if p["id"] == i))
            cambios = form_producto(f"editar_producto_{pid}", db.uno(con, "productos", pid))
            if cambios:
                db.actualizar(con, "productos", pid, cambios)
                st.success("Guardado.")
                st.rerun()
            if st.button("Borrar este producto", key=f"borrar_{pid}"):
                db.borrar(con, "productos", pid)
                st.rerun()
    if prods:
        if st.button("Preparar fichas de publicación (Excel)"):
            with st.spinner("Buscando categoría de Global Selling y atributos obligatorios…"):
                filas = analisis.analizar_todo(con)
                fichas = [publicar.armar_ficha(x, filas) for x in db.todos(con, "productos")
                          if x.get("activo", 1) and (x.get("condicion") or "nuevo") != "usado"]
                st.session_state["fichas_xlsx"] = a_excel({
                    "Fichas": pd.DataFrame(fichas),
                    "Precios por país": pd.DataFrame([{k: v for k, v in f.items() if k != "_detalle"}
                                                      for f in filas])})
        if st.session_state.get("fichas_xlsx"):
            st.download_button("Descargar fichas", st.session_state["fichas_xlsx"],
                               file_name="fichas_publicacion.xlsx")
    with st.expander("Cargar una tanda de candidatos (archivo .json de la carpeta candidatos/)"):
        carpeta = Path(__file__).resolve().parent / "candidatos"
        archivos = sorted(carpeta.glob("*.json")) if carpeta.exists() else []
        if archivos:
            elegido = st.selectbox("Tanda", archivos, format_func=lambda a: a.name)
            if st.button("Cargar tanda"):
                nuevos, act = candidatos.cargar(con, elegido)
                st.success(f"{nuevos} nuevos, {act} actualizados.")
                st.rerun()
        else:
            st.caption("No hay tandas en la carpeta candidatos/.")
    with st.expander("Importar productos desde un CSV (catálogo del proveedor)"):
        plantilla = pd.DataFrame(columns=["titulo", "rubro", "fuente_compra", "sku", "marca", "upc", "costo_usd",
                                          "envio_local_usd",
                                          "prep_usd", "peso_kg", "largo_cm", "ancho_cm", "alto_cm", "ruta",
                                          "busqueda", "url_proveedor"])
        st.download_button("Descargar planilla modelo", plantilla.to_csv(index=False).encode("utf-8"),
                           file_name="productos_modelo.csv")
        st.caption("Rubros válidos: " + ", ".join(NOMBRE_RUBRO))
        provs = {p["id"]: p["nombre"] for p in db.todos(con, "proveedores", "nombre")}
        prov_csv = st.selectbox("Proveedor de estos productos", [None] + list(provs),
                                format_func=lambda i: "— sin asignar —" if i is None else provs[i], key="prov_csv")
        archivo = st.file_uploader("CSV", type=["csv"])
        if archivo and st.button("Importar"):
            datos = pd.read_csv(archivo)
            cargados = 0
            for _, r in datos.iterrows():
                fila = {k: (None if pd.isna(v) else v) for k, v in r.items()}
                if not fila.get("titulo"):
                    continue
                db.insertar(con, "productos", {**fila, "proveedor_id": prov_csv})
                cargados += 1
            st.success(f"{cargados} productos importados.")


# ---------------------------------------------------------------- proveedores
def form_proveedor(clave: str, datos: dict | None = None) -> dict | None:
    d = datos or {}
    with st.form(clave, clear_on_submit=datos is None):
        nombre = st.text_input("Nombre *", d.get("nombre", ""))
        c1, c2, c3 = st.columns(3)
        tipos = ["mayorista", "distribuidor", "fabricante", "tienda online", "otro"]
        tipo = c1.selectbox("Tipo", tipos, index=tipos.index(d["tipo"]) if d.get("tipo") in tipos else 0)
        pais = c2.text_input("País", d.get("pais") or "EE.UU.")
        ciudad = c3.text_input("Ciudad / estado", d.get("ciudad") or "")
        c1, c2, c3 = st.columns(3)
        contacto = c1.text_input("Persona de contacto", d.get("contacto") or "")
        email = c2.text_input("Email", d.get("email") or "")
        whatsapp = c3.text_input("WhatsApp (con código de país)", d.get("whatsapp") or "")
        c1, c2, c3 = st.columns(3)
        web = c1.text_input("Web", d.get("web") or "")
        idiomas = ["en", "es"]
        idioma = c2.selectbox("Idioma", idiomas, index=idiomas.index(d.get("idioma") or "en"),
                              format_func={"en": "Inglés", "es": "Español"}.get)
        estado = c3.selectbox("Estado", db.ESTADOS_PROVEEDOR,
                              index=db.ESTADOS_PROVEEDOR.index(d["estado"]) if d.get("estado") in db.ESTADOS_PROVEEDOR else 0)
        c1, c2, c3, c4 = st.columns(4)
        opciones = ["?", "si", "no"]
        dropship = c1.selectbox("¿Envía unidades sueltas?", opciones,
                                index=opciones.index(d.get("acepta_dropship") or "?"))
        etiqueta = c2.selectbox("¿Usa tu etiqueta ML?", opciones,
                                index=opciones.index(d.get("acepta_etiqueta_ml") or "?"))
        dias = c3.number_input("Días hábiles de preparación (0 = no sabe)", 0.0, value=n(d.get("dias_preparacion")))
        transito = c4.number_input("Días de tránsito a tu 3PL", 0.0, value=n(d.get("dias_transito_local")))
        c1, c2, c3 = st.columns(3)
        corte = c1.text_input("Hora de corte", d.get("corte_horario") or "")
        minimo = c2.text_input("Pedido mínimo", d.get("pedido_minimo") or "")
        confiabilidad = c3.slider("Confiabilidad", 1, 5, int(n(d.get("confiabilidad"), 3)))
        condiciones = st.text_input("Condiciones de pago", d.get("condiciones") or "")
        notas = st.text_area("Notas", d.get("notas") or "")
        if st.form_submit_button("Guardar"):
            if not nombre.strip():
                st.error("Falta el nombre.")
                return None
            return {"nombre": nombre.strip(), "tipo": tipo, "pais": pais, "ciudad": ciudad, "contacto": contacto,
                    "email": email, "whatsapp": whatsapp, "web": web, "idioma": idioma, "estado": estado,
                    "acepta_dropship": dropship, "acepta_etiqueta_ml": etiqueta, "dias_preparacion": dias or None,
                    "dias_transito_local": transito or None, "corte_horario": corte, "pedido_minimo": minimo,
                    "confiabilidad": confiabilidad, "condiciones": condiciones, "notas": notas}
    return None


def pagina_proveedores():
    st.title("Proveedores")
    for p in pendientes:
        st.warning(f"Hacer seguimiento a **{p['nombre']}** (contactado el {p['ultimo_contacto']}).")
    provs = db.todos(con, "proveedores", "nombre")
    if provs:
        st.dataframe(pd.DataFrame(provs)[["id", "nombre", "estado", "dias_preparacion", "acepta_dropship",
                                          "acepta_etiqueta_ml", "email", "whatsapp", "ultimo_contacto",
                                          "proximo_seguimiento", "confiabilidad"]], hide_index=True,
                     column_config={"nombre": "Nombre", "estado": "Estado", "dias_preparacion": "Días prep.",
                                    "acepta_dropship": "Sueltas", "acepta_etiqueta_ml": "Etiqueta ML",
                                    "email": "Email", "whatsapp": "WhatsApp", "ultimo_contacto": "Último contacto",
                                    "proximo_seguimiento": "Seguimiento", "confiabilidad": "Confiabilidad"})
    with st.expander("Agregar proveedor", expanded=not provs):
        nuevo = form_proveedor("nuevo_proveedor")
        if nuevo:
            db.insertar(con, "proveedores", nuevo)
            st.rerun()
    if not provs:
        return
    nombres = {p["id"]: p["nombre"] for p in provs}
    with st.expander("Editar o borrar un proveedor"):
        vid = st.selectbox("Proveedor", list(nombres), format_func=nombres.get, key="editar_prov")
        cambios = form_proveedor(f"form_prov_{vid}", db.uno(con, "proveedores", vid))
        if cambios:
            db.actualizar(con, "proveedores", vid, cambios)
            st.rerun()
        if st.button("Borrar este proveedor", key=f"borrar_prov_{vid}"):
            db.borrar(con, "proveedores", vid)
            st.rerun()

    st.subheader("Preguntarle la demora y las condiciones")
    vid = st.selectbox("Proveedor", list(nombres), format_func=nombres.get, key="msg_prov")
    prov = db.uno(con, "proveedores", vid)
    suyos = db.filas(con, "SELECT * FROM productos WHERE proveedor_id = ?", (vid,))
    c1, c2 = st.columns(2)
    tipo = c1.selectbox("Mensaje", list(plantillas.TIPOS), format_func=plantillas.TIPOS.get)
    idioma = c2.selectbox("Idioma", ["en", "es"], index=0 if prov.get("idioma") != "es" else 1,
                          format_func={"en": "Inglés", "es": "Español"}.get, key=f"idioma_{vid}")
    elegidos = st.multiselect("Productos a consultar", [p["id"] for p in suyos], default=[p["id"] for p in suyos],
                              format_func=lambda i: next(p["titulo"] for p in suyos if p["id"] == i))
    msg = plantillas.armar(tipo, idioma, prov, [p for p in suyos if p["id"] in elegidos], GENERAL)
    asunto = st.text_input("Asunto", msg["asunto"], key=f"asunto_{vid}_{tipo}_{idioma}") if msg["asunto"] else ""
    cuerpo = st.text_area("Texto (editalo si querés)", msg["cuerpo"], height=320, key=f"cuerpo_{vid}_{tipo}_{idioma}")
    c1, c2, c3 = st.columns(3)
    if prov.get("email"):
        c1.link_button("Abrir en mi email", plantillas.link_email(prov["email"], asunto, cuerpo))
    if prov.get("whatsapp"):
        c2.link_button("Abrir en WhatsApp", plantillas.link_whatsapp(prov["whatsapp"], cuerpo))
    if not prov.get("email") and not prov.get("whatsapp"):
        c1.caption("Cargale email o WhatsApp al proveedor para tener los botones. Mientras, copiá el texto.")
    if c3.button("Ya lo envié"):
        db.registrar_contacto(con, vid, "whatsapp" if tipo == "whatsapp" else "email", "enviado",
                              (asunto + "\n\n" + cuerpo).strip())
        st.success("Registrado. Te aviso en 3 días si no responde.")
        st.rerun()

    st.subheader("Anotar lo que respondió")
    with st.form(f"respuesta_{vid}", clear_on_submit=True):
        texto = st.text_area("Respuesta (pegala)")
        c1, c2, c3 = st.columns(3)
        dias = c1.number_input("Días hábiles que informó (0 = no dijo)", 0.0, step=1.0)
        dropship = c2.selectbox("¿Envía unidades sueltas?", ["?", "si", "no"])
        etiqueta = c3.selectbox("¿Usa tu etiqueta ML?", ["?", "si", "no"])
        if st.form_submit_button("Guardar respuesta"):
            db.registrar_contacto(con, vid, "email", "recibido", texto, dias or None)
            cambios = {k: v for k, v in (("acepta_dropship", dropship), ("acepta_etiqueta_ml", etiqueta)) if v != "?"}
            db.actualizar(con, "proveedores", vid, cambios)
            st.success("Guardado. El análisis ya usa esta demora.")
    historial = db.filas(con, "SELECT fecha, canal, direccion, dias_informados, mensaje FROM contactos "
                              "WHERE proveedor_id = ? ORDER BY fecha DESC", (vid,))
    if historial:
        st.caption("Historial")
        st.dataframe(pd.DataFrame(historial), hide_index=True)


# ---------------------------------------------------------------- precios de mercado
def pagina_mercado():
    st.title("Precios de la competencia")
    prods = db.todos(con, "productos")
    if not prods:
        st.info("Primero cargá productos.")
        return
    pid = st.selectbox("Producto", [p["id"] for p in prods],
                       format_func=lambda i: next(p["titulo"] for p in prods if p["id"] == i))
    prod = db.uno(con, "productos", pid)
    texto = st.text_input("Buscar en Mercado Libre como", prod.get("busqueda") or prod["titulo"])
    ultimos = db.ultimos_precios(con, pid)
    if ultimos:
        st.dataframe(pd.DataFrame(ultimos.values())[["pais", "fecha", "precio_min_local", "precio_mediana_local",
                                                     "precio_max_local", "resultados", "internacionales", "fuente"]],
                     hide_index=True)
    if not estado_ml["conectado"]:
        st.caption("Sin la API conectada: abrí el link de cada país, mirá los primeros resultados nuevos y anotá "
                   "el precio más bajo, el del medio y el más alto.")
    else:
        sin_precios = [x for x in prods if x.get("activo", 1) and not db.ultimos_precios(con, x["id"])]
        if sin_precios and st.button(f"Traer precios por API de los {len(sin_precios)} productos que no tienen"):
            barra = st.progress(0.0)
            errores = []
            for i, x in enumerate(sin_precios):
                busq = x.get("busqueda") or x["titulo"]
                for codigo in GENERAL["paises_activos"]:
                    try:
                        resumen = ml.resumir(ml.buscar(PAISES[codigo]["site_id"], busq))
                    except ml.ErrorML as e:
                        errores.append(str(e))
                        break
                    if resumen:
                        db.insertar(con, "precios_mercado", {**resumen, "producto_id": x["id"], "pais": codigo,
                                                             "fuente": "api",
                                                             "url": ml.url_listado(PAISES[codigo], busq)})
                barra.progress((i + 1) / len(sin_precios))
                if errores and "no autorizó" in errores[-1]:
                    break
            if errores:
                st.error(errores[-1])
            else:
                st.success("Listo.")
    for codigo in GENERAL["paises_activos"]:
        cfg = PAISES[codigo]
        with st.expander(f"{cfg['nombre']} ({cfg['moneda']})"):
            c1, c2, c3 = st.columns(3)
            c1.link_button("Ver listado en ML", ml.url_listado(cfg, texto))
            if c2.button("Categoría sugerida", key=f"cat_{codigo}"):
                try:
                    cat = ml.predecir_categoria(cfg["site_id"], texto)
                    st.write(f"{cat['category_name']} ({cat['category_id']})" if cat else "Sin sugerencia")
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
            if c3.button("Traer precios por API", key=f"api_{codigo}", disabled=not estado_ml["conectado"]):
                try:
                    resumen = ml.resumir(ml.buscar(cfg["site_id"], texto))
                    if resumen:
                        db.insertar(con, "precios_mercado", {**resumen, "producto_id": pid, "pais": codigo,
                                                             "fuente": "api", "url": ml.url_listado(cfg, texto)})
                        st.success(f"Mediana {resumen['precio_mediana_local']:,.0f} {cfg['moneda']} "
                                   f"({resumen['resultados']} resultados, {resumen['internacionales']} internacionales)")
                        st.rerun()
                    else:
                        st.warning("Sin resultados.")
                except ml.ErrorML as e:
                    st.error(str(e))
            with st.form(f"manual_{codigo}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                pmin = c1.number_input("Más barato", 0.0, key=f"min_{codigo}")
                pmed = c2.number_input("Del medio *", 0.0, key=f"med_{codigo}")
                pmax = c3.number_input("Más caro", 0.0, key=f"max_{codigo}")
                inter = c4.number_input("Vendedores internacionales", 0, step=1, key=f"int_{codigo}")
                if st.form_submit_button("Guardar a mano"):
                    if not pmed:
                        st.error("El precio del medio es obligatorio.")
                    else:
                        db.insertar(con, "precios_mercado", {"producto_id": pid, "pais": codigo,
                                                             "precio_min_local": pmin or None,
                                                             "precio_mediana_local": pmed,
                                                             "precio_max_local": pmax or None,
                                                             "internacionales": inter, "fuente": "manual",
                                                             "url": ml.url_listado(cfg, texto)})
                        st.rerun()


# ---------------------------------------------------------------- configuración
def pagina_configuracion():
    st.title("Configuración")
    st.warning("Los valores de fábrica (comisiones, tabla de envíos, impuestos) son ESTIMADOS para arrancar. "
               "Cuando tengas la cuenta de Global Selling, copiá los reales de tu Seller Center.")
    t_general, t_paises, t_rubros, t_api = st.tabs(["General", "Países", "Rubros", "Conexiones"])

    with t_general, st.form("general"):
        g = GENERAL
        c1, c2, c3 = st.columns(3)
        margen = c1.number_input("Margen objetivo (%)", 0.0, 90.0, float(g["margen_objetivo_pct"]))
        gmin = c2.number_input("Ganancia mínima por venta (USD)", 0.0, value=float(g["ganancia_minima_usd"]))
        factor = c3.number_input("Precio vs competencia (0,97 = 3 % más barato)", 0.5, 1.5,
                                 float(g["factor_precio_competitivo"]), step=0.01)
        c1, c2, c3 = st.columns(3)
        payout = c1.number_input("Costo de cobro / retiro (%)", 0.0, value=float(g["payout_pct"]))
        reserva = c2.number_input("Reserva para reclamos y devoluciones (%)", 0.0, value=float(g["reserva_reclamos_pct"]))
        divisor = c3.number_input("Divisor peso volumétrico", 1000, 10000, int(g["divisor_volumetrico"]))
        c1, c2, c3 = st.columns(3)
        estandar = c1.number_input("Días de despacho que da ML sin declarar", 0, 10, int(g["dias_despacho_estandar"]))
        colchon = c2.number_input("Días de colchón", 0, 10, int(g["colchon_dias"]))
        dias3pl = c3.number_input("Días de proceso del 3PL", 0, 10, int(g["dias_3pl"]))
        c1, c2, c3 = st.columns(3)
        dprov = c1.number_input("Demora supuesta si el proveedor no informó", 0, 30, int(g["dias_proveedor_por_defecto"]))
        dtran = c2.number_input("Tránsito supuesto hasta el 3PL", 0, 30, int(g["dias_transito_local_por_defecto"]))
        dmax = c3.number_input("Máximo de días recomendado", 1, 60, int(g["max_dias_recomendado"]))
        st.markdown("**Compra en EE.UU., logística y publicidad**")
        c1, c2, c3, c4 = st.columns(4)
        tax = c1.number_input("Sales tax de compra (%)", 0.0, 15.0, float(g["sales_tax_compra_pct"]),
                              help="0 si tu prep center está en Oregon, Delaware, Montana o New Hampshire, "
                                   "o si comprás con certificado de reventa")
        publicidad = c2.number_input("Publicidad, ACOS (% del precio)", 0.0, 50.0, float(g["publicidad_pct"]))
        prep_u = c3.number_input("Prep center por unidad (USD)", 0.0, value=float(g["prep_por_unidad_usd"]))
        zip_prep = c4.text_input("Código postal del prep center", g.get("zip_prep_center", ""),
                                 help="Para que eBay calcule el envío hasta ahí")
        c1, c2, c3, c4 = st.columns(4)
        alm = c1.number_input("Depósito Texas: USD por unidad y mes", 0.0, value=float(g["full_almacenaje_usd_mes"]))
        meses = c2.number_input("Meses que tarda en venderse", 0.0, 24.0, float(g["full_meses_stock"]))
        bmin = c3.number_input("Buscar desde (USD)", 0.0, value=float(g["costo_min_busqueda_usd"]))
        bmax = c4.number_input("Buscar hasta (USD)", 0.0, value=float(g["costo_max_busqueda_usd"]))
        c1, c2 = st.columns(2)
        empresa = c1.text_input("Nombre de tu empresa (para los mensajes)", g["empresa"])
        firma = c2.text_input("Firma (para los mensajes)", g["firma"])
        activos = st.multiselect("Países activos", list(PAISES), default=g["paises_activos"], format_func=nombre_pais)
        if st.form_submit_button("Guardar"):
            config.guardar_cambios("general", {
                "margen_objetivo_pct": margen, "ganancia_minima_usd": gmin, "factor_precio_competitivo": factor,
                "payout_pct": payout, "reserva_reclamos_pct": reserva, "divisor_volumetrico": divisor,
                "dias_despacho_estandar": estandar, "colchon_dias": colchon, "dias_3pl": dias3pl,
                "dias_proveedor_por_defecto": dprov, "dias_transito_local_por_defecto": dtran,
                "max_dias_recomendado": dmax, "empresa": empresa, "firma": firma, "paises_activos": activos,
                "sales_tax_compra_pct": tax, "publicidad_pct": publicidad, "prep_por_unidad_usd": prep_u,
                "zip_prep_center": zip_prep.strip(), "full_almacenaje_usd_mes": alm, "full_meses_stock": meses,
                "costo_min_busqueda_usd": bmin, "costo_max_busqueda_usd": bmax})
            st.rerun()

    with t_paises:
        if st.button("Actualizar tipos de cambio de hoy"):
            try:
                st.success(", ".join(f"{k}: {v:,.2f}" for k, v in fx.actualizar_tipos_de_cambio().items()))
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"No se pudo actualizar: {e}")
        for codigo, cfg in PAISES.items():
            with st.expander(f"{cfg['nombre']} — comisión {cfg['comision_pct']} %, USD 1 = {cfg['usd_a_local']:,.2f} "
                             f"{cfg['moneda']}"):
                with st.form(f"pais_{codigo}"):
                    c1, c2, c3, c4 = st.columns(4)
                    tc = c1.number_input(f"USD → {cfg['moneda']}", 0.0, value=float(cfg["usd_a_local"]), format="%.4f")
                    com = c2.number_input("Comisión (%)", 0.0, 60.0, float(cfg["comision_pct"]))
                    fijo = c3.number_input("Cargo fijo (USD)", 0.0, value=float(cfg.get("cargo_fijo_usd", 0)))
                    fijo_hasta = c4.number_input("…en ventas de menos de (USD)", 0.0,
                                                 value=float(cfg.get("cargo_fijo_hasta_usd", 0)))
                    c1, c2, c3, c4 = st.columns(4)
                    modos = ["siempre", "sobre_umbral", "nunca"]
                    modo = c1.selectbox("Envío internacional a tu cargo", modos,
                                        index=modos.index(cfg["envio"].get("a_cargo_vendedor", "siempre")),
                                        format_func={"siempre": "Siempre", "sobre_umbral": "Desde el umbral",
                                                     "nunca": "Nunca (lo paga el comprador)"}.get)
                    umbral = c2.number_input("Umbral envío gratis (USD)", 0.0,
                                             value=float(cfg["envio"].get("umbral_envio_gratis_usd", 0)))
                    tmin = c3.number_input("Tránsito internacional mín. (días)", 0, 60,
                                           int(cfg["transito_internacional_dias"][0]))
                    tmax = c4.number_input("Tránsito internacional máx. (días)", 0, 60,
                                           int(cfg["transito_internacional_dias"][1]))
                    st.caption("Costo del envío internacional que te cobra ML, por peso facturable")
                    tabla = st.data_editor(pd.DataFrame(cfg["envio"]["tabla_usd_por_kg"], columns=["hasta_kg", "usd"]),
                                           num_rows="dynamic", hide_index=True, key=f"tabla_{codigo}")
                    imp = cfg.get("impuestos_comprador", {})
                    st.caption("Impuestos que paga el comprador. 'hasta_usd' vacío = sin tope. " + imp.get("nota", ""))
                    tramos = st.data_editor(pd.DataFrame(imp.get("tramos", []),
                                                         columns=["hasta_usd", "pct", "deduccion_usd"]),
                                            num_rows="dynamic", hide_index=True, key=f"tramos_{codigo}")
                    por_dentro = st.number_input("IVA/ICMS calculado 'por dentro' (%)", 0.0, 50.0,
                                                 float(imp.get("iva_por_dentro_pct", 0)))
                    if st.form_submit_button("Guardar " + cfg["nombre"]):
                        filas_tabla = sorted([float(r.hasta_kg), float(r.usd)] for r in tabla.itertuples()
                                             if not pd.isna(r.hasta_kg) and not pd.isna(r.usd))
                        filas_tramos = []
                        for r in tramos.itertuples():
                            if pd.isna(r.pct):
                                continue
                            t = {"hasta_usd": None if pd.isna(r.hasta_usd) else float(r.hasta_usd), "pct": float(r.pct)}
                            if not pd.isna(r.deduccion_usd):
                                t["deduccion_usd"] = float(r.deduccion_usd)
                            filas_tramos.append(t)
                        filas_tramos.sort(key=lambda t: float("inf") if t["hasta_usd"] is None else t["hasta_usd"])
                        config.guardar_cambios("paises", {codigo: {
                            "usd_a_local": tc, "comision_pct": com, "cargo_fijo_usd": fijo,
                            "cargo_fijo_hasta_usd": fijo_hasta, "transito_internacional_dias": [tmin, tmax],
                            "envio": {"a_cargo_vendedor": modo, "umbral_envio_gratis_usd": umbral,
                                      "tabla_usd_por_kg": filas_tabla or cfg["envio"]["tabla_usd_por_kg"]},
                            "impuestos_comprador": {"tramos": filas_tramos, "iva_por_dentro_pct": por_dentro}}})
                        st.rerun()

    with t_rubros:
        st.caption("Si ML te cobra otra comisión en un rubro, ponela en la columna del país. Vacío = la del país.")
        filas = []
        for r in RUBROS:
            fila = {k: r.get(k, "") for k in ("id", "nombre", "riesgo", "nota", "ideas")}
            for c in PAISES:
                fila[f"comision_{c}"] = (r.get("comision_pct") or {}).get(c)
            filas.append(fila)
        editado = st.data_editor(pd.DataFrame(filas), num_rows="dynamic", hide_index=True, key="ed_rubros",
                                 column_config={"riesgo": st.column_config.SelectboxColumn(
                                     "riesgo", options=["bajo", "medio", "alto"])})
        if st.button("Guardar rubros"):
            nuevos = []
            for r in editado.to_dict("records"):
                if not r.get("id"):
                    continue
                comisiones = {c: float(r[f"comision_{c}"]) for c in PAISES
                              if r.get(f"comision_{c}") not in (None, "") and not pd.isna(r.get(f"comision_{c}"))}
                nuevos.append({**{k: r.get(k) or "" for k in ("id", "nombre", "riesgo", "nota", "ideas")},
                               "comision_pct": comisiones})
            config.guardar_cambios("rubros", {"rubros": nuevos})
            st.rerun()

    with t_api:
        st.subheader("eBay (para buscar ofertas)")
        st.markdown(
            "1. Registrate gratis en **developer.ebay.com** con tu cuenta de eBay.\n"
            "2. En **Application Keys**, creá un keyset de **Production**.\n"
            "3. Copiá acá el **App ID (Client ID)** y el **Cert ID (Client Secret)**.")
        ce = ebay.credenciales()
        with st.form("cred_ebay"):
            eid = st.text_input("App ID (Client ID)", ce.get("client_id", ""))
            esec = st.text_input("Cert ID (Client Secret)", ce.get("client_secret", ""), type="password")
            if st.form_submit_button("Guardar credenciales de eBay"):
                ebay.guardar_credenciales(eid, esec)
                st.rerun()
        if ebay.configurado() and st.button("Probar eBay"):
            try:
                st.dataframe(pd.DataFrame(ebay.buscar("ssd nvme 2tb", 50, 500, limite=5)))
            except ebay.ErrorEbay as e:
                st.error(str(e))
        st.subheader("Mercado Libre (para traer precios de la competencia)")
        st.markdown(
            "1. Entrá a **developers.mercadolibre.com.ar → Mis aplicaciones → Crear aplicación** (con tu usuario de ML).\n"
            "2. En *Redirect URI* poné una dirección https (por ejemplo `https://www.google.com`).\n"
            "3. Copiá acá el **Client ID** y el **Client Secret**, guardá y tocá *Autorizar*.\n"
            "4. Después de aceptar, el navegador va a una dirección que tiene `?code=TG-...`: copiala entera y pegala abajo.")
        cred = ml.credenciales()
        with st.form("cred_ml"):
            cid = st.text_input("Client ID", cred.get("client_id", ""))
            secreto = st.text_input("Client Secret", cred.get("client_secret", ""), type="password")
            redirect = st.text_input("Redirect URI", cred.get("redirect_uri", "https://www.google.com"))
            if st.form_submit_button("Guardar credenciales"):
                ml.guardar_credenciales(cid, secreto, redirect)
                st.rerun()
        if cred.get("client_id"):
            dominios = {"GS": "https://global-selling.mercadolibre.com", **{c: PAISES[c]["dominio_auth"] for c in PAISES}}
            pais_auth = st.selectbox("Cuenta de Mercado Libre", list(dominios),
                                     format_func=lambda c: "Global Selling (para publicar)" if c == "GS"
                                     else f"{nombre_pais(c)} (solo para leer precios)")
            st.link_button("Autorizar en Mercado Libre", ml.url_autorizacion(dominios[pais_auth]))
            codigo = st.text_input("Pegá acá la dirección (o el código TG-...)")
            if st.button("Conectar") and codigo:
                try:
                    t = ml.canjear_codigo(codigo)
                    st.success(f"Conectado (usuario {t.get('user_id')}).")
                    st.rerun()
                except ml.ErrorML as e:
                    st.error(str(e))
        st.write("Estado: " + ("conectada" if estado_ml["conectado"] else "sin conectar"))
        if estado_ml["conectado"] and st.button("Probar una búsqueda en México"):
            try:
                st.dataframe(pd.DataFrame(ml.buscar("MLM", "cable usb c", 5)))
            except ml.ErrorML as e:
                st.error(str(e))

    st.divider()
    if st.button("Volver a los valores de fábrica (no borra productos ni proveedores)"):
        for nombre in ("general", "paises", "rubros"):
            config.restablecer(nombre)
        st.rerun()


{"Oportunidades": pagina_oportunidades, "Buscar ofertas": pagina_buscar, "Calculadora rápida": pagina_calculadora,
 "Productos": pagina_productos,
 "Proveedores": pagina_proveedores, "Precios de mercado": pagina_mercado,
 "Configuración": pagina_configuracion}[pagina]()
