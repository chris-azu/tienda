import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import config, db
from .schemas import LoginIn

_PBKDF2_ITERATIONS = 260_000
_serializer = URLSafeTimedSerializer(config.SESSION_SECRET, salt="tienda-session")

_fallos: dict[str, dict] = {}


def hash_pin(pin: str) -> str:
    sal = os.urandom(16)
    digesto = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), sal, _PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ITERATIONS, sal.hex(), digesto.hex()
    )


def verify_pin(pin: str, guardado: str) -> bool:
    try:
        _, iteraciones, sal_hex, digesto_hex = guardado.split("$")
        digesto = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            bytes.fromhex(sal_hex),
            int(iteraciones),
        )
        return hmac.compare_digest(digesto.hex(), digesto_hex)
    except (ValueError, TypeError):
        return False


def ensure_pin_hash() -> None:
    """Si settings.pin_hash esta vacio, lo siembra desde APP_PIN."""
    client = db.get_db()
    fila = client.table("settings").select("pin_hash").limit(1).execute().data
    if fila and not fila[0].get("pin_hash"):
        client.table("settings").update(
            {"pin_hash": hash_pin(config.APP_PIN)}
        ).neq("id", 0).execute()


def set_session(response: Response) -> None:
    token = _serializer.dumps({"ok": 1})
    response.set_cookie(
        config.SESSION_COOKIE,
        token,
        max_age=config.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=config.SESSION_COOKIE_SECURE,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE, path="/")


def hay_sesion(request: Request) -> bool:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=config.SESSION_MAX_AGE)
        return True
    except BadSignature:
        return False


def requiere_sesion(request: Request) -> None:
    if not hay_sesion(request):
        raise HTTPException(status_code=401, detail="Sesion requerida")


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def _bloqueo(ip: str) -> int:
    """Segundos restantes de bloqueo (0 si no esta bloqueada)."""
    registro = _fallos.get(ip)
    if not registro:
        return 0
    if registro["bloqueado_hasta"] <= 0:
        return 0
    restantes = int(registro["bloqueado_hasta"] - time.monotonic())
    if restantes <= 0:
        _fallos.pop(ip, None)
        return 0
    return restantes


def _registrar_fallo(ip: str) -> int:
    registro = _fallos.setdefault(ip, {"intentos": 0, "bloqueado_hasta": 0.0})
    registro["intentos"] += 1
    if registro["intentos"] >= config.LOGIN_MAX_ATTEMPTS:
        registro["bloqueado_hasta"] = (
            time.monotonic() + config.LOGIN_BLOCK_SECONDS
        )
        return config.LOGIN_BLOCK_SECONDS
    return 0


def _limpiar(ip: str) -> None:
    _fallos.pop(ip, None)


router = APIRouter(tags=["auth"])


@router.post("/auth/login")
def login(datos: LoginIn, request: Request, response: Response):
    ip = _ip(request)
    restantes = _bloqueo(ip)
    if restantes:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Intenta de nuevo en {restantes} segundos",
        )

    ensure_pin_hash()
    fila = (
        db.get_db()
        .table("settings")
        .select("pin_hash")
        .limit(1)
        .execute()
        .data
    )
    pin_hash = fila[0].get("pin_hash") if fila else None
    if not pin_hash or not verify_pin(datos.pin, pin_hash):
        bloqueo = _registrar_fallo(ip)
        if bloqueo:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Demasiados intentos. "
                    f"Intenta de nuevo en {bloqueo} segundos"
                ),
            )
        raise HTTPException(status_code=401, detail="PIN incorrecto")

    _limpiar(ip)
    set_session(response)
    return {"ok": True}


@router.post("/auth/logout")
def logout(response: Response):
    clear_session(response)
    return {"ok": True}
