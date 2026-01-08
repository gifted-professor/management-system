#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度销售分析脚本
用途：快速生成指定月份范围的销售数据分析报告

使用方法：
    python3 tech/analyze_monthly_sales.py
    python3 tech/analyze_monthly_sales.py --start-month 5 --end-month 11 --year 2025

数据源：tech/账单汇总_全部.xlsx
"""

import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ============================================================
# 配置区域
# ============================================================

# 默认数据源路径
DEFAULT_SOURCE = Path(__file__).parent / "账单汇总_全部.xlsx"
DEFAULT_SHEET = "汇总(全部)"

# 退货类型定义
RETURN_TYPES = {"退", "换", "退芋圆"}  # 算退货
EXCLUDE_TYPES = {"取消"}              # 完全排除，不参与任何计算
# "补" 不算退货，但参与订单统计

# 排除货品关键词
EXCLUDE_PRODUCT_KEYWORDS = ["样品", "代发"]  # 货品名包含这些关键词的订单不参与统计


# ============================================================
# 核心函数
# ============================================================

def parse_excel_date(value):
    """处理混合日期格式（Excel序列号 + 字符串）"""
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # Excel序列号转日期
        try:
            return pd.Timestamp("1900-01-01") + pd.Timedelta(days=int(value) - 2)
        except:
            return pd.NaT
    if isinstance(value, str):
        try:
            return pd.to_datetime(value)
        except:
            return pd.NaT
    return pd.NaT


def load_data(source_path: Path, sheet_name: str) -> pd.DataFrame:
    """加载并预处理数据"""
    print(f"📂 读取数据: {source_path}")
    df = pd.read_excel(source_path, sheet_name=sheet_name)

    # 处理日期字段
    date_col = "顾客付款日期"
    if date_col in df.columns:
        df[date_col] = df[date_col].apply(parse_excel_date)
    else:
        raise ValueError(f"找不到日期字段: {date_col}")

    print(f"✅ 加载完成: {len(df):,} 条记录")
    return df


def filter_valid_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    筛选有效订单：
    1. 排除"取消"订单
    2. 排除货品名包含"样品"或"代发"的订单
    """
    refund_type_col = "退款类型"
    product_col = "货品名"

    # 排除取消订单
    mask = ~df[refund_type_col].isin(EXCLUDE_TYPES)

    # 排除样品和代发订单
    if product_col in df.columns:
        for keyword in EXCLUDE_PRODUCT_KEYWORDS:
            mask &= ~df[product_col].astype(str).str.contains(keyword, na=False)

    valid_df = df[mask].copy()
    excluded = len(df) - len(valid_df)
    print(f"📋 有效订单: {len(valid_df):,} 条 (排除 {excluded:,} 条取消/样品/代发订单)")

    return valid_df


def calculate_monthly_metrics(df: pd.DataFrame, year: int, start_month: int, end_month: int) -> pd.DataFrame:
    """计算月度指标"""
    date_col = "顾客付款日期"
    revenue_col = "收款额"
    refund_type_col = "退款类型"

    # 筛选指定日期范围
    df = df[df[date_col].notna()].copy()
    df["年"] = df[date_col].dt.year
    df["月"] = df[date_col].dt.month

    # 筛选年份和月份
    mask = (df["年"] == year) & (df["月"] >= start_month) & (df["月"] <= end_month)
    df = df[mask]

    if df.empty:
        print(f"⚠️ 没有找到 {year}年{start_month}-{end_month}月 的数据")
        return pd.DataFrame()

    # 按月分组统计
    results = []
    for month in range(start_month, end_month + 1):
        month_df = df[df["月"] == month]

        if month_df.empty:
            results.append({
                "月份": f"{year}-{month:02d}",
                "销售额": 0,
                "订单数": 0,
                "客单价": 0,
                "退货数": 0,
                "退货率": 0,
            })
            continue

        # 销售额
        revenue = month_df[revenue_col].sum()

        # 订单数
        order_count = len(month_df)

        # 客单价
        aov = revenue / order_count if order_count > 0 else 0

        # 退货数（退/换/退芋圆）
        return_count = month_df[refund_type_col].isin(RETURN_TYPES).sum()

        # 退货率
        return_rate = (return_count / order_count * 100) if order_count > 0 else 0

        results.append({
            "月份": f"{year}-{month:02d}",
            "销售额": revenue,
            "订单数": order_count,
            "客单价": aov,
            "退货数": return_count,
            "退货率": return_rate,
        })

    return pd.DataFrame(results)


def calculate_mom_growth(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """计算环比增长率"""
    df = metrics_df.copy()

    # 销售额环比
    df["销售额环比"] = df["销售额"].pct_change() * 100

    # 订单数环比
    df["订单数环比"] = df["订单数"].pct_change() * 100

    return df


def format_number(value, fmt=",.0f"):
    """格式化数字"""
    if pd.isna(value) or value == 0:
        return "-"
    return f"{value:{fmt}}"


def format_percent(value):
    """格式化百分比"""
    if pd.isna(value):
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def print_report(metrics_df: pd.DataFrame, year: int):
    """打印分析报告"""
    print("\n" + "=" * 70)
    print(f"📊 {year}年月度销售分析报告")
    print("=" * 70)

    # 计算环比
    df = calculate_mom_growth(metrics_df)

    # 打印表格头
    print(f"\n{'月份':^10} {'销售额':^12} {'订单数':^8} {'客单价':^8} {'退货率':^8} {'销售额环比':^10} {'订单数环比':^10}")
    print("-" * 70)

    # 打印每月数据
    for _, row in df.iterrows():
        month = row["月份"]
        revenue = f"¥{row['销售额']/10000:.1f}万"
        orders = f"{int(row['订单数'])}单"
        aov = f"¥{row['客单价']:.0f}"
        return_rate = f"{row['退货率']:.1f}%"
        rev_growth = format_percent(row["销售额环比"])
        ord_growth = format_percent(row["订单数环比"])

        print(f"{month:^10} {revenue:^12} {orders:^8} {aov:^8} {return_rate:^8} {rev_growth:^10} {ord_growth:^10}")

    # 打印合计
    print("-" * 70)
    total_revenue = df["销售额"].sum()
    total_orders = df["订单数"].sum()
    total_aov = total_revenue / total_orders if total_orders > 0 else 0
    total_returns = df["退货数"].sum()
    total_return_rate = (total_returns / total_orders * 100) if total_orders > 0 else 0

    print(f"{'合计':^10} ¥{total_revenue/10000:.1f}万{' ':^4} {int(total_orders)}单{' ':^4} ¥{total_aov:.0f}{' ':^4} {total_return_rate:.1f}%")

    # 关键洞察
    print("\n" + "=" * 70)
    print("💡 关键洞察")
    print("=" * 70)

    # 找出最高/最低月份
    valid_df = df[df["订单数"] > 0]
    if not valid_df.empty:
        best_rev_month = valid_df.loc[valid_df["销售额"].idxmax(), "月份"]
        worst_rev_month = valid_df.loc[valid_df["销售额"].idxmin(), "月份"]
        best_aov_month = valid_df.loc[valid_df["客单价"].idxmax(), "月份"]
        lowest_return_month = valid_df.loc[valid_df["退货率"].idxmin(), "月份"]
        highest_return_month = valid_df.loc[valid_df["退货率"].idxmax(), "月份"]

        # 客单价变化
        first_aov = valid_df.iloc[0]["客单价"]
        last_aov = valid_df.iloc[-1]["客单价"]
        aov_change = ((last_aov - first_aov) / first_aov * 100) if first_aov > 0 else 0

        # 订单数变化
        first_orders = valid_df.iloc[0]["订单数"]
        last_orders = valid_df.iloc[-1]["订单数"]
        orders_change = ((last_orders - first_orders) / first_orders * 100) if first_orders > 0 else 0

        print(f"\n📈 销售额最高: {best_rev_month} (¥{valid_df.loc[valid_df['销售额'].idxmax(), '销售额']/10000:.1f}万)")
        print(f"📉 销售额最低: {worst_rev_month} (¥{valid_df.loc[valid_df['销售额'].idxmin(), '销售额']/10000:.1f}万)")
        print(f"💰 客单价最高: {best_aov_month} (¥{valid_df.loc[valid_df['客单价'].idxmax(), '客单价']:.0f})")
        print(f"✅ 退货率最低: {lowest_return_month} ({valid_df.loc[valid_df['退货率'].idxmin(), '退货率']:.1f}%)")
        print(f"⚠️  退货率最高: {highest_return_month} ({valid_df.loc[valid_df['退货率'].idxmax(), '退货率']:.1f}%)")
        print(f"\n📊 客单价趋势: ¥{first_aov:.0f} → ¥{last_aov:.0f} ({aov_change:+.1f}%)")
        print(f"📊 订单数趋势: {int(first_orders)}单 → {int(last_orders)}单 ({orders_change:+.1f}%)")

    print("\n" + "=" * 70)
    print("📋 计算规则说明")
    print("=" * 70)
    print("• 有效订单 = 退款类型≠取消 且 货品名不含样品/代发")
    print("• 退货类型 = 退、换、退芋圆（不含'补'）")
    print("• 取消/样品/代发订单完全排除，不参与任何计算")
    print("• 收款额可以为0（正常订单包含免费赠品等）")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="月度销售分析脚本")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="数据源Excel文件路径")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SHEET, help="工作表名称")
    parser.add_argument("--year", type=int, default=2025, help="分析年份")
    parser.add_argument("--start-month", type=int, default=5, help="起始月份")
    parser.add_argument("--end-month", type=int, default=11, help="结束月份")

    args = parser.parse_args()

    # 加载数据
    df = load_data(args.source, args.sheet)

    # 筛选有效订单
    valid_df = filter_valid_orders(df)

    # 计算月度指标
    metrics_df = calculate_monthly_metrics(valid_df, args.year, args.start_month, args.end_month)

    if not metrics_df.empty:
        # 打印报告
        print_report(metrics_df, args.year)


if __name__ == "__main__":
    main()
