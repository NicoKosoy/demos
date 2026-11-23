"""Junta producto + proveedor + precios de la competencia y calcula, por país, si conviene publicar."""
from __future__ import annotations

from . import config, db
from .demora import calcular_demora
from .margen import Producto, calcular, precio_competitivo, precio_minimo
from .puntaje import calcular_puntaje


def armar_producto(prod: dict, general: dict) -> Producto:
    """Producto con el sales tax de compra y, si va al depósito de Texas, el almacenaje."""
    tax = prod.get("sales_tax_pct")
    almacenaje = 0.0
    if (prod.get("ruta") or "").lower() == "full":
        almacenaje = float(general.get("full_almacenaje_usd_mes", 0)) * float(general.get("full_meses_stock", 0))
    return Producto.desde_dict({**prod, "almacenaje_usd": almacenaje,
                                "sales_tax_pct": general.get("sales_tax_compra_pct", 0) if tax in (None, "") else tax})


def analizar_producto(prod: dict, prov: dict | None, mercado_por_pais: dict, paises_cfg: dict,
                      general: dict, rubros: list[dict], paises: list[str] | None = None) -> list[dict]:
    rubro_cfg = next((r for r in rubros if r["id"] == prod.get("rubro")), None)
    riesgo = prod.get("riesgo") or (rubro_cfg or {}).get("riesgo", "medio")
    condicion = (prod.get("condicion") or "nuevo").lower()
    ruta = (prod.get("ruta") or "directo").lower()
    p = armar_producto(prod, general)
    salida = []
    for codigo in paises or general["paises_activos"]:
        cfg = paises_cfg.get(codigo)
        if not cfg:
            continue
        tc = float(cfg["usd_a_local"])
        mercado = mercado_por_pais.get(codigo) or {}
        mediana_local = mercado.get("precio_mediana_local")
        mediana_usd = mediana_local / tc if mediana_local else None
        minimo = precio_minimo(p, cfg, general, rubro_cfg=rubro_cfg, pais=codigo)
        competitivo = None
        if mediana_usd:
            competitivo = precio_competitivo(p, cfg, general, mediana_usd * float(general["factor_precio_competitivo"]),
                                             rubro_cfg, codigo)
        if prod.get("precio_venta_usd"):
            precio, origen = float(prod["precio_venta_usd"]), "fijado por vos"
        elif competitivo:
            precio, origen = competitivo, "para competir"
        elif minimo:
            precio, origen = minimo, "mínimo para el margen"
        else:
            precio, origen = max(p.costo_total * 2, 1.0), "estimado"
        res = calcular(p, cfg, general, precio, rubro_cfg, codigo)
        dem = calcular_demora(prov, prod, general, cfg)
        pun = calcular_puntaje(res, dem, riesgo, general, mediana_usd)
        if pun["veredicto"] == "Publicar" and not dem["demora_confirmada"]:
            pun["veredicto"] = "Confirmar demora"
        alertas = []
        if condicion == "usado":
            pun["veredicto"], pun["puntaje"] = "No permitido", 0
            alertas.append("Global Selling solo acepta productos nuevos")
        elif condicion == "reacondicionado":
            alertas.append("Reacondicionado: confirmar con Mercado Libre si se permite en este país")
        if ruta == "full":
            alertas.append("Stock en Texas: se compra antes de vender (capital inmovilizado)")
        minimo_final = (calcular(p, cfg, general, minimo, rubro_cfg, codigo)["precio_final_comprador_local"]
                        if minimo else None)
        equilibrio = precio_minimo(p, cfg, general, 0, 0, rubro_cfg, codigo)
        equilibrio_final = (calcular(p, cfg, general, equilibrio, rubro_cfg, codigo)["precio_final_comprador_local"]
                            if equilibrio else None)
        if minimo is None:
            alertas.append("Con estos costos no hay precio que llegue al margen objetivo")
        elif competitivo and competitivo < minimo:
            alertas.append(f"La competencia obliga a vender a USD {competitivo:.2f} y tu mínimo es USD {minimo:.2f}")
        if not mercado:
            alertas.append("Sin precios de la competencia")
        elif mercado.get("fuente") == "ejemplo":
            alertas.append("Precios de competencia de EJEMPLO (inventados)")
        if not dem["demora_confirmada"]:
            alertas.append(f"Demora del proveedor sin confirmar (se asumen {general['dias_proveedor_por_defecto']} días)")
        if dem["alerta_exposicion"]:
            alertas.append(f"Más de {general['max_dias_recomendado']} días de disponibilidad: baja la exposición")
        if not p.peso_kg and not (p.largo_cm and p.ancho_cm and p.alto_cm):
            alertas.append("Falta el peso: el envío se calculó con el tramo mínimo")
        if riesgo == "alto":
            alertas.append("Riesgo regulatorio alto: " + (rubro_cfg or {}).get("nota", "verificar homologación"))
        if prov and prov.get("acepta_etiqueta_ml") == "no" and dem["ruta"] == "directo":
            alertas.append("El proveedor no acepta etiqueta de ML: pasalo a ruta 3PL")
        if res["impuesto_comprador_usd"] > 0:
            pct = res["impuesto_comprador_usd"] / res["precio_usd"] * 100
            alertas.append(f"El comprador paga ~{pct:.0f} % de impuestos de importación")

        salida.append({
            "producto_id": prod["id"],
            "producto": prod["titulo"],
            "rubro": (rubro_cfg or {}).get("nombre", prod.get("rubro") or ""),
            "proveedor": (prov or {}).get("nombre", ""),
            "pais": codigo,
            "pais_nombre": cfg["nombre"],
            "moneda": cfg["moneda"],
            "precio_usd": res["precio_usd"],
            "origen_precio": origen,
            "precio_local": res["precio_local"],
            "precio_minimo_usd": minimo,
            "minimo_final_comprador_local": minimo_final,
            "equilibrio_usd": equilibrio,
            "equilibrio_final_comprador_local": equilibrio_final,
            "fuente_compra": prod.get("fuente_compra") or "",
            "condicion": condicion,
            "costo_compra_usd": round(float(prod.get("costo_usd") or 0), 2),
            "precio_competitivo_usd": competitivo,
            "ganancia_usd": res["ganancia_usd"],
            "margen_pct": res["margen_pct"],
            "roi_pct": res["roi_pct"],
            "comision_usd": res["comision_usd"],
            "envio_vendedor_usd": res["envio_vendedor_usd"],
            "publicidad_usd": res["publicidad_usd"],
            "cargos_usd": round(res["cargo_fijo_usd"] + res["payout_usd"] + res["reserva_usd"], 2),
            "costo_producto_usd": res["costo_producto_usd"],
            "precio_final_comprador_local": res["precio_final_comprador_local"],
            "mediana_competencia_local": mediana_local,
            "dif_vs_competencia_pct": (round((res["precio_final_comprador_local"] / mediana_local - 1) * 100, 1)
                                       if mediana_local else None),
            "competidores_internacionales": mercado.get("internacionales"),
            "dias_a_declarar": dem["dias_a_declarar"],
            "entrega_estimada": f"{dem['entrega_min']}-{dem['entrega_max']} días hábiles",
            "demora_confirmada": dem["demora_confirmada"],
            "riesgo": riesgo,
            "puntaje": pun["puntaje"],
            "veredicto": pun["veredicto"],
            "alertas": " · ".join(alertas),
            "_detalle": {"resultado": res, "demora": dem, "puntaje": pun["partes"]},
        })
    return salida


def margen_a_precio(con, producto_id: int, pais: str, precio_usd: float) -> dict | None:
    """Cuenta con el costo de HOY a un precio dado (sirve cuando entra un pedido)."""
    prod = db.uno(con, "productos", producto_id)
    paises_cfg = config.paises()
    if not prod or pais not in paises_cfg:
        return None
    general = config.general()
    rubro_cfg = config.rubro(prod.get("rubro"))
    return calcular(armar_producto(prod, general), paises_cfg[pais], general, precio_usd, rubro_cfg, pais)


def analizar_todo(con, paises: list[str] | None = None, solo_activos: bool = True) -> list[dict]:
    paises_cfg = config.paises()
    general = config.general()
    rubros = config.rubros()
    proveedores = {p["id"]: p for p in db.todos(con, "proveedores")}
    filas = []
    for prod in db.todos(con, "productos"):
        if solo_activos and not prod.get("activo", 1):
            continue
        filas += analizar_producto(prod, proveedores.get(prod.get("proveedor_id")),
                                   db.ultimos_precios(con, prod["id"]), paises_cfg, general, rubros, paises)
    return filas
