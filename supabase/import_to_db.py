#!/usr/bin/env python3
"""
BOV Finance App — M2 Import Script
====================================
Scans ~/Downloads for AccountStatement*.csv files downloaded from BOV eBanking,
identifies each account, deduplicates against Supabase, applies category rules,
and inserts new transactions into the database.

Usage:
  python3 import_to_db.py              # run the full import
  python3 import_to_db.py --last-dates # print last transaction date per account (for BOV date picker)
  python3 import_to_db.py --dry-run    # parse CSVs and show what would be inserted, without writing
"""

import os
import sys
import csv
import json
import glob
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).parent
BANK_DIR        = SCRIPT_DIR.parent
CATEGORIES_FILE = BANK_DIR / "bov_categories_REPLACED.json"
DOWNLOADS_DIR   = Path.home() / "Downloads"
ENV_FILE        = SCRIPT_DIR / ".env"

load_dotenv(ENV_FILE)
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY not set in supabase/.env")

# ── Account number → DB account name ─────────────────────────────────────────
# Update these if BOV ever changes your account numbers.
ACCOUNT_NUMBER_MAP = {
    # Andrew's accounts
    "40010904923":      "Current Account",
    "40011630296":      "Expenses",
    "17314879017":      "Tax & SS",
    "4459514045016084": "Visa Gold",
    # Lyn's accounts
    "13415542014":      "Savings",
    "40012661277":      "Ctrl+S",
    "4552401324944010": "Visa",
    # Joint account (appears under Lyn's BOV login as "Joint Savings")
    "40013839972":      "Joint Account",
}

VISA_ACCOUNT_NAME = "Visa Gold"


# ── CSV parsing ────────────────────────────────────────────────────────────────

def read_csv_rows(path):
    """Read all rows from a CSV file, returning a list of lists."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def extract_account_number(rows):
    """
    Row 1 = column headers (Account Number, Type, ...)
    Row 2 = account data — account number is in the first column.
    """
    if len(rows) < 2:
        return None
    return str(rows[1][0]).strip() if rows[1] else None


def extract_closing_balance(rows):
    """
    Find the closing balance from the account data row (row 2).
    Looks for a column header containing 'balance' in row 1.
    Falls back to the last numeric value in row 2.
    """
    if len(rows) < 2:
        return None
    headers = [str(h).lower() for h in rows[0]]
    data    = rows[1]

    # Prefer a column explicitly named with "balance"
    for i, h in enumerate(headers):
        if "balance" in h and i < len(data):
            try:
                return float(str(data[i]).replace(",", "").strip())
            except ValueError:
                pass

    # Fallback: last numeric value in the data row
    for val in reversed(data):
        try:
            return float(str(val).replace(",", "").strip())
        except ValueError:
            pass
    return None


def find_transaction_header_row(rows):
    """
    Return the index of the row that contains transaction column headers
    (the row with 'Date' as first column).
    """
    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower() == "date":
            return i
        # Visa Gold header starts with "Card Number"
        if row and str(row[0]).strip().lower() == "card number":
            return i
    return None


def parse_standard_transactions(rows, header_idx):
    """
    Parse standard account transactions (Current Account, Expenses, Tax & SS).
    Columns: Date | Detail | Amount
    Returns list of dicts with date, description, amount.
    """
    txns = []
    for row in rows[header_idx + 1:]:
        if not row or not row[0] or str(row[0]).strip() == "":
            continue
        try:
            raw_date = str(row[0]).strip()
            # BOV uses YYYY/MM/DD in CSV
            tx_date = datetime.strptime(raw_date, "%Y/%m/%d").date().isoformat()
        except ValueError:
            try:
                tx_date = datetime.strptime(raw_date, "%d/%m/%Y").date().isoformat()
            except ValueError:
                continue  # skip unparseable date rows

        detail = str(row[1]).strip() if len(row) > 1 else ""
        try:
            amount = float(str(row[2]).replace(",", "").strip()) if len(row) > 2 and row[2] else 0.0
        except ValueError:
            amount = 0.0

        txns.append({"date": tx_date, "description": detail, "amount": amount,
                     "source_amount": None, "source_currency": None})
    return txns


def parse_visa_transactions(rows, header_idx):
    """
    Parse Visa Gold transactions.
    Columns: Card Number | Date | Detail | Source amount | Source currency | Destination amount
    """
    txns = []
    for row in rows[header_idx + 1:]:
        if not row or len(row) < 3 or not row[1] or str(row[1]).strip() == "":
            continue
        try:
            raw_date = str(row[1]).strip()
            tx_date = datetime.strptime(raw_date, "%Y/%m/%d").date().isoformat()
        except ValueError:
            try:
                tx_date = datetime.strptime(raw_date, "%d/%m/%Y").date().isoformat()
            except ValueError:
                continue

        detail = str(row[2]).strip() if len(row) > 2 else ""

        def safe_float(v):
            try:
                return float(str(v).replace(",", "").strip()) if v and str(v).strip() else None
            except ValueError:
                return None

        src_amount   = safe_float(row[3]) if len(row) > 3 else None
        src_currency = str(row[4]).strip() if len(row) > 4 and row[4] and str(row[4]).strip() not in ("", "None") else None
        dest_amount  = safe_float(row[5]) if len(row) > 5 else None

        # Use destination (EUR) amount as the transaction amount
        amount = dest_amount if dest_amount is not None else (src_amount or 0.0)

        txns.append({"date": tx_date, "description": detail, "amount": amount,
                     "source_amount": src_amount, "source_currency": src_currency})
    return txns


def calculate_running_balances(txns, closing_balance):
    """
    BOV CSVs are newest-first. The closing balance is after the most recent transaction.
    Assign balance[0] = closing_balance, then work backwards:
      balance[i] = balance[i-1] - txns[i-1].amount
    Finally reverse so the list is oldest-first (chronological order for insertion).

    Also assigns sort_order within each calendar date (0 = oldest, N = newest).
    This is critical for same-day multi-transaction accounts so the app can reliably
    identify the final balance of the day by sorting date DESC, sort_order DESC.
    """
    if not txns or closing_balance is None:
        return txns

    # Assign balances newest-first
    txns[0]["balance"] = round(closing_balance, 2)
    for i in range(1, len(txns)):
        txns[i]["balance"] = round(txns[i-1]["balance"] - txns[i-1]["amount"], 2)

    # Reverse to chronological order (oldest first)
    txns.reverse()

    # Assign sort_order within each date group (0 = oldest on that day, N = newest)
    date_counter = {}
    for tx in txns:
        d = tx["date"]
        date_counter[d] = date_counter.get(d, -1) + 1
        tx["sort_order"] = date_counter[d]

    return txns


def parse_csv(path):
    """
    Parse a BOV CSV file.
    Returns: (account_number, transactions) where transactions is a list of dicts.
    """
    rows = read_csv_rows(path)
    if not rows:
        return None, []

    account_number  = extract_account_number(rows)
    closing_balance = extract_closing_balance(rows)
    header_idx      = find_transaction_header_row(rows)

    if header_idx is None:
        print(f"  ⚠ Could not find transaction headers in {path.name} — skipping")
        return account_number, []

    is_visa = str(rows[header_idx][0]).strip().lower() == "card number"

    if is_visa:
        txns = parse_visa_transactions(rows, header_idx)
    else:
        txns = parse_standard_transactions(rows, header_idx)

    txns = calculate_running_balances(txns, closing_balance)
    return account_number, txns


# ── Categorisation ────────────────────────────────────────────────────────────

def load_category_rules(sb):
    """
    Load category rules from Supabase (ordered by priority).
    This ensures any edits made via the app are picked up immediately.
    Falls back to bov_categories.json if DB query fails.
    """
    try:
        rows = sb.table("category_rules").select("keyword,category_name").order("priority").execute().data
        return [(r["keyword"], r["category_name"]) for r in rows]
    except Exception as e:
        print(f"  ⚠ Could not load rules from DB ({e}), falling back to JSON")
        with open(CATEGORIES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        rules = []
        for cat in data.get("categories", []):
            for kw in cat.get("keywords", []):
                if kw:
                    rules.append((kw, cat["name"]))
        return rules


def load_internal_transfer_config():
    """Load internal transfer and Lyn contribution keywords from bov_categories.json."""
    with open(CATEGORIES_FILE, encoding="utf-8") as f:
        data = json.load(f)
    it = data.get("internal_transfers", {})
    return (
        [kw.lower() for kw in it.get("lyn_contribution_keywords", [])],
        [kw.lower() for kw in it.get("keywords", [])],
    )


def categorise(description, category_rules, lyn_keywords, internal_keywords):
    """
    Apply category rules to a transaction description.
    Returns (category, category_source).

    Priority:
    1. Check Lyn contribution keywords first (subset of internal transfers, treated as income)
    2. Check internal transfer keywords (excluded from spending)
    3. Check category rules top-to-bottom (first match wins)
    4. Fall back to 'Uncategorised'
    """
    desc_lower = description.lower()

    for kw in lyn_keywords:
        if kw in desc_lower:
            return "Lyn Contribution", "rule"

    for kw in internal_keywords:
        if kw in desc_lower:
            return "Internal Transfer", "rule"

    for keyword, cat_name in category_rules:
        if keyword.lower() in desc_lower:
            return cat_name, "rule"

    return "Uncategorised", "uncategorised"


def apply_categories(txns, category_rules, lyn_keywords, internal_keywords):
    """Apply categorisation to all transactions in a list."""
    for tx in txns:
        cat, source = categorise(
            tx.get("description", ""), category_rules, lyn_keywords, internal_keywords
        )
        tx["category"]        = cat
        tx["category_source"] = source
    return txns


# ── Supabase operations ────────────────────────────────────────────────────────

def get_account_id(account_name, sb):
    """Look up account UUID from the accounts table by name."""
    rows = sb.table("accounts").select("id").eq("name", account_name).execute().data
    return rows[0]["id"] if rows else None


def get_last_transaction_date(account_id, sb):
    """Return the most recent transaction date for an account, or None."""
    rows = (
        sb.table("transactions")
        .select("date")
        .eq("account_id", account_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["date"] if rows else None


def get_existing_keys(account_id, date_from, date_to, sb):
    """
    Return a set of (date, description, amount) tuples already in the DB
    for an account within the given date range.
    Used for deduplication.
    """
    rows = (
        sb.table("transactions")
        .select("date,description,amount")
        .eq("account_id", account_id)
        .gte("date", date_from)
        .lte("date", date_to)
        .execute()
        .data
    )
    return {(r["date"], r["description"], float(r["amount"])) for r in rows}


def insert_transactions(txns, sb):
    """Insert a batch of transactions into Supabase."""
    if txns:
        sb.table("transactions").insert(txns).execute()


def log_import(account_id, rows_added, rows_skipped, sb, notes=None):
    """Write an entry to the import_log table."""
    sb.table("import_log").insert({
        "account_id":   account_id,
        "rows_added":   rows_added,
        "rows_skipped": rows_skipped,
        "notes":        notes,
    }).execute()


# ── Main flow ──────────────────────────────────────────────────────────────────

def write_last_dates_file(totals, sb):
    """
    After a successful import, write last_import_dates.json to the Bank folder.
    Records the most recent transaction date per account so the next import
    can use it as the 'From' date without querying Supabase.
    """
    dates = {}
    for acct_num, acct_name in ACCOUNT_NUMBER_MAP.items():
        acct_id = get_account_id(acct_name, sb)
        if not acct_id:
            continue
        last = get_last_transaction_date(acct_id, sb)
        if last:
            dates[acct_name] = last
    if dates:
        out_path = BANK_DIR / "last_import_dates.json"
        with open(out_path, "w") as f:
            json.dump({"updated_at": datetime.today().isoformat(), "last_dates": dates}, f, indent=2)
        print(f"\n  ✓ Saved last import dates → {out_path.name}")


def print_last_dates(sb):
    """Print the last transaction date per account — use as the 'From' date in BOV."""
    print("\n  Last transaction dates (use as 'From' date in BOV eBanking):\n")
    fallback = (datetime.today() - timedelta(days=90)).strftime("%d/%m/%Y")
    for acct_num, acct_name in ACCOUNT_NUMBER_MAP.items():
        acct_id = get_account_id(acct_name, sb)
        if not acct_id:
            print(f"  {acct_name:<20} → account not found in DB")
            continue
        last = get_last_transaction_date(acct_id, sb)
        if last:
            # Format as DD/MM/YYYY for BOV date picker
            d = datetime.strptime(last, "%Y-%m-%d")
            print(f"  {acct_name:<20} → {d.strftime('%d/%m/%Y')}  (last transaction)")
        else:
            print(f"  {acct_name:<20} → {fallback}  (no data, using 90-day fallback)")
    print()


def main():
    dry_run    = "--dry-run"    in sys.argv
    last_dates = "--last-dates" in sys.argv

    print("=" * 55)
    print("  BOV Finance App — Monthly Import")
    print("=" * 55)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    if last_dates:
        print_last_dates(sb)
        return

    if dry_run:
        print("  Mode: DRY RUN — no data will be written\n")

    # Find CSVs in Downloads
    csv_files = sorted(DOWNLOADS_DIR.glob("AccountStatement*.csv"))
    if not csv_files:
        print(f"\n  No AccountStatement*.csv files found in {DOWNLOADS_DIR}")
        print("  Download your CSVs from BOV eBanking first, then run this script.")
        return

    print(f"\n  Found {len(csv_files)} CSV file(s) in ~/Downloads\n")

    # Load shared resources once
    category_rules    = load_category_rules(sb)
    lyn_keywords, internal_keywords = load_internal_transfer_config()

    # Process each CSV
    totals = {}  # account_name → (added, skipped)
    uncategorised_total = 0
    processed_files = []

    for csv_path in csv_files:
        print(f"▸ {csv_path.name}")
        account_number, txns = parse_csv(csv_path)

        if not account_number:
            print(f"  ⚠ Could not read account number — skipping\n")
            continue

        account_name = ACCOUNT_NUMBER_MAP.get(account_number)
        if not account_name:
            print(f"  ⚠ Unknown account number: {account_number} — skipping\n")
            continue

        account_id = get_account_id(account_name, sb)
        if not account_id:
            print(f"  ⚠ Account '{account_name}' not found in DB — skipping\n")
            continue

        print(f"  Account:  {account_name}")

        if not txns:
            print(f"  No transactions found in CSV\n")
            continue

        date_from = min(t["date"] for t in txns)
        date_to   = max(t["date"] for t in txns)
        print(f"  CSV range: {date_from} → {date_to}  ({len(txns)} rows)")

        # Check for gap vs last known date
        last_db_date = get_last_transaction_date(account_id, sb)
        if last_db_date:
            last_db_dt  = datetime.strptime(last_db_date, "%Y-%m-%d").date()
            csv_from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
            gap_days = (csv_from_dt - last_db_dt).days
            if gap_days > 1:
                print(f"  ⚠ GAP DETECTED: last DB date is {last_db_date}, CSV starts {date_from} ({gap_days} days gap)")
        else:
            print(f"  (No existing data for this account in DB)")

        # Categorise
        txns = apply_categories(txns, category_rules, lyn_keywords, internal_keywords)

        # Deduplicate
        existing = get_existing_keys(account_id, date_from, date_to, sb)
        new_txns  = []
        skipped   = 0
        for tx in txns:
            key = (tx["date"], tx["description"], round(float(tx["amount"]), 2))
            if key in existing:
                skipped += 1
            else:
                tx["account_id"] = account_id
                tx["reviewed"]   = False
                new_txns.append(tx)

        uncategorised = sum(1 for t in new_txns if t["category"] == "Uncategorised")
        uncategorised_total += uncategorised

        print(f"  New: {len(new_txns)}  |  Duplicates skipped: {skipped}  |  Uncategorised: {uncategorised}")

        if not dry_run:
            if new_txns:
                insert_transactions(new_txns, sb)
            log_import(account_id, len(new_txns), skipped, sb)

        prev_added, prev_skipped = totals.get(account_name, (0, 0))
        totals[account_name] = (prev_added + len(new_txns), prev_skipped + skipped)
        processed_files.append(csv_path)
        print()

    # Summary
    print("=" * 55)
    print("  Summary")
    print("=" * 55)
    for acct, (added, skipped) in totals.items():
        print(f"  {acct:<22} +{added} new  ({skipped} skipped)")

    if uncategorised_total > 0:
        print(f"\n  ⚠ {uncategorised_total} uncategorised transaction(s) — review in the app inbox")
    else:
        print(f"\n  ✓ All transactions categorised")

    # Clean up CSVs
    if not dry_run and processed_files:
        print(f"\n  Deleting {len(processed_files)} processed CSV file(s) from ~/Downloads...")
        for f in processed_files:
            f.unlink()
            print(f"    ✓ Deleted {f.name}")

    print("\n  ✅ Import complete!")
    if dry_run:
        print("  (Dry run — nothing was written to the database)")
    else:
        write_last_dates_file(totals, sb)


if __name__ == "__main__":
    main()
