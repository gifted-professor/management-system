#!/usr/bin/env python3
# relocated to tech/
"""
从飞书多维表「库存管理」拉取当月订单并导出为本地新增账单 Excel。

用法示例：
  python3 fetch_bitable_month.py \
    --app-token GRZsbC1pOaTiazsV9ryc3wc8nIe \
    --table-id tbloGctGk4QoXwll \
    --month 2025-11 \
    --output 新增账单/拉取_202511.xlsx

鉴权：优先读取环境变量 FEISHU_USER_ACCESS_TOKEN（User Access Token）。
也可通过 --token 显式传入。

实现说明：
  - 先获取表的字段列表，仅请求存在的列，避免因缺列报错。
  - 按「顾客付款日期」降序分页抓取；在本地过滤“当月”范围。
  - 将字段值规范化为纯文本/数字；导出为标准 COLUMNS 表头。
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from openpyxl import Workbook
try:
    from .common import LEDGER_COLUMNS
except Exception:
    import sys, os
    sys.path.append(os.path.dirname(__file__))
    from common import LEDGER_COLUMNS


BASE_DIR = Path(__file__).resolve().parent
EXTRA_DIR = BASE_DIR / '新增账单'

# 目标表头，保持与 combine_ledgers.py 相同


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='从飞书多维表拉取当月订单到新增账单 Excel')
    p.add_argument('--app-token', default='GRZsbC1pOaTiazsV9ryc3wc8nIe', help='多维表 App Token')
    p.add_argument('--table-id', default='tbloGctGk4QoXwll', help='表 ID（如：库存管理）')
    p.add_argument('--view-id', default=None, help='可选：视图 ID')
    p.add_argument('--month', default=None, help='月份，格式 YYYY-MM；默认取当前月')
    p.add_argument('--platform', default=None, help='可选：仅拉取指定 出售平台')
    p.add_argument('--token', default=None, help='User Access Token；若未提供将读取 FEISHU_USER_ACCESS_TOKEN')
    p.add_argument('--app-id', default=None, help='App ID（可选，用于服务器到服务器获取租户令牌）')
    p.add_argument('--app-secret', default=None, help='App Secret（可选，用于服务器到服务器获取租户令牌）')
    p.add_argument('--tenant-token', default=None, help='Tenant Access Token（可选，直接提供）')
    p.add_argument('--output', default=None, help='输出路径；默认 新增账单/拉取_YYYYMM.xlsx')
    return p.parse_args()


def month_range(yyyymm: Optional[str]) -> Tuple[datetime, datetime]:
    if yyyymm:
        dt = datetime.strptime(yyyymm, '%Y-%m')
    else:
        now = datetime.now()
        dt = datetime(year=now.year, month=now.month, day=1)
    start = dt.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)
    return start, end


class FeishuClient:
    def __init__(self, uat: Optional[str] = None, refresh_token: Optional[str] = None,
                 app_id: Optional[str] = None, app_secret: Optional[str] = None,
                 tenant_access_token: Optional[str] = None) -> None:
        self.uat = uat
        self.refresh_token = refresh_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token = tenant_access_token
        if not (self.uat or self.tenant_access_token) and self.app_id and self.app_secret:
            self._get_tenant_token()

    def headers(self) -> Dict[str, str]:
        token = self.uat or self.tenant_access_token
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
        }

    def _maybe_refresh(self) -> bool:
        # 优先刷新用户令牌
        if self.refresh_token:
            url = 'https://open.feishu.cn/open-apis/authen/v1/refresh_access_token'
            body = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token}
            resp = requests.post(url, json=body, timeout=30)
            try:
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return False
            if isinstance(data, dict) and data.get('code') == 0:
                d = data.get('data', {})
                self.uat = d.get('access_token') or self.uat
                self.refresh_token = d.get('refresh_token') or self.refresh_token
                return True
            return False
        # 其次通过应用凭证重新获取租户令牌
        if self.app_id and self.app_secret:
            return self._get_tenant_token()
        return False

    def _get_tenant_token(self) -> bool:
        url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
        body = {'app_id': self.app_id, 'app_secret': self.app_secret}
        resp = requests.post(url, json=body, timeout=30)
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return False
        if isinstance(data, dict) and data.get('code') == 0:
            self.tenant_access_token = data.get('tenant_access_token') or self.tenant_access_token
            return True
        d = data.get('data') if isinstance(data, dict) else None
        if isinstance(d, dict) and d.get('tenant_access_token'):
            self.tenant_access_token = d.get('tenant_access_token')
            return True
        return False

    def _should_refresh(self, data: Dict[str, Any], status: int) -> bool:
        if status == 401:
            return True
        # 一些场景返回 200 但 code 非 0，且提示 token 问题
        code = data.get('code')
        msg = (data.get('msg') or '').lower()
        if code and any(k in msg for k in ['token', 'unauthorized', 'no permission']):
            return True
        return False

    def get(self, url: str, *, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        resp = requests.get(url, headers=self.headers(), params=params, timeout=timeout)
        status = resp.status_code
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            return {}
        if self._should_refresh(data, status) and self._maybe_refresh():
            resp = requests.get(url, headers=self.headers(), params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return data

    def post(self, url: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
        resp = requests.post(url, headers=self.headers(), params=params or {}, json=json_body or {}, timeout=timeout)
        status = resp.status_code
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            return {}
        if self._should_refresh(data, status) and self._maybe_refresh():
            resp = requests.post(url, headers=self.headers(), params=params or {}, json=json_body or {}, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return data


def list_fields(client: FeishuClient, app_token: str, table_id: str, view_id: Optional[str] = None) -> List[str]:
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
    params: Dict[str, Any] = {}
    if view_id:
        params['view_id'] = view_id
    names: List[str] = []
    page_token: Optional[str] = None
    while True:
        if page_token:
            params['page_token'] = page_token
        data = client.get(url, params=params, timeout=30)
        items = data.get('data', {}).get('items', [])
        for it in items:
            n = it.get('field_name')
            if isinstance(n, str) and n:
                names.append(n)
        page_token = data.get('data', {}).get('page_token')
        has_more = data.get('data', {}).get('has_more')
        if not has_more:
            break
    return names


def normalize_field_value(v: Any) -> Any:
    # 数值
    if isinstance(v, (int, float)):
        return v
    # 字符串
    if isinstance(v, str):
        return v
    # 单元格结构值
    if isinstance(v, dict):
        # DateTime as milliseconds
        # 有些 SDK 返回 {"type":2,"value":[...]}，但 REST v1 直接返回基础类型，这里做兜底
        if 'value' in v:
            val = v['value']
            if isinstance(val, list):
                # 合并文本 / 选项
                out: List[str] = []
                for item in val:
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        out.append(str(item['text']))
                    else:
                        out.append(str(item))
                return ' / '.join(x for x in out if x)
            return val
    # 文本数组 [{text:...}]
    if isinstance(v, list):
        out: List[str] = []
        for item in v:
            if isinstance(item, dict) and 'text' in item:
                out.append(str(item['text']))
            elif isinstance(item, str):
                out.append(item)
        return ' '.join(out).strip()
    return v


def ms_to_date(ms: int) -> str:
    try:
        # 飞书返回毫秒戳（UTC+0），按本地日期写入 YYYY-MM-DD
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return ''


def fetch_month_records(client: FeishuClient, app_token: str, table_id: str, month_start: datetime, next_month: datetime,
                        want_fields: List[str], view_id: Optional[str] = None, platform: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search'
    page_token: Optional[str] = None
    results: List[Dict[str, Any]] = []
    while True:
        body: Dict[str, Any] = {
            'automatic_fields': True,
            'sort': [{'field_name': '顾客付款日期', 'desc': True}],
            'field_names': want_fields,
        }
        if view_id:
            body['view_id'] = view_id
        if page_token:
            # 注意：search 接口的分页在 querystring 上
            pass
        params: Dict[str, Any] = {'page_size': 200}
        if page_token:
            params['page_token'] = page_token
        data = client.post(url, params=params, json_body=body, timeout=60)
        items = data.get('data', {}).get('items', [])
        for it in items:
            fields = it.get('fields', {})
            # 提取付款日期
            raw_dt = fields.get('顾客付款日期')
            # 既可能是毫秒，也可能是字符串/日期
            pay_date: Optional[str] = None
            pay_ts: Optional[int] = None
            if isinstance(raw_dt, (int, float)):
                pay_ts = int(raw_dt)
                pay_date = ms_to_date(pay_ts)
            elif isinstance(raw_dt, str):
                pay_date = raw_dt
            # 本地过滤月份范围
            in_month = True
            if pay_date:
                try:
                    d = datetime.strptime(pay_date[:10], '%Y-%m-%d')
                    in_month = (month_start <= d < next_month)
                except Exception:
                    # 无法解析，则不过滤
                    in_month = True
            if not in_month:
                # 由于按日期降序排列，一旦出现小于本月起点的数据，可直接停止
                # 但为稳妥，只有当明确解析出早于月初才中断
                if pay_date:
                    try:
                        d2 = datetime.strptime(pay_date[:10], '%Y-%m-%d')
                        if d2 < month_start:
                            return results
                    except Exception:
                        pass
                continue
            # 平台过滤
            if platform and fields.get('出售平台') and fields.get('出售平台') != platform:
                continue

            # 规范化为扁平字典
            rec: Dict[str, Any] = {col: None for col in LEDGER_COLUMNS}
            for k, v in fields.items():
                if k in rec:
                    rec[k] = normalize_field_value(v)
            # 确保日期是标准文本
            if pay_ts is not None:
                rec['顾客付款日期'] = ms_to_date(pay_ts)
            results.append(rec)

        page_token = data.get('data', {}).get('page_token')
        has_more = data.get('data', {}).get('has_more')
        if not has_more:
            break

    return results


def export_excel(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title='当月新增')
    ws.append(LEDGER_COLUMNS)
    for rec in records:
        ws.append([rec.get(col) for col in LEDGER_COLUMNS])
    wb.save(path)


def main() -> None:
    args = parse_args()
    # 支持三种凭证：UAT、Tenant Token、AppID+Secret
    uat = args.token or os.getenv('FEISHU_USER_ACCESS_TOKEN')
    refresh_token = os.getenv('FEISHU_REFRESH_TOKEN')
    app_id = args.app_id or os.getenv('FEISHU_APP_ID')
    app_secret = args.app_secret or os.getenv('FEISHU_APP_SECRET')
    tenant_access_token = args.tenant_token or os.getenv('FEISHU_TENANT_ACCESS_TOKEN')
    if not (uat or tenant_access_token or (app_id and app_secret)):
        raise SystemExit('缺少凭证：请提供 User Access Token，或 FEISHU_APP_ID/FEISHU_APP_SECRET，或 FEISHU_TENANT_ACCESS_TOKEN。')

    month_start, next_month = month_range(args.month)
    yyyymm = month_start.strftime('%Y%m')
    out_path = Path(args.output) if args.output else (EXTRA_DIR / f'拉取_{yyyymm}.xlsx')

    # 获取可用字段名，避免请求不存在列导致报错
    client = FeishuClient(uat=uat, refresh_token=refresh_token,
                         app_id=app_id, app_secret=app_secret,
                         tenant_access_token=tenant_access_token)
    field_names = list_fields(client, args.app_token, args.table_id, args.view_id)
    wanted = [c for c in LEDGER_COLUMNS if c in field_names]
    # 确保关键列存在
    base_required = ['姓名', '顾客付款日期', '出售平台', '商品名称', '货品名', '收款额', '成本价', '单号', '手机号', '备注']
    for k in base_required:
        if k in field_names and k not in wanted:
            wanted.append(k)

    print(f'准备拉取 {month_start:%Y-%m} 当月订单……')
    recs = fetch_month_records(
        client=client,
        app_token=args.app_token,
        table_id=args.table_id,
        month_start=month_start,
        next_month=next_month,
        want_fields=wanted,
        view_id=args.view_id,
        platform=args.platform,
    )
    print(f'获取记录：{len(recs)} 条（当月）')
    export_excel(recs, out_path)
    print(f'已导出到：{out_path}')


if __name__ == '__main__':
    main()
