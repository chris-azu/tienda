-- Tabla de ajustes propia de Tienda Joana.
-- La tabla public.settings quedo en uso por otra app del mismo proyecto
-- Supabase (esquema key/value), por eso Tienda usa su propia tabla.

create table if not exists public.tienda_settings (
  id                boolean primary key default true check (id),
  pin_hash          text,
  low_stock_default numeric(12,3) not null default 5 check (low_stock_default >= 0)
);

alter table public.tienda_settings enable row level security;

insert into public.tienda_settings (id, pin_hash, low_stock_default)
values (true, null, 5)
on conflict (id) do nothing;
