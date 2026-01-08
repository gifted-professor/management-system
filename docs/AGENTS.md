# Repository Guidelines

_Relocated to docs/ for a tidier root._

## Project Structure & Module Organization
- Root now exposes three directories: raw ledgers in `2025 账单`, cleanup archives in `清除数据`, and the workflow workspace in `tech/`.
- `tech/combine_ledgers.py` merges `2024年总表.xlsx` and `2025年账单汇总.xlsx` into `tech/账单汇总_截至10月前.xlsx`.
- `tech/generate_customer_alerts.py` builds risk/action views from the consolidated workbook; the action sheet follows the follow-up flow (checkbox → priority → name → last order date → primary platform → phone → tags → actions → favorite item → owner → order count → return rate → days since purchase → AOV); optional HTML dashboard saves as `客户预警仪表盘.html` in the root directory.
- `tech/run_customer_dashboard.command` wraps the alert script for macOS double-click runs; keep it executable (`chmod +x`).
- Already-contacted source: Feishu Bitable is preferred. If Feishu tokens aren’t configured, the script falls back to local `tech/contact_log.xlsx` (two columns: `手机号`, `最后联系日期`).

## Build, Test, and Development Commands
- `python3 tech/combine_ledgers.py`: regenerate the pre-October consolidated ledger; run after monthly uploads.
- `python3 tech/generate_customer_alerts.py --source tech/账单汇总_截至10月前.xlsx --sheet 汇总(截至10月前) --output tech/客户预警输出.xlsx`: produce Excel alerts. Behavior:
  - If Feishu env vars are present (see below), fetch the “already-contacted” list from Bitable first.
  - Otherwise read the Excel specified by `--contact-log` (default `tech/contact_log.xlsx`).
- `python3 tech/generate_customer_alerts.py --help`: review optional flags (anniversaries, HTML export).
- `./tech/run_customer_dashboard.command`: shortcut that refreshes both Excel and HTML outputs with the default alert filters.

## Follow-up Cooldown (“Snooze”)
By default, the script reads the “already-contacted” list from Feishu Bitable. To fall back to Excel, omit Feishu tokens.
Front-line staff may continue using `tech/contact_log.xlsx` (two columns: `手机号`, `最后联系日期`).
The generator hides phones contacted within the cooldown window (default 30 days via `--cooldown-days`).
Remove/rename the Excel to resurface everyone; tweak parameters to test different windows.
The `客户预警仪表盘.html` dashboard (in root directory) supports marking rows and exporting `手机号,最后联系日期` CSV compatible with `contact_log.xlsx`.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and descriptive snake_case names; keep constants (`COLUMNS`, `CUTOFF`) in UPPER_SNAKE_CASE.
- Maintain type hints and docstrings mirroring existing modules; prefer `pathlib.Path` for filesystem access.
- Keep user-facing messages bilingual-friendly and concise; existing scripts print key metrics in Chinese.

## Testing Guidelines
- Add regression scripts under `tests/` using `pytest` or lightweight smoke checks; mock small Excel slices to avoid leaking live data.
- Validate date filters by asserting row counts and earliest/latest dates against fixtures.
- For manual QA, compare generated workbooks against expected totals inside Excel and ensure HTML dashboard renders without console errors.

## Commit & Pull Request Guidelines
- Use imperative, bilingual-friendly commit subjects (e.g., `feat: tighten churn alert thresholds`); reference affected workbook names where helpful.
- Document data prerequisites and sample commands in the PR body; attach before/after screenshots for dashboard or worksheet changes.
- Link related tickets or spreadsheet change requests; list any files intentionally excluded from version control (raw monthly ledgers).

## Security & Data Handling
- Raw ledgers contain personal data—keep them out of shared screenshots and redact exports before sharing externally.
- Never commit production Excel files; if you need fixtures, sanitize copies and store them under `tests/fixtures/`.

## Using Feishu Bitable for the “Already-Contacted” List
- Create `.env.local` at the repo root (see `.env.local.example`) with at least:
  - `FEISHU_CONTACT_APP_TOKEN`, `FEISHU_CONTACT_TABLE_ID` (required)
  - `FEISHU_CONTACT_VIEW_ID` (optional; restrict to a view)
  - One of `FEISHU_USER_ACCESS_TOKEN` or `FEISHU_TENANT_ACCESS_TOKEN`
- The run scripts auto-load `.env.local`. When set, Bitable becomes the primary source for cooldown and the script hides phones contacted within `COOLDOWN_DAYS` (default 7).
- Example (based on the “单号查询” Bitable):
  - `FEISHU_CONTACT_APP_TOKEN=GRZsbC1pOaTiazsV9ryc3wc8nIe`
  - `FEISHU_CONTACT_TABLE_ID=tblK0lGgBftyonCM`
  - `FEISHU_CONTACT_VIEW_ID=vewfuMyZFU`
  - Token placeholder only—fill with your own valid token: `FEISHU_USER_ACCESS_TOKEN=...`
