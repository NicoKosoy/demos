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
    assert {f["veredicto"] for f in filas} >= {"Publicar", "Pierde plata"}
    demo.borrar_ejemplos(con)
    assert analizar_todo(con) == []
