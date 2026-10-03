import os
import httpx

TOKEN = os.getenv("CF_API_TOKEN")
ZONE_ID = os.getenv("CF_ZONE_ID")

BASE_URL = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"


class CloudflareError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def _error_text(data):
    errors = data.get("errors") or []
    if not errors:
        return "Cloudflare rechazó la solicitud."

    return " | ".join(
        str(item.get("message", item))
        for item in errors
    )


async def crear_registro(tipo: str, nombre: str, contenido: str, proxied=False):
    payload = {
        "type": tipo,
        "name": nombre,
        "content": contenido,
        "ttl": 1,
    }

    # NS no utiliza proxy de Cloudflare.
    if tipo in {"A", "AAAA", "CNAME"}:
        payload["proxied"] = bool(proxied)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            BASE_URL,
            headers=_headers(),
            json=payload,
        )

    try:
        data = response.json()
    except ValueError:
        raise CloudflareError(
            f"Respuesta no válida de Cloudflare (HTTP {response.status_code})."
        )

    if not response.is_success or not data.get("success"):
        raise CloudflareError(_error_text(data))

    return data["result"]
  
