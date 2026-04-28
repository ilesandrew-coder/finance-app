#!/usr/bin/env python3
"""
BOV Finance App — FL3XX Combined PDF Report Generator
======================================================
Pulls FL3XX-flagged transactions for a selected month from Supabase,
downloads their receipts from Google Drive, and produces a single PDF:

  Page 1:  Transaction table (cover page)
  Page 2+: Receipt files appended in date order

Usage:
  python3 generate_fl3xx_report.py              # interactive month selector
  python3 generate_fl3xx_report.py 2025-11      # specify month directly
  python3 generate_fl3xx_report.py 2025-11 --no-receipts  # table only

Output: FL3XX_Report_YYYY-MM.pdf saved to the Bank folder.

First-run setup:
  1. In Google Cloud Console > APIs & Services > Credentials,
     create an additional OAuth 2.0 Client ID of type "Desktop app".
  2. Download the JSON, rename it to drive_credentials.json,
     and place it next to this script (in Bank/supabase/).
  3. Run this script once; a browser will open for Google sign-in.
     A drive_token.json is then saved for future runs (no sign-in needed).

Dependencies (add to the existing pip install command):
  pip install fpdf2 pypdf Pillow google-auth-oauthlib google-api-python-client --break-system-packages
"""

import os
import sys
import io
import re
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR       = Path(__file__).parent
BANK_DIR         = SCRIPT_DIR.parent
ENV_FILE         = SCRIPT_DIR / ".env"
CREDENTIALS_FILE = SCRIPT_DIR / "drive_credentials.json"
TOKEN_FILE       = SCRIPT_DIR / "drive_token.json"

load_dotenv(ENV_FILE)
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY not set in supabase/.env")

# ── Argument parsing ───────────────────────────────────────────────────────────
args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = [a for a in sys.argv[1:] if a.startswith('--')]
include_receipts = '--no-receipts' not in flags

month_arg = args[0] if args else None
if month_arg:
    try:
        datetime.strptime(month_arg, "%Y-%m")
        selected_month = month_arg
    except ValueError:
        raise SystemExit(f"ERROR: Invalid month format '{month_arg}'. Use YYYY-MM (e.g. 2025-11)")
else:
    selected_month = None

# ── Supabase ──────────────────────────────────────────────────────────────────
from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Fetch all FL3XX transactions, grouped by month, to offer a selector
resp = sb.from_("transactions") \
    .select("id, date, description, amount, account_id, receipt_url, fl3xx_flag") \
    .eq("fl3xx_flag", True) \
    .order("date", desc=True) \
    .execute()

all_fl3xx = resp.data or []

if not all_fl3xx:
    raise SystemExit("No FL3XX-flagged transactions found in the database.")

# Build sorted list of unique months that have FL3XX transactions
months_with_data = sorted(set(t["date"][:7] for t in all_fl3xx), reverse=True)

if not selected_month:
    print("\nFL3XX months with transactions:")
    for i, m in enumerate(months_with_data):
        dt = datetime.strptime(m, "%Y-%m")
        count = sum(1 for t in all_fl3xx if t["date"].startswith(m))
        print(f"  [{i+1}] {dt.strftime('%B %Y')}  ({count} transaction{'s' if count != 1 else ''})")
    print()
    choice = input("Select month number: ").strip()
    try:
        selected_month = months_with_data[int(choice) - 1]
    except (ValueError, IndexError):
        raise SystemExit("Invalid selection.")

# Filter to selected month
txs = [t for t in all_fl3xx if t["date"].startswith(selected_month)]
txs.sort(key=lambda t: t["date"])

if not txs:
    raise SystemExit(f"No FL3XX transactions found for {selected_month}.")

month_label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")
print(f"\n✓ Found {len(txs)} FL3XX transaction(s) for {month_label}")

# Fetch account names for display
acct_resp = sb.from_("accounts").select("id, name").execute()
acct_map = {a["id"]: a["name"] for a in (acct_resp.data or [])}

total_eur = sum(abs(t["amount"]) for t in txs)

# ── Google Drive setup ────────────────────────────────────────────────────────
drive_service = None

if include_receipts:
    receipts_needed = [t for t in txs if t.get("receipt_url")]
    if not receipts_needed:
        print("  ℹ  No receipts linked — generating table only.")
        include_receipts = False

if include_receipts:
    if not CREDENTIALS_FILE.exists():
        print(f"\n⚠  {CREDENTIALS_FILE.name} not found.")
        print("   Create a Desktop app OAuth client in Google Cloud Console,")
        print(f"   download the JSON, and save it as:\n   {CREDENTIALS_FILE}")
        print("\n   Generating table-only PDF instead.\n")
        include_receipts = False
    else:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = None

        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json())
            print("  ✓ Google Drive authenticated — token saved for future runs.")

        drive_service = build("drive", "v3", credentials=creds)
        print("  ✓ Connected to Google Drive")

# ── Cover page PDF (transaction table) ───────────────────────────────────────
from fpdf import FPDF

class ReportPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 41, 59)   # slate-800
        self.rect(0, 0, 297, 22, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(8, 5)
        self.cell(0, 6, "BOV Finance — FL3XX Expenses Report", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_x(8)
        self.cell(0, 5, f"Andrew Iles  ·  {month_label}", ln=False)
        self.set_x(-60)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%d/%m/%Y')}", align="R", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, f"Total: €{total_eur:.2f}  ·  {len(txs)} transaction{'s' if len(txs) != 1 else ''}",
                  align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R")

pdf = ReportPDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Column definitions: (header, width, align)
cols = [
    ("Date",         22, "C"),
    ("Description",  95, "L"),
    ("Account",      40, "L"),
    ("Amount (€)",   25, "R"),
    ("Receipt",      80, "L"),
]

# Table header row
pdf.set_font("Helvetica", "B", 8)
pdf.set_fill_color(59, 130, 246)
pdf.set_text_color(255, 255, 255)
for hdr, w, align in cols:
    pdf.cell(w, 7, hdr, border=0, align=align, fill=True)
pdf.ln()

# Data rows
pdf.set_font("Helvetica", "", 8)
pdf.set_text_color(0, 0, 0)
for i, t in enumerate(txs):
    fill = i % 2 == 1
    pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
    receipt_label = "No receipt" if not t.get("receipt_url") else "✓ Attached"
    row_data = [
        t["date"],
        t["description"][:55],
        acct_map.get(t["account_id"], "—")[:30],
        f"{abs(t['amount']):.2f}",
        receipt_label,
    ]
    for j, (val, (_, w, align)) in enumerate(zip(row_data, cols)):
        pdf.cell(w, 6, val, border=0, align=align, fill=fill)
    pdf.ln()

# Summary row
pdf.ln(2)
pdf.set_font("Helvetica", "B", 9)
pdf.set_fill_color(241, 245, 249)
pdf.cell(sum(w for _, w, _ in cols[:3]), 7, f"Total ({len(txs)} transactions)", fill=True)
pdf.cell(cols[3][1], 7, f"€{total_eur:.2f}", align="R", fill=True)
pdf.cell(cols[4][1], 7, "", fill=True)
pdf.ln()

cover_bytes = bytes(pdf.output())
print(f"  ✓ Cover page generated ({len(txs)} transactions, €{total_eur:.2f})")

# ── Download receipts and merge ───────────────────────────────────────────────
if not include_receipts:
    # Save table-only PDF
    out_path = BANK_DIR / f"FL3XX_Report_{selected_month}.pdf"
    out_path.write_bytes(cover_bytes)
    print(f"\n✓ Saved: {out_path}")
    sys.exit(0)

from pypdf import PdfWriter, PdfReader
from PIL import Image

def extract_drive_id(url):
    """Pull the file ID out of a Drive viewer URL."""
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else None

def download_drive_file(file_id):
    """Download a Drive file; returns (bytes, mime_type)."""
    meta = drive_service.files().get(fileId=file_id, fields="mimeType, name").execute()
    mime = meta.get("mimeType", "")
    buf = io.BytesIO()
    req = drive_service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), mime

def image_bytes_to_pdf_bytes(img_bytes):
    """Convert an image (JPEG/PNG/etc.) to a single-page PDF via Pillow."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    # A4 landscape in points: 841 x 595 (72 dpi equivalent)
    scale = min(841 / w, 595 / h, 1.0)   # don't upscale
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    pdf_buf = io.BytesIO()
    img.save(pdf_buf, format="PDF")
    return pdf_buf.getvalue()

writer = PdfWriter()

# Add cover page
writer.append(PdfReader(io.BytesIO(cover_bytes)))

# Add receipts in transaction date order
receipt_count = 0
for t in txs:
    url = t.get("receipt_url")
    if not url:
        print(f"  ⚠  No receipt for: {t['date']} {t['description'][:40]}")
        continue
    file_id = extract_drive_id(url)
    if not file_id:
        print(f"  ⚠  Can't parse Drive ID from: {url}")
        continue
    try:
        print(f"  ↓  Downloading receipt for {t['date']} {t['description'][:35]}…")
        file_bytes, mime = download_drive_file(file_id)
        if "image" in mime:
            pdf_bytes = image_bytes_to_pdf_bytes(file_bytes)
        elif "pdf" in mime:
            pdf_bytes = file_bytes
        else:
            print(f"     Skipped (unsupported type: {mime})")
            continue
        writer.append(PdfReader(io.BytesIO(pdf_bytes)))
        receipt_count += 1
    except Exception as e:
        print(f"  ✗  Failed to download receipt: {e}")

# Write final merged PDF
out_path = BANK_DIR / f"FL3XX_Report_{selected_month}.pdf"
with open(out_path, "wb") as f:
    writer.write(f)

print(f"\n✓ Combined PDF saved: {out_path}")
print(f"  Pages: 1 (table) + {receipt_count} receipt(s)")
if receipt_count < len([t for t in txs if t.get("receipt_url")]):
    print("  ⚠  Some receipts could not be downloaded — check Drive access.")
