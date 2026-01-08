# Repository Guidelines

This file is a concise contributor guide for the root of the project. For full details, see `docs/AGENTS.md` (English) and `docs/AGENTS_CN.md` (Chinese).

## Project Structure & Module Organization
- `tech/`: core Python scripts, data utilities, templates, and Excel workbooks.
- `scripts/`: helper tools for HTML layout, SaaS transforms, and debugging.
- `docs/`: architecture notes, deployment guides, and extended contributor docs.
- Root `.command` files (`run_customer_dashboard.command`, `analyze_monthly_sales.command`, etc.) provide macOS double‑click entry points.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate`: create and activate a virtualenv.
- `pip install -r requirements.txt`: install Python dependencies.
- `python3 tech/combine_ledgers.py`: regenerate consolidated ledgers from raw monthly files.
- `python3 tech/generate_customer_alerts.py --help`: view options for Excel + HTML outputs.
- `./run_customer_dashboard.command`: refresh the default customer alert Excel and HTML dashboard.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4‑space indentation and descriptive `snake_case` identifiers; keep constants in `UPPER_SNAKE_CASE`.
- Prefer `pathlib.Path` for filesystem paths and keep functions small, data‑oriented, and side‑effect aware.
- Keep user‑visible messages concise and bilingual‑friendly where reasonable (Chinese first if only one language is practical).

## Testing Guidelines
- Use `pytest` or lightweight Python scripts under `tests/` (or a similar directory) for regression checks.
- Build tests around small, anonymized Excel fixtures and HTML snapshots instead of production data.
- When changing date filters or priority logic, assert row counts and representative sample rows against expected behavior.

## Commit & Pull Request Guidelines
- Use imperative, descriptive commit messages (e.g., `feat: tighten churn alert threshold`) and mention key workbooks or scripts when relevant.
- PRs should explain the business motivation, list sample commands to reproduce the behavior, and include screenshots for dashboard/UI changes.
- Call out any data prerequisites, new environment variables (e.g., Feishu tokens in `.env.local`), and migration notes in the PR description.

## Security & Configuration Tips
- Treat Excel workbooks as sensitive; never commit real customer data or internal tokens.
- Use `.env.local` (see `.env.local.example`) for Feishu Bitable and related secrets; do not hard‑code them into scripts or configs.

