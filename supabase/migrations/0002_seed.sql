-- Datos de ejemplo: puestos de productos (precios en cordobas)

insert into public.settings (id, pin_hash, low_stock_default)
values (true, null, 5)
on conflict (id) do nothing;

insert into public.products (name, cost, price, stock, min_stock, unit)
values
  ('Arroz',    30.00,  38.00, 120, 10, 'libra'),
  ('Frijoles', 55.00,  70.00,  80, 10, 'libra'),
  ('Aceite',  120.00, 150.00,  45,  5, 'litro'),
  ('Azúcar',   32.00,  42.00,  90, 10, 'libra'),
  ('Sal',       8.00,  12.00,  60, 10, 'libra'),
  ('Café',    150.00, 190.00,   3,  5, 'libra');
