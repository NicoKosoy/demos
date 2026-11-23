import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mlglobal import db, demo
from mlglobal.analisis import analizar_todo
from mlglobal.demora import calcular_demora
from mlglobal.margen import (Producto, calcular, costo_envio_internacional, impuesto_comprador,
                             precio_competitivo, precio_minimo)

GENERAL = {"margen_objetivo_pct": 25, "ganancia_minima_usd": 4, "payout_pct": 1.5, "reserva_reclamos_pct": 3,
           "divisor_volumetrico": 5000, "dias_despacho_estandar": 2, "colchon_dias": 1, "dias_3pl": 1,
           "dias_proveedor_por_defecto": 3, "dias_transito_local_por_defecto": 2, "max_dias_recomendado": 7,
           "factor_precio_competitivo": 0.97, "paises_activos": ["XX"]}

PAIS = {"nombre": "Prueba", "moneda": "XXX", "usd_a_local": 10, "comision_pct": 15,
        "cargo_fijo_usd": 1, "cargo_fijo_hasta_usd": 12,
        "envio": {"a_cargo_vendedor": "siempre", "umbral_envio_gratis_usd": 20,
                  "tabla_usd_por_kg": [[0.5, 5], [1, 8], [2, 12]]},
        "impuestos_comprador": {"tramos": [{"hasta_usd": 50, "pct": 0}, {"hasta_usd": None, "pct": 20}]},
        "transito_internacional_dias": [5, 10]}


def test_cuenta_a_mano():
    p = Producto(costo_usd=10, envio_local_usd=1, peso_kg=0.3)
    r = calcular(p, PAIS, GENERAL, 40)
    # 40 - 6 comisión - 0 fijo - 5 envío - 0.6 payout - 1.2 reserva - 11 costo = 16.2
    assert r["ganancia_usd"] == 16.2
    assert r["margen_pct"] == 40.5
    assert r["impuesto_comprador_usd"] == 0
    assert r["precio_final_comprador_local"] == 400


def test_peso_volumetrico_manda():
    p = Producto(costo_usd=1, peso_kg=0.1, largo_cm=30, ancho_cm=20, alto_cm=10)  # 1,2 kg volumétrico
    assert calcular(p, PAIS, GENERAL, 50)["envio_vendedor_usd"] == 12


def test_envio_extrapola_arriba_de_la_tabla():
    assert math.isclose(costo_envio_internacional(PAIS, 3), 16)


def test_precio_minimo_cumple_y_es_minimo():
    p = Producto(costo_usd=10, envio_local_usd=1, peso_kg=0.3)
    precio = precio_minimo(p, PAIS, GENERAL)
    r = calcular(p, PAIS, GENERAL, precio)
    assert r["margen_pct"] >= 25 and r["ganancia_usd"] >= 4
    r_menos = calcular(p, PAIS, GENERAL, precio - 0.05)
    assert r_menos["margen_pct"] < 25 or r_menos["ganancia_usd"] < 4


def test_precio_minimo_imposible():
    pais = {**PAIS, "comision_pct": 80}
    assert precio_minimo(Producto(costo_usd=5), pais, GENERAL) is None


def test_impuestos_brasil_por_dentro():
    br = {"impuestos_comprador": {"tramos": [{"hasta_usd": 50, "pct": 20},
                                             {"hasta_usd": 3000, "pct": 60, "deduccion_usd": 20}],
                                  "iva_por_dentro_pct": 17}}
    assert math.isclose(impuesto_comprador(br, 40), 40 * 1.2 / 0.83 - 40)
    assert math.isclose(impuesto_comprador(br, 100), (100 + 40) / 0.83 - 100)


def test_precio_competitivo_respeta_objetivo():
    p = Producto(costo_usd=10, peso_kg=0.3)
    precio = precio_competitivo(p, PAIS, GENERAL, 70)  # arriba de 50 hay 20 % de impuesto
    assert calcular(p, PAIS, GENERAL, precio)["precio_final_comprador_usd"] <= 70
    assert precio == 58.33  # 58,33 + 20 % de impuesto = 70: el precio de lista más alto posible


def test_demora_directo_y_3pl():
    prov = {"dias_preparacion": 2, "dias_transito_local": 3}
    directo = calcular_demora(prov, {"ruta": "directo"}, GENERAL, PAIS)
    assert directo["dias_a_declarar"] == 3 and directo["demora_confirmada"]
    tres_pl = calcular_demora(prov, {"ruta": "3pl"}, GENERAL, PAIS)
    assert tres_pl["dias_a_declarar"] == 7 and tres_pl["entrega_max"] == 17
    sin_dato = calcular_demora({}, {"ruta": "directo"}, GENERAL, PAIS)
    assert not sin_dato["demora_confirmada"] and sin_dato["dias_a_declarar"] == 4


def test_demo_de_punta_a_punta(tmp_path):
    con = db.conectar(tmp_path / "prueba.sqlite")
    demo.cargar_ejemplos(con)
    filas = analizar_todo(con)
    assert len(filas) == 5 * 5
    assert {f["veredicto"] for f in filas} >= {"Publicar", "Pierde plata", "No permitido"}
    demo.borrar_ejemplos(con)
    assert analizar_todo(con) == []


def test_sales_tax_y_publicidad():
    p = Producto(costo_usd=100, sales_tax_pct=8.25, peso_kg=0.3)
    r = calcular(p, PAIS, {**GENERAL, "publicidad_pct": 5}, 200)
    # 200 - 30 comisión - 5 envío - 3 payout - 6 reserva - 10 publicidad - 108,25 costo = 37,75
    assert r["publicidad_usd"] == 10 and r["ganancia_usd"] == 37.75
    precio = precio_minimo(p, PAIS, {**GENERAL, "publicidad_pct": 5})
    assert calcular(p, PAIS, {**GENERAL, "publicidad_pct": 5}, precio)["margen_pct"] >= 25


def test_ruta_full_sin_demora():
    d = calcular_demora({}, {"ruta": "full"}, GENERAL, {**PAIS, "transito_full_dias": [2, 4]})
    assert d["dias_a_declarar"] == 0 and d["entrega_max"] == 4 and d["demora_confirmada"]


def test_usado_no_permitido_y_margen_de_hoy(tmp_path):
    from mlglobal.analisis import margen_a_precio
    con = db.conectar(tmp_path / "b.sqlite")
    demo.cargar_ejemplos(con)
    filas = analizar_todo(con)
    usados = [f for f in filas if f["condicion"] == "usado"]
    assert usados and all(f["veredicto"] == "No permitido" for f in usados)
    pid = filas[0]["producto_id"]
    antes = margen_a_precio(con, pid, "MX", 150)["ganancia_usd"]
    db.actualizar(con, "productos", pid, {"costo_usd": 80})  # subió el precio en Amazon
    assert margen_a_precio(con, pid, "MX", 150)["ganancia_usd"] < antes


def test_migra_base_vieja(tmp_path):
    import sqlite3
    ruta = tmp_path / "vieja.sqlite"
    vieja = sqlite3.connect(ruta)
    vieja.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, costo_usd REAL)")
    vieja.commit()
    vieja.close()
    con = db.conectar(ruta)
    assert {"fuente_compra", "condicion", "sales_tax_pct"} <= set(db.columnas(con, "productos"))
    db.asegurar_fuentes(con)
    db.asegurar_fuentes(con)
    assert len(db.todos(con, "proveedores")) == 3


def test_ebay_interpreta_resultados(tmp_path, monkeypatch):
    from mlglobal import ebay

    class Resp:
        def __init__(self, status, datos):
            self.status_code, self._datos, self.text = status, datos, ""

        def json(self):
            return self._datos

    monkeypatch.setattr(ebay, "RUTA_CREDENCIALES", tmp_path / "c.json")
    monkeypatch.setattr(ebay, "RUTA_TOKEN", tmp_path / "t.json")
    monkeypatch.setattr(ebay, "DATOS_DIR", tmp_path)
    ebay.guardar_credenciales("id", "secreto")
    llamadas = {}
    monkeypatch.setattr(ebay.requests, "post", lambda *a, **k: Resp(200, {"access_token": "T", "expires_in": 7200}))

    def falso_get(url, params=None, headers=None, timeout=None):
        llamadas["params"] = params
        return Resp(200, {"itemSummaries": [
            {"title": "SSD 2TB", "price": {"value": "119.99"}, "condition": "New",
             "shippingOptions": [{"shippingCost": {"value": "0.00"}}],
             "seller": {"username": "tienda", "feedbackPercentage": "99.5", "feedbackScore": 1200},
             "itemWebUrl": "https://www.ebay.com/itm/1", "itemId": "v1|1|0"}]})
    monkeypatch.setattr(ebay.requests, "get", falso_get)
    res = ebay.buscar("ssd 2tb", 50, 500)
    assert res[0]["precio_usd"] == 119.99 and res[0]["envio_usd"] == 0 and res[0]["feedback_pct"] == 99.5
    assert "price:[50..500]" in llamadas["params"]["filter"] and "conditions:{NEW}" in llamadas["params"]["filter"]


def test_candidatos_y_payload(tmp_path, monkeypatch):
    import json as _json
    from mlglobal import candidatos, publicar
    monkeypatch.setattr(publicar, "categoria_global",
                        lambda texto: {"category_id": "CBT3012", "category_name": "Effects Pedals"})
    monkeypatch.setattr(publicar, "atributos_requeridos", lambda cat: ("BRAND", "MODEL"))
    archivo = tmp_path / "tanda.json"
    archivo.write_text(_json.dumps({"fuente_precios": "buscador", "productos": [
        {"titulo": "Pedal Boss BD-2", "titulo_en": "Boss BD-2 Blues Driver Pedal", "marca": "Boss",
         "modelo": "BD-2", "upc": "761294037195", "rubro": "audio_musica", "fuente_compra": "amazon",
         "costo_usd": 99, "peso_kg": 0.45, "largo_cm": 15, "ancho_cm": 10, "alto_cm": 8, "ruta": "3pl",
         "precios_competencia": {"MX": 3999}}]}), encoding="utf-8")
    con = db.conectar(tmp_path / "b.sqlite")
    assert candidatos.cargar(con, archivo) == (1, 0)
    assert candidatos.cargar(con, archivo) == (0, 1)  # la segunda vez actualiza, no duplica
    prod = db.todos(con, "productos")[0]
    assert prod["proveedor_id"] == db.proveedor_por_nombre(con, "Amazon")["id"]
    ficha = publicar.armar_ficha(prod, analizar_todo(con))
    assert ficha["categoria_cbt"] == "CBT3012" and ficha["precio_usd_MX"] > 99 and ficha["dias_MX"] == 5
    cuerpo = publicar.payload_global_item(prod, ficha, ["MX", "CO"], {"MX": "MLM", "CO": "MCO"})
    assert cuerpo["title"] == "Boss BD-2 Blues Driver Pedal" and cuerpo["currency_id"] == "USD"
    assert {s["site_id"] for s in cuerpo["sites_to_sell"]} == {"MLM", "MCO"}
    assert cuerpo["sale_terms"][0]["value_name"] == "5 days"


def test_tanda_01_carga_completa(tmp_path):
    from pathlib import Path as _P
    from mlglobal import candidatos
    con = db.conectar(tmp_path / "b.sqlite")
    nuevos, _ = candidatos.cargar(con, _P(__file__).resolve().parent.parent / "candidatos" / "tanda-01.json")
    assert nuevos == 20
    assert db.proveedor_por_nombre(con, "Sweetwater")["dias_preparacion"] == 1
    filas = analizar_todo(con)
    assert all(f["equilibrio_usd"] and f["equilibrio_usd"] > f["costo_compra_usd"] for f in filas)
