#!/bin/zsh
# 双击运行：先合并 2024/2025 账单，再按个体复购周期生成客户预警 Excel 与 HTML。

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 可选：加载本地环境变量（不纳入版本控制）
if [[ -f "$SCRIPT_DIR/.env.local" ]]; then
  set -a
  source "$SCRIPT_DIR/.env.local"
  set +a
fi

pause() {
  read -k "REPLY?按回车键退出..."
  echo ""
}

fail() {
  echo "❌ $1"
  pause
  exit 1
}

RAW_2024="$SCRIPT_DIR/tech/2024年总表.xlsx"
RAW_2025="$SCRIPT_DIR/tech/2025年账单汇总.xlsx"
LEDGER_OUTPUT_ALL="$SCRIPT_DIR/tech/账单汇总_全部.xlsx"
LEDGER_OUTPUT_LEGACY="$SCRIPT_DIR/tech/账单汇总_截至10月前.xlsx"
# 可通过 .env.local 或环境变量 CONTACT_LOG_PATH 覆盖默认路径
CONTACT_LOG_PATH="${CONTACT_LOG_PATH:-$SCRIPT_DIR/tech/contact_log.xlsx}"
COOLDOWN_DAYS="${COOLDOWN_DAYS:-30}"
CHURN_MULTIPLIER="${CHURN_MULTIPLIER:-1.5}"
FETCH_MONTH_FROM_FEISHU="${FETCH_MONTH_FROM_FEISHU:-1}"
FEISHU_MONTH="${FEISHU_MONTH:-}"
FEISHU_PLATFORM="${FEISHU_PLATFORM:-}"
CONTACT_SERVER="${CONTACT_SERVER:-0}"

# 提示：是否已配置"已联系客户"从飞书多维表读取
if [[ -n "${FEISHU_CONTACT_APP_TOKEN:-}" && -n "${FEISHU_CONTACT_TABLE_ID:-}" && ( -n "${FEISHU_USER_ACCESS_TOKEN:-}" || -n "${FEISHU_TENANT_ACCESS_TOKEN:-}" ) ]]; then
  echo "✅ 已配置：已联系客户将从飞书多维表读取 (app=${FEISHU_CONTACT_APP_TOKEN}, table=${FEISHU_CONTACT_TABLE_ID}${FEISHU_CONTACT_VIEW_ID:+, view=${FEISHU_CONTACT_VIEW_ID}})"

  # 自动刷新 Feishu Token（避免 2 小时过期问题）
  if [[ -n "${FEISHU_APP_ID:-}" && -n "${FEISHU_APP_SECRET:-}" ]]; then
    echo "🔄 自动刷新 Feishu Token..."
    if python3 "$SCRIPT_DIR/tech/save_tenant_token.py"; then
      echo "✅ Token 刷新成功"
      # 重新加载环境变量以使用新 token
      if [[ -f "$SCRIPT_DIR/.env.local" ]]; then
        set -a
        source "$SCRIPT_DIR/.env.local"
        set +a
      fi
    else
      echo "⚠️ Token 刷新失败，将使用现有 token 或回退到本地文件"
    fi
  fi
else
  echo "ℹ️ 未检测到 Feishu 令牌，已联系客户将回退读取本地 ${CONTACT_LOG_PATH}"
fi

# 0/2（可选）从飞书多维表拉取当月新增订单，写入 新增账单/ 拉取_YYYYMM.xlsx
# 0/2（可选）从飞书多维表拉取当月新增订单，写入 新增账单/ 拉取_YYYYMM.xlsx
# 以及可选启动本地“联系写入”服务（用于 HTML 仪表盘打勾时写入飞书表格）
if [[ "$FETCH_MONTH_FROM_FEISHU" == "1" ]]; then
  echo "☁️ 0/2 拉取当月订单（飞书多维表）..."
  FETCH_ARGS=()
  if [[ -n "$FEISHU_MONTH" ]]; then
    FETCH_ARGS+=(--month "$FEISHU_MONTH")
  fi
  if [[ -n "$FEISHU_PLATFORM" ]]; then
    FETCH_ARGS+=(--platform "$FEISHU_PLATFORM")
  fi
  # 可选传入 AppID/Secret/租户令牌，脚本也会从环境变量读取
  if [[ -n "${FEISHU_APP_ID:-}" ]]; then
    FETCH_ARGS+=(--app-id "$FEISHU_APP_ID")
  fi
  if [[ -n "${FEISHU_APP_SECRET:-}" ]]; then
    FETCH_ARGS+=(--app-secret "$FEISHU_APP_SECRET")
  fi
  # 可选：为当月订单抓取指定 app/table（默认使用脚本内置值）
  if [[ -n "${FEISHU_ORDER_APP_TOKEN:-}" ]]; then
    FETCH_ARGS+=(--app-token "$FEISHU_ORDER_APP_TOKEN")
  fi
  if [[ -n "${FEISHU_ORDER_TABLE_ID:-}" ]]; then
    FETCH_ARGS+=(--table-id "$FEISHU_ORDER_TABLE_ID")
  fi
  if [[ -n "${FEISHU_TENANT_ACCESS_TOKEN:-}" ]]; then
    FETCH_ARGS+=(--tenant-token "$FEISHU_TENANT_ACCESS_TOKEN")
  fi
  if [[ -n "${FEISHU_USER_ACCESS_TOKEN:-}" ]]; then
    FETCH_ARGS+=(--token "$FEISHU_USER_ACCESS_TOKEN")
  fi
  if ! python3 "$SCRIPT_DIR/tech/fetch_bitable_month.py" "${FETCH_ARGS[@]}"; then
    echo "⚠️ 拉取失败：将继续使用本地文件合并。"
  fi
fi

if [[ "$CONTACT_SERVER" == "1" ]]; then
  echo "🛰️ 启动本地联系写入服务 (http://127.0.0.1:${CONTACT_SERVER_PORT:-5005}/mark) ..."
  ( python3 "$SCRIPT_DIR/tech/contact_server.py" & )
fi

echo "📦 1/2 合并 2024/2025 账单（自动适配根目录/tech/路径）..."
if ! python3 "$SCRIPT_DIR/tech/combine_ledgers.py"; then
  fail "合并账单失败，请确认原始 Excel 是否完整。"
fi



# 1.5/2（可选）补全飞书“促单用户”表的姓名/联系平台空值（基于账单汇总_全部.xlsx 的统计）
if [[ -n "${FEISHU_CONTACT_APP_TOKEN:-}" && -n "${FEISHU_CONTACT_TABLE_ID:-}" && ( -n "${FEISHU_USER_ACCESS_TOKEN:-}" || -n "${FEISHU_TENANT_ACCESS_TOKEN:-}" ) ]]; then
  echo "🧽 正在补全飞书‘促单用户’表的姓名/联系平台空值…"
  if ! python3 "$SCRIPT_DIR/tech/fill_contact_fields.py"; then
    echo "⚠️ 补全失败（可能是权限或网络问题），继续后续流程。"
  fi
fi

# 选择用于预警的来源（优先用“全部”，否则回退到旧兼容文件）
ALERT_SOURCE_FILE="${ALERT_SOURCE_FILE:-$LEDGER_OUTPUT_ALL}"
ALERT_SOURCE_SHEET="${ALERT_SOURCE_SHEET:-汇总(全部)}"
if [[ ! -f "$ALERT_SOURCE_FILE" ]]; then
  echo "ℹ️ 未找到 $ALERT_SOURCE_FILE，回退到旧兼容表 $LEDGER_OUTPUT_LEGACY"
  ALERT_SOURCE_FILE="$LEDGER_OUTPUT_LEGACY"
  ALERT_SOURCE_SHEET='汇总(截至10月前)'
fi

ARGS=(
  --source "$ALERT_SOURCE_FILE"
  --sheet "$ALERT_SOURCE_SHEET"
  --output "$SCRIPT_DIR/tech/客户预警输出.xlsx"
  --html-output "$SCRIPT_DIR/客户预警仪表盘.html"
  --contact-log "$CONTACT_LOG_PATH"
  --cooldown-days "$COOLDOWN_DAYS"
  --churn-multiplier "$CHURN_MULTIPLIER"
  --config "$SCRIPT_DIR/tech/config.json"
)

if [[ "${ANNIVERSARY_ONLY:-0}" == "1" ]]; then
  ARGS+=(--anniversary-only)
fi

if [[ -n "${ANNIVERSARY_MONTHS:-}" ]]; then
  ARGS+=(--anniversary-months "$ANNIVERSARY_MONTHS")
fi

if [[ -n "${MAX_ACTION:-}" ]]; then
  ARGS+=(--max-action "$MAX_ACTION")
fi

# 可选：排除最近 N 天内下单的客户（默认 30；环境变量 EXCLUDE_RECENT_DAYS 可覆盖）
if [[ -n "${EXCLUDE_RECENT_DAYS:-}" ]]; then
  ARGS+=(--exclude-recent-days "$EXCLUDE_RECENT_DAYS")
fi

# SHOW_ALL=1 时，展示所有客户：不过滤高退货 & 不排除近单
if [[ "${SHOW_ALL:-0}" == "1" ]]; then
  ARGS+=(--allow-high-return)
  # 若未显式设置，强制 recent 过滤为 0
  if [[ -z "${EXCLUDE_RECENT_DAYS:-}" ]]; then
    ARGS+=(--exclude-recent-days 0)
  fi
fi

echo "📊 2/2 生成客户预警视图（复购周期倍数: ${CHURN_MULTIPLIER}x）..."
if ! python3 "$SCRIPT_DIR/tech/generate_customer_alerts.py" "${ARGS[@]}"; then
  fail "生成客户预警失败，请检查命令行输出。"
fi

echo "✅ 已根据今天的数据生成：tech/客户预警输出.xlsx 与 客户预警仪表盘.html"

# 🧹 清理冗余的账单变体文件（保留主文件 账单汇总_全部.xlsx 和兼容文件 账单汇总_截至10月前.xlsx）
echo "🧹 清理冗余文件..."
CLEANUP_COUNT=0

# 删除未被使用的账单变体（保留 账单汇总_全部.xlsx 和 账单汇总_截至10月前.xlsx）
REDUNDANT_FILES=(
  "$SCRIPT_DIR/tech/账单汇总_截至本月前.xlsx"
  "$SCRIPT_DIR/tech/账单汇总_当月.xlsx"
  "$SCRIPT_DIR/tech/账单汇总_今日.xlsx"
)

for file in "${REDUNDANT_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    rm -f "$file"
    CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
    echo "  ✓ 已删除: $(basename "$file")"
  fi
done

if [[ $CLEANUP_COUNT -gt 0 ]]; then
  echo "✅ 已清理 $CLEANUP_COUNT 个冗余账单文件（节省约 7 MB）"
fi

# 可选：将 HTML 同步到 docs/index.html（便于 GitHub Pages 发布）
if [[ "${PUBLISH_TO_DOCS:-0}" == "1" ]]; then
  DOCS_DIR="$SCRIPT_DIR/docs"
  mkdir -p "$DOCS_DIR"
  cp -f "$SCRIPT_DIR/客户预警仪表盘.html" "$DOCS_DIR/index.html"
  echo "📤 已同步到 docs/index.html（可用于 GitHub Pages 发布）"
fi

pause
