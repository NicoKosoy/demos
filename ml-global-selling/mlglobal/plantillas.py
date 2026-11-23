"""Mensajes para pedirle a cada proveedor la demora de despacho y las condiciones."""
from __future__ import annotations

import re
from urllib.parse import quote

PLANTILLAS = {
    "en": {
        "primer_contacto": {
            "asunto": "Wholesale / dropship inquiry - {empresa}",
            "cuerpo": """Hi {contacto},

We are {empresa}, an online retailer selling on Mercado Libre (the largest marketplace in Latin America) through its Global Selling program, shipping to Mexico, Brazil, Chile, Colombia and Argentina.

We would like to carry these products of yours:
{productos}

Could you please tell us:
1. Handling time: how many business days from order to shipment? What is your daily cut-off time?
2. Can you ship single units to a US address we provide, using a prepaid label we send you? Is shipping blind (no prices or invoice in the box)?
3. Your wholesale / dropship price for these items and any minimum order.
4. Do you have a stock feed (CSV, spreadsheet or API) so we never sell out-of-stock items?
5. Payment terms, and whether you need a resale certificate.
6. Your policy for defective units and returns.

Thank you,
{firma}
{empresa}""",
        },
        "seguimiento": {
            "asunto": "Re: Wholesale / dropship inquiry - {empresa}",
            "cuerpo": """Hi {contacto},

Just following up on my previous message. The key thing we need is your handling time (business days from order to shipment) for:
{productos}

If you can ship single units with our prepaid label, we can start with a first test order this week.

Thanks,
{firma}
{empresa}""",
        },
        "whatsapp": {
            "asunto": "",
            "cuerpo": "Hi {contacto}! This is {firma} from {empresa}. We sell on Mercado Libre (Latin America) and would like to resell: {productos_linea}. How many business days do you need from order to shipment? Can you ship single units with our prepaid label? Thanks!",
        },
    },
    "es": {
        "primer_contacto": {
            "asunto": "Consulta mayorista / dropshipping - {empresa}",
            "cuerpo": """Hola {contacto}:

Somos {empresa}, vendemos en Mercado Libre a través de su programa Global Selling, con envíos a México, Brasil, Chile, Colombia y Argentina.

Nos interesa revender estos productos suyos:
{productos}

¿Nos podrían indicar?
1. Demora de despacho: ¿cuántos días hábiles pasan desde el pedido hasta el envío? ¿Hasta qué hora toman pedidos en el día?
2. ¿Pueden enviar unidades sueltas a una dirección que les indiquemos, con una etiqueta prepaga que les mandamos? ¿El envío va sin precios ni factura adentro?
3. Precio mayorista / dropshipping de estos productos y pedido mínimo, si hay.
4. ¿Tienen un listado de stock actualizado (planilla, CSV o API) para no vender sin stock?
5. Forma y plazos de pago.
6. Política de garantía y devoluciones.

Muchas gracias,
{firma}
{empresa}""",
        },
        "seguimiento": {
            "asunto": "Re: Consulta mayorista / dropshipping - {empresa}",
            "cuerpo": """Hola {contacto}:

Retomo mi mensaje anterior. Lo principal que necesitamos saber es la demora de despacho (días hábiles desde el pedido hasta el envío) de:
{productos}

Si pueden enviar unidades sueltas con nuestra etiqueta prepaga, podemos arrancar con un pedido de prueba esta semana.

Gracias,
{firma}
{empresa}""",
        },
        "whatsapp": {
            "asunto": "",
            "cuerpo": "¡Hola {contacto}! Soy {firma}, de {empresa}. Vendemos en Mercado Libre (Latinoamérica) y queremos revender: {productos_linea}. ¿Cuántos días hábiles necesitan desde el pedido hasta el envío? ¿Pueden despachar unidades sueltas con nuestra etiqueta prepaga? ¡Gracias!",
        },
    },
}

TIPOS = {"primer_contacto": "Primer contacto (email)", "seguimiento": "Seguimiento (email)",
         "whatsapp": "WhatsApp corto"}


def armar(tipo: str, idioma: str, proveedor: dict, productos: list[dict], general: dict) -> dict:
    plantilla = PLANTILLAS.get(idioma, PLANTILLAS["en"])[tipo]
    nombres = [p["titulo"] + (f" (SKU {p['sku']})" if p.get("sku") else "") for p in productos] or ["(products)"]
    valores = {
        "empresa": general.get("empresa", ""),
        "firma": general.get("firma", ""),
        "contacto": proveedor.get("contacto") or ("team" if idioma == "en" else "equipo"),
        "productos": "\n".join(f"- {n}" for n in nombres),
        "productos_linea": "; ".join(nombres),
    }
    return {"asunto": plantilla["asunto"].format(**valores), "cuerpo": plantilla["cuerpo"].format(**valores)}


def link_email(email: str, asunto: str, cuerpo: str) -> str:
    return f"mailto:{email or ''}?subject={quote(asunto)}&body={quote(cuerpo)}"


def link_whatsapp(numero: str, texto: str) -> str:
    digitos = re.sub(r"\D", "", numero or "")
    return f"https://wa.me/{digitos}?text={quote(texto)}"
