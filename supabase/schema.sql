-- ============================================================
-- BOV Finance App — Database Schema
-- Version: 1.0  |  Run in: Supabase SQL Editor
-- ============================================================
-- Run this once after creating your Supabase project.
-- Safe to re-run: all statements use IF NOT EXISTS.
-- ============================================================


-- ============================================================
-- ACCOUNTS
-- Represents each BOV bank account.
-- owner is a plain text label ('andrew', 'lyn', 'joint') for now;
-- will be migrated to a UUID FK to auth.users in a later milestone.
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
  id           UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  name         TEXT    NOT NULL UNIQUE,           -- internal key, matches Excel sheet name for Andrew's accounts
  display_name TEXT,                              -- shown in the UI
  type         TEXT    NOT NULL CHECK (type IN ('current', 'credit_card', 'savings', 'joint')),
  owner        TEXT    NOT NULL CHECK (owner IN ('andrew', 'lyn', 'joint')),
  currency     TEXT    NOT NULL DEFAULT 'EUR',
  is_joint     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- TRANSACTIONS
-- One row per bank transaction across all accounts.
-- source_amount / source_currency are only populated for
-- foreign-currency credit card transactions.
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
  id              UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  account_id      UUID    NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  date            DATE    NOT NULL,
  description     TEXT,
  amount          NUMERIC(12, 2),                 -- EUR amount (debit = negative, credit = positive)
  balance         NUMERIC(12, 2),                 -- running balance after this transaction
  source_amount   NUMERIC(12, 2),                 -- original foreign currency amount (Visa Gold FX only)
  source_currency TEXT,                           -- e.g. 'USD', 'GBP' (Visa Gold FX only)
  import_month    TEXT,                           -- 'YYYY-MM', the month this row was imported
  category        TEXT    DEFAULT 'Uncategorised',
  category_source TEXT    DEFAULT 'rule'
                  CHECK (category_source IN ('rule', 'manual', 'uncategorised')),
  business_flag   BOOLEAN DEFAULT NULL,           -- Y = claimable business expense
  fl3xx_flag      BOOLEAN DEFAULT NULL,           -- Y = FL3XX related
  reviewed        BOOLEAN NOT NULL DEFAULT FALSE,
  receipt_url     TEXT,                           -- Google Drive file URL
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tx_account_id    ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_tx_date          ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category      ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_business_flag ON transactions(business_flag) WHERE business_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_tx_fl3xx_flag    ON transactions(fl3xx_flag)    WHERE fl3xx_flag = TRUE;


-- ============================================================
-- CATEGORY RULES
-- Keyword-to-category mapping. Evaluated top-to-bottom
-- (ascending priority); first match wins.
-- ============================================================
CREATE TABLE IF NOT EXISTS category_rules (
  id            UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  category_name TEXT    NOT NULL,
  keyword       TEXT    NOT NULL UNIQUE,          -- keywords are globally unique (first match wins)
  priority      INTEGER NOT NULL DEFAULT 0,       -- lower number = checked first
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_priority ON category_rules(priority);


-- ============================================================
-- CATEGORY OVERRIDES
-- Per-transaction manual category corrections.
-- One override per transaction (UNIQUE constraint).
-- ============================================================
CREATE TABLE IF NOT EXISTS category_overrides (
  id             UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  transaction_id UUID    NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
  category       TEXT    NOT NULL,
  overridden_by  TEXT,                            -- 'andrew' or 'lyn' (will become UUID FK later)
  overridden_at  TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- BUDGETS
-- Monthly budget per category.
-- month = NULL means "default for all months".
-- A month-specific row overrides the default for that month.
-- ============================================================
CREATE TABLE IF NOT EXISTS budgets (
  id           UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  category     TEXT    NOT NULL,
  amount       NUMERIC(12, 2) NOT NULL,
  month        DATE,                              -- NULL = default; or first day of the month e.g. 2026-03-01
  person_scope TEXT    NOT NULL DEFAULT 'andrew'
               CHECK (person_scope IN ('andrew', 'lyn', 'household')),
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (category, month, person_scope)
);


-- ============================================================
-- SAVINGS GOALS
-- Named targets linked to a specific savings account.
-- ============================================================
CREATE TABLE IF NOT EXISTS savings_goals (
  id            UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  account_id    UUID    REFERENCES accounts(id) ON DELETE CASCADE,
  name          TEXT    NOT NULL,
  target_amount NUMERIC(12, 2),
  deadline      DATE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- CATEGORIES
-- User-manageable category list.  System categories (is_system=TRUE)
-- are seeded once and cannot be renamed or deleted via the app.
-- Custom categories are created/edited by the user from within the app.
-- The app loads this table on startup; falls back to a hardcoded list
-- if the table is empty or unavailable (e.g. offline).
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
  id           UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  name         TEXT    NOT NULL UNIQUE,
  color        TEXT    NOT NULL DEFAULT '#6b7280',  -- hex from PALETTE
  is_system    BOOLEAN NOT NULL DEFAULT FALSE,       -- locks rename/delete in the app
  sort_order   INTEGER NOT NULL DEFAULT 0,           -- controls picker order
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_categories_sort ON categories(sort_order, name);

-- Seed system categories (safe to re-run: INSERT ... ON CONFLICT DO NOTHING)
INSERT INTO categories (name, color, is_system, sort_order) VALUES
  ('Groceries & Supermarkets',    '#3b82f6', TRUE,  10),
  ('Dining & Cafes',              '#10b981', TRUE,  20),
  ('Fuel & Petrol',               '#f59e0b', TRUE,  30),
  ('Transport',                   '#ef4444', TRUE,  40),
  ('Travel & Accommodation',      '#8b5cf6', TRUE,  50),
  ('Utilities',                   '#06b6d4', TRUE,  60),
  ('Insurance',                   '#f97316', TRUE,  70),
  ('Tax & Government',            '#84cc16', TRUE,  80),
  ('Subscriptions & Digital',     '#ec4899', TRUE,  90),
  ('Healthcare',                  '#6366f1', TRUE, 100),
  ('Shopping & Retail',           '#14b8a6', TRUE, 110),
  ('School & Extra-curriculars',  '#a855f7', TRUE, 120),
  ('Professional Services',       '#0ea5e9', TRUE, 130),
  ('Loan Repayment',              '#d946ef', TRUE, 140),
  ('Bank Fees & Interest',        '#64748b', TRUE, 150),
  ('General Expenses',            '#9ca3af', TRUE, 160),
  ('ATM Withdrawal',              '#374151', TRUE, 170),
  ('Income & Refunds',            '#059669', TRUE, 180),
  ('Lyn Contribution',            '#db2777', TRUE, 190),
  ('Internal Transfer',           '#6b7280', TRUE, 200),
  ('Uncategorised',               '#f59e0b', TRUE, 210)
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- IMPORT LOG
-- Audit trail of every CSV import run.
-- ============================================================
CREATE TABLE IF NOT EXISTS import_log (
  id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  account_id  UUID    REFERENCES accounts(id),
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  rows_added  INTEGER DEFAULT 0,
  rows_skipped INTEGER DEFAULT 0,
  notes       TEXT
);


-- ============================================================
-- ROW LEVEL SECURITY (disabled for now — enable at M3 when
-- auth and the PWA are set up)
-- ============================================================
-- ALTER TABLE accounts      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transactions  ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE budgets        ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "owner_access" ON accounts     USING (owner = current_setting('app.current_user', true));
-- CREATE POLICY "owner_access" ON transactions USING (account_id IN (SELECT id FROM accounts WHERE owner = current_setting('app.current_user', true)));
