# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Customer Repurchase Alert System** (客户预警仪表盘系统) designed for e-commerce customer relationship management. It analyzes historical order data from Feishu (Lark) Bitable to:

- Automatically identify customers who need follow-up
- Calculate priority scores based on uplift probability, profit margin, and return risk
- Generate differentiated engagement strategies by customer value tier
- Provide real-time SKU alerts (low-margin products, high-return items)
- Output interactive HTML dashboard and Excel reports

The system processes ~16,000+ order records from 9,549+ customers to generate actionable contact lists (typically 950-1,644 customers after filtering).

---

## Common Commands

### Running the System

**One-command execution (recommended):**
```bash
./run_customer_dashboard.command
```
This script automatically:
1. Fetches current month orders from Feishu Bitable (optional)
2. Merges historical ledgers (2024年总表.xlsx + 2025年账单汇总.xlsx)
3. Generates customer alerts (Excel + HTML dashboard)

**Manual execution:**
```bash
# 1. Fetch current month orders from Feishu (optional)
python3 tech/fetch_bitable_month.py

# 2. Merge ledgers
python3 tech/combine_ledgers.py

# 3. Generate customer alerts
python3 tech/generate_customer_alerts.py \
  --source tech/账单汇总_全部.xlsx \
  --sheet 汇总(全部) \
  --output tech/客户预警输出.xlsx \
  --html-output 客户预警仪表盘.html \
  --config tech/config.json
```

### Testing and Development

**Run with test parameters:**
```bash
python3 tech/generate_customer_alerts.py \
  --source tech/账单汇总_全部.xlsx \
  --sheet 汇总(全部) \
  --output test_output.xlsx \
  --html-output test_dashboard.html \
  --today 2025-11-12 \
  --churn-multiplier 1.5 \
  --cooldown-days 7
```

**Order lookup (by order number or return tracking number):**
```bash
python3 tech/lookup_order.py <order_number>
```

**Feishu authentication (save tenant token):**
```bash
python3 tech/save_tenant_token.py
```

### Environment Configuration

Copy `.env.local.example` to `.env.local` and configure:
```bash
cp .env.local.example .env.local
# Edit .env.local with your Feishu credentials
```

---

## Architecture & Data Flow

### Core Pipeline

```
Raw Data (Feishu Bitable)
    ↓
[fetch_bitable_month.py] → 新增账单/拉取_YYYYMM.xlsx
    ↓
[combine_ledgers.py] → tech/账单汇总_全部.xlsx (merged ledger)
    ↓
[generate_customer_alerts.py] →
    ├─ tech/客户预警输出.xlsx (3 sheets: 客户概览, 触达优先级, 指标说明)
    └─ 客户预警仪表盘.html (interactive dashboard)
```

### Key Scripts

**tech/generate_customer_alerts.py** (219KB, 2878 lines) - Core analysis engine
- Customer aggregation and priority score calculation
- CLV (Customer Lifetime Value) scoring (0-100 scale)
- Tag-based SOP recommendation generation
- Excel + HTML output with styling

**tech/combine_ledgers.py** - Ledger merging
- Merges 2024年总表.xlsx and 2025年账单汇总.xlsx
- Handles path auto-detection (root directory vs tech/ folder)
- Outputs: 账单汇总_全部.xlsx (all records) and 账单汇总_截至10月前.xlsx (legacy compatibility)

**tech/fetch_bitable_month.py** - Feishu data fetching
- Pulls current month orders from Feishu Bitable
- Supports filtering by month and platform
- Requires FEISHU_APP_ID, FEISHU_APP_SECRET, or FEISHU_TENANT_ACCESS_TOKEN

**tech/contact_server.py** - Local contact logging server
- Optional HTTP server (port 8081) for HTML dashboard to mark contacts
- Writes to Feishu Bitable when user checks "已跟进" in HTML

**tech/fill_contact_fields.py** - Auto-fill missing data
- Fills empty "姓名" and "联系平台" fields in Feishu "促单用户" table
- Uses aggregated data from 账单汇总_全部.xlsx

**tech/common.py** - Shared utilities
- Excel sheet resolution
- Phone number deduplication
- Date parsing helpers

### Data Sources

**Input:**
- `tech/账单汇总_全部.xlsx` - Merged order ledger (16,579+ records)
- `tech/contact_log.xlsx` - Contact history (columns: 手机号, 最后联系日期)
- `tech/config.json` - Category-specific parameters (margin, cycle, return rate, touch cost)
- Feishu Bitable (optional) - "促单用户" table for contact tracking

**Output:**
- `tech/客户预警输出.xlsx` - Excel report with 3 sheets
- `客户预警仪表盘.html` - 8.2MB interactive dashboard (sortable table, order details, SKU alerts)

---

## Priority Score Algorithm

**Formula:**
```python
priority_score = (uplift × estimated_margin × (1 - return_rate)) - touch_cost
```

**Components:**

1. **Uplift** (conversion probability)
   - Based on `days_since_last_order / personal_threshold`
   - Range: [0.2, 2.0] for regular customers, [0.2, 3.5] for premium (3+ orders, <30% return rate)
   - Calculation: `uplift_base + max(0, ratio - 1.0)` clamped to floor/ceiling

2. **Estimated Margin**
   - Priority: Use actual profit if available (`累计毛利 ÷ 有效订单数`)
   - Fallback: `AOV × category_gross_margin`
   - Capped at `max_estimated_margin` (default 8000 yuan, configurable per category)

3. **Return Rate** (mixed approach)
   - 3+ orders: `0.7 × actual_return_rate + 0.3 × expected_return_rate`
   - 1-2 orders: `max(actual_return_rate, expected_return_rate)`
   - Capped at 95%

4. **Touch Cost**
   - Platform-specific costs (WeChat: 6.0, Xiaohongshu: 8.0, Douyin: 6.5, Shipinhao: 7.0)
   - Configurable in `config.json` under `platform_touch_cost`

5. **Order Dampening** (confidence decay)
   - 1 order: 0.3× weight
   - 2 orders: 0.7× weight
   - 3+ orders: 1.0× weight

**Bucketing:**
- ≥80: High priority
- 50-79: Medium priority
- 0-49: Low priority
- <0: Negative score

---

## Customer Value Segmentation

### CLV Scoring (0-100 scale, introduced in v3.0)

**Components:**
- Historical Value (40%): Cumulative spending + order count
- Current Activity (30%): Recent engagement + spending ratio
- Growth Potential (30%): Spending trend + repurchase stability

**Tags:**
- **明星客户 (Star)**: CLV score indicates top-tier value (2 customers)
- **潜力客户 (Potential)**: High growth trajectory (599 customers)
- **成长型 (Growing)**: Positive spending trend (213 customers)

### Value Tiers (for SOP strategy)

| Tier | Criteria | Count | Strategy |
|------|----------|-------|----------|
| **高价值 (High)** | Cumulative >5000 OR (3+ orders AND AOV>500) | 3 | 1v1 exclusive chat |
| **中价值 (Medium)** | Cumulative 2000-5000 OR 2+ orders | 894 | Small incentives |
| **低价值 (Low)** | Others | 53 | Flash sales / clearance |

---

## Configuration System (config.json)

### Structure

```json
{
  "defaults": {
    "gross_margin": 0.32,           // Default margin 32%
    "category_cycle_days": 60,      // Default repurchase cycle
    "expected_return_rate": 0.08,   // Expected return rate
    "touch_cost": 6.0,              // Default touch cost
    "uplift_base": 0.6,             // Uplift baseline
    "uplift_floor": 0.2,            // Min uplift
    "uplift_ceiling": 2.0,          // Max uplift (regular)
    "uplift_ceiling_premium": 3.5,  // Max uplift (premium customers)
    "orders_dampening": {...}       // Order-based confidence weighting
  },
  "categories": {
    "羽绒服": {
      "aliases": ["羽绒服", "羽绒衣", "羽绒外套"],
      "gross_margin": 0.42,
      "category_cycle_days": 180,
      "expected_return_rate": 0.05,
      "touch_cost": 12.0
    }
  },
  "platform_touch_cost": {
    "小红书": 8.0,
    "抖音": 6.5
  }
}
```

### Category Matching

Categories are matched by `aliases` against customer's preferred items (偏好单品). If no match, falls back to `defaults`.

### Tuning Parameters

**Churn multiplier** (`--churn-multiplier`, default 1.5):
- Multiplier applied to personal/category repurchase cycle
- Higher value = more lenient (longer before flagging as churned)

**Cooldown days** (`--cooldown-days`, default 7):
- Days after last contact before customer reappears in action list

**Single-order filter** (`config.json → single_order`):
- `enabled: true` - Filter 1-order customers
- `mode: "previous_month"` - Only keep previous month's new customers
- Result: 7,677 → 53 single-order customers (0.7% retention)

---

## Filtering Logic

### Contact List Criteria (触达优先级 sheet)

Customers must meet **ALL** of the following:

1. **At least one risk/opportunity tag:**
   - 高价值流失预警 / 长期未复购 / 短期未复购
   - 消费骤降 / 退货激增
   - 节点回访 / 高价值活跃
   - OR: 明星客户 / 潜力客户
   - OR: Priority score ≥ 50
   - OR: Order count ≥ 5
   - OR: Growth type = 成长型/高潜新客

2. **Not in cooldown period:**
   - If `contact_log.xlsx` exists and phone number appears within last N days (`--cooldown-days`)

3. **Return rate ≠ 100%:**
   - Excludes customers who always return (unless `--allow-high-return` flag)

4. **Not recently ordered (optional):**
   - `--exclude-recent-days N` filters customers who ordered within last N days (default: 30)

5. **Single-order strategy:**
   - If enabled in config, only keeps previous month's 1-order customers

### Churn Threshold Calculation

```python
personal_threshold = avg_repurchase_cycle × churn_multiplier
category_threshold = category_cycle × churn_multiplier
default_threshold = churn_days (default 90)

final_threshold = max(personal_threshold, category_threshold, default_threshold)
```

**Short-term vs Long-term:**
- Short-term threshold: `final_threshold / 2` (min 1 day)
- Long-term threshold: `final_threshold`

---

## SOP Recommendations (推荐动作)

### Tag-Driven Actions

**High priority (禁止促单):**
- `退货激增` → 【售后排查】核实退款原因
- `消费骤降` (high value) → 【关系修复】了解流失原因

**Engagement actions:**
- `高价值流失预警` → 【专属福利】基于{偏好单品}定制权益
- `长期未复购` (medium value) → 【小福利唤醒】限时折扣
- `短期未复购` (medium value) → 【小福利唤醒】热卖搭配
- `节点回访` → 【周年关怀】纪念日专属优惠

**Default (no tag):**
- 【常规复购关怀】结合{偏好单品}与{主要平台}复购场景

### Platform-Specific Strategies

**微信渠道:**
- High value → 1v1专属私聊
- Medium value → 小福利唤醒
- Low value → 限时秒杀

**闲鱼渠道:**
- Unified strategy: 生日福利、直送、限时秒杀、独家款式

---

## HTML Dashboard Features

### Interactive Elements

1. **Real-time filtering:**
   - Keyword search (name, phone, platform, tags)
   - Priority score range slider
   - Value tier dropdown
   - Tag checkboxes
   - Platform filter

2. **Sortable columns:**
   - Click header to toggle ascending/descending
   - All columns have `data-sort-value` attributes

3. **Contact tracking:**
   - Checkbox to mark customer as contacted
   - Stored in localStorage
   - Export to CSV format: `手机号,最后联系日期`

4. **Order details drill-down:**
   - Click any row to expand customer's full order history
   - Shows: 姓名, 下单平台, 货品名, 付款金额, 退款类型, 退款原因

5. **Global order search:**
   - Search by order number or return tracking number
   - Searches across all 16,579+ records

### Three Alert Cards

1. **加推SKU** (High-performing products):
   - Last 45 days: Order count >4 AND return rate <20%
   - Sorted by order count descending

2. **高退货预警** (High-return products):
   - Detail count >3 AND return rate >30%
   - Quality issue indicators

3. **低毛利预警** (Low-margin products):
   - 115 products with margin <35%
   - Excludes dropship and sample orders
   - Sorted by margin ascending

---

## Feishu Integration

### Environment Variables

```bash
# Contact tracking table (优先使用多维表)
FEISHU_CONTACT_APP_TOKEN=GRZsbC1pOaTiazsV9ryc3wc8nIe
FEISHU_CONTACT_TABLE_ID=tblK0lGgBftyonCM
FEISHU_CONTACT_VIEW_ID=vewfuMyZFU  # Optional: specific view

# Authentication (provide at least one)
FEISHU_USER_ACCESS_TOKEN=...      # User OAuth token
FEISHU_TENANT_ACCESS_TOKEN=...    # Tenant access token

# Order table (for fetch_bitable_month.py)
FEISHU_ORDER_APP_TOKEN=...
FEISHU_ORDER_TABLE_ID=...
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
```

### Data Flow

**Contact tracking:**
1. Script checks for Feishu credentials in `.env.local`
2. If valid, fetches "已联系客户" from Bitable
3. Falls back to local `tech/contact_log.xlsx` if unavailable
4. Applies cooldown filter (default 7 days)

**Auto-filling:**
- `fill_contact_fields.py` uses aggregated data from `账单汇总_全部.xlsx` to fill missing "姓名" and "联系平台" fields in Feishu "促单用户" table

**Write-back (optional):**
- Set `CONTACT_SERVER=1` to start local server
- HTML dashboard POSTs to `http://127.0.0.1:8081/mark` when user checks contact boxes
- Server writes to Feishu Bitable in real-time

---

## Excel Output Structure

### Sheet 1: 客户概览 (Customer Overview)
- All 9,549 customers with valid orders
- Includes cancelled orders in metrics (取消单数)
- No filtering applied
- Used for full data analysis and reconciliation

### Sheet 2: 触达优先级 (Contact Priority)
- Filtered action list (typically 950-1,644 customers)
- Sorted by: priority_score DESC → orders DESC → return_rate ASC → AOV DESC
- New fields in v3.0:
  - `价值层级` (High/Medium/Low)
  - `推荐动作` (SOP recommendation)
  - `CLV分数` (0-100 lifecycle value)
  - `成长类型` (Growth type)
  - `潜力标签` (Potential tag)

### Sheet 3: 指标说明 (Metrics Explanation)
- Generation timestamp
- Parameter configuration
- Priority score formula
- Filtering rules
- Field definitions

---

## Code Style & Conventions

- Follow PEP 8 (4-space indentation, snake_case)
- Constants in UPPER_CASE (e.g., `COLUMNS`, `CUTOFF`)
- Use `pathlib.Path` for file paths
- Type annotations for functions
- Chinese user-facing messages, English code comments

---

## Critical Business Logic

### Profit Calculation Bug Fix (v3.0)

**Issue:** Some customers showed 7357亿 (735.7 billion yuan) profit due to return tracking numbers being misread as profit values.

**Fix:** Forced calculation method:
```python
profit = gross_revenue - payment_amount  # 收款额 - 打款金额
```

Added field aliases for robustness:
```python
"cost": ("打款金额", "打款", "打款价", "成本价", "成本")
```

### Key Data Fields

**Order validation:**
- Cancelled if: `状态` contains "取消" OR `退款类型` contains "取消" OR `付款金额 ≤ 0`
- Return if: `退款金额 > 0` OR `退货状态` contains "退" OR `退款类型` contains "退"

**Customer merging:**
- Priority: `手机号` → `姓名|地址` → `姓名` → `地址`
- Phone deduplication: Uses `common_deduplicate_phone()` to handle formatting variations

**Date parsing:**
- Handles Excel serial dates and string formats
- Uses `common_parse_excel_date()` for robustness

---

## Version History Highlights

### v3.0 (2025-11-12)
- ✨ CLV lifecycle value scoring (0-100)
- ✨ Customer classification tags (明星/潜力/成长型)
- ✨ Priority score boosts (+30 for stars, +20 for 10+ orders)
- ✨ Colloquial SOP recommendations (removed technical jargon)
- ✨ Expanded filtering criteria (now includes CLV, order count, growth type)
- 🐛 Fixed profit calculation anomaly (7357亿 → 22.5~374元)
- 📊 Increased contact list: 950 → 1,644 customers (+73%)

### v2.0 (2025-11-12)
- ✨ Customer value tiers (High/Medium/Low)
- ✨ Differentiated engagement strategies (WeChat/Xianyu)
- ✨ Low-margin alert (115 products <35% margin)
- 🔧 Filter customers beyond 2× threshold
- 🔧 Single-order filter: 7,677 → 53 (0.7%)

### v1.0 (2025-10)
- Initial release
- Priority score sorting
- Excel + HTML output
- SKU alerts (high-performing + high-return)

---

## Security & Privacy

- **Personal data:** The system contains customer phone numbers, names, and addresses
- **Local use only:** Do NOT deploy HTML dashboard (8.2MB) to public servers
- **Git ignore:** Raw ledger files (`*.xlsx`) are excluded from version control
- **Test data:** Use anonymized data in `tests/fixtures/` if needed

---

## Performance Notes

- Excel generation: ~10-15 seconds
- HTML generation: ~5-8 seconds
- Browser load time: 3-5 seconds (first load)
- Dataset: 16,579 records → 9,549 customers → 950-1,644 action items

---

## Important Paths

```
表格/
├── tech/
│   ├── generate_customer_alerts.py    # Core engine (219KB)
│   ├── combine_ledgers.py             # Ledger merger
│   ├── fetch_bitable_month.py         # Feishu data fetch
│   ├── contact_server.py              # Optional write-back server
│   ├── fill_contact_fields.py         # Auto-fill Feishu blanks
│   ├── lookup_order.py                # Order search utility
│   ├── common.py                      # Shared utilities
│   ├── config.json                    # Configuration
│   ├── 账单汇总_全部.xlsx              # Merged ledger (INPUT)
│   └── 客户预警输出.xlsx               # Excel report (OUTPUT)
├── run_customer_dashboard.command      # One-click runner (macOS)
├── run_customer_dashboard.bat          # One-click runner (Windows)
├── 客户预警仪表盘.html                  # HTML dashboard (OUTPUT)
├── .env.local                          # Feishu credentials (git-ignored)
└── docs/
    ├── AGENTS.md / AGENTS_CN.md       # Development guidelines
    ├── priority_model_notes.md        # Algorithm documentation
    └── index.html                     # Published dashboard (optional)
```

---

## Testing & Debugging

**Dry run with custom date:**
```bash
python3 tech/generate_customer_alerts.py \
  --source tech/账单汇总_全部.xlsx \
  --today 2025-11-12 \
  --output test.xlsx \
  --html-output test.html
```

**Adjust filtering:**
```bash
# More lenient (include more customers)
--churn-multiplier 2.0    # 2× cycle instead of 1.5×
--allow-high-return       # Include 100% return rate customers
--exclude-recent-days 0   # Don't exclude recent orders

# More strict (fewer customers)
--churn-multiplier 1.0    # 1× cycle
--max-action 500          # Top 500 only
```

**View specific anniversary cohort:**
```bash
--anniversary-only \
--anniversary-months 1,6,12 \
--anniversary-window 14
```

---

## Git Workflow

**Current branch:** `main`

**Commit message format:**
```
feat: 调整高价值客户流失阈值
fix: 修复毛利计算异常
docs: 更新配置文件说明
```

**Recent commits:**
- `cc2dfbf` - publish dashboard: update docs/index.html
- `4dbf0db` - Add files via upload

**Untracked files of note:**
- `2024年总表.xlsx`, `2025年账单汇总.xlsx` - Raw ledgers (intentionally excluded)
- `客户预警输出.xlsx` - Generated output
- `.env.local` - Credentials (git-ignored)

---

## Additional Resources

- **Algorithm deep-dive:** See `docs/priority_model_notes.md`
- **Development guidelines:** See `docs/AGENTS_CN.md`
- **Multi-list system design:** See `多列表系统设计.md` (proposed 4-tier segmentation)
- **Feature specs:** See `促单理由功能说明.md`, `优化方案.md`
