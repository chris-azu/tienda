from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..auth import requiere_sesion
from ..services import ventas_service

router = APIRouter(
    prefix="/api/ganancias",
    tags=["ganancias"],
    dependencies=[Depends(requiere_sesion)],
)


@router.get("")
def ganancias(rango: schemas.Rango = Query(default="hoy")):
    return ventas_service.ganancias_rango(rango)
