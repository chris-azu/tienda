from fastapi import APIRouter, Depends, HTTPException, Query, Request
from uuid import UUID

from .. import schemas
from ..auth import requiere_sesion
from ..services import ventas_service

router = APIRouter(
    prefix="/api/ventas",
    tags=["ventas"],
    dependencies=[Depends(requiere_sesion)],
)


@router.post("", status_code=201)
def crear(datos: schemas.VentaCreate):
    return ventas_service.crear_venta(datos)


@router.get("")
def listar(rango: schemas.Rango = Query(default="hoy")):
    return ventas_service.ventas_rango(rango)


@router.get("/{venta_id}")
def detalle(venta_id: UUID):
    venta = ventas_service.obtener_venta(str(venta_id))
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta


@router.post("/{venta_id}/anular")
def anular(venta_id: UUID):
    return ventas_service.anular_venta(str(venta_id))
