from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

Rango = Literal["hoy", "semana", "mes"]

DINERO = dict(max_digits=12, decimal_places=2)
CANTIDAD = dict(max_digits=12, decimal_places=3)


class LoginIn(BaseModel):
    pin: str = Field(min_length=1, max_length=32)


class ProductoCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cost: Decimal = Field(**DINERO, ge=0)
    price: Decimal = Field(**DINERO, ge=0)
    stock: Decimal = Field(default=Decimal("0"), **CANTIDAD, ge=0)
    min_stock: Decimal = Field(default=Decimal("5"), **CANTIDAD, ge=0)
    unit: str = Field(default="unidad", min_length=1, max_length=30)


class ProductoUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    cost: Optional[Decimal] = Field(default=None, **DINERO, ge=0)
    price: Optional[Decimal] = Field(default=None, **DINERO, ge=0)
    stock: Optional[Decimal] = Field(default=None, **CANTIDAD, ge=0)
    min_stock: Optional[Decimal] = Field(default=None, **CANTIDAD, ge=0)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=30)

    def campos(self) -> dict:
        return {
            k: v for k, v in self.model_dump(exclude_none=True).items()
        }


class EntradaStock(BaseModel):
    cantidad: Decimal = Field(**CANTIDAD, gt=0)


class VentaItemIn(BaseModel):
    product_id: UUID
    cantidad: Decimal = Field(**CANTIDAD, gt=0)
    precio_unitario: Optional[Decimal] = Field(default=None, **DINERO, ge=0)


class VentaCreate(BaseModel):
    items: list[VentaItemIn] = Field(min_length=1)
