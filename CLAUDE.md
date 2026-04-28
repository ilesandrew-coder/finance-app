# Family Finance App — Standing Instructions for Claude

This file is read automatically at the start of every Cowork session.
All instructions below apply to every task in this project.

---

## Spec file maintenance (MANDATORY)

The file `BOV_Finance_App_Spec.md` in this folder is the authoritative product specification.

**Whenever Andrew approves a new feature, a change, or a bug fix that affects the product:**
- Update `BOV_Finance_App_Spec.md` as part of the same implementation — not as a separate follow-up step.
- Update the version number (increment the minor version, e.g. 1.3 → 1.4) and the `Last updated` date.
- Sections to consider updating: feature sections (§4.x), database schema (§6.2), milestones table (§7), and the PWA implementation notes.
- If a new feature is large enough to warrant its own section, add it. If it's a small fix or enhancement, update the relevant existing section.

Do not wait to be asked to update the spec. It is part of every implementation task.

---

## Project context

- **App:** Family Finance PWA — personal finance tracker for Andrew and Lyn Iles (Malta)
- **Stack:** Supabase (PostgreSQL) + Cloudflare Workers (Static Assets) + Python import script
- **Workspace:** `~/Documents/Personal/Bank/`
- **Key files:**
  - `app/index.html` — the entire PWA (single file)
  - `supabase/import_to_db.py` — monthly CSV import script
  - `BOV_Finance_App_Spec.md` — product specification (keep updated)
  - `deploy.sh` — deploys the app to Cloudflare (`bash deploy.sh`)
  - `last_import_dates.json` — last transaction date per account (written after each import)
- **Database migrations** go in `supabase/` as `.sql` files; Andrew runs them manually in the Supabase SQL Editor.
- **Deploy** after any change to `app/index.html`: `bash deploy.sh` from the Bank folder.
