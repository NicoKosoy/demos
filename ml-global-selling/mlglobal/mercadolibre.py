"""Cliente mínimo de la API de Mercado Libre.

Desde 2025 casi todos los recursos (búsqueda, más vendidos, conversión de monedas) piden un access token.
Para tenerlo: crear una aplicación en https://developers.mercadolibre.com.ar/devcenter, copiar
Client ID y Client Secret, y autorizarla una vez (ver README). El token dura 6 horas y se renueva solo.
Sin token igual funciona el predictor de categorías.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

from .config import DATOS_DIR

API = "https://api.mercadolibre.com"
RUTA_TOKEN = DATOS_DIR / "ml_token.json"
RUTA_CREDENCIALES = DATOS_DIR / "ml_credenciales.json"


class ErrorML(Exception):
    pass


def _leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def _escribir(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2), encoding="utf-8")


def credenciales() -> dict:
    return _leer(RUTA_CREDENCIALES)


def guardar_credenciales(client_id: str, client_secret: str, redirect_uri: str) -> None:
    _escribir(RUTA_CREDENCIALES, {"client_id": client_id.strip(), "client_secret": client_secret.strip(),
                                  "redirect_uri": redirect_uri.strip()})


def url_autorizacion(dominio_auth: str = "https://auth.mercadolibre.com.ar") -> str:
    c = credenciales()
    if not c.get("client_id"):
        raise ErrorML("Faltan las credenciales de la aplicación (Client ID / Secret / Redirect URI).")
    return f"{dominio_auth}/authorization?" + urlencode(
        {"response_type": "code", "client_id": c["client_id"], "redirect_uri": c["redirect_uri"]})


def _pedir_token(datos: dict) -> dict:
    r = requests.post(f"{API}/oauth/token", data=datos, timeout=30,
                      headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        raise ErrorML(f"Mercado Libre rechazó el pedido de token ({r.status_code}): {r.text[:300]}")
    token = r.json()
    token["expira"] = time.time() + int(token.get("expires_in", 21600)) - 120
    _escribir(RUTA_TOKEN, token)
    return token


def canjear_codigo(codigo: str) -> dict:
    """El 'code' es lo que aparece en la URL después de autorizar: ...?code=TG-xxxx"""
    c = credenciales()
    codigo = codigo.strip()
    if "code=" in codigo:
        codigo = codigo.split("code=", 1)[1].split("&", 1)[0]
    return _pedir_token({"grant_type": "authorization_code", "client_id": c.get("client_id"),
                         "client_secret": c.get("client_secret"), "code": codigo,
                         "redirect_uri": c.get("redirect_uri")})


def token_valido() -> str | None:
    t = _leer(RUTA_TOKEN)
    if not t.get("access_token"):
        return None
    if time.time() < t.get("expira", 0):
        return t["access_token"]
    c = credenciales()
    if not (t.get("refresh_token") and c.get("client_id")):
        return None
    try:
        return _pedir_token({"grant_type": "refresh_token", "client_id": c["client_id"],
                             "client_secret": c["client_secret"], "refresh_token": t["refresh_token"]})["access_token"]
    except ErrorML:
        return None


def estado_token() -> dict:
    t = _leer(RUTA_TOKEN)
    return {"conectado": token_valido() is not None, "user_id": t.get("user_id"),
            "expira": t.get("expira")}


def _get(ruta: str, params: dict | None = None, con_token: bool = True) -> dict | list:
    headers = {"accept": "application/json"}
    if con_token:
        token = token_valido()
        if not token:
            raise ErrorML("Este recurso de Mercado Libre pide token. Conectá tu aplicación en Configuración.")
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{API}{ruta}", params=params, headers=headers, timeout=30)
    if r.status_code in (401, 403):
        raise ErrorML(f"Mercado Libre no autorizó {ruta} ({r.status_code}). Puede que tu app no tenga permiso "
                      f"para este recurso: cargá los precios a mano desde el link del listado.")
    if r.status_code != 200:
        raise ErrorML(f"Error {r.status_code} en {ruta}: {r.text[:200]}")
    return r.json()


def predecir_categoria(site_id: str, texto: str) -> dict | None:
    """Funciona sin token."""
    datos = _get(f"/sites/{site_id}/domain_discovery/search", {"q": texto, "limit": 1}, con_token=False)
    return datos[0] if datos else None


def _es_internacional(item: dict) -> bool:
    etiquetas = [str(t).lower() for t in (item.get("tags") or []) + ((item.get("shipping") or {}).get("tags") or [])]
    modo = str(item.get("international_delivery_mode") or "none").lower()
    return any("cbt" in t or "international" in t for t in etiquetas) or modo not in ("none", "")


def buscar(site_id: str, texto: str, limite: int = 50) -> list[dict]:
    datos = _get(f"/sites/{site_id}/search", {"q": texto, "limit": min(limite, 50)})
    salida = []
    for it in datos.get("results", []):
        if it.get("price") is None:
            continue
        salida.append({
            "titulo": it.get("title"),
            "precio": float(it["price"]),
            "moneda": it.get("currency_id"),
            "condicion": it.get("condition"),
            "envio_gratis": bool((it.get("shipping") or {}).get("free_shipping")),
            "internacional": _es_internacional(it),
            "vendedor_id": (it.get("seller") or {}).get("id"),
            "categoria_id": it.get("category_id"),
            "link": it.get("permalink"),
        })
    return salida


def resumir(items: list[dict]) -> dict:
    nuevos = [i for i in items if i.get("condicion") in (None, "new")] or items
    precios = sorted(i["precio"] for i in nuevos)
    if not precios:
        return {}
    categorias = [i["categoria_id"] for i in nuevos if i.get("categoria_id")]
    return {
        "precio_min_local": precios[0],
        "precio_mediana_local": statistics.median(precios),
        "precio_max_local": precios[-1],
        "resultados": len(precios),
        "internacionales": sum(1 for i in nuevos if i.get("internacional")),
        "categoria_id": max(set(categorias), key=categorias.count) if categorias else None,
    }


def url_listado(cfg_pais: dict, texto: str) -> str:
    slug = "-".join(texto.strip().lower().split())
    return cfg_pais.get("url_listado", "https://listado.mercadolibre.com.ar/") + quote(slug)
