#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv
import re

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

def parse_bitable_url(url):
    match = re.search(r'/base/([a-zA-Z0-9]+)', url)
    app_token = match.group(1) if match else None
    table_match = re.search(r'table=([a-zA-Z0-9]+)', url)
    table_id = table_match.group(1) if table_match else None
    return app_token, table_id

BITABLE_URL = os.getenv('BITABLE_URL')
if BITABLE_URL:
    BITABLE_APP_TOKEN, BITABLE_TABLE_ID = parse_bitable_url(BITABLE_URL)
else:
    BITABLE_APP_TOKEN = os.getenv('BITABLE_APP_TOKEN')
    BITABLE_TABLE_ID = os.getenv('BITABLE_TABLE_ID')

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

def clean_table():
    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        print("❌ 未配置飞书表格")
        return

    token = get_access_token()
    if not token:
        print("获取token失败")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"正在获取表格 {BITABLE_TABLE_ID} 中的所有记录...")
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records'

    response = requests.get(url, headers=headers)
    result = response.json()

    if result.get('code') != 0:
        print(f"获取记录失败: {result.get('msg')}")
        return

    items = result.get('data', {}).get('items', [])
    total = len(items)
    print(f"共找到 {total} 条记录")

    if total == 0:
        print("表格已经是空的")
        return

    print("正在逐个删除记录...")
    for item in items:
        record_id = item.get('record_id')
        delete_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records/{record_id}'
        delete_response = requests.delete(delete_url, headers=headers)
        if delete_response.json().get('code') == 0:
            print(f"  ✓ 删除记录 {record_id}")
        else:
            print(f"  ✗ 删除失败: {delete_response.json().get('msg')}")

    print("\n✅ 表格清理完成，现在可以重新运行脚本写入新数据")

if __name__ == "__main__":
    clean_table()
