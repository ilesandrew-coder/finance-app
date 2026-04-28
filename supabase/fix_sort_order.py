#!/usr/bin/env python3
"""
One-time fix: backfill sort_order for all existing transactions in Supabase.

The sort_order column was added to fix a bug where same-day multi-transaction
accounts showed the wrong balance (a random intra-day balance instead of
the closing one).

This script:
  1. Fetches all transactions from Supabase
  2. For each (account, date) group with >1 transaction, sorts them
     chronologically by following the balance chain:
       balance_before_tx = tx.balance - tx.amount
       The first tx of the day is the one whose balance_before doesn't
       match any other tx's balance in the group.
  3. Assigns sort_order 0, 1, 2... (oldest to newest) and updates Supabase.

Run once from your Mac:
  cd ~/Documents/Personal/Bank/supabase
  python3 fix_sort_order.py
"""

import os
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY not set in supabase/.env")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def sort_group_by_chain(txns):
    """
    Given a list of same-day transactions (balance and amount populated),
    return them in chronological order (oldest first) by walking the chain:

      balance_before_tx = tx.balance - tx.amount

    The FIRST transaction of the day is the one whose balance_before doesn't
    appear as any other transaction's balance in the group (it came from the
    previous day's closing balance).
    """
    if len(txns) == 1:
        return txns

    bal_set = {round(float(t["balance"]), 2) for t in txns}

    # Find the starting tx: its pre-transaction balance is NOT in the group's balances
    first = None
    for t in txns:
        balance_before = round(float(t["balance"]) - float(t["amount"]), 2)
        if balance_before not in bal_set:
            first = t
            break

    if first is None:
        # Couldn't determine order (floating point edge case) — return as-is
        return txns

    ordered   = [first]
    remaining = [t for t in txns if t["id"] != first["id"]]

    while remaining:
        last_bal = round(float(ordered[-1]["balance"]), 2)
        next_tx  = None
        for t in remaining:
            balance_before = round(float(t["balance"]) - float(t["amount"]), 2)
            if abs(balance_before - last_bal) < 0.005:   # small fp tolerance
                next_tx = t
                break

        if next_tx is None:
            # Chain broken — append the rest in whatever order
            ordered.extend(remaining)
            break

        ordered.append(next_tx)
        remaining = [t for t in remaining if t["id"] != next_tx["id"]]

    return ordered


def fetch_all_transactions():
    """Fetch all transactions in batches (Supabase caps at 1 000 rows by default)."""
    all_rows = []
    offset   = 0
    page     = 1000
    while True:
        rows = (
            sb.table("transactions")
            .select("id, account_id, date, balance, amount")
            .order("date")
            .range(offset, offset + page - 1)
            .execute()
            .data
        )
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page:
            break
        offset += page
    return all_rows


def main():
    print("=" * 55)
    print("  BOV Finance App — Backfill sort_order")
    print("=" * 55)

    # ── 1. Fetch ──────────────────────────────────────────────
    print("\n  Fetching all transactions from Supabase…")
    txns = fetch_all_transactions()
    print(f"  Fetched {len(txns)} transactions")

    # ── 2. Group by (account_id, date) ────────────────────────
    groups = defaultdict(list)
    for t in txns:
        groups[(t["account_id"], t["date"])].append(t)

    multi = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"  Found {len(multi)} (account, date) group(s) with >1 transaction")

    if not multi:
        print("\n  Nothing to fix — all days have at most 1 transaction. ✓")
        return

    # ── 3. Determine correct order and build update list ──────
    updates = []
    for (account_id, date), group_txns in multi.items():
        ordered = sort_group_by_chain(group_txns)
        for i, tx in enumerate(ordered):
            if tx.get("sort_order", 0) != i:   # only update if wrong
                updates.append({"id": tx["id"], "sort_order": i})

    if not updates:
        print("\n  sort_order is already correct for all multi-tx days. ✓")
        return

    print(f"  Updating sort_order for {len(updates)} transaction(s)…\n")

    # ── 4. Apply updates one by one (simple, reliable) ────────
    for i, upd in enumerate(updates, 1):
        sb.table("transactions").update({"sort_order": upd["sort_order"]}).eq("id", upd["id"]).execute()
        if i % 10 == 0 or i == len(updates):
            print(f"    Updated {i}/{len(updates)}…")

    print(f"\n  ✅  Done — {len(updates)} transaction(s) updated.")
    print("  Refresh the app and all account balances should now be correct.\n")


if __name__ == "__main__":
    main()
