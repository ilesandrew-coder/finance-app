-- ============================================================
-- Migration: Add sort_order to transactions
-- Run in: Supabase SQL Editor
-- Purpose: Fix same-day multi-transaction balance display bug.
--
-- The app determines each account's current balance by reading
-- the 'balance' field from the most-recently-dated transaction.
-- When multiple transactions share the same date, the ordering
-- was previously by UUID (random), so an arbitrary intra-day
-- transaction was picked — giving the wrong account balance.
--
-- sort_order is assigned by the import script: 0 = oldest
-- transaction on that day, N = newest. Sorting by
-- date DESC, sort_order DESC reliably picks the correct
-- closing balance for each account.
-- ============================================================

-- Step 1: Add the column (safe to re-run)
ALTER TABLE transactions
  ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_tx_date_sort
  ON transactions(account_id, date, sort_order);


-- ============================================================
-- Step 2: Fix the 3 same-day Expenses transactions on
--         2026-03-05 that caused the wrong balance (1,395.41
--         shown instead of 0.41).
--
-- Logic: within that day's transactions, the one with the
-- HIGHEST balance was executed FIRST (it was the incoming
-- transfer), so it gets sort_order=0. The one with the
-- LOWEST balance was executed LAST (final debit), so it gets
-- the highest sort_order and is picked first by the app.
-- ============================================================

WITH expenses_acct AS (
  SELECT id FROM accounts WHERE name = 'Expenses'
),
ranked AS (
  SELECT
    t.id,
    (ROW_NUMBER() OVER (ORDER BY t.balance DESC) - 1)::INTEGER AS new_sort_order
  FROM transactions t
  JOIN expenses_acct a ON t.account_id = a.id
  WHERE t.date = '2026-03-05'
)
UPDATE transactions t
SET sort_order = ranked.new_sort_order
FROM ranked
WHERE t.id = ranked.id;


-- ============================================================
-- Verify: should show 3 rows with sort_order 0, 1, 2
-- and balance 1395.41, 580.41, 0.41 respectively
-- ============================================================
-- SELECT t.date, t.description, t.amount, t.balance, t.sort_order
-- FROM transactions t
-- JOIN accounts a ON t.account_id = a.id
-- WHERE a.name = 'Expenses' AND t.date = '2026-03-05'
-- ORDER BY t.sort_order;
