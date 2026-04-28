-- =============================================================
--  M4 — Write policies for Category Review UI
--  Run this in Supabase SQL Editor after rls.sql (M3).
-- =============================================================

-- Allow authenticated users to update category/reviewed fields on transactions.
-- (Column-level restrictions aren't possible in RLS; the frontend only sends
--  the allowed fields. The service_role key used by the import script bypasses
--  RLS entirely, so this only affects the frontend anon/authenticated key.)
CREATE POLICY "authenticated_update_transactions"
  ON transactions
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Allow authenticated users to log manual category overrides.
CREATE POLICY "authenticated_insert_category_overrides"
  ON category_overrides
  FOR INSERT
  TO authenticated
  WITH CHECK (true);
