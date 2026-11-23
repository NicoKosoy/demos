"""Búsqueda de ofertas en eBay (Browse API, gratis con una cuenta de developer.ebay.com).

Solo hace falta el App ID (Client ID) y el Cert ID (Client Secret) de producción: el token de aplicación
se pide solo y dura 2 horas. No hace falta iniciar sesión con tu usuario de eBay.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote, urlencode

import requests

from .config import DATOS_DIR

API = "https://api.ebay.com"
RUTA_CREDENCIALES = DATOS_DIR / "ebay_credenciales.json"
RUTA_TOKEN = DATOS_DIR / "ebay_token.json"


class ErrorEbay(Exception):
    pass


def credenciales() -> dict:
    return json.loads(RUTA_CREDENCIALES.read_text(encoding="utf-8")) if RUTA_CREDENCIALES.exists() else {}


def guardar_credenciales(client_id: str, client_secret: str) -> None:
    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    RUTA_CREDENCIALES.write_text(json.dumps({"client_id": client_id.strip(), "client_secret": client_secret.strip()}),
                                 encoding="utf-8")
    if RUTA_TOKEN.exists():
        RUTA_TOKEN.unlink()


def configurado() -> bool:
    c = credenciales()
    return bool(c.get("client_id") and c.get("client_secret"))


def _token() -> str:
    if RUTA_TOKEN.exists():
        t = json.loads(RUTA_TOKEN.read_text(encoding="utf-8"))
        if time.time() < t.get("expira", 0):
            return t["access_token"]
    c = credenciales()
    if not configurado():
        raise ErrorEbay("Faltan las credenciales de eBay (Configuración → Conexiones).")
    r = requests.post(f"{API}/identity/v1/oauth2/token", auth=(c["client_id"], c["client_secret"]), timeout=30,
                      data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"})
    if r.status_code != 200:
        raise ErrorEbay(f"eBay rechazó las credenciales ({r.status_code}): {r.text[:200]}")
    t = r.json()
    t["expira"] = time.time() + int(t.get("expires_in", 7200)) - 120
    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    RUTA_TOKEN.write_text(json.dumps(t), encoding="utf-8")
    return t["access_token"]


def _envio(item: dict) -> float | None:
    opciones = item.get("shippingOptions") or []
    if not opciones:
        return None
    costo = (opciones[0].get("shippingCost") or {}).get("value")
    if costo is None:
        return 0.0 if opciones[0].get("shippingCostType") == "FIXED" else None
    return float(costo)


def buscar(texto: str, precio_min: float = 50, precio_max: float = 500, solo_nuevos: bool = True,
           limite: int = 50, orden: str | None = None, zip_destino: str = "") -> list[dict]:
    filtros = [f"price:[{precio_min:g}..{precio_max:g}]", "priceCurrency:USD", "buyingOptions:{FIXED_PRICE}",
               "deliveryCountry:US"]
    if solo_nuevos:
        filtros.append("conditions:{NEW}")
    params = {"q": texto, "filter": ",".join(filtros), "limit": max(1, min(limite, 200))}
    if orden:
        params["sort"] = orden
    headers = {"Authorization": f"Bearer {_token()}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}
    if zip_destino:
        headers["X-EBAY-C-ENDUSERCTX"] = "contextualLocation=" + quote(f"country=US,zip={zip_destino}")
    r = requests.get(f"{API}/buy/browse/v1/item_summary/search", params=params, headers=headers, timeout=30)
    if r.status_code != 200:
        raise ErrorEbay(f"Error {r.status_code} buscando en eBay: {r.text[:200]}")
    salida = []
    for it in r.json().get("itemSummaries", []):
        precio = (it.get("price") or {}).get("value")
        if precio is None:
            continue
        vendedor = it.get("seller") or {}
        salida.append({
            "titulo": it.get("title"),
            "precio_usd": float(precio),
            "envio_usd": _envio(it),
            "condicion": it.get("condition"),
            "vendedor": vendedor.get("username"),
            "feedback_pct": float(vendedor["feedbackPercentage"]) if vendedor.get("feedbackPercentage") else None,
            "feedback_cantidad": vendedor.get("feedbackScore"),
            "url": it.get("itemWebUrl"),
            "imagen": (it.get("image") or {}).get("imageUrl"),
            "item_id": it.get("itemId"),
        })
    return salida


def links_busqueda(texto: str, precio_min: float = 50, precio_max: float = 500) -> dict[str, str]:
    """Búsquedas web con rango de precio y solo productos nuevos, para revisar a mano."""
    q = quote(texto)
    amazon_rh = quote(f"p_36:{int(precio_min * 100)}-{int(precio_max * 100)},p_n_condition-type:6461716011")
    return {
        "Amazon": f"https://www.amazon.com/s?k={q}&rh={amazon_rh}",
        "eBay": "https://www.ebay.com/sch/i.html?" + urlencode(
            {"_nkw": texto, "_udlo": f"{precio_min:g}", "_udhi": f"{precio_max:g}", "LH_ItemCondition": 1000,
             "LH_BIN": 1}),
        "Walmart": "https://www.walmart.com/search?" + urlencode(
            {"q": texto, "min_price": f"{precio_min:g}", "max_price": f"{precio_max:g}"}),
    }
