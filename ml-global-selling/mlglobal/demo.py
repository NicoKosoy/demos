"""Datos de EJEMPLO para ver la herramienta funcionando. Los precios de competencia son inventados."""
from __future__ import annotations

from . import db

PREFIJO = "[EJEMPLO]"

PROVEEDORES = [
    {"nombre": f"{PREFIJO} Mayorista de tecnología (Miami, FL)", "tipo": "mayorista", "pais": "EE.UU.",
     "ciudad": "Miami", "idioma": "en", "estado": "respondió", "acepta_dropship": "si", "acepta_etiqueta_ml": "si",
     "dias_preparacion": 1, "dias_transito_local": 1, "confiabilidad": 4,
     "notas": "Ejemplo: respondió que despacha en 24 h hábiles con etiqueta prepaga."},
    {"nombre": f"{PREFIJO} Fábrica con depósito en California", "tipo": "fabricante", "pais": "EE.UU.",
     "ciudad": "Ontario, CA", "idioma": "en", "estado": "sin contactar", "acepta_dropship": "?",
     "acepta_etiqueta_ml": "?", "dias_transito_local": 4, "confiabilidad": 3,
     "notas": "Ejemplo: todavía no se le preguntó la demora."},
]

# (producto, índice del proveedor, medianas de competencia en moneda local por país)
PRODUCTOS = [
    ({"titulo": f"{PREFIJO} Cable USB-C a USB-C 240 W trenzado 2 m", "rubro": "cables", "costo_usd": 3.2,
      "envio_local_usd": 0.6, "peso_kg": 0.08, "largo_cm": 18, "ancho_cm": 10, "alto_cm": 2,
      "busqueda": "cable usb c 240w 2 metros"}, 0,
     {"MX": 249, "BR": 69, "CL": 12990, "CO": 45000, "AR": 18000}),
    ({"titulo": f"{PREFIJO} Hub USB-C 7 en 1 con HDMI 4K", "rubro": "hubs", "costo_usd": 14.5,
      "envio_local_usd": 0.8, "peso_kg": 0.12, "largo_cm": 14, "ancho_cm": 7, "alto_cm": 3,
      "busqueda": "hub usb c 7 en 1 hdmi 4k"}, 0,
     {"MX": 899, "BR": 229, "CL": 44990, "CO": 199000, "AR": 79000}),
    ({"titulo": f"{PREFIJO} SSD NVMe 1 TB PCIe 4.0", "rubro": "almacenamiento", "costo_usd": 58,
      "envio_local_usd": 0.8, "peso_kg": 0.05, "largo_cm": 12, "ancho_cm": 9, "alto_cm": 2,
      "busqueda": "ssd nvme 1tb pcie 4.0"}, 0,
     {"MX": 1599, "BR": 499, "CL": 79990, "CO": 349000, "AR": 145000}),
    ({"titulo": f"{PREFIJO} Kit 24 boquillas para impresora 3D", "rubro": "impresion3d", "costo_usd": 4.8,
      "envio_local_usd": 0.5, "prep_usd": 1.5, "peso_kg": 0.05, "ruta": "3pl",
      "busqueda": "kit boquillas impresora 3d"}, 1,
     {"MX": 499, "BR": 119, "CL": 21990, "CO": 89000, "AR": 39000}),
    ({"titulo": f"{PREFIJO} Power bank 20000 mAh", "rubro": "carga_energia", "costo_usd": 16, "peso_kg": 0.4,
      "largo_cm": 15, "ancho_cm": 8, "alto_cm": 3, "busqueda": "power bank 20000 mah"}, 1,
     {"MX": 499, "BR": 149, "CL": 24990, "CO": 109000, "AR": 45000}),
]


def cargar_ejemplos(con) -> int:
    ids = [db.insertar(con, "proveedores", p) for p in PROVEEDORES]
    for prod, i_prov, medianas in PRODUCTOS:
        pid = db.insertar(con, "productos", {**prod, "proveedor_id": ids[i_prov]})
        for pais, mediana in medianas.items():
            db.insertar(con, "precios_mercado", {"producto_id": pid, "pais": pais, "precio_mediana_local": mediana,
                                                 "fuente": "ejemplo", "notas": "Precio inventado para la demo"})
    return len(PRODUCTOS)


def hay_ejemplos(con) -> bool:
    return bool(db.filas(con, "SELECT 1 FROM productos WHERE titulo LIKE ? LIMIT 1", (PREFIJO + "%",)))


def borrar_ejemplos(con) -> None:
    con.execute("DELETE FROM productos WHERE titulo LIKE ?", (PREFIJO + "%",))
    con.execute("DELETE FROM proveedores WHERE nombre LIKE ?", (PREFIJO + "%",))
    con.commit()
