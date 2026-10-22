-- Paridad con el proyecto Supabase: indice de FK aplicado desde el dashboard.
create index if not exists sale_items_product_id_idx
  on public.sale_items (product_id);
