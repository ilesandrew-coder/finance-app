-- ============================================================
-- M5 RLS Policies — Budget Management
-- Run this once in Supabase SQL Editor after deploying M5.
-- ============================================================

-- Allow authenticated users to create, edit, and delete budgets.
CREATE POLICY "authenticated_manage_budgets"
  ON budgets FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);
