from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from .. import config, db
from ..schemas import VentaCreate

DOS_DECIMALES = Decimal("0.01")


def dinero(valor) -> float:
    return float(Decimal(str(valor)).quantize(DOS_DECIMALES, ROUND_HALF_UP))


def inicio_rango(rango: str) -> datetime:
    """Inicio local (medianoche) del rango, en hora de America/Managua."""
    ahora = datetime.now(config.TZ)
    if rango == "hoy":
        inicio = datetime.combine(ahora.date(), time.min, tzinfo=config.TZ)
    elif rango == "semana":
        lunes = ahora.date() - timedelta(days=ahora.weekday())
        inicio = datetime.combine(lunes, time.min, tzinfo=config.TZ)
    elif rango == "mes":
        inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError("Rango invalido. Usa: hoy, semana o mes")
    return inicio


def _iso_utc(valor: datetime) -> str:
    return valor.astimezone(timezone.utc).isoformat()


def ventas_rango(rango: str) -> list[dict]:
    inicio = inicio_rango(rango)
    filas = (
        db.get_db()
        .table("sales")
        .select("*, sale_items(quantity)")
        .gte("created_at", _iso_utc(inicio))
        .order("created_at", desc=True)
        .execute()
        .data
    )
    salida = []
    for fila in filas:
        renglones = fila.pop("sale_items", []) or []
        fila["items_count"] = sum(int(r.get("quantity") or 0) for r in renglones)
        salida.append(fila)
    return salida


def obtener_venta(venta_id: str) -> Optional[dict]:
    filas = (
        db.get_db()
        .table("sales")
        .select("*, sale_items(*)")
        .eq("id", venta_id)
        .limit(1)
        .execute()
        .data
    )
    if not filas:
        return None
    venta = filas[0]
    venta["items"] = venta.pop("sale_items", [])
    return venta


def ganancias_rango(rango: str) -> dict:
    inicio = inicio_rango(rango)
    filas = (
        db.get_db()
        .table("sales")
        .select("total, profit")
        .eq("status", "completada")
        .gte("created_at", _iso_utc(inicio))
        .execute()
        .data
    )
    vendido = sum((Decimal(str(f["total"])) for f in filas), Decimal("0"))
    ganancia = sum((Decimal(str(f["profit"])) for f in filas), Decimal("0"))
    return {
        "rango": rango,
        "vendido": dinero(vendido),
        "ganancia": dinero(ganancia),
        "cantidad_ventas": len(filas),
    }


def _a_jsonb(item) -> dict:
    dato = {
        "product_id": str(item.product_id),
        "cantidad": str(item.cantidad),
    }
    if item.precio_unitario is not None:
        dato["precio_unitario"] = str(item.precio_unitario)
    return dato


def crear_venta(datos: VentaCreate) -> dict:
    items = [_a_jsonb(i) for i in datos.items]
    try:
        return (
            db.get_db()
            .rpc("create_sale", {"items": items})
            .execute()
            .data
        )
    except Exception as e:
        raise db.http_desde_error_db(e) from e


def anular_venta(venta_id: str) -> dict:
    try:
        return (
            db.get_db()
            .rpc("cancel_sale", {"sale_id": venta_id})
            .execute()
            .data
        )
    except Exception as e:
        raise db.http_desde_error_db(e) from e


def lista_productos(q: Optional[str], solo_bajos: bool) -> list[dict]:
    consulta = (
        db.get_db()
        .table("products")
        .select("*")
        .eq("active", True)
        .order("name")
    )
    if q:
        consulta = consulta.ilike("name", f"%{q}%")
    filas = consulta.execute().data
    if solo_bajos:
        filas = [
            f
            for f in filas
            if Decimal(str(f["stock"])) <= Decimal(str(f["min_stock"]))
        ]
    return filas


def alertas_stock() -> dict:
    bajos = lista_productos(None, True)
    return {"conteo": len(bajos), "productos": bajos}
