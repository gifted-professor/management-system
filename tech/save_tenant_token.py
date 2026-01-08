'''
Author: gifted-professor 1044396185@qq.com
Date: 2025-11-14 14:42:23
LastEditors: gifted-professor 1044396185@qq.com
LastEditTime: 2025-11-14 14:42:24
FilePath: /表格【Codex】_副本/tech/save_tenant_token.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%ao'ge
'''
#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / '.env.local'

def read_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
        if m:
            k, v = m.group(1), m.group(2)
            env[k] = v
    return env

def write_env(path: Path, updates: dict):
    lines = []
    existing = read_env(path)
    existing.update(updates)
    for k, v in existing.items():
        lines.append(f'{k}={v}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main():
    env = read_env(ENV_PATH)
    app_id = env.get('FEISHU_APP_ID') or os.getenv('FEISHU_APP_ID')
    app_secret = env.get('FEISHU_APP_SECRET') or os.getenv('FEISHU_APP_SECRET')
    if not app_id or not app_secret:
        print('Missing FEISHU_APP_ID or FEISHU_APP_SECRET')
        return 1
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    body = {'app_id': app_id, 'app_secret': app_secret}
    try:
        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        print('Request failed')
        return 2
    token = None
    if isinstance(data, dict) and data.get('code') == 0:
        token = data.get('tenant_access_token') or data.get('data', {}).get('tenant_access_token')
    elif isinstance(data, dict):
        token = data.get('data', {}).get('tenant_access_token')
    if not token:
        print('No token in response')
        return 3
    write_env(ENV_PATH, {'FEISHU_TENANT_ACCESS_TOKEN': token})
    print('Tenant token saved to .env.local')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())