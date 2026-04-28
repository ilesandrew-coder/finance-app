# BOV Finance App — M1 Setup Guide

This folder contains the database schema and seeding script for Milestone 1.
Follow the steps below from top to bottom.

---

## Step 1 — Create a Supabase account and project

1. Go to **https://supabase.com** and sign up for a free account.
2. Click **New project**.
3. Fill in:
   - **Name:** `bov-finance` (or anything you like)
   - **Database password:** choose a strong password and save it somewhere safe
   - **Region:** `West EU (Ireland)` — closest to Malta
4. Click **Create new project** and wait ~2 minutes for it to provision.

---

## Step 2 — Get your API credentials

1. In your project, go to **Project Settings** (gear icon, bottom-left).
2. Click **API** in the left sidebar.
3. Copy two values:
   - **Project URL** — looks like `https://abcdefghijkl.supabase.co`
   - **service_role** key — the long JWT starting with `eyJ...`
     ⚠️ Keep this secret. It bypasses all security rules and is only for local scripts.

---

## Step 3 — Set up your credentials file

1. In this folder (`Bank/supabase/`), duplicate the file `.env.example` and rename the copy to `.env`.
2. Open `.env` and paste your Project URL and service_role key into the correct fields.

---

## Step 4 — Run the schema SQL

1. In Supabase, click **SQL Editor** (left sidebar).
2. Click **New query**.
3. Open the file `Bank/supabase/schema.sql` in a text editor, copy the entire contents, and paste into the SQL editor.
4. Click **Run** (or press Cmd+Enter / Ctrl+Enter).
5. You should see `Success. No rows returned.` — this means all tables were created.

To verify: click **Table Editor** in the left sidebar. You should see 7 tables:
`accounts`, `transactions`, `category_rules`, `category_overrides`, `budgets`, `savings_goals`, `import_log`.

---

## Step 5 — Install Python dependencies

Open Terminal, navigate to this folder, and run:

```bash
pip install supabase python-dotenv openpyxl --break-system-packages
```

---

## Step 6 — Run the seeding script

From the `Bank/supabase/` folder, run:

```bash
python seed.py
```

The script will:
- Create 8 account records (Andrew's 4 accounts + Lyn's 3 placeholders + Joint)
- Import all transactions from `Bank_Transactions.xlsx` (~350 rows)
- Seed category keyword rules from `bov_categories.json`
- Seed default monthly budgets from the Budgets sheet

Expected output:
```
=======================================================
  BOV Finance App — M1 Seeding Script
=======================================================
▸ Seeding accounts...
  ✓ 8 accounts ready
▸ Seeding transactions...
  ▸ Current Account...
    ✓ 143 inserted
  ▸ Expenses...
    ✓ 100 inserted
  ...
✅ M1 seeding complete!
```

---

## Step 7 — Verify the data

1. In Supabase, click **Table Editor**.
2. Click `transactions` — you should see all your historical transactions.
3. Click `accounts` — you should see 8 accounts.
4. Click `category_rules` — you should see ~60 keyword rules.
5. Click `budgets` — you should see your monthly budget defaults.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `SUPABASE_URL and SUPABASE_SERVICE_KEY must be set` | Check that `.env` exists in the `supabase/` folder and contains the correct values |
| `supabase` module not found | Run `pip install supabase --break-system-packages` |
| Tables already exist error from SQL | Safe to ignore — schema uses `IF NOT EXISTS` |
| Duplicate transactions warning | The script detected existing data; only type `yes` if you deliberately want to add more |

---

## What's next — M2

See `import_to_db.py` for the monthly import script (M2). Run `python3 import_to_db.py --last-dates` to check last import dates, and `python3 import_to_db.py` to import new CSVs from Downloads.

---

# M3 Setup Guide — Read-only PWA Dashboard

The PWA lives in `Bank/app/index.html`. Follow these steps to get it running.

---

## M3 Step 1 — Enable Row Level Security

1. In Supabase, go to **SQL Editor** → **New query**.
2. Copy the contents of `Bank/supabase/rls.sql` and paste into the editor.
3. Click **Run**.
4. You should see `Success. No rows returned.`

---

## M3 Step 2 — Configure Supabase Auth

### Get your anon key

1. Go to **Project Settings** → **API**.
2. Copy the **anon / public** key (starts with `eyJ...`).
   - This is different from the `service_role` key — it's safe to embed in the frontend.

### Configure redirect URLs

1. Go to **Authentication** → **URL Configuration**.
2. Under **Redirect URLs**, click **Add URL** and add:
   - `https://your-app.netlify.app` (your production URL)
   - `http://localhost` (for local testing)
   - `http://127.0.0.1` (also for local testing)
3. Click **Save**.

### Restrict sign-in to your email only

1. Sign in to the app once with your email (magic link) to create your Auth account.
2. After signing in successfully, go to **Authentication** → **Providers** → **Email**.
3. Turn off **"Enable email signup"** — this prevents new users from creating accounts.
   From now on, only your pre-existing Auth account can receive magic links.

---

## M3 Step 3 — Add credentials to the app

1. Open `Bank/app/index.html` in a text editor.
2. Find these two lines near the bottom of the file (in the `<script>` block):
   ```javascript
   const SUPABASE_URL      = 'YOUR_SUPABASE_URL';
   const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';
   ```
3. Replace `YOUR_SUPABASE_URL` with your Project URL.
4. Replace `YOUR_SUPABASE_ANON_KEY` with your **anon / public** key.
5. Save the file.

---

## M3 Step 4 — Test locally

Open `Bank/app/index.html` directly in Chrome. You'll see the login screen.

Enter your email address, click **Send magic link**, then check your inbox and click the link. You'll be signed in and see your dashboard.

> **Note on local testing:** Magic link redirects require a proper URL. If the link doesn't work when opening the file directly (via `file://`), serve the app folder locally:
> ```bash
> cd Bank
> python3 -m http.server 8080
> ```
> Then open `http://localhost:8080/app/` in Chrome. Make sure `http://localhost` is in your Supabase redirect URLs (see M3 Step 2).

---

## M3 Step 5 — Deploy to Netlify (optional)

The `Bank/app/` folder is a static site — drop it into Netlify:

1. Go to **https://app.netlify.com** → **Add new site** → **Deploy manually**.
2. Drag and drop the `Bank/app/` folder onto the deploy target.
3. Note the assigned URL (e.g. `https://bov-finance-abc123.netlify.app`).
4. Add this URL to your Supabase redirect URLs (M3 Step 2).
5. The app is now live and installable on your phone via "Add to Home Screen".

---

---

# M4 Setup Guide — Category Review UI

M4 adds write access to the app: categorise transactions from an Inbox tab, with a one-tap category picker and bulk re-categorise by keyword.

---

## M4 Step 1 — Apply write RLS policies

1. In Supabase, go to **SQL Editor** → **New query**.
2. Copy the contents of `Bank/supabase/rls_m4.sql` and paste into the editor.
3. Click **Run**. You should see `Success. No rows returned.`

This adds two policies:
- `authenticated_update_transactions` — lets the signed-in user update category/reviewed fields
- `authenticated_insert_category_overrides` — lets the signed-in user log manual overrides

---

## M4 Step 2 — Deploy updated app

Drag and drop the `Bank/app/` folder onto your Netlify site's deploy dropzone (same as M3 Step 5). The update takes ~10 seconds.

On your phone, close and re-open the PWA from your home screen. You should see an **Inbox** tab in the nav bar (with a red badge if there are uncategorised transactions).

---

## M4 How to use

**Inbox tab:** Shows all uncategorised transactions, oldest first. Tap any row to open the category picker. Select a category to apply it — the transaction immediately disappears from the Inbox and moves to the main Transactions list.

**Category picker:** A bottom sheet slides up showing all categories. Type to search/filter. The selected category is applied immediately to the tapped transaction.

**Bulk re-categorise:** At the bottom of the picker is a "Apply to all containing:" section, pre-filled with the transaction description. Edit the keyword to something broader (e.g. trim "LIDL MALTA 001" to just "LIDL") then tap "Apply to all" — every transaction whose description contains that keyword gets re-categorised in one shot.

**From the Transactions tab:** Each transaction's category badge is now tappable (shows a ✏ icon). Tap it to change the category of any already-categorised transaction.

---

---

# M5 Setup Guide — Budget Management

M5 adds the ability to create and edit monthly budgets directly from the app. Budget progress bars were already visible in M3/M4; M5 makes them interactive.

---

## M5 Step 1 — Apply RLS policy for budgets

1. In Supabase, go to **SQL Editor** → **New query**.
2. Copy the contents of `Bank/supabase/rls_m5.sql` and paste into the editor.
3. Click **Run**. You should see `Success. No rows returned.`

This adds one policy:
- `authenticated_manage_budgets` — lets the signed-in user create, edit, and delete budgets

---

## M5 Step 2 — Deploy updated app

Drag and drop the `Bank/app/` folder onto your Netlify site's deploy dropzone. The update takes ~10 seconds.

---

## M5 How to use

**Edit a budget:** On the Budgets tab, tap any budget row (the whole row is a tap target). A bottom sheet slides up showing the current amount. Edit the amount and tap **Save**. The change applies to all months (budgets are global monthly defaults).

**Add a new budget:** Tap the **＋ Add budget** button at the bottom of the Budgets list. Select a category from the dropdown (only categories without budgets are shown) and enter the monthly amount.

**Delete a budget:** Open the edit sheet for a budget, then tap **Delete** (and confirm). This removes the budget from all months.

**Amount entry tip:** You can type the amount and press Enter to save without tapping the button.

---

---

# M6 Setup Guide — Category Rule Editor

M6 adds the ability to view, create, edit, delete, and reorder category rules from within the app.

---

## M6 Step 1 — Apply RLS policy for category rules

1. In Supabase, go to **SQL Editor** → **New query**.
2. Copy the contents of `Bank/supabase/rls_m6.sql` and paste into the editor.
3. Click **Run**. You should see `Success. No rows returned.`

This adds one policy:
- `authenticated_manage_category_rules` — lets the signed-in user create, edit, delete, and reorder rules

---

## M6 Step 2 — Deploy updated app

Drag and drop the `Bank/app/` folder onto your Netlify site's deploy dropzone.

---

## M6 How to use

**Opening the rules manager:** Open the category picker on any transaction, then tap **⚙ Manage category rules** at the bottom of the picker sheet.

**Viewing rules:** Rules are listed sorted by priority (the order they are evaluated during import). Each row shows the keyword → category and its rank number.

**Searching:** Type in the search bar to filter by keyword or category name.

**Reordering:** Use the ▲ ▼ buttons to move a rule up or down. Tap **Save order** when done — changes are not persisted until you tap that button.

**Adding a rule:** Tap **＋ Add rule** at the bottom of the list. Enter a keyword (case-insensitive contains match — "LIDL" catches "LIDL MALTA 001") and pick a category. New rules are appended at the lowest priority by default.

**Editing / deleting:** Tap any rule row to open the editor. Change the keyword or category and tap **Save**, or tap **Delete** to remove it. Deleting a rule does not re-categorise existing transactions.

---

## M6 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Write blocked" toast | Run `rls_m6.sql` in Supabase SQL Editor (M6 Step 1) |
| "Keyword already exists" when adding | Each keyword is globally unique — tap the existing rule with that keyword and edit it instead |
| Rules not loading | Check browser console; verify you are signed in |
| ▲ ▼ buttons not saving | Tap the **Save order** button — it appears when the order has unsaved changes |

---

## M5 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Write blocked" toast when saving | Run `rls_m5.sql` in Supabase SQL Editor (M5 Step 1) |
| Category not appearing in "Add budget" dropdown | That category already has a budget — tap its row in the list to edit it instead |
| Changes don't persist after reload | Ensure you're still signed in (session may have expired); check browser console |

---

## M4 Troubleshooting

| Problem | Fix |
|---------|-----|
| "new row violates row-level security" error | Run `rls_m4.sql` in Supabase SQL Editor (M4 Step 1) |
| Category change not saving | Check browser console; verify you're signed in (session may have expired) |
| Bulk update applied too broadly | The keyword match is case-insensitive `CONTAINS` — edit the keyword to be more specific before applying |
| Inbox badge not updating | Hard reload (Cmd+Shift+R) to clear the service worker cache after deploying |

---

## M3 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Invalid API key" error in browser console | Check that `SUPABASE_ANON_KEY` is set to the **anon** key, not the `service_role` key |
| Magic link redirects to wrong URL | Add the correct URL to Supabase → Authentication → URL Configuration → Redirect URLs |
| Data not loading after sign-in | Check browser console for errors; verify RLS policies are active (M3 Step 1) |
| Charts not rendering | Check browser console; ensure Chart.js CDN loaded (requires internet connection) |
| "No accounts found" | Verify `accounts` table has rows with `owner = 'andrew'` in Supabase Table Editor |

---

## M7 — Business & FL3XX Flags

### M7 Setup

**No new SQL file required.** The `authenticated_update_transactions` policy created in M4 already allows updating all transaction columns (including `business_flag` and `fl3xx_flag`). Just redeploy `Bank/app/` to Netlify and force-refresh.

---

## M7 How to use

**Flagging a transaction:** Every transaction row (in the Transactions tab and the Inbox) shows two small buttons on the right: **B** (Business) and **F** (FL3XX).

- **Tap B or F** on an unflagged transaction → an action sheet slides up asking whether to flag just that transaction or all transactions with the same description.
- **Tap B or F** on an already-flagged transaction → immediately unflagged (no sheet).

**Bulk-flagging by merchant:** When the flag action sheet is open, tap the blue **"All transactions containing …"** button to flag all matching transactions in one go.

**Flag filter:** In the Transactions tab, use the **All types / Business only / FL3XX only** dropdown next to the account filter to view only flagged transactions.

**Receipts counter:** When any transaction is flagged Business or FL3XX but has no receipt attached, a red **🧾 N** counter appears in the app header. This is the outstanding-receipts counter — receipt attachment comes in M8.

**Both flags independently:** The B and F flags are fully independent. Setting one does not affect the other.

---

## M7 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Save failed" / "Write blocked" toast when toggling | Ensure `rls_m4.sql` has been run in Supabase SQL Editor (M7 uses the same policy) |
| Flag buttons not visible on transaction rows | Hard-reload after redeploying to clear service-worker cache |
| Receipts counter stays at 0 after flagging | Check browser console; verify the flag was actually saved in Supabase Table Editor |
| Bulk flag applied to wrong transactions | The keyword is the full transaction description — edit the bulk target in the action sheet by cancelling and using the Transactions search to identify the correct merchant, then flag manually |


---

## M8 — Receipt Upload (Google Drive)

### M8 Setup — One-time Google Cloud configuration

Receipt upload requires a Google Cloud project with the Drive API enabled and an OAuth 2.0 Client ID. This takes about 5 minutes.

**Step 1 — Create a Google Cloud project**

1. Go to **https://console.cloud.google.com** and sign in with the Google account that owns your Drive.
2. Click the project dropdown at the top → **New Project**.
3. Name it `bov-finance` (or anything) and click **Create**.

**Step 2 — Enable the Drive API**

1. In your new project, go to **APIs & Services → Library**.
2. Search for **Google Drive API** and click **Enable**.

**Step 3 — Create OAuth credentials**

1. Go to **APIs & Services → Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. If prompted, configure the consent screen first:
   - User type: **External** → Create
   - App name: `BOV Finance`, support email: your email
   - Add scope: `https://www.googleapis.com/auth/drive.file`
   - Add yourself as a **Test user** (your Google account email)
   - Save and continue
4. Back in Create OAuth client ID:
   - Application type: **Web application**
   - Name: `BOV Finance PWA`
   - Under **Authorised JavaScript origins**, add:
     - `https://your-netlify-site.netlify.app` (your Netlify URL)
     - `http://localhost` (for local testing)
   - Click **Create**
5. Copy the **Client ID** (looks like `123456789-abc.apps.googleusercontent.com`)

**Step 4 — Add the Client ID to the app**

Open `Bank/app/index.html` and find this line near the top of the `<script>` block:

```javascript
const GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';
```

Replace the placeholder with your actual Client ID, redeploy to Netlify, and force-refresh.

---

## M8 How to use

**Attaching a receipt:** On any transaction that has the B or F flag set, a dashed amber **📎 Attach receipt** button appears below the category label.

1. Tap **📎 Attach receipt** — on desktop this opens a file picker; on mobile it offers the camera or file browser.
2. Select or photograph the receipt.
3. A Google sign-in popup appears (first time only per session). Sign in with the Google account you set up above.
4. The file uploads automatically to the correct Drive folder:
   - **Business only** → `BOV Receipts/Business/YYYY-Qx_Mmm-Mmm/`
   - **FL3XX only** → `BOV Receipts/FL3XX/`
   - **Both Business + FL3XX** → Business quarterly folder (one file, no duplication)
5. The button changes to a green **📎 Receipt ↗** link. Tap it to open the file in Drive.

**Folder structure created automatically in your Drive:**
```
BOV Receipts/
  Business/
    2025-Q4_Nov-Jan/
    2026-Q1_Feb-Apr/
    ...
  FL3XX/
```

**Outstanding receipts counter:** The 🧾 N badge in the header clears automatically once all flagged transactions have receipts attached.

---

## M8 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Google Client ID not configured" toast | Replace the placeholder in `index.html` and redeploy |
| "Google Identity Services not loaded" toast | Check internet connection; the GSI script loads from `accounts.google.com` |
| Google popup blocked by browser | Allow popups for your Netlify domain in browser settings |
| "Access blocked: app not verified" | Add yourself as a test user in Google Cloud Console → OAuth consent screen → Test users |
| Upload fails with 403 | Your token may have expired (1hr limit) — reload the page and try again |
| Receipt uploaded to wrong folder | Check that both the `business_flag` and `fl3xx_flag` on the transaction are set correctly before attaching |
| Drive folder not appearing | Check Google Drive → My Drive; folders are created at root level under `BOV Receipts/` |


---

## M8 Phase 2 — Report Generation

### Business Report (browser, no setup needed)

1. Open the app → **Reports** tab
2. Select a quarter from the **Business Expenses Report** dropdown
3. Click **↓ Generate PDF** — the file downloads immediately
4. Send the PDF to your accountant; receipt Drive links are included in the table

### FL3XX Combined PDF (Python script — one-time setup)

**Install additional dependencies:**
```bash
pip install fpdf2 pypdf Pillow google-auth-oauthlib google-api-python-client --break-system-packages
```

**Create a Desktop app OAuth client for Python Drive access:**
1. Go to **console.cloud.google.com** → **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app** → name it `BOV Finance Desktop` → **Create**
4. Click **Download JSON** on the new client → rename the file to **`drive_credentials.json`**
5. Move it to `Bank/supabase/drive_credentials.json`

**First run (opens browser for Google sign-in once):**
```bash
python3 Bank/supabase/generate_fl3xx_report.py
```
Select the month from the interactive menu. A browser tab opens for Google sign-in — this is a one-time step. `drive_token.json` is saved next to the script; future runs use it automatically.

**Subsequent runs:**
```bash
python3 Bank/supabase/generate_fl3xx_report.py 2025-11        # specify month
python3 Bank/supabase/generate_fl3xx_report.py 2025-11 --no-receipts  # table only
```

Output is saved as `FL3XX_Report_YYYY-MM.pdf` in the Bank folder.

### FL3XX Troubleshooting

| Problem | Fix |
|---------|-----|
| `drive_credentials.json not found` | Follow the Desktop OAuth client setup above |
| `403 Forbidden` downloading a receipt | Ensure the Desktop OAuth client is in the same Google Cloud project as the web app |
| Image receipt missing from output | Check Pillow is installed; run `python3 -c "from PIL import Image; print('ok')"` |
| PDF merge fails | Run `python3 -c "from pypdf import PdfWriter; print('ok')"` to verify pypdf installed |
