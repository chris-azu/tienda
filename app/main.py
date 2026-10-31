import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, config
from .auth import router as auth_router
from .routers import ganancias, productos, ventas

logger = logging.getLogger("tienda")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        auth.ensure_pin_hash()
    except Exception:
        logger.warning(
            "No se pudo sembrar el PIN en tienda_settings; "
            "se reintentara en el primer login.",
            exc_info=True,
        )
    yield


app = FastAPI(title="Tienda Joana", lifespan=lifespan)

BASE_DIR = config.BASE_DIR
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth_router)
app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(ganancias.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validacion_handler(request: Request, exc: RequestValidationError):
    errores = []
    for error in exc.errors():
        campo = " -> ".join(str(p) for p in error.get("loc", []))
        tipo = error.get("type", "")
        if tipo == "missing":
            mensaje = "es obligatorio"
        elif "greater" in tipo or "positive" in tipo:
            mensaje = "debe ser un valor valido"
        else:
            mensaje = "valor invalido"
        errores.append(f"{campo} {mensaje}")
    detalle = "Datos invalidos: " + "; ".join(errores) if errores else "Datos invalidos"
    return JSONResponse(status_code=422, content={"detail": detalle})


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception):
    logger.exception("Error interno en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"detail": "Error interno del servidor"}
    )


def _requiere_vista(request: Request, destino: str) -> RedirectResponse | None:
    if not auth.hay_sesion(request):
        return RedirectResponse(url=destino, status_code=303)
    return None


@app.get("/")
def raiz(request: Request):
    if not auth.hay_sesion(request):
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/vender", status_code=303)


@app.get("/login")
def vista_login(request: Request):
    if auth.hay_sesion(request):
        return RedirectResponse(url="/vender", status_code=303)
    return templates.TemplateResponse(request, "login.html", {})


@app.get("/vender")
def vista_vender(request: Request):
    salida = _requiere_vista(request, "/login")
    if salida:
        return salida
    return templates.TemplateResponse(request, "vender.html", {})


@app.get("/inventario")
def vista_inventario(request: Request):
    salida = _requiere_vista(request, "/login")
    if salida:
        return salida
    return templates.TemplateResponse(request, "inventario.html", {})


@app.get("/ganancias")
def vista_ganancias(request: Request):
    salida = _requiere_vista(request, "/login")
    if salida:
        return salida
    return templates.TemplateResponse(request, "ganancias.html", {})


@app.get("/recibo")
def vista_recibo(request: Request):
    salida = _requiere_vista(request, "/login")
    if salida:
        return salida
    return templates.TemplateResponse(request, "recibo.html", {})
