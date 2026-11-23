"""Base de datos SQLite local (datos/base.sqlite)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .config import DATOS_DIR

RUTA_DB = DATOS_DIR / "base.sqlite"

ESTADOS_PROVEEDOR = ["sin contactar", "contactado", "respondió", "aprobado", "descartado"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT,
    pais TEXT,
    ciudad TEXT,
    web TEXT,
    email TEXT,
    whatsapp TEXT,
    contacto TEXT,
    idioma TEXT DEFAULT 'en',
    estado TEXT DEFAULT 'sin contactar',
    acepta_dropship TEXT DEFAULT '?',
    acepta_etiqueta_ml TEXT DEFAULT '?',
    dias_preparacion REAL,
    dias_transito_local REAL,
    corte_horario TEXT,
    pedido_minimo TEXT,
    condiciones TEXT,
    confiabilidad INTEGER DEFAULT 3,
    ultimo_contacto TEXT,
    proximo_seguimiento TEXT,
    notas TEXT,
    creado TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
    titulo TEXT NOT NULL,
    rubro TEXT,
    sku TEXT,
    marca TEXT,
    upc TEXT,
    url_proveedor TEXT,
    url_imagen TEXT,
    costo_usd REAL NOT NULL DEFAULT 0,
    envio_local_usd REAL DEFAULT 0,
    prep_usd REAL DEFAULT 0,
    peso_kg REAL DEFAULT 0,
    largo_cm REAL,
    ancho_cm REAL,
    alto_cm REAL,
    ruta TEXT DEFAULT 'directo',
    precio_venta_usd REAL,
    busqueda TEXT,
    riesgo TEXT,
    activo INTEGER DEFAULT 1,
    notas TEXT,
    creado TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS precios_mercado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
    pais TEXT NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    precio_min_local REAL,
    precio_mediana_local REAL,
    precio_max_local REAL,
    resultados INTEGER,
    internacionales INTEGER,
    categoria_id TEXT,
    fuente TEXT,
    url TEXT,
    notas TEXT
);
CREATE TABLE IF NOT EXISTS contactos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER REFERENCES proveedores(id) ON DELETE CASCADE,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    canal TEXT,
    direccion TEXT,
    mensaje TEXT,
    dias_informados REAL
);
CREATE TABLE IF NOT EXISTS publicaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
    pais TEXT,
    precio_usd REAL,
    dias_disponibilidad INTEGER,
    margen_pct REAL,
    estado TEXT DEFAULT 'borrador',
    item_id_ml TEXT,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    notas TEXT
);
"""

TABLAS = {"proveedores", "productos", "precios_mercado", "contactos", "publicaciones"}


def conectar(ruta: str | Path | None = None) -> sqlite3.Connection:
    ruta = Path(ruta or RUTA_DB)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def _tabla(tabla: str) -> str:
    if tabla not in TABLAS:
        raise ValueError(f"Tabla desconocida: {tabla}")
    return tabla


def columnas(con: sqlite3.Connection, tabla: str) -> list[str]:
    return [r["name"] for r in con.execute(f"PRAGMA table_info({_tabla(tabla)})")]


def filas(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, params)]


def todos(con: sqlite3.Connection, tabla: str, orden: str = "id") -> list[dict]:
    if orden not in columnas(con, tabla):
        orden = "id"
    return filas(con, f"SELECT * FROM {_tabla(tabla)} ORDER BY {orden}")


def uno(con: sqlite3.Connection, tabla: str, id_: int) -> dict | None:
    r = con.execute(f"SELECT * FROM {_tabla(tabla)} WHERE id = ?", (id_,)).fetchone()
    return dict(r) if r else None


def _limpiar(con, tabla, datos: dict) -> dict:
    validas = set(columnas(con, tabla)) - {"id"}
    return {k: (None if v == "" else v) for k, v in datos.items() if k in validas}


def insertar(con: sqlite3.Connection, tabla: str, datos: dict) -> int:
    datos = _limpiar(con, tabla, datos)
    cols = ", ".join(datos)
    marcas = ", ".join("?" for _ in datos)
    cur = con.execute(f"INSERT INTO {_tabla(tabla)} ({cols}) VALUES ({marcas})", tuple(datos.values()))
    con.commit()
    return cur.lastrowid


def actualizar(con: sqlite3.Connection, tabla: str, id_: int, datos: dict) -> None:
    datos = _limpiar(con, tabla, datos)
    if not datos:
        return
    asignaciones = ", ".join(f"{k} = ?" for k in datos)
    con.execute(f"UPDATE {_tabla(tabla)} SET {asignaciones} WHERE id = ?", (*datos.values(), id_))
    con.commit()


def borrar(con: sqlite3.Connection, tabla: str, id_: int) -> None:
    con.execute(f"DELETE FROM {_tabla(tabla)} WHERE id = ?", (id_,))
    con.commit()


def ultimos_precios(con: sqlite3.Connection, producto_id: int) -> dict[str, dict]:
    """Último relevamiento de precios por país para un producto."""
    salida: dict[str, dict] = {}
    for r in filas(con, "SELECT * FROM precios_mercado WHERE producto_id = ? ORDER BY fecha, id", (producto_id,)):
        salida[r["pais"]] = r
    return salida


def registrar_contacto(con: sqlite3.Connection, proveedor_id: int, canal: str, direccion: str,
                       mensaje: str, dias_informados: float | None = None,
                       dias_seguimiento: int = 3) -> None:
    hoy = date.today().isoformat()
    insertar(con, "contactos", {"proveedor_id": proveedor_id, "canal": canal, "direccion": direccion,
                                "mensaje": mensaje, "dias_informados": dias_informados})
    cambios: dict = {"ultimo_contacto": hoy}
    prov = uno(con, "proveedores", proveedor_id) or {}
    if direccion == "enviado":
        cambios["proximo_seguimiento"] = (date.today() + timedelta(days=dias_seguimiento)).isoformat()
        if prov.get("estado") in (None, "sin contactar"):
            cambios["estado"] = "contactado"
    else:
        cambios["proximo_seguimiento"] = None
        if prov.get("estado") in (None, "sin contactar", "contactado"):
            cambios["estado"] = "respondió"
        if dias_informados is not None:
            cambios["dias_preparacion"] = dias_informados
    actualizar(con, "proveedores", proveedor_id, cambios)


def seguimientos_pendientes(con: sqlite3.Connection) -> list[dict]:
    hoy = date.today().isoformat()
    return filas(con, "SELECT * FROM proveedores WHERE estado = 'contactado' AND proximo_seguimiento IS NOT NULL "
                      "AND proximo_seguimiento <= ? ORDER BY proximo_seguimiento", (hoy,))
