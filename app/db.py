from functools import lru_cache

from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client, create_client
from supabase._sync.client import SupabaseException

from . import config


@lru_cache(maxsize=1)
def get_db() -> Client:
    try:
        return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    except SupabaseException as e:
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible: revisa SUPABASE_SERVICE_KEY en .env",
        ) from e


def _mensaje(e: Exception) -> str:
    if isinstance(e, APIError):
        return e.message or str(e) or ""
    return str(e)


def _codigo(e: Exception) -> str:
    if isinstance(e, APIError):
        return e.code or ""
    return ""


def http_desde_error_db(e: Exception) -> HTTPException:
    """Traduce errores de Supabase/PostgREST a HTTPException con mensaje en
    espanol. Los mensajes que no reconocemos nunca se filtran al cliente."""
    msg = _mensaje(e)
    codigo = _codigo(e)

    if codigo == "23505" or "duplicate key" in msg:
        return HTTPException(
            status_code=409,
            detail="Ya existe un producto con ese nombre",
        )
    if msg.startswith("Stock insuficiente"):
        return HTTPException(status_code=409, detail=msg)
    if msg == "La venta ya esta anulada":
        return HTTPException(status_code=409, detail=msg)
    if msg == "Producto no encontrado" or msg == "Venta no encontrada":
        return HTTPException(status_code=404, detail=msg)

    mensajes_propios = (
        "La venta",
        "Cada producto",
        "El producto",
        "El precio",
        "La cantidad",
        "Producto",
        "Venta",
        "Ya existe",
    )
    if any(msg.startswith(prefijo) for prefijo in mensajes_propios):
        return HTTPException(status_code=400, detail=msg)

    raise e
