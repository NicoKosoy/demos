"""Puntaje de oportunidad 0-100, transparente: cada parte se puede ver por separado."""
from __future__ import annotations


def _entre(x: float, bajo: float, alto: float) -> float:
    """0 en 'bajo', 1 en 'alto', lineal en el medio (sirve también con bajo > alto)."""
    if alto == bajo:
        return 1.0 if x >= alto else 0.0
    t = (x - bajo) / (alto - bajo)
    return max(0.0, min(1.0, t))


def calcular_puntaje(res: dict, demora: dict, riesgo: str, general: dict,
                     mediana_mercado_usd: float | None) -> dict:
    objetivo = float(general["margen_objetivo_pct"])
    g_min = float(general["ganancia_minima_usd"])
    partes = {
        "margen": 35 * _entre(res["margen_pct"], 0, objetivo * 1.6),
        "ganancia": 15 * _entre(res["ganancia_usd"], 0, g_min * 2.5),
        "valor_por_kg": 10 * _entre(res["precio_usd"] / max(res["peso_facturable_kg"], 0.05), 20, 150),
        "demora": 10 * _entre(demora["entrega_max"], 25, 10),
        "riesgo": {"bajo": 5, "medio": 2}.get(riesgo, 0),
    }
    if mediana_mercado_usd:
        relacion = res["precio_final_comprador_usd"] / mediana_mercado_usd
        partes["competencia"] = 25 * _entre(relacion, 1.3, 0.9)
    else:
        partes["competencia"] = 8  # sin datos: neutro tirando a bajo
    total = sum(partes.values())
    if riesgo == "alto":
        total -= 20
    total = round(max(0.0, min(100.0, total)), 0)

    if res["ganancia_usd"] <= 0:
        veredicto = "Pierde plata"
    elif res["margen_pct"] >= objetivo and res["ganancia_usd"] >= g_min and total >= 65:
        veredicto = "Publicar"
    elif total >= 45 and res["margen_pct"] > 0:
        veredicto = "Revisar"
    else:
        veredicto = "No conviene"
    return {"puntaje": total, "veredicto": veredicto, "partes": {k: round(v, 1) for k, v in partes.items()}}
