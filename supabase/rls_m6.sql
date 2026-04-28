-- ============================================================
-- M6 RLS Policies — Category Rule Editor
-- Run this once in Supabase SQL Editor after deploying M6.
-- ============================================================

-- Allow authenticated users to create, edit, and delete category rules.
CREATE POLICY "authenticated_manage_category_rules"
  ON category_rules FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);
