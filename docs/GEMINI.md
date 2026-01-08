# GEMINI.md

## Project Overview

**Project Name:** Customer Repurchase Alert System (客户预警仪表盘系统)

**Type:** Python Data Analysis & CRM System

**Purpose:**
This system is an intelligent Customer Relationship Management (CRM) tool designed for e-commerce businesses. It analyzes historical order data to automatically identify high-value customers who are at risk of churning or are due for a repurchase. It provides actionable insights through priority scores, value segmentation, and differentiated engagement strategies.

**Key Features:**
*   **Intelligent Prioritization:** Calculates a "Priority Score" for each customer based on purchase history, uplift potential, profit margin, and return risk.
*   **Customer Segmentation:** Classifies customers into High, Medium, and Low value tiers with tailored Standard Operating Procedures (SOPs).
*   **Churn Detection:** Identifies customers who have exceeded their personal or category-specific repurchase cycles.
*   **SKU Alerts:** Monitors product performance to flag low-margin items and high-return rate products.
*   **Interactive Dashboard:** Generates a rich HTML dashboard (`客户预警仪表盘.html`) for real-time filtering and contact tracking.
*   **Excel Reporting:** Outputs detailed Excel reports (`客户预警输出.xlsx`) for deep analysis.

## Architecture

The system follows a linear data processing pipeline:

1.  **Data Ingestion:**
    *   Fetches recent orders from Feishu/Lark Bitable (`tech/fetch_bitable_month.py`).
    *   Merges historical and new billing data into a master ledger (`tech/combine_ledgers.py`).

2.  **Core Analysis (`tech/generate_customer_alerts.py`):**
    *   Aggregates data by customer.
    *   Calculates metrics: Recency, Frequency, Monetary (RFM), Return Rate, CLV (Customer Lifetime Value).
    *   Applies business rules from `tech/config.json`.
    *   Computes Priority Scores and assigns Risk/Opportunity Tags.

3.  **Presentation:**
    *   **Excel:** Uses `openpyxl` to create a multi-sheet Excel report.
    *   **HTML:** Uses `tech/html_generator.py` and Jinja2 templates (`tech/templates/`) to render the interactive dashboard.

## Key Files & Directories

*   `tech/generate_customer_alerts.py`: **Main Engine**. Contains the core logic for data processing, scoring, and alert generation.
*   `tech/config.json`: **Configuration**. Centralized file for business logic parameters (margins, thresholds, weights).
*   `tech/html_generator.py`: **UI Rendering**. Handles the generation of the HTML dashboard using Jinja2.
*   `tech/templates/`: **Templates**. Contains HTML/CSS/JS templates for the dashboard components.
*   `tech/combine_ledgers.py`: **Data Prep**. Merges multiple Excel sources into a single analysis-ready file.
*   `tech/fetch_bitable_month.py`: **Integration**. API client for fetching data from Feishu.
*   `run_customer_dashboard.command`: **Entry Point**. Shell script for one-click execution of the full pipeline.

## Building and Running

### Prerequisites
*   Python 3.9+
*   Dependencies: `pip install -r requirements.txt` (mainly `pandas`, `openpyxl`, `jinja2`, `requests`)

### Standard Execution
The recommended way to run the system is via the wrapper script:

```bash
./run_customer_dashboard.command
```

### Manual Pipeline Execution
If you need to run specific steps individually:

1.  **Fetch Data (Optional):**
    ```bash
    python3 tech/fetch_bitable_month.py
    ```

2.  **Merge Ledgers:**
    ```bash
    python3 tech/combine_ledgers.py
    ```

3.  **Generate Alerts:**
    ```bash
    python3 tech/generate_customer_alerts.py \
        --source tech/账单汇总_全部.xlsx \
        --output 客户预警输出.xlsx \
        --config tech/config.json
    ```

## Configuration (`tech/config.json`)

This file controls the behavior of the analysis engine. Key sections:

*   `defaults`: Global defaults for margins, cycle days, and costs.
*   `categories`: Overrides for specific product categories (e.g., "羽绒服" has higher margin and longer cycle).
*   `clv_weights`: Weights for calculating Customer Lifetime Value (Historical vs. Activity vs. Potential).
*   `priority_score_boost`: Bonus points for specific customer attributes (e.g., Star Customers).
*   `sku_alerts`: Thresholds for triggering product warnings (Low Margin, High Return).

## Development Conventions

*   **Code Style:** Follow PEP 8. Use snake_case for functions/variables and UPPER_CASE for constants.
*   **Path Handling:** Use `pathlib.Path` for file system operations.
*   **HTML Generation:** Do not hardcode HTML in Python strings. Use `tech/html_generator.py` and modify templates in `tech/templates/`.
*   **Data Privacy:** Customer PII (Personally Identifiable Information) is processed locally. Do not commit raw data files (e.g., `.xlsx`) to version control.
*   **Testing:** Use the `--today` flag in `generate_customer_alerts.py` to simulate runs for specific dates and verify logic consistency.
