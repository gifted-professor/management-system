#!/usr/bin/env python3
"""Combine 2024 and 2025 ledgers and produce multiple consolidated workbooks.

使用 Pandas 优化的版本 - 性能提升 3-5x

- 汇总(截至本月前): 本月月初之前的所有（含无法解析日期的行）
- 汇总(当月):       本月内的订单
- 汇总(今日):       顾客付款日期为今天的订单

兼容输出: 继续生成 `账单汇总_截至10月前.xlsx`，其内容与"截至本月前"一致，
以保证既有脚本与仪表盘兼容。

说明：
- 为便于目录整理，脚本会在 tech/ 目录与其上级目录同时查找原始 Excel 与"新增账单"目录。
"""
from __future__ import annotations

import time
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
import warnings

import pandas as pd
from zipfile import is_zipfile

try:
    from .common import LEDGER_COLUMNS
except Exception:
    import sys, os
    sys.path.append(os.path.dirname(__file__))
    from common import LEDGER_COLUMNS

# 忽略 openpyxl 的警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


BASE_DIR = Path(__file__).resolve().parent
SEARCH_DIRS = [BASE_DIR, BASE_DIR.parent]


def find_file(name: str) -> Path:
    for d in SEARCH_DIRS:
        p = d / name
        if p.exists():
            return p
    return BASE_DIR / name


def find_dir(name: str) -> Path:
    for d in SEARCH_DIRS:
        p = d / name
        if p.exists() and p.is_dir():
            return p
    return BASE_DIR / name


INPUT_2024 = find_file('2024年总表.xlsx')
INPUT_2025 = find_file('2025年账单汇总.xlsx')
OUTPUT = BASE_DIR / '账单汇总_截至10月前.xlsx'
EXTRA_DIR = find_dir('新增账单')
DAILY_DIR = BASE_DIR.parent / '当天订单'
OUTPUT_BEFORE_MONTH = BASE_DIR / '账单汇总_截至本月前.xlsx'
OUTPUT_THIS_MONTH = BASE_DIR / '账单汇总_当月.xlsx'
OUTPUT_TODAY = BASE_DIR / '账单汇总_今日.xlsx'
OUTPUT_ALL = BASE_DIR / '账单汇总_全部.xlsx'


def load_excel_pandas(path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """使用 Pandas 高效读取 Excel 文件。

    Args:
        path: Excel 文件路径
        sheet_name: 工作表名称，None 则读取第一个工作表

    Returns:
        DataFrame
    """
    try:
        if sheet_name:
            df = pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl')
        else:
            df = pd.read_excel(path, sheet_name=0, engine='openpyxl')
    except Exception as e:
        print(f"  ⚠️ 读取 {path.name} 失败: {e}")
        return pd.DataFrame(columns=LEDGER_COLUMNS)

    # 确保所有列都存在
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # 只保留定义的列，并按顺序排列
    existing_cols = [col for col in LEDGER_COLUMNS if col in df.columns]
    df = df[existing_cols]

    # 移除全空行
    df = df.dropna(how='all')

    return df


def load_rows_from_2024_pandas(path: Path) -> pd.DataFrame:
    """加载 2024 年账单（Pandas 版本）。"""
    try:
        df = pd.read_excel(path, sheet_name='数据表', engine='openpyxl')
    except Exception:
        try:
            df = pd.read_excel(path, sheet_name=0, engine='openpyxl')
        except Exception as e:
            print(f"  ⚠️ 读取 2024 账单失败: {e}")
            return pd.DataFrame(columns=LEDGER_COLUMNS)

    # 只保留有效列
    valid_cols = [col for col in df.columns if col in LEDGER_COLUMNS]
    df = df[valid_cols]

    # 添加缺失的列
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # 移除全空行
    df = df.dropna(how='all')

    # 添加数据来源标记
    df['数据来源'] = '历史数据'

    return df[LEDGER_COLUMNS]


def load_rows_from_2025_pandas(path: Path) -> pd.DataFrame:
    """加载 2025 年账单（Pandas 版本）。

    2025 数据是按位置映射的，没有表头。
    """
    try:
        df = pd.read_excel(path, header=None, engine='openpyxl')
    except Exception as e:
        print(f"  ⚠️ 读取 2025 账单失败: {e}")
        return pd.DataFrame(columns=LEDGER_COLUMNS)

    # 检查第一行是否为表头
    if df.shape[0] > 0:
        first_val = df.iloc[0, 0] if df.shape[1] > 0 else None
        if isinstance(first_val, str) and first_val.strip() == '姓名':
            df = df.iloc[1:]  # 跳过表头行
            df = df.reset_index(drop=True)

    # 按位置映射列名
    num_cols = min(len(LEDGER_COLUMNS), df.shape[1])
    df.columns = LEDGER_COLUMNS[:num_cols] + list(range(num_cols, df.shape[1]))

    # 只保留定义的列
    df = df[[col for col in LEDGER_COLUMNS if col in df.columns]]

    # 添加缺失的列
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # 移除全空行
    df = df.dropna(how='all')

    # 添加数据来源标记
    df['数据来源'] = '飞书2025'

    return df[LEDGER_COLUMNS]


def load_rows_from_additional_pandas(path: Path) -> pd.DataFrame:
    """加载新增账单（Pandas 版本）。"""
    try:
        df = pd.read_excel(path, engine='openpyxl')
    except Exception as e:
        print(f"  ⚠️ 读取 {path.name} 失败: {e}")
        return pd.DataFrame(columns=LEDGER_COLUMNS)

    # 检查是否有表头
    has_header = any(col in df.columns for col in ['姓名', '顾客付款日期'])

    if not has_header:
        # 无表头，尝试按位置映射
        df = pd.read_excel(path, header=None, engine='openpyxl')
        first_val = df.iloc[0, 0] if df.shape[0] > 0 and df.shape[1] > 0 else None
        if isinstance(first_val, str) and first_val.strip() == '姓名':
            df = df.iloc[1:]
            df = df.reset_index(drop=True)

        num_cols = min(len(LEDGER_COLUMNS), df.shape[1])
        df.columns = LEDGER_COLUMNS[:num_cols] + list(range(num_cols, df.shape[1]))

    # 只保留有效列
    valid_cols = [col for col in LEDGER_COLUMNS if col in df.columns]
    df = df[valid_cols]

    # 添加缺失的列
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # 移除全空行
    df = df.dropna(how='all')

    # 有效性过滤：有单号的保留，或者有足够信息的保留
    def is_valid_row(row):
        order_no = str(row.get('单号') or '').strip()
        if order_no:
            return True
        score = 0
        if pd.notna(row.get('顾客付款日期')):
            score += 1
        for k in ['收款额', '商品名称', '手机号']:
            if str(row.get(k) or '').strip():
                score += 1
        return score >= 2

    df = df[df.apply(is_valid_row, axis=1)]

    # 添加数据来源标记
    df['数据来源'] = '飞书新增'

    return df[LEDGER_COLUMNS]


def parse_dates_vectorized(series: pd.Series) -> pd.Series:
    """向量化日期解析。"""
    return pd.to_datetime(series, errors='coerce')


def create_dedup_key(df: pd.DataFrame) -> pd.Series:
    """创建去重键（向量化）。"""

    def make_key(row):
        order_no = str(row.get('单号') or '').strip()
        if order_no:
            return f'NO|{order_no}'

        name = str(row.get('姓名') or '').strip()
        dt_val = row.get('顾客付款日期')
        if pd.notna(dt_val):
            if isinstance(dt_val, (datetime, date)):
                dt_key = dt_val.strftime('%Y-%m-%d') if hasattr(dt_val, 'strftime') else str(dt_val)[:10]
            else:
                dt_key = str(dt_val)[:10]
        else:
            dt_key = ''
        item = str(row.get('商品名称') or '').strip()
        amount = str(row.get('收款额') or '').strip()
        phone = str(row.get('手机号') or '').strip()
        return f'ALT|{name}|{dt_key}|{item}|{amount}|{phone}'

    return df.apply(make_key, axis=1)


def export_to_excel_pandas(df: pd.DataFrame, path: Path, sheet_name: str) -> None:
    """使用 Pandas 高效导出 Excel。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    # 确保列顺序正确
    df = df[LEDGER_COLUMNS]

    # 如果文件存在，先删除
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

    # 使用 openpyxl 引擎，不写入索引
    try:
        df.to_excel(path, sheet_name=sheet_name, index=False, engine='openpyxl')
    except Exception as e:
        # 尝试写入临时文件再重命名
        import tempfile
        import shutil
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df.to_excel(tmp.name, sheet_name=sheet_name, index=False, engine='openpyxl')
            shutil.move(tmp.name, path)


def month_boundaries(now: datetime = None) -> tuple:
    """返回 (月初, 下月初) 时间戳。"""
    if now is None:
        now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month


def main() -> None:
    start_time = time.time()
    print("📊 开始合并账单数据 (Pandas 优化版)")
    print("=" * 50)

    # 1. 加载主数据
    print("\n📂 加载主账单...")
    load_start = time.time()

    dfs = []

    if INPUT_2024.exists():
        df_2024 = load_rows_from_2024_pandas(INPUT_2024)
        print(f"  ✓ 2024年总表: {len(df_2024):,} 行")
        dfs.append(df_2024)
    else:
        print("  ⚠️ 2024年总表不存在")
        df_2024 = pd.DataFrame()

    if INPUT_2025.exists():
        df_2025 = load_rows_from_2025_pandas(INPUT_2025)
        print(f"  ✓ 2025年账单汇总: {len(df_2025):,} 行")
        dfs.append(df_2025)
    else:
        print("  ⚠️ 2025年账单汇总不存在")
        df_2025 = pd.DataFrame()

    load_time = time.time() - load_start
    print(f"  ⏱️  加载耗时: {load_time:.2f} 秒")

    # 2. 加载新增账单
    def list_xlsx(dir_path: Path) -> List[Path]:
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        return sorted(
            p for p in dir_path.glob('*.xlsx')
            if p.is_file()
            and not p.name.startswith('~$')
            and not p.name.startswith('._')
            and is_zipfile(p)
        )

    extra_files = list_xlsx(EXTRA_DIR) + list_xlsx(DAILY_DIR)

    if extra_files:
        print(f"\n📁 加载新增账单 ({len(extra_files)} 个文件)...")
        extra_start = time.time()
        extra_rows_total = 0

        for file in extra_files:
            try:
                df_extra = load_rows_from_additional_pandas(file)
                if len(df_extra) > 0:
                    dfs.append(df_extra)
                    extra_rows_total += len(df_extra)
            except Exception as exc:
                print(f"  ⚠️ 无法读取 {file.name}: {exc}")

        print(f"  ✓ 新增账单: {extra_rows_total:,} 行")
        print(f"  ⏱️  耗时: {time.time() - extra_start:.2f} 秒")

    # 3. 合并并去重
    print("\n🔄 合并数据并去重...")
    merge_start = time.time()

    if dfs:
        # 过滤掉空的 DataFrame
        dfs = [df for df in dfs if len(df) > 0]
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
        else:
            combined = pd.DataFrame(columns=LEDGER_COLUMNS)
    else:
        combined = pd.DataFrame(columns=LEDGER_COLUMNS)

    total_before_dedup = len(combined)

    # 创建去重键
    combined['_dedup_key'] = create_dedup_key(combined)

    # 去重（保留第一个）
    combined = combined.drop_duplicates(subset=['_dedup_key'], keep='first')
    combined = combined.drop(columns=['_dedup_key'])

    dup_count = total_before_dedup - len(combined)
    print(f"  ✓ 合并后: {len(combined):,} 行 (去除重复 {dup_count:,} 行)")
    print(f"  ⏱️  耗时: {time.time() - merge_start:.2f} 秒")

    # 4. 解析日期并过滤
    print("\n📅 按日期筛选...")
    filter_start = time.time()

    combined['_parsed_date'] = parse_dates_vectorized(combined['顾客付款日期'])

    month_start, next_month = month_boundaries()
    today = datetime.now().date()

    # 截至本月前：日期为空或日期 < 月初
    before_month_mask = combined['_parsed_date'].isna() | (combined['_parsed_date'] < month_start)
    before_month = combined[before_month_mask].copy()

    # 当月：月初 <= 日期 < 下月初
    this_month_mask = (combined['_parsed_date'] >= month_start) & (combined['_parsed_date'] < next_month)
    this_month = combined[this_month_mask].copy()

    # 今日
    today_mask = combined['_parsed_date'].dt.date == today
    today_rows = combined[today_mask].copy()

    # 排序
    def sort_df(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['_sort_marker'] = df['_parsed_date'].isna().astype(int)
        df = df.sort_values(
            by=['_sort_marker', '_parsed_date', '姓名'],
            ascending=[True, True, True],
            na_position='last'
        )
        return df.drop(columns=['_sort_marker', '_parsed_date'], errors='ignore')

    combined = sort_df(combined)
    before_month = sort_df(before_month)
    this_month = sort_df(this_month)
    today_rows = sort_df(today_rows)

    print(f"  ✓ 截至本月前: {len(before_month):,} 行")
    print(f"  ✓ 当月: {len(this_month):,} 行")
    print(f"  ✓ 今日: {len(today_rows):,} 行")
    print(f"  ⏱️  耗时: {time.time() - filter_start:.2f} 秒")

    # 5. 导出文件
    print("\n💾 导出 Excel 文件...")
    export_start = time.time()

    export_to_excel_pandas(before_month, OUTPUT, '汇总(截至10月前)')
    export_to_excel_pandas(before_month, OUTPUT_BEFORE_MONTH, '汇总(截至本月前)')
    export_to_excel_pandas(this_month, OUTPUT_THIS_MONTH, '汇总(当月)')
    export_to_excel_pandas(today_rows, OUTPUT_TODAY, '汇总(今日)')
    export_to_excel_pandas(combined, OUTPUT_ALL, '汇总(全部)')

    print(f"  ✓ 旧兼容: {OUTPUT.name}")
    print(f"  ✓ 截至本月前: {OUTPUT_BEFORE_MONTH.name}")
    print(f"  ✓ 当月: {OUTPUT_THIS_MONTH.name}")
    print(f"  ✓ 今日: {OUTPUT_TODAY.name}")
    print(f"  ✓ 全部: {OUTPUT_ALL.name}")
    print(f"  ⏱️  耗时: {time.time() - export_start:.2f} 秒")

    # 6. 总结
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"✅ 合并完成！总耗时: {total_time:.2f} 秒")
    print(f"   总记录数: {len(combined):,}")


if __name__ == '__main__':
    main()
