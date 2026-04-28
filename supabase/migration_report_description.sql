-- ============================================================
-- Migration: report_description field
-- Run in: Supabase SQL Editor
-- ============================================================

-- Adds a manually-entered description used in B & F PDF reports
-- instead of the raw imported bank description.
-- NULL means "use the existing description column" (no change to existing data).

ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS report_description TEXT;
