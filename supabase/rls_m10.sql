-- =============================================================
--  M10 — Receipt URL column + GRANT fix
--  Run this in Supabase SQL Editor if receipt uploads are not
--  being saved (column may be missing if schema was seeded
--  before receipt_url was added to schema.sql).
-- =============================================================

-- Add receipt_url column if it doesn't already exist.
-- Safe to run multiple times.
ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS receipt_url TEXT;
