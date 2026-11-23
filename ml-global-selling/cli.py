"""Comandos para usar sin la interfaz (o para automatizar).

    python cli.py init                 crea la base de datos
    python cli.py demo                 carga datos de ejemplo
    python cli.py borrar-demo          borra los datos de ejemplo
    python cli.py analizar [--pais MX] [--excel salida.xlsx]
    python cli.py fx                   actualiza tipos de cambio
    python cli.py ml-url               muestra el link para autorizar la app de Mercado Libre
    python cli.py ml-codigo TG-xxxx    canjea el código por un token
    python cli.py escanear --producto 3 [--paises MX,CO]   trae precios de la competencia por API
    python cli.py escanear --texto "cable usb c 240w"      solo muestra, no guarda
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mlglobal import analisis, config, db, demo, fx  # noqa: E402
from mlglobal import mercadolibre as ml  # noqa: E402


def cmd_analizar(args, con):
    filas = analisis.analizar_todo(con, args.pais.split(",") if args.pais else None)
    if not filas:
        print("No hay productos cargados. Probá: python cli.py demo")
        return
    filas.sort(key=lambda f: -f["puntaje"])
    print(f"{'Producto':42} {'País':4} {'Precio':>8} {'Ganancia':>9} {'Margen':>7} {'Días':>4} {'Pts':>4}  Veredicto")
    for f in filas:
        print(f"{f['producto'][:42]:42} {f['pais']:4} {f['precio_usd']:8.2f} {f['ganancia_usd']:9.2f} "
              f"{f['margen_pct']:6.1f}% {f['dias_a_declarar']:4d} {f['puntaje']:4.0f}  {f['veredicto']}")
    if args.excel:
        import pandas as pd
        pd.DataFrame([{k: v for k, v in f.items() if k != "_detalle"} for f in filas]).to_excel(args.excel, index=False)
        print(f"\nGuardado en {args.excel}")


def cmd_escanear(args, con):
    paises = config.paises()
    codigos = args.paises.split(",") if args.paises else config.general()["paises_activos"]
    texto = args.texto
    if args.producto:
        prod = db.uno(con, "productos", args.producto)
        if not prod:
            sys.exit(f"No existe el producto {args.producto}")
        texto = texto or prod.get("busqueda") or prod["titulo"]
    if not texto:
        sys.exit("Indicá --producto o --texto")
    for c in codigos:
        cfg = paises[c]
        try:
            resumen = ml.resumir(ml.buscar(cfg["site_id"], texto))
        except ml.ErrorML as e:
            print(f"{c}: {e}\n    Cargalo a mano mirando {ml.url_listado(cfg, texto)}")
            continue
        if not resumen:
            print(f"{c}: sin resultados")
            continue
        print(f"{c}: mediana {resumen['precio_mediana_local']:,.0f} {cfg['moneda']} "
              f"(mín {resumen['precio_min_local']:,.0f}, máx {resumen['precio_max_local']:,.0f}, "
              f"{resumen['resultados']} resultados, {resumen['internacionales']} internacionales)")
        if args.producto:
            db.insertar(con, "precios_mercado", {**resumen, "producto_id": args.producto, "pais": c, "fuente": "api",
                                                 "url": ml.url_listado(cfg, texto)})


def main():
    ap = argparse.ArgumentParser(description="Analizador de productos para Mercado Libre Global Selling")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("demo")
    sub.add_parser("borrar-demo")
    a = sub.add_parser("analizar")
    a.add_argument("--pais")
    a.add_argument("--excel")
    sub.add_parser("fx")
    sub.add_parser("ml-url").add_argument("--dominio", default="https://auth.mercadolibre.com.ar")
    sub.add_parser("ml-codigo").add_argument("codigo")
    e = sub.add_parser("escanear")
    e.add_argument("--producto", type=int)
    e.add_argument("--texto")
    e.add_argument("--paises")
    args = ap.parse_args()

    con = db.conectar()
    if args.cmd == "init":
        print(f"Base lista en {db.RUTA_DB}")
    elif args.cmd == "demo":
        print(f"{demo.cargar_ejemplos(con)} productos de ejemplo cargados.")
    elif args.cmd == "borrar-demo":
        demo.borrar_ejemplos(con)
        print("Ejemplos borrados.")
    elif args.cmd == "analizar":
        cmd_analizar(args, con)
    elif args.cmd == "fx":
        for k, v in fx.actualizar_tipos_de_cambio().items():
            print(f"{k}: {v:,.4f}")
    elif args.cmd == "ml-url":
        print(ml.url_autorizacion(args.dominio))
    elif args.cmd == "ml-codigo":
        t = ml.canjear_codigo(args.codigo)
        print(f"Conectado. user_id={t.get('user_id')}")
    elif args.cmd == "escanear":
        cmd_escanear(args, con)


if __name__ == "__main__":
    main()
