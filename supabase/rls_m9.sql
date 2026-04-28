-- ============================================================
--  M9 — Lyn's Accounts & Perspective Toggle
--  Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

-- ── 1. Ensure accounts.owner column exists ──────────────────
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS owner text;

-- ── 2. Tag all existing (Andrew's) accounts ─────────────────
--  All accounts in the DB before M9 belong to Andrew.
--  The joint account gets owner='joint'; everything else = 'andrew'.
--  Adjust the ILIKE match if your joint account has a different name.
UPDATE accounts SET owner = 'andrew' WHERE owner IS NULL;
UPDATE accounts SET owner = 'joint'  WHERE owner = 'andrew' AND name ILIKE '%joint%';

-- ── 3. Add Lyn's accounts ────────────────────────────────────
--  Using ON CONFLICT DO NOTHING so re-running this is safe.
--  'type' column uses the same values already in the table:
--  current / savings / credit_card
INSERT INTO accounts (name, type, owner) VALUES
  ('Savings',  'savings',     'lyn'),
  ('Ctrl+S',   'savings',     'lyn'),
  ('Visa',     'credit_card', 'lyn')
ON CONFLICT DO NOTHING;

-- ── 4. Ensure budgets.person_scope column exists ─────────────
--  (May already exist from M5 — ADD COLUMN IF NOT EXISTS is safe)
ALTER TABLE budgets ADD COLUMN IF NOT EXISTS person_scope text;

-- Update any existing budgets that have no person_scope to 'andrew'
UPDATE budgets SET person_scope = 'andrew' WHERE person_scope IS NULL;

-- ── 5. RLS policy for Lyn's accounts & transactions ──────────
--  The existing authenticated_read/write policies already cover
--  any authenticated user, so no new RLS rows are needed.
--  Verify the existing policy allows reads for all accounts:
--  SELECT * FROM pg_policies WHERE tablename = 'accounts';

-- ── 6. Verify ────────────────────────────────────────────────
SELECT name, type, owner FROM accounts ORDER BY owner, name;
