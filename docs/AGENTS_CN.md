# 仓库指南

（已移至 docs/ 以保持根目录整洁）

## 项目结构与模块组织
- 根目录仅保留三类目录：`2025 账单`（当年原始台账）、`清除数据`（历史清理归档）与自动化工作区 `tech/`。
- `tech/combine_ledgers.py` 合并 `2024年总表.xlsx` 与 `2025年账单汇总.xlsx`，生成 `tech/账单汇总_截至10月前.xlsx`。
- `tech/generate_customer_alerts.py` 基于汇总表产出客户风险与行动清单；触达页按“标记完成→优先级→姓名→最近下单日→主要平台→手机号→风险标签→推荐动作→偏好单品→主要负责人→有效订单数→退货率→未复购天数→平均客单价”排列；可选 HTML 仪表盘写入根目录 `客户预警仪表盘.html`。
- `tech/run_customer_dashboard.command` 为 macOS 双击脚本，记得保持可执行权限（`chmod +x`）。
- 已联系客户来源：优先从飞书多维表（Bitable）读取；若未配置令牌，则回退到本地 `tech/contact_log.xlsx`（两列：`手机号`、`最后联系日期`）。

## 构建、测试与开发命令
- `python3 tech/combine_ledgers.py`：在更新月度数据后重新生成 10 月前汇总表。
- `python3 tech/generate_customer_alerts.py --source tech/账单汇总_截至10月前.xlsx --sheet 汇总(截至10月前) --output tech/客户预警输出.xlsx`：输出最新客户预警 Excel。脚本会：
  - 若存在 Feishu 环境变量（见下），优先从多维表拉取“已联系客户”。
  - 否则读取 `--contact-log` 指定的 Excel（默认 `tech/contact_log.xlsx`）。
- `python3 tech/generate_customer_alerts.py --help`：查看纪念日过滤、HTML 导出等可选参数。
- `./tech/run_customer_dashboard.command`：一键同时生成 Excel 与 HTML 预警视图。

## 跟进冷却（Snooze）
默认从飞书多维表读取“已联系客户”。如需回退到本地 Excel，请在未配置 Feishu 令牌时使用。
一线同事也可继续在 `tech/contact_log.xlsx` 记录当日跟进：两列分别为 `手机号`、`最后联系日期`。
生成触达名单时，脚本会屏蔽冷却期内（默认 7 天，可用 `--cooldown-days` 调整）的手机号，避免重复催单。
若需全部客户重新出现，删除或暂时改名该 Excel 文件；测试不同窗口时修改参数或清理对应手机号记录。
根目录的 `客户预警仪表盘.html` 支持逐行勾选“跟进完成”，状态保存在浏览器中，并可通过“导出今日联系记录 (CSV)”按钮下载，便于填入 `contact_log.xlsx`。

## 代码风格与命名约定
- 遵循 PEP 8，使用 4 空格缩进和具描述性的 snake_case；常量（如 `COLUMNS`, `CUTOFF`）保持全大写。
- 保留类型标注与模块说明；文件路径统一使用 `pathlib.Path`。
- 用户提示信息保持中英兼顾、重点突出，沿用现有脚本的简洁输出。

## 测试规范
- 如需自动化验证，可在 `tests/` 下使用 `pytest` 或轻量脚本；建议用脱敏 Excel 片段作为夹具。
- 重点检验日期过滤：断言记录数量、最早/最晚付款日与预期一致。
- 手动验收时比对生成表格关键汇总值，并在浏览器确认 HTML 仪表盘无控制台报错。

## 提交与合并请求
- 提交说明使用动词开头、兼顾双语（例：`feat: 调整高价值客户流失阈值`），必要时点出受影响的工作簿。
- PR 描述中列出依赖的数据前置条件与使用示例；界面或报表改动需附前后对比截图。
- 关联相关工单或表格需求，并说明未纳入版本控制的原始月度账单。

## 安全与数据处理
- 原始台账含个人信息，截屏或分享前务必脱敏。
- 禁止提交真实生产 Excel；若需测试数据，请放入 `tests/fixtures/` 并确保已匿名化。

## 使用飞书多维表作为已联系来源
- 在仓库根目录创建 `.env.local`（可参考 `.env.local.example`），至少设置：
  - `FEISHU_CONTACT_APP_TOKEN`、`FEISHU_CONTACT_TABLE_ID`（必填）
  - `FEISHU_CONTACT_VIEW_ID`（可选，仅拉取该视图）
  - `FEISHU_USER_ACCESS_TOKEN` 或 `FEISHU_TENANT_ACCESS_TOKEN`（二选一）
- 本仓库脚本会在启动时自动读取 `.env.local`，若配置有效则优先从多维表拉取“已联系客户”，并在冷却期内（`COOLDOWN_DAYS`，默认 7 天）屏蔽这些手机号。
- 示例（基于“单号查询”表）：
  - `FEISHU_CONTACT_APP_TOKEN=GRZsbC1pOaTiazsV9ryc3wc8nIe`
  - `FEISHU_CONTACT_TABLE_ID=tblK0lGgBftyonCM`
  - `FEISHU_CONTACT_VIEW_ID=vewfuMyZFU`
  - 令牌（仅示例占位，实际请填写自己的有效 token）：`FEISHU_USER_ACCESS_TOKEN=...`
