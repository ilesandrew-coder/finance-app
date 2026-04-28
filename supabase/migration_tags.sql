-- ============================================================
-- Migration: Tags feature
-- Run in: Supabase SQL Editor
-- ============================================================

-- 1. Tags table
CREATE TABLE IF NOT EXISTS tags (
  id         UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  name       TEXT    NOT NULL UNIQUE,
  color      TEXT    NOT NULL DEFAULT '#a855f7',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Add tag_id FK to transactions (nullable — untagged = NULL)
ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS tag_id UUID REFERENCES tags(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tx_tag_id ON transactions(tag_id);
