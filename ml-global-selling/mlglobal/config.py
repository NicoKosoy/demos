"""Carga de configuración: valores por defecto en config/ y cambios del usuario en datos/."""
from __future__ import annotations

import copy
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE / "config"
DATOS_DIR = BASE / "datos"


def _leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _fusionar(base: dict, extra: dict) -> dict:
    """Mezcla recursiva: los dicts se combinan, el resto (listas, números) se reemplaza."""
    salida = copy.deepcopy(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(salida.get(clave), dict):
            salida[clave] = _fusionar(salida[clave], valor)
        else:
            salida[clave] = copy.deepcopy(valor)
    return salida


def cargar(nombre: str) -> dict:
    datos = _leer(CONFIG_DIR / f"{nombre}.json")
    propio = DATOS_DIR / f"{nombre}.json"
    if propio.exists():
        datos = _fusionar(datos, _leer(propio))
    return datos


def guardar(nombre: str, datos: dict) -> Path:
    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = DATOS_DIR / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def restablecer(nombre: str) -> None:
    ruta = DATOS_DIR / f"{nombre}.json"
    if ruta.exists():
        ruta.unlink()


def paises() -> dict:
    return {k: v for k, v in cargar("paises").items() if not k.startswith("_")}


def general() -> dict:
    return cargar("general")


def rubros() -> list[dict]:
    return cargar("rubros")["rubros"]


def rubro(rubro_id: str | None) -> dict | None:
    return next((r for r in rubros() if r["id"] == rubro_id), None)


def guardar_cambios(nombre: str, cambios: dict) -> Path:
    """Mezcla 'cambios' con lo que ya guardaste antes (no pisa el resto de tus ajustes)."""
    ruta = DATOS_DIR / f"{nombre}.json"
    actual = _leer(ruta) if ruta.exists() else {}
    return guardar(nombre, _fusionar(actual, cambios))
