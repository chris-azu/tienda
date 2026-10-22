from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID

from .. import db, schemas
from ..auth import requiere_sesion
from ..services import ventas_service

router = APIRouter(
    prefix="/api/productos",
    tags=["productos"],
    dependencies=[Depends(requiere_sesion)],
)


@router.get("")
def listar(q: str = "", bajo: bool = False):
    return ventas_service.lista_productos(q or None, bajo)


@router.get("/alertas")
def alertas():
    return ventas_service.alertas_stock()


def _verificar_nombre(nombre: str, excluir_id: str = None) -> None:
    consulta = (
        db.get_db()
        .table("products")
        .select("id")
        .eq("active", True)
        .ilike("name", nombre)
    )
    if excluir_id:
        consulta = consulta.neq("id", excluir_id)
    if consulta.limit(1).execute().data:
        raise HTTPException(
            status_code=409, detail="Ya existe un producto con ese nombre"
        )


@router.post("", status_code=201)
def crear(datos: schemas.ProductoCreate):
    _verificar_nombre(datos.name)
    try:
        fila = (
            db.get_db()
            .table("products")
            .insert(
                {
                    "name": datos.name,
                    "cost": str(datos.cost),
                    "price": str(datos.price),
                    "stock": str(datos.stock),
                    "min_stock": str(datos.min_stock),
                    "unit": datos.unit,
                }
            )
            .execute()
            .data
        )
    except Exception as e:
        raise db.http_desde_error_db(e) from e
    return fila[0]


@router.put("/{producto_id}")
def editar(producto_id: UUID, datos: schemas.ProductoUpdate):
    campos = datos.campos()
    if not campos:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    existe = (
        db.get_db()
        .table("products")
        .select("id, name")
        .eq("id", str(producto_id))
        .eq("active", True)
        .limit(1)
        .execute()
        .data
    )
    if not existe:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if "name" in campos:
        _verificar_nombre(campos["name"], str(producto_id))
    for campo in ("cost", "price", "stock", "min_stock"):
        if campo in campos:
            campos[campo] = str(campos[campo])
    try:
        fila = (
            db.get_db()
            .table("products")
            .update(campos)
            .eq("id", str(producto_id))
            .execute()
            .data
        )
    except Exception as e:
        raise db.http_desde_error_db(e) from e
    if not fila:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return fila[0]


@router.delete("/{producto_id}")
def eliminar(producto_id: UUID):
    fila = (
        db.get_db()
        .table("products")
        .update({"active": False})
        .eq("id", str(producto_id))
        .eq("active", True)
        .execute()
        .data
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"ok": True}


@router.post("/{producto_id}/entrada")
def entrada_stock(producto_id: UUID, datos: schemas.EntradaStock):
    try:
        resultado = (
            db.get_db()
            .rpc(
                "add_stock",
                {"product_id": str(producto_id), "qty": str(datos.cantidad)},
            )
            .execute()
            .data
        )
    except Exception as e:
        raise db.http_desde_error_db(e) from e
    return {
        "id": producto_id,
        "stock": float(Decimal(str(resultado["stock"]))),
    }
