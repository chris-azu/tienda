-- Tienda: esquema base (productos, ventas, detalles, ajustes)

create table if not exists public.products (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  cost        numeric(12,2) not null default 0 check (cost >= 0),
  price       numeric(12,2) not null default 0 check (price >= 0),
  stock       numeric(12,3) not null default 0 check (stock >= 0),
  min_stock   numeric(12,3) not null default 5 check (min_stock >= 0),
  unit        text not null default 'unidad',
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create unique index if not exists products_active_lower_name_key
  on public.products (lower(name)) where active;

create index if not exists products_active_stock_idx
  on public.products (active, stock);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists products_set_updated_at on public.products;
create trigger products_set_updated_at
  before update on public.products
  for each row
  execute function public.set_updated_at();

create table if not exists public.sales (
  id           uuid primary key default gen_random_uuid(),
  created_at   timestamptz not null default now(),
  total        numeric(12,2) not null default 0,
  profit       numeric(12,2) not null default 0,
  status       text not null default 'completada'
               check (status in ('completada', 'anulada')),
  cancelled_at timestamptz
);

create index if not exists sales_created_at_idx
  on public.sales (created_at);

create table if not exists public.sale_items (
  id           uuid primary key default gen_random_uuid(),
  sale_id      uuid not null references public.sales (id) on delete cascade,
  product_id   uuid not null references public.products (id),
  product_name text not null,
  quantity     numeric(12,3) not null check (quantity > 0),
  unit_price   numeric(12,2) not null check (unit_price >= 0),
  unit_cost    numeric(12,2) not null check (unit_cost >= 0)
);

create index if not exists sale_items_sale_id_idx
  on public.sale_items (sale_id);

create table if not exists public.settings (
  id                boolean primary key default true check (id),
  pin_hash          text,
  low_stock_default numeric(12,3) not null default 5 check (low_stock_default >= 0)
);

-- RLS activo sin politicas: solo el backend (service key) accede.
alter table public.products   enable row level security;
alter table public.sales      enable row level security;
alter table public.sale_items enable row level security;
alter table public.settings   enable row level security;

-- Crea la venta y sus items en una sola transaccion:
-- valida stock (bloqueando las filas), descuenta, y calcula total/ganancia.
create or replace function public.create_sale(items jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sale_id uuid;
  v_total   numeric(12,2) := 0;
  v_profit  numeric(12,2) := 0;
  v_item    jsonb;
  v_product public.products%rowtype;
  v_qty     numeric(12,3);
  v_price   numeric(12,2);
begin
  if items is null or jsonb_array_length(items) = 0 then
    raise exception 'La venta debe incluir al menos un producto';
  end if;

  insert into public.sales (total, profit) values (0, 0)
  returning id into v_sale_id;

  for v_item in select value from jsonb_array_elements(items) loop
    if v_item ->> 'product_id' is null then
      raise exception 'Cada producto de la venta debe indicar el producto';
    end if;
    if v_item ->> 'cantidad' is null then
      raise exception 'Cada producto de la venta debe indicar la cantidad';
    end if;

    v_qty := (v_item ->> 'cantidad')::numeric;
    if v_qty is null or v_qty <= 0 then
      raise exception 'La cantidad debe ser mayor a cero';
    end if;

    select * into v_product
      from public.products
     where id = (v_item ->> 'product_id')::uuid
       for update;

    if not found then
      raise exception 'Producto no encontrado';
    end if;
    if not v_product.active then
      raise exception 'El producto % esta desactivado', v_product.name;
    end if;
    if v_product.stock < v_qty then
      raise exception 'Stock insuficiente para %: hay % y se requieren %',
        v_product.name, v_product.stock, v_qty;
    end if;

    if v_item ? 'precio_unitario' and v_item ->> 'precio_unitario' is not null then
      v_price := (v_item ->> 'precio_unitario')::numeric;
      if v_price < 0 then
        raise exception 'El precio unitario no puede ser negativo';
      end if;
    else
      v_price := v_product.price;
    end if;

    insert into public.sale_items (sale_id, product_id, product_name, quantity, unit_price, unit_cost)
    values (v_sale_id, v_product.id, v_product.name, v_qty, v_price, v_product.cost);

    update public.products
       set stock = stock - v_qty
     where id = v_product.id;

    v_total  := v_total  + round(v_price * v_qty, 2);
    v_profit := v_profit + round((v_price - v_product.cost) * v_qty, 2);
  end loop;

  update public.sales
     set total = v_total, profit = v_profit
   where id = v_sale_id;

  return jsonb_build_object(
    'id', v_sale_id,
    'total', v_total,
    'profit', v_profit,
    'status', 'completada',
    'created_at', now()
  );
end;
$$;

-- Anula solo ventas completadas y devuelve el stock.
create or replace function public.cancel_sale(sale_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sale public.sales%rowtype;
begin
  select * into v_sale
    from public.sales
   where id = cancel_sale.sale_id
     for update;

  if not found then
    raise exception 'Venta no encontrada';
  end if;

  if v_sale.status <> 'completada' then
    raise exception 'La venta ya esta anulada';
  end if;

  update public.products p
     set stock = p.stock + si.quantity
    from public.sale_items si
   where si.sale_id = cancel_sale.sale_id
     and p.id = si.product_id;

  update public.sales
     set status = 'anulada', cancelled_at = now()
   where id = cancel_sale.sale_id;

  return jsonb_build_object(
    'id', v_sale.id,
    'total', v_sale.total,
    'profit', v_sale.profit,
    'status', 'anulada',
    'cancelled_at', now()
  );
end;
$$;

-- Entrada de stock atomica.
create or replace function public.add_stock(product_id uuid, qty numeric)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_product public.products%rowtype;
begin
  if qty is null or qty <= 0 then
    raise exception 'La cantidad debe ser mayor a cero';
  end if;

  update public.products
     set stock = stock + qty
   where id = add_stock.product_id
   returning * into v_product;

  if not found then
    raise exception 'Producto no encontrado';
  end if;

  return jsonb_build_object(
    'id', v_product.id,
    'name', v_product.name,
    'stock', v_product.stock
  );
end;
$$;

revoke execute on function public.create_sale(jsonb) from public, anon, authenticated;
revoke execute on function public.cancel_sale(uuid) from public, anon, authenticated;
revoke execute on function public.add_stock(uuid, numeric) from public, anon, authenticated;
grant execute on function public.create_sale(jsonb) to service_role;
grant execute on function public.cancel_sale(uuid) to service_role;
grant execute on function public.add_stock(uuid, numeric) to service_role;
