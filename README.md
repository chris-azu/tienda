# Tienda Joana

App web movil para una tienda de barrio: facturacion (venta, cobro, anulacion),
inventario con alertas de stock bajo y ganancia por venta.

## Requisitos

- Python 3.13+
- Un proyecto Supabase con las migraciones de `supabase/migrations/` aplicadas
  (se aplican desde el dashboard o con `supabase db push`).

## Configuracion

1. Copia `.env.example` a `.env` y completa los valores:

   - `SUPABASE_URL`: URL del proyecto (`https://<ref>.supabase.co`).
   - `SUPABASE_SERVICE_KEY`: clave secreta del servidor (Dashboard >
     Project Settings > API Keys). Nunca va al frontend.
   - `SESSION_SECRET`: aleatorio, minimo 32 caracteres
     (`python -c "import secrets; print(secrets.token_hex(32))"`).
   - `APP_PIN`: PIN de entrada; se siembra en `settings.pin_hash` la primera
     vez que arranca.
   - `TIMEZONE`: zona IANA (`America/Managua`).

2. Instala dependencias:

   python -m venv .venv
   .venv\Scripts\activate  (Windows) o source .venv/bin/activate
   pip install -r requirements.txt

## Arranque

uvicorn app.main:app --reload

- Vistas: `http://127.0.0.1:8000/` (redirige a `/login`).
- Health: `GET /health` → `{"status": "ok"}`.

## API

Todas las rutas `/api/*` requieren la sesion iniciada (cookie `session`);
sin ella responden `401`.

- `POST /auth/login` `{pin}` · `POST /auth/logout`
- `GET /api/productos?q=&bajo=` · `POST /api/productos`
- `PUT /api/productos/{id}` · `DELETE /api/productos/{id}` (borrado logico)
- `POST /api/productos/{id}/entrada` `{cantidad}`
- `GET /api/productos/alertas`
- `POST /api/ventas` `{items:[{product_id, cantidad, precio_unitario?}]}`
- `GET /api/ventas?rango=hoy|semana|mes` · `GET /api/ventas/{id}`
- `POST /api/ventas/{id}/anular`
- `GET /api/ganancias?rango=hoy|semana|mes`

La logica de stock/ganancia vive en funciones SQL `create_sale`,
`cancel_sale` y `add_stock` (migracion `0001_init.sql`), atomicas y de solo
uso del backend (service role).

## Despliegue en Render (plan gratis)

1. Sube el repo (privado) a GitHub.
2. En Render: **New → Web Service**, conecta el repo, rama `main`.
   - Runtime: **Python**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/health`
   - Plan: **Free**
   - La version de Python se fija con `runtime.txt` (`python-3.13.15`).
   - Tambien puedes usar el Blueprint `render.yaml`.
3. Variables de entorno en Render (nunca en git):
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SESSION_SECRET`, `APP_PIN`,
   `TIMEZONE=America/Managua`, `ENV=production`.
   - Con `ENV=production` la cookie de sesion se marca `Secure` (HTTPS).
   - Genera `SESSION_SECRET` con:
     `python -c "import secrets; print(secrets.token_hex(32))"`.
4. El plan free suspende el servicio tras ~15 min de inactividad; el primer
   acceso puede tardar ~30-60 s en reactivar.

## Base de datos

- Migraciones: `supabase/migrations/0001_init.sql` (esquema + RPCs),
  `0002_seed.sql` (settings + productos de ejemplo),
  `0003_sale_items_product_id_idx.sql` (indice de FK, paridad con el
  proyecto).
- RLS habilitado en todas las tablas sin politicas: solo el service role
  (backend) tiene acceso. Los valores derivados (`total`, `profit`,
  `status`, `stock`) se calculan en la BD, nunca en el cliente.
- El asesor de seguridad de Supabase reporta `rls_enabled_no_policy`
  (nivel INFO) en las 4 tablas: es intencional, el acceso pasa solo por el
  backend con la service key y las RPCs (`security definer`).
