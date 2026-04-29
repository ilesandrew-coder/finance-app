# Family Finance App — Product Specification

**Version:** 1.6
**Last updated:** 2026-04-28
**Status:** Active development — M12 complete; PWA v1 deployed

---

## 1. Overview

This document describes the evolution of the current static BOV Dashboard (a Python-generated HTML file hosted on Cloudflare Pages) into a fully interactive Progressive Web App (PWA) with cloud persistence, multi-account support, and a mobile-first interface.

The app replaces the current workflow of: CSV download → Excel → Python → static HTML with: CSV download → cloud database → live web/mobile app.

---

## 2. User Story

> Once a month, I open my laptop and import new transactions from BOV eBanking for both my accounts and Lyn's (my wife) accounts. The data is saved to a cloud database. I then use my phone (or any browser) to review uncategorised transactions, fix any mis-categorised ones, flag business or FL3XX transactions, attach receipts, check budget progress, and view spending reports — all without needing to touch a spreadsheet.

---

## 3. Users & Accounts

### Andrew
| Account | Type | Purpose |
|---------|------|---------|
| Current Account | Current | Main income + day-to-day expenses |
| Expenses Account | Current | Discretionary spending |
| Tax & SS Account | Current | Tax and social security provisioning |
| VISA Gold Account | Credit Card | Card spending |

### Lyn
| Account | BOV name | Type | Purpose |
|---------|----------|------|---------|
| Savings | "Savings" | Current | Main income received here; primary expense account |
| Ctrl+S | "Ctrl+S" | Savings | Savings dumps; linked to savings targets / buckets |
| Visa | "Visa" | Credit Card | Card spending |

### Joint
| Account | Type | Purpose |
|---------|------|---------|
| Joint Account | Savings | Shared account; both Andrew and Lyn contribute. No transactions in DB yet (M9 will add). |

### Perspectives
The app supports three viewing perspectives (M9):
- **Andrew** — Andrew's accounts + joint account
- **Lyn** — Lyn's accounts + joint account
- **Combined** — All accounts (inter-account transfers deduplicated)

Both users (Andrew and Lyn) have individual app logins. The selected perspective persists per user in localStorage.

---

## 4. Core Features

### 4.1 Monthly Import
- Triggered manually from a laptop (desktop browser or script)
- User manually logs into BOV eBanking (ebanking.bov.com) — login cannot be automated due to 2FA
- Downloads CSVs for each account, starting from the date of the last transaction for that relevant account (read from `last_import_dates.json` if present, otherwise first day of previous month)
- Supports sequential login: Andrew's accounts first, then Lyn's
- Balance is taken directly from the CSV balance column (not recalculated)
- If a gap is detected between the CSV start date and the last known transaction date, the import flags the discrepancy
- Deduplicates transactions already present in the database
- Auto-applies category rules from the category ruleset (keyword matching)
- Flags uncategorised or low-confidence transactions for review in the web app (Inbox — see §4.3)
- Maintains a running balance per account
- Assigns a `sort_order` integer to each transaction within its calendar date (0 = oldest transaction on that day, N = newest). This ensures the app always picks the correct closing balance for the day when multiple transactions share the same date. The app queries `ORDER BY date DESC, sort_order DESC` to find the most recent balance.
- After each successful import, writes `last_import_dates.json` to the Bank folder recording the last transaction date per account. Used as the "From" date for the next import without querying Supabase.

**macOS launcher:** A double-clickable `BOV Import.command` file in the Bank folder handles the full import cycle on Andrew's Mac: installs Python dependencies if missing, runs `import_to_db.py`, shows a macOS notification on completion. A `BOV Import.app` bundle wraps the .command so it can be pinned to the Dock. The app icon is a custom-designed purple credit card with a down-arrow, matching the BOV brand colour.

### 4.2 Category Management
- Categories are stored in a `categories` table in Supabase and loaded dynamically at app startup.
- The app falls back gracefully to a built-in `SYSTEM_CATEGORIES` constant if the table is unavailable (offline or not yet migrated).
- `bov_categories.json` has been retired as the authoritative category source; the file is retained as `bov_categories_REPLACED.json` for reference only.
- User can override a category for any specific transaction (stored as an override, not modifying the base rule)
- **User can create new categories** from within the app via two entry points:
  - **Inline (primary):** In the category picker, type a name that doesn't match any existing category → a "＋ Create '[name]' as new category" row appears → tap to expand a mini create-form (name + colour picker) → "Create & select" saves to DB, assigns to transaction, closes picker
  - **Manage Categories (admin):** "🏷 Manage categories" link in the picker footer opens a full Manage Categories sheet (similar to Rules Manager) — lists all categories with colour dots, Edit buttons for user-created categories, system categories shown locked, and a "＋ Add category" button
- User can edit (rename + recolour) any user-created category; renaming propagates to all matching transactions and rules in the DB
- User can delete a user-created category only if no transactions are assigned to it (the app enforces this with an error message)
- System categories (Internal Transfer, Uncategorised, Income & Refunds, Lyn Contribution, etc.) are seeded with `is_system = TRUE` and cannot be renamed or deleted via the app
- User can edit keywords for existing categories (via Rules Manager, unchanged)
- Category rules are evaluated top-to-bottom; first match wins
- Certain patterns (internal transfers, Lyn's contributions) are handled before the main ruleset

**System categories (seeded in `categories` table):**
Groceries & Supermarkets, Dining & Cafes, Fuel & Petrol, Transport, Travel & Accommodation, Utilities, Insurance, Tax & Government, Subscriptions & Digital, Healthcare, Shopping & Retail, School & Extra-curriculars, Professional Services, Loan Repayment, Bank Fees & Interest, General Expenses, ATM Withdrawal, Income & Refunds, Lyn Contribution, Internal Transfer, Uncategorised

### 4.3 Transaction Review
- Mobile-optimised interface for reviewing transactions
- Filter by: account, date range, category, person (Andrew / Lyn / Combined)
- One-tap category correction on any transaction
- Bulk re-categorise: apply a category to all transactions matching a merchant name or text string
- Search by description / merchant
- Mark transactions as reviewed

**Uncategorised Inbox:**
- Uncategorised transactions are routed to a dedicated Inbox view, separate from the main transaction list
- The app header shows a persistent badge/counter when the inbox has unactioned items
- No mobile push notifications — inbox badge is the only prompt
- Clearing the inbox (by categorising each transaction) removes items from it; they move into the main transaction list
- The main transaction list is never polluted by uncategorised items

### 4.4 Budget Management
- Monthly budgets per category (stored in the cloud database), only for those categories with budgets set
- Create new budget items
- Edit existing budget items
- Visual progress bars showing spend vs budget (with overflow representation for exceedance)
- Budget view has three modes matching the perspective toggle:
  - **Andrew view** — Andrew's budgets against his transactions (personal + joint)
  - **Lyn view** — Lyn's budgets against her transactions (personal + joint)
  - **Combined view** — all budgets side by side, with household totals
- Each perspective can have independent budget figures for the same category (e.g. Andrew and Lyn each have their own Groceries budget)

### 4.5 Spending Reports
- Monthly spending summary by category
- Month-over-month comparison
- Year-to-date totals
- Filter by account, category, date range, person
- Credit card balance trend (end-of-month balance for last N months)
- Total wealth chart (sum of all account balances over time)

### 4.6 Savings Goals (Lyn's Savings Account)
- Define named savings goals with a target amount and optional deadline
- Track progress toward each goal
- Display current balance vs goal target on dashboard
- Show estimated completion date based on current contribution rate

### 4.7 Dashboard / Overview
- Summary of current balances per account
- Budget health at a glance (how many categories are over/under)
- Inbox badge showing count of unactioned uncategorised transactions
- Credit card balance trend widget (last 3 months)
- Total wealth chart
- Savings goal progress
- Perspective toggle: Andrew / Lyn / Combined (see §3 — Perspectives)
- Help button (?) in header top-right: opens contextual help sheet (see §4.9)

### 4.8 Business & FL3XX Transaction Flags

> **Andrew's perspective only.** All B/F flag UI elements (toggle buttons, flag filter, receipt counter, Reports tab) are hidden when the app is in Lyn's perspective. The underlying database columns exist on all transactions regardless of owner.

Every transaction has two optional boolean flags:

| Flag | Values | Meaning |
|------|--------|---------|
| Business | Y / N / null | Transaction is a claimable business expense |
| FL3XX | Y / N / null | Transaction is related to FL3XX operations |

**Flagging UI:**
- The two flags are fully independent — setting one does NOT automatically set the other
- Both flags are set manually by the user only; there is no automatic flag inference
- Toggle buttons on each transaction in the review interface
- Bulk-flag by merchant name (e.g. "mark all Ryanair transactions as FL3XX")
- Flagged transactions show a badge in all list views
- Separate filter: "Show only Business" / "Show only FL3XX"

**Receipt requirement:**
Any transaction with Business = Y or FL3XX = Y requires a receipt on file. The app shows an outstanding-receipts counter in the dashboard header and prompts for missing receipts.

**Receipt storage routing** (see §5 for full details):

| Business | FL3XX | Receipt stored in | App link |
|----------|-------|-------------------|----------|
| Y | Y | Business quarterly folder | Linked to both flags; no file duplication |
| Y | N | Business quarterly folder | Business only |
| N | Y | FL3XX folder | FL3XX only |

### 4.10 Tags ✅ Implemented (2026-04-07)

Tags are a freeform cross-cutting reporting dimension — a label that can be applied to any transaction regardless of its category or account. The primary use case is grouping all spend for a bounded purpose (a trip, a renovation, a school term) to see total spend and breakdown across categories and people.

**Data model:**
- One tag per transaction (nullable). A transaction either has a tag or doesn't.
- Tags are created and assigned manually — there is no automatic tag inference.
- Tags are cross-account and cross-perspective: a tag can include transactions from both Andrew's and Lyn's accounts.

**Tags tab:**
- Dedicated tab in the navigation showing all active tags as cards
- Each card shows: tag name (coloured pill), total spend, date range, transaction count, a category-breakdown colour bar, and the Andrew/Lyn spend split
- Tapping a card opens the tag detail view
- A "Bulk tag…" button opens the bulk-tag modal

**Tag detail view:**
- Full-screen overlay showing: total spent, transaction count, duration in days
- Category donut chart with legend showing spend per category
- Andrew / Lyn split bars showing each person's portion of total spend
- Full list of tagged transactions showing date, account, description, category, and amount

**Bulk-tag modal (primary workflow):**
- Select a tag from a dropdown, or create a new tag (name + colour picker)
- Set a date range (from / to)
- Select which accounts to include (chip toggles, all selected by default)
- Preview shows all matching transactions in a scrollable list with checkboxes — uncheck any transaction to exclude it from the tag
- Preview header shows total transaction count and total spend for the selection
- "Apply tag to N transactions" button writes `tag_id` to all included transactions in a single Supabase update

**Tag chips on transactions:**
- Each tagged transaction in the Transactions tab shows a coloured tag chip below the category badge
- Untagged transactions show a faint "+ tag" prompt
- Tapping either chip opens a small floating picker to assign or change the tag for that individual transaction

**Tag filter in Transactions tab:**
- A row of filter chips appears below the account filter when at least one tag exists
- "All" chip (default) plus one chip per tag
- Selecting a tag chip filters the transaction list to show only that tag's transactions

A contextual help sheet accessible via a **?** button in the app header (top-right, between the Drive button and Sign out).

- Opens as a bottom-sheet modal (slides up from the bottom of the screen)
- Covers all features: perspectives, dashboard, inbox, transactions, flags, spending, budgets, balances, reports, Google Drive, monthly import
- **Perspective-aware:** B/F flags and Reports sections are automatically hidden when the app is in Lyn's perspective, so she only sees features relevant to her
- Written for a new user (no prior knowledge assumed) — intended primarily for Lyn onboarding
- Content is static HTML within the app (no external URL); always available offline

**Implementation note:** Elements hidden from Lyn's perspective carry a `data-andrew-only` HTML attribute. A single CSS rule `[data-perspective="lyn"] [data-andrew-only] { display:none }` controls all visibility. When M9 sets `document.body.dataset.perspective = 'lyn'`, everything snaps into place with no additional logic.

---

## 5. Receipt Management

### 5.1 Storage Architecture

**Confirmed:** Google Drive for file storage + Supabase for metadata.

| Component | Role |
|-----------|------|
| Google Drive | Physical file storage; two top-level areas: Business (quarterly folders) and FL3XX (flat folder) |
| Supabase DB | Stores Drive file URL linked to transaction ID; no file is ever duplicated |
| PWA (desktop) | User selects/captures the receipt file; the app auto-uploads to the correct Drive folder and stores the link |

Receipt upload and Drive folder creation are handled automatically by the app — the only manual step is the user selecting or photographing the receipt file.

### 5.2 Folder Structure

**Business receipts** are organised by VAT return quarter:

| Folder name | Period |
|-------------|--------|
| `Business/YYYY-Q4_Nov-Jan/` | November (prior year) – January |
| `Business/YYYY-Q1_Feb-Apr/` | February – April |
| `Business/YYYY-Q2_May-Jul/` | May – July |
| `Business/YYYY-Q3_Aug-Oct/` | August – October |

Year in folder name = the calendar year of the majority of months in the period.
Example: Nov 2025 – Jan 2026 → `Business/2025-Q4_Nov-Jan/`

**FL3XX receipts** are kept in a single flat folder (no quarterly subfolders needed since the report is monthly):

`FL3XX/`

**No file is ever duplicated.** When a transaction has both B = Y and F = Y, the file is stored once in the Business quarterly folder; the app stores that same Drive URL against the FL3XX flag in Supabase.

### 5.3 Receipt Attachment Workflow

There is no need to manually upload anything to Google Drive beforehand. The app handles the entire upload from whatever file the user already has on their device.

**End-to-end flow:**

1. A transaction is imported from the monthly BOV CSV as normal
2. The user opens the app, finds the transaction, and taps **B** or **F** to flag it as Business/FL3XX
3. A dashed **📎 Attach receipt** button appears on that transaction row
4. The user taps it — the device opens a **file picker** (desktop) or **camera/file browser** (mobile); no Drive interaction yet
5. The user selects the receipt from wherever it currently lives: camera roll, Downloads folder, a PDF saved from email, or a photo taken on the spot
6. On first use per session, a Google sign-in popup appears; the user approves Drive access once
7. The app automatically determines the correct destination folder from the B/F flag combination (see routing table in §4.8), creates the folder in Drive if it doesn't exist yet, and uploads the file with a clean sortable filename (`YYYY-MM-DD_description_amount.ext`)
8. The Drive URL is saved in Supabase against the transaction; the 📎 button changes to a green **📎 Receipt ↗** chip
9. The outstanding-receipts counter in the header decrements; when all flagged transactions have receipts it disappears

**Receipt sources supported:** photo taken on phone, image or PDF saved from email, downloaded file from a supplier website, scanned physical copy.

**No duplication:** when a transaction has both B = Y and F = Y, the file is uploaded once to the Business quarterly folder; that same Drive URL covers both flags.

**Replacing or removing a receipt (M14):** tapping the green **📎 Receipt ↗** chip opens an inline action sheet with three options: View receipt (opens Drive), Replace receipt (upload new file — follows same folder/naming logic as the original upload), Remove receipt (two-step confirm before clearing). Tapping anywhere outside the menu closes it.

### 5.4 Business Report

Generated on demand per VAT quarter from the **Reports tab** in the web app:
- Filters all transactions with Business = Y in the selected quarter (Malta VAT quarters: Q1 Feb–Apr, Q2 May–Jul, Q3 Aug–Oct, Q4 Nov–Jan)
- Produces an A4 landscape PDF: dated header, transaction table (Date / Description / Category / Amount / Receipt), total row
- **Prepare descriptions step (M12):** before generating, tap "Review & edit descriptions" to enter a manual `report_description` per transaction. This text appears in the PDF instead of the raw bank import text. Descriptions are saved to Supabase and persist across sessions. If `report_description` is blank, the original bank description is used as fallback.
- Receipt column shows "View receipt ↗" as a clickable link (URL stored in Drive); blank if no receipt attached
- Total appears as a prominent dark table row at the bottom of the Amount column (not a footer)
- PDF title: **Business Expenses Report** (no "Family Finance —" prefix)
- **Two generate buttons (M13):** "↓ Generate PDF" (table only) and "↓ PDF + Receipts" (table + all receipt attachments appended in date order as subsequent pages)
- Generated entirely in the browser using jsPDF + autoTable + pdf-lib; no Python required

### 5.5 FL3XX Report

Two-part output generated for a selected month:

Generated from the Reports tab, same format as the Business report (including Prepare descriptions step) but filtered to FL3XX = Y transactions. PDF title: **FL3XX Expenses Report**. Columns: Date / Description / Amount / Receipt (no Account or Category columns).

**Two generate buttons (M13):**
- **↓ Generate PDF** — transaction table only; downloaded immediately
- **↓ PDF + Receipts** — transaction table as cover page(s), then each receipt appended in date order as subsequent pages. Receipts are downloaded from Google Drive via the Drive API (requires Drive to be connected via the ☁️ button). PDF receipts are merged directly; image receipts (JPEG, PNG) are embedded as A4 landscape pages. Combined file saved as `FL3XX_Report_YYYY-MM_with_receipts.pdf`.

---

## 6. Technical Architecture

### 6.1 Recommended Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Database | Supabase (PostgreSQL) | Cloud-hosted, free tier sufficient initially |
| File storage | Google Drive | Receipt files; 15 GB free; shareable with accountant |
| Auth | Supabase Auth | Email/password (implicit flow) |
| Backend API | Supabase auto-generated REST + PostgREST | No custom server needed initially |
| Frontend | PWA (HTML + JS + CSS) | No app store; works on iOS/Android/desktop |
| Import script | Python (existing codebase) | Runs on laptop; pushes to Supabase via API |
| Report generation | Python (pypdf / fpdf2) | Runs on laptop or as a Supabase Edge Function |
| Hosting | Cloudflare Workers (Static Assets) | `wrangler.toml` with `assets = { directory = "." }`; deploy via `npx wrangler deploy` |

### 6.2 Database Schema (draft)

**accounts** — account metadata (`id, owner, name, type, currency`)
- `owner` values: `'andrew'` | `'lyn'` | `'joint'`
- All existing rows (pre-M9): `owner = 'andrew'`, except the joint account which gets `owner = 'joint'`
- Lyn's accounts added in M9: Savings, Ctrl+S, Visa — all `owner = 'lyn'`

**transactions** — one row per transaction:
`id, account_id, date, description, amount, balance, sort_order, tag_id, category, category_source, business_flag, fl3xx_flag, reviewed, receipt_url, created_at`
- `sort_order` — integer assigned by the import script; 0 = oldest transaction on that calendar date for this account, N = newest. Used as secondary sort key (`ORDER BY date DESC, sort_order DESC`) so the app reliably identifies the day's closing balance when multiple transactions share the same date.
- `tag_id` — nullable FK to `tags.id`; `ON DELETE SET NULL`. One tag per transaction.

**categories** — user-manageable category list (`id, name, color, is_system, sort_order, created_at`)
- `is_system = TRUE` rows are seeded at migration time; the app prevents rename/delete of these rows
- `color` is a hex string chosen from the app's colour palette
- `sort_order` controls the order categories appear in all pickers and dropdowns

**category_rules** — keyword rules (id, category_name, keyword, priority, created_at)

**category_overrides** — per-transaction overrides (transaction_id, category, overridden_by, overridden_at)

**budgets** — monthly budget items (`id, category, amount, month, person_scope`)
- `person_scope` values: `'andrew'` | `'lyn'` — each perspective has its own budget rows for each category

**savings_goals** — savings targets (id, account_id, name, target_amount, deadline, created_at)

**tags** — user-created tag labels (`id, name, color, created_at`)
- `name` is unique; `color` is a hex string
- Tags are created from within the app (bulk-tag modal or single-transaction picker)

**transactions** additional columns (M12):
- `report_description TEXT` — manually entered description used in B & F PDF reports in place of the imported `description`. NULL = use `description` as fallback. Edited from the Prepare descriptions overlay in the Reports tab.

**import_log** — audit trail of imports (id, account_id, imported_at, rows_added, rows_skipped)

### 6.3 Import Pipeline

```
BOV eBanking (browser)
    → CSV download (per account)
    → Python import script (laptop)
        → Parse & deduplicate
        → Apply category rules
        → Push to Supabase via REST API
    → PWA reflects new data immediately
```

### 6.4 PWA Delivery
- Installable on iOS (Add to Home Screen) and Android
- Offline read capability via service worker caching
- Push notifications (optional, future): e.g. "3 uncategorised transactions this month"
- Single codebase for mobile and desktop

---

## 7. Delivery Milestones

| # | Milestone | Description |
|---|-----------|-------------|
| M1 | Database setup | Create Supabase project; define schema; seed with existing Excel data |
| M2 | Import script | Python script reads CSVs, pushes to Supabase, deduplicates |
| M3 | Read-only PWA | Dashboard displaying balances, spending, budgets from live DB |
| M4 | Category review UI | Mobile UI to review/fix transaction categories |
| M5 | Budget management | Create/edit budgets; progress bars |
| M6 | Category rule editor | Manage keyword rules from within the app |
| M7 | Business & FL3XX flags | Flag transactions; receipt attachment; outstanding-receipts counter |
| M8 | Report generation | Business report (renamed files) + FL3XX combined PDF |
| M9 | Lyn's accounts & perspective toggle | Add Lyn's accounts to DB; Andrew/Lyn/Combined segmented control in header; perspective-aware filtering throughout; Andrew-only UI hidden in Lyn's view; per-perspective budgets; bov-import skill updated for Lyn's CSVs |
| M10 | Savings goals UI | Goal tracking, progress, estimated completion |
| M11 | Tags | Cross-cutting transaction labels for trip/project/event spend tracking. Tags tab, bulk-tag modal, tag detail view with category donut + person split, tag chips on transactions, tag filter. See §4.10. |
| M12 | Report improvements | `report_description` field on transactions; Prepare descriptions overlay in Reports tab; PDF total as table row; receipt column as clickable link; report titles no longer prefixed with "Family Finance —"; receipt Drive links fixed (files now shared as "anyone with link"); tag save freeze fixed. |
| M13 | PDF + Receipts merge | "↓ PDF + Receipts" button on both report cards and overlay — downloads a single PDF with the report table as the cover + all receipt attachments appended in date order (PDF receipts merged natively, image receipts embedded as landscape pages). Account column removed from both reports. Total row cropping fixed (margin + rowPageBreak). |
| M14 | Receipt replace/remove | Tapping the receipt chip opens an inline action sheet: View (Drive), Replace (new upload), Remove (two-step confirm). Closes on outside tap. |

---

## 8. Decisions Log

Previously open questions, now resolved:

| Question | Decision |
|----------|----------|
| Lyn login | Separate login for Lyn |
| Balance source of truth | Use balance column directly from CSV; flag any detected gap between CSV start date and last known transaction date; store last closing balance per account for cross-check |
| BOV login automation | Cannot automate — BOV uses 2FA; manual CSV download required |
| Excel file as backup | Keeping Excel adds ~5–10s process time per import run and additional token usage in the current workflow. It can remain during the transition period but should be retired once Supabase is the source of truth (at M2). Bypassing it makes the import leaner. |
| Monthly-variable budgets | Deferred — see §13 Later Updates |
| Savings buckets | Savings goals linked to specific accounts (confirmed). Savings buckets (splitting an account balance across named goals) deferred — see §13 Later Updates |
| Uncategorised notifications | Inbox concept (see §4.3): badge counter only, no mobile push notifications |
| Receipt storage | Google Drive confirmed |
| B & F flags independent | Yes — flags are fully independent and set manually only; no automatic inference |
| Report generation access | Andrew only, from desktop/laptop via the web app |
| B/F flags visibility for Lyn | Hidden — Lyn's perspective suppresses all B/F flag UI, receipt counter, Reports tab, and flag filter. B/F columns exist in DB for all transactions but Lyn has no UI to interact with them. |
| Budget views | Separate per-perspective (Andrew / Lyn have independent budgets per category) with a Combined toggle showing household totals |
| Perspective persistence | Stored in `localStorage` keyed by user email so each user's last-used perspective is remembered across sessions |
| Perspective label | "Household" renamed to "Combined" throughout the app and spec |
| Lyn's BOV account names | Savings (main income/expenses), Ctrl+S (savings dumps), Visa (credit card). Joint account is shared with Andrew. |
| Andrew's existing accounts owner field | All existing `accounts` rows get `owner = 'andrew'` except the joint account which gets `owner = 'joint'`. No ambiguity — all pre-M9 data is Andrew's. |

---

## 9. Cost Estimate

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| Supabase | 500 MB DB, 2 GB bandwidth/month | $25/month for Pro |
| Cloudflare Pages | Unlimited bandwidth, 500 builds/month | Free tier (Pro $20/month) |
| Google Drive | 15 GB storage | €2.99/month for 100 GB |
| Domain (optional) | — | ~€12/year |

**Expected cost at current scale: €0/month** (well within free tiers for a personal finance app)

---

## 10. Out of Scope (v1)

- Automatic bank sync (Open Banking API) — BOV does not support this
- Multi-currency support (all accounts are EUR)
- Investment portfolio tracking
- Shared access for third parties (accountant, etc.) — reports are exported instead
- OCR / automatic text extraction from receipt images

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| Internal Transfer | Transaction moving money between Andrew's own accounts — excluded from spending totals |
| Lyn Contribution | Lyn's transfers to Andrew's accounts to cover shared costs — treated as income |
| Combined view | Perspective showing all accounts (Andrew's + Lyn's + joint), with inter-account transfers deduplicated so they don't inflate spending totals. Formerly called "Household view". |
| Andrew-only feature | A UI element hidden when the app is in Lyn's perspective. Marked in code with `data-andrew-only`. Currently: B/F flag buttons, flag filter, receipt counter, receipt attachment, Reports tab and help sections. |
| Category override | A manual category assignment for a specific transaction, taking precedence over keyword rules |
| Business flag | Marks a transaction as a claimable business expense requiring a receipt |
| FL3XX flag | Marks a transaction as FL3XX-related requiring a receipt |
| VAT quarter | One of four 3-month periods matching Malta's VAT return schedule: Nov-Jan, Feb-Apr, May-Jul, Aug-Oct |
| PWA | Progressive Web App — a website installable on a phone's home screen, behaving like a native app |

---

## 13. Future Releases

Features agreed in principle but deferred from v1 scope. Version numbering convention: static HTML dashboard = v0.x; first PWA = v1.x; each future release below is a new major version.

---

### v2 — Monthly-variable budgets + Savings buckets

**Monthly-variable budgets:** The current design uses a single fixed monthly budget amount per category (`month = null` in the `budgets` table). v2 would allow the budget amount to vary by month — for example, a higher Travel budget in summer. This requires converting the schema from a single global row per category to per-month rows, and updating the budget UI to support month-specific editing.

**Savings buckets:** The current design supports savings goals linked to a specific account (e.g. Lyn's savings account). v2 would allow the account balance to be split across named buckets (e.g. €1,000 towards "Holidays", €1,000 towards "Renovations"), with each bucket's progress tracked independently of the total account balance.

---

### v3 — Budget historical view

User story: as a user, I want to select a past month and see my actual spending compared to the budget that was set for that specific month — not today's budget figure.

The current budget architecture stores one global figure per category (`month = null`), so changing a budget today retroactively alters every historical comparison. Implementing this feature would require converting from global budget rows to per-month budget snapshots (i.e. locking in the budget amount for each month at the time of import or at month close). The Budget tab already shows spend-vs-budget for the selected month; the historical view would extend this with a multi-month comparison — for example, a chart showing 6 months of budgeted vs. actual spend per category, using the budget figure that was actually in force for each respective month.

Note: v3 depends on v2 (monthly-variable budgets schema) being in place first, since the historical view only makes sense once per-month budget snapshots exist.

---

### v4 — Email & password login ✅ Implemented (2026-03-11)

~~The current login uses Supabase magic links (a one-time sign-in link sent by email). v4 would replace this with a conventional email + password form.~~

Implemented. The login now uses email + password with a full password-reset flow. Magic link auth has been removed. Supabase Auth `flowType` changed to `implicit` to avoid PKCE verifier issues on PWA/iOS. The login screen has three sub-views: sign-in, forgot password (sends reset link), and set-new-password (shown after clicking reset link in email).

---

### PWA implementation notes (as of v1.0, 2026-03-11)

These features have been built into the live PWA and are not separate future releases — they describe the current implemented state:

**Mobile-first responsive layout.** A hamburger menu (☰) replaces the tab bar on screens narrower than 768px. A slide-in drawer contains all navigation items, perspective toggle, Drive, Help, and Sign out. The header is a 2-row layout on mobile (row 1: hamburger + title, row 2: perspective pills). Safe-area padding uses `env(safe-area-inset-top)` for compatibility with Dynamic Island and notch devices. Desktop layout (≥769px) is unchanged. The `data-andrew-only` visibility mechanism works identically in the drawer via existing CSS.

**Pull-to-refresh.** Swipe down from the top of the screen to trigger a data refresh (calls `loadAll()`). A small indicator animates from off-screen, showing a down-arrow while pulling, flipping to up-arrow when the threshold is reached, then switching to a spinner while loading. Rubber-band easing makes the pull feel native.

**Period picker (replacing month picker).** All tabs use a period dropdown (1 month / 2 months / 3 months / 6 months / 1 year) instead of a calendar month-picker input. Dashboard, Spending, and Budgets share a single `sharedPeriod` state; the dropdown appears in each of those three tabs and is kept in sync. Transactions has its own independent `txPeriod` state. The ← → arrows advance by the selected period (e.g. clicking ← with "3 months" selected moves back 3 months). Budget amounts are scaled by the period (e.g. a €400/month budget shows as €1,200 when 3 months is selected, labelled `€400×3`).

**Spending drill-down.** Clicking a category row in the Spending tab navigates directly to the Transactions tab filtered by that category and the same month, making it easy to inspect individual transactions behind a spending figure.

**Tab order.** Navigation order: Dashboard → Spending → Transactions → Budgets → Balances → Tags → Inbox → Reports.

**Tags tab (M11, 2026-04-07).** See §4.10 for full feature description. The CSS variable `--purple: #6B1C5E` is defined in `:root` for use across tag UI elements.

**Supabase keep-alive (2026-04-07).** Supabase free tier pauses projects after 7 days of database inactivity. Two mechanisms prevent this:
1. **pg_cron** — a scheduled PostgreSQL job (`cron.schedule('keep-alive', '0 12 */4 * *', $$SELECT count(*) FROM accounts$$)`) runs every 4 days at noon entirely inside Supabase. Enable the pg_cron extension first via Dashboard → Database → Extensions.
2. **UptimeRobot** — monitors `https://[project].supabase.co/rest/v1/accounts?select=id&limit=1&apikey=[ANON_KEY]`. The anon key is passed as a URL parameter (free UptimeRobot does not support custom headers). This returns HTTP 200 with an empty array (RLS filters all rows) and counts as a real database query. Check interval: 5 minutes.

**Demo mode.** Visiting the app URL with `?demo` appended bypasses authentication entirely and loads realistic fictional EUR/Malta data. All interactive features work in demo mode: categorisation, B/F flags, bulk operations, budget editing. A yellow banner identifies demo mode. Supabase is never called.

---

### v5 — Automatic BOV transaction download via Open Banking

**Status: aggregator research complete — Salt Edge application submitted, awaiting approval.**

BOV is confirmed to support the EU PSD2 Open Banking standard. BOV publishes its own developer documentation at `openbanking.bov.com/docs/berlingroup/bov_mt` (NextGenPSD2 / Berlin Group v1.3.6 standard) and a TPP Portal at `bov.com/content/tpp-portal`, including a sandbox environment. Direct integration via the BOV API is technically feasible but requires a QSEAL eIDAS certificate and formal TPP registration — both designed for licensed business entities, not individual developers.

**How it would work (via aggregator):**

Rather than manually logging into BOV and downloading CSVs each month, the user would tap a "Sync" button in the app. On first use (and periodically thereafter, roughly every 90 days as required by PSD2), a redirect takes them to BOV's login page where they authenticate normally including 2FA. After that consent is granted, the aggregator's API can pull transaction data and balances on demand with no further bank logins needed.

**The workflow change:**

| Current (v1) | v5 |
|---|---|
| Login to BOV → download 4 CSVs → run Python import script | Tap "Sync" in app → bank login + 2FA once per 90 days → transactions fetched automatically |
| ~10 minutes of manual work per month | ~30 seconds, mostly waiting |

**The 2FA issue is resolved** by PSD2's consent model — the OTP is only needed once every ~90 days for re-authorisation, not on every sync.

**Aggregator research findings (March 2026):**

| Aggregator | Status | Notes |
|---|---|---|
| GoCardless (formerly Nordigen) | ❌ Closed to new accounts from July 2025 | Was the obvious choice; BOV confirmed supported; no longer available for new sign-ups |
| Enable Banking | ❌ BOV not supported | Finnish aggregator; only HSBC Malta listed for Malta coverage — BOV excluded |
| Salt Edge | ✅ BOV confirmed in coverage — **application submitted** | 5,000+ banks, 50+ countries; Malta explicitly listed; BOV confirmed in their bank list. API access application submitted March 2026, awaiting approval. May require business entity registration. |
| TrueLayer | ❌ Malta not supported | Listed countries do not include Malta |
| Tink (Visa) | 🔍 Malta in principle, BOV unverified | Pan-EU provider; Malta accessible but BOV-specific coverage not confirmed |
| Yapily (Visa Open Banking) | 🔍 Malta accessible, BOV unverified | Large pan-EU provider; needs direct confirmation of BOV support |
| finAPI | ❌ Malta not supported | Explicitly lists 13 countries; Malta not among them |
| Plaid, Kontomatik, TrueLayer | ❌ | Malta not in coverage for any of these |
| BOV direct API | 🔍 Possible but high friction | Requires QSEAL cert + TPP registration; designed for licensed businesses, not individuals |

**Key constraint — regulatory:** PSD2 was designed for licensed service providers (AISPs), not individual personal apps. Every aggregator requires business registration. This may limit personal-use access even where technical coverage exists. Salt Edge application will clarify whether individual developer accounts are permitted.

**Next step:** Await Salt Edge API approval response. If approved, integrate their AIS (Account Information Services) API: add an "Authorise with BOV" flow to the PWA, replace the Python CSV import with an API call. If Salt Edge requires a business entity, assess whether Tink or Yapily support BOV and accept individual accounts. Estimated effort: one full milestone once the aggregator is confirmed.

---

### v6 — Budget look-ahead (cash flow forecast)

**Status: agreed in principle — design pending.**

**User story:** As a user, I want to open the app mid-month and see a forward-looking view of the current (and optionally next) month — not just how I've spent so far, but what I expect to spend and earn for the rest of the period, so I can see whether I'm heading for a surplus or shortfall before it happens.

**What this is not:** The existing Budget tab already shows actual-vs-budget spend for the selected month. v6 is a *forward projection* layer on top of that — it combines committed recurring items (known future outgoings) with remaining budget headroom to forecast the end-of-month position.

**Core concept — the look-ahead view:**

The view has two halves for the current month:
- **Income side:** expected income (salary, rental income, any other regular credits) with actuals filled in as the month progresses
- **Expense side:** broken down at the individual recurring-item level (not just top-level category), plus remaining budget headroom for variable categories

The result is a projected end-of-month net figure: *Expected income − Committed outgoings − Remaining variable budget = Projected surplus / (shortfall)*.

**Recurring item detection:**

Rather than asking the user to manually enter a list of expected transactions, v6 would auto-detect recurring items from transaction history: any transaction where the same description appears in 3 or more consecutive months within ±5 days of the same day-of-month is flagged as recurring. The user can confirm, dismiss, or edit these suggestions. Confirmed recurring items are stored in a new `recurring_items` table and used to populate the look-ahead.

**Granularity:**

Unlike the current Budget tab (which groups spend by category against a single monthly target), the look-ahead shows at least two levels:

| Level | Example |
|---|---|
| Income line items | Salary — Andrew; Rental income |
| Fixed expense line items | Bolt rent; Netflix; ARMS direct debit; loan repayment |
| Variable expense categories | Groceries: €320 spent, €80 remaining budget; Dining: €95 spent, €105 remaining |
| Projected net | +€ 420 expected surplus |

**As the month progresses**, matched actual transactions replace their corresponding recurring placeholders, so the forecast tightens into actuals.

**Schema additions (indicative):**

A new `recurring_items` table:

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `user_id` | uuid | FK to auth.users |
| `description` | text | Display label |
| `amount` | numeric | Expected amount (positive = income, negative = expense) |
| `category` | text | Category tag |
| `account_id` | uuid | FK to accounts |
| `day_of_month` | int | Expected day (1–31) |
| `active` | bool | Whether to include in forecasts |
| `auto_detected` | bool | True if surfaced by detection algorithm |

**Dependency on v2:** v6 is more useful after v2 (monthly-variable budgets) is in place, since the variable-budget headroom figures will then be month-specific. v6 can be built before v2, but forecast accuracy for variable categories will be limited to the single global budget figure.

**Estimated effort:** one to two milestones (recurring item detection + look-ahead UI).

---

### v7 — Spending & cash flow notifications

Two alert types surfaced as in-app banners on the dashboard (and optionally as push notifications once PWA push support is added in a later version):

**Alert 1 — Budget pace overspend**

Triggers when actual spend in a category exceeds its proportional expected spend for the point in the month.

Formula: `alert if actual_spend > (monthly_budget × days_elapsed / days_in_month)`

Example: on day 15 of a 30-day month (50% through), if €600 of a €1,000 Groceries budget is already spent, the alert fires because 60% of budget is consumed at only 50% of the month elapsed.

- Shown as a warning card on the dashboard per affected category
- Threshold configurable (e.g. alert at 110% of pace, not exactly 100%, to avoid noise)
- Perspective-aware: alerts shown per the active Andrew / Lyn / Combined view
- Depends on: budgets being set for the relevant categories

**Alert 2 — Insufficient funds for upcoming payment**

Triggers when a known recurring/hard payment is due within N days and the source account's current balance is insufficient to cover it.

Example: Bolt rent of €X is due on the 1st; on the 28th, if the current account balance is below €X, an alert fires.

- Based on confirmed recurring items (requires v6 recurring items table to be in place)
- Only fires for account-specific payments (where a source `account_id` is known)
- Shows expected payment date, amount, account, and current shortfall
- Dismissible per occurrence

**Estimated effort:** small–medium; Alert 1 can be built independently of v6; Alert 2 depends on v6.

---

### v8 — Investment portfolio

A new read-only (initially manual-entry) section for tracking family investments. No live market data in v1 — values are entered and updated manually.

**Core concept:**

A single investment instrument (e.g. a Malta Government Stock, a unit trust, a property) may be owned jointly by different family members in different proportions. The investments section needs to reflect both the total instrument value and the individual allocation per person.

**Schema additions:**

`investments` table:
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `name` | text | e.g. "MGS 4.5% 2031", "Medina Property" |
| `type` | text | stock / bond / fund / property / savings / other |
| `currency` | text | Default EUR |
| `total_value` | numeric | Current total market/book value |
| `maturity_date` | date | For fixed-term instruments (null if open-ended) |
| `fixed_rate` | numeric | Annual interest/yield rate (null if variable) |
| `notes` | text | Free text |
| `created_at` | timestamptz | |

`investment_allocations` table — who owns what share of each investment:
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `investment_id` | uuid | FK to investments |
| `person` | text | 'andrew' / 'lyn' / 'joint' |
| `amount` | numeric | Absolute amount (not percentage, to avoid rounding issues) |

`investment_income` table — dividends, interest payments, coupons received:
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `investment_id` | uuid | FK to investments |
| `date` | date | Payment date |
| `amount` | numeric | Gross amount received |
| `type` | text | 'dividend' / 'interest' / 'coupon' |
| `description` | text | Optional notes |

**UI:**

- New **Investments** tab (or sub-section of Dashboard)
- List view of all investments with: name, type, total value, Andrew's share, Lyn's share
- Perspective-aware: Andrew view shows his allocation; Lyn view shows hers; Combined shows everything
- For fixed-term instruments: shows interest paid to date, interest remaining (based on rate × remaining term), and maturity date countdown
- Income log: chronological list of dividends/interest received per instrument
- Summary: total portfolio value, split by person and by asset type
- Manual entry form to add/edit investments and log income payments (no CSV import in v1)

**Out of scope for v8:** live price feeds, brokerage API integration, unrealised gain/loss tracking, tax reporting.

---

## 14. Operational Notes

### 14.1 Supabase Free Tier — Project Pausing

Supabase automatically **pauses** a free-tier project after **7 consecutive days with zero API requests**. When paused:
- All API calls return errors (dashboard shows no data)
- Data is fully preserved; the project resumes in ~30 seconds
- You can manually unpause from the Supabase dashboard at any time

**In practice the risk is low** — every time you open the PWA or run the monthly import, API calls are made and the 7-day timer resets.

**Keepalive strategy — UptimeRobot (recommended, free, laptop-independent):**

UptimeRobot is a free external monitoring service that pings a URL from their servers every 5 minutes, 24/7, regardless of whether your laptop is on.

Setup (one-time, ~3 minutes):
1. Go to **https://uptimerobot.com** and create a free account.
2. Click **Add New Monitor** → **HTTP(s)**.
3. Set the URL to:
   ```
   https://zdromvjncrgagwizilrz.supabase.co/rest/v1/accounts?select=id&limit=1
   ```
4. Under **Custom HTTP Headers**, add:
   - `apikey` : `sb_publishable_os1S9GRrnpe7ddJerK-b7g_0LpDMnOF`
   - `Authorization` : `Bearer sb_publishable_os1S9GRrnpe7ddJerK-b7g_0LpDMnOF`
5. Set monitoring interval to **every 60 minutes** (more than enough).
6. Click **Create Monitor**.

This makes a single lightweight read (one row from the `accounts` table) once per hour. Supabase never pauses as long as UptimeRobot is active.

> If you upgrade Supabase to the Pro plan ($25/month), project pausing is disabled entirely and this workaround is no longer needed.

---

## 12. Revision History

| Version | Date | Notes |
|---------|------|-------|
| 0.1 | 2026-03-06 | Initial draft based on planning session |
| 0.2 | 2026-03-07 | Added Business & FL3XX flags, receipt management (§4.8, §5); Lyn references throughout; updated schema, milestones, glossary; restored user edits: Joint Account, perspectives, import detail, bulk re-categorise, budget qualifier |
| 0.3 | 2026-03-07 | FL3XX report changed to monthly; revised receipt folder structure (Business quarterly / FL3XX flat, no duplication); added B/F routing table; inbox concept (§4.3); 2FA/manual import note; resolved all open questions → Decisions Log (§8); added §13 Later Updates (variable budgets, savings buckets) |
| 0.4 | 2026-03-08 | Expanded §5.3 Receipt Attachment Workflow with full end-to-end UX description; restructured §13 as versioned future releases (v2–v5) with email/password login and automatic BOV sync research added |
| 0.5 | 2026-03-08 | Updated v5 with Open Banking research findings: BOV confirmed PSD2-compliant; GoCardless closed to new accounts July 2025; Enable Banking identified as primary candidate to verify; workflow comparison table added |
| 0.6 | 2026-03-09 | Added v6 — Budget look-ahead (cash flow forecast): recurring item auto-detection, income/expense line-item granularity, projected end-of-month net position, indicative schema |
| 0.7 | 2026-03-09 | App renamed BOV Finance → Family Finance. Lyn's account names confirmed (Savings, Ctrl+S, Visa). Joint account noted as not yet imported. Perspectives renamed: Household → Combined. M9 confirmed: separate per-perspective budgets with combined toggle; Lyn gets own login; perspective persists per user. Help page added. |
| 0.8 | 2026-03-09 | Pre-M9 spec update. Added §4.9 Help Page (implementation detail + `data-andrew-only` pattern). §4.4 budget views expanded (Andrew / Lyn / Combined modes). §4.8 Andrew-only callout added. §6.2 accounts.owner and budgets.person_scope clarified. M9 milestone description updated. Decisions Log expanded with 7 new M9 decisions. Glossary: "Household view" replaced with "Combined view" and "Andrew-only feature" added. §7 M9 milestone fully described. |
| 0.9 | 2026-03-11 | Marked v4 (email/password login) as implemented. Added v7 — Spending & cash flow notifications (budget pace alert + insufficient funds alert). Added v8 — Investment portfolio (manual-entry, multi-owner allocations, fixed-term tracking, dividend/interest income log). |
| 1.0 | 2026-03-11 | PWA v1 live. Updated hosting from Cloudflare Pages to Cloudflare Workers Static Assets (`wrangler.toml`). Added PWA implementation notes section covering: mobile responsive layout (hamburger drawer, safe-area padding), pull-to-refresh gesture, period picker (1m/2m/3m/6m/1y replacing month picker across all tabs), spending-to-transactions drill-down, tab reorder, and demo mode (`?demo`). |
| 1.1 | 2026-03-12 | v5 Open Banking research complete. Enable Banking ruled out (BOV not in Malta coverage). Full aggregator landscape researched — Salt Edge confirmed BOV in coverage, API access application submitted March 2026 awaiting approval. BOV direct API documented (NextGenPSD2 / Berlin Group at openbanking.bov.com) but requires QSEAL cert + TPP registration. Regulatory constraint noted: PSD2 designed for licensed AISPs, may block individual developer access. |
| 1.2 | 2026-03-14 | Dynamic categories. `categories` table added to Supabase schema with seed data for all system categories. `bov_categories.json` retired (renamed `bov_categories_REPLACED.json`). `CATEGORIES` JS constant replaced with a `let` variable populated by `loadCategories()` at startup, falling back to `SYSTEM_CATEGORIES` if the table is unavailable. Two new entry points for creating categories: inline "＋ Create" row in the picker (appears on no-results search), and a "🏷 Manage Categories" sheet accessible from the picker footer. Manage Categories sheet supports add, rename+recolour, and delete (guarded by zero-usage check). Rename propagates to all matching transactions and category_rules in DB. §4.2 and §6.2 updated accordingly. |

---

*This document is the living specification for the Family Finance App. Update it whenever requirements change before beginning implementation of any milestone.*
