"""Datos de EJEMPLO para ver la herramienta funcionando. Los precios de competencia son INVENTADOS."""
from __future__ import annotations

from . import db

PREFIJO = "[EJEMPLO]"

# (producto, tienda donde se compra, medianas de competencia en moneda local por país)
PRODUCTOS = [
    ({"titulo": f"{PREFIJO} Hotend completo para impresora 3D", "rubro": "impresion3d", "fuente_compra": "amazon",
      "costo_usd": 59, "prep_usd": 2.5, "peso_kg": 0.15, "largo_cm": 12, "ancho_cm": 8, "alto_cm": 5,
      "ruta": "3pl", "busqueda": "hotend impresora 3d"}, "Amazon",
     {"MX": 3499, "BR": 549, "CL": 99990, "CO": 459000, "AR": 189000}),
    ({"titulo": f"{PREFIJO} Pedal de guitarra overdrive", "rubro": "audio_musica", "fuente_compra": "ebay",
      "costo_usd": 99, "envio_local_usd": 8, "prep_usd": 2.5, "peso_kg": 0.4, "largo_cm": 15, "ancho_cm": 10,
      "alto_cm": 8, "ruta": "3pl", "busqueda": "pedal overdrive guitarra"}, "eBay",
     {"MX": 3999, "BR": 999, "CL": 169990, "CO": 749000, "AR": 289000}),
    ({"titulo": f"{PREFIJO} Objetivo 50 mm f/1.8 para mirrorless", "rubro": "foto_video", "riesgo": "bajo",
      "fuente_compra": "walmart", "costo_usd": 199, "prep_usd": 2.5, "peso_kg": 0.25, "largo_cm": 12,
      "ancho_cm": 10, "alto_cm": 10, "ruta": "3pl", "busqueda": "lente 50mm 1.8"}, "Walmart",
     {"MX": 6999, "BR": 1899, "CL": 299990, "CO": 1299000, "AR": 549000}),
    ({"titulo": f"{PREFIJO} SSD NVMe 2 TB PCIe 4.0", "rubro": "almacenamiento", "fuente_compra": "amazon",
      "costo_usd": 119, "prep_usd": 2.5, "peso_kg": 0.06, "largo_cm": 12, "ancho_cm": 9, "alto_cm": 2,
      "ruta": "full", "envio_local_usd": 1.5, "busqueda": "ssd nvme 2tb"}, "Amazon",
     {"MX": 3499, "BR": 1099, "CL": 169990, "CO": 799000, "AR": 299000}),
    ({"titulo": f"{PREFIJO} Consola usada", "rubro": "videojuegos", "fuente_compra": "ebay", "condicion": "usado",
      "costo_usd": 280, "envio_local_usd": 15, "peso_kg": 2.5, "ruta": "3pl", "busqueda": "consola"}, "eBay",
     {"MX": 8999, "BR": 2999, "CL": 399990, "CO": 1899000, "AR": 749000}),
]


def cargar_ejemplos(con) -> int:
    db.asegurar_fuentes(con)
    for prod, tienda, medianas in PRODUCTOS:
        prov = db.proveedor_por_nombre(con, tienda) or {}
        pid = db.insertar(con, "productos", {**prod, "proveedor_id": prov.get("id")})
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
