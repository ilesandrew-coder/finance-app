-- ============================================================
--  BOV Finance App — Row Level Security (M3)
--  Run this in the Supabase SQL editor (Project → SQL editor)
--
--  These policies allow any authenticated user to READ all rows.
--  The service_role key (used by import scripts) bypasses RLS.
--  Write access from the frontend is added in later milestones.
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE accounts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE category_rules    ENABLE ROW LEVEL SECURITY;
ALTER TABLE category_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets            ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_goals      ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_log         ENABLE ROW LEVEL SECURITY;

-- ---- Read policies (authenticated users can read everything) ----

CREATE POLICY "authenticated_read" ON accounts
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON transactions
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON category_rules
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON category_overrides
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON budgets
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON savings_goals
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read" ON import_log
  FOR SELECT TO authenticated USING (true);

-- ============================================================
--  IMPORTANT: After running this script, go to:
--    Supabase Dashboard → Authentication → Providers → Email
--  and set:
--    - "Enable Email Signup" → ON  (needed for magic link)
--    - "Confirm email" → ON
--
--  Then go to:
--    Supabase Dashboard → Authentication → URL Configuration
--  and add your app URL to "Redirect URLs", e.g.:
--    https://your-app.netlify.app
--    http://localhost (for local testing)
--
--  Finally, to restrict sign-in to your email only:
--    Supabase Dashboard → Authentication → Settings
--    → "Disable signup" (after your first sign-in)
-- ============================================================
