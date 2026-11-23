"""Fichas de publicación para Global Selling y alta por API.

Categoría y atributos obligatorios se consultan sin token (sitio CBT = Global Selling).
Publicar sí necesita tu cuenta de Global Selling conectada (token con permiso de escritura).
"""
from __future__ import annotations

from functools import lru_cache

import requests

from . import mercadolibre as ml

API = "https://api.mercadolibre.com"


@lru_cache(maxsize=512)
def categoria_global(texto: str) -> dict:
    try:
        r = requests.get(f"{API}/sites/CBT/domain_discovery/search", params={"q": texto, "limit": 1}, timeout=20)
        datos = r.json() if r.status_code == 200 else []
    except requests.RequestException:
        datos = []
    return datos[0] if datos else {}


@lru_cache(maxsize=512)
def atributos_requeridos(categoria_id: str) -> tuple[str, ...]:
    try:
        r = requests.get(f"{API}/categories/{categoria_id}/attributes", timeout=20)
        datos = r.json() if r.status_code == 200 else []
    except requests.RequestException:
        datos = []
    return tuple(a["id"] for a in datos if (a.get("tags") or {}).get("required"))


def armar_ficha(prod: dict, filas: list[dict]) -> dict:
    """Una fila por producto con todo lo que pide la publicación, más el precio sugerido por país."""
    texto = prod.get("titulo_en") or prod.get("busqueda") or prod["titulo"]
    cat = categoria_global(texto)
    dims = [prod.get(k) for k in ("largo_cm", "ancho_cm", "alto_cm")]
    ficha = {
        "producto_id": prod["id"],
        "titulo_en": (prod.get("titulo_en") or "")[:60],
        "titulo_es": prod["titulo"][:60],
        "marca": prod.get("marca") or "",
        "modelo": prod.get("modelo") or "",
        "upc": prod.get("upc") or "",
        "condicion": "new",
        "categoria_cbt": cat.get("category_id", ""),
        "categoria_nombre": cat.get("category_name", ""),
        "atributos_obligatorios": ", ".join(atributos_requeridos(cat["category_id"])) if cat.get("category_id") else "",
        "peso_kg": prod.get("peso_kg"),
        "caja_cm": " x ".join(f"{d:g}" for d in dims) if all(dims) else "",
        "logistica": prod.get("ruta") or "",
        "comprar_en": prod.get("fuente_compra") or "",
        "link_compra": prod.get("url_proveedor") or "",
        "costo_usd": prod.get("costo_usd"),
    }
    for f in filas:
        if f["producto_id"] != prod["id"]:
            continue
        c = f["pais"]
        precio = max(f["precio_usd"], f["precio_minimo_usd"] or 0)
        ficha[f"precio_usd_{c}"] = round(precio, 2)
        ficha[f"dias_{c}"] = f["dias_a_declarar"]
        ficha[f"equilibrio_comprador_{c}"] = f["equilibrio_final_comprador_local"]
        ficha[f"objetivo_comprador_{c}"] = f["minimo_final_comprador_local"]
    return ficha


def payload_global_item(prod: dict, ficha: dict, paises: list[str], site_ids: dict[str, str],
                        stock: int = 2, imagenes: list[str] | None = None) -> dict:
    """Cuerpo para POST /global/items. Global Selling pide el título en inglés.

    Mercado Libre no tiene sandbox: probalo con UN producto y ajustá según el error que devuelva
    (suele pedir atributos extra de la categoría o fotos).
    """
    atributos = [{"id": "BRAND", "value_name": ficha["marca"]}, {"id": "MODEL", "value_name": ficha["modelo"]},
                 {"id": "ITEM_CONDITION", "value_name": "New"}]
    if ficha["upc"]:
        atributos.append({"id": "GTIN", "value_name": str(ficha["upc"])})
    if prod.get("peso_kg"):
        atributos.append({"id": "PACKAGE_WEIGHT", "value_name": f"{prod['peso_kg'] * 1000:.0f} g"})
    for clave, attr in (("largo_cm", "PACKAGE_LENGTH"), ("ancho_cm", "PACKAGE_WIDTH"), ("alto_cm", "PACKAGE_HEIGHT")):
        if prod.get(clave):
            atributos.append({"id": attr, "value_name": f"{prod[clave]:g} cm"})
    dias = max([ficha.get(f"dias_{c}") or 0 for c in paises] or [0])
    precio = max([ficha.get(f"precio_usd_{c}") or 0 for c in paises] or [0])
    cuerpo = {
        "title": ficha["titulo_en"] or ficha["titulo_es"],
        "category_id": ficha["categoria_cbt"],
        "price": precio,
        "currency_id": "USD",
        "available_quantity": stock,
        "buying_mode": "buy_it_now",
        "listing_type_id": "gold_pro",
        "condition": "new",
        "pictures": [{"source": u} for u in (imagenes or [])],
        "attributes": [a for a in atributos if a["value_name"]],
        "sites_to_sell": [{"site_id": site_ids[c], "logistic_type": "remote"} for c in paises],
    }
    if dias:
        cuerpo["sale_terms"] = [{"id": "MANUFACTURING_TIME", "value_name": f"{dias} days"}]
    return cuerpo


def publicar(cuerpo: dict) -> dict:
    token = ml.token_valido()
    if not token:
        raise ml.ErrorML("Conectá tu cuenta de Global Selling en Configuración → Conexiones antes de publicar.")
    r = requests.post(f"{API}/global/items", json=cuerpo, timeout=60,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    if r.status_code not in (200, 201):
        raise ml.ErrorML(f"Mercado Libre rechazó la publicación ({r.status_code}): {r.text[:800]}")
    return r.json()
