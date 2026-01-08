'''
Author: gifted-professor 1044396185@qq.com
Date: 2025-11-14 14:29:02
LastEditors: gifted-professor 1044396185@qq.com
LastEditTime: 2025-11-14 14:29:04
FilePath: /表格【Codex】_副本/tech/contact_server.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
import requests

APP_TOKEN = os.getenv('FEISHU_CONTACT_APP_TOKEN') or os.getenv('FEISHU_APP_TOKEN')
TABLE_ID = os.getenv('FEISHU_CONTACT_TABLE_ID') or os.getenv('FEISHU_TABLE_ID')
UAT = os.getenv('FEISHU_USER_ACCESS_TOKEN')
TENANT = os.getenv('FEISHU_TENANT_ACCESS_TOKEN')
PORT = int(os.getenv('CONTACT_SERVER_PORT') or '5005')

def auth_headers() -> dict:
    token = UAT or TENANT
    return {
        'Authorization': f'Bearer {token}' if token else '',
        'Content-Type': 'application/json; charset=utf-8',
    }

def list_fields(app_token: str, table_id: str) -> list:
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
    headers = auth_headers()
    params = {}
    page_token = None
    names = []
    while True:
        if page_token:
            params['page_token'] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break
        items = data.get('data', {}).get('items', []) or []
        for it in items:
            n = it.get('field_name')
            if isinstance(n, str) and n:
                names.append(n)
        page_token = data.get('data', {}).get('page_token')
        if not data.get('data', {}).get('has_more'):
            break
    return names

def pick_name(candidates: list[str], available: list[str]) -> str | None:
    s = set(available)
    for c in candidates:
        if c in s:
            return c
    return None

def create_contact_record(phone: str, name: str, owner: str, platform: str, note: str | None = None) -> dict:
    if not (APP_TOKEN and TABLE_ID):
        return {'ok': False, 'error': 'Missing FEISHU_CONTACT_APP_TOKEN or FEISHU_CONTACT_TABLE_ID'}
    fields_available = list_fields(APP_TOKEN, TABLE_ID)
    # 兼容不同中文/英文列名
    phone_col = pick_name(['手机号','手机','手机号码','联系电话','电话','联系方式','Phone','phone'], fields_available)
    date_col = pick_name(['最后联系日期','最后联系日','最近联系日期','最近联系日','员工联系日期','联系日期','LastContact','last_contact'], fields_available)
    owner_col = pick_name(['联系人','负责人','跟进人','Owner','owner'], fields_available)
    platform_col = pick_name(['联系平台','主要平台','平台','Platform','platform'], fields_available)
    note_col = pick_name(['备注','Note','note'], fields_available)
    name_col = pick_name(['姓名','客户名称','顾客姓名','Name','name'], fields_available)
    fields_out = {}
    if phone_col: fields_out[phone_col] = phone
    if date_col: fields_out[date_col] = datetime.now().strftime('%Y-%m-%d')
    if owner_col: fields_out[owner_col] = owner or ''
    if platform_col: fields_out[platform_col] = platform or ''
    if note_col and note is not None: fields_out[note_col] = note
    if name_col: fields_out[name_col] = name or ''
    if not fields_out:
        return {'ok': False, 'error': 'No matching columns found in target table', 'available': fields_available}
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records'
    body = {'records': [{'fields': fields_out}]}
    resp = requests.post(url, headers=auth_headers(), json=body, timeout=30)
    try:
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        return {'ok': False, 'error': f'HTTP {resp.status_code}: {exc}', 'detail': detail, 'fields': fields_out, 'available': fields_available}
    return {'ok': True, 'data': data}

def call_deepseek_analysis(api_key: str, mfr_name: str, sku_stats: list) -> dict:
    if not api_key:
        return {'ok': False, 'error': 'Missing API Key'}
    url = "https://api.deepseek.com/chat/completions"
    prompt = f"""
    你是一位电商资深运营专家。请分析厂家【{mfr_name}】的货品表现数据，并给出具体、可操作的运营建议。
    
    数据分析重点：
    1. 识别出高风险款式（退货率高或毛利低）。
    2. 针对退货原因（如质量问题、色差、尺码不准等）给出改进建议。
    3. 语言要专业、干练，给运营看，不需要客套话。
    4. 结果控制在 250 字以内。
    
    待分析数据：
    {json.dumps(sku_stats, ensure_ascii=False, indent=2)}
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个电商数据分析助手，擅长通过订单数据发现经营风险并提供战术建议。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": False
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=40)
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']
        return {'ok': True, 'analysis': content}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        
        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8')) if raw else {}
        except Exception:
            payload = {}

        if parsed.path == '/analyze_manufacturer':
            api_key = payload.get('api_key')
            mfr_name = payload.get('mfr_name')
            sku_stats = payload.get('sku_stats')
            result = call_deepseek_analysis(api_key, mfr_name, sku_stats)
            body = json.dumps(result, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path != '/mark':
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        
        phone = str(payload.get('phone') or '').strip()
        name = str(payload.get('name') or '').strip()
        owner = str(payload.get('owner') or '').strip()
        platform = str(payload.get('platform') or '').strip()
        note = str(payload.get('note') or '').strip()
        result = create_contact_record(phone, name, owner, platform, note)
        body = json.dumps(result, ensure_ascii=False).encode('utf-8')
        self.send_response(200 if result.get('ok') else 500)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    httpd = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Contact server listening on http://127.0.0.1:{PORT}/mark')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
