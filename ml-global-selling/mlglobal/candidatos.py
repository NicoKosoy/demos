"""Carga una tanda de candidatos (JSON) a la base. Si un título ya existe, lo actualiza."""
from __future__ import annotations

import json
from pathlib import Path

from . import db

TIENDAS = {"amazon": "Amazon", "ebay": "eBay", "walmart": "Walmart"}


def cargar(con, ruta: str | Path) -> tuple[int, int]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    db.asegurar_fuentes(con)
    nuevos = actualizados = 0
    for item in datos["productos"]:
        fila = {k: v for k, v in item.items() if k not in ("precios_competencia", "proveedor")}
        tienda = item.get("proveedor") or {}
        if tienda.get("nombre") and not db.proveedor_por_nombre(con, tienda["nombre"]):
            db.insertar(con, "proveedores", {"tipo": "tienda online", "pais": "EE.UU.", "estado": "aprobado",
                                             "acepta_dropship": "si", "acepta_etiqueta_ml": "no", **tienda})
        prov = db.proveedor_por_nombre(con, tienda.get("nombre") or
                                       TIENDAS.get((fila.get("fuente_compra") or "").lower(), ""))
        if prov and not fila.get("proveedor_id"):
            fila["proveedor_id"] = prov["id"]
        existente = con.execute("SELECT id FROM productos WHERE titulo = ?", (fila["titulo"],)).fetchone()
        if existente:
            pid = existente["id"]
            db.actualizar(con, "productos", pid, fila)
            actualizados += 1
        else:
            pid = db.insertar(con, "productos", fila)
            nuevos += 1
        for pais, precio in (item.get("precios_competencia") or {}).items():
            db.insertar(con, "precios_mercado", {"producto_id": pid, "pais": pais, "precio_mediana_local": precio,
                                                 "fuente": datos.get("fuente_precios", "manual")})
    return nuevos, actualizados
